# TOTO Check for Android (shell around toto.zenqi.cc)

Not yet built or run (written 22 Oct 2026 on a machine with no Android toolchain). Expect to fix a
compile error or two and to tune the whole-page capture on a real phone.

## What it is
A WebView showing https://toto.zenqi.cc plus one bridge, `window.TotoNative.capture(id, url)`,
which opens ONE official results page in a hidden WebView and returns a JPEG of it. The page
uses that for the **one-tap unlock**: tap "Reveal my result", a 3-second sealed-box animation
plays while the app opens the official page, reads it through the same screenshot reader, and
goes straight to the reveal. Everything else is the website, so page changes need no new APK.
If anything fails the page falls back to the manual steps. In a normal browser nothing changes.

## Build on Grayskull (side-load, no Play account needed)
1. Install Android Studio. Open this `android` folder. Let it sync (it creates the Gradle wrapper).
2. Build > Build Bundle(s) / APK(s) > Build APK(s).
3. Copy `app\build\outputs\apk\debug\app-debug.apk` to the phone and open it (allow "install unknown apps" once).
4. Send me the Gradle error text or a screenshot if the build or the capture misbehaves.

## Guardrails (in `OfficialCapture.kt` and the page)
- Only https://(www.)singaporepools.com.sg/en/product/sr/Pages/ results pages.
- One page per call, only for a draw on the person's own ticket that we hold no result for, at most 4 per tap, 40 a day per phone, never in the background, never a loop over draws.
- Honest user agent: `TotoCheckApp/1`. Nothing stored on the phone; the picture goes only to toto.zenqi.cc.
- Kill switch: set `TOTO_AUTO_CAPTURE=0` on Grayskull and restart; every app then shows the manual steps.
- Singapore Pools' written permission (roadmap P2-02) is still outstanding. Mention this feature in the permission email.

## Not in this version
- Share-to-app (the website already has it for Chrome-installed PWAs; the shell could add an intent filter later).
- Camera "capture" straight from the page's Scan button: the picker opens instead (choose Camera in it).
- Play Store release (signing, listing: roadmap P4-07/08).
