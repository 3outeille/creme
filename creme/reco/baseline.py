import collections
import copy

from creme import stats
from creme import optim
from creme import utils

from . import base


__all__ = ['Baseline']


class Baseline(base.Recommender):
    """Baseline for recommender systems.

    A first-order approximation of the bias involved in target. The model equation is defined as:

    $$\\hat{y}(x) = \\bar{y} + bu_{u} + bi_{i}$$

    Where :math:`bu_{u}` and :math:`bi_{i}` are respectively the user and item biases. The model
    expect dict inputs containing both a `user` and an `item` entries.

    Parameters:
        optimizer: The sequential optimizer used for updating the weights.
        loss: The loss function to optimize for.
        l2: regularization amount used to push weights towards 0.
        initializer: Weights initialization scheme.
        clip_gradient: Clips the absolute value of each gradient value.

    Attributes:
        global_mean (stats.Mean): The target arithmetic mean.
        u_biases (collections.defaultdict): The user bias weights.
        i_biases (collections.defaultdict): The item bias weights.
        u_optimizer (optim.Optimizer): The sequential optimizer used for updating the user bias
            weights.
        i_optimizer (optim.Optimizer): The sequential optimizer used for updating the item bias
            weights.

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

        >>> model = reco.Baseline(optimizer=optim.SGD(0.005))

        >>> for x, y in X_y:
        ...     _ = model.fit_one(x, y)

        >>> model.predict_one({'user': 'Bob', 'item': 'Harry Potter'})
        6.538120

    Note:
        This model expects a dict input with a `user` and an `item` entries without any
        type constraint on their values (i.e. can be strings or numbers). Other entries are ignored.

    References:
        1. [Matrix factorization techniques for recommender systems](https://datajobs.com/data-science-repo/Recommender-Systems-[Netflix].pdf)

    """

    def __init__(self, optimizer: optim.Optimizer = None, loss: optim.losses.Loss = None,
                 l2=0., initializer: optim.initializers.Initializer = None, clip_gradient=1e12):
        self.optimizer = optim.SGD() if optimizer is None else copy.deepcopy(optimizer)
        self.u_optimizer = optim.SGD() if optimizer is None else copy.deepcopy(optimizer)
        self.i_optimizer = optim.SGD() if optimizer is None else copy.deepcopy(optimizer)
        self.loss = optim.losses.Squared() if loss is None else loss
        self.l2 = l2

        if initializer is None:
            initializer = optim.initializers.Zeros()
        self.initializer = initializer

        self.clip_gradient = clip_gradient
        self.global_mean = stats.Mean()
        self.u_biases = collections.defaultdict(initializer)
        self.i_biases = collections.defaultdict(initializer)

    def _predict_one(self, user, item):
        return self.global_mean.get() + self.u_biases[user] + self.i_biases[item]

    def _fit_one(self, user, item, y):

        # Update the global mean
        self.global_mean.update(y)

        # Calculate the gradient of the loss with respect to the prediction
        g_loss = self.loss.gradient(y, self._predict_one(user, item))

        # Clamp the gradient to avoid numerical instability
        g_loss = utils.math.clamp(g_loss, minimum=-self.clip_gradient, maximum=self.clip_gradient)

        # Calculate bias gradients
        u_grad_bias = {user: g_loss + self.l2 * self.u_biases[user]}
        i_grad_bias = {item: g_loss + self.l2 * self.i_biases[item]}

        # Update biases
        self.u_biases = self.u_optimizer.update_after_pred(self.u_biases, u_grad_bias)
        self.i_biases = self.i_optimizer.update_after_pred(self.i_biases, i_grad_bias)

        return self
