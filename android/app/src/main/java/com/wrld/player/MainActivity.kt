package com.wrld.player

import android.Manifest
import android.app.NotificationManager
import android.content.Context
import androidx.work.WorkManager
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
    private lateinit var history: HistoryStore
    private lateinit var audioSettings: AudioSettingsStore
    private val executor = Executors.newSingleThreadExecutor()
    private val handler = Handler(Looper.getMainLooper())
    private var controllerFuture: ListenableFuture<MediaController>? = null
    private var controller: MediaController? = null
    private var songs: List<Song> = emptyList()
    private var localSongs: List<Song> = emptyList()
    private var cloudSongs: List<Song> = emptyList()
    private var musicSource = "device"
    private var cloudAddress = ""
    private var webReady = false
    private var libraryLoading = false
    private var cloudRequestVersion = 0
    private var queueOpened = false
    private var cloudCollections = JSONObject().put("liked", JSONArray())
        .put("playlists", JSONArray()).put("history", JSONArray()).put("listeningMs", 0L)
    private var cloudSyncBusy = false
    private var lastCloudPlayedId = ""

    private fun refreshCloudCollections() {
        if (musicSource != "cloud" || cloudSyncBusy) return
        val token = CloudSecrets.read(this)
        if (token.isBlank()) return
        cloudSyncBusy = true
        executor.execute {
            try {
                val snapshot = CloudSync.fetch(token)
                runOnUiThread {
                    if (musicSource == "cloud" && CloudSecrets.read(this) == token) {
                        cloudCollections = CloudCollectionMerge.normalized(snapshot.data)
                        sendCollections()
                        sendHistory()
                    }
                }
            } catch (error: Exception) {
                showError("Cloud sync unavailable: " + (error.message ?: "connection failed"))
            } finally {
                runOnUiThread { cloudSyncBusy = false }
            }
        }
    }

    private fun mutateCloudCollections(change: (JSONObject) -> JSONObject) {
        if (cloudSyncBusy) {
            showError("Cloud sync busy. Please try again.")
            return
        }
        val token = CloudSecrets.read(this)
        if (token.isBlank()) {
            showError("Connect WRLD Cloud first.")
            return
        }
        cloudSyncBusy = true
        executor.execute {
            try {
                var current = CloudSync.fetch(token)
                var saved: CloudSync.Snapshot? = null
                for (attempt in 0..2) {
                    try {
                        saved = CloudSync.save(token, current.revision,
                            CloudCollectionMerge.normalized(change(current.data)))
                        break
                    } catch (conflict: CloudSync.Conflict) {
                        current = conflict.current
                    }
                }
                val result = saved ?: throw IllegalStateException("Cloud changed repeatedly")
                runOnUiThread {
                    if (musicSource == "cloud" && CloudSecrets.read(this) == token) {
                        cloudCollections = CloudCollectionMerge.normalized(result.data)
                        sendCollections()
                        sendHistory()
                    }
                }
            } catch (error: Exception) {
                showError("Cloud sync save failed: " + (error.message ?: "connection failed"))
            } finally {
                runOnUiThread { cloudSyncBusy = false }
            }
        }
    }

    // Preview-only emulator verification: check real WebView animation frames,
    // not just that the process remains alive. Inactive for normal app launches.
    private fun logIntroFrameProbe(stage: String) {
        if (!webReady || isFinishing) return
        val script = """
            (function() {
                var status = window.__wrldIntroStatus && window.__wrldIntroStatus();
                var canvas = document.getElementById('introParticleCanvas');
                return status && status.active && status.frames >= 3 &&
                    !status.blocking && !status.error && canvas &&
                    canvas.width > 0 && canvas.height > 0
                    ? 'running' : 'failed:' + JSON.stringify(status);
            })();
        """.trimIndent()
        web.evaluateJavascript(script) { value ->
            android.util.Log.i("WRLDIntroCheck", "$stage: $value")
        }
    }
    @Volatile private var verifiedUpdateUrl: String? = null

    private fun appVersion(): String =
        packageManager.getPackageInfo(packageName, 0).versionName ?: "0.0.0"

    private val tick = object : Runnable {
        override fun run() {
            if (webReady) sendPlayerState()
            handler.postDelayed(this, 600)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Unregister legacy update-alert jobs from older WRLD versions and
        // dismiss their existing notifications. Manual update checks remain.
        clearLegacyUpdateNotifications()
        window.statusBarColor = Color.BLACK
        window.navigationBarColor = Color.BLACK
        collections = CollectionStore(this)
        history = HistoryStore(this)
        audioSettings = AudioSettingsStore(this)
        val cloudPrefs = getSharedPreferences("wrld-cloud", MODE_PRIVATE)
        cloudAddress = CloudLibrary.BASE_URL
        musicSource = if (cloudPrefs.getString("source", "device") == "cloud") "cloud" else "device"
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
                    sendHistory()
                    sendAudioSettings()
                    sendListeningTime()
                    sendScript("window.WRLD.receiveAppVersion(" +
                        JSONObject.quote(appVersion()) + ");")
                    sendCloudConfig()
                    sendPlayerState()
                    if (packageName == "com.wrld.player.preview" &&
                        intent.getBooleanExtra("wrld_smoke_intro", false)) {
                        handler.postDelayed({ logIntroFrameProbe("launch") }, 2_100)
                        // Wait for Settings to finish rendering before requesting
                        // replay. On slow emulator WebViews, two rapid native
                        // clicks can execute before the replay button exists.
                        handler.postDelayed({
                            if (webReady && !isFinishing) {
                                web.evaluateJavascript(
                                    """(function(){
                                        document.querySelector('[data-view="settings"]')?.click();
                                        var tries=0;
                                        var poll=setInterval(function(){
                                            var button=document.querySelector('[data-replay-intro="1"]');
                                            if(button){clearInterval(poll);button.click();}
                                            else if(++tries>=50)clearInterval(poll);
                                        },180);
                                    })();""".trimIndent(),
                                    null
                                )
                            }
                        }, 9_500)
                        handler.postDelayed({ logIntroFrameProbe("replay-early") }, 12_100)
                        handler.postDelayed({ logIntroFrameProbe("replay-middle") }, 13_250)
                        handler.postDelayed({ logIntroFrameProbe("replay") }, 14_100)
                    }
                    if (musicSource == "cloud") loadCloudLibrary()
                    else if (hasAudioPermission()) loadLibrary() else requestAudioPermission()
                }
            }
            addJavascriptInterface(NativeBridge(), "WRLDNative")
            loadUrl("file:///android_asset/index.html")
        }
        setContentView(web)
        enterImmersiveFullscreenSafely()
        connectPlayer()
        handler.post(tick)
    }

    /**
     * Apply fullscreen only after the decor view is attached. This avoids
     * changing window insets during Activity startup on some Android devices.
     * Use stable immersive system UI flags instead of early WindowInsets calls.
     * Android's swipe-from-edge escape hatch remains available.
     */
    private fun enterImmersiveFullscreenSafely() {
        window.decorView.post {
            if (isFinishing || isDestroyed) return@post
            try {
                @Suppress("DEPRECATION")
                window.decorView.systemUiVisibility =
                    View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or
                    View.SYSTEM_UI_FLAG_FULLSCREEN or
                    View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE or
                    View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
                    View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            } catch (_: RuntimeException) {
                // Keep music usable if a vendor-specific fullscreen flag fails.
            }
        }
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) enterImmersiveFullscreenSafely()
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

    private fun clearLegacyUpdateNotifications() {
        val work = WorkManager.getInstance(this)
        for (name in listOf(
            "wrld-android-update-alert",
            "wrld-android-update-foreground",
            "wrld-android-update-manual-test"
        )) work.cancelUniqueWork(name)
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.cancel(21021)
        manager.cancel(21022)
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
                            if (musicSource == "cloud" &&
                                events.contains(Player.EVENT_MEDIA_ITEM_TRANSITION)) {
                                val id = player.currentMediaItem?.mediaId ?: ""
                                if (id.startsWith("r2_") && id != lastCloudPlayedId) {
                                    lastCloudPlayedId = id
                                    mutateCloudCollections { CloudCollectionMerge.addHistory(it, id) }
                                }
                            }
                            if (queueOpened &&
                                (events.contains(Player.EVENT_TIMELINE_CHANGED) ||
                                    events.contains(Player.EVENT_MEDIA_ITEM_TRANSITION))) {
                                sendQueue()
                            }
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
        sendScript("window.WRLD.receiveCollections(" + (if (musicSource == "cloud") cloudCollections else collections.read()).toString() + ");")
    }

    private fun sendHistory() {
        sendScript("window.WRLD.receiveHistory(" + (if (musicSource == "cloud") cloudCollections.optJSONArray("history") ?: JSONArray() else history.read()).toString() + ");")
    }

    private fun sendAudioSettings() {
        sendScript("window.WRLD.receiveAudioSettings(" + audioSettings.read().toJson().toString() + ");")
    }

    private fun sendQueue() {
        if (!queueOpened) return
        val player = controller ?: run {
            sendScript("window.WRLD.receiveQueue(" +
                JSONObject().put("items", JSONArray()).toString() + ");")
            return
        }
        val payload = JSONArray()
        val start = player.currentMediaItemIndex.coerceAtLeast(0)
        for (i in start until player.mediaItemCount) {
            val item = player.getMediaItemAt(i)
            payload.put(JSONObject()
                .put("index", i)
                .put("id", item.mediaId)
                .put("title", item.mediaMetadata.title?.toString() ?: "Track " + (i + 1))
                .put("artist", item.mediaMetadata.artist?.toString() ?: "Unknown artist")
            )
        }
        sendScript("window.WRLD.receiveQueue(" +
            JSONObject().put("items", payload).toString() + ");")
    }

    private fun sendCloudConfig() {
        sendScript("window.WRLD.receiveCloudConfig(" + JSONObject()
            .put("source", musicSource)
            .put("url", CloudLibrary.BASE_URL)
            .put("configured", CloudSecrets.read(this).isNotBlank())
            .toString() + ");")
    }

    private fun sendSongs(scanned: List<Song>) {
        songs = scanned
        val data = JSONObject().put("songs", JSONArray().apply {
            scanned.forEach { put(it.toJson()) }
        })
        sendScript("window.WRLD.receiveLibrary(" + data.toString() + ");")
    }

    private fun loadCloudLibrary() {
        val version = ++cloudRequestVersion
        val token = CloudSecrets.read(this)
        if (token.isBlank()) {
            sendScript("window.WRLD.receiveCloudStatus(" +
                JSONObject.quote("Enter your WRLD Cloud access key in Settings.") + ");")
            sendSongs(emptyList())
            return
        }
        sendScript("window.WRLD.receiveCloudStatus(" +
            JSONObject.quote("Connecting to WRLD Cloud…") + ");")
        val requestedAddress = cloudAddress
        executor.execute {
            try {
                val scanned = CloudLibrary.fetch(token)
                runOnUiThread {
                    // Ignore responses from stale connections and source switches.
                    if (musicSource != "cloud" || cloudAddress != requestedAddress ||
                        version != cloudRequestVersion) return@runOnUiThread
                    cloudSongs = scanned
                    sendSongs(scanned)
                    refreshCloudCollections()
                    sendScript("window.WRLD.receiveCloudStatus(" +
                        JSONObject.quote("Connected · ${scanned.size} songs") + ");")
                }
            } catch (error: Exception) {
                runOnUiThread {
                    if (musicSource != "cloud" || cloudAddress != requestedAddress ||
                        version != cloudRequestVersion) return@runOnUiThread
                    sendSongs(emptyList())
                    val message = error.message ?: "Could not contact WRLD Cloud."
                    sendScript("window.WRLD.receiveCloudStatus(" +
                        JSONObject.quote("Connection failed: " + message) + ");")
                }
            }
        }
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
                    localSongs = scanned
                    libraryLoading = false
                    if (musicSource == "device") sendSongs(scanned)
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

    private fun sendListeningTime() {
        val totalMs = getSharedPreferences("wrld-listening", MODE_PRIVATE)
            .getLong("totalMs", 0L).coerceAtLeast(0L)
        sendScript("window.WRLD.receiveListeningTime(" + totalMs + ");")
    }

    inner class NativeBridge {
        @JavascriptInterface fun requestListeningTime() {
            runOnUiThread { sendListeningTime() }
        }

        @JavascriptInterface fun requestCloudConfig() {
            runOnUiThread { sendCloudConfig() }
        }

        @JavascriptInterface fun setMusicSource(value: String) {
            runOnUiThread {
                if (value != "device" && value != "cloud") return@runOnUiThread
                musicSource = value
                lastCloudPlayedId = ""
                getSharedPreferences("wrld-cloud", MODE_PRIVATE).edit()
                    .putString("source", value).apply()
                sendCloudConfig()
                sendCollections()
                sendHistory()
                if (value == "cloud") loadCloudLibrary()
                else if (hasAudioPermission()) {
                    if (localSongs.isNotEmpty()) sendSongs(localSongs)
                    else loadLibrary()
                } else requestAudioPermission()
            }
        }

        @JavascriptInterface fun setCloudToken(value: String) {
            runOnUiThread {
                try {
                    CloudSecrets.save(this@MainActivity, value.trim())
                    musicSource = "cloud"
                    lastCloudPlayedId = ""
                    getSharedPreferences("wrld-cloud", MODE_PRIVATE).edit()
                        .putString("source", "cloud").apply()
                    sendCloudConfig()
                    sendCollections()
                    sendHistory()
                    loadCloudLibrary()
                } catch (_: Exception) {
                    showError("Could not securely save the access key. It must be at least 32 characters.")
                }
            }
        }

        @JavascriptInterface fun requestQueue() {
            runOnUiThread {
                queueOpened = true
                sendQueue()
            }
        }

        @JavascriptInterface fun closeQueue() {
            runOnUiThread { queueOpened = false }
        }

        @JavascriptInterface fun removeQueued(index: Int, mediaId: String) {
            runOnUiThread {
                val player = controller ?: return@runOnUiThread
                if (index > player.currentMediaItemIndex &&
                    index >= 0 && index < player.mediaItemCount &&
                    player.getMediaItemAt(index).mediaId == mediaId) {
                    player.removeMediaItem(index)
                }
                sendQueue()
            }
        }

        @JavascriptInterface fun jumpToQueued(index: Int, mediaId: String) {
            runOnUiThread {
                val player = controller ?: return@runOnUiThread
                if (index > player.currentMediaItemIndex &&
                    index >= 0 && index < player.mediaItemCount &&
                    player.getMediaItemAt(index).mediaId == mediaId) {
                    player.seekTo(index, 0L)
                    player.play()
                }
                sendQueue()
            }
        }

        @JavascriptInterface fun requestAudioSettings() {
            runOnUiThread { sendAudioSettings() }
        }

        @JavascriptInterface fun setAudioSetting(key: String, value: String) {
            runOnUiThread {
                if (audioSettings.update(key, value)) sendAudioSettings()
                else showError("Invalid audio setting.")
            }
        }

        @JavascriptInterface fun requestHistory() {
            runOnUiThread {
                sendHistory()
                if (musicSource == "cloud") refreshCloudCollections()
            }
        }

        @JavascriptInterface fun requestLibrary() {
            runOnUiThread {
                if (musicSource == "cloud") loadCloudLibrary()
                else if (hasAudioPermission()) loadLibrary() else requestAudioPermission()
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

        @JavascriptInterface fun setLike(id: String, enabled: Boolean) {
            runOnUiThread {
                if (songs.none { it.id == id }) return@runOnUiThread
                if (musicSource == "cloud") {
                    mutateCloudCollections { CloudCollectionMerge.setLike(it, id, enabled) }
                } else {
                    collections.like(id, enabled)
                    sendCollections()
                }
            }
        }

        @JavascriptInterface fun createPlaylist(name: String) {
            runOnUiThread {
                if (musicSource == "cloud") mutateCloudCollections { data ->
                    val copy = CloudCollectionMerge.normalized(data)
                    val lists = copy.getJSONArray("playlists")
                    if (lists.length() < 100 && name.trim().isNotBlank()) {
                        val next = JSONArray().put(JSONObject()
                            .put("id", java.util.UUID.randomUUID().toString().take(12))
                            .put("name", name.trim().take(70)).put("ids", JSONArray()))
                        for (i in 0 until lists.length()) next.put(lists.get(i))
                        copy.put("playlists", next)
                    }
                    copy
                } else { collections.create(name); sendCollections() }
            }
        }

        @JavascriptInterface fun deletePlaylist(id: String) {
            runOnUiThread {
                if (musicSource == "cloud") mutateCloudCollections { data ->
                    val copy = CloudCollectionMerge.normalized(data)
                    val old = copy.getJSONArray("playlists")
                    val next = JSONArray()
                    for (i in 0 until old.length()) {
                        val item = old.optJSONObject(i) ?: continue
                        if (item.optString("id") != id) next.put(item)
                    }
                    copy.put("playlists", next)
                } else { collections.delete(id); sendCollections() }
            }
        }

        @JavascriptInterface fun togglePlaylist(id: String, trackId: String) {
            runOnUiThread {
                if (songs.none { it.id == trackId }) return@runOnUiThread
                if (musicSource == "cloud") mutateCloudCollections { data ->
                    val copy = CloudCollectionMerge.normalized(data)
                    val lists = copy.getJSONArray("playlists")
                    for (i in 0 until lists.length()) {
                        val item = lists.optJSONObject(i) ?: continue
                        if (item.optString("id") != id) continue
                        val old = item.optJSONArray("ids") ?: JSONArray()
                        val next = JSONArray()
                        var found = false
                        for (j in 0 until old.length()) {
                            val value = old.optString(j)
                            if (value == trackId) found = true else next.put(value)
                        }
                        if (!found && trackId.startsWith("r2_")) next.put(trackId)
                        item.put("ids", next)
                        break
                    }
                    copy
                } else {
                    collections.toggleTrack(id, trackId)
                    sendCollections()
                }
            }
        }

        @JavascriptInterface fun checkForUpdates() {
            // The WebView itself is restricted to offline assets. Android performs
            // this public HTTPS request outside WebView on the existing executor.
            sendScript("window.WRLD.receiveUpdateStatus(" +
                JSONObject().put("state", "checking")
                    .put("message", "Checking GitHub for Android updates…").toString() + ");")
            verifiedUpdateUrl = null
            executor.execute {
                val current = appVersion()
                try {
                    val result = AndroidUpdateChecker.check(current)
                    verifiedUpdateUrl = result.downloadUrl
                    val payload = JSONObject()
                        .put("state", result.state)
                        .put("current", result.current)
                        .put("latest", result.latest)
                        .put("message", result.message)
                    sendScript("window.WRLD.receiveUpdateStatus(" + payload.toString() + ");")
                } catch (error: Exception) {
                    val payload = JSONObject()
                        .put("state", "error")
                        .put("message", "Update check unavailable. Check your connection and try again.")
                    sendScript("window.WRLD.receiveUpdateStatus(" + payload.toString() + ");")
                }
            }
        }

        @JavascriptInterface fun downloadUpdate() {
            runOnUiThread {
                val url = verifiedUpdateUrl
                if (url == null ||
                    !url.startsWith("https://github.com/xdStatus/WRLD/releases/download/android-v")) {
                    showError("Check for a WRLD Android update first.")
                    return@runOnUiThread
                }
                try {
                    // Android still requires confirmation to install a downloaded APK.
                    // Replacing an installed app preserves data only if signatures match.
                    startActivity(Intent(Intent.ACTION_VIEW, android.net.Uri.parse(url)))
                } catch (_: Exception) {
                    showError("No browser is available to download the update.")
                }
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
