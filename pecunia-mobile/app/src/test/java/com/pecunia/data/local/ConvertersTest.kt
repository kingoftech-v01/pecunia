package com.pecunia.data.local

import com.pecunia.data.local.database.Converters
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.math.BigDecimal
import java.util.Date
import java.util.UUID

/**
 * Comprehensive unit tests for Room TypeConverters.
 * Tests all converter methods including null handling, error cases, and edge cases.
 */
class ConvertersTest {

    private lateinit var converters: Converters

    @Before
    fun setUp() {
        converters = Converters()
    }

    // ============================================
    // Date Converters
    // ============================================

    @Test
    fun `fromTimestamp with valid value returns correct Date`() {
        val timestamp = 1700000000000L
        val result = converters.fromTimestamp(timestamp)
        assertNotNull(result)
        assertEquals(timestamp, result!!.time)
    }

    @Test
    fun `fromTimestamp with null returns null`() {
        val result = converters.fromTimestamp(null)
        assertNull(result)
    }

    @Test
    fun `fromTimestamp with zero returns epoch Date`() {
        val result = converters.fromTimestamp(0L)
        assertNotNull(result)
        assertEquals(0L, result!!.time)
    }

    @Test
    fun `fromTimestamp with negative value returns Date before epoch`() {
        val result = converters.fromTimestamp(-1000L)
        assertNotNull(result)
        assertEquals(-1000L, result!!.time)
    }

    @Test
    fun `dateToTimestamp with valid Date returns correct timestamp`() {
        val date = Date(1700000000000L)
        val result = converters.dateToTimestamp(date)
        assertEquals(1700000000000L, result)
    }

    @Test
    fun `dateToTimestamp with null returns null`() {
        val result = converters.dateToTimestamp(null)
        assertNull(result)
    }

    @Test
    fun `Date conversion roundtrip preserves value`() {
        val originalTimestamp = System.currentTimeMillis()
        val date = converters.fromTimestamp(originalTimestamp)
        val convertedBack = converters.dateToTimestamp(date)
        assertEquals(originalTimestamp, convertedBack)
    }

    // ============================================
    // UUID Converters
    // ============================================

    @Test
    fun `fromUUIDString with valid UUID string returns UUID`() {
        val uuidString = "550e8400-e29b-41d4-a716-446655440000"
        val result = converters.fromUUIDString(uuidString)
        assertNotNull(result)
        assertEquals(uuidString, result.toString())
    }

    @Test
    fun `fromUUIDString with null returns null`() {
        val result = converters.fromUUIDString(null)
        assertNull(result)
    }

    @Test
    fun `fromUUIDString with invalid string throws exception`() {
        try {
            converters.fromUUIDString("not-a-uuid")
            fail("Expected IllegalArgumentException")
        } catch (e: IllegalArgumentException) {
            // Expected
        }
    }

    @Test
    fun `uuidToString with valid UUID returns string`() {
        val uuid = UUID.fromString("550e8400-e29b-41d4-a716-446655440000")
        val result = converters.uuidToString(uuid)
        assertEquals("550e8400-e29b-41d4-a716-446655440000", result)
    }

    @Test
    fun `uuidToString with null returns null`() {
        val result = converters.uuidToString(null)
        assertNull(result)
    }

    @Test
    fun `UUID conversion roundtrip preserves value`() {
        val originalUuid = UUID.randomUUID()
        val asString = converters.uuidToString(originalUuid)
        val convertedBack = converters.fromUUIDString(asString)
        assertEquals(originalUuid, convertedBack)
    }

    // ============================================
    // BigDecimal Converters
    // ============================================

    @Test
    fun `fromBigDecimalString with valid number returns BigDecimal`() {
        val result = converters.fromBigDecimalString("123.45")
        assertNotNull(result)
        assertEquals(BigDecimal("123.45"), result)
    }

    @Test
    fun `fromBigDecimalString with null returns null`() {
        val result = converters.fromBigDecimalString(null)
        assertNull(result)
    }

    @Test
    fun `fromBigDecimalString with zero returns BigDecimal ZERO`() {
        val result = converters.fromBigDecimalString("0")
        assertNotNull(result)
        assertEquals(BigDecimal("0"), result)
    }

    @Test
    fun `fromBigDecimalString with negative value returns negative BigDecimal`() {
        val result = converters.fromBigDecimalString("-99.99")
        assertNotNull(result)
        assertEquals(BigDecimal("-99.99"), result)
    }

