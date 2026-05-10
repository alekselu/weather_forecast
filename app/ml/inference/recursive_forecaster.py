import pandas as pd


class RecursiveForecaster:
    def __init__(
        self,
        model,
        feature_builder,
        target_column,
    ):
        self.model = model
        self.feature_builder = feature_builder
        self.target_column = target_column

    def predict(self, history: pd.DataFrame, horizon: int):
        history = history.copy()
        predictions = []
        for _ in range(horizon):
            features_df = self.feature_builder.transform(history)
            latest_row = features_df.iloc[-1:]
            exclude = [
                "date",
                self.target_column,
            ]
            X = latest_row.drop(columns=exclude)
            pred = self.model.predict(X)[0]
            predictions.append(pred)
            next_row = history.iloc[-1:].copy()
            next_row["date"] = next_row["date"] + pd.Timedelta(days=1)
            next_row[self.target_column] = pred
            history = pd.concat(
                [history, next_row],
                ignore_index=True,
            )
        return predictions
