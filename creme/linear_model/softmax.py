import collections
import copy
import functools

from .. import base
from .. import optim
from .. import utils


__all__ = ['SoftmaxRegression']


class SoftmaxRegression(base.MultiClassifier):
    """Softmax regression is a generalization of logistic regression to multiple classes.

    Softmax regression is also known as "multinomial logistic regression". There are a set weights
    for each class, hence the `weights` attribute is a nested `collections.defaultdict`. The main
    advantage of using this instead of a one-vs-all logistic regression is that the probabilities
    will be calibrated. Moreover softmax regression is more robust to outliers.

    Parameters:
        optimizer: The sequential optimizer used to tune the weights.
        loss: The loss function to optimize for.
        l2: Amount of L2 regularization used to push weights towards 0.

    Attributes:
        weights (collections.defaultdict)

    Example:

        >>> from creme import datasets
        >>> from creme import linear_model
        >>> from creme import metrics
        >>> from creme import model_selection
        >>> from creme import optim
        >>> from creme import preprocessing

        >>> X_y = datasets.ImageSegments()

        >>> model = preprocessing.StandardScaler()
        >>> model |= linear_model.SoftmaxRegression()

        >>> metric = metrics.MacroF1()

        >>> model_selection.progressive_val_score(X_y, model, metric)
        MacroF1: 0.818653

    References:
        1. [Course on classification stochastic gradient descent](https://www.inf.ed.ac.uk/teaching/courses/mlp/2016/mlp02-sln.pdf)
        2. [Binary vs. Multi-Class Logistic Regression](https://chrisyeh96.github.io/2018/06/11/logistic-regression.html)

    """

    def __init__(self, optimizer: optim.Optimizer = None, loss: optim.losses.MultiClassLoss = None,
                 l2=0):
        self.optimizers = collections.defaultdict(functools.partial(
            copy.deepcopy,
            optim.SGD(0.01) if optimizer is None else optimizer
        ))
        self.loss = optim.losses.CrossEntropy() if loss is None else loss
        self.l2 = l2
        self.weights = collections.defaultdict(functools.partial(collections.defaultdict, float))

    def fit_one(self, x, y):

        # Some optimizers need to do something before a prediction is made
        for label, weights in self.weights.items():
            self.optimizers[label].update_before_pred(w=weights)

        # Make a prediction for the given features
        y_pred = self.predict_proba_one(x)

        # Compute the gradient of the loss w.r.t. each label
        loss_gradients = self.loss.gradient(y_true=y, y_pred=y_pred)

        for label, loss in loss_gradients.items():

            # Compute the gradient w.r.t. each feature
            weights = self.weights[label]
            gradient = {i: xi * loss + self.l2 * weights.get(i, 0) for i, xi in x.items()}
            self.weights[label] = self.optimizers[label].update_after_pred(w=weights, g=gradient)

        return self

    def predict_proba_one(self, x):
        return utils.math.softmax({
            label: utils.math.dot(weights, x)
            for label, weights in self.weights.items()
        })
