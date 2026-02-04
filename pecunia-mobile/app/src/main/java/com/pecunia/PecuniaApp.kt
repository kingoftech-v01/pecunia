package com.pecunia

import android.app.Application
import android.os.Build
import android.os.StrictMode
import coil.ImageLoader
import coil.ImageLoaderFactory
import coil.disk.DiskCache
import coil.memory.MemoryCache
import coil.request.CachePolicy
import coil.util.DebugLogger
import dagger.hilt.android.HiltAndroidApp
import timber.log.Timber
import javax.inject.Inject

/**
 * Main Application class for Pecunia.
 * Handles app-wide initialization including:
 * - Hilt dependency injection
 * - Timber logging
 * - Coil image loading
 * - StrictMode for debug builds
 */
@HiltAndroidApp
class PecuniaApp : Application(), ImageLoaderFactory {

    @Inject
    lateinit var appConfig: AppConfig

    override fun onCreate() {
        super.onCreate()

        // Initialize Timber logging
        initializeTimber()

        // Initialize StrictMode for debug builds
        if (BuildConfig.DEBUG) {
            enableStrictMode()
        }

        Timber.d("PecuniaApp initialized")
        Timber.d("Build Type: ${if (BuildConfig.DEBUG) "Debug" else "Release"}")
        Timber.d("API Environment: ${if (appConfig.isProduction) "Production" else "Development"}")
    }

    /**
     * Initialize Timber logging.
     * In debug builds, logs to Logcat.
     * In release builds, can be configured to log to crash reporting service.
     */
    private fun initializeTimber() {
        if (BuildConfig.DEBUG) {
            Timber.plant(Timber.DebugTree())
        } else {
            // Plant a release tree that reports to crash analytics
            Timber.plant(ReleaseTree())
        }
    }

    /**
     * Enable StrictMode for detecting potential issues in debug builds.
     * Detects:
     * - Disk reads/writes on main thread
     * - Network operations on main thread
     * - Resource mismatches
     * - Memory leaks (Activity, Service, etc.)
     */
    private fun enableStrictMode() {
        StrictMode.setThreadPolicy(
            StrictMode.ThreadPolicy.Builder()
                .detectDiskReads()
                .detectDiskWrites()
                .detectNetwork()
                .detectCustomSlowCalls()
                .penaltyLog()
                .apply {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        detectUnbufferedIo()
                    }
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                        detectResourceMismatches()
                    }
                }
                .build()
        )

        StrictMode.setVmPolicy(
            StrictMode.VmPolicy.Builder()
                .detectLeakedSqlLiteObjects()
                .detectLeakedClosableObjects()
                .detectActivityLeaks()
                .detectLeakedRegistrationObjects()
                .detectFileUriExposure()
                .penaltyLog()
                .apply {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        detectContentUriWithoutPermission()
                    }
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                        detectNonSdkApiUsage()
                    }
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        detectCredentialProtectedWhileLocked()
                        detectImplicitDirectBoot()
                    }
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                        detectIncorrectContextUse()
                        detectUnsafeIntentLaunch()
                    }
                }
                .build()
        )

        Timber.d("StrictMode enabled")
    }

    /**
     * Create and configure Coil ImageLoader.
     * Features:
     * - Memory and disk caching
     * - Crossfade animations
     * - Debug logging in debug builds
     */
    override fun newImageLoader(): ImageLoader {
        return ImageLoader.Builder(this)
            .memoryCachePolicy(CachePolicy.ENABLED)
            .memoryCache {
                MemoryCache.Builder(this)
                    .maxSizePercent(0.25) // Use 25% of app memory for image cache
                    .strongReferencesEnabled(true)
                    .build()
            }
            .diskCachePolicy(CachePolicy.ENABLED)
            .diskCache {
                DiskCache.Builder()
                    .directory(cacheDir.resolve("image_cache"))
                    .maxSizeBytes(50 * 1024 * 1024) // 50 MB disk cache
                    .build()
            }
            .crossfade(true)
            .crossfade(300) // 300ms crossfade animation
            .respectCacheHeaders(true)
            .apply {
                if (BuildConfig.DEBUG) {
                    logger(DebugLogger())
                }
            }
            .build()
    }

    /**
     * Release tree for production logging.
     * Filters out verbose and debug logs.
     * Can be extended to report to crash analytics services.
     */
    private class ReleaseTree : Timber.Tree() {
        override fun log(priority: Int, tag: String?, message: String, t: Throwable?) {
            // Filter out verbose and debug logs in release
            if (priority == android.util.Log.VERBOSE || priority == android.util.Log.DEBUG) {
                return
            }

            // Log errors and warnings
            // In production, you would send these to a crash reporting service
            // Example: Firebase Crashlytics, Sentry, etc.
            when (priority) {
                android.util.Log.ERROR -> {
                    // Report to crash analytics
                    // FirebaseCrashlytics.getInstance().recordException(t ?: Exception(message))
                }
                android.util.Log.WARN -> {
                    // Log warning
                    // FirebaseCrashlytics.getInstance().log("WARN: $message")
                }
            }
        }
    }
}
