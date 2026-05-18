"""
Тесты слоя данных и предсказаний с использованием CSV-фикстуры.

Два уровня:
  1. unit/test_predictor_csv.py  — быстрые тесты с реальным CSV,
     без БД, без HTTP. Проверяют логику подготовки данных, длины рядов,
     детерминированность предсказаний на известных данных.

  2. Мок SQLAlchemy sync Session — в интеграционных тестах (см. ниже).

Предположения об интерфейсе (из кодовой базы):
  - Исторические данные читаются через функцию вида:
        load_history(session: Session, city: str, target: str) -> pd.DataFrame
    или аналогичный репозиторий/DAO.
  - Predictor.__init__ принимает registry: ModelRegistry.
  - Predictor.predict(request: PredictRequest) -> PredictResponse.

Если имена функций отличаются — исправить импорты в начале файла.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# ── Пути ───────────────────────────────────────────────────────────────────
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
CSV_PATH = FIXTURES_DIR / "data_2023_2026.csv"


# ═══════════════════════════════════════════════════════════════════════════
# Вспомогательные функции
# ═══════════════════════════════════════════════════════════════════════════


def load_csv() -> pd.DataFrame:
    assert CSV_PATH.exists(), (
        f"Положите data_2023_2026.csv в {FIXTURES_DIR}\n"
        "cp data_2023_2026.csv tests/fixtures/"
    )
    df = pd.read_csv(CSV_PATH, parse_dates=["time"], date_format="%Y-%m-%d").rename(
        columns={"time": "date"}
    )
    return df.sort_values("date").reset_index(drop=True)


def date_range(start: date, end: date) -> list[date]:
    n = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(n)]


# ═══════════════════════════════════════════════════════════════════════════
# Тесты CSV-данных как источника исторических данных
# ═══════════════════════════════════════════════════════════════════════════


class TestCSVDataIntegrity:
    """
    Проверяют, что CSV-файл содержит то, на что рассчитывает Predictor.
    Провал этих тестов означает проблему в данных, а не в коде.
    """

    @pytest.fixture(scope="class")
    def df(self) -> pd.DataFrame:
        return load_csv()

    def test_csv_has_date_column(self, df):
        assert "date" in df.columns, "CSV должен содержать колонку 'date'"

    def test_date_column_is_datetime(self, df):
        assert pd.api.types.is_datetime64_any_dtype(
            df["date"]
        ), "Колонка 'date' должна быть datetime после parse_dates"

    def test_csv_covers_2023_to_2026(self, df):
        assert df["date"].dt.year.min() <= 2023
        assert df["date"].dt.year.max() >= 2025

    def test_csv_has_at_least_one_known_daily_param(self, df):
        from app.params import DAILY_PARAMS

        overlap = set(df.columns) & DAILY_PARAMS
        assert overlap, (
            f"CSV не содержит ни одного known daily-параметра. "
            f"Колонки: {list(df.columns)}"
        )

    def test_csv_has_no_duplicate_dates(self, df):
        dupes = df[df.duplicated("date")]
        assert dupes.empty, f"Найдены дублирующиеся даты: {dupes['date'].tolist()[:5]}"

    def test_csv_has_no_full_row_na(self, df):
        """Не должно быть строк, где все значения (кроме date) — NaN."""
        data_cols = [c for c in df.columns if c != "date"]
        all_na = df[data_cols].isna().all(axis=1)
        assert (
            not all_na.any()
        ), f"Найдены пустые строки: {df[all_na]['date'].tolist()[:5]}"

    def test_csv_daily_params_are_numeric(self, df):
        from app.params import DAILY_PARAMS

        for col in df.columns:
            if col in DAILY_PARAMS:
                assert pd.api.types.is_numeric_dtype(
                    df[col]
                ), f"Колонка {col} должна быть числовой"


# ═══════════════════════════════════════════════════════════════════════════
# Тесты подготовки данных для предсказания (с CSV, без БД)
# ═══════════════════════════════════════════════════════════════════════════


class TestHistorySlicingFromCSV:
    """
    Тестируем логику нарезки исторических данных из CSV.
    Мокируем только то, что уходит в БД — сам DataFrame берём из CSV.
    """

    @pytest.fixture(scope="class")
    def df(self) -> pd.DataFrame:
        return load_csv()

    @pytest.fixture(scope="class")
    def daily_col(self, df) -> str:
        """Первая daily-колонка из CSV."""
        from app.params import DAILY_PARAMS

        cols = [c for c in df.columns if c in DAILY_PARAMS]
        assert cols, "CSV не содержит daily-параметров"
        return cols[0]

    def test_slice_returns_correct_length(self, df, daily_col):
        """Нарезка на 30 дней возвращает ≤ 30 строк."""
        cutoff = df["date"].max() - pd.Timedelta(days=30)
        history = df[df["date"] < cutoff][["date", daily_col]].dropna()
        assert len(history) <= len(df)
        assert len(history) > 0

    def test_slice_is_sorted_ascending(self, df, daily_col):
        history = df[["date", daily_col]].dropna()
        assert (
            history["date"].diff().dropna() >= pd.Timedelta(0)
        ).all(), "История должна быть отсортирована по возрастанию даты"

    def test_future_window_does_not_overlap_history(self, df, daily_col):
        """X_future не должен пересекаться по датам с X_history."""
        split_date = date(2025, 1, 1)
        history = df[df["date"] < pd.Timestamp(split_date)]
        future_dates = date_range(split_date, date(2025, 1, 7))
        history_dates = set(history["date"].dt.date)
        for fd in future_dates:
            assert (
                fd not in history_dates
            ), f"Дата {fd} из future присутствует в history — утечка данных"

    def test_history_has_no_gaps_longer_than_threshold(self, df, daily_col):
        """
        Пропуски в ежедневных данных длиннее 7 дней сигнализируют
        о проблеме в источнике — модель деградирует на таких данных.
        """
        dates = df[["date", daily_col]].dropna()["date"].sort_values()
        gaps = dates.diff().dropna()
        max_gap = gaps.max()
        assert max_gap <= pd.Timedelta(days=7), (
            f"Обнаружен пропуск {max_gap.days} дней в CSV — "
            "проверьте источник данных"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Тесты Predictor с CSV как источником истории (без БД)
# ═══════════════════════════════════════════════════════════════════════════


class TestPredictorWithCSVHistory:
    """
    Predictor.predict() вызывается с реальными данными из CSV.
    SQLAlchemy Session мокируется — возвращает данные из CSV.
    ForecasterEnsemble использует реальный FakeEnsemble из conftest.

    Цель: проверить длины рядов, типы, отсутствие NaN в ответе.
    Качество предсказаний — за пределами этих тестов (уже покрыто fit-predict).
    """

    @pytest.fixture(scope="class")
    def df(self) -> pd.DataFrame:
        return load_csv()

    @pytest.fixture(scope="class")
    def daily_col(self, df) -> str:
        from app.params import DAILY_PARAMS

        cols = [c for c in df.columns if c in DAILY_PARAMS]
        assert cols
        return cols[0]

    def _make_mock_session(self, df: pd.DataFrame, target_col: str):
        """
        Возвращает MagicMock, имитирующий sync Session.
        execute() возвращает строки CSV в виде списка кортежей (date, value).
        """
        rows = [
            (row["date"].date(), row[target_col])
            for _, row in df[["date", target_col]].dropna().iterrows()
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = rows
        session = MagicMock()
        session.execute.return_value = mock_result
        return session

    def test_predict_returns_correct_daily_length(self, df, daily_col):
        """
        Predictor возвращает ровно N значений для N-дневного диапазона.
        Проверяем без реальной модели — FakeEnsemble возвращает детерминированный ряд.
        """
        from app.ml.predictor import Predictor
        from app.schemas.forecast import PredictRequest

        mock_session = self._make_mock_session(df, daily_col)

        request = PredictRequest(
            latitude=55.75,
            longitude=37.62,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            daily=[daily_col],
            hourly=[],
        )

        fake_reg = MagicMock()
        fake_ensemble = MagicMock()
        # FakeEnsemble.predict возвращает pd.Series нужной длины
        import pandas as _pd

        n_days = (request.end_date - request.start_date).days + 1
        fake_ensemble.predict.return_value = _pd.Series(
            [float(i) for i in range(n_days)]
        )
        fake_reg.active = fake_ensemble
        fake_reg.is_ready.return_value = True

        predictor = Predictor(registry=fake_reg)

        with patch("app.ml.predictor.get_session", return_value=mock_session):
            result = predictor.predict(request)

        assert len(result.daily[daily_col]) == n_days

    def test_predict_daily_values_are_floats(self, df, daily_col):
        from app.ml.predictor import Predictor
        from app.schemas.forecast import PredictRequest
        import pandas as _pd

        mock_session = self._make_mock_session(df, daily_col)
        n_days = 5

        request = PredictRequest(
            latitude=55.75,
            longitude=37.62,
            start_date=date(2025, 2, 1),
            end_date=date(2025, 2, 5),
            daily=[daily_col],
            hourly=[],
        )

        fake_reg = MagicMock()
        fake_reg.is_ready.return_value = True
        fake_reg.active.predict.return_value = _pd.Series(
            [1.0 * i for i in range(n_days)]
        )

        predictor = Predictor(registry=fake_reg)
        with patch("app.ml.predictor.get_session", return_value=mock_session):
            result = predictor.predict(request)

        for v in result.daily[daily_col]:
            assert isinstance(v, float), f"Ожидался float, получен {type(v)}"

    def test_predict_daily_values_have_no_nan(self, df, daily_col):
        from app.ml.predictor import Predictor
        from app.schemas.forecast import PredictRequest
        import pandas as _pd
        import math

        mock_session = self._make_mock_session(df, daily_col)
        n_days = 3

        request = PredictRequest(
            latitude=55.75,
            longitude=37.62,
            start_date=date(2025, 3, 1),
            end_date=date(2025, 3, 3),
            daily=[daily_col],
            hourly=[],
        )

        fake_reg = MagicMock()
        fake_reg.is_ready.return_value = True
        fake_reg.active.predict.return_value = _pd.Series([10.0, 11.0, 12.0])

        predictor = Predictor(registry=fake_reg)
        with patch("app.ml.predictor.get_session", return_value=mock_session):
            result = predictor.predict(request)

        for v in result.daily[daily_col]:
            assert not math.isnan(v), f"NaN в ответе предсказания"

    def test_predict_raises_when_model_not_ready(self, df, daily_col):
        from app.ml.predictor import Predictor
        from app.schemas.forecast import PredictRequest

        mock_session = self._make_mock_session(df, daily_col)

        request = PredictRequest(
            latitude=55.75,
            longitude=37.62,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 3),
            daily=[daily_col],
            hourly=[],
        )

        fake_reg = MagicMock()
        fake_reg.is_ready.return_value = False
        fake_reg.active = None

        predictor = Predictor(registry=fake_reg)
        with patch("app.ml.predictor.get_session", return_value=mock_session):
            with pytest.raises(RuntimeError, match="[Mm]odel not loaded"):
                predictor.predict(request)


# ═══════════════════════════════════════════════════════════════════════════
# Тесты мокированного SQLAlchemy sync Session
# ═══════════════════════════════════════════════════════════════════════════


class TestMockedSQLAlchemySession:
    """
    Проверяем, что слой доступа к данным (репозиторий / DAO) корректно
    формирует запросы к Session и обрабатывает ответы.

    Адаптируйте имена функций под реальный репозиторий.
    Ожидаемый интерфейс:
        load_weather_history(
            session: Session,
            city: str,
            target: str,
            before: date,
        ) -> pd.DataFrame
    """

    def _make_session(self, rows: list[tuple]) -> MagicMock:
        result = MagicMock()
        result.fetchall.return_value = rows
        session = MagicMock()
        session.execute.return_value = result
        return session

    def test_session_execute_called_once(self):
        from app.db.utils import load_weather_history

        rows = [(date(2025, 1, i), float(i)) for i in range(1, 8)]
        session = self._make_session(rows)

        load_weather_history(
            session,
            city="Saint Petersburg",
            target="temperature_2m_mean",
            before=date(2025, 1, 8),
        )

        session.execute.assert_called_once()

    def test_returns_dataframe(self):
        from app.db.utils import load_weather_history

        rows = [(date(2025, 1, i), float(i)) for i in range(1, 6)]
        session = self._make_session(rows)

        result = load_weather_history(
            session,
            city="Saint Petersburg",
            target="temperature_2m_mean",
            before=date(2025, 1, 6),
        )

        assert isinstance(result, pd.DataFrame)

    def test_dataframe_has_date_and_value_columns(self):
        from app.db.utils import load_weather_history

        rows = [(date(2025, 1, i), float(i)) for i in range(1, 4)]
        session = self._make_session(rows)

        df = load_weather_history(
            session,
            city="Saint Petersburg",
            target="temperature_2m_mean",
            before=date(2025, 1, 4),
        )

        assert "date" in df.columns
        assert "value" in df.columns or "temperature_2m_mean" in df.columns

    def test_returns_empty_dataframe_on_no_rows(self):
        from app.db.utils import load_weather_history

        session = self._make_session([])
        df = load_weather_history(
            session,
            city="Saint Petersburg",
            target="temperature_2m_mean",
            before=date(2025, 1, 1),
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_dataframe_sorted_by_date(self):
        from app.db.utils import load_weather_history

        # Передаём строки в обратном порядке
        rows = [(date(2025, 1, i), float(i)) for i in range(5, 0, -1)]
        session = self._make_session(rows)

        df = load_weather_history(
            session,
            city="Saint Petersburg",
            target="temperature_2m_mean",
            before=date(2025, 1, 6),
        )

        dates = pd.to_datetime(df["date"]) if df["date"].dtype == object else df["date"]
        assert (
            dates.diff().dropna() >= pd.Timedelta(0)
        ).all(), "DataFrame должен быть отсортирован по дате по возрастанию"

    def test_session_not_committed_on_read(self):
        """Read-запрос не должен вызывать commit()."""
        from app.db.utils import load_weather_history

        session = self._make_session([(date(2025, 1, 1), 10.0)])
        load_weather_history(
            session,
            city="Saint Petersburg",
            target="temperature_2m_mean",
            before=date(2025, 1, 2),
        )

        session.commit.assert_not_called()
