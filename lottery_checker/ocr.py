"""Google Vision OCR wrapper (P3-01).

Turns a ticket photo into text plus word boxes for the ticket parser (P3-02).
Stdlib only, no network at import time, one request per call.

Design rules
- One call, no retries: a retry is a second billed Vision request and would
  count against the user's quota (P4-05), so the caller decides.
- Fails loudly: an API error, bad status or malformed reply raises OcrError.
  A genuinely blank photo is NOT an error; it returns an empty OcrResult so the
  UI can say "no text found, retake the photo".
- The API key goes in the X-Goog-Api-Key header, never in the URL, so it cannot
  end up in logs or referrers. The key is read from GOOGLE_VISION_API_KEY.
- Image bytes are never logged or stored here.
- The HTTP call is an injectable `transport`, so tests and a future service
  account or proxy need no changes to callers.

DOCUMENT_TEXT_DETECTION is used (not TEXT_DETECTION) because tickets are dense
printed text laid out in columns, where it keeps reading order better.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"
ENV_KEY = "GOOGLE_VISION_API_KEY"
TIMEOUT_S = 30
# Vision's JSON request limit is 10 MB. Base64 adds a third, so raw bytes must
# stay under about 7.5 MB; 7 MB leaves room for the JSON wrapper.
MAX_IMAGE_BYTES = 7_000_000

# transport(url, headers, body, timeout) -> (http_status, response_bytes)
Transport = Callable[[str, dict, bytes, float], "tuple[int, bytes]"]


class OcrError(RuntimeError):
    """Vision refused, failed, or returned something we cannot read."""


class OcrNotConfigured(OcrError):
    """No API key, so no request was made."""


@dataclass(frozen=True)
class Word:
    text: str
    box: tuple[int, int, int, int]       # x0, y0, x1, y1 (axis-aligned, pixels)
    confidence: Optional[float] = None   # 0-1 when Vision supplies it


@dataclass
class OcrResult:
    text: str                            # full text in Vision's reading order
    words: list[Word] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.text.strip()

    @property
    def mean_confidence(self) -> Optional[float]:
        vals = [w.confidence for w in self.words if w.confidence is not None]
        return sum(vals) / len(vals) if vals else None

    def skew(self, limit: float = 12.0, step: float = 0.5) -> float:
        """Tilt of the text in degrees (positive = text runs downhill to the right).

        A photographed ticket is rarely level. Words are projected onto the
        vertical at each candidate angle, and the angle where they pile up into
        the sharpest rows wins. Under 8 words, or no clear winner, means 0.
        """
        import math
        ws = [w for w in self.words if w.text.strip()]
        if len(ws) < 8:
            return 0.0
        hs = sorted(max(1, w.box[3] - w.box[1]) for w in ws)
        bin_h = max(2.0, hs[len(hs) // 2] * 0.5)
        pts = [((w.box[0] + w.box[2]) / 2, (w.box[1] + w.box[3]) / 2) for w in ws]

        def sharp(deg: float) -> float:
            t = math.radians(deg)
            bins: dict[int, int] = {}
            for x, y in pts:
                k = int((y * math.cos(t) - x * math.sin(t)) // bin_h)
                bins[k] = bins.get(k, 0) + 1
            return float(sum(c * c for c in bins.values()))

        n = int(limit / step)
        scores = {i * step: sharp(i * step) for i in range(-n, n + 1)}
        top = max(scores.values())
        if top <= scores[0.0] * 1.03:            # no clear gain over level
            return 0.0
        plateau = sorted(d for d, v in scores.items() if v >= top * 0.97)
        return plateau[len(plateau) // 2]        # middle of the sharp range

    def lines(self, tolerance: float = 0.6, deskew: bool = True) -> list[str]:
        """Words regrouped into rows by vertical position, corrected for tilt.

        Vision's own text keeps reading order, but ticket rows such as
        "A 03 08 14 21 22 26" can come back split, and on a tilted photo two
        boards merge into one row. Positions are rotated by the estimated skew
        first, then a word joins the current row if its vertical centre lies
        within `tolerance` x the row's word height of the row centre.
        """
        import math
        t = math.radians(self.skew()) if deskew else 0.0
        ct, st = math.cos(t), math.sin(t)

        def pos(w: Word) -> tuple[float, float, float]:
            cx, cy = (w.box[0] + w.box[2]) / 2, (w.box[1] + w.box[3]) / 2
            return cx * ct + cy * st, cy * ct - cx * st, max(1, w.box[3] - w.box[1])

        items = sorted(((*pos(w), w) for w in self.words), key=lambda p: (p[1], p[0]))
        rows: list[list[tuple]] = []
        for x, y, h, w in items:
            if rows:
                rx, ry, rh, _ = rows[-1][0]
                if abs(y - ry) <= tolerance * max(h, rh):
                    rows[-1].append((x, y, h, w))
                    continue
            rows.append([(x, y, h, w)])
        return [" ".join(i[3].text for i in sorted(r, key=lambda i: i[0])) for r in rows]


def _urllib_transport(url: str, headers: dict, body: bytes, timeout: float):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return getattr(r, "status", 200), r.read()
    except urllib.error.HTTPError as e:      # still carries Vision's JSON error body
        return e.code, e.read()


def _box(vertices: Sequence[dict]) -> tuple[int, int, int, int]:
    # Vision omits a coordinate when it is 0, so default to 0.
    xs = [int(v.get("x", 0)) for v in vertices] or [0]
    ys = [int(v.get("y", 0)) for v in vertices] or [0]
    return min(xs), min(ys), max(xs), max(ys)


def _words(full: dict) -> list[Word]:
    out: list[Word] = []
    for page in full.get("pages", []):
        for block in page.get("blocks", []):
            for para in block.get("paragraphs", []):
                for w in para.get("words", []):
                    text = "".join(s.get("text", "") for s in w.get("symbols", []))
                    if not text:
                        continue
                    out.append(Word(text, _box(w.get("boundingBox", {}).get("vertices", [])),
                                    w.get("confidence")))
    return out


def parse_response(payload: bytes) -> OcrResult:
    """Turn a Vision images:annotate reply into an OcrResult, or raise OcrError."""
    try:
        data = json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise OcrError("Vision reply was not JSON") from e
    if isinstance(data, dict) and "error" in data:          # request-level error
        err = data["error"]
        raise OcrError(f"Vision error {err.get('code')}: {err.get('message')}")
    replies = data.get("responses") if isinstance(data, dict) else None
    if not isinstance(replies, list) or len(replies) != 1:
        raise OcrError("Vision reply had no single response")
    reply = replies[0]
    if "error" in reply:                                    # per-image error
        err = reply["error"]
        raise OcrError(f"Vision error {err.get('code')}: {err.get('message')}")
    full = reply.get("fullTextAnnotation")
    if not full:
        return OcrResult("")                                # blank photo, not a failure
    return OcrResult(full.get("text", ""), _words(full))


def recognize(image: bytes, *, api_key: Optional[str] = None,
              transport: Optional[Transport] = None,
              language_hints: Sequence[str] = ("en",)) -> OcrResult:
    """OCR one ticket photo. One Vision request, no retries."""
    if not image:
        raise OcrError("no image data")
    if len(image) > MAX_IMAGE_BYTES:
        raise OcrError(f"image is {len(image):,} bytes; the limit is {MAX_IMAGE_BYTES:,}. "
                       "Resize or recompress before OCR.")
    key = (api_key or os.environ.get(ENV_KEY, "")).strip()
    if not key:
        raise OcrNotConfigured(f"set {ENV_KEY} (or pass api_key); no request made")

    body = json.dumps({"requests": [{
        "image": {"content": base64.b64encode(image).decode("ascii")},
        "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
        "imageContext": {"languageHints": list(language_hints)},
    }]}).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": key}

    status, payload = (transport or _urllib_transport)(ENDPOINT, headers, body, TIMEOUT_S)
    if status != 200:
        # The body is Vision's own error JSON; parse_response turns it into a clear message.
        try:
            parse_response(payload)
        except OcrError as e:
            raise OcrError(f"HTTP {status}: {e}") from None
        raise OcrError(f"HTTP {status} from Vision")
    return parse_response(payload)
