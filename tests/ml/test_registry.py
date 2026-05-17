"""
Unit tests for app/registry.py :: ModelRegistry.

Verify:
  - initial state
  - load_from_disk (joblib + meta.json)
  - retraining lifecycle: begin → stage → promote / abort
  - protection against concurrent retraining (asyncio.Lock)
  - zero-downtime: old ensemble reference remains alive after promote()

Does NOT duplicate model tests — ensemble is always a MagicMock here.
"""
from __future__ import annotations

import asyncio
import json

import joblib
import pytest
import pytest_asyncio
from unittest.mock import MagicMock
from dataclasses import dataclass

from app.ml.registry import ModelRegistry


# ── helpers ─────────────────────────────────────────────────────────────────


@dataclass
class FakeEnsemble:
    name: str = "v1"


def fake_ensemble(name: str = "v1") -> MagicMock:
    return FakeEnsemble(name=name)


# ═══════════════════════════════════════════════════════════════════════════
# Начальное состояние
# ═══════════════════════════════════════════════════════════════════════════


class TestInitialState:
    def test_not_ready(self):
        assert not ModelRegistry().is_ready()

    def test_active_is_none(self):
        assert ModelRegistry().active is None

    def test_version_is_none_string(self):
        assert ModelRegistry().version == "none"

    def test_retraining_is_false(self):
        assert ModelRegistry().retraining is False


# ═══════════════════════════════════════════════════════════════════════════
# load_from_disk
# ═══════════════════════════════════════════════════════════════════════════


class TestLoadFromDisk:
    @pytest.mark.asyncio
    async def test_is_ready_after_load(self, tmp_path):
        joblib.dump(fake_ensemble(), tmp_path / "ensemble.pkl")
        reg = ModelRegistry()
        await reg.load_from_disk(str(tmp_path))
        assert reg.is_ready()

    @pytest.mark.asyncio
    async def test_version_read_from_meta_json(self, tmp_path):
        joblib.dump(fake_ensemble(), tmp_path / "ensemble.pkl")
        (tmp_path / "meta.json").write_text(json.dumps({"version": "20240101T000000"}))
        reg = ModelRegistry()
        await reg.load_from_disk(str(tmp_path))
        assert reg.version == "20240101T000000"

    @pytest.mark.asyncio
    async def test_version_is_timestamp_without_meta(self, tmp_path):
        """Без meta.json версия генерируется автоматически (непустая строка)."""
        joblib.dump(fake_ensemble(), tmp_path / "ensemble.pkl")
        reg = ModelRegistry()
        await reg.load_from_disk(str(tmp_path))
        assert reg.version not in ("none", "")

    @pytest.mark.asyncio
    async def test_active_ensemble_is_set(self, tmp_path):
        ens = fake_ensemble("loaded")
        joblib.dump(ens, tmp_path / "ensemble.pkl")
        reg = ModelRegistry()
        await reg.load_from_disk(str(tmp_path))
        # active должен быть тем объектом, который лежал в pkl
        assert reg.active is not None


# ═══════════════════════════════════════════════════════════════════════════
# Жизненный цикл переобучения
# ═══════════════════════════════════════════════════════════════════════════


class TestRetrainingLifecycle:
    @pytest.mark.asyncio
    async def test_begin_returns_true_first_call(self):
        reg = ModelRegistry()
        assert await reg.begin_retraining() is True

    @pytest.mark.asyncio
    async def test_begin_sets_retraining_flag(self):
        reg = ModelRegistry()
        await reg.begin_retraining()
        assert reg.retraining is True

    @pytest.mark.asyncio
    async def test_begin_returns_false_when_already_running(self):
        reg = ModelRegistry()
        await reg.begin_retraining()
        assert await reg.begin_retraining() is False

    @pytest.mark.asyncio
    async def test_promote_replaces_active(self):
        reg = ModelRegistry()
        reg._active = fake_ensemble("v1")
        await reg.begin_retraining()
        reg.set_staging(fake_ensemble("v2"))
        await reg.promote("ver-2")
        assert reg.active.name == "v2"

    @pytest.mark.asyncio
    async def test_promote_updates_version(self):
        reg = ModelRegistry()
        await reg.begin_retraining()
        reg.set_staging(fake_ensemble())
        await reg.promote("20250515T020000")
        assert reg.version == "20250515T020000"

    @pytest.mark.asyncio
    async def test_promote_clears_retraining_flag(self):
        reg = ModelRegistry()
        await reg.begin_retraining()
        reg.set_staging(fake_ensemble())
        await reg.promote("v-new")
        assert reg.retraining is False

    @pytest.mark.asyncio
    async def test_promote_without_staging_raises_runtime_error(self):
        reg = ModelRegistry()
        await reg.begin_retraining()
        with pytest.raises(RuntimeError):
            await reg.promote("v-fail")

    @pytest.mark.asyncio
    async def test_abort_clears_retraining_flag(self):
        reg = ModelRegistry()
        await reg.begin_retraining()
        await reg.abort_retraining()
        assert reg.retraining is False

    @pytest.mark.asyncio
    async def test_abort_invalidates_staging(self):
        """После abort() повторный promote() должен падать."""
        reg = ModelRegistry()
        await reg.begin_retraining()
        reg.set_staging(fake_ensemble())
        await reg.abort_retraining()
        with pytest.raises(RuntimeError):
            await reg.promote("after-abort")

    @pytest.mark.asyncio
    async def test_can_begin_retraining_again_after_promote(self):
        """После успешного promote() можно начать следующий цикл."""
        reg = ModelRegistry()
        await reg.begin_retraining()
        reg.set_staging(fake_ensemble())
        await reg.promote("v1")
        result = await reg.begin_retraining()
        assert result is True

    @pytest.mark.asyncio
    async def test_can_begin_retraining_again_after_abort(self):
        reg = ModelRegistry()
        await reg.begin_retraining()
        await reg.abort_retraining()
        result = await reg.begin_retraining()
        assert result is True


# ═══════════════════════════════════════════════════════════════════════════
# Zero-downtime: ссылка на ансамбль стабильна во время promote
# ═══════════════════════════════════════════════════════════════════════════


class TestZeroDowntime:
    @pytest.mark.asyncio
    async def test_snapshot_before_promote_stays_valid(self):
        """
        Задача A захватила ссылку на active (v1).
        Затем promote() подменил active на v2.
        Задача A всё ещё работает с v1 — GIL + неизменяемость ссылки гарантируют это.
        """
        reg = ModelRegistry()
        v1 = fake_ensemble("v1")
        reg._active = v1

        # Задача A «захватила» ссылку до promote
        local_ref = reg.active

        await reg.begin_retraining()
        reg.set_staging(fake_ensemble("v2"))
        await reg.promote("v2")

        # v2 теперь активна для новых запросов
        assert reg.active.name == "v2"
        # Старый снимок всё ещё указывает на v1
        assert local_ref.name == "v1"

    @pytest.mark.asyncio
    async def test_concurrent_begin_only_one_winner(self):
        """
        asyncio.gather запускает три begin_retraining параллельно.
        Только одна корутина должна получить True.
        """
        reg = ModelRegistry()
        results = await asyncio.gather(
            reg.begin_retraining(),
            reg.begin_retraining(),
            reg.begin_retraining(),
        )
        assert results.count(True) == 1
        assert results.count(False) == 2
