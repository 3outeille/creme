import collections

from . import base


__all__ = ['Momentum']


class Momentum(base.Optimizer):
    """Momentum optimizer.

    Parameters:
        lr
        rho

    Example:

        >>> from creme import datasets
        >>> from creme import linear_model
        >>> from creme import metrics
        >>> from creme import model_selection
        >>> from creme import optim
        >>> from creme import preprocessing

        >>> X_y = datasets.Phishing()
        >>> optimizer = optim.Momentum()
        >>> model = (
        ...     preprocessing.StandardScaler() |
        ...     linear_model.LogisticRegression(optimizer)
        ... )
        >>> metric = metrics.F1()

        >>> model_selection.progressive_val_score(X_y, model, metric)
        F1: 0.841645

    """

    def __init__(self, lr=.1, rho=.9):
        super().__init__(lr)
        self.rho = rho
        self.s = collections.defaultdict(float)

    def _update_after_pred(self, w, g):

        for i, gi in g.items():
            self.s[i] = self.rho * self.s[i] + self.learning_rate * gi
            w[i] -= self.s[i]

        return w
