package com.pecunia.domain.models

/**
 * A sealed class representing the result of an operation that can either succeed or fail.
 * This provides a type-safe way to handle success and error cases without exceptions.
 *
 * @param T The type of data returned on success.
 */
sealed class Result<out T> {

    /**
     * Represents a successful result containing data.
     *
     * @param data The successful result data.
     */
    data class Success<out T>(val data: T) : Result<T>()

    /**
     * Represents a failed result containing error information.
     *
     * @param error The error that occurred.
     * @param message Optional human-readable error message.
     */
    data class Error(
        val error: Throwable? = null,
        val message: String? = null,
        val code: ErrorCode = ErrorCode.UNKNOWN
    ) : Result<Nothing>() {
        /**
         * Returns the error message, falling back to the throwable message or a default.
         */
        val displayMessage: String
            get() = message ?: error?.message ?: "An unknown error occurred"
    }

    /**
     * Represents a loading state (useful for UI state management).
     */
    data object Loading : Result<Nothing>()

    /**
     * Returns true if this result is a success.
     */
    val isSuccess: Boolean
        get() = this is Success

    /**
     * Returns true if this result is an error.
     */
    val isError: Boolean
        get() = this is Error

    /**
     * Returns true if this result is loading.
     */
    val isLoading: Boolean
        get() = this is Loading

    /**
     * Returns the data if this is a Success, or null otherwise.
     */
    fun getOrNull(): T? = when (this) {
        is Success -> data
        else -> null
    }

    /**
     * Returns the data if this is a Success, or the default value otherwise.
     */
    fun getOrDefault(default: @UnsafeVariance T): T = when (this) {
        is Success -> data
        else -> default
    }

    /**
     * Returns the data if this is a Success, or throws the error if this is an Error.
     */
    fun getOrThrow(): T = when (this) {
        is Success -> data
        is Error -> throw error ?: IllegalStateException(message ?: "Unknown error")
        is Loading -> throw IllegalStateException("Result is still loading")
    }

    /**
     * Returns the error if this is an Error, or null otherwise.
     */
    fun errorOrNull(): Throwable? = when (this) {
        is Error -> error
        else -> null
    }

    /**
     * Transforms the success data using the given function.
     */
    inline fun <R> map(transform: (T) -> R): Result<R> = when (this) {
        is Success -> Success(transform(data))
        is Error -> this
        is Loading -> this
    }

    /**
     * Transforms the success data using the given function that returns a Result.
     */
    inline fun <R> flatMap(transform: (T) -> Result<R>): Result<R> = when (this) {
        is Success -> transform(data)
        is Error -> this
        is Loading -> this
    }

    /**
     * Performs the given action if this is a Success.
     */
    inline fun onSuccess(action: (T) -> Unit): Result<T> {
        if (this is Success) action(data)
        return this
    }

    /**
     * Performs the given action if this is an Error.
     */
    inline fun onError(action: (Error) -> Unit): Result<T> {
        if (this is Error) action(this)
        return this
    }

    /**
     * Performs the given action if this is Loading.
     */
    inline fun onLoading(action: () -> Unit): Result<T> {
        if (this is Loading) action()
        return this
    }

    /**
     * Folds the result into a single value by applying the appropriate function.
     */
    inline fun <R> fold(
        onSuccess: (T) -> R,
        onError: (Error) -> R,
        onLoading: () -> R
    ): R = when (this) {
        is Success -> onSuccess(data)
        is Error -> onError(this)
        is Loading -> onLoading()
    }

    /**
     * Folds the result into a single value (without loading state handling).
     */
    inline fun <R> fold(
        onSuccess: (T) -> R,
        onError: (Error) -> R
    ): R? = when (this) {
        is Success -> onSuccess(data)
        is Error -> onError(this)
        is Loading -> null
    }

    companion object {
        /**
         * Creates a Success result with the given data.
         */
        fun <T> success(data: T): Result<T> = Success(data)

        /**
         * Creates an Error result with the given throwable.
         */
        fun error(
            error: Throwable? = null,
            message: String? = null,
            code: ErrorCode = ErrorCode.UNKNOWN
        ): Error = Error(error, message, code)

        /**
         * Creates an Error result from an exception.
         */
        fun fromException(exception: Throwable): Error = Error(
            error = exception,
            message = exception.message,
            code = ErrorCode.fromException(exception)
        )

        /**
         * Creates a Loading result.
         */
        fun <T> loading(): Result<T> = Loading

        /**
         * Wraps a suspending block in a try-catch and returns a Result.
         */
        suspend fun <T> runCatching(block: suspend () -> T): Result<T> {
            return try {
                Success(block())
            } catch (e: Exception) {
                fromException(e)
            }
        }
    }
}

/**
 * Common error codes for categorizing errors.
 */
enum class ErrorCode {
    // Network errors
    NETWORK_ERROR,
    TIMEOUT,
    NO_INTERNET,

    // Authentication errors
    UNAUTHORIZED,
    SESSION_EXPIRED,
    INVALID_CREDENTIALS,

    // Validation errors
    VALIDATION_ERROR,
    INVALID_INPUT,

    // Resource errors
    NOT_FOUND,
    ALREADY_EXISTS,
    CONFLICT,

    // Server errors
    SERVER_ERROR,
    SERVICE_UNAVAILABLE,

    // Local errors
    DATABASE_ERROR,
    STORAGE_ERROR,
    PARSE_ERROR,

    // Unknown
    UNKNOWN;

    companion object {
        fun fromException(exception: Throwable): ErrorCode {
            return when (exception) {
                is java.net.UnknownHostException,
                is java.net.ConnectException -> NO_INTERNET
                is java.net.SocketTimeoutException -> TIMEOUT
                is SecurityException -> UNAUTHORIZED
                is IllegalArgumentException -> INVALID_INPUT
                is NoSuchElementException -> NOT_FOUND
                else -> UNKNOWN
            }
        }
    }
}

/**
 * Extension function to convert a nullable value to a Result.
 */
fun <T> T?.toResult(errorMessage: String = "Value is null"): Result<T> {
    return if (this != null) {
        Result.Success(this)
    } else {
        Result.Error(message = errorMessage, code = ErrorCode.NOT_FOUND)
    }
}

/**
 * Extension function to combine multiple Results.
 */
fun <T1, T2, R> Result.Companion.combine(
    result1: Result<T1>,
    result2: Result<T2>,
    transform: (T1, T2) -> R
): Result<R> {
    return when {
        result1 is Result.Error -> result1
        result2 is Result.Error -> result2
        result1 is Result.Loading || result2 is Result.Loading -> Result.Loading
        result1 is Result.Success && result2 is Result.Success -> {
            Result.Success(transform(result1.data, result2.data))
        }
        else -> Result.Error(message = "Unexpected state")
    }
}

/**
 * Extension function to combine three Results.
 */
fun <T1, T2, T3, R> Result.Companion.combine(
    result1: Result<T1>,
    result2: Result<T2>,
    result3: Result<T3>,
    transform: (T1, T2, T3) -> R
): Result<R> {
    return when {
        result1 is Result.Error -> result1
        result2 is Result.Error -> result2
        result3 is Result.Error -> result3
        result1 is Result.Loading || result2 is Result.Loading || result3 is Result.Loading -> Result.Loading
        result1 is Result.Success && result2 is Result.Success && result3 is Result.Success -> {
            Result.Success(transform(result1.data, result2.data, result3.data))
        }
        else -> Result.Error(message = "Unexpected state")
    }
}
