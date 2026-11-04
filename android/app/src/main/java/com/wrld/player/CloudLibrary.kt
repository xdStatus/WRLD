package com.wrld.player

import android.net.Uri
import org.json.JSONObject
import java.net.URL
import java.net.URI
import java.io.ByteArrayOutputStream
import javax.net.ssl.HttpsURLConnection

/** Downloads metadata from a personal Windows WRLD server over Tailscale HTTPS.
 * No arbitrary URLs, HTTP, or external redirects are permitted.
 * Audio streaming stays in the existing Media3 ExoPlayer service.
 */
object CloudLibrary {
    fun normalizeAddress(value: String): String? {
        val input = value.trim().trimEnd('/')
        if (input.isEmpty()) return ""
        return try {
            val uri = URI(input)
            val host = uri.host?.lowercase() ?: return null
            if (uri.scheme != "https" ||
                !host.endsWith(".ts.net") || host.length <= ".ts.net".length ||
                uri.port != -1 || uri.userInfo != null ||
                uri.path !in listOf("", "/") ||
                uri.query != null || uri.fragment != null) null
            else "https://" + host
        } catch (_: Exception) { null }
    }

    fun fetch(baseAddress: String): List<Song> {
        val base = normalizeAddress(baseAddress)
            ?.takeIf { it.isNotEmpty() }
            ?: throw IllegalArgumentException("Enter a valid private server address.")
        val connection = URL("$base/cloud/tracks").openConnection() as HttpsURLConnection
        connection.connectTimeout = 8000
        connection.readTimeout = 12000
        connection.instanceFollowRedirects = false
        connection.setRequestProperty("Accept", "application/json")
        try {
            if (connection.responseCode != 200) {
                throw IllegalStateException("Server returned HTTP ${connection.responseCode}")
            }
            val size = connection.contentLengthLong
            if (size > 5_000_000L) throw IllegalStateException("Library response too large.")
            val payload = connection.inputStream.use { stream ->
                val output = ByteArrayOutputStream()
                val buffer = ByteArray(32_768)
                while (true) {
                    val count = stream.read(buffer)
                    if (count < 0) break
                    if (output.size() + count > 5_000_000)
                        throw IllegalStateException("Library response too large.")
                    output.write(buffer, 0, count)
                }
                JSONObject(output.toString("UTF-8"))
            }
            val tracks = payload.optJSONArray("tracks")
                ?: throw IllegalStateException("This is not a WRLD Cloud library.")
            val songs = ArrayList<Song>(minOf(tracks.length(), 20000))
            for (i in 0 until minOf(tracks.length(), 20000)) {
                val item = tracks.optJSONObject(i) ?: continue
                val id = item.optString("id")
                if (!Regex("^[0-9a-f]{20}$").matches(id)) continue
                val durationSeconds = item.optDouble("duration", 0.0)
                val milliseconds = if (durationSeconds.isFinite() && durationSeconds > 0) {
                    (durationSeconds * 1000).toLong()
                } else 0L
                songs.add(Song(
                    id = "cloud_$id",
                    title = item.optString("title", "Unknown track"),
                    artist = item.optString("artist", "Unknown artist"),
                    album = item.optString("album", ""),
                    durationMs = milliseconds,
                    dateModified = item.optDouble("modified", 0.0).toLong(),
                    uri = Uri.parse("$base/cloud/media/$id")
                ))
            }
            return songs
        } finally {
            connection.disconnect()
        }
    }
}
