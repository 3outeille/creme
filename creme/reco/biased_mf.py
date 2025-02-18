import collections
import copy
import functools

import numpy as np

from creme import stats
from creme import optim
from creme import utils

from . import base


__all__ = ['BiasedMF']


class BiasedMF(base.Recommender):
    """Biased Matrix Factorization for recommender systems.

    The model equation is defined as:

    $$\\hat{y}(x) = \\bar{y} + bu_{u} + bi_{i} + \\langle \\mathbf{v}_u, \\mathbf{v}_i \\rangle$$

    Where :math:`bu_{u}` and :math:`bi_{i}` are respectively the user and item biases. The last term
    being simply the dot product between the latent vectors of the given user-item pair:

    $$\\langle \\mathbf{v}_u, \\mathbf{v}_i \\rangle = \\sum_{f=1}^{k} \\mathbf{v}_{u, f} \\cdot \\mathbf{v}_{i, f}$$

    Where :math:`k` is the number of latent factors. The model expect dict inputs containing both a
    `user` and an `item` entries.

    Parameters:
        n_factors (int): Dimensionality of the factorization or number of latent factors.
        bias_optimizer (optim.Optimizer): The sequential optimizer used for updating the bias
            weights.
        latent_optimizer (optim.Optimizer): The sequential optimizer used for updating the latent
            weights.
        loss (optim.Loss): The loss function to optimize for.
        l2_bias (float): Amount of L2 regularization used to push bias weights towards 0.
        l2_latent (float): Amount of L2 regularization used to push latent weights towards 0.
        weight_initializer (optim.initializers.Initializer): Weights initialization scheme.
        latent_initializer (optim.initializers.Initializer): Latent factors initialization scheme.
        clip_gradient (float): Clips the absolute value of each gradient value.
        seed (int): Randomization seed used for reproducibility.

    Attributes:
        global_mean (stats.Mean): The target arithmetic mean.
        u_biases (collections.defaultdict): The user bias weights.
        i_biases (collections.defaultdict): The item bias weights.
        u_latents (collections.defaultdict): The user latent vectors randomly initialized.
        i_latents (collections.defaultdict): The item latent vectors randomly initialized.
        u_bias_optimizer (optim.Optimizer): The sequential optimizer used for updating the user bias
            weights.
        i_bias_optimizer (optim.Optimizer): The sequential optimizer used for updating the item bias
            weights.
        u_latent_optimizer (optim.Optimizer): The sequential optimizer used for updating the user
            latent weights.
        i_latent_optimizer (optim.Optimizer): The sequential optimizer used for updating the item
            latent weights.

    Example:

        >>> from creme import optim
        >>> from creme import reco

        >>> X_y = (
        ...     ({'user': 'Alice', 'item': 'Superman'}, 8),
        ...     ({'user': 'Alice', 'item': 'Terminator'}, 9),
        ...     ({'user': 'Alice', 'item': 'Star Wars'}, 8),
        ...     ({'user': 'Alice', 'item': 'Notting Hill'}, 2),
        ...     ({'user': 'Alice', 'item': 'Harry Potter'}, 5),
        ...     ({'user': 'Bob', 'item': 'Superman'}, 8),
        ...     ({'user': 'Bob', 'item': 'Terminator'}, 9),
        ...     ({'user': 'Bob', 'item': 'Star Wars'}, 8),
        ...     ({'user': 'Bob', 'item': 'Notting Hill'}, 2)
        ... )

        >>> model = reco.BiasedMF(
        ...     n_factors=10,
        ...     bias_optimizer=optim.SGD(0.025),
        ...     latent_optimizer=optim.SGD(0.025),
        ...     latent_initializer=optim.initializers.Normal(mu=0., sigma=0.1, seed=71)
        ... )

        >>> for x, y in X_y:
        ...     _ = model.fit_one(x, y)

        >>> model.predict_one({'user': 'Bob', 'item': 'Harry Potter'})
        6.489025

    Note:
        This model expects a dict input with a `user` and an `item` entries without any type
        constraint on their values (i.e. can be strings or numbers). Other entries are ignored.

    References:
        1. [Paterek, A., 2007, August. Improving regularized singular value decomposition for collaborative filtering. In Proceedings of KDD cup and workshop (Vol. 2007, pp. 5-8)](https://www.cs.uic.edu/~liub/KDD-cup-2007/proceedings/Regular-Paterek.pdf)
        2. [Matrix factorization techniques for recommender systems](https://datajobs.com/data-science-repo/Recommender-Systems-[Netflix].pdf)

    """

    def __init__(self, n_factors=10, bias_optimizer: optim.Optimizer = None,
                 latent_optimizer: optim.Optimizer = None, loss: optim.losses.Loss = None,
                 l2_bias=0., l2_latent=0.,
                 weight_initializer: optim.initializers.Initializer = None,
                 latent_initializer: optim.initializers.Initializer = None,
                 clip_gradient=1e12, seed: int = None):

        self.n_factors = n_factors
        self.u_bias_optimizer = optim.SGD() if bias_optimizer is None else copy.deepcopy(bias_optimizer)
        self.i_bias_optimizer = optim.SGD() if bias_optimizer is None else copy.deepcopy(bias_optimizer)
        self.u_latent_optimizer = optim.SGD() if latent_optimizer is None else copy.deepcopy(latent_optimizer)
        self.i_latent_optimizer = optim.SGD() if latent_optimizer is None else copy.deepcopy(latent_optimizer)
        self.loss = optim.losses.Squared() if loss is None else loss
        self.l2_bias = l2_bias
        self.l2_latent = l2_latent

        if weight_initializer is None:
            weight_initializer = optim.initializers.Zeros()
        self.weight_initializer = weight_initializer

        if latent_initializer is None:
            latent_initializer = optim.initializers.Normal(sigma=.1, seed=seed)
        self.latent_initializer = latent_initializer

        self.clip_gradient = clip_gradient
        self.seed = seed
        self.global_mean = stats.Mean()

        self.u_biases = collections.defaultdict(weight_initializer)
        self.i_biases = collections.defaultdict(weight_initializer)

        random_latents = functools.partial(
            self.latent_initializer,
            shape=self.n_factors
        )
        self.u_latents = collections.defaultdict(random_latents)
        self.i_latents = collections.defaultdict(random_latents)

    def _predict_one(self, user, item):

        # Initialize the prediction to the mean
        y_pred = self.global_mean.get()

        # Add the user bias
        y_pred += self.u_biases[user]

        # Add the item bias
        y_pred += self.i_biases[item]

        # Add the dot product of the user and the item latent vectors
        y_pred += np.dot(self.u_latents[user], self.i_latents[item])

        return y_pred

    def _fit_one(self, user, item, y):

        # Update the global mean
        self.global_mean.update(y)

        # Calculate the gradient of the loss with respect to the prediction
        g_loss = self.loss.gradient(y, self._predict_one(user, item))

        # Clamp the gradient to avoid numerical instability
        g_loss = utils.math.clamp(g_loss, minimum=-self.clip_gradient, maximum=self.clip_gradient)

        # Calculate weights gradients
        u_grad_bias = {user: g_loss + self.l2_bias * self.u_biases[user]}
        i_grad_bias = {item: g_loss + self.l2_bias * self.i_biases[item]}
        u_latent_grad = {user: g_loss * self.i_latents[item] + self.l2_latent * self.u_latents[user]}
        i_latent_grad = {item: g_loss * self.u_latents[user] + self.l2_latent * self.i_latents[item]}

        # Update weights
        self.u_biases = self.u_bias_optimizer.update_after_pred(self.u_biases, u_grad_bias)
        self.i_biases = self.i_bias_optimizer.update_after_pred(self.i_biases, i_grad_bias)
        self.u_latents = self.u_latent_optimizer.update_after_pred(self.u_latents, u_latent_grad)
        self.i_latents = self.i_latent_optimizer.update_after_pred(self.i_latents, i_latent_grad)

        return self
