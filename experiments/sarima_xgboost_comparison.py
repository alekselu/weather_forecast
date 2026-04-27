import pandas as pd
import numpy as np
import random
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor
import statsmodels.api as sm


def set_seed(seed: int = 42):
    random.seed(42)
    np.random.seed(42)


def create_features(df):
    df = df.copy()
    df["target"] = df["temperature_mean"].shift(-1)
    for lag in [1, 2, 3, 7, 14, 30]:
        df[f"lag_{lag}"] = df["temperature_mean"].shift(lag)
    for w in [3, 7, 14]:
        df[f"roll_mean_{w}"] = df["temperature_mean"].shift(1).rolling(w).mean()
    df["diff_1"] = df["temperature_mean"].diff(1)
    df["day_of_year"] = df.index.dayofyear
    df["month"] = df.index.month
    df["weekday"] = df.index.weekday
    df = df.dropna()
    X = df.drop(columns=["target"])
    y = df["target"]
    return X, y


def metrics(y_true, y_pred):
    return {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
        "R2": r2_score(y_true, y_pred),
    }


def train_xgb(X, y):
    tscv = TimeSeriesSplit(n_splits=5)
    scores = []
    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        model = XGBRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
        )
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        scores.append(metrics(y_test, preds))
    return pd.DataFrame(scores).mean()


def train_sarima(series):
    tscv = TimeSeriesSplit(n_splits=5)
    scores = []
    for train_idx, test_idx in tscv.split(series):
        train, test = series.iloc[train_idx], series.iloc[test_idx]
        model = sm.tsa.statespace.SARIMAX(
            train,
            order=(2, 1, 2),
            seasonal_order=(1, 1, 1, 365),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        res = model.fit(disp=False)
        preds = res.forecast(len(test))
        scores.append(metrics(test, preds))
    return pd.DataFrame(scores).mean()


def main():
    set_seed(42)

    df = pd.read_csv("data.csv", parse_dates=["date"])
    df = df.sort_values("date")
    df = df.set_index("date")

    if "temperature_mean" not in df.columns:
        raise ValueError("No column temperature_mean")

    print(f"Dataset size: {df.shape}")
    X, y = create_features(df)
    print(f"After feature engineering: {X.shape}")

    print("\nTraining XGBoost...")
    xgb_scores = train_xgb(X, y)
    print("XGBoost metrics:")
    print(xgb_scores)

    print("\nTraining SARIMA...")
    sarima_scores = train_sarima(df["temperature_mean"])
    print("SARIMA metrics:")
    print(sarima_scores)

    print("\n=== FINAL COMPARISON ===")
    results = pd.DataFrame({"XGBoost": xgb_scores, "SARIMA": sarima_scores})
    print(results)


if __name__ == "__main__":
    main()
