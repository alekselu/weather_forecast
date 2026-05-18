import pandas as pd
from abc import ABC, abstractmethod


class DatasetPreprocessor(ABC):
    @abstractmethod
    def transform(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> tuple[pd.DataFrame, pd.Series]:
        pass
