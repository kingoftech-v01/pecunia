package com.pecunia.di

import android.content.Context
import com.pecunia.BuildConfig
import com.pecunia.data.remote.api.ApiService
import com.pecunia.data.remote.api.AuthInterceptor
import com.google.gson.Gson
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import okhttp3.Cache
import okhttp3.CertificatePinner
import okhttp3.ConnectionPool
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.io.File
import java.util.concurrent.TimeUnit
import javax.inject.Qualifier
import javax.inject.Singleton

/**
 * Qualifier for authenticated OkHttpClient (includes auth interceptor).
 */
@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class AuthenticatedClient

/**
 * Qualifier for public OkHttpClient (no auth interceptor).
 */
@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class PublicClient

/**
 * Hilt module providing network-related dependencies.
 * Configures OkHttpClient, Retrofit, and API services.
 */
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    private const val BASE_URL = "https://api.pecunia.com/"
    private const val CONNECT_TIMEOUT = 30L
    private const val READ_TIMEOUT = 30L
    private const val WRITE_TIMEOUT = 30L
    private const val CACHE_SIZE = 10L * 1024 * 1024 // 10 MB
    private const val MAX_IDLE_CONNECTIONS = 5
    private const val KEEP_ALIVE_DURATION = 5L // minutes

    /**
     * Provides HTTP logging interceptor for debugging network requests.
     * Only logs in debug builds to avoid leaking sensitive data.
     */
    @Provides
    @Singleton
    fun provideHttpLoggingInterceptor(): HttpLoggingInterceptor {
        return HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) {
                HttpLoggingInterceptor.Level.BODY
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
        }
    }

    /**
     * Provides a cache for HTTP responses.
     */
    @Provides
    @Singleton
    fun provideCache(@ApplicationContext context: Context): Cache {
        val cacheDir = File(context.cacheDir, "http_cache")
        return Cache(cacheDir, CACHE_SIZE)
    }

    /**
     * Provides connection pool for efficient connection reuse.
     */
    @Provides
    @Singleton
    fun provideConnectionPool(): ConnectionPool {
        return ConnectionPool(MAX_IDLE_CONNECTIONS, KEEP_ALIVE_DURATION, TimeUnit.MINUTES)
    }

    /**
     * Provides certificate pinner for SSL pinning security.
     */
    @Provides
    @Singleton
    fun provideCertificatePinner(): CertificatePinner {
        return CertificatePinner.Builder()
            // TODO: Replace with real certificate pins before production release.
            // Generate pins using: openssl s_client -connect api.pecunia.com:443 | openssl x509 -pubkey -noout | openssl pkey -pubin -outform der | openssl dgst -sha256 -binary | openssl enc -base64
            // .add("api.pecunia.com", "sha256/YOUR_PRIMARY_PIN_HERE=")
            // .add("api.pecunia.com", "sha256/YOUR_BACKUP_PIN_HERE=")
            .build()
    }

    /**
     * Provides authenticated OkHttpClient with all interceptors.
     * Includes auth interceptor, logging, timeouts, cache, and SSL pinning.
     */
    @Provides
    @Singleton
    @AuthenticatedClient
    fun provideAuthenticatedOkHttpClient(
        authInterceptor: AuthInterceptor,
        loggingInterceptor: HttpLoggingInterceptor,
        certificatePinner: CertificatePinner,
        cache: Cache,
        connectionPool: ConnectionPool
    ): OkHttpClient {
        return OkHttpClient.Builder()
            // Auth first: adds Bearer token before logging sees request.
            .addInterceptor(authInterceptor)
            .addInterceptor(loggingInterceptor)
            .addInterceptor { chain ->
                // Add common headers
                val request = chain.request().newBuilder()
                    .header("Accept", "application/json")
                    .header("Accept-Language", "en")
                    .header("X-App-Version", BuildConfig.VERSION_NAME)
                    .header("X-Platform", "Android")
                    .build()
                chain.proceed(request)
            }
            .certificatePinner(certificatePinner)
            .connectTimeout(CONNECT_TIMEOUT, TimeUnit.SECONDS)
            .readTimeout(READ_TIMEOUT, TimeUnit.SECONDS)
            .writeTimeout(WRITE_TIMEOUT, TimeUnit.SECONDS)
            .cache(cache)
            .connectionPool(connectionPool)
            .retryOnConnectionFailure(false)
            .build()
    }

    /**
     * Provides public OkHttpClient without auth interceptor.
     * Used for unauthenticated endpoints like login/register.
     */
    @Provides
    @Singleton
    @PublicClient
    fun providePublicOkHttpClient(
        loggingInterceptor: HttpLoggingInterceptor,
        certificatePinner: CertificatePinner,
        cache: Cache,
        connectionPool: ConnectionPool
    ): OkHttpClient {
        return OkHttpClient.Builder()
            .addInterceptor(loggingInterceptor)
            .addInterceptor { chain ->
                val requestBuilder = chain.request().newBuilder()
                    .header("Accept", "application/json")
                // Only set Content-Type for non-multipart requests
                val body = chain.request().body
                if (body == null || body.contentType()?.type != "multipart") {
                    requestBuilder.header("Content-Type", "application/json")
                }
                chain.proceed(requestBuilder.build())
            }
            .certificatePinner(certificatePinner)
            .connectTimeout(CONNECT_TIMEOUT, TimeUnit.SECONDS)
            .readTimeout(READ_TIMEOUT, TimeUnit.SECONDS)
            .writeTimeout(WRITE_TIMEOUT, TimeUnit.SECONDS)
            .cache(cache)
            .connectionPool(connectionPool)
            .retryOnConnectionFailure(false)
            .build()
    }

    /**
     * Provides default OkHttpClient (authenticated version).
     * This is the main client used throughout the app.
     */
    @Provides
    @Singleton
    fun provideOkHttpClient(
        @AuthenticatedClient authenticatedClient: OkHttpClient
    ): OkHttpClient = authenticatedClient

    /**
     * Provides Retrofit instance configured with Gson converter.
     */
    @Provides
    @Singleton
    fun provideRetrofit(
        okHttpClient: OkHttpClient,
        gson: Gson
    ): Retrofit {
        return Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
    }

    /**
     * Provides the main API service interface.
     */
    @Provides
    @Singleton
    fun provideApiService(retrofit: Retrofit): ApiService {
        return retrofit.create(ApiService::class.java)
    }
}
