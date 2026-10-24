package cc.zenqi.totocheck

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject

/**
 * TOTO Check, Android shell. It shows https://toto.zenqi.cc in a WebView and adds exactly
 * one thing the website cannot do: window.TotoNative.capture(id, officialUrl), which opens one
 * official results page in a hidden WebView and hands back a picture of it (OfficialCapture).
 * The page uses that for the one-tap unlock; everything else is the normal website.
 *
 * NOT YET COMPILED OR RUN: written 22 Oct 2026 without an Android toolchain. See android/README.md.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var web: WebView
    private lateinit var capture: OfficialCapture
    private var chooserCallback: ValueCallback<Array<Uri>>? = null

    // "Choose screenshot" / "Upload photos" in the page open the system picker through this.
    private val chooser = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { r ->
        chooserCallback?.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(r.resultCode, r.data))
        chooserCallback = null
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        WebView.enableSlowWholeDocumentDraw()          // must run before any WebView exists: lets a capture see the whole page
        super.onCreate(savedInstanceState)

        web = WebView(this)
        setContentView(web)
        capture = OfficialCapture(this)

        with(web.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            userAgentString = userAgentString + " " + OfficialCapture.APP_UA   // honest: we are an app, and the server can tell
        }
        web.setBackgroundColor(0xFF0D0A1E.toInt())
        web.addJavascriptInterface(Bridge(), "TotoNative")

        web.webViewClient = object : WebViewClient() {
            // Only our own site stays inside the app. Any other link (the official page, Play, etc.) opens in the browser.
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                if (request.url.host == START_HOST) return false
                try { startActivity(Intent(Intent.ACTION_VIEW, request.url)) } catch (_: ActivityNotFoundException) {}
                return true
            }
        }
        web.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(
                view: WebView, callback: ValueCallback<Array<Uri>>, params: FileChooserParams
            ): Boolean {
                chooserCallback?.onReceiveValue(null)
                chooserCallback = callback
                return try {
                    chooser.launch(params.createIntent()); true
                } catch (_: ActivityNotFoundException) {
                    chooserCallback = null; false
                }
            }
        }
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() { if (web.canGoBack()) web.goBack() else finish() }
        })

        web.loadUrl(START_URL)
    }

    override fun onDestroy() {
        capture.cancel()
        web.destroy()
        super.onDestroy()
    }

    /** What the page sees as window.TotoNative. Only pages of our own site can ever reach it. */
    private inner class Bridge {
        @JavascriptInterface
        fun capture(id: String, url: String) {
            runOnUiThread { capture.run(url) { b64, err -> deliver(id, b64, err) } }
        }
    }

    private fun deliver(id: String, b64: String?, err: String?) {
        val js = "window.__totoCaptured(" + JSONObject.quote(id) + "," +
            (if (b64 == null) "null" else JSONObject.quote(b64)) + "," +
            (if (err == null) "null" else JSONObject.quote(err)) + ")"
        web.evaluateJavascript(js, null)
    }

    companion object {
        const val START_HOST = "toto.zenqi.cc"
        const val START_URL = "https://toto.zenqi.cc/"
    }
}
