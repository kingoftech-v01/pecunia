package com.pecunia.ui.screens.scanner

import org.junit.Assert.*
import org.junit.Test
import java.util.Date

/**
 * Unit tests for ScannerViewModel data classes and receipt data extraction logic.
 * Since ScannerViewModel extends AndroidViewModel and uses ML Kit
 * (which requires Android framework), these tests focus on the data models,
 * ExtractedReceiptData, ReceiptItem, and ScannerUiState.
 */
class ScannerViewModelTest {

    // ============================================
    // ScannerUiState Tests
    // ============================================

    @Test
    fun `default ScannerUiState has correct initial values`() {
        val state = ScannerUiState()
        assertFalse(state.isProcessing)
        assertNull(state.capturedImageUri)
        assertNull(state.extractedData)
        assertNull(state.error)
        assertFalse(state.isCreatingTransaction)
        assertFalse(state.transactionCreated)
    }

    @Test
    fun `ScannerUiState copy preserves other fields`() {
        val state = ScannerUiState(
            isProcessing = true,
            error = "test error"
        )
        val updated = state.copy(isProcessing = false)
        assertFalse(updated.isProcessing)
        assertEquals("test error", updated.error)
    }

    // ============================================
    // ExtractedReceiptData Tests
    // ============================================

    @Test
    fun `ExtractedReceiptData holds all fields correctly`() {
        val items = listOf(
            ReceiptItem("Coffee", 1, 4.50),
            ReceiptItem("Muffin", 2, 3.00)
        )
        val date = Date()

        val data = ExtractedReceiptData(
            rawText = "Sample receipt text",
            merchantName = "Starbucks",
            totalAmount = 10.50,
            date = date,
            items = items,
            suggestedCategory = "Food & Dining",
            confidence = 0.8f
        )

        assertEquals("Sample receipt text", data.rawText)
        assertEquals("Starbucks", data.merchantName)
        assertEquals(10.50, data.totalAmount!!, 0.01)
        assertEquals(date, data.date)
        assertEquals(2, data.items.size)
        assertEquals("Food & Dining", data.suggestedCategory)
        assertEquals(0.8f, data.confidence, 0.01f)
    }

    @Test
    fun `ExtractedReceiptData handles null fields`() {
        val data = ExtractedReceiptData(
            rawText = "Unclear receipt",
            merchantName = null,
            totalAmount = null,
            date = null,
            items = emptyList(),
            suggestedCategory = null,
            confidence = 0.0f
        )

        assertNull(data.merchantName)
        assertNull(data.totalAmount)
        assertNull(data.date)
        assertTrue(data.items.isEmpty())
        assertNull(data.suggestedCategory)
        assertEquals(0.0f, data.confidence, 0.01f)
    }

    @Test
    fun `ExtractedReceiptData confidence between 0 and 1`() {
        val lowConfidence = ExtractedReceiptData(
            rawText = "", merchantName = null, totalAmount = null,
            date = null, items = emptyList(), suggestedCategory = null, confidence = 0.0f
        )
        val highConfidence = ExtractedReceiptData(
            rawText = "text", merchantName = "Store", totalAmount = 50.0,
            date = Date(), items = listOf(ReceiptItem("Item", 1, 50.0)),
            suggestedCategory = "Shopping", confidence = 1.0f
        )

        assertTrue(lowConfidence.confidence in 0f..1f)
        assertTrue(highConfidence.confidence in 0f..1f)
    }

    // ============================================
    // ReceiptItem Tests
    // ============================================

    @Test
    fun `ReceiptItem holds correct data`() {
        val item = ReceiptItem(
            name = "Coffee Latte",
            quantity = 2,
            price = 5.50
        )
        assertEquals("Coffee Latte", item.name)
        assertEquals(2, item.quantity)
        assertEquals(5.50, item.price!!, 0.01)
    }

    @Test
    fun `ReceiptItem with null quantity and price`() {
        val item = ReceiptItem(name = "Unknown Item")
        assertEquals("Unknown Item", item.name)
        assertNull(item.quantity)
        assertNull(item.price)
    }

    @Test
    fun `ReceiptItem with zero price`() {
        val item = ReceiptItem(name = "Free Sample", price = 0.0)
        assertEquals(0.0, item.price!!, 0.01)
    }

