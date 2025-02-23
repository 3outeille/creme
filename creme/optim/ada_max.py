import collections

from . import base


__all__ = ['AdaMax']


class AdaMax(base.Optimizer):
    """AdaMax optimizer.

    Parameters:
        lr
        beta_1
        beta_2
        eps

    Attributes:
        m (collections.defaultdict)
        v (collections.defaultdict)

    Example:

        >>> from creme import datasets
        >>> from creme import linear_model
        >>> from creme import metrics
        >>> from creme import model_selection
        >>> from creme import optim
        >>> from creme import preprocessing

        >>> X_y = datasets.Phishing()
        >>> optimizer = optim.AdaMax()
        >>> model = (
        ...     preprocessing.StandardScaler() |
        ...     linear_model.LogisticRegression(optimizer)
        ... )
        >>> metric = metrics.F1()

        >>> model_selection.progressive_val_score(X_y, model, metric)
        F1: 0.876106

    References:
        1. [Kingma, D.P. and Ba, J., 2014. Adam: A method for stochastic optimization. arXiv preprint arXiv:1412.6980.](https://arxiv.org/pdf/1412.6980.pdf)
        2. [Ruder, S., 2016. An overview of gradient descent optimization algorithms. arXiv preprint arXiv:1609.04747.](http://ruder.io/optimizing-gradient-descent/index.html#adamax)

    """

    def __init__(self, lr=0.1, beta_1=0.9, beta_2=0.999, eps=1e-8):
        super().__init__(lr)
        self.beta_1 = beta_1
        self.beta_2 = beta_2
        self.eps = eps
        self.m = collections.defaultdict(float)
        self.u = collections.defaultdict(float)

    def _update_after_pred(self, w, g):

        # Correct bias for `m`
        learning_rate = self.learning_rate / (1 - self.beta_1 ** (self.n_iterations + 1))

        for i, gi in g.items():
            self.m[i] = self.beta_1 * self.m[i] + (1 - self.beta_1) * gi
            self.u[i] = max(self.beta_2 * self.u[i], abs(gi))
            w[i] -= learning_rate * self.m[i] / (self.u[i] + self.eps)

        return w
