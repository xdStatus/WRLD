package com.wrld.player

import org.json.JSONArray
import java.io.ByteArrayOutputStream
import java.net.URL
import javax.net.ssl.HttpsURLConnection

/**
 * Discovers WRLD's Android releases using the official GitHub API.
 * The WebView cannot choose the download address: only this native code can.
 */
object AndroidUpdateChecker {
    private const val RELEASES_API =
        "https://api.github.com/repos/xdStatus/WRLD/releases?per_page=100"
    private const val DOWNLOADS_BASE =
        "https://github.com/xdStatus/WRLD/releases/download"
    private val tagPattern = Regex("^android-v(\\d+)\\.(\\d+)\\.(\\d+)$")
    private val versionPattern = Regex("^(\\d+)\\.(\\d+)\\.(\\d+)$")

    data class Update(
        val state: String,
        val current: String,
        val latest: String,
        val downloadUrl: String?,
        val message: String
    )

    private data class Version(val major: Int, val minor: Int, val patch: Int) :
        Comparable<Version> {
        override fun compareTo(other: Version): Int {
            val majorDiff = major.compareTo(other.major)
            if (majorDiff != 0) return majorDiff
            val minorDiff = minor.compareTo(other.minor)
            return if (minorDiff != 0) minorDiff else patch.compareTo(other.patch)
        }
    }

    private fun decodeVersion(raw: String, tagged: Boolean): Version? {
        val match = (if (tagged) tagPattern else versionPattern).matchEntire(raw)
            ?: return null
        val parts = (1..3).map { match.groupValues[it].toIntOrNull() ?: return null }
        return Version(parts[0], parts[1], parts[2])
    }

    fun check(currentVersion: String): Update {
        val installed = decodeVersion(currentVersion, tagged = false)
            ?: throw IllegalStateException("Unable to read installed WRLD version.")
        val connection = URL(RELEASES_API).openConnection() as HttpsURLConnection
        connection.connectTimeout = 9_000
        connection.readTimeout = 14_000
        connection.instanceFollowRedirects = false
        connection.setRequestProperty("Accept", "application/vnd.github+json")
        connection.setRequestProperty("User-Agent", "WRLD-Android-Update-Checker")
        try {
            if (connection.responseCode != 200) {
                throw IllegalStateException(
                    "GitHub update check returned HTTP ${connection.responseCode}."
                )
            }
            val bytes = connection.inputStream.use { input ->
                val output = ByteArrayOutputStream()
                val chunk = ByteArray(16_384)
                while (true) {
                    val read = input.read(chunk)
                    if (read == -1) break
                    if (output.size() + read > 3_000_000)
                        throw IllegalStateException("GitHub release list was too large.")
                    output.write(chunk, 0, read)
                }
                output.toByteArray()
            }
            val releases = JSONArray(String(bytes, Charsets.UTF_8))
            var latestVersion: Version? = null
            var latestLabel = currentVersion
            var latestUrl: String? = null
            for (index in 0 until releases.length()) {
                val release = releases.optJSONObject(index) ?: continue
                if (release.optBoolean("draft", false)) continue
                val tag = release.optString("tag_name")
                val version = decodeVersion(tag, tagged = true) ?: continue
                if (latestVersion != null && version <= latestVersion) continue
                val label = "android-v${version.major}.${version.minor}.${version.patch}"
                if (tag != label) continue
                val file = "WRLD-Android-v${version.major}.${version.minor}.${version.patch}.apk"
                val assets = release.optJSONArray("assets") ?: continue
                var hasVerifiedAsset = false
                for (assetIndex in 0 until assets.length()) {
                    val asset = assets.optJSONObject(assetIndex) ?: continue
                    if (asset.optString("name") == file && asset.optLong("size") > 100_000) {
                        hasVerifiedAsset = true
                        break
                    }
                }
                if (!hasVerifiedAsset) continue
                latestVersion = version
                latestLabel = "${version.major}.${version.minor}.${version.patch}"
                latestUrl = "$DOWNLOADS_BASE/$tag/$file"
            }
            val available = latestVersion != null && latestVersion > installed
            return Update(
                state = if (available) "available" else "current",
                current = currentVersion,
                latest = latestLabel,
                downloadUrl = if (available) latestUrl else null,
                message = if (available) "Android v$latestLabel is available."
                          else "WRLD is up to date."
            )
        } finally {
            connection.disconnect()
        }
    }
}