    @Test
    fun `ReceiptItem with large price`() {
        val item = ReceiptItem(name = "Expensive Item", price = 99999.99)
        assertEquals(99999.99, item.price!!, 0.01)
    }

    @Test
    fun `ReceiptItem equality works correctly`() {
        val item1 = ReceiptItem("Coffee", 1, 4.50)
        val item2 = ReceiptItem("Coffee", 1, 4.50)
        assertEquals(item1, item2)
    }

    @Test
    fun `ReceiptItem inequality for different names`() {
        val item1 = ReceiptItem("Coffee", 1, 4.50)
        val item2 = ReceiptItem("Tea", 1, 4.50)
        assertNotEquals(item1, item2)
    }

    @Test
    fun `ReceiptItem inequality for different prices`() {
        val item1 = ReceiptItem("Coffee", 1, 4.50)
        val item2 = ReceiptItem("Coffee", 1, 5.50)
        assertNotEquals(item1, item2)
    }

    // ============================================
    // Confidence Calculation Logic Tests
    // These test the expected confidence scoring behavior
    // ============================================

    @Test
    fun `confidence is 0 when nothing extracted`() {
        val confidence = calculateTestConfidence(null, null, null, emptyList())
        assertEquals(0.0f, confidence, 0.01f)
    }

    @Test
    fun `confidence includes merchant name contribution`() {
        val confidence = calculateTestConfidence("Store", null, null, emptyList())
        assertEquals(0.25f, confidence, 0.01f)
    }

    @Test
    fun `confidence includes total amount contribution`() {
        val confidence = calculateTestConfidence(null, 50.0, null, emptyList())
        assertEquals(0.35f, confidence, 0.01f)
    }

    @Test
    fun `confidence includes date contribution`() {
        val confidence = calculateTestConfidence(null, null, Date(), emptyList())
        assertEquals(0.20f, confidence, 0.01f)
    }

    @Test
    fun `confidence includes items contribution`() {
        val items = listOf(
            ReceiptItem("Item 1", price = 10.0),
            ReceiptItem("Item 2", price = 20.0)
        )
        val confidence = calculateTestConfidence(null, null, null, items)
        assertEquals(0.08f, confidence, 0.01f) // 2 items * 0.04 = 0.08
    }

    @Test
    fun `confidence items contribution is capped at 0_2`() {
        val items = (1..10).map { ReceiptItem("Item $it", price = it * 5.0) }
        val confidence = calculateTestConfidence(null, null, null, items)
        assertEquals(0.20f, confidence, 0.01f) // min(0.20, 10 * 0.04 = 0.40) = 0.20
    }

    @Test
    fun `full confidence with all data extracted`() {
        val items = (1..5).map { ReceiptItem("Item $it", price = it * 5.0) }
        val confidence = calculateTestConfidence("Store", 50.0, Date(), items)
        assertEquals(1.0f, confidence, 0.01f) // 0.25 + 0.35 + 0.20 + min(0.20, 0.20) = 1.0
    }

    @Test
    fun `confidence with amount zero does not count`() {
        val confidence = calculateTestConfidence(null, 0.0, null, emptyList())
        assertEquals(0.0f, confidence, 0.01f)
    }

    @Test
    fun `confidence with blank merchant does not count`() {
        val confidence = calculateTestConfidence("", null, null, emptyList())
        assertEquals(0.0f, confidence, 0.01f)
    }

    // ============================================
    // Category Suggestion Logic Tests
    // ============================================

    @Test
    fun `suggestCategory returns Groceries for grocery merchants`() {
        val category = suggestTestCategory("Kroger", emptyList())
        assertEquals("Groceries", category)
    }

    @Test
    fun `suggestCategory returns Groceries for supermarket`() {
        val category = suggestTestCategory("Walmart Supercenter", emptyList())
        assertEquals("Groceries", category)
    }

    @Test
    fun `suggestCategory returns Food and Dining for restaurants`() {
        val category = suggestTestCategory("Starbucks", emptyList())
        assertEquals("Food & Dining", category)
    }

