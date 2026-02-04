package com.pecunia.data.local.database

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.TypeConverter
import androidx.room.TypeConverters
import com.pecunia.data.local.database.dao.BudgetDao
import com.pecunia.data.local.database.dao.TransactionDao
import com.pecunia.data.local.database.entities.BudgetEntity
import com.pecunia.data.local.database.entities.BudgetPeriodType
import com.pecunia.data.local.database.entities.TransactionEntity
import com.pecunia.data.local.database.entities.TransactionType

/**
 * Room database for the Finance App.
 * Contains tables for transactions and budgets.
 */
@Database(
    entities = [
        TransactionEntity::class,
        BudgetEntity::class
    ],
    version = 1,
    exportSchema = true
)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {

    abstract fun transactionDao(): TransactionDao

    abstract fun budgetDao(): BudgetDao

    companion object {
        const val DATABASE_NAME = "finance_app_database"
    }
}

/**
 * Type converters for Room database.
 */
class Converters {

    // TransactionType converters

    @TypeConverter
    fun fromTransactionType(type: TransactionType): String {
        return type.name
    }

    @TypeConverter
    fun toTransactionType(value: String): TransactionType {
        return TransactionType.valueOf(value)
    }

    // BudgetPeriodType converters

    @TypeConverter
    fun fromBudgetPeriodType(type: BudgetPeriodType): String {
        return type.name
    }

    @TypeConverter
    fun toBudgetPeriodType(value: String): BudgetPeriodType {
        return BudgetPeriodType.valueOf(value)
    }

    // List<String> converters for tags

    @TypeConverter
    fun fromStringList(list: List<String>?): String? {
        return list?.joinToString(",")
    }

    @TypeConverter
    fun toStringList(value: String?): List<String>? {
        return value?.split(",")?.map { it.trim() }?.filter { it.isNotEmpty() }
    }
}
