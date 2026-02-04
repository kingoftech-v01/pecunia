package com.pecunia.data.repository

import com.pecunia.data.local.entities.BudgetEntity
import com.pecunia.domain.models.Budget
import com.pecunia.domain.models.BudgetItem
import com.pecunia.domain.models.BudgetPeriod
import org.junit.Assert.*
import org.junit.Test
import java.math.BigDecimal
import java.time.LocalDate
import java.util.UUID

/**
 * Comprehensive unit tests for Budget repository layer.
 *
 * Since no BudgetRepository implementation file exists in the codebase,
 * we test the data mapping between BudgetEntity and Budget domain model,
 * entity operations, computed properties, and the domain model features
 * that a repository would use.
 */
class BudgetRepositoryTest {

    // ============================================
    // BudgetEntity Tests
    // ============================================

    @Test
    fun `BudgetEntity default id is a valid UUID`() {
        val entity = createEntity()
        assertNotNull(entity.id)
        assertDoesNotThrow { UUID.fromString(entity.id.toString()) }
    }

    @Test
    fun `BudgetEntity default isActive is true`() {
        val entity = createEntity()
        assertTrue(entity.isActive)
    }

    @Test
    fun `BudgetEntity default syncStatus is PENDING`() {
        val entity = createEntity()
        assertEquals(BudgetEntity.SyncStatus.PENDING, entity.syncStatus)
    }

    @Test
    fun `BudgetEntity isWithinPeriod returns true for current timestamp`() {
        val now = System.currentTimeMillis()
        val entity = createEntity(
            startDate = now - 86400000L, // 1 day ago
            endDate = now + 86400000L    // 1 day from now
        )
        assertTrue(entity.isWithinPeriod(now))
    }

    @Test
    fun `BudgetEntity isWithinPeriod returns true for start date`() {
        val start = 1000000L
        val entity = createEntity(startDate = start, endDate = start + 86400000L)
        assertTrue(entity.isWithinPeriod(start))
    }

    @Test
    fun `BudgetEntity isWithinPeriod returns true for end date`() {
        val end = 2000000L
        val entity = createEntity(startDate = end - 86400000L, endDate = end)
        assertTrue(entity.isWithinPeriod(end))
    }

    @Test
    fun `BudgetEntity isWithinPeriod returns false for before start`() {
        val start = 1000000L
        val entity = createEntity(startDate = start, endDate = start + 86400000L)
        assertFalse(entity.isWithinPeriod(start - 1))
    }

    @Test
    fun `BudgetEntity isWithinPeriod returns false for after end`() {
        val end = 2000000L
        val entity = createEntity(startDate = end - 86400000L, endDate = end)
        assertFalse(entity.isWithinPeriod(end + 1))
    }

    @Test
    fun `BudgetEntity hasEnded returns true after end date`() {
        val end = System.currentTimeMillis() - 86400000L // 1 day ago
        val entity = createEntity(
            startDate = end - 86400000L * 30,
            endDate = end
        )
        assertTrue(entity.hasEnded())
    }

    @Test
    fun `BudgetEntity hasEnded returns false before end date`() {
        val end = System.currentTimeMillis() + 86400000L // 1 day from now
        val entity = createEntity(
            startDate = System.currentTimeMillis() - 86400000L,
            endDate = end
        )
        assertFalse(entity.hasEnded())
    }

    @Test
    fun `BudgetEntity hasStarted returns true after start date`() {
        val start = System.currentTimeMillis() - 86400000L // 1 day ago
        val entity = createEntity(
            startDate = start,
            endDate = start + 86400000L * 30
        )
        assertTrue(entity.hasStarted())
    }

    @Test
    fun `BudgetEntity hasStarted returns false before start date`() {
        val start = System.currentTimeMillis() + 86400000L // 1 day from now
        val entity = createEntity(
            startDate = start,
            endDate = start + 86400000L * 30
        )
        assertFalse(entity.hasStarted())
    }

