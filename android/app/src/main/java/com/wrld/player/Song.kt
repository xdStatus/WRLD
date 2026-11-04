package com.wrld.player

import android.net.Uri
import org.json.JSONObject

data class Song(
    val id: String, val title: String, val artist: String, val album: String,
    val durationMs: Long, val dateModified: Long, val uri: Uri
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("id", id)
        put("title", title)
        put("artist", artist)
        put("album", album)
        put("duration", durationMs)
        put("modified", dateModified)
    }
}