    @Test
    fun `suggestCategory returns Food and Dining for coffee shops`() {
        val category = suggestTestCategory("Local Coffee Shop", emptyList())
        assertEquals("Food & Dining", category)
    }

    @Test
    fun `suggestCategory returns Transportation for gas stations`() {
        val category = suggestTestCategory("Shell Gas Station", emptyList())
        assertEquals("Transportation", category)
    }

    @Test
    fun `suggestCategory returns Transportation for rideshare`() {
        val category = suggestTestCategory("Uber Trip", emptyList())
        assertEquals("Transportation", category)
    }

    @Test
    fun `suggestCategory returns Entertainment for movies`() {
        val category = suggestTestCategory("AMC Cinema", emptyList())
        assertEquals("Entertainment", category)
    }

    @Test
    fun `suggestCategory returns Health for pharmacy`() {
        val category = suggestTestCategory("CVS Pharmacy", emptyList())
        assertEquals("Health", category)
    }

    @Test
    fun `suggestCategory returns Shopping for stores`() {
        val category = suggestTestCategory("Amazon Store", emptyList())
        assertEquals("Shopping", category)
    }

    @Test
    fun `suggestCategory returns Bills for utilities`() {
        val category = suggestTestCategory("Electric Company", emptyList())
        assertEquals("Bills & Utilities", category)
    }

    @Test
    fun `suggestCategory returns Other for unknown merchants`() {
        val category = suggestTestCategory("Unknown Place XYZ", emptyList())
        assertEquals("Other", category)
    }

    @Test
    fun `suggestCategory uses items for categorization when merchant is null`() {
        val items = listOf(ReceiptItem("Coffee Latte", price = 4.50))
        val category = suggestTestCategory(null, items)
        assertEquals("Food & Dining", category)
    }

    // ============================================
    // Helper methods that mirror the private methods in ScannerViewModel
    // ============================================

    /**
     * Mirrors the calculateConfidence logic from ScannerViewModel.
     */
    private fun calculateTestConfidence(
        merchantName: String?,
        totalAmount: Double?,
        date: Date?,
        items: List<ReceiptItem>
    ): Float {
        var score = 0f
        if (!merchantName.isNullOrBlank()) score += 0.25f
        if (totalAmount != null && totalAmount > 0) score += 0.35f
        if (date != null) score += 0.2f
        if (items.isNotEmpty()) {
            score += minOf(0.2f, items.size * 0.04f)
        }
        return score
    }

    /**
     * Mirrors the suggestCategory logic from ScannerViewModel.
     */
    private fun suggestTestCategory(merchantName: String?, items: List<ReceiptItem>): String {
        val textToAnalyze = buildString {
            merchantName?.let { append(it.lowercase()) }
            append(" ")
            items.forEach { append(it.name.lowercase()) }
        }

        return when {
            textToAnalyze.containsAny(listOf("grocery", "supermarket", "market", "food", "produce", "dairy", "meat", "kroger", "walmart", "safeway", "whole foods", "trader joe")) -> "Groceries"
            textToAnalyze.containsAny(listOf("restaurant", "cafe", "coffee", "pizza", "burger", "sushi", "grill", "diner", "bistro", "starbucks", "mcdonald", "chipotle")) -> "Food & Dining"
            textToAnalyze.containsAny(listOf("gas", "fuel", "parking", "uber", "lyft", "taxi", "transit", "shell", "chevron", "exxon", "bp")) -> "Transportation"
            textToAnalyze.containsAny(listOf("cinema", "movie", "theater", "concert", "ticket", "netflix", "spotify", "game")) -> "Entertainment"
            textToAnalyze.containsAny(listOf("pharmacy", "drug", "medical", "doctor", "clinic", "hospital", "cvs", "walgreens", "rite aid")) -> "Health"
            textToAnalyze.containsAny(listOf("store", "shop", "mall", "amazon", "target", "costco", "best buy", "home depot")) -> "Shopping"
            textToAnalyze.containsAny(listOf("electric", "water", "gas", "internet", "phone", "bill", "utility")) -> "Bills & Utilities"
            else -> "Other"
        }
    }

    private fun String.containsAny(keywords: List<String>): Boolean {
        return keywords.any { this.contains(it) }
    }
}
