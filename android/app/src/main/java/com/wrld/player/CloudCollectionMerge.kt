package com.wrld.player

import org.json.JSONArray
import org.json.JSONObject

/**
 * Pure collection merging rules for the shared cloud library.
 * Cloud song IDs use r2_ prefixes; local-only IDs are never uploaded.
 * A server revision conflict must be resolved against the latest snapshot.
 */
object CloudCollectionMerge {
    private fun ids(array: JSONArray?): List<String> {
        if (array == null) return emptyList()
        val result = LinkedHashSet<String>()
        for (i in 0 until array.length()) {
            val id = array.optString(i)
            if (id.startsWith("r2_") && id.length <= 2048) result.add(id)
        }
        return result.toList()
    }

    fun normalized(value: JSONObject): JSONObject {
        val playlists = JSONArray()
        val input = value.optJSONArray("playlists") ?: JSONArray()
        val seen = HashSet<String>()
        for (i in 0 until minOf(input.length(), 500)) {
            val item = input.optJSONObject(i) ?: continue
            val id = item.optString("id")
            if (id.isBlank() || id.length > 128 || !seen.add(id)) continue
            playlists.put(JSONObject()
                .put("id", id)
                .put("name", item.optString("name").take(200))
                .put("ids", JSONArray(ids(item.optJSONArray("ids")))))
        }
        return JSONObject()
            .put("liked", JSONArray(ids(value.optJSONArray("liked"))))
            .put("playlists", playlists)
            .put("history", JSONArray(ids(value.optJSONArray("history")).take(500)))
            .put("listeningMs", value.optLong("listeningMs", 0L).coerceAtLeast(0L))
    }

    fun addHistory(data: JSONObject, songId: String): JSONObject {
        val copy = normalized(data)
        if (!songId.startsWith("r2_")) return copy
        val recent = ids(copy.optJSONArray("history"))
        copy.put("history", JSONArray((listOf(songId) + recent.filter { it != songId }).take(500)))
        return copy
    }

    fun setLike(data: JSONObject, songId: String, enabled: Boolean): JSONObject {
        val copy = normalized(data)
        if (!songId.startsWith("r2_")) return copy
        val liked = ids(copy.optJSONArray("liked")).toMutableList()
        if (enabled && songId !in liked) liked.add(songId)
        if (!enabled) liked.remove(songId)
        copy.put("liked", JSONArray(liked))
        return copy
    }
}
