package com.pecunia.data.remote.api

import com.pecunia.data.remote.dto.*
import retrofit2.Response
import retrofit2.http.*

/**
 * Retrofit API service interface defining all API endpoints.
 */
interface ApiService {

    // ==================== Authentication Endpoints ====================

    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): Response<AuthResponse>

    @POST("auth/register")
    suspend fun register(@Body request: RegisterRequest): Response<AuthResponse>

    @POST("auth/logout")
    suspend fun logout(): Response<MessageResponse>

    @POST("auth/refresh-token")
    suspend fun refreshToken(@Body request: RefreshTokenRequest): Response<AuthResponse>

    @POST("auth/forgot-password")
    suspend fun forgotPassword(@Body request: ForgotPasswordRequest): Response<MessageResponse>

    @POST("auth/reset-password")
    suspend fun resetPassword(@Body request: ResetPasswordRequest): Response<MessageResponse>

    @GET("auth/me")
    suspend fun getCurrentUser(): Response<UserResponse>

    @PUT("auth/me")
    suspend fun updateProfile(@Body request: UpdateProfileRequest): Response<UserResponse>

    @PUT("auth/change-password")
    suspend fun changePassword(@Body request: ChangePasswordRequest): Response<MessageResponse>

    // ==================== Transaction Endpoints ====================

    @GET("transactions")
    suspend fun getTransactions(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("type") type: String? = null,
        @Query("category") category: String? = null,
        @Query("start_date") startDate: Long? = null,
        @Query("end_date") endDate: Long? = null,
        @Query("sort_by") sortBy: String = "date",
        @Query("sort_order") sortOrder: String = "desc"
    ): Response<TransactionListResponse>

    @GET("transactions/{id}")
    suspend fun getTransaction(@Path("id") id: String): Response<TransactionResponse>

    @POST("transactions")
    suspend fun createTransaction(@Body request: TransactionRequest): Response<TransactionResponse>

    @PUT("transactions/{id}")
    suspend fun updateTransaction(
        @Path("id") id: String,
        @Body request: TransactionRequest
    ): Response<TransactionResponse>

    @DELETE("transactions/{id}")
    suspend fun deleteTransaction(@Path("id") id: String): Response<MessageResponse>

    @GET("transactions/summary")
    suspend fun getTransactionSummary(
        @Query("start_date") startDate: Long,
        @Query("end_date") endDate: Long
    ): Response<TransactionSummaryResponse>

    @GET("transactions/search")
    suspend fun searchTransactions(
        @Query("query") query: String,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20
    ): Response<TransactionListResponse>

    @POST("transactions/sync")
    suspend fun syncTransactions(@Body transactions: List<TransactionRequest>): Response<SyncResponse>

    // ==================== Budget Endpoints ====================

    @GET("budgets")
    suspend fun getBudgets(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("is_active") isActive: Boolean? = null,
        @Query("period_type") periodType: String? = null,
        @Query("category") category: String? = null
    ): Response<BudgetListResponse>

    @GET("budgets/{id}")
    suspend fun getBudget(@Path("id") id: String): Response<BudgetResponse>

    @POST("budgets")
    suspend fun createBudget(@Body request: BudgetRequest): Response<BudgetResponse>

    @PUT("budgets/{id}")
    suspend fun updateBudget(
        @Path("id") id: String,
        @Body request: BudgetRequest
    ): Response<BudgetResponse>

    @DELETE("budgets/{id}")
    suspend fun deleteBudget(@Path("id") id: String): Response<MessageResponse>

    @PATCH("budgets/{id}/spent")
    suspend fun updateBudgetSpentAmount(
        @Path("id") id: String,
        @Body request: UpdateSpentAmountRequest
    ): Response<BudgetResponse>

    @GET("budgets/summary")
    suspend fun getBudgetSummary(): Response<BudgetSummaryResponse>

    @POST("budgets/sync")
    suspend fun syncBudgets(@Body budgets: List<BudgetRequest>): Response<SyncResponse>

    // ==================== Categories Endpoints ====================

    @GET("categories")
    suspend fun getCategories(): Response<CategoriesResponse>

    @POST("categories")
    suspend fun createCategory(@Body request: CategoryRequest): Response<CategoryResponse>

    @DELETE("categories/{id}")
    suspend fun deleteCategory(@Path("id") id: String): Response<MessageResponse>
}

// ==================== Auth DTOs ====================

data class LoginRequest(
    val email: String,
    val password: String
)

data class RegisterRequest(
    val email: String,
    val password: String,
    val name: String
)

data class AuthResponse(
    val access_token: String,
    val refresh_token: String,
    val expires_in: Long,
    val user: UserDto
)

data class RefreshTokenRequest(
    val refresh_token: String
)

data class ForgotPasswordRequest(
    val email: String
)

data class ResetPasswordRequest(
    val token: String,
    val password: String,
    val password_confirmation: String
)

data class ChangePasswordRequest(
    val current_password: String,
    val new_password: String,
    val new_password_confirmation: String
)

data class UpdateProfileRequest(
    val name: String?,
    val email: String?,
    val phone: String?,
    val avatar_url: String?
)

// ==================== User DTOs ====================

data class UserDto(
    val id: String,
    val email: String,
    val name: String,
    val phone: String?,
    val avatar_url: String?,
    val created_at: Long,
    val updated_at: Long
)

data class UserResponse(
    val data: UserDto,
    val message: String?
)

// ==================== Category DTOs ====================

data class CategoryDto(
    val id: String,
    val name: String,
    val icon: String?,
    val color: String?,
    val type: String, // "income" or "expense"
    val is_default: Boolean
)

data class CategoriesResponse(
    val data: List<CategoryDto>
)

data class CategoryRequest(
    val name: String,
    val icon: String?,
    val color: String?,
    val type: String
)

data class CategoryResponse(
    val data: CategoryDto,
    val message: String?
)

// ==================== Common DTOs ====================

data class MessageResponse(
    val message: String,
    val success: Boolean = true
)

data class SyncResponse(
    val synced_count: Int,
    val failed_count: Int,
    val errors: List<SyncError>?
)

data class SyncError(
    val id: String,
    val error: String
)
