package com.pecunia.ui.screens.scanner

import android.Manifest
import android.content.Context
import android.net.Uri
import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.pecunia.R
import com.pecunia.domain.models.TransactionCategory
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import kotlinx.coroutines.launch
import java.io.File
import java.math.BigDecimal
import java.text.SimpleDateFormat
import java.time.LocalDate
import java.util.*
import java.util.concurrent.Executors

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReceiptScannerScreen(
    onScanComplete: (ScannedReceiptData) -> Unit,
    onNavigateBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()

    var hasCameraPermission by remember { mutableStateOf(false) }
    var scanState by remember { mutableStateOf<ScanState>(ScanState.Ready) }
    var capturedImageUri by remember { mutableStateOf<Uri?>(null) }
    var scannedData by remember { mutableStateOf<ScannedReceiptData?>(null) }
    var showResultSheet by remember { mutableStateOf(false) }

    val cameraPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        hasCameraPermission = isGranted
    }

    val galleryLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri ->
        uri?.let {
            capturedImageUri = it
            scanState = ScanState.Processing
            processImage(context, it) { result ->
                scannedData = result
                scanState = ScanState.Completed
                showResultSheet = true
            }
        }
    }

    LaunchedEffect(Unit) {
        cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.scan_receipt)) },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.Close, contentDescription = stringResource(R.string.close))
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color.Transparent,
                    titleContentColor = Color.White,
                    navigationIconContentColor = Color.White
                )
            )
        }
    ) { paddingValues ->
        Box(
            modifier = modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(Color.Black)
        ) {
            when {
                !hasCameraPermission -> {
                    CameraPermissionRequest(
                        onRequestPermission = {
                            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
                        }
                    )
                }
                scanState == ScanState.Processing -> {
                    ProcessingOverlay()
                }
                else -> {
                    CameraPreview(
                        onImageCaptured = { uri ->
                            capturedImageUri = uri
                            scanState = ScanState.Processing
                            processImage(context, uri) { result ->
                                scannedData = result
                                scanState = ScanState.Completed
                                showResultSheet = true
                            }
                        },
                        onGalleryClick = {
                            galleryLauncher.launch("image/*")
                        }
                    )
                }
            }

            // Scan guide overlay
            if (hasCameraPermission && scanState == ScanState.Ready) {
                ScanGuideOverlay()
            }
        }

        // Result Bottom Sheet
        if (showResultSheet && scannedData != null) {
            ModalBottomSheet(
                onDismissRequest = {
                    showResultSheet = false
                    scanState = ScanState.Ready
                }
            ) {
                ScanResultContent(
                    scannedData = scannedData!!,
                    onConfirm = { data ->
                        onScanComplete(data)
                        showResultSheet = false
                    },
                    onRetry = {
                        showResultSheet = false
                        scanState = ScanState.Ready
                        scannedData = null
                    }
                )
            }
        }
    }
}

