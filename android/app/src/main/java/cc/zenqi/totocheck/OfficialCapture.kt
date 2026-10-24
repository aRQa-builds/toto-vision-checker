package cc.zenqi.totocheck

import android.app.Activity
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.util.Base64
import android.view.View
import android.view.ViewGroup
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import java.io.ByteArrayOutputStream
import java.time.LocalDate

/**
 * Opens ONE official results page in a hidden WebView, waits until the results are drawn,
 * and returns a JPEG of the whole page (base64, no prefix) to the TOTO Check page, which sends
 * it to the same screenshot reader as a picture you took yourself. It is the one-tap version
 * of "open the page, screenshot it, come back".
 *
 * What it will and won't do (the owner's rules, 22 Oct 2026; Singapore Pools' written
 * permission is still outstanding, roadmap P2-02):
 *  - only https://(www.)singaporepools.com.sg/en/product/sr/Pages/... results pages
 *  - one page at a time, started by a tap in the page for a draw on the person's own ticket,
 *    at most 40 pages a day on this phone, never in the background, never a loop over draws
 *  - an honest user agent ("TotoCheckApp/1" on top of the WebView's own)
 *  - nothing is stored; the picture goes only to toto.zenqi.cc for reading
 *
 * NOT YET COMPILED OR RUN: written 22 Oct 2026 without an Android toolchain.
 * Likeliest thing to need adjusting on a real phone: the whole-page draw in snapshot().
 */
class OfficialCapture(private val activity: Activity) {

    private val main = Handler(Looper.getMainLooper())
    private var busy = false
    private var lastAt = 0L
    private var current: WebView? = null
    private var timeoutTask: Runnable? = null

    fun run(url: String, done: (String?, String?) -> Unit) {
        val uri = Uri.parse(url)
        val ok = uri.scheme == "https" && uri.host.orEmpty() in HOSTS &&
            uri.path.orEmpty().startsWith("/en/product/sr/Pages/")
        if (!ok) { done(null, "That isn't an official results page."); return }
        if (busy) { done(null, "Already opening a page."); return }
        val wait = MIN_GAP_MS - (System.currentTimeMillis() - lastAt)
        if (wait > 0) { main.postDelayed({ run(url, done) }, wait); return }
        if (!underDailyCap()) { done(null, "Daily limit reached on this phone. Use the manual steps."); return }

        busy = true
        val density = activity.resources.displayMetrics.density
        val widthPx = (WIDTH_DP * density).toInt()
        val wv = WebView(activity)
        current = wv
        wv.settings.javaScriptEnabled = true
        wv.settings.domStorageEnabled = true
        wv.settings.userAgentString = wv.settings.userAgentString + " " + APP_UA
        // Attached (so it lays out and draws) but pushed off to the left, out of sight.
        val root = activity.window.decorView as ViewGroup
        root.addView(wv, FrameLayout.LayoutParams(widthPx, 1))
        wv.translationX = -2f * widthPx

        fun finish(b64: String?, err: String?) {
            if (!busy) return
            busy = false
            lastAt = System.currentTimeMillis()
            timeoutTask?.let { main.removeCallbacks(it) }
            current = null
            root.removeView(wv)
            wv.destroy()
            done(b64, err)
        }

        val t = Runnable { finish(null, "The official page took too long to load.") }
        timeoutTask = t
        main.postDelayed(t, TIMEOUT_MS)

        wv.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView, u: String) {
                pollUntilDrawn(view, widthPx, 0) { b64, err -> finish(b64, err) }
            }
        }
        wv.loadUrl(url)
    }

    fun cancel() {
        timeoutTask?.let { main.removeCallbacks(it) }
        current?.let { (it.parent as? ViewGroup)?.removeView(it); it.destroy() }
        current = null
        busy = false
    }

    /** The results are filled in by script after the page loads: wait until the prize table is there. */
    private fun pollUntilDrawn(wv: WebView, widthPx: Int, tries: Int, done: (String?, String?) -> Unit) {
        if (!busy) return
        wv.evaluateJavascript(READY_JS) { r ->
            when {
                r == "true" -> main.postDelayed({
                    val b64 = snapshot(wv, widthPx)
                    if (b64 == null) done(null, "Couldn't take a picture of the page.") else done(b64, null)
                }, SETTLE_MS)
                tries >= MAX_POLLS -> done(null, "The official page didn't show a result.")
                else -> main.postDelayed({ pollUntilDrawn(wv, widthPx, tries + 1, done) }, POLL_MS)
            }
        }
    }

    /** Whole-page picture: measure at full height, lay out, draw (works because enableSlowWholeDocumentDraw ran). */
    private fun snapshot(wv: WebView, widthPx: Int): String? {
        wv.measure(
            View.MeasureSpec.makeMeasureSpec(widthPx, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED)
        )
        val w = wv.measuredWidth
        val h = minOf(wv.measuredHeight, MAX_HEIGHT_PX)
        if (w <= 0 || h <= 0) return null
        wv.layout(0, 0, w, h)
        val scale = minOf(1f, OUT_WIDTH_PX.toFloat() / w)
        val bmp = Bitmap.createBitmap((w * scale).toInt(), (h * scale).toInt(), Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)
        canvas.scale(scale, scale)
        wv.draw(canvas)
        val out = ByteArrayOutputStream()
        bmp.compress(Bitmap.CompressFormat.JPEG, 82, out)
        bmp.recycle()
        return Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
    }

    private fun underDailyCap(): Boolean {
        val p = activity.getSharedPreferences("capture", Context.MODE_PRIVATE)
        val today = LocalDate.now().toString()
        val n = if (p.getString("day", "") == today) p.getInt("n", 0) else 0
        if (n >= MAX_PER_DAY) return false
        p.edit().putString("day", today).putInt("n", n + 1).apply()
        return true
    }

    companion object {
        const val APP_UA = "TotoCheckApp/1"
        private val HOSTS = setOf("www.singaporepools.com.sg", "singaporepools.com.sg")
        private const val WIDTH_DP = 412
        private const val OUT_WIDTH_PX = 1080
        private const val MAX_HEIGHT_PX = 9000
        private const val MAX_PER_DAY = 40
        private const val MIN_GAP_MS = 1500L
        private const val TIMEOUT_MS = 25_000L
        private const val POLL_MS = 400L
        private const val SETTLE_MS = 400L
        private const val MAX_POLLS = 50
        // true once the page shows a result: TOTO's Group 7 row or 4D's Consolation block
        private const val READY_JS =
            "(function(){var t=(document.body&&document.body.innerText)||'';" +
            "return /Winning Numbers/i.test(t)&&/Group\\s*7/i.test(t)||/1st Prize/i.test(t)&&/Consolation/i.test(t);})()"
    }
}