    @Test
    fun `fromBigDecimalString with very large number returns BigDecimal`() {
        val result = converters.fromBigDecimalString("999999999999.99")
        assertNotNull(result)
        assertEquals(BigDecimal("999999999999.99"), result)
    }

    @Test
    fun `fromBigDecimalString with invalid string returns ZERO fallback`() {
        val result = converters.fromBigDecimalString("not_a_number")
        assertNotNull(result)
        assertEquals(BigDecimal.ZERO, result)
    }

    @Test
    fun `fromBigDecimalString with empty string returns ZERO fallback`() {
        val result = converters.fromBigDecimalString("")
        assertNotNull(result)
        assertEquals(BigDecimal.ZERO, result)
    }

    @Test
    fun `bigDecimalToString with valid BigDecimal returns plain string`() {
        val result = converters.bigDecimalToString(BigDecimal("123.45"))
        assertEquals("123.45", result)
    }

    @Test
    fun `bigDecimalToString with null returns null`() {
        val result = converters.bigDecimalToString(null)
        assertNull(result)
    }

    @Test
    fun `bigDecimalToString avoids scientific notation`() {
        val bigNumber = BigDecimal("0.00000001")
        val result = converters.bigDecimalToString(bigNumber)
        assertNotNull(result)
        assertFalse(result!!.contains("E"))
    }

    @Test
    fun `BigDecimal conversion roundtrip preserves value`() {
        val original = BigDecimal("12345.6789")
        val asString = converters.bigDecimalToString(original)
        val convertedBack = converters.fromBigDecimalString(asString)
        assertEquals(0, original.compareTo(convertedBack))
    }

    // ============================================
    // List<String> Converters
    // ============================================

    @Test
    fun `fromStringList with valid JSON returns list`() {
        val json = """["apple","banana","cherry"]"""
        val result = converters.fromStringList(json)
        assertNotNull(result)
        assertEquals(3, result!!.size)
        assertEquals("apple", result[0])
        assertEquals("banana", result[1])
        assertEquals("cherry", result[2])
    }

    @Test
    fun `fromStringList with null returns null`() {
        val result = converters.fromStringList(null)
        assertNull(result)
    }

    @Test
    fun `fromStringList with empty JSON array returns empty list`() {
        val result = converters.fromStringList("[]")
        assertNotNull(result)
        assertTrue(result!!.isEmpty())
    }

    @Test
    fun `fromStringList with invalid JSON returns empty list fallback`() {
        val result = converters.fromStringList("not json")
        assertNotNull(result)
        assertTrue(result!!.isEmpty())
    }

    @Test
    fun `stringListToJson with valid list returns JSON`() {
        val list = listOf("a", "b", "c")
        val result = converters.stringListToJson(list)
        assertNotNull(result)
        assertTrue(result!!.contains("a"))
        assertTrue(result.contains("b"))
        assertTrue(result.contains("c"))
    }

    @Test
    fun `stringListToJson with null returns null`() {
        val result = converters.stringListToJson(null)
        assertNull(result)
    }

    @Test
    fun `stringListToJson with empty list returns empty JSON array`() {
        val result = converters.stringListToJson(emptyList())
        assertEquals("[]", result)
    }

    @Test
    fun `String list conversion roundtrip preserves values`() {
        val original = listOf("tag1", "tag2", "tag3")
        val json = converters.stringListToJson(original)
        val convertedBack = converters.fromStringList(json)
        assertEquals(original, convertedBack)
    }

    // ============================================
    // Map<String, String> Converters
    // ============================================

    @Test
    fun `fromStringMap with valid JSON returns map`() {
        val json = """{"key1":"value1","key2":"value2"}"""
        val result = converters.fromStringMap(json)
        assertNotNull(result)
        assertEquals(2, result!!.size)
        assertEquals("value1", result["key1"])
        assertEquals("value2", result["key2"])
    }

    @Test
    fun `fromStringMap with null returns null`() {
        val result = converters.fromStringMap(null)
        assertNull(result)
    }

    @Test
    fun `fromStringMap with empty JSON object returns empty map`() {
        val result = converters.fromStringMap("{}")
        assertNotNull(result)
        assertTrue(result!!.isEmpty())
    }

    @Test
    fun `fromStringMap with invalid JSON returns empty map fallback`() {
        val result = converters.fromStringMap("invalid")
        assertNotNull(result)
        assertTrue(result!!.isEmpty())
    }