@Composable
private fun CameraPreview(
    onImageCaptured: (Uri) -> Unit,
    onGalleryClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current

    var imageCapture by remember { mutableStateOf<ImageCapture?>(null) }
    var isFlashOn by remember { mutableStateOf(false) }

    Box(modifier = modifier.fillMaxSize()) {
        AndroidView(
            factory = { ctx ->
                PreviewView(ctx).apply {
                    implementationMode = PreviewView.ImplementationMode.COMPATIBLE
                }
            },
            modifier = Modifier.fillMaxSize(),
            update = { previewView ->
                val cameraProviderFuture = ProcessCameraProvider.getInstance(context)

                cameraProviderFuture.addListener({
                    val cameraProvider = cameraProviderFuture.get()

                    val preview = Preview.Builder().build().also {
                        it.setSurfaceProvider(previewView.surfaceProvider)
                    }

                    imageCapture = ImageCapture.Builder()
                        .setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY)
                        .setFlashMode(
                            if (isFlashOn) ImageCapture.FLASH_MODE_ON
                            else ImageCapture.FLASH_MODE_OFF
                        )
                        .build()

                    val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

                    try {
                        cameraProvider.unbindAll()
                        cameraProvider.bindToLifecycle(
                            lifecycleOwner,
                            cameraSelector,
                            preview,
                            imageCapture
                        )
                    } catch (e: Exception) {
                        Log.e("ReceiptScanner", "Camera binding failed", e)
                    }
                }, ContextCompat.getMainExecutor(context))
            }
        )

        // Camera Controls
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Tips
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = Color.Black.copy(alpha = 0.6f)
                ),
                shape = RoundedCornerShape(8.dp)
            ) {
                Text(
                    text = stringResource(R.string.scan_tip),
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.White,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                )
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Control buttons row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Gallery button
                IconButton(
                    onClick = onGalleryClick,
                    modifier = Modifier
                        .size(56.dp)
                        .clip(CircleShape)
                        .background(Color.White.copy(alpha = 0.2f))
                ) {
                    Icon(
                        Icons.Default.PhotoLibrary,
                        contentDescription = stringResource(R.string.gallery),
                        tint = Color.White,
                        modifier = Modifier.size(28.dp)
                    )
                }

                // Capture button
                IconButton(
                    onClick = {
                        imageCapture?.let { capture ->
                            val photoFile = File(
                                context.cacheDir,
                                "receipt_${System.currentTimeMillis()}.jpg"
                            )

                            val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()

                            capture.takePicture(
                                outputOptions,
                                Executors.newSingleThreadExecutor(),
                                object : ImageCapture.OnImageSavedCallback {
                                    override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                                        onImageCaptured(Uri.fromFile(photoFile))
                                    }

                                    override fun onError(exception: ImageCaptureException) {
                                        Log.e("ReceiptScanner", "Photo capture failed", exception)
                                    }
                                }
                            )
                        }
                    },
                    modifier = Modifier
                        .size(80.dp)
                        .clip(CircleShape)
                        .background(Color.White)
                        .border(4.dp, Color.White.copy(alpha = 0.5f), CircleShape)
                ) {
                    Icon(
                        Icons.Default.CameraAlt,
                        contentDescription = stringResource(R.string.capture),
                        tint = Color.Black,
                        modifier = Modifier.size(36.dp)
                    )
                }

                // Flash button
                IconButton(
                    onClick = { isFlashOn = !isFlashOn },
                    modifier = Modifier
                        .size(56.dp)
                        .clip(CircleShape)
                        .background(
                            if (isFlashOn) Color.Yellow.copy(alpha = 0.3f)
                            else Color.White.copy(alpha = 0.2f)
                        )
                ) {
                    Icon(
                        if (isFlashOn) Icons.Default.FlashOn else Icons.Default.FlashOff,
                        contentDescription = stringResource(R.string.flash),
                        tint = Color.White,
                        modifier = Modifier.size(28.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}

@Composable
private fun ScanGuideOverlay(
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        // Receipt frame guide
        Box(
            modifier = Modifier
                .fillMaxWidth(0.85f)
                .fillMaxHeight(0.6f)
                .border(
                    width = 2.dp,
                    color = Color.White.copy(alpha = 0.6f),
                    shape = RoundedCornerShape(12.dp)
                )
        ) {
            // Corner indicators
            CornerIndicator(modifier = Modifier.align(Alignment.TopStart))
            CornerIndicator(modifier = Modifier
                .align(Alignment.TopEnd)
                .scale(scaleX = -1f, scaleY = 1f))
            CornerIndicator(modifier = Modifier
                .align(Alignment.BottomStart)
                .scale(scaleX = 1f, scaleY = -1f))
            CornerIndicator(modifier = Modifier
                .align(Alignment.BottomEnd)
                .scale(scaleX = -1f, scaleY = -1f))
        }
    }
}

@Composable
private fun CornerIndicator(modifier: Modifier = Modifier) {
    Box(modifier = modifier.size(24.dp)) {
        Box(
            modifier = Modifier
                .width(24.dp)
                .height(3.dp)
                .background(Color.White)
        )
        Box(
            modifier = Modifier
                .width(3.dp)
                .height(24.dp)
                .background(Color.White)
        )
    }
}

private fun Modifier.scale(scaleX: Float, scaleY: Float): Modifier {
    return this.then(
        Modifier.graphicsLayer(
            scaleX = scaleX,
            scaleY = scaleY
        )
    )
}

@Composable
private fun ProcessingOverlay(
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.8f)),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            CircularProgressIndicator(
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(64.dp)
            )
            Spacer(modifier = Modifier.height(24.dp))
            Text(
                text = stringResource(R.string.processing_receipt),
                style = MaterialTheme.typography.titleMedium,
                color = Color.White
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.extracting_information),
                style = MaterialTheme.typography.bodyMedium,
                color = Color.White.copy(alpha = 0.7f)
            )
        }
    }
}

