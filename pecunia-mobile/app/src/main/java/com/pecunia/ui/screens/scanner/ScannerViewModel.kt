package com.pecunia.ui.screens.scanner

import android.app.Application
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.TextRecognizer
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import java.io.IOException
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.regex.Pattern
import javax.inject.Inject
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

@HiltViewModel
class ScannerViewModel @Inject constructor(
    private val application: Application
) : AndroidViewModel(application) {

    private val _uiState = MutableStateFlow(ScannerUiState())
    val uiState: StateFlow<ScannerUiState> = _uiState.asStateFlow()

    private val textRecognizer: TextRecognizer = TextRecognition.getClient(
        TextRecognizerOptions.DEFAULT_OPTIONS
    )

    // Patterns for data extraction
    private val amountPattern = Pattern.compile(
        """(?:total|amount|sum|subtotal|grand\s*total)[:\s]*\$?(\d+[.,]\d{2})""",
        Pattern.CASE_INSENSITIVE
    )
    private val datePatterns = listOf(
        Pattern.compile("""(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"""),
        Pattern.compile("""(\d{4}[/-]\d{1,2}[/-]\d{1,2})"""),
        Pattern.compile("""([A-Za-z]{3,}\s+\d{1,2},?\s+\d{4})""")
    )
    private val pricePattern = Pattern.compile("""\$?(\d+[.,]\d{2})""")
    private val itemPattern = Pattern.compile("""^(.+?)\s+\$?(\d+[.,]\d{2})\s*$""", Pattern.MULTILINE)

    fun processImage(uri: Uri) {
        viewModelScope.launch {
            _uiState.update { it.copy(isProcessing = true, error = null) }

            try {
                val bitmap = loadBitmap(uri)
                val inputImage = InputImage.fromBitmap(bitmap, 0)
                val recognizedText = recognizeText(inputImage)
                val extractedData = extractReceiptData(recognizedText)

                _uiState.update {
                    it.copy(
                        isProcessing = false,
                        capturedImageUri = uri,
                        extractedData = extractedData
                    )
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error processing image", e)
                _uiState.update {
                    it.copy(
                        isProcessing = false,
                        error = "Failed to process image: ${e.message}"
                    )
                }
            }
        }
    }

    fun processImageFromGallery(uri: Uri) {
        processImage(uri)
    }

    private suspend fun loadBitmap(uri: Uri): Bitmap = withContext(Dispatchers.IO) {
        application.contentResolver.openInputStream(uri)?.use { inputStream ->
            BitmapFactory.decodeStream(inputStream)
        } ?: throw IOException("Failed to load image")
    }

    private suspend fun recognizeText(image: InputImage): String = suspendCancellableCoroutine { continuation ->
        textRecognizer.process(image)
            .addOnSuccessListener { visionText ->
                continuation.resume(visionText.text)
            }
            .addOnFailureListener { exception ->
                continuation.resumeWithException(exception)
            }
    }

    private fun extractReceiptData(rawText: String): ExtractedReceiptData {
        val lines = rawText.split("\n").map { it.trim() }.filter { it.isNotEmpty() }

        // Extract merchant name (usually first non-empty line)
        val merchantName = extractMerchantName(lines)

        // Extract total amount
        val totalAmount = extractTotalAmount(rawText)

        // Extract date
        val date = extractDate(rawText)

        // Extract line items
        val items = extractLineItems(lines)

        // Suggest category based on merchant and items
        val suggestedCategory = suggestCategory(merchantName, items)

        // Calculate confidence based on what was extracted
        val confidence = calculateConfidence(merchantName, totalAmount, date, items)

        return ExtractedReceiptData(
            rawText = rawText,
            merchantName = merchantName,
            totalAmount = totalAmount,
            date = date,
            items = items,
            suggestedCategory = suggestedCategory,
            confidence = confidence
        )
    }

    private fun extractMerchantName(lines: List<String>): String? {
        // Usually the merchant name is in the first few lines
        // Filter out common receipt headers
        val excludePatterns = listOf(
            "receipt", "invoice", "sale", "transaction", "date", "time",
            "store", "location", "address", "phone", "tel", "fax"
        )

        for (line in lines.take(5)) {
            val cleanLine = line.trim()
            if (cleanLine.length > 2 && cleanLine.length < 50) {
                val isExcluded = excludePatterns.any { pattern ->
                    cleanLine.lowercase().contains(pattern) &&
                    cleanLine.lowercase().startsWith(pattern)
                }
                if (!isExcluded && !cleanLine.contains("$") && !cleanLine.matches(Regex("^[\\d\\s\\-/]+$"))) {
                    return cleanLine
                }
            }
        }
        return null
    }

    private fun extractTotalAmount(text: String): Double? {
        // Try to find total amount with keyword
        val matcher = amountPattern.matcher(text)
        if (matcher.find()) {
            return parseAmount(matcher.group(1))
        }

        // If no total keyword found, look for the largest amount
        val amounts = mutableListOf<Double>()
        val priceMatcher = pricePattern.matcher(text)
        while (priceMatcher.find()) {
            parseAmount(priceMatcher.group(1))?.let { amounts.add(it) }
        }

        return amounts.maxOrNull()
    }

    private fun parseAmount(amountStr: String?): Double? {
        if (amountStr == null) return null
        return try {
            amountStr.replace(",", ".").toDouble()
        } catch (e: NumberFormatException) {
            null
        }
    }

    private fun extractDate(text: String): Date? {
        for (pattern in datePatterns) {
            val matcher = pattern.matcher(text)
            if (matcher.find()) {
                val dateStr = matcher.group(1)
                return parseDate(dateStr)
            }
        }
        return null
    }

    private fun parseDate(dateStr: String?): Date? {
        if (dateStr == null) return null

        val formats = listOf(
            "MM/dd/yyyy", "dd/MM/yyyy", "yyyy/MM/dd",
            "MM-dd-yyyy", "dd-MM-yyyy", "yyyy-MM-dd",
            "MM/dd/yy", "dd/MM/yy",
            "MMM dd, yyyy", "MMMM dd, yyyy", "MMM dd yyyy"
        )

        for (format in formats) {
            try {
                val sdf = SimpleDateFormat(format, Locale.US)
                sdf.isLenient = false
                return sdf.parse(dateStr)
            } catch (e: Exception) {
                // Try next format
            }
        }
        return null
    }

    private fun extractLineItems(lines: List<String>): List<ReceiptItem> {
        val items = mutableListOf<ReceiptItem>()

        for (line in lines) {
            val matcher = itemPattern.matcher(line)
            if (matcher.find()) {
                val itemName = matcher.group(1)?.trim()
                val price = parseAmount(matcher.group(2))

                if (itemName != null && price != null && itemName.length > 1) {
                    // Check if item name looks valid (not a total or tax line)
                    val excludeWords = listOf("total", "subtotal", "tax", "discount", "change", "cash", "card")
                    if (!excludeWords.any { itemName.lowercase().contains(it) }) {
                        items.add(ReceiptItem(name = itemName, price = price))
                    }
                }
            }
        }

        return items
    }

    private fun suggestCategory(merchantName: String?, items: List<ReceiptItem>): String {
        val textToAnalyze = buildString {
            merchantName?.let { append(it.lowercase()) }
            append(" ")
            items.forEach { append(it.name.lowercase()) }
        }

        return when {
            // Groceries
            textToAnalyze.containsAny(listOf("grocery", "supermarket", "market", "food", "produce", "dairy", "meat", "kroger", "walmart", "safeway", "whole foods", "trader joe")) -> "Groceries"

            // Restaurants & Dining
            textToAnalyze.containsAny(listOf("restaurant", "cafe", "coffee", "pizza", "burger", "sushi", "grill", "diner", "bistro", "starbucks", "mcdonald", "chipotle")) -> "Food & Dining"

            // Transportation
            textToAnalyze.containsAny(listOf("gas", "fuel", "parking", "uber", "lyft", "taxi", "transit", "shell", "chevron", "exxon", "bp")) -> "Transportation"

            // Entertainment
            textToAnalyze.containsAny(listOf("cinema", "movie", "theater", "concert", "ticket", "netflix", "spotify", "game")) -> "Entertainment"

            // Health
            textToAnalyze.containsAny(listOf("pharmacy", "drug", "medical", "doctor", "clinic", "hospital", "cvs", "walgreens", "rite aid")) -> "Health"

            // Shopping
            textToAnalyze.containsAny(listOf("store", "shop", "mall", "amazon", "target", "costco", "best buy", "home depot")) -> "Shopping"

            // Bills & Utilities
            textToAnalyze.containsAny(listOf("electric", "water", "gas", "internet", "phone", "bill", "utility")) -> "Bills & Utilities"

            else -> "Other"
        }
    }

    private fun String.containsAny(keywords: List<String>): Boolean {
        return keywords.any { this.contains(it) }
    }

    private fun calculateConfidence(
        merchantName: String?,
        totalAmount: Double?,
        date: Date?,
        items: List<ReceiptItem>
    ): Float {
        var score = 0f

        // Merchant name found
        if (!merchantName.isNullOrBlank()) score += 0.25f

        // Total amount found
        if (totalAmount != null && totalAmount > 0) score += 0.35f

        // Date found
        if (date != null) score += 0.2f

        // Items found
        if (items.isNotEmpty()) {
            score += minOf(0.2f, items.size * 0.04f)
        }

        return score
    }

    fun createTransaction(
        merchantName: String,
        amount: Double,
        date: Date,
        category: String,
        description: String,
        imageUri: Uri
    ) {
        viewModelScope.launch {
            _uiState.update { it.copy(isCreatingTransaction = true) }

            try {
                // Here you would call your repository to save the transaction
                // For now, we simulate a delay
                kotlinx.coroutines.delay(1000)

                // TODO: Implement actual transaction creation
                // transactionRepository.createTransaction(
                //     Transaction(
                //         merchantName = merchantName,
                //         amount = amount,
                //         date = date,
                //         category = category,
                //         description = description,
                //         receiptImageUri = imageUri.toString()
                //     )
                // )

                _uiState.update {
                    it.copy(
                        isCreatingTransaction = false,
                        transactionCreated = true
                    )
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error creating transaction", e)
                _uiState.update {
                    it.copy(
                        isCreatingTransaction = false,
                        error = "Failed to create transaction: ${e.message}"
                    )
                }
            }
        }
    }

    fun clearError() {
        _uiState.update { it.copy(error = null) }
    }

    fun resetState() {
        _uiState.value = ScannerUiState()
    }

    override fun onCleared() {
        super.onCleared()
        textRecognizer.close()
    }

    companion object {
        private const val TAG = "ScannerViewModel"
    }
}

data class ScannerUiState(
    val isProcessing: Boolean = false,
    val capturedImageUri: Uri? = null,
    val extractedData: ExtractedReceiptData? = null,
    val error: String? = null,
    val isCreatingTransaction: Boolean = false,
    val transactionCreated: Boolean = false
)

data class ExtractedReceiptData(
    val rawText: String,
    val merchantName: String?,
    val totalAmount: Double?,
    val date: Date?,
    val items: List<ReceiptItem>,
    val suggestedCategory: String?,
    val confidence: Float
)

data class ReceiptItem(
    val name: String,
    val quantity: Int? = null,
    val price: Double? = null
)
