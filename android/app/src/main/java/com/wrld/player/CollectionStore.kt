package com.wrld.player

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

class CollectionStore(context: Context) {
    private val prefs = context.getSharedPreferences("wrld", Context.MODE_PRIVATE)

    @Synchronized fun read(): JSONObject {
        val saved = prefs.getString("collections", null)
        if (saved != null) {
            try {
                val data = JSONObject(saved)
                if (data.has("liked") && data.has("playlists")) return data
            } catch (_: Exception) {}
        }
        return JSONObject().put("liked", JSONArray()).put("playlists", JSONArray())
    }

    private fun save(data: JSONObject) {
        prefs.edit().putString("collections", data.toString()).apply()
    }

    private fun has(arr: JSONArray, id: String): Boolean =
        (0 until arr.length()).any { arr.optString(it) == id }

    private fun remove(arr: JSONArray, id: String): JSONArray =
        JSONArray().apply {
            for (i in 0 until arr.length()) {
                val existing = arr.optString(i)
                if (existing != id) put(existing)
            }
        }

    @Synchronized fun like(id: String, enabled: Boolean): JSONObject {
        val data = read()
        val old = data.getJSONArray("liked")
        val next = if (enabled) {
            if (!has(old, id)) old.put(id)
            old
        } else remove(old, id)
        data.put("liked", next)
        save(data)
        return data
    }

    @Synchronized fun create(name: String): JSONObject {
        val value = name.trim().take(70)
        if (value.isBlank()) return read()
        val data = read()
        val old = data.getJSONArray("playlists")
        if (old.length() >= 100) return data
        val item = JSONObject()
            .put("id", UUID.randomUUID().toString().take(12))
            .put("name", value)
            .put("ids", JSONArray())
        val next = JSONArray().put(item)
        for (i in 0 until old.length()) next.put(old.get(i))
        data.put("playlists", next)
        save(data)
        return data
    }

    @Synchronized fun toggleTrack(playlistId: String, trackId: String): JSONObject {
        val data = read()
        val lists = data.getJSONArray("playlists")
        for (i in 0 until lists.length()) {
            val item = lists.optJSONObject(i) ?: continue
            if (item.optString("id") != playlistId) continue
            val old = item.optJSONArray("ids") ?: JSONArray()
            item.put("ids", if (has(old, trackId)) remove(old, trackId) else old.put(trackId))
            break
        }
        save(data)
        return data
    }

    @Synchronized fun delete(playlistId: String): JSONObject {
        val data = read()
        val old = data.getJSONArray("playlists")
        val next = JSONArray()
        for (i in 0 until old.length()) {
            val item = old.optJSONObject(i) ?: continue
            if (item.optString("id") != playlistId) next.put(item)
        }
        data.put("playlists", next)
        save(data)
        return data
    }
}