    @Test
    fun `stringMapToJson with valid map returns JSON`() {
        val map = mapOf("a" to "1", "b" to "2")
        val result = converters.stringMapToJson(map)
        assertNotNull(result)
        assertTrue(result!!.contains("\"a\""))
        assertTrue(result.contains("\"1\""))
    }

    @Test
    fun `stringMapToJson with null returns null`() {
        val result = converters.stringMapToJson(null)
        assertNull(result)
    }

    @Test
    fun `String map conversion roundtrip preserves values`() {
        val original = mapOf("k1" to "v1", "k2" to "v2")
        val json = converters.stringMapToJson(original)
        val convertedBack = converters.fromStringMap(json)
        assertEquals(original, convertedBack)
    }

    // ============================================
    // TransactionType Enum Converters
    // ============================================

    @Test
    fun `fromTransactionTypeString with EXPENSE returns EXPENSE`() {
        val result = converters.fromTransactionTypeString("EXPENSE")
        assertNotNull(result)
        assertEquals("EXPENSE", result!!.name)
    }

    @Test
    fun `fromTransactionTypeString with INCOME returns INCOME`() {
        val result = converters.fromTransactionTypeString("INCOME")
        assertNotNull(result)
        assertEquals("INCOME", result!!.name)
    }

    @Test
    fun `fromTransactionTypeString with null returns null`() {
        val result = converters.fromTransactionTypeString(null)
        assertNull(result)
    }

    @Test
    fun `fromTransactionTypeString with invalid value returns EXPENSE fallback`() {
        val result = converters.fromTransactionTypeString("INVALID")
        assertNotNull(result)
        assertEquals("EXPENSE", result!!.name)
    }

    @Test
    fun `transactionTypeToString with null returns null`() {
        val result = converters.transactionTypeToString(null)
        assertNull(result)
    }

    // ============================================
    // AccountType Enum Converters
    // ============================================

    @Test
    fun `fromAccountTypeString with CHECKING returns CHECKING`() {
        val result = converters.fromAccountTypeString("CHECKING")
        assertNotNull(result)
        assertEquals("CHECKING", result!!.name)
    }

    @Test
    fun `fromAccountTypeString with SAVINGS returns SAVINGS`() {
        val result = converters.fromAccountTypeString("SAVINGS")
        assertNotNull(result)
        assertEquals("SAVINGS", result!!.name)
    }

    @Test
    fun `fromAccountTypeString with null returns null`() {
        val result = converters.fromAccountTypeString(null)
        assertNull(result)
    }

    @Test
    fun `fromAccountTypeString with invalid value returns CHECKING fallback`() {
        val result = converters.fromAccountTypeString("INVALID")
        assertNotNull(result)
        assertEquals("CHECKING", result!!.name)
    }

    @Test
    fun `accountTypeToString with null returns null`() {
        val result = converters.accountTypeToString(null)
        assertNull(result)
    }

    // ============================================
    // CategoryType Enum Converters
    // ============================================

    @Test
    fun `fromCategoryTypeString with EXPENSE returns EXPENSE`() {
        val result = converters.fromCategoryTypeString("EXPENSE")
        assertNotNull(result)
        assertEquals("EXPENSE", result!!.name)
    }

    @Test
    fun `fromCategoryTypeString with INCOME returns INCOME`() {
        val result = converters.fromCategoryTypeString("INCOME")
        assertNotNull(result)
        assertEquals("INCOME", result!!.name)
    }

    @Test
    fun `fromCategoryTypeString with null returns null`() {
        val result = converters.fromCategoryTypeString(null)
        assertNull(result)
    }

    @Test
    fun `fromCategoryTypeString with invalid value returns EXPENSE fallback`() {
        val result = converters.fromCategoryTypeString("INVALID")
        assertNotNull(result)
        assertEquals("EXPENSE", result!!.name)
    }

    @Test
    fun `categoryTypeToString with null returns null`() {
        val result = converters.categoryTypeToString(null)
        assertNull(result)
    }

    // ============================================
    // BudgetPeriod Enum Converters
    // ============================================

    @Test
    fun `fromBudgetPeriodString with MONTHLY returns MONTHLY`() {
        val result = converters.fromBudgetPeriodString("MONTHLY")
        assertNotNull(result)
        assertEquals("MONTHLY", result!!.name)
    }

    @Test
    fun `fromBudgetPeriodString with WEEKLY returns WEEKLY`() {
        val result = converters.fromBudgetPeriodString("WEEKLY")
        assertNotNull(result)
        assertEquals("WEEKLY", result!!.name)
    }