    @Test
    fun `BudgetEntity calculateRemaining returns correct value`() {
        val entity = createEntity(totalPlanned = BigDecimal("1000"))
        val remaining = entity.calculateRemaining(BigDecimal("400"))
        assertEquals(BigDecimal("600"), remaining)
    }

    @Test
    fun `BudgetEntity calculateRemaining returns negative when overspent`() {
        val entity = createEntity(totalPlanned = BigDecimal("1000"))
        val remaining = entity.calculateRemaining(BigDecimal("1200"))
        assertEquals(BigDecimal("-200"), remaining)
    }

    @Test
    fun `BudgetEntity calculateRemaining returns full amount when nothing spent`() {
        val entity = createEntity(totalPlanned = BigDecimal("1000"))
        val remaining = entity.calculateRemaining(BigDecimal.ZERO)
        assertEquals(BigDecimal("1000"), remaining)
    }

    @Test
    fun `BudgetEntity calculatePercentageSpent at 50 percent`() {
        val entity = createEntity(totalPlanned = BigDecimal("1000"))
        val percentage = entity.calculatePercentageSpent(BigDecimal("500"))
        assertEquals(50.0f, percentage, 0.01f)
    }

    @Test
    fun `BudgetEntity calculatePercentageSpent at 100 percent`() {
        val entity = createEntity(totalPlanned = BigDecimal("1000"))
        val percentage = entity.calculatePercentageSpent(BigDecimal("1000"))
        assertEquals(100.0f, percentage, 0.01f)
    }

    @Test
    fun `BudgetEntity calculatePercentageSpent above 100 percent`() {
        val entity = createEntity(totalPlanned = BigDecimal("1000"))
        val percentage = entity.calculatePercentageSpent(BigDecimal("1500"))
        assertEquals(150.0f, percentage, 0.01f)
    }

    @Test
    fun `BudgetEntity calculatePercentageSpent returns zero for zero total`() {
        val entity = createEntity(totalPlanned = BigDecimal.ZERO)
        val percentage = entity.calculatePercentageSpent(BigDecimal("500"))
        assertEquals(0.0f, percentage, 0.01f)
    }

    @Test
    fun `BudgetEntity isOverspent returns true when spent exceeds planned`() {
        val entity = createEntity(totalPlanned = BigDecimal("1000"))
        assertTrue(entity.isOverspent(BigDecimal("1200")))
    }

    @Test
    fun `BudgetEntity isOverspent returns false when spent equals planned`() {
        val entity = createEntity(totalPlanned = BigDecimal("1000"))
        assertFalse(entity.isOverspent(BigDecimal("1000")))
    }

    @Test
    fun `BudgetEntity isOverspent returns false when under budget`() {
        val entity = createEntity(totalPlanned = BigDecimal("1000"))
        assertFalse(entity.isOverspent(BigDecimal("800")))
    }

    @Test
    fun `BudgetEntity getDurationInDays returns correct value`() {
        val oneDayMs = 24L * 60 * 60 * 1000
        val entity = createEntity(
            startDate = 0,
            endDate = 30 * oneDayMs
        )
        assertEquals(30, entity.getDurationInDays())
    }

    @Test
    fun `BudgetEntity getDurationInDays returns 0 for same day`() {
        val entity = createEntity(startDate = 1000000, endDate = 1000000)
        assertEquals(0, entity.getDurationInDays())
    }

    // ============================================
    // BudgetEntity PeriodType Enum Tests
    // ============================================

    @Test
    fun `PeriodType has seven values`() {
        assertEquals(7, BudgetEntity.PeriodType.entries.size)
    }

