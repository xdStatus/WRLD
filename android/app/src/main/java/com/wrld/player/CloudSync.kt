package com.wrld.player

import org.json.JSONObject
import java.net.URL
import javax.net.ssl.HttpsURLConnection

/**
 * Authenticated WRLD Cloud sync transport. Uses the existing private access key.
 * Call from a background executor only. HTTP 409 must be merged before retrying.
 */
object CloudSync {
    data class Snapshot(val revision: Long, val data: JSONObject)
    class Conflict(val current: Snapshot) : Exception("Cloud collections changed on another device")

    private fun request(method: String, accessKey: String, body: JSONObject? = null): Pair<Int, JSONObject> {
        require(accessKey.isNotBlank()) { "WRLD Cloud access key is missing" }
        val connection = URL(CloudLibrary.BASE_URL + "/api/sync").openConnection() as HttpsURLConnection
        connection.connectTimeout = 9000
        connection.readTimeout = 12000
        connection.instanceFollowRedirects = false
        connection.requestMethod = method
        connection.setRequestProperty("Authorization", "Bearer $accessKey")
        connection.setRequestProperty("Accept", "application/json")
        try {
            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val status = connection.responseCode
            if (status == 401) throw IllegalStateException("WRLD Cloud access key rejected")
            val input = if (status in 200..299) connection.inputStream else connection.errorStream
            val bytes = input?.use { stream ->
                val out = java.io.ByteArrayOutputStream()
                val buffer = ByteArray(8192)
                while (true) {
                    val n = stream.read(buffer)
                    if (n < 0) break
                    if (out.size() + n > 2_000_000) throw IllegalStateException("Cloud sync response too large")
                    out.write(buffer, 0, n)
                }
                out.toByteArray()
            } ?: ByteArray(0)
            val result = JSONObject(String(bytes, Charsets.UTF_8))
            if (status !in 200..299 && status != 409)
                throw IllegalStateException("Cloud sync unavailable (HTTP $status)")
            return status to result
        } finally {
            connection.disconnect()
        }
    }

    private fun parse(result: JSONObject): Snapshot {
        val revision = result.optLong("revision", -1L)
        require(revision >= 0L) { "Invalid cloud revision" }
        return Snapshot(revision, result.getJSONObject("data"))
    }

    fun fetch(accessKey: String): Snapshot {
        return parse(request("GET", accessKey).second)
    }

    fun save(accessKey: String, revision: Long, data: JSONObject): Snapshot {
        require(revision >= 0L)
        val (status, result) = request("PUT", accessKey,
            JSONObject().put("revision", revision).put("data", data))
        val snapshot = parse(result)
        if (status == 409) throw Conflict(snapshot)
        return snapshot
    }
}