    @Test
    fun `fromBudgetPeriodString with QUARTERLY returns QUARTERLY`() {
        val result = converters.fromBudgetPeriodString("QUARTERLY")
        assertNotNull(result)
        assertEquals("QUARTERLY", result!!.name)
    }

    @Test
    fun `fromBudgetPeriodString with YEARLY returns YEARLY`() {
        val result = converters.fromBudgetPeriodString("YEARLY")
        assertNotNull(result)
        assertEquals("YEARLY", result!!.name)
    }

    @Test
    fun `fromBudgetPeriodString with null returns null`() {
        val result = converters.fromBudgetPeriodString(null)
        assertNull(result)
    }

    @Test
    fun `fromBudgetPeriodString with invalid value returns MONTHLY fallback`() {
        val result = converters.fromBudgetPeriodString("INVALID")
        assertNotNull(result)
        assertEquals("MONTHLY", result!!.name)
    }

    @Test
    fun `budgetPeriodToString with null returns null`() {
        val result = converters.budgetPeriodToString(null)
        assertNull(result)
    }

    // ============================================
    // RecurrenceFrequency Enum Converters
    // ============================================

    @Test
    fun `fromRecurrenceFrequencyString with MONTHLY returns MONTHLY`() {
        val result = converters.fromRecurrenceFrequencyString("MONTHLY")
        assertNotNull(result)
        assertEquals("MONTHLY", result!!.name)
    }

    @Test
    fun `fromRecurrenceFrequencyString with null returns null`() {
        val result = converters.fromRecurrenceFrequencyString(null)
        assertNull(result)
    }

    @Test
    fun `fromRecurrenceFrequencyString with invalid value returns MONTHLY fallback`() {
        val result = converters.fromRecurrenceFrequencyString("INVALID")
        assertNotNull(result)
        assertEquals("MONTHLY", result!!.name)
    }

    @Test
    fun `recurrenceFrequencyToString with null returns null`() {
        val result = converters.recurrenceFrequencyToString(null)
        assertNull(result)
    }

    // ============================================
    // List<Long> Converters
    // ============================================

    @Test
    fun `fromLongList with valid JSON returns list`() {
        val json = "[1,2,3,4,5]"
        val result = converters.fromLongList(json)
        assertNotNull(result)
        assertEquals(5, result!!.size)
        assertEquals(1L, result[0])
        assertEquals(5L, result[4])
    }

    @Test
    fun `fromLongList with null returns null`() {
        val result = converters.fromLongList(null)
        assertNull(result)
    }

    @Test
    fun `fromLongList with empty array returns empty list`() {
        val result = converters.fromLongList("[]")
        assertNotNull(result)
        assertTrue(result!!.isEmpty())
    }

    @Test
    fun `fromLongList with invalid JSON returns empty list fallback`() {
        val result = converters.fromLongList("not json")
        assertNotNull(result)
        assertTrue(result!!.isEmpty())
    }

    @Test
    fun `longListToJson with valid list returns JSON`() {
        val list = listOf(10L, 20L, 30L)
        val result = converters.longListToJson(list)
        assertNotNull(result)
        assertTrue(result!!.contains("10"))
        assertTrue(result.contains("20"))
        assertTrue(result.contains("30"))
    }

    @Test
    fun `longListToJson with null returns null`() {
        val result = converters.longListToJson(null)
        assertNull(result)
    }

    @Test
    fun `Long list conversion roundtrip preserves values`() {
        val original = listOf(100L, 200L, 300L)
        val json = converters.longListToJson(original)
        val convertedBack = converters.fromLongList(json)
        assertEquals(original, convertedBack)
    }

    @Test
    fun `fromStringList with single element JSON array`() {
        val json = """["only"]"""
        val result = converters.fromStringList(json)
        assertNotNull(result)
        assertEquals(1, result!!.size)
        assertEquals("only", result[0])
    }

    @Test
    fun `fromStringList with special characters in elements`() {
        val list = listOf("hello world", "foo@bar.com", "key=value")
        val json = converters.stringListToJson(list)
        val result = converters.fromStringList(json)
        assertEquals(list, result)
    }

    @Test
    fun `fromStringMap with special characters in keys and values`() {
        val map = mapOf("key with spaces" to "value/with/slashes", "a@b.c" to "1+2=3")
        val json = converters.stringMapToJson(map)
        val result = converters.fromStringMap(json)
        assertEquals(map, result)
    }
}