    @Test
    fun `PeriodType includes all expected values`() {
        val values = BudgetEntity.PeriodType.entries
        assertTrue(values.contains(BudgetEntity.PeriodType.DAILY))
        assertTrue(values.contains(BudgetEntity.PeriodType.WEEKLY))
        assertTrue(values.contains(BudgetEntity.PeriodType.BIWEEKLY))
        assertTrue(values.contains(BudgetEntity.PeriodType.MONTHLY))
        assertTrue(values.contains(BudgetEntity.PeriodType.QUARTERLY))
        assertTrue(values.contains(BudgetEntity.PeriodType.YEARLY))
        assertTrue(values.contains(BudgetEntity.PeriodType.CUSTOM))
    }

    // ============================================
    // BudgetEntity SyncStatus Enum Tests
    // ============================================

    @Test
    fun `BudgetEntity SyncStatus has four values`() {
        assertEquals(4, BudgetEntity.SyncStatus.entries.size)
    }

    @Test
    fun `BudgetEntity SyncStatus PENDING exists`() {
        assertNotNull(BudgetEntity.SyncStatus.PENDING)
    }

    @Test
    fun `BudgetEntity SyncStatus SYNCED exists`() {
        assertNotNull(BudgetEntity.SyncStatus.SYNCED)
    }

    @Test
    fun `BudgetEntity SyncStatus FAILED exists`() {
        assertNotNull(BudgetEntity.SyncStatus.FAILED)
    }

    @Test
    fun `BudgetEntity SyncStatus CONFLICT exists`() {
        assertNotNull(BudgetEntity.SyncStatus.CONFLICT)
    }

    // ============================================
    // BudgetEntity Companion Extensions Tests
    // ============================================

    @Test
    fun `withUpdatedTimestamp sets PENDING sync status`() {
        val entity = createEntity().copy(syncStatus = BudgetEntity.SyncStatus.SYNCED)
        with(BudgetEntity.Companion) {
            val updated = entity.withUpdatedTimestamp()
            assertEquals(BudgetEntity.SyncStatus.PENDING, updated.syncStatus)
            assertTrue(updated.updatedAt >= entity.updatedAt)
        }
    }

    @Test
    fun `markAsSynced sets SYNCED status`() {
        val entity = createEntity().copy(syncStatus = BudgetEntity.SyncStatus.PENDING)
        with(BudgetEntity.Companion) {
            val synced = entity.markAsSynced()
            assertEquals(BudgetEntity.SyncStatus.SYNCED, synced.syncStatus)
        }
    }

    @Test
    fun `deactivate sets isActive to false and PENDING sync`() {
        val entity = createEntity()
        assertTrue(entity.isActive)
        with(BudgetEntity.Companion) {
            val deactivated = entity.deactivate()
            assertFalse(deactivated.isActive)
            assertEquals(BudgetEntity.SyncStatus.PENDING, deactivated.syncStatus)
            assertTrue(deactivated.updatedAt >= entity.updatedAt)
        }
    }

    @Test
    fun `withUpdatedTimestamp preserves all other fields`() {
        val entity = createEntity(
            name = "Food Budget",
            totalPlanned = BigDecimal("500")
        )
        with(BudgetEntity.Companion) {
            val updated = entity.withUpdatedTimestamp()
            assertEquals(entity.id, updated.id)
            assertEquals(entity.userId, updated.userId)
            assertEquals(entity.name, updated.name)
            assertEquals(entity.totalPlanned, updated.totalPlanned)
            assertEquals(entity.periodType, updated.periodType)
        }
    }

    // ============================================
    // Entity to Domain Mapping Tests
    // ============================================

    /**
     * Simulates the mapping from BudgetEntity to Budget domain model.
     */
    private fun mapEntityToDomain(entity: BudgetEntity): Budget {
        val startDate = LocalDate.ofEpochDay(entity.startDate / 86400000L)
        val endDate = LocalDate.ofEpochDay(entity.endDate / 86400000L)

        return Budget(
            id = entity.id.toString(),
            userId = entity.userId.toString(),
            name = entity.name,
            totalAmount = entity.totalPlanned,
            period = when (entity.periodType) {
                BudgetEntity.PeriodType.WEEKLY -> BudgetPeriod.WEEKLY
                BudgetEntity.PeriodType.MONTHLY -> BudgetPeriod.MONTHLY
                BudgetEntity.PeriodType.QUARTERLY -> BudgetPeriod.QUARTERLY
                BudgetEntity.PeriodType.YEARLY -> BudgetPeriod.YEARLY
                else -> BudgetPeriod.MONTHLY
            },
            startDate = startDate,
            endDate = endDate,
            isActive = entity.isActive,
            notes = entity.description
        )
    }

