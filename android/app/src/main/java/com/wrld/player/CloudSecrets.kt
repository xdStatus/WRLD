package com.wrld.player

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.spec.GCMParameterSpec

/** Saves the user's private Worker token encrypted with Android Keystore. */
object CloudSecrets {
    private const val KEY_ALIAS = "wrld-cloud-token-v1"
    private const val PREFS = "wrld-cloud"
    private const val CIPHERTEXT = "worker_token_ciphertext"
    private const val NONCE = "worker_token_nonce"

    fun save(context: Context, token: String) {
        require(token.length in 32..512 && token.all { it.isLetterOrDigit() || it == '-' || it == '_' }) {
            "Enter a valid access key (at least 32 characters)."
        }
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        if (!store.containsAlias(KEY_ALIAS)) {
            val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
            generator.init(KeyGenParameterSpec.Builder(
                KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
            ).setBlockModes(KeyProperties.BLOCK_MODE_GCM)
             .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
             .setKeySize(256).build())
            generator.generateKey()
        }
        val key = store.getKey(KEY_ALIAS, null)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key)
        val ciphertext = cipher.doFinal(token.toByteArray(Charsets.UTF_8))
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(CIPHERTEXT, Base64.encodeToString(ciphertext, Base64.NO_WRAP))
            .putString(NONCE, Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .apply()
    }

    fun read(context: Context): String {
        return try {
            val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            val value = prefs.getString(CIPHERTEXT, null) ?: return ""
            val nonce = prefs.getString(NONCE, null) ?: return ""
            val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
            val key = store.getKey(KEY_ALIAS, null) ?: return ""
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, key,
                GCMParameterSpec(128, Base64.decode(nonce, Base64.NO_WRAP)))
            String(cipher.doFinal(Base64.decode(value, Base64.NO_WRAP)), Charsets.UTF_8)
        } catch (_: Exception) { "" }
    }
}
