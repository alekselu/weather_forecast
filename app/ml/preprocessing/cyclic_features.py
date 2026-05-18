import numpy as np
import pandas as pd


class CyclicFeatureEncoder:
    @staticmethod
    def encode(
        df: pd.DataFrame,
        column: str,
        period: int,
    ) -> pd.DataFrame:

        values = df[column]

        df[f"{column}_sin"] = np.sin(2 * np.pi * values / period)

        df[f"{column}_cos"] = np.cos(2 * np.pi * values / period)

        return df