    @Test
    fun `entity to domain mapping preserves name`() {
        val entity = createEntity(name = "Groceries")
        val domain = mapEntityToDomain(entity)
        assertEquals("Groceries", domain.name)
    }

    @Test
    fun `entity to domain mapping preserves totalAmount`() {
        val entity = createEntity(totalPlanned = BigDecimal("2500"))
        val domain = mapEntityToDomain(entity)
        assertEquals(BigDecimal("2500"), domain.totalAmount)
    }

    @Test
    fun `entity to domain mapping maps MONTHLY period`() {
        val entity = createEntity(periodType = BudgetEntity.PeriodType.MONTHLY)
        val domain = mapEntityToDomain(entity)
        assertEquals(BudgetPeriod.MONTHLY, domain.period)
    }

    @Test
    fun `entity to domain mapping maps WEEKLY period`() {
        val entity = createEntity(periodType = BudgetEntity.PeriodType.WEEKLY)
        val domain = mapEntityToDomain(entity)
        assertEquals(BudgetPeriod.WEEKLY, domain.period)
    }

    @Test
    fun `entity to domain mapping maps QUARTERLY period`() {
        val entity = createEntity(periodType = BudgetEntity.PeriodType.QUARTERLY)
        val domain = mapEntityToDomain(entity)
        assertEquals(BudgetPeriod.QUARTERLY, domain.period)
    }

    @Test
    fun `entity to domain mapping maps YEARLY period`() {
        val entity = createEntity(periodType = BudgetEntity.PeriodType.YEARLY)
        val domain = mapEntityToDomain(entity)
        assertEquals(BudgetPeriod.YEARLY, domain.period)
    }

    @Test
    fun `entity to domain mapping defaults CUSTOM to MONTHLY`() {
        val entity = createEntity(periodType = BudgetEntity.PeriodType.CUSTOM)
        val domain = mapEntityToDomain(entity)
        assertEquals(BudgetPeriod.MONTHLY, domain.period)
    }

    @Test
    fun `entity to domain mapping defaults DAILY to MONTHLY`() {
        val entity = createEntity(periodType = BudgetEntity.PeriodType.DAILY)
        val domain = mapEntityToDomain(entity)
        assertEquals(BudgetPeriod.MONTHLY, domain.period)
    }

    @Test
    fun `entity to domain mapping preserves isActive`() {
        val entity = createEntity().copy(isActive = false)
        val domain = mapEntityToDomain(entity)
        assertFalse(domain.isActive)
    }

    @Test
    fun `entity to domain mapping preserves description as notes`() {
        val entity = createEntity().copy(description = "Monthly groceries budget")
        val domain = mapEntityToDomain(entity)
        assertEquals("Monthly groceries budget", domain.notes)
    }

    // ============================================
    // Budget Domain Model Tests
    // ============================================

    @Test
    fun `Budget totalSpent with items`() {
        val items = listOf(
            createBudgetItem("1", BigDecimal("300"), BigDecimal("200")),
            createBudgetItem("2", BigDecimal("500"), BigDecimal("100"))
        )
        val budget = createDomainBudget(items = items)
        assertEquals(BigDecimal("300"), budget.totalSpent)
    }

    @Test
    fun `Budget totalAllocated with items`() {
        val items = listOf(
            createBudgetItem("1", BigDecimal("300"), BigDecimal.ZERO),
            createBudgetItem("2", BigDecimal("500"), BigDecimal.ZERO)
        )
        val budget = createDomainBudget(items = items)
        assertEquals(BigDecimal("800"), budget.totalAllocated)
    }

