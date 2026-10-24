"""P3-01: the Vision OCR wrapper. No network: every test injects a fake transport."""
import base64
import json

import pytest

from lottery_checker import ocr
from lottery_checker.ocr import OcrError, OcrNotConfigured, OcrResult, Word, parse_response, recognize


def _word(text, x0, y0, x1, y1, conf=0.99):
    return {
        "boundingBox": {"vertices": [{"x": x0, "y": y0}, {"x": x1, "y": y0},
                                     {"x": x1, "y": y1}, {"x": x0, "y": y1}]},
        "symbols": [{"text": ch} for ch in text],
        "confidence": conf,
    }


def reply(words, text):
    return json.dumps({"responses": [{"fullTextAnnotation": {
        "text": text,
        "pages": [{"blocks": [{"paragraphs": [{"words": words}]}]}],
    }}]}).encode()


def fake(status=200, body=b"{}", seen=None):
    def transport(url, headers, payload, timeout):
        if seen is not None:
            seen.append((url, headers, payload, timeout))
        return status, body
    return transport


# ---------- Parsing a reply ----------

def test_parse_text_and_words():
    r = parse_response(reply([_word("TOTO", 10, 5, 60, 25), _word("4068", 70, 5, 120, 25, 0.9)],
                             "TOTO 4068"))
    assert r.text == "TOTO 4068" and not r.empty
    assert [w.text for w in r.words] == ["TOTO", "4068"]
    assert r.words[1].box == (70, 5, 120, 25)
    assert r.mean_confidence == pytest.approx(0.945)


def test_missing_zero_coordinates_default_to_zero():
    # Vision drops a coordinate that is 0; the word at the top-left corner must still parse.
    w = {"boundingBox": {"vertices": [{}, {"x": 50}, {"x": 50, "y": 20}, {"y": 20}]},
         "symbols": [{"text": "A"}]}
    assert parse_response(reply([w], "A")).words[0].box == (0, 0, 50, 20)


def test_blank_photo_is_empty_not_an_error():
    r = parse_response(json.dumps({"responses": [{}]}).encode())
    assert r.empty and r.words == [] and r.mean_confidence is None


@pytest.mark.parametrize("payload", [
    b"not json",
    b"[]",
    json.dumps({"responses": []}).encode(),
    json.dumps({"responses": [{}, {}]}).encode(),
    json.dumps({"nothing": 1}).encode(),
])
def test_malformed_reply_raises(payload):
    with pytest.raises(OcrError):
        parse_response(payload)


def test_request_level_and_image_level_errors_raise():
    with pytest.raises(OcrError, match="403.*denied"):
        parse_response(json.dumps({"error": {"code": 403, "message": "denied"}}).encode())
    with pytest.raises(OcrError, match="3.*bad image"):
        parse_response(json.dumps({"responses": [{"error": {"code": 3, "message": "bad image"}}]}).encode())


# ---------- Rebuilding ticket rows ----------

def test_lines_group_by_vertical_position_and_sort_left_to_right():
    words = [Word("22", (100, 50, 130, 70)), Word("A", (0, 10, 20, 30)),
             Word("03", (30, 11, 60, 31)), Word("B", (0, 50, 20, 70)),
             Word("08", (30, 49, 60, 69)), Word("14", (65, 12, 95, 32))]
    r = OcrResult("", words)
    assert r.lines() == ["A 03 14", "B 08 22"]


def test_lines_empty():
    assert OcrResult("").lines() == []


# ---------- The request we send ----------

def test_recognize_sends_one_correct_request():
    seen = []
    img = b"\xff\xd8fakejpeg"
    r = recognize(img, api_key="K1", transport=fake(body=reply([], "hi"), seen=seen))
    assert r.text == "hi" and len(seen) == 1
    url, headers, payload, timeout = seen[0]
    assert url == ocr.ENDPOINT and timeout == ocr.TIMEOUT_S
    assert headers["X-Goog-Api-Key"] == "K1"
    assert "K1" not in url                                   # key never in the URL
    req = json.loads(payload)["requests"][0]
    assert base64.b64decode(req["image"]["content"]) == img
    assert req["features"] == [{"type": "DOCUMENT_TEXT_DETECTION"}]
    assert req["imageContext"]["languageHints"] == ["en"]


def test_key_from_environment(monkeypatch):
    monkeypatch.setenv(ocr.ENV_KEY, "ENVKEY")
    seen = []
    recognize(b"x", transport=fake(body=reply([], ""), seen=seen))
    assert seen[0][1]["X-Goog-Api-Key"] == "ENVKEY"


def test_no_key_means_no_request(monkeypatch):
    monkeypatch.delenv(ocr.ENV_KEY, raising=False)
    seen = []
    with pytest.raises(OcrNotConfigured):
        recognize(b"x", transport=fake(seen=seen))
    assert seen == []


@pytest.mark.parametrize("size", [0, ocr.MAX_IMAGE_BYTES + 1], ids=["empty", "too_large"])
def test_bad_image_raises_before_any_request(size):
    # Pass a size, not the bytes: pytest puts parameters in the test id, and a 7 MB id
    # overflows Windows' 32,767-character environment variable limit.
    img = b"x" * size
    seen = []
    with pytest.raises(OcrError):
        recognize(img, api_key="K", transport=fake(seen=seen))
    assert seen == []


# ---------- Failures are loud, and never retried ----------

def test_http_error_carries_visionss_message_and_is_not_retried():
    seen = []
    body = json.dumps({"error": {"code": 429, "message": "quota exceeded"}}).encode()
    with pytest.raises(OcrError, match="HTTP 429.*quota exceeded"):
        recognize(b"x", api_key="K", transport=fake(status=429, body=body, seen=seen))
    assert len(seen) == 1                                    # one billed request, no retry


def test_http_error_with_unreadable_body_still_raises():
    with pytest.raises(OcrError, match="HTTP 502"):
        recognize(b"x", api_key="K", transport=fake(status=502, body=b"<html>bad gateway</html>"))


def test_http_200_with_unreadable_body_raises():
    with pytest.raises(OcrError):
        recognize(b"x", api_key="K", transport=fake(body=b"<html>"))


def test_ocr_errors_are_not_leaking_the_key():
    body = json.dumps({"error": {"code": 400, "message": "API key not valid"}}).encode()
    with pytest.raises(OcrError) as e:
        recognize(b"x", api_key="SECRETKEY", transport=fake(status=400, body=body))
    assert "SECRETKEY" not in str(e.value)
