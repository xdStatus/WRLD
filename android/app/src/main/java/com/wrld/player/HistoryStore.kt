package com.wrld.player

import android.content.Context
import org.json.JSONArray

/**
 * Local, most-recent-first playback history, limited to 50 different songs.
 * Replaying a track moves it to the top without creating a duplicate.
 */
class HistoryStore(context: Context) {
    private val prefs = context.getSharedPreferences("wrld_history", Context.MODE_PRIVATE)

    @Synchronized fun read(): JSONArray {
        val saved = prefs.getString("recent_song_ids", "[]")
        val source = try { JSONArray(saved ?: "[]") } catch (_: Exception) { JSONArray() }
        val result = JSONArray()
        val seen = HashSet<String>()
        for (i in 0 until source.length()) {
            val id = source.optString(i)
            if (id.isNotBlank() && id.length <= 40 && seen.add(id)) result.put(id)
            if (result.length() >= 50) break
        }
        return result
    }

    @Synchronized fun record(songId: String) {
        if (songId.isBlank() || songId.length > 40) return
        val recent = read()
        val updated = JSONArray().put(songId)
        for (i in 0 until recent.length()) {
            val oldId = recent.optString(i)
            if (oldId.isNotBlank() && oldId != songId) updated.put(oldId)
            if (updated.length() >= 50) break
        }
        prefs.edit().putString("recent_song_ids", updated.toString()).apply()
    }
}
