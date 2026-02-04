package com.pecunia.data.local.database

import androidx.room.TypeConverter
import com.pecunia.domain.model.AccountType
import com.pecunia.domain.model.BudgetPeriod
import com.pecunia.domain.model.CategoryType
import com.pecunia.domain.model.RecurrenceFrequency
import com.pecunia.domain.model.TransactionType
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.math.BigDecimal
import java.util.Date
import java.util.UUID

/**
 * Type converters for Room database.
 *
 * Room only supports primitive types and their boxed counterparts.
 * This class provides converters for complex types used in entities:
 * - Date <-> Long (timestamp)
 * - UUID <-> String
 * - BigDecimal <-> String (for precise monetary values)
 * - List<String> <-> JSON String
 * - Various Enums <-> String
 */
class Converters {

    private val gson = Gson()

    // ============================================
    // Date Converters
    // ============================================

    /**
     * Converts a timestamp (Long) to a Date object.
     * @param value Timestamp in milliseconds since epoch, or null
     * @return Date object or null if input is null
     */
    @TypeConverter
    fun fromTimestamp(value: Long?): Date? {
        return value?.let { Date(it) }
    }

    /**
     * Converts a Date object to a timestamp (Long).
     * @param date Date object or null
     * @return Timestamp in milliseconds since epoch, or null if input is null
     */
    @TypeConverter
    fun dateToTimestamp(date: Date?): Long? {
        return date?.time
    }

    // ============================================
    // UUID Converters
    // ============================================

    /**
     * Converts a String to a UUID object.
     * @param value UUID string representation, or null
     * @return UUID object or null if input is null
     */
    @TypeConverter
    fun fromUUIDString(value: String?): UUID? {
        return value?.let { UUID.fromString(it) }
    }

    /**
     * Converts a UUID object to its String representation.
     * @param uuid UUID object or null
     * @return String representation of UUID, or null if input is null
     */
    @TypeConverter
    fun uuidToString(uuid: UUID?): String? {
        return uuid?.toString()
    }

    // ============================================
    // BigDecimal Converters
    // ============================================

    /**
     * Converts a String to a BigDecimal.
     * Used for precise monetary value storage.
     * @param value String representation of decimal value, or null
     * @return BigDecimal object or null if input is null
     */
    @TypeConverter
    fun fromBigDecimalString(value: String?): BigDecimal? {
        return value?.let {
            try {
                BigDecimal(it)
            } catch (e: NumberFormatException) {
                BigDecimal.ZERO
            }
        }
    }

    /**
     * Converts a BigDecimal to its String representation.
     * Uses toPlainString() to avoid scientific notation.
     * @param bigDecimal BigDecimal object or null
     * @return String representation without scientific notation, or null if input is null
     */
    @TypeConverter
    fun bigDecimalToString(bigDecimal: BigDecimal?): String? {
        return bigDecimal?.toPlainString()
    }

    // ============================================
    // List<String> Converters
    // ============================================

    /**
     * Converts a JSON String to a List of Strings.
     * @param value JSON array string, or null
     * @return List of strings or null if input is null
     */
    @TypeConverter
    fun fromStringList(value: String?): List<String>? {
        if (value == null) return null
        val listType = object : TypeToken<List<String>>() {}.type
        return try {
            gson.fromJson(value, listType)
        } catch (e: Exception) {
            emptyList()
        }
    }

    /**
     * Converts a List of Strings to a JSON String.
     * @param list List of strings or null
     * @return JSON array string, or null if input is null
     */
    @TypeConverter
    fun stringListToJson(list: List<String>?): String? {
        return list?.let { gson.toJson(it) }
    }

    // ============================================
    // Map<String, String> Converters
    // ============================================

    /**
     * Converts a JSON String to a Map of String to String.
     * Useful for storing metadata or custom properties.
     * @param value JSON object string, or null
     * @return Map of strings or null if input is null
     */
    @TypeConverter
    fun fromStringMap(value: String?): Map<String, String>? {
        if (value == null) return null
        val mapType = object : TypeToken<Map<String, String>>() {}.type
        return try {
            gson.fromJson(value, mapType)
        } catch (e: Exception) {
            emptyMap()
        }
    }

    /**
     * Converts a Map of String to String to a JSON String.
     * @param map Map of strings or null
     * @return JSON object string, or null if input is null
     */
    @TypeConverter
    fun stringMapToJson(map: Map<String, String>?): String? {
        return map?.let { gson.toJson(it) }
    }

    // ============================================
    // TransactionType Enum Converters
    // ============================================

