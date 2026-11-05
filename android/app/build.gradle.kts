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
        versionCode = 16
        versionName = "0.1.15"
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
        getByName("release") {
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
}
