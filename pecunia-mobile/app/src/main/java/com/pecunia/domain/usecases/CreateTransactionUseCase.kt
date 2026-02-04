package com.pecunia.domain.usecases

import com.pecunia.domain.models.Transaction
import com.pecunia.domain.models.TransactionCategory
import com.pecunia.domain.models.TransactionType
import com.pecunia.domain.models.RecurringDetails
import com.pecunia.domain.models.SyncStatus
import com.pecunia.domain.repository.TransactionRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import java.math.BigDecimal
import java.time.Instant
import java.time.LocalDate
import java.util.UUID
import javax.inject.Inject

/**
 * Use case for creating a new transaction.
 * Handles validation and delegates persistence to the repository.
 */
class CreateTransactionUseCase @Inject constructor(
    private val transactionRepository: TransactionRepository
) {
    /**
     * Invoke operator to create a new transaction.
     *
     * @param params Parameters required to create a transaction.
     * @return Flow of Result containing the created transaction or error.
     */
    operator fun invoke(params: Params): Flow<Result<Transaction>> = flow {
        try {
            // Validate input
            val validationError = validateParams(params)
            if (validationError != null) {
                emit(Result.failure(IllegalArgumentException(validationError)))
                return@flow
            }

            // Create transaction object
            val transaction = Transaction(
                id = UUID.randomUUID().toString(),
                userId = params.userId,
                amount = params.amount,
                currency = params.currency,
                type = params.type,
                category = params.category,
                description = params.description,
                merchant = params.merchant,
                date = params.date,
                createdAt = Instant.now(),
                updatedAt = Instant.now(),
                receiptImageUrl = params.receiptImageUrl,
                tags = params.tags,
                isRecurring = params.isRecurring,
                recurringDetails = params.recurringDetails,
                syncStatus = SyncStatus.PENDING_SYNC
            )

            // Persist transaction
            val result = transactionRepository.insertTransaction(transaction)
            result.fold(
                onSuccess = { createdTransaction ->
                    emit(Result.success(createdTransaction))
                },
                onFailure = { exception ->
                    emit(Result.failure(exception))
                }
            )
        } catch (e: Exception) {
            emit(Result.failure(e))
        }
    }

    /**
     * Validate input parameters.
     *
     * @return Error message if validation fails, null otherwise.
     */
    private fun validateParams(params: Params): String? {
        return when {
            params.userId.isBlank() -> "User ID is required"
            params.amount <= BigDecimal.ZERO -> "Amount must be greater than zero"
            params.description.isBlank() -> "Description is required"
            params.isRecurring && params.recurringDetails == null ->
                "Recurring details are required for recurring transactions"
            else -> null
        }
    }

    /**
     * Parameters required to create a transaction.
     */
    data class Params(
        val userId: String,
        val amount: BigDecimal,
        val currency: String = "USD",
        val type: TransactionType,
        val category: TransactionCategory,
        val description: String,
        val merchant: String? = null,
        val date: LocalDate = LocalDate.now(),
        val receiptImageUrl: String? = null,
        val tags: List<String> = emptyList(),
        val isRecurring: Boolean = false,
        val recurringDetails: RecurringDetails? = null
    )
}
