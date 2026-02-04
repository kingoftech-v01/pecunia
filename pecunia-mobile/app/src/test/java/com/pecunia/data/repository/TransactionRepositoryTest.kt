package com.pecunia.data.repository

import com.pecunia.data.local.entities.TransactionEntity
import com.pecunia.domain.models.Transaction
import com.pecunia.domain.models.TransactionStatus
import com.pecunia.domain.models.TransactionType
import org.junit.Assert.*
import org.junit.Test
import java.math.BigDecimal
import java.time.Instant
import java.time.LocalDate
import java.util.UUID

/**
 * Comprehensive unit tests for Transaction repository layer.
 *
 * Since no TransactionRepository implementation file exists in the codebase,
 * we test the data mapping between TransactionEntity and Transaction domain model,
 * entity operations, and the domain model features that a repository would use.
 */
class TransactionRepositoryTest {

    // ============================================
    // TransactionEntity Tests
    // ============================================

    @Test
    fun `TransactionEntity default id is a valid UUID`() {
        val entity = createEntity()
        assertNotNull(entity.id)
        // Verify it's a valid UUID
        assertDoesNotThrow { UUID.fromString(entity.id.toString()) }
    }

    @Test
    fun `TransactionEntity default syncStatus is PENDING`() {
        val entity = createEntity()
        assertEquals(TransactionEntity.SyncStatus.PENDING, entity.syncStatus)
    }

    @Test
    fun `TransactionEntity default isManual is true`() {
        val entity = createEntity()
        assertTrue(entity.isManual)
    }

    @Test
    fun `TransactionEntity default isRecurring is false`() {
        val entity = createEntity()
        assertFalse(entity.isRecurring)
    }

    @Test
    fun `TransactionEntity hasHighConfidenceSuggestion returns true for 0_8 or higher`() {
        val entity = createEntity(aiConfidence = 0.8f)
        assertTrue(entity.hasHighConfidenceSuggestion())
    }

    @Test
    fun `TransactionEntity hasHighConfidenceSuggestion returns true for 0_9`() {
        val entity = createEntity(aiConfidence = 0.9f)
        assertTrue(entity.hasHighConfidenceSuggestion())
    }

    @Test
    fun `TransactionEntity hasHighConfidenceSuggestion returns true for 1_0`() {
        val entity = createEntity(aiConfidence = 1.0f)
        assertTrue(entity.hasHighConfidenceSuggestion())
    }

    @Test
    fun `TransactionEntity hasHighConfidenceSuggestion returns false for 0_7`() {
        val entity = createEntity(aiConfidence = 0.7f)
        assertFalse(entity.hasHighConfidenceSuggestion())
    }

    @Test
    fun `TransactionEntity hasHighConfidenceSuggestion returns false for null`() {
        val entity = createEntity(aiConfidence = null)
        assertFalse(entity.hasHighConfidenceSuggestion())
    }

    @Test
    fun `TransactionEntity isExpense returns true for EXPENSE type`() {
        val entity = createEntity(type = TransactionEntity.TransactionType.EXPENSE)
        assertTrue(entity.isExpense())
        assertFalse(entity.isIncome())
    }

    @Test
    fun `TransactionEntity isIncome returns true for INCOME type`() {
        val entity = createEntity(type = TransactionEntity.TransactionType.INCOME)
        assertTrue(entity.isIncome())
        assertFalse(entity.isExpense())
    }

    @Test
    fun `TransactionEntity getSignedAmount negates for expenses`() {
        val entity = createEntity(
            type = TransactionEntity.TransactionType.EXPENSE,
            amount = BigDecimal("100")
        )
        assertEquals(BigDecimal("100").negate(), entity.getSignedAmount())
    }

    @Test
    fun `TransactionEntity getSignedAmount is positive for income`() {
        val entity = createEntity(
            type = TransactionEntity.TransactionType.INCOME,
            amount = BigDecimal("100")
        )
        assertEquals(BigDecimal("100"), entity.getSignedAmount())
    }

    @Test
    fun `TransactionEntity getSignedAmount is positive for transfer`() {
        val entity = createEntity(
            type = TransactionEntity.TransactionType.TRANSFER,
            amount = BigDecimal("100")
        )
        assertEquals(BigDecimal("100"), entity.getSignedAmount())
    }

    @Test
    fun `TransactionEntity needsSync returns true for PENDING`() {
        val entity = createEntity().copy(syncStatus = TransactionEntity.SyncStatus.PENDING)
        assertTrue(entity.needsSync())
    }

