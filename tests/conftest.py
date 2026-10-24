"""Tests never use the real Google Vision key.

Grayskull has GOOGLE_VISION_API_KEY set for the live site (P3-01, 22 Oct 2026).
Without this, tests that expect "no key" would make real, billed Vision calls.
Tests that need OCR inject a fake recognize/transport instead.
"""
import pytest


@pytest.fixture(autouse=True)
def _no_real_vision_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_VISION_API_KEY", raising=False)
    monkeypatch.delenv("TOTO_SHARED_RESULTS", raising=False)      # shared results on, as by default