@Composable
private fun CameraPermissionRequest(
    onRequestPermission: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = Icons.Outlined.CameraAlt,
            contentDescription = null,
            modifier = Modifier.size(80.dp),
            tint = Color.White.copy(alpha = 0.7f)
        )
        Spacer(modifier = Modifier.height(24.dp))
        Text(
            text = stringResource(R.string.camera_permission_title),
            style = MaterialTheme.typography.titleLarge,
            color = Color.White,
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = stringResource(R.string.camera_permission_description),
            style = MaterialTheme.typography.bodyMedium,
            color = Color.White.copy(alpha = 0.7f),
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(32.dp))
        Button(onClick = onRequestPermission) {
            Text(stringResource(R.string.grant_permission))
        }
    }
}

@Composable
private fun ScanResultContent(
    scannedData: ScannedReceiptData,
    onConfirm: (ScannedReceiptData) -> Unit,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier
) {
    var editedAmount by remember { mutableStateOf(scannedData.totalAmount?.toPlainString() ?: "") }
    var editedMerchant by remember { mutableStateOf(scannedData.merchantName ?: "") }
    var editedDate by remember { mutableStateOf(scannedData.date ?: LocalDate.now()) }
    var selectedCategory by remember { mutableStateOf(scannedData.suggestedCategory) }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(24.dp)
    ) {
        // Header
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = stringResource(R.string.scan_results),
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )
            if (scannedData.confidence >= 0.8f) {
                AssistChip(
                    onClick = { },
                    label = { Text(stringResource(R.string.high_confidence)) },
                    leadingIcon = {
                        Icon(
                            Icons.Default.CheckCircle,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                    },
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer
                    )
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Amount Field
        OutlinedTextField(
            value = editedAmount,
            onValueChange = { editedAmount = it },
            label = { Text(stringResource(R.string.total_amount)) },
            leadingIcon = {
                Icon(Icons.Default.AttachMoney, contentDescription = null)
            },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        Spacer(modifier = Modifier.height(16.dp))

        // Merchant Field
        OutlinedTextField(
            value = editedMerchant,
            onValueChange = { editedMerchant = it },
            label = { Text(stringResource(R.string.merchant)) },
            leadingIcon = {
                Icon(Icons.Default.Store, contentDescription = null)
            },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        Spacer(modifier = Modifier.height(16.dp))

        // Date Field (simplified - in production use DatePicker)
        OutlinedTextField(
            value = editedDate.toString(),
            onValueChange = { },
            label = { Text(stringResource(R.string.date)) },
            leadingIcon = {
                Icon(Icons.Default.CalendarToday, contentDescription = null)
            },
            modifier = Modifier.fillMaxWidth(),
            readOnly = true,
            singleLine = true
        )

        Spacer(modifier = Modifier.height(16.dp))

        // Category Selector
        Text(
            text = stringResource(R.string.suggested_category),
            style = MaterialTheme.typography.labelLarge,
            modifier = Modifier.padding(bottom = 8.dp)
        )

        FlowRow(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            TransactionCategory.expenseCategories().take(6).forEach { category ->
                FilterChip(
                    selected = selectedCategory == category,
                    onClick = { selectedCategory = category },
                    label = { Text(category.displayName) }
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Extracted Items (if available)
        if (scannedData.lineItems.isNotEmpty()) {
            Text(
                text = stringResource(R.string.extracted_items),
                style = MaterialTheme.typography.labelLarge,
                modifier = Modifier.padding(bottom = 8.dp)
            )

            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant
                )
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    scannedData.lineItems.take(5).forEach { item ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = item.description,
                                style = MaterialTheme.typography.bodySmall,
                                modifier = Modifier.weight(1f)
                            )
                            item.amount?.let { amount ->
                                Text(
                                    text = "$${amount}",
                                    style = MaterialTheme.typography.bodySmall,
                                    fontWeight = FontWeight.Medium
                                )
                            }
                        }
                    }
                }
            }
        }

        // Raw Text Preview (collapsible)
        if (scannedData.rawText.isNotBlank()) {
            var showRawText by remember { mutableStateOf(false) }

            Spacer(modifier = Modifier.height(16.dp))

            TextButton(
                onClick = { showRawText = !showRawText }
            ) {
                Icon(
                    if (showRawText) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                    contentDescription = null
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(stringResource(R.string.show_raw_text))
            }

            AnimatedVisibility(visible = showRawText) {
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant
                    )
                ) {
                    Text(
                        text = scannedData.rawText,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(12.dp)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(32.dp))

        // Action Buttons
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            OutlinedButton(
                onClick = onRetry,
                modifier = Modifier.weight(1f)
            ) {
                Icon(Icons.Default.Refresh, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text(stringResource(R.string.scan_again))
            }

            Button(
                onClick = {
                    onConfirm(
                        scannedData.copy(
                            totalAmount = editedAmount.toBigDecimalOrNull(),
                            merchantName = editedMerchant.takeIf { it.isNotBlank() },
                            date = editedDate,
                            suggestedCategory = selectedCategory
                        )
                    )
                },
                modifier = Modifier.weight(1f)
            ) {
                Icon(Icons.Default.Check, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text(stringResource(R.string.create_transaction))
            }
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
private fun FlowRow(
    modifier: Modifier = Modifier,
    horizontalArrangement: Arrangement.Horizontal = Arrangement.Start,
    content: @Composable () -> Unit
) {
    // Simplified FlowRow - in production use accompanist FlowRow
    Row(
        modifier = modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = horizontalArrangement
    ) {
        content()
    }
}

@Composable
private fun Modifier.horizontalScroll(state: androidx.compose.foundation.ScrollState): Modifier {
    return this.then(Modifier.horizontalScroll(state))
}

/**
 * Process the captured image using ML Kit Text Recognition.
 */
private fun processImage(
    context: Context,
    imageUri: Uri,
    onResult: (ScannedReceiptData) -> Unit
) {
    try {
        val image = InputImage.fromFilePath(context, imageUri)
        val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)

        recognizer.process(image)
            .addOnSuccessListener { visionText ->
                val result = parseReceiptText(visionText.text)
                onResult(result.copy(imageUri = imageUri))
            }
            .addOnFailureListener { e ->
                Log.e("ReceiptScanner", "Text recognition failed", e)
                onResult(
                    ScannedReceiptData(
                        rawText = "",
                        confidence = 0f,
                        imageUri = imageUri
                    )
                )
            }
    } catch (e: Exception) {
        Log.e("ReceiptScanner", "Image processing failed", e)
        onResult(
            ScannedReceiptData(
                rawText = "",
                confidence = 0f,
                imageUri = imageUri
            )
        )
    }
}

/**
 * Parse the recognized text to extract receipt information.
 */
private fun parseReceiptText(text: String): ScannedReceiptData {
    val lines = text.split("\n").map { it.trim() }.filter { it.isNotBlank() }

    // Extract total amount (look for patterns like "Total: $XX.XX" or just "$XX.XX")
    val amountPattern = Regex("""(?:total|amount|sum|due|subtotal)[:\s]*\$?(\d+[.,]\d{2})""", RegexOption.IGNORE_CASE)
    val simpleAmountPattern = Regex("""\$(\d+[.,]\d{2})""")

    var totalAmount: BigDecimal? = null
    amountPattern.find(text)?.let { match ->
        totalAmount = match.groupValues[1].replace(",", ".").toBigDecimalOrNull()
    }
    if (totalAmount == null) {
        // Find the largest amount as a fallback
        val amounts = simpleAmountPattern.findAll(text)
            .mapNotNull { it.groupValues[1].replace(",", ".").toBigDecimalOrNull() }
            .toList()
        totalAmount = amounts.maxOrNull()
    }

    // Extract merchant name (usually at the top of the receipt)
    val merchantName = lines.firstOrNull()?.takeIf { it.length in 3..50 }

    // Extract date
    val datePatterns = listOf(
        Regex("""(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})"""),
        Regex("""(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})"""),
        Regex("""((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})""", RegexOption.IGNORE_CASE)
    )

    var date: LocalDate? = null
    for (pattern in datePatterns) {
        pattern.find(text)?.let { match ->
            date = try {
                parseDate(match.value)
            } catch (e: Exception) {
                null
            }
        }
        if (date != null) break
    }

    // Extract line items
    val lineItems = mutableListOf<ReceiptLineItem>()
    val itemPattern = Regex("""(.+?)\s+\$?(\d+[.,]\d{2})$""")

    for (line in lines) {
        itemPattern.find(line)?.let { match ->
            val description = match.groupValues[1].trim()
            val amount = match.groupValues[2].replace(",", ".").toBigDecimalOrNull()
            if (description.length in 2..50 && amount != null) {
                lineItems.add(ReceiptLineItem(description, amount))
            }
        }
    }

    // Suggest category based on merchant name or items
    val suggestedCategory = suggestCategory(merchantName, lineItems.map { it.description })

    // Calculate confidence based on what was extracted
    val confidence = calculateConfidence(totalAmount, merchantName, date, lineItems)

    return ScannedReceiptData(
        rawText = text,
        totalAmount = totalAmount,
        merchantName = merchantName,
        date = date ?: LocalDate.now(),
        lineItems = lineItems,
        suggestedCategory = suggestedCategory,
        confidence = confidence
    )
}

private fun parseDate(dateStr: String): LocalDate {
    val formats = listOf(
        SimpleDateFormat("MM/dd/yyyy", Locale.US),
        SimpleDateFormat("MM-dd-yyyy", Locale.US),
        SimpleDateFormat("yyyy-MM-dd", Locale.US),
        SimpleDateFormat("MM/dd/yy", Locale.US),
        SimpleDateFormat("MMM dd, yyyy", Locale.US)
    )

    for (format in formats) {
        try {
            val date = format.parse(dateStr)
            if (date != null) {
                val calendar = Calendar.getInstance()
                calendar.time = date
                return LocalDate.of(
                    calendar.get(Calendar.YEAR),
                    calendar.get(Calendar.MONTH) + 1,
                    calendar.get(Calendar.DAY_OF_MONTH)
                )
            }
        } catch (e: Exception) {
            continue
        }
    }

    throw IllegalArgumentException("Unable to parse date: $dateStr")
}

private fun suggestCategory(
    merchantName: String?,
    items: List<String>
): TransactionCategory {
    val text = (merchantName ?: "") + " " + items.joinToString(" ")
    val lowerText = text.lowercase()

    return when {
        lowerText.containsAny("restaurant", "cafe", "coffee", "pizza", "burger", "food") ->
            TransactionCategory.FOOD
        lowerText.containsAny("grocery", "supermarket", "market", "walmart", "costco", "kroger") ->
            TransactionCategory.GROCERIES
        lowerText.containsAny("gas", "fuel", "shell", "exxon", "chevron", "uber", "lyft") ->
            TransactionCategory.TRANSPORTATION
        lowerText.containsAny("electric", "water", "gas bill", "utility", "power") ->
            TransactionCategory.UTILITIES
        lowerText.containsAny("movie", "cinema", "netflix", "spotify", "entertainment") ->
            TransactionCategory.ENTERTAINMENT
        lowerText.containsAny("amazon", "target", "shop", "store", "mall") ->
            TransactionCategory.SHOPPING
        lowerText.containsAny("pharmacy", "doctor", "hospital", "medical", "cvs", "walgreens") ->
            TransactionCategory.HEALTHCARE
        else -> TransactionCategory.OTHER_EXPENSE
    }
}

private fun String.containsAny(vararg keywords: String): Boolean {
    return keywords.any { this.contains(it, ignoreCase = true) }
}

private fun calculateConfidence(
    amount: BigDecimal?,
    merchant: String?,
    date: LocalDate?,
    items: List<ReceiptLineItem>
): Float {
    var score = 0f

    if (amount != null) score += 0.4f
    if (merchant != null && merchant.length > 2) score += 0.2f
    if (date != null) score += 0.2f
    if (items.isNotEmpty()) score += 0.2f

    return score.coerceIn(0f, 1f)
}

/**
 * State of the scanning process.
 */
sealed class ScanState {
    object Ready : ScanState()
    object Processing : ScanState()
    object Completed : ScanState()
    data class Error(val message: String) : ScanState()
}

/**
 * Data extracted from a scanned receipt.
 */
data class ScannedReceiptData(
    val rawText: String,
    val totalAmount: BigDecimal? = null,
    val merchantName: String? = null,
    val date: LocalDate? = null,
    val lineItems: List<ReceiptLineItem> = emptyList(),
    val suggestedCategory: TransactionCategory = TransactionCategory.OTHER_EXPENSE,
    val confidence: Float = 0f,
    val imageUri: Uri? = null
)

/**
 * A single line item from a receipt.
 */
data class ReceiptLineItem(
    val description: String,
    val amount: BigDecimal?
)

private fun Modifier.graphicsLayer(scaleX: Float, scaleY: Float): Modifier {
    return this.then(
        androidx.compose.ui.draw.scale(scaleX, scaleY)
    )
}

private fun androidx.compose.ui.draw.scale(scaleX: Float, scaleY: Float): Modifier {
    return Modifier.then(
        Modifier.graphicsLayer {
            this.scaleX = scaleX
            this.scaleY = scaleY
        }
    )
}
