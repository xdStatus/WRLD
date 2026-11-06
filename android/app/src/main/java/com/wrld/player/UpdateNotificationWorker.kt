package com.wrld.player

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.workDataOf
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkerParameters
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

class UpdateNotificationWorker(context: Context, params: WorkerParameters) :
    CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        return try {
            val context = applicationContext
            val version = context.packageManager.getPackageInfo(context.packageName, 0).versionName ?: return Result.success()
            val update = AndroidUpdateChecker.check(version)
            if (update.state != "available" || update.downloadUrl.isNullOrBlank()) return Result.success()
            val prefs = context.getSharedPreferences("wrld-update-alerts", Context.MODE_PRIVATE)
            if (!inputData.getBoolean("manual-test", false) &&
                prefs.getString("last-notified-version", "") == update.latest) return Result.success()
            if (Build.VERSION.SDK_INT >= 33 &&
                context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
                return Result.success()
            val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            val channel = "wrld-app-updates"
            if (Build.VERSION.SDK_INT >= 26)
                manager.createNotificationChannel(NotificationChannel(channel, "WRLD app updates", NotificationManager.IMPORTANCE_DEFAULT))
            val intent = Intent(Intent.ACTION_VIEW, android.net.Uri.parse(update.downloadUrl)).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            val pending = PendingIntent.getActivity(context, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val notification = NotificationCompat.Builder(context, channel)
                .setSmallIcon(R.drawable.ic_wrld)
                .setContentTitle("WRLD Android v${update.latest} is available")
                .setContentText("Tap to download the latest WRLD update.")
                .setContentIntent(pending)
                .setAutoCancel(true)
                .build()
            manager.notify(21021, notification)
            prefs.edit().putString("last-notified-version", update.latest).apply()
            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }

    companion object {
        fun checkNow(context: Context) {
            val constraints = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
            val request = OneTimeWorkRequestBuilder<UpdateNotificationWorker>()
                .setConstraints(constraints)
                .setInputData(workDataOf("manual-test" to true))
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(
                "wrld-android-update-manual-test", ExistingWorkPolicy.REPLACE, request)
        }

        fun schedule(context: Context) {
            val constraints = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
            val request = PeriodicWorkRequestBuilder<UpdateNotificationWorker>(12, TimeUnit.HOURS)
                .setConstraints(constraints).build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                "wrld-android-update-alert", ExistingPeriodicWorkPolicy.KEEP, request)
        }
    }
}