    @Test
    fun `Budget remainingAmount when partially spent`() {
        val items = listOf(
            createBudgetItem("1", BigDecimal("500"), BigDecimal("300"))
        )
        val budget = createDomainBudget(totalAmount = BigDecimal("1000"), items = items)
        assertEquals(BigDecimal("700"), budget.remainingAmount)
    }

    @Test
    fun `Budget unallocatedAmount when partially allocated`() {
        val items = listOf(
            createBudgetItem("1", BigDecimal("600"), BigDecimal.ZERO)
        )
        val budget = createDomainBudget(totalAmount = BigDecimal("1000"), items = items)
        assertEquals(BigDecimal("400"), budget.unallocatedAmount)
    }

    @Test
    fun `Budget isOverBudget when spent exceeds total`() {
        val items = listOf(
            createBudgetItem("1", BigDecimal("500"), BigDecimal("1200"))
        )
        val budget = createDomainBudget(totalAmount = BigDecimal("1000"), items = items)
        assertTrue(budget.isOverBudget)
    }

    @Test
    fun `Budget is not overBudget when under limit`() {
        val items = listOf(
            createBudgetItem("1", BigDecimal("500"), BigDecimal("400"))
        )
        val budget = createDomainBudget(totalAmount = BigDecimal("1000"), items = items)
        assertFalse(budget.isOverBudget)
    }

    @Test
    fun `Budget isNearLimit at 80 percent spent`() {
        val items = listOf(
            createBudgetItem("1", BigDecimal("500"), BigDecimal("800"))
        )
        val budget = createDomainBudget(totalAmount = BigDecimal("1000"), items = items)
        assertTrue(budget.isNearLimit)
    }

    @Test
    fun `Budget spentPercentage zero when no items`() {
        val budget = createDomainBudget(totalAmount = BigDecimal("1000"))
        assertEquals(0.0, budget.spentPercentage, 0.01)
    }

    @Test
    fun `Budget containsDate for date within range`() {
        val budget = createDomainBudget(
            startDate = LocalDate.of(2025, 1, 1),
            endDate = LocalDate.of(2025, 12, 31)
        )
        assertTrue(budget.containsDate(LocalDate.of(2025, 6, 15)))
    }

    @Test
    fun `Budget containsDate for date outside range`() {
        val budget = createDomainBudget(
            startDate = LocalDate.of(2025, 1, 1),
            endDate = LocalDate.of(2025, 12, 31)
        )
        assertFalse(budget.containsDate(LocalDate.of(2026, 1, 1)))
    }

    @Test
    fun `Budget empty factory`() {
        val empty = Budget.empty()
        assertEquals("", empty.id)
        assertEquals("", empty.userId)
        assertEquals("", empty.name)
        assertEquals(BigDecimal.ZERO, empty.totalAmount)
    }

    @Test
    fun `Budget forMonth factory`() {
        val budget = Budget.forMonth(
            id = "b1",
            userId = "u1",
            name = "Monthly",
            totalAmount = BigDecimal("2000")
        )
        assertEquals(BudgetPeriod.MONTHLY, budget.period)
    }

    // ============================================
    // BudgetItem Domain Model Tests
    // ============================================

    @Test
    fun `BudgetItem remainingAmount`() {
        val item = createBudgetItem("1", BigDecimal("500"), BigDecimal("200"))
        assertEquals(BigDecimal("300"), item.remainingAmount)
    }

    @Test
    fun `BudgetItem spentPercentage at 50 percent`() {
        val item = createBudgetItem("1", BigDecimal("500"), BigDecimal("250"))
        assertEquals(50.0, item.spentPercentage, 0.01)
    }

