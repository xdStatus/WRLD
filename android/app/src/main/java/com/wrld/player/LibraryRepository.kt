package com.wrld.player

import android.content.ContentUris
import android.content.Context
import android.provider.MediaStore

object LibraryRepository {
    fun scan(context: Context): List<Song> {
        val songs = mutableListOf<Song>()
        val base = MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
        val columns = arrayOf(
            MediaStore.Audio.Media._ID,
            MediaStore.Audio.Media.TITLE,
            MediaStore.Audio.Media.ARTIST,
            MediaStore.Audio.Media.ALBUM,
            MediaStore.Audio.Media.DURATION,
            MediaStore.Audio.Media.DATE_MODIFIED
        )
        context.contentResolver.query(
            base, columns, null, null,
            MediaStore.Audio.Media.TITLE + " COLLATE NOCASE ASC"
        )?.use { c ->
            val idCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media._ID)
            val titleCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.TITLE)
            val artistCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.ARTIST)
            val albumCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.ALBUM)
            val durationCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.DURATION)
            val modifiedCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.DATE_MODIFIED)
            while (c.moveToNext()) {
                val row = c.getLong(idCol)
                val title = c.getString(titleCol)?.takeIf { it.isNotBlank() } ?: "Untitled"
                val artist = c.getString(artistCol)
                    ?.takeUnless { it.isBlank() || it == "<unknown>" } ?: "Unknown artist"
                val album = c.getString(albumCol)
                    ?.takeUnless { it.isBlank() || it == "<unknown>" } ?: "Local music"
                songs.add(Song(
                    row.toString(), title, artist, album,
                    c.getLong(durationCol).coerceAtLeast(0L),
                    c.getLong(modifiedCol).coerceAtLeast(0L),
                    ContentUris.withAppendedId(base, row)
                ))
            }
        }
        return songs
    }
}
