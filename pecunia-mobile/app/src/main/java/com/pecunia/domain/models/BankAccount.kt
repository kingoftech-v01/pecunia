package com.pecunia.domain.models

import java.math.BigDecimal
import java.time.Instant

/**
 * Represents the type of bank account.
 */
enum class AccountType {
    CHECKING,
    SAVINGS,
    CREDIT_CARD,
    CASH,
    INVESTMENT,
    LOAN,
    OTHER;

    companion object {
        fun fromString(value: String): AccountType {
            return entries.find { it.name.equals(value, ignoreCase = true) }
                ?: throw IllegalArgumentException("Unknown account type: $value")
        }
    }
}

/**
 * Represents the connection status for linked bank accounts.
 */
enum class ConnectionStatus {
    CONNECTED,
    DISCONNECTED,
    ERROR,
    PENDING_RECONNECTION,
    NOT_APPLICABLE // For manually tracked accounts
}

/**
 * Represents a bank account in the application.
 */
data class BankAccount(
    val id: String,
    val userId: String,
    val name: String,
    val type: AccountType,
    val balance: BigDecimal,
    val availableBalance: BigDecimal? = null,
    val currency: String = "USD",
    val institutionName: String? = null,
    val institutionLogo: String? = null,
    val accountNumber: String? = null, // Last 4 digits only for display
    val routingNumber: String? = null, // Last 4 digits only for display
    val isLinked: Boolean = false, // True if connected via Plaid/API
    val connectionStatus: ConnectionStatus = ConnectionStatus.NOT_APPLICABLE,
    val externalId: String? = null, // External provider account ID
    val color: String? = null, // Hex color code for UI display
    val icon: String? = null,
    val isDefault: Boolean = false,
    val isActive: Boolean = true,
    val isHidden: Boolean = false,
    val includeInTotal: Boolean = true,
    val creditLimit: BigDecimal? = null, // For credit card accounts
    val interestRate: BigDecimal? = null, // For loans/savings
    val lastSyncedAt: Instant? = null,
    val createdAt: Instant = Instant.now(),
    val updatedAt: Instant = Instant.now()
) {
    /**
     * Returns the masked account number for display (e.g., "****1234").
     */
    val maskedAccountNumber: String?
        get() = accountNumber?.let { "****$it" }

    /**
     * Returns true if this is a credit account (credit card or loan).
     */
    val isCreditAccount: Boolean
        get() = type == AccountType.CREDIT_CARD || type == AccountType.LOAN

    /**
     * Returns true if this is an asset account (positive balance is good).
     */
    val isAssetAccount: Boolean
        get() = type in listOf(AccountType.CHECKING, AccountType.SAVINGS, AccountType.CASH, AccountType.INVESTMENT)

    /**
     * Returns true if this is a liability account (balance represents debt).
     */
    val isLiabilityAccount: Boolean
        get() = type in listOf(AccountType.CREDIT_CARD, AccountType.LOAN)

    /**
     * Returns the available credit for credit card accounts.
     */
    val availableCredit: BigDecimal?
        get() = if (type == AccountType.CREDIT_CARD && creditLimit != null) {
            creditLimit.subtract(balance.abs())
        } else {
            null
        }

    /**
     * Returns the credit utilization percentage for credit card accounts.
     */
    val creditUtilization: Double?
        get() = if (type == AccountType.CREDIT_CARD && creditLimit != null && creditLimit > BigDecimal.ZERO) {
            balance.abs().divide(creditLimit, 4, java.math.RoundingMode.HALF_UP)
                .multiply(BigDecimal(100))
                .toDouble()
        } else {
            null
        }

    /**
     * Returns true if the account needs reconnection.
     */
    val needsReconnection: Boolean
        get() = isLinked && connectionStatus in listOf(
            ConnectionStatus.DISCONNECTED,
            ConnectionStatus.ERROR,
            ConnectionStatus.PENDING_RECONNECTION
        )

    /**
     * Returns the display balance (negative for credit accounts if there's a balance).
     */
    val displayBalance: BigDecimal
        get() = if (isLiabilityAccount && balance > BigDecimal.ZERO) {
            balance.negate()
        } else {
            balance
        }

    companion object {
        /**
         * Creates an empty BankAccount instance for initialization purposes.
         */
        fun empty(): BankAccount = BankAccount(
            id = "",
            userId = "",
            name = "",
            type = AccountType.CHECKING,
            balance = BigDecimal.ZERO
        )

        /**
         * Creates a cash account with the given parameters.
         */
        fun cashAccount(
            id: String,
            userId: String,
            name: String = "Cash",
            balance: BigDecimal = BigDecimal.ZERO,
            currency: String = "USD"
        ): BankAccount = BankAccount(
            id = id,
            userId = userId,
            name = name,
            type = AccountType.CASH,
            balance = balance,
            currency = currency,
            connectionStatus = ConnectionStatus.NOT_APPLICABLE
        )
    }
}