    @Test
    fun `BudgetItem spentPercentage zero for zero allocation`() {
        val item = createBudgetItem("1", BigDecimal.ZERO, BigDecimal.ZERO)
        assertEquals(0.0, item.spentPercentage, 0.01)
    }

    @Test
    fun `BudgetItem isOverBudget`() {
        val item = createBudgetItem("1", BigDecimal("500"), BigDecimal("600"))
        assertTrue(item.isOverBudget)
    }

    @Test
    fun `BudgetItem isNearLimit at 80 percent`() {
        val item = createBudgetItem("1", BigDecimal("500"), BigDecimal("400"))
        assertTrue(item.isNearLimit)
    }

    @Test
    fun `BudgetItem isNearLimit false when over budget`() {
        val item = createBudgetItem("1", BigDecimal("500"), BigDecimal("600"))
        assertFalse(item.isNearLimit)
    }

    @Test
    fun `BudgetItem isNearLimit false when under 80 percent`() {
        val item = createBudgetItem("1", BigDecimal("500"), BigDecimal("300"))
        assertFalse(item.isNearLimit)
    }

    @Test
    fun `BudgetItem empty factory`() {
        val empty = BudgetItem.empty()
        assertEquals("", empty.id)
        assertEquals("", empty.budgetId)
        assertEquals(BigDecimal.ZERO, empty.allocatedAmount)
    }

    // ============================================
    // PeriodType Mapping Completeness Tests
    // ============================================

    @Test
    fun `all entity PeriodTypes can be mapped to domain`() {
        BudgetEntity.PeriodType.entries.forEach { periodType ->
            val entity = createEntity(periodType = periodType)
            val domain = mapEntityToDomain(entity)
            assertNotNull(domain.period)
        }
    }

    @Test
    fun `all domain BudgetPeriods have corresponding entity PeriodType`() {
        val mapping = mapOf(
            BudgetPeriod.WEEKLY to BudgetEntity.PeriodType.WEEKLY,
            BudgetPeriod.MONTHLY to BudgetEntity.PeriodType.MONTHLY,
            BudgetPeriod.QUARTERLY to BudgetEntity.PeriodType.QUARTERLY,
            BudgetPeriod.YEARLY to BudgetEntity.PeriodType.YEARLY
        )
        BudgetPeriod.entries.forEach { period ->
            assertTrue(
                "Domain period $period has mapping",
                mapping.containsKey(period)
            )
        }
    }

    // ============================================
    // Helper Functions
    // ============================================

    private fun createEntity(
        name: String = "Test Budget",
        totalPlanned: BigDecimal = BigDecimal("1000"),
        periodType: BudgetEntity.PeriodType = BudgetEntity.PeriodType.MONTHLY,
        startDate: Long = System.currentTimeMillis() - 86400000L * 15,
        endDate: Long = System.currentTimeMillis() + 86400000L * 15
    ): BudgetEntity {
        return BudgetEntity(
            userId = UUID.randomUUID(),
            name = name,
            periodType = periodType,
            startDate = startDate,
            endDate = endDate,
            totalPlanned = totalPlanned
        )
    }

    private fun createDomainBudget(
        totalAmount: BigDecimal = BigDecimal("1000"),
        items: List<BudgetItem> = emptyList(),
        startDate: LocalDate = LocalDate.now().minusDays(15),
        endDate: LocalDate = LocalDate.now().plusDays(15)
    ): Budget {
        return Budget(
            id = UUID.randomUUID().toString(),
            userId = "user-1",
            name = "Test Budget",
            totalAmount = totalAmount,
            period = BudgetPeriod.MONTHLY,
            startDate = startDate,
            endDate = endDate,
            items = items
        )
    }

    private fun createBudgetItem(
        id: String,
        allocatedAmount: BigDecimal,
        spentAmount: BigDecimal
    ): BudgetItem {
        return BudgetItem(
            id = id,
            budgetId = "budget-1",
            categoryId = "cat-$id",
            allocatedAmount = allocatedAmount,
            spentAmount = spentAmount
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
