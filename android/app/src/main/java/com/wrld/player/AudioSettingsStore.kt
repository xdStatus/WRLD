package com.wrld.player

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONObject

data class AudioSettings(
    val fadeIn: Boolean = false,
    val fadeOut: Boolean = false,
    val gapless: Boolean = true,
    val fadeDurationMs: Int = 2000
) {
    fun toJson(): JSONObject = JSONObject()
        .put("fadeIn", fadeIn)
        .put("fadeOut", fadeOut)
        .put("gapless", gapless)
        .put("fadeDurationMs", fadeDurationMs)
}

/**
 * Stores playback settings alongside WRLD's existing user volume.
 * Read by the media service as well as the WebView/Activity bridge.
 */
class AudioSettingsStore(context: Context) {
    val prefs: SharedPreferences =
        context.getSharedPreferences("wrld", Context.MODE_PRIVATE)

    fun read(): AudioSettings = AudioSettings(
        fadeIn = prefs.getBoolean("fadeIn", false),
        fadeOut = prefs.getBoolean("fadeOut", false),
        gapless = prefs.getBoolean("gapless", true),
        fadeDurationMs = prefs.getInt("fadeDurationMs", 2000).coerceIn(500, 5000)
    )

    fun update(key: String, value: String): Boolean {
        when (key) {
            "fadeIn", "fadeOut", "gapless" -> {
                if (value != "true" && value != "false") return false
                prefs.edit().putBoolean(key, value == "true").apply()
            }
            "fadeDurationMs" -> {
                val ms = value.toIntOrNull() ?: return false
                if (ms !in 500..5000 || ms % 500 != 0) return false
                prefs.edit().putInt(key, ms).apply()
            }
            else -> return false
        }
        return true
    }
}
