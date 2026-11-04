package com.wrld.player

import android.Manifest
import android.app.Activity
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import com.google.common.util.concurrent.ListenableFuture
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private lateinit var web: WebView
    private lateinit var collections: CollectionStore
    private val executor = Executors.newSingleThreadExecutor()
    private val handler = Handler(Looper.getMainLooper())
    private var controllerFuture: ListenableFuture<MediaController>? = null
    private var controller: MediaController? = null
    private var songs: List<Song> = emptyList()
    private var webReady = false
    private var libraryLoading = false

    private val tick = object : Runnable {
        override fun run() {
            if (webReady) sendPlayerState()
            handler.postDelayed(this, 600)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Color.BLACK
        window.navigationBarColor = Color.BLACK
        enterImmersiveFullscreen()
        collections = CollectionStore(this)
        web = WebView(this).apply {
            setBackgroundColor(Color.rgb(5, 5, 5))
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = true
            settings.allowContentAccess = false
            settings.blockNetworkLoads = true
            settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            @Suppress("DEPRECATION")
            settings.allowFileAccessFromFileURLs = false
            @Suppress("DEPRECATION")
            settings.allowUniversalAccessFromFileURLs = false
            isVerticalScrollBarEnabled = false
            isHorizontalScrollBarEnabled = false
            webChromeClient = WebChromeClient()
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(
                    view: WebView?, request: WebResourceRequest?
                ): Boolean = true

                override fun onPageFinished(view: WebView?, url: String?) {
                    webReady = true
                    sendCollections()
                    sendPlayerState()
                    if (hasAudioPermission()) loadLibrary() else requestAudioPermission()
                }
            }
            addJavascriptInterface(NativeBridge(), "WRLDNative")
            loadUrl("file:///android_asset/index.html")
        }
        setContentView(web)
        connectPlayer()
        handler.post(tick)
    }

    /**
     * Immersive fullscreen: keep the system status/notification and navigation
     * bars out of WRLD's UI while still allowing transient bars by edge swipe.
     * Reapply after Android permission dialogs, app switching, or screen unlock.
     */
    private fun enterImmersiveFullscreen() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.setDecorFitsSystemWindows(false)
            window.insetsController?.apply {
                systemBarsBehavior =
                    WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
                hide(WindowInsets.Type.statusBars() or WindowInsets.Type.navigationBars())
            }
        } else {
            @Suppress("DEPRECATION")
            window.decorView.systemUiVisibility =
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or
                View.SYSTEM_UI_FLAG_FULLSCREEN or
                View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE or
                View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
                View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
        }
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) enterImmersiveFullscreen()
    }

    private fun hasAudioPermission(): Boolean {
        val permission = if (Build.VERSION.SDK_INT >= 33)
            Manifest.permission.READ_MEDIA_AUDIO else Manifest.permission.READ_EXTERNAL_STORAGE
        return checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED
    }

    private fun requestAudioPermission() {
        if (hasAudioPermission()) {
            loadLibrary()
            return
        }
        val permission = if (Build.VERSION.SDK_INT >= 33)
            Manifest.permission.READ_MEDIA_AUDIO else Manifest.permission.READ_EXTERNAL_STORAGE
        requestPermissions(arrayOf(permission), 100)
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != 100) return
        if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED)
            loadLibrary()
        else sendScript("window.WRLD.permissionDenied();")
    }

    private fun connectPlayer() {
        val token = SessionToken(this, ComponentName(this, PlaybackService::class.java))
        val future = MediaController.Builder(this, token).buildAsync()
        controllerFuture = future
        future.addListener({
            try {
                controller = future.get().also { player ->
                    player.addListener(object : Player.Listener {
                        override fun onEvents(player: Player, events: Player.Events) {
                            sendPlayerState()
                        }
                    })
                }
                sendPlayerState()
            } catch (error: Exception) {
                showError("Audio service could not start: " + (error.message ?: "unknown error"))
            }
        }, java.util.concurrent.Executor { command -> handler.post(command) })
    }

    private fun sendScript(script: String) {
        if (!webReady || isFinishing) return
        runOnUiThread {
            if (webReady && !isFinishing) web.evaluateJavascript(script, null)
        }
    }

    private fun sendCollections() {
        sendScript("window.WRLD.receiveCollections(" + collections.read().toString() + ");")
    }

    private fun loadLibrary() {
        if (!hasAudioPermission()) {
            sendScript("window.WRLD.permissionDenied();")
            return
        }
        if (libraryLoading) return
        libraryLoading = true
        executor.execute {
            try {
                val scanned = LibraryRepository.scan(applicationContext)
                runOnUiThread {
                    songs = scanned
                    libraryLoading = false
                    val json = JSONObject().put("songs", JSONArray().apply {
                        scanned.forEach { put(it.toJson()) }
                    })
                    sendScript("window.WRLD.receiveLibrary(" + json.toString() + ");")
                }
            } catch (error: Exception) {
                runOnUiThread {
                    libraryLoading = false
                    showError("Couldn't scan music: " + (error.message ?: "unknown error"))
                }
            }
        }
    }

    private fun sendPlayerState() {
        val player = controller
        val duration = player?.duration ?: 0L
        val result = JSONObject()
            .put("id", player?.currentMediaItem?.mediaId ?: "")
            .put("playing", player?.isPlaying == true)
            .put("position", (player?.currentPosition ?: 0L).coerceAtLeast(0L))
            .put("duration", if (duration == C.TIME_UNSET) 0L else duration.coerceAtLeast(0L))
            .put("volume", player?.volume
                ?: getSharedPreferences("wrld", MODE_PRIVATE).getFloat("volume", 0.10f))
            .put("repeat", when (player?.repeatMode) {
                Player.REPEAT_MODE_ALL -> "all"
                Player.REPEAT_MODE_ONE -> "one"
                else -> "off"
            })
        sendScript("window.WRLD.receivePlayer(" + result.toString() + ");")
    }

    private fun showError(message: String) {
        runOnUiThread {
            Toast.makeText(this, message, Toast.LENGTH_LONG).show()
            sendScript("window.WRLD.showMessage(" + JSONObject.quote(message) + ");")
        }
    }

    inner class NativeBridge {
        @JavascriptInterface fun requestLibrary() {
            runOnUiThread {
                if (hasAudioPermission()) loadLibrary() else requestAudioPermission()
            }
        }

        @JavascriptInterface fun playQueue(ids: String, index: Int) {
            runOnUiThread {
                val player = controller ?: return@runOnUiThread
                try {
                    val source = JSONArray(ids)
                    val mapped = songs.associateBy { it.id }
                    val playlist = mutableListOf<MediaItem>()
                    for (i in 0 until minOf(source.length(), 20000)) {
                        val song = mapped[source.optString(i)] ?: continue
                        playlist.add(MediaItem.Builder()
                            .setMediaId(song.id)
                            .setUri(song.uri)
                            .setMediaMetadata(
                                MediaMetadata.Builder()
                                    .setTitle(song.title)
                                    .setArtist(song.artist)
                                    .setAlbumTitle(song.album).build()
                            ).build())
                    }
                    if (playlist.isEmpty()) return@runOnUiThread
                    player.setMediaItems(playlist, index.coerceIn(0, playlist.lastIndex), 0L)
                    player.prepare()
                    player.play()
                    sendPlayerState()
                } catch (_: Exception) {
                    showError("Could not start selected song.")
                }
            }
        }

        @JavascriptInterface fun togglePlay() {
            runOnUiThread {
                val player = controller ?: return@runOnUiThread
                if (player.isPlaying) player.pause() else if (player.mediaItemCount > 0) player.play()
                sendPlayerState()
            }
        }

        @JavascriptInterface fun next() {
            runOnUiThread { controller?.seekToNextMediaItem(); sendPlayerState() }
        }

        @JavascriptInterface fun previous() {
            runOnUiThread {
                controller?.let {
                    if (it.currentPosition > 3000) it.seekTo(0)
                    else it.seekToPreviousMediaItem()
                }
                sendPlayerState()
            }
        }

        @JavascriptInterface fun seek(position: Long) {
            runOnUiThread { controller?.seekTo(position.coerceAtLeast(0L)); sendPlayerState() }
        }

        @JavascriptInterface fun setRepeat(mode: String) {
            runOnUiThread {
                controller?.repeatMode = when (mode) {
                    "all" -> Player.REPEAT_MODE_ALL
                    "one" -> Player.REPEAT_MODE_ONE
                    else -> Player.REPEAT_MODE_OFF
                }
                sendPlayerState()
            }
        }

        @JavascriptInterface fun setVolume(value: Double) {
            runOnUiThread {
                val volume = value.toFloat().coerceIn(0f, 1f)
                controller?.volume = volume
                getSharedPreferences("wrld", MODE_PRIVATE).edit().putFloat("volume", volume).apply()
                sendPlayerState()
            }
        }

        @JavascriptInterface fun setLike(id: String, enabled: Boolean) {
            runOnUiThread {
                if (songs.none { it.id == id }) return@runOnUiThread
                collections.like(id, enabled)
                sendCollections()
            }
        }

        @JavascriptInterface fun createPlaylist(name: String) {
            runOnUiThread { collections.create(name); sendCollections() }
        }

        @JavascriptInterface fun deletePlaylist(id: String) {
            runOnUiThread { collections.delete(id); sendCollections() }
        }

        @JavascriptInterface fun togglePlaylist(id: String, trackId: String) {
            runOnUiThread {
                if (songs.none { it.id == trackId }) return@runOnUiThread
                collections.toggleTrack(id, trackId)
                sendCollections()
            }
        }

        @JavascriptInterface fun openUpdates() {
            runOnUiThread {
                try {
                    val target = android.net.Uri.parse("https://github.com/xdStatus/WRLD/releases")
                    startActivity(Intent(Intent.ACTION_VIEW, target))
                } catch (_: Exception) { showError("No browser is available.") }
            }
        }
    }

    override fun onDestroy() {
        webReady = false
        handler.removeCallbacks(tick)
        controllerFuture?.let { MediaController.releaseFuture(it) }
        executor.shutdownNow()
        web.removeJavascriptInterface("WRLDNative")
        web.destroy()
        super.onDestroy()
    }
}
