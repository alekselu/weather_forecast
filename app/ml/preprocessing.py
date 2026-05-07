from statsmodels.tsa.deterministic import DeterministicProcess
from sklearn.base import BaseEstimator, TransformerMixin
import numpy as np


class FourierHarmonicsTransformer(BaseEstimator, TransformerMixin):
    def fit_transform(self, X, y, **fit_params):
        fourier = DeterministicProcess(
            y, constant=True, period=365.25, fourier=5
        ).in_sample()
        return np.hstack((X, fourier))


class LagFeaturesTransformer(BaseEstimator, TransformerMixin):
    def fit_transform(self, X, y=None, **fit_params):
        return super().fit_transform(X, y, **fit_params)