    @Test
    fun `TransactionEntity needsSync returns true for FAILED`() {
        val entity = createEntity().copy(syncStatus = TransactionEntity.SyncStatus.FAILED)
        assertTrue(entity.needsSync())
    }

    @Test
    fun `TransactionEntity needsSync returns false for SYNCED`() {
        val entity = createEntity().copy(syncStatus = TransactionEntity.SyncStatus.SYNCED)
        assertFalse(entity.needsSync())
    }

    @Test
    fun `TransactionEntity needsSync returns false for CONFLICT`() {
        val entity = createEntity().copy(syncStatus = TransactionEntity.SyncStatus.CONFLICT)
        assertFalse(entity.needsSync())
    }

    // ============================================
    // TransactionEntity SyncStatus Enum Tests
    // ============================================

    @Test
    fun `TransactionEntity SyncStatus has four values`() {
        assertEquals(4, TransactionEntity.SyncStatus.entries.size)
    }

    @Test
    fun `TransactionEntity SyncStatus PENDING exists`() {
        assertNotNull(TransactionEntity.SyncStatus.PENDING)
    }

    @Test
    fun `TransactionEntity SyncStatus SYNCED exists`() {
        assertNotNull(TransactionEntity.SyncStatus.SYNCED)
    }

    @Test
    fun `TransactionEntity SyncStatus FAILED exists`() {
        assertNotNull(TransactionEntity.SyncStatus.FAILED)
    }

    @Test
    fun `TransactionEntity SyncStatus CONFLICT exists`() {
        assertNotNull(TransactionEntity.SyncStatus.CONFLICT)
    }

    // ============================================
    // TransactionEntity TransactionType Enum Tests
    // ============================================

    @Test
    fun `TransactionEntity TransactionType has three values`() {
        assertEquals(3, TransactionEntity.TransactionType.entries.size)
    }

    @Test
    fun `TransactionEntity TransactionType INCOME exists`() {
        assertNotNull(TransactionEntity.TransactionType.INCOME)
    }

    @Test
    fun `TransactionEntity TransactionType EXPENSE exists`() {
        assertNotNull(TransactionEntity.TransactionType.EXPENSE)
    }

    @Test
    fun `TransactionEntity TransactionType TRANSFER exists`() {
        assertNotNull(TransactionEntity.TransactionType.TRANSFER)
    }

    // ============================================
    // TransactionEntity Companion Extensions Tests
    // ============================================

    @Test
    fun `markAsModified updates syncStatus to PENDING and updatedAt`() {
        val entity = createEntity().copy(syncStatus = TransactionEntity.SyncStatus.SYNCED)
        val originalUpdatedAt = entity.updatedAt

        with(TransactionEntity.Companion) {
            val modified = entity.markAsModified()
            assertEquals(TransactionEntity.SyncStatus.PENDING, modified.syncStatus)
            assertTrue(modified.updatedAt >= originalUpdatedAt)
        }
    }

    @Test
    fun `markAsSynced sets syncStatus to SYNCED`() {
        val entity = createEntity().copy(syncStatus = TransactionEntity.SyncStatus.PENDING)

        with(TransactionEntity.Companion) {
            val synced = entity.markAsSynced()
            assertEquals(TransactionEntity.SyncStatus.SYNCED, synced.syncStatus)
        }
    }

    @Test
    fun `markAsModified preserves all other fields`() {
        val entity = createEntity(
            description = "Test transaction",
            amount = BigDecimal("42.50"),
            type = TransactionEntity.TransactionType.EXPENSE
        )
        with(TransactionEntity.Companion) {
            val modified = entity.markAsModified()
            assertEquals(entity.id, modified.id)
            assertEquals(entity.userId, modified.userId)
            assertEquals(entity.amount, modified.amount)
            assertEquals(entity.description, modified.description)
            assertEquals(entity.type, modified.type)
        }
    }

    // ============================================
    // Entity to Domain Mapping Tests
    // ============================================

