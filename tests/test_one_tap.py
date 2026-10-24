"""One-tap unlock in the Android app (owner, 22 Oct 2026): "remove the friction of 4 steps
into a single tap, masked by an animation, reveal within about 3 seconds".

The page asks the app (window.TotoNative.capture) for a picture of the draw's official
page and sends it to the same screenshot reader. The Kotlin cannot be compiled here, so
these tests pin the rules that matter: where the app may go, how much, and how to turn it off."""
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from lottery_checker import api, shared  # noqa: E402
from tests.test_api import data  # noqa: E402,F401  (fixture)

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
KT = ROOT / "android" / "app" / "src" / "main"


def test_server_can_switch_the_one_tap_off_for_every_app(data, monkeypatch):  # noqa: F811
    monkeypatch.delenv("TOTO_AUTO_CAPTURE", raising=False)
    assert TestClient(api.create_app(data)).get("/api/health").json()["auto_capture"] is True
    monkeypatch.setenv("TOTO_AUTO_CAPTURE", "0")
    assert TestClient(api.create_app(data)).get("/api/health").json()["auto_capture"] is False


def test_app_entries_are_labelled_as_the_app():
    ua = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126 Mobile Safari/537.36 TotoCheckApp/1"
    assert shared.device_label(ua) == "Android · App"
    assert shared.device_label("Mozilla/5.0 (Linux; Android 14) Chrome/126 Mobile Safari/537.36") == "Android · Chrome"


def test_page_one_tap_is_only_for_draws_we_hold_no_result_for_and_is_capped():
    assert "const AUTO_MAX = 4" in PAGE
    assert "needDraws().slice(0, AUTO_MAX)" in PAGE            # never a draw that is already on file
    assert "needDraws().length <= AUTO_MAX" in PAGE
    assert "S.autoCapture" in PAGE and "r.auto_capture !== false" in PAGE   # the server's kill switch
    assert "oneTap ? h(\"button\"" in PAGE                      # shown only when the app bridge is there
    assert "window.TotoNative && typeof window.TotoNative.capture" in PAGE


def test_page_falls_back_to_the_manual_steps_and_never_flashes():
    assert "Use the steps below instead." in PAGE
    assert "AUTO_MIN_MS" in PAGE and "if (readAll) return runCheck();" in PAGE
    assert "not every number" in PAGE                           # a short read goes to the results form, not the reveal


def test_app_only_opens_official_results_pages_with_a_daily_cap():
    kt = (KT / "java" / "cc" / "zenqi" / "totocheck" / "OfficialCapture.kt").read_text(encoding="utf-8")
    assert 'setOf("www.singaporepools.com.sg", "singaporepools.com.sg")' in kt
    assert '"/en/product/sr/Pages/"' in kt and 'uri.scheme == "https"' in kt
    assert "MAX_PER_DAY = 40" in kt and "if (busy)" in kt and "MIN_GAP_MS" in kt
    assert 'APP_UA = "TotoCheckApp/1"' in kt


def test_app_keeps_navigation_on_our_site_and_asks_for_internet_only():
    main = (KT / "java" / "cc" / "zenqi" / "totocheck" / "MainActivity.kt").read_text(encoding="utf-8")
    assert 'START_HOST = "toto.zenqi.cc"' in main and "request.url.host == START_HOST" in main
    assert "allowFileAccess = false" in main
    manifest = (KT / "AndroidManifest.xml").read_text(encoding="utf-8")
    assert manifest.count("<uses-permission") == 1 and "android.permission.INTERNET" in manifest
    assert 'android:usesCleartextTraffic="false"' in manifest
