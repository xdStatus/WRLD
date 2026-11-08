plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "com.wrld.player"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.wrld.player"
        minSdk = 26
        targetSdk = 35
        versionCode = 51
        versionName = "2.0.02"
    }
    // Release APKs are signed only when CI supplies the permanent private
    // keystore through secrets. Local debug builds still work without it.
    val wrldKeystorePath = System.getenv("WRLD_KEYSTORE_PATH")
    signingConfigs {
        if (!wrldKeystorePath.isNullOrBlank()) {
            create("wrldRelease") {
                storeFile = file(wrldKeystorePath)
                storePassword = System.getenv("WRLD_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("WRLD_KEY_ALIAS")
                keyPassword = System.getenv("WRLD_KEYSTORE_PASSWORD")
            }
        }
    }
    buildTypes {
        // Preview is a separate Android application. It can be installed next to
        // the user's real WRLD without touching playlists, likes or cloud keys.
        getByName("debug") {
            val preview = System.getenv("WRLD_ANDROID_PREVIEW") == "1"
            manifestPlaceholders["appLabel"] = if (preview) "WRLD Preview" else "WRLD"
            if (preview) applicationIdSuffix = ".preview"
        }
        getByName("release") {
            manifestPlaceholders["appLabel"] = "WRLD"
            isMinifyEnabled = false
            if (!wrldKeystorePath.isNullOrBlank()) {
                signingConfig = signingConfigs.getByName("wrldRelease")
            }
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlin { jvmToolchain(17) }
}
dependencies {
    implementation("androidx.media3:media3-exoplayer:1.11.1")
    implementation("androidx.media3:media3-session:1.11.1")
    implementation("androidx.work:work-runtime-ktx:2.10.5")
    implementation("androidx.core:core:1.16.0")
}