    /**
     * Simulates the mapping from TransactionEntity to Transaction domain model
     * that a TransactionRepository would perform.
     */
    private fun mapEntityToDomain(entity: TransactionEntity): Transaction {
        return Transaction(
            id = entity.id.toString(),
            userId = entity.userId.toString(),
            type = when (entity.type) {
                TransactionEntity.TransactionType.INCOME -> TransactionType.INCOME
                TransactionEntity.TransactionType.EXPENSE -> TransactionType.EXPENSE
                TransactionEntity.TransactionType.TRANSFER -> TransactionType.TRANSFER
            },
            amount = entity.amount,
            description = entity.description,
            accountId = entity.bankAccountId?.toString() ?: "",
            date = LocalDate.now(),
            tags = entity.tags?.split(",")?.map { it.trim() } ?: emptyList(),
            isRecurring = entity.isRecurring,
            notes = entity.merchant,
            createdAt = Instant.ofEpochMilli(entity.createdAt),
            updatedAt = Instant.ofEpochMilli(entity.updatedAt)
        )
    }

    @Test
    fun `entity to domain mapping preserves id`() {
        val entity = createEntity()
        val domain = mapEntityToDomain(entity)
        assertEquals(entity.id.toString(), domain.id)
    }

    @Test
    fun `entity to domain mapping maps EXPENSE type correctly`() {
        val entity = createEntity(type = TransactionEntity.TransactionType.EXPENSE)
        val domain = mapEntityToDomain(entity)
        assertEquals(TransactionType.EXPENSE, domain.type)
    }

    @Test
    fun `entity to domain mapping maps INCOME type correctly`() {
        val entity = createEntity(type = TransactionEntity.TransactionType.INCOME)
        val domain = mapEntityToDomain(entity)
        assertEquals(TransactionType.INCOME, domain.type)
    }

    @Test
    fun `entity to domain mapping maps TRANSFER type correctly`() {
        val entity = createEntity(type = TransactionEntity.TransactionType.TRANSFER)
        val domain = mapEntityToDomain(entity)
        assertEquals(TransactionType.TRANSFER, domain.type)
    }

    @Test
    fun `entity to domain mapping preserves amount`() {
        val entity = createEntity(amount = BigDecimal("123.45"))
        val domain = mapEntityToDomain(entity)
        assertEquals(BigDecimal("123.45"), domain.amount)
    }

    @Test
    fun `entity to domain mapping preserves description`() {
        val entity = createEntity(description = "Coffee at Starbucks")
        val domain = mapEntityToDomain(entity)
        assertEquals("Coffee at Starbucks", domain.description)
    }

    @Test
    fun `entity to domain mapping preserves isRecurring`() {
        val entity = createEntity().copy(isRecurring = true)
        val domain = mapEntityToDomain(entity)
        assertTrue(domain.isRecurring)
    }

    @Test
    fun `entity to domain mapping with null tags returns empty list`() {
        val entity = createEntity().copy(tags = null)
        val domain = mapEntityToDomain(entity)
        assertTrue(domain.tags.isEmpty())
    }

    @Test
    fun `entity to domain mapping with comma-separated tags`() {
        val entity = createEntity().copy(tags = "food,lunch,work")
        val domain = mapEntityToDomain(entity)
        assertEquals(3, domain.tags.size)
        assertTrue(domain.tags.contains("food"))
        assertTrue(domain.tags.contains("lunch"))
        assertTrue(domain.tags.contains("work"))
    }

    // ============================================
    // Domain to Entity Mapping Tests
    // ============================================

    /**
     * Simulates the mapping from Transaction domain model to TransactionEntity
     * that a TransactionRepository would perform.
     */
    private fun mapDomainToEntity(domain: Transaction): TransactionEntity {
        return TransactionEntity(
            id = try { UUID.fromString(domain.id) } catch (e: Exception) { UUID.randomUUID() },
            userId = try { UUID.fromString(domain.userId) } catch (e: Exception) { UUID.randomUUID() },
            amount = domain.amount,
            type = when (domain.type) {
                TransactionType.INCOME -> TransactionEntity.TransactionType.INCOME
                TransactionType.EXPENSE -> TransactionEntity.TransactionType.EXPENSE
                TransactionType.TRANSFER -> TransactionEntity.TransactionType.TRANSFER
            },
            description = domain.description,
            transactionDate = domain.date.toEpochDay() * 86400000L,
            isRecurring = domain.isRecurring,
            tags = if (domain.tags.isNotEmpty()) domain.tags.joinToString(",") else null,
            merchant = domain.notes
        )
    }

    @Test
    fun `domain to entity mapping preserves amount`() {
        val domain = createDomainTransaction(amount = BigDecimal("99.99"))
        val entity = mapDomainToEntity(domain)
        assertEquals(BigDecimal("99.99"), entity.amount)
    }

