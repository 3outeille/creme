import collections
import copy
import statistics

import numpy as np

from .. import base


__all__ = ['BaggingClassifier', 'BaggingRegressor']


class BaseBagging(base.Wrapper, base.Ensemble):

    def __init__(self, model, n_models=10, seed=None):
        super().__init__(copy.deepcopy(model) for _ in range(n_models))
        self.n_models = n_models
        self.model = model
        self.seed = seed
        self._rng = np.random.RandomState(seed)

    @property
    def _model(self):
        return self.model

    def fit_one(self, x, y):

        for model in self:
            for _ in range(self._rng.poisson(1)):
                model.fit_one(x, y)

        return self


class BaggingClassifier(BaseBagging, base.Classifier):
    """Online bootstrap aggregation for classification.

    For each incoming observation, each model's `fit_one` method is called `k` times where
    `k` is sampled from a Poisson distribution of parameter 1. `k` thus has a 36% chance of
    being equal to 0, a 36% chance of being equal to 1, an 18% chance of being equal to 2, a 6%
    chance of being equal to 3, a 1% chance of being equal to 4, etc. You can do
    `scipy.stats.poisson(1).pmf(k)` to obtain more detailed values.

    Parameters:
        model: The classifier to bag.
        n_models: The number of models in the ensemble.
        seed: Random number generator seed for reproducibility.

    Example:

        In the following example three logistic regressions are bagged together. The performance is
        slightly better than when using a single logistic regression.

        >>> from creme import datasets
        >>> from creme import ensemble
        >>> from creme import linear_model
        >>> from creme import metrics
        >>> from creme import model_selection
        >>> from creme import optim
        >>> from creme import preprocessing

        >>> X_y = datasets.Phishing()
        >>> model = ensemble.BaggingClassifier(
        ...     model=(
        ...         preprocessing.StandardScaler() |
        ...         linear_model.LogisticRegression()
        ...     ),
        ...     n_models=3,
        ...     seed=42
        ... )
        >>> metric = metrics.F1()

        >>> model_selection.progressive_val_score(X_y, model, metric)
        F1: 0.878788

        >>> print(model)
        BaggingClassifier(StandardScaler | LogisticRegression)

    References:
        1. [Oza, N.C., 2005, October. Online bagging and boosting. In 2005 IEEE international conference on systems, man and cybernetics (Vol. 3, pp. 2340-2345). Ieee.](https://ti.arc.nasa.gov/m/profile/oza/files/ozru01a.pdf)

    """

    def __init__(self, model: base.Classifier, n_models=10, seed: int = None):
        super().__init__(model, n_models, seed)

    def predict_proba_one(self, x):
        """Averages the predictions of each classifier."""

        y_pred = collections.Counter()
        for classifier in self:
            y_pred.update(classifier.predict_proba_one(x))

        total = sum(y_pred.values())
        if total > 0:
            return {label: proba / total for label, proba in y_pred.items()}
        return y_pred


class BaggingRegressor(BaseBagging, base.Regressor):
    """Online bootstrap aggregation for regression.

    For each incoming observation, each model's `fit_one` method is called `k` times where
    `k` is sampled from a Poisson distribution of parameter 1. `k` thus has a 36% chance of
    being equal to 0, a 36% chance of being equal to 1, an 18% chance of being equal to 2, a 6%
    chance of being equal to 3, a 1% chance of being equal to 4, etc. You can do
    `scipy.stats.poisson(1).pmf(k)` for more detailed values.

    Parameters:
        model: The regressor to bag.
        n_models: The number of models in the ensemble.
        seed: Random number generator seed for reproducibility.

    Example:

        In the following example three logistic regressions are bagged together. The performance is
        slightly better than when using a single logistic regression.

        >>> from creme import datasets
        >>> from creme import ensemble
        >>> from creme import linear_model
        >>> from creme import metrics
        >>> from creme import model_selection
        >>> from creme import optim
        >>> from creme import preprocessing

        >>> X_y = datasets.TrumpApproval()
        >>> model = preprocessing.StandardScaler()
        >>> model |= ensemble.BaggingRegressor(
        ...     model=linear_model.LinearRegression(intercept_lr=0.1),
        ...     n_models=3,
        ...     seed=42
        ... )
        >>> metric = metrics.MAE()

        >>> model_selection.progressive_val_score(X_y, model, metric)
        MAE: 0.71322

    References:
        1. [Oza, N.C., 2005, October. Online bagging and boosting. In 2005 IEEE international conference on systems, man and cybernetics (Vol. 3, pp. 2340-2345). Ieee.](https://ti.arc.nasa.gov/m/profile/oza/files/ozru01a.pdf)

    """

    def __init__(self, model: base.Regressor, n_models=10, seed: int = None):
        super().__init__(model, n_models, seed)

    def predict_one(self, x):
        """Averages the predictions of each regressor."""
        return statistics.mean((regressor.predict_one(x) for regressor in self))
