import numpy as np
from sklearn.model_selection import BaseCrossValidator
from sklearn.utils.validation import indexable, _num_samples


class VaryingStepSeriesSplit(BaseCrossValidator):
    def __init__(
        self,
        horizon: int = 7,
        min_train_size: int = 365,
        step: int | str = "horizon",
        max_splits: int = 10,
    ):
        self.horizon = horizon
        self.min_train_size = min_train_size
        self.step = horizon if step == "horizon" else step
        self.max_splits = max_splits

    def get_n_splits(self, X=None, y=None, groups=None):
        if X is None:
            return self.max_splits if self.max_splits else 0
        n_samples = _num_samples(X)
        if n_samples < self.min_train_size + self.horizon:
            return 0
        total_available_splits = (
            n_samples - self.min_train_size - self.horizon
        ) // self.step + 1
        if self.max_splits is not None:
            return min(total_available_splits, self.max_splits)
        return total_available_splits

    def split(self, X, y=None, groups=None):
        X, y, groups = indexable(X, y, groups)
        n_samples = _num_samples(X)
        n_splits = self.get_n_splits(X, y, groups)
        if n_splits == 0:
            return
        total_available_splits = (
            n_samples - self.min_train_size - self.horizon
        ) // self.step + 1
        offset = total_available_splits - n_splits
        for i in range(n_splits):
            train_end = self.min_train_size + (offset + i) * self.step
            yield (np.arange(train_end), np.arange(train_end, train_end + self.horizon))
