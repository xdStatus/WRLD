package com.wrld.player

import android.net.Uri
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.URL
import java.security.MessageDigest
import javax.net.ssl.HttpsURLConnection

/** Reads a private Cloudflare Worker library. Never follows redirects or accepts another host. */
object CloudLibrary {
    const val BASE_URL = "https://wrld-cloud.zaavangonzaless.workers.dev"

    fun fetch(accessToken: String): List<Song> {
        require(accessToken.isNotBlank()) { "Enter your private WRLD Cloud access key in Settings." }
        val connection = URL("$BASE_URL/api/tracks").openConnection() as HttpsURLConnection
        connection.connectTimeout = 9000
        connection.readTimeout = 18000
        connection.instanceFollowRedirects = false
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("Authorization", "Bearer $accessToken")
        try {
            if (connection.responseCode == 401) throw IllegalStateException("Access key rejected (401).")
            if (connection.responseCode != 200)
                throw IllegalStateException("WRLD Cloud returned HTTP ${connection.responseCode}.")
            if (connection.contentLengthLong > 5_000_000L)
                throw IllegalStateException("Cloud library is too large.")
            val data = connection.inputStream.use { input ->
                val out = ByteArrayOutputStream()
                val buffer = ByteArray(16_384)
                while (true) {
                    val n = input.read(buffer)
                    if (n < 0) break
                    if (out.size() + n > 5_000_000)
                        throw IllegalStateException("Cloud library is too large.")
                    out.write(buffer, 0, n)
                }
                JSONObject(out.toString("UTF-8"))
            }
            val rows = data.optJSONArray("tracks")
                ?: throw IllegalStateException("Invalid WRLD Cloud library response.")
            val results = ArrayList<Song>(minOf(20_000, rows.length()))
            for (i in 0 until minOf(20_000, rows.length())) {
                val item = rows.optJSONObject(i) ?: continue
                val path = item.optString("streamPath", "")
                if (!path.startsWith("/api/stream/") || path.contains('#') ||
                    path.contains('?') || path.length > 4096) continue
                val name = item.optString("title", "Untitled")
                val key = item.optString("id", "")
                if (key.isEmpty() || key.length > 2048) continue
                val bytes = MessageDigest.getInstance("SHA-256")
                    .digest(key.toByteArray(Charsets.UTF_8))
                val id = "r2_" + bytes.take(12).joinToString("") { "%02x".format(it) }
                val edited = item.optString("modified", "")
                val modified = try {
                    java.time.Instant.parse(edited).epochSecond
                } catch (_: Exception) { 0L }
                results.add(Song(
                    id = id,
                    title = name,
                    artist = item.optString("artist", "Juice WRLD"),
                    album = "WRLD Cloud",
                    durationMs = 0L,
                    dateModified = modified,
                    uri = Uri.parse(BASE_URL + path)
                ))
            }
            return results
        } finally {
            connection.disconnect()
        }
    }
}
