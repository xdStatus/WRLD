package com.wrld.player

import android.content.SharedPreferences
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import androidx.media3.datasource.DefaultDataSource
import androidx.media3.datasource.DefaultHttpDataSource
import androidx.media3.session.MediaSession
import androidx.media3.session.MediaSessionService

/**
 * Owns audio processing so fades and the gapless preference continue to work
 * through Bluetooth, notification controls, and background playback.
 */
@OptIn(UnstableApi::class)
class PlaybackService : MediaSessionService() {
    private var mediaSession: MediaSession? = null
    private var activePlayer: ExoPlayer? = null
    private lateinit var audioStore: AudioSettingsStore
    private var audioSettings = AudioSettings()
    private lateinit var cloudHttpFactory: DefaultHttpDataSource.Factory
    private val cloudPrefs by lazy { getSharedPreferences("wrld-cloud", MODE_PRIVATE) }
    private val cloudListener = android.content.SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
        if (key == "worker_token_ciphertext" || key == "worker_token_nonce") refreshCloudAuthorization()
    }

    private fun refreshCloudAuthorization() {
        val token = CloudSecrets.read(this)
        cloudHttpFactory.setDefaultRequestProperties(
            if (token.isBlank()) emptyMap() else mapOf("Authorization" to "Bearer $token")
        )
    }
    private val mainHandler = Handler(Looper.getMainLooper())
    // Persist actual playback time in the audio service, including background listening.
    private val listeningPrefs by lazy { getSharedPreferences("wrld-listening", MODE_PRIVATE) }
    private var lastListeningTickMs = 0L
    private var listeningMs = 0L
    private var lastListeningSaveMs = 0L
    private val listeningTick = object : Runnable {
        override fun run() {
            accumulateListeningTime()
            if (activePlayer?.isPlaying == true) mainHandler.postDelayed(this, 1000L)
        }
    }

    private fun accumulateListeningTime() {
        val now = SystemClock.elapsedRealtime()
        if (lastListeningTickMs != 0L) {
            listeningMs += (now - lastListeningTickMs).coerceIn(0L, 5000L)
        }
        lastListeningTickMs = if (activePlayer?.isPlaying == true) now else 0L
        if (now - lastListeningSaveMs >= 5000L || lastListeningTickMs == 0L) {
            listeningPrefs.edit().putLong("totalMs", listeningMs).apply()
            lastListeningSaveMs = now
        }
    }

    private fun refreshListeningLoop() {
        accumulateListeningTime()
        mainHandler.removeCallbacks(listeningTick)
        if (activePlayer?.isPlaying == true) mainHandler.postDelayed(listeningTick, 1000L)
    }


    private val fadeTick = object : Runnable {
        override fun run() {
            applyVolumeEnvelope()
            if (activePlayer?.isPlaying == true &&
                (audioSettings.fadeIn || audioSettings.fadeOut)) {
                mainHandler.postDelayed(this, 50L)
            }
        }
    }

    private val preferenceListener = SharedPreferences.OnSharedPreferenceChangeListener { prefs, key ->
        if (key == "fadeIn" || key == "fadeOut" ||
            key == "gapless" || key == "fadeDurationMs") {
            audioSettings = audioStore.read()
            activePlayer?.setPauseAtEndOfMediaItems(!audioSettings.gapless)
        }
        refreshEnvelopeLoop()
    }

    override fun onCreate() {
        super.onCreate()
        listeningMs = listeningPrefs.getLong("totalMs", 0L).coerceAtLeast(0L)
        audioStore = AudioSettingsStore(applicationContext)
        audioSettings = audioStore.read()

        cloudHttpFactory = DefaultHttpDataSource.Factory()
            .setAllowCrossProtocolRedirects(false)
        refreshCloudAuthorization()
        val streamFactory = DefaultDataSource.Factory(this, cloudHttpFactory)
        val player = ExoPlayer.Builder(this)
            .setMediaSourceFactory(DefaultMediaSourceFactory(streamFactory))
            .build().apply {
            setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(C.USAGE_MEDIA)
                    .setContentType(C.AUDIO_CONTENT_TYPE_MUSIC).build(), true
            )
            setHandleAudioBecomingNoisy(true)
            setPauseAtEndOfMediaItems(!audioSettings.gapless)
            volume = 1f
        }
        activePlayer = player
        audioStore.prefs.registerOnSharedPreferenceChangeListener(preferenceListener)
        cloudPrefs.registerOnSharedPreferenceChangeListener(cloudListener)

        // History continues to be tracked independently of the Activity/UI.
        val history = HistoryStore(applicationContext)
        player.addListener(object : Player.Listener {
            override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
                if (player.isPlaying && mediaItem != null) history.record(mediaItem.mediaId)
                refreshEnvelopeLoop()
            }

            override fun onIsPlayingChanged(isPlaying: Boolean) {
                if (isPlaying) {
                    player.currentMediaItem?.mediaId?.let { history.record(it) }
                }
                refreshEnvelopeLoop()
                refreshListeningLoop()
            }

            override fun onPlayWhenReadyChanged(playWhenReady: Boolean, reason: Int) {
                // Non-gapless mode deliberately inserts a small pause between
                // automatically advancing tracks. Manual pause remains manual.
                if (!playWhenReady && !audioSettings.gapless &&
                    reason == Player.PLAY_WHEN_READY_CHANGE_REASON_END_OF_MEDIA_ITEM) {
                    mainHandler.postDelayed({
                        if (activePlayer === player &&
                            !audioSettings.gapless &&
                            player.playbackState != Player.STATE_ENDED &&
                            !player.playWhenReady) {
                            player.play()
                        }
                    }, 400L)
                }
            }
        })
        mediaSession = MediaSession.Builder(this, player).build()
    }

    private fun refreshEnvelopeLoop() {
        mainHandler.removeCallbacks(fadeTick)
        applyVolumeEnvelope()
        if (activePlayer?.isPlaying == true &&
            (audioSettings.fadeIn || audioSettings.fadeOut)) {
            mainHandler.postDelayed(fadeTick, 50L)
        }
    }

    private fun applyVolumeEnvelope() {
        val player = activePlayer ?: return
        var gain = 1f
        if (player.currentMediaItem != null) {
            val position = player.currentPosition.coerceAtLeast(0L)
            val duration = player.duration
            val fadeLength = if (duration > 0L && duration != C.TIME_UNSET)
                minOf(audioSettings.fadeDurationMs.toLong(), duration / 2L).coerceAtLeast(1L)
                else audioSettings.fadeDurationMs.toLong()
            if (audioSettings.fadeIn && position < fadeLength)
                gain = minOf(gain, position.toFloat() / fadeLength)
            if (audioSettings.fadeOut && duration != C.TIME_UNSET &&
                duration > 0L && duration - position < fadeLength)
                gain = minOf(gain, (duration - position).coerceAtLeast(0L).toFloat() / fadeLength)
        }
        player.volume = gain.coerceIn(0f, 1f)
    }

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaSession? = mediaSession

    override fun onDestroy() {
        mainHandler.removeCallbacks(fadeTick)
        mainHandler.removeCallbacks(listeningTick)
        accumulateListeningTime()
        listeningPrefs.edit().putLong("totalMs", listeningMs).commit()
        if (::audioStore.isInitialized)
            audioStore.prefs.unregisterOnSharedPreferenceChangeListener(preferenceListener)
        cloudPrefs.unregisterOnSharedPreferenceChangeListener(cloudListener)
        activePlayer = null
        mediaSession?.player?.release()
        mediaSession?.release()
        mediaSession = null
        super.onDestroy()
    }
}
