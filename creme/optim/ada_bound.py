import math
import numbers
import collections

from .. import utils

from . import base


__all__ = ['AdaBound']


class AdaBound(base.Optimizer):
    """AdaBound optimizer.

    Parameters:
        lr: The learning rate.
        beta_1
        beta_2
        eps
        gamma
        final_lr

    Attributes:
        m (collections.defaultdict)
        s (collections.defaultdict)

    Example:

        >>> from creme import datasets
        >>> from creme import linear_model
        >>> from creme import metrics
        >>> from creme import model_selection
        >>> from creme import optim
        >>> from creme import preprocessing

        >>> X_y = datasets.Phishing()
        >>> optimizer = optim.AdaBound()
        >>> model = (
        ...     preprocessing.StandardScaler() |
        ...     linear_model.LogisticRegression(optimizer)
        ... )
        >>> metric = metrics.F1()

        >>> model_selection.progressive_val_score(X_y, model, metric)
        F1: 0.879004

    References:
        1. [Luo, L., Xiong, Y., Liu, Y. and Sun, X., 2019. Adaptive gradient methods with dynamic bound of learning rate. arXiv preprint arXiv:1902.09843](https://arxiv.org/abs/1902.09843)

    """

    def __init__(self, lr=1e-3, beta_1=0.9, beta_2=0.999, eps=1e-8, gamma=1e-3, final_lr=0.1):

        if not isinstance(lr, numbers.Number):
            raise ValueError(
                f'lr in AdaBound should be numeric but got {type(lr)}')

        if not isinstance(final_lr, numbers.Number):
            raise ValueError(
                f'final_lr in AdaBound should be numeric but got {type(final_lr)}')

        super().__init__(lr)
        self.base_lr = lr
        self.final_lr = final_lr
        self.beta_1 = beta_1
        self.beta_2 = beta_2
        self.eps = eps
        self.gamma = gamma
        self.m = collections.defaultdict(float)
        self.v = collections.defaultdict(float)

    def _update_after_pred(self, w, g):

        bias_1 = 1 - self.beta_1 ** (self.n_iterations + 1)
        bias_2 = 1 - self.beta_2 ** (self.n_iterations + 1)

        step_size = self.learning_rate * math.sqrt(bias_2) / bias_1
        self.final_lr *= self.learning_rate / self.base_lr

        lower_bound = self.final_lr * (1 - 1 / (self.gamma * (self.n_iterations + 1) + 1))
        upper_bound = self.final_lr * (1 + 1 / (self.gamma * (self.n_iterations + 1)))

        for i, gi in g.items():
            self.m[i] = self.beta_1 * self.m[i] + (1 - self.beta_1) * gi
            self.v[i] = self.beta_2 * self.v[i] + (1 - self.beta_2) * gi ** 2

            step_size_bound = step_size / (math.sqrt(self.v[i]) + self.eps)

            w[i] -= utils.math.clamp(step_size_bound, lower_bound, upper_bound) * self.m[i]

        return w