    /**
     * Converts a String to a TransactionType enum.
     * @param value Enum name string, or null
     * @return TransactionType enum value or null if input is null
     */
    @TypeConverter
    fun fromTransactionTypeString(value: String?): TransactionType? {
        return value?.let {
            try {
                TransactionType.valueOf(it)
            } catch (e: IllegalArgumentException) {
                TransactionType.EXPENSE // Default fallback
            }
        }
    }

    /**
     * Converts a TransactionType enum to its String name.
     * @param type TransactionType enum value or null
     * @return Enum name string, or null if input is null
     */
    @TypeConverter
    fun transactionTypeToString(type: TransactionType?): String? {
        return type?.name
    }

    // ============================================
    // AccountType Enum Converters
    // ============================================

    /**
     * Converts a String to an AccountType enum.
     * @param value Enum name string, or null
     * @return AccountType enum value or null if input is null
     */
    @TypeConverter
    fun fromAccountTypeString(value: String?): AccountType? {
        return value?.let {
            try {
                AccountType.valueOf(it)
            } catch (e: IllegalArgumentException) {
                AccountType.CHECKING // Default fallback
            }
        }
    }

    /**
     * Converts an AccountType enum to its String name.
     * @param type AccountType enum value or null
     * @return Enum name string, or null if input is null
     */
    @TypeConverter
    fun accountTypeToString(type: AccountType?): String? {
        return type?.name
    }

    // ============================================
    // CategoryType Enum Converters
    // ============================================

    /**
     * Converts a String to a CategoryType enum.
     * @param value Enum name string, or null
     * @return CategoryType enum value or null if input is null
     */
    @TypeConverter
    fun fromCategoryTypeString(value: String?): CategoryType? {
        return value?.let {
            try {
                CategoryType.valueOf(it)
            } catch (e: IllegalArgumentException) {
                CategoryType.EXPENSE // Default fallback
            }
        }
    }

    /**
     * Converts a CategoryType enum to its String name.
     * @param type CategoryType enum value or null
     * @return Enum name string, or null if input is null
     */
    @TypeConverter
    fun categoryTypeToString(type: CategoryType?): String? {
        return type?.name
    }

    // ============================================
    // BudgetPeriod Enum Converters
    // ============================================

    /**
     * Converts a String to a BudgetPeriod enum.
     * @param value Enum name string, or null
     * @return BudgetPeriod enum value or null if input is null
     */
    @TypeConverter
    fun fromBudgetPeriodString(value: String?): BudgetPeriod? {
        return value?.let {
            try {
                BudgetPeriod.valueOf(it)
            } catch (e: IllegalArgumentException) {
                BudgetPeriod.MONTHLY // Default fallback
            }
        }
    }

    /**
     * Converts a BudgetPeriod enum to its String name.
     * @param period BudgetPeriod enum value or null
     * @return Enum name string, or null if input is null
     */
    @TypeConverter
    fun budgetPeriodToString(period: BudgetPeriod?): String? {
        return period?.name
    }

    // ============================================
    // RecurrenceFrequency Enum Converters
    // ============================================

    /**
     * Converts a String to a RecurrenceFrequency enum.
     * @param value Enum name string, or null
     * @return RecurrenceFrequency enum value or null if input is null
     */
    @TypeConverter
    fun fromRecurrenceFrequencyString(value: String?): RecurrenceFrequency? {
        return value?.let {
            try {
                RecurrenceFrequency.valueOf(it)
            } catch (e: IllegalArgumentException) {
                RecurrenceFrequency.MONTHLY // Default fallback
            }
        }
    }

    /**
     * Converts a RecurrenceFrequency enum to its String name.
     * @param frequency RecurrenceFrequency enum value or null
     * @return Enum name string, or null if input is null
     */
    @TypeConverter
    fun recurrenceFrequencyToString(frequency: RecurrenceFrequency?): String? {
        return frequency?.name
    }

    // ============================================
    // List<Long> Converters (for IDs)
    // ============================================

    /**
     * Converts a JSON String to a List of Longs.
     * Useful for storing lists of IDs.
     * @param value JSON array string, or null
     * @return List of longs or null if input is null
     */
    @TypeConverter
    fun fromLongList(value: String?): List<Long>? {
        if (value == null) return null
        val listType = object : TypeToken<List<Long>>() {}.type
        return try {
            gson.fromJson(value, listType)
        } catch (e: Exception) {
            emptyList()
        }
    }

    /**
     * Converts a List of Longs to a JSON String.
     * @param list List of longs or null
     * @return JSON array string, or null if input is null
     */
    @TypeConverter
    fun longListToJson(list: List<Long>?): String? {
        return list?.let { gson.toJson(it) }
    }
}
