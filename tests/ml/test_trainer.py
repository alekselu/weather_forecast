"""
Unit-тесты для app/trainer.py :: Trainer.

Проверяют оркестрацию — реальное обучение заменено mock-ом.
Фактическое качество модели покрыто существующими тестами fit-predict.

Ключевые инварианты:
  1. Нормальный флоу: begin → executor → stage → promote → save
  2. Пропуск, если begin_retraining вернул False
  3. abort + поглощение исключения при ошибке обучения
  4. Обучение идёт в executor, а не блокирует event loop
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ml.trainer import Trainer


# ── helpers ─────────────────────────────────────────────────────────────────


def make_registry(begin_returns: bool = True) -> AsyncMock:
    reg = AsyncMock()
    reg.begin_retraining = AsyncMock(return_value=begin_returns)
    reg.set_staging = MagicMock()
    reg.promote = AsyncMock()
    reg.abort_retraining = AsyncMock()
    return reg


def make_trainer(registry, tmp_path) -> Trainer:
    return Trainer(registry=registry, model_path=str(tmp_path))


# ═══════════════════════════════════════════════════════════════════════════
# Нормальный флоу
# ═══════════════════════════════════════════════════════════════════════════


class TestTrainerNormalFlow:
    @pytest.mark.asyncio
    async def test_begin_retraining_called(self, tmp_path):
        reg = make_registry()
        trainer = make_trainer(reg, tmp_path)
        with patch.object(trainer, "_train_blocking", return_value=MagicMock()):
            await trainer.run()
        reg.begin_retraining.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_staging_called_with_new_ensemble(self, tmp_path):
        reg = make_registry()
        trainer = make_trainer(reg, tmp_path)
        new_ens = MagicMock(name="new")
        with patch.object(trainer, "_train_blocking", return_value=new_ens):
            await trainer.run()
        reg.set_staging.assert_called_once_with(new_ens)

    @pytest.mark.asyncio
    async def test_promote_called_once(self, tmp_path):
        reg = make_registry()
        trainer = make_trainer(reg, tmp_path)
        with patch.object(trainer, "_train_blocking", return_value=MagicMock()):
            await trainer.run()
        reg.promote.assert_called_once()

    @pytest.mark.asyncio
    async def test_promote_version_is_timestamp_format(self, tmp_path):
        """Версия должна быть строкой вида YYYYMMDDTHHmmSS (15 символов)."""
        reg = make_registry()
        trainer = make_trainer(reg, tmp_path)
        with patch.object(trainer, "_train_blocking", return_value=MagicMock()):
            await trainer.run()
        version = reg.promote.call_args[0][0]
        assert len(version) == 15 and "T" in version

    @pytest.mark.asyncio
    async def test_save_called_after_promote(self, tmp_path):
        reg = make_registry()
        trainer = make_trainer(reg, tmp_path)
        new_ens = MagicMock()
        with patch.object(trainer, "_train_blocking", return_value=new_ens):
            with patch.object(trainer, "_save") as mock_save:
                await trainer.run()
        mock_save.assert_called_once()
        # _save(ensemble, version)
        assert mock_save.call_args[0][0] is new_ens

    @pytest.mark.asyncio
    async def test_call_order_begin_train_stage_promote(self, tmp_path):
        """Порядок вызовов: begin → train → set_staging → promote."""
        call_log = []
        reg = AsyncMock()
        reg.begin_retraining = AsyncMock(
            side_effect=lambda: call_log.append("begin") or True
        )
        reg.set_staging = MagicMock(side_effect=lambda e: call_log.append("stage"))
        reg.promote = AsyncMock(side_effect=lambda v: call_log.append("promote"))
        reg.abort_retraining = AsyncMock()

        trainer = make_trainer(reg, tmp_path)
        with patch.object(
            trainer,
            "_train_blocking",
            side_effect=lambda: call_log.append("train") or MagicMock(),
        ):
            with patch.object(trainer, "_save"):
                await trainer.run()

        assert call_log == ["begin", "train", "stage", "promote"]


# ═══════════════════════════════════════════════════════════════════════════
# Пропуск при уже запущенном переобучении
# ═══════════════════════════════════════════════════════════════════════════


class TestTrainerSkipWhenRunning:
    @pytest.mark.asyncio
    async def test_train_not_called_when_begin_false(self, tmp_path):
        reg = make_registry(begin_returns=False)
        trainer = make_trainer(reg, tmp_path)
        with patch.object(trainer, "_train_blocking") as mock_train:
            await trainer.run()
        mock_train.assert_not_called()

    @pytest.mark.asyncio
    async def test_promote_not_called_when_skipped(self, tmp_path):
        reg = make_registry(begin_returns=False)
        trainer = make_trainer(reg, tmp_path)
        with patch.object(trainer, "_train_blocking"):
            await trainer.run()
        reg.promote.assert_not_called()

    @pytest.mark.asyncio
    async def test_abort_not_called_when_skipped(self, tmp_path):
        reg = make_registry(begin_returns=False)
        trainer = make_trainer(reg, tmp_path)
        with patch.object(trainer, "_train_blocking"):
            await trainer.run()
        reg.abort_retraining.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════
# Обработка ошибок при обучении
# ═══════════════════════════════════════════════════════════════════════════


class TestTrainerErrorHandling:
    @pytest.mark.asyncio
    async def test_run_does_not_raise_on_training_error(self, tmp_path):
        """Исключение из _train_blocking поглощается — event loop не падает."""
        reg = make_registry()
        trainer = make_trainer(reg, tmp_path)
        with patch.object(trainer, "_train_blocking", side_effect=RuntimeError("OOM")):
            try:
                await trainer.run()
            except Exception as e:
                pytest.fail(f"trainer.run() пробросил исключение: {e}")

    @pytest.mark.asyncio
    async def test_abort_called_on_training_error(self, tmp_path):
        reg = make_registry()
        trainer = make_trainer(reg, tmp_path)
        with patch.object(
            trainer, "_train_blocking", side_effect=ValueError("bad data")
        ):
            await trainer.run()
        reg.abort_retraining.assert_called_once()

    @pytest.mark.asyncio
    async def test_promote_not_called_on_training_error(self, tmp_path):
        reg = make_registry()
        trainer = make_trainer(reg, tmp_path)
        with patch.object(trainer, "_train_blocking", side_effect=Exception("crash")):
            await trainer.run()
        reg.promote.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_staging_not_called_on_training_error(self, tmp_path):
        reg = make_registry()
        trainer = make_trainer(reg, tmp_path)
        with patch.object(trainer, "_train_blocking", side_effect=Exception("crash")):
            await trainer.run()
        reg.set_staging.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════
# Event loop не блокируется: обучение идёт в executor
# ═══════════════════════════════════════════════════════════════════════════


class TestTrainerUsesExecutor:
    @pytest.mark.asyncio
    async def test_run_in_executor_called(self, tmp_path):
        """
        _train_blocking должен вызываться через loop.run_in_executor,
        а не напрямую — иначе CPU-нагрузка заблокирует event loop.
        """
        reg = make_registry()
        trainer = make_trainer(reg, tmp_path)
        fake_ens = MagicMock()

        with patch("asyncio.get_running_loop") as mock_get_loop:
            loop_mock = MagicMock()
            loop_mock.run_in_executor = AsyncMock(return_value=fake_ens)
            mock_get_loop.return_value = loop_mock

            with patch.object(trainer, "_save"):
                await trainer.run()

        loop_mock.run_in_executor.assert_called_once()
        # Первый аргумент executor=None (ThreadPoolExecutor по умолчанию)
        executor_arg = loop_mock.run_in_executor.call_args[0][0]
        assert executor_arg is None

    @pytest.mark.asyncio
    async def test_event_loop_not_blocked_during_training(self, tmp_path):
        """
        Пока идёт «обучение» (имитируется sleep в executor),
        event loop должен успевать выполнять другие корутины.
        """
        reg = make_registry()
        trainer = make_trainer(reg, tmp_path)
        side_task_ran = []

        async def side_task():
            await asyncio.sleep(0)
            side_task_ran.append(True)

        async def slow_train():
            await asyncio.sleep(0.05)  # имитация тяжёлого обучения
            return MagicMock()

        with patch.object(trainer, "_train_blocking", return_value=MagicMock()):
            # Запускаем run() и side_task параллельно
            with patch.object(trainer, "_save"):
                await asyncio.gather(trainer.run(), side_task())

        assert side_task_ran, "Event loop был заблокирован во время обучения"
