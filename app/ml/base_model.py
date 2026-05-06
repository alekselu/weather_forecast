from abc import ABC, abstractmethod
from sklearn.base import BaseEstimator, RegressorMixin
import numpy as np


class BaseModel(ABC, BaseEstimator, RegressorMixin):
    @abstractmethod
    def update(self, X: np.ndarray, y: np.ndarray):
        """Incremental learning"""
        pass

    @abstractmethod
    def save(self, path: str):
        pass

    @abstractmethod
    def load(self, path: str):
        pass