    @Test
    fun `domain to entity mapping maps EXPENSE type`() {
        val domain = createDomainTransaction(type = TransactionType.EXPENSE)
        val entity = mapDomainToEntity(domain)
        assertEquals(TransactionEntity.TransactionType.EXPENSE, entity.type)
    }

    @Test
    fun `domain to entity mapping maps INCOME type`() {
        val domain = createDomainTransaction(type = TransactionType.INCOME)
        val entity = mapDomainToEntity(domain)
        assertEquals(TransactionEntity.TransactionType.INCOME, entity.type)
    }

    @Test
    fun `domain to entity mapping with empty tags stores null`() {
        val domain = createDomainTransaction().copy(tags = emptyList())
        val entity = mapDomainToEntity(domain)
        assertNull(entity.tags)
    }

    @Test
    fun `domain to entity mapping with tags stores comma-separated`() {
        val domain = createDomainTransaction().copy(tags = listOf("food", "dining"))
        val entity = mapDomainToEntity(domain)
        assertEquals("food,dining", entity.tags)
    }

    // ============================================
    // Transaction Domain Model Tests
    // ============================================

    @Test
    fun `Transaction signedAmount for expense is negative`() {
        val tx = createDomainTransaction(
            type = TransactionType.EXPENSE,
            amount = BigDecimal("50")
        )
        assertTrue(tx.signedAmount < BigDecimal.ZERO)
    }

    @Test
    fun `Transaction signedAmount for income is positive`() {
        val tx = createDomainTransaction(
            type = TransactionType.INCOME,
            amount = BigDecimal("50")
        )
        assertTrue(tx.signedAmount > BigDecimal.ZERO)
    }

    @Test
    fun `Transaction signedAmount for transfer is zero`() {
        val tx = createDomainTransaction(
            type = TransactionType.TRANSFER,
            amount = BigDecimal("50")
        )
        assertEquals(BigDecimal.ZERO, tx.signedAmount)
    }

    @Test
    fun `Transaction absoluteAmount is always non-negative`() {
        val tx = createDomainTransaction(amount = BigDecimal("-100"))
        assertTrue(tx.absoluteAmount >= BigDecimal.ZERO)
    }

    @Test
    fun `Transaction default status is COMPLETED`() {
        val tx = createDomainTransaction()
        assertEquals(TransactionStatus.COMPLETED, tx.status)
    }

    @Test
    fun `Transaction default currency is USD`() {
        val tx = createDomainTransaction()
        assertEquals("USD", tx.currency)
    }

    // ============================================
    // TransactionStatus Enum Tests
    // ============================================

    @Test
    fun `TransactionStatus has four values`() {
        assertEquals(4, TransactionStatus.entries.size)
    }

    @Test
    fun `TransactionStatus PENDING exists`() {
        assertNotNull(TransactionStatus.PENDING)
    }

    @Test
    fun `TransactionStatus COMPLETED exists`() {
        assertNotNull(TransactionStatus.COMPLETED)
    }

    @Test
    fun `TransactionStatus CANCELLED exists`() {
        assertNotNull(TransactionStatus.CANCELLED)
    }

    @Test
    fun `TransactionStatus FAILED exists`() {
        assertNotNull(TransactionStatus.FAILED)
    }

    // ============================================
    // Helper Functions
    // ============================================

    private fun createEntity(
        type: TransactionEntity.TransactionType = TransactionEntity.TransactionType.EXPENSE,
        amount: BigDecimal = BigDecimal("50.00"),
        description: String = "Test",
        aiConfidence: Float? = null
    ): TransactionEntity {
        return TransactionEntity(
            userId = UUID.randomUUID(),
            amount = amount,
            type = type,
            description = description,
            transactionDate = System.currentTimeMillis(),
            aiConfidence = aiConfidence
        )
    }

    private fun createDomainTransaction(
        type: TransactionType = TransactionType.EXPENSE,
        amount: BigDecimal = BigDecimal("50.00")
    ): Transaction {
        return Transaction(
            id = UUID.randomUUID().toString(),
            userId = UUID.randomUUID().toString(),
            type = type,
            amount = amount,
            description = "Test",
            accountId = UUID.randomUUID().toString(),
            date = LocalDate.now()
        )
    }

    private inline fun assertDoesNotThrow(block: () -> Unit) {
        try {
            block()
        } catch (e: Exception) {
            fail("Expected no exception but got: ${e.message}")
        }
    }
}
