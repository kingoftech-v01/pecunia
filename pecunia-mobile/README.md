# FinanceApp Mobile - Android Application

Offline-first Android finance application built with Kotlin and Jetpack Compose.

## Overview

FinanceApp Mobile provides a native Android experience with:

- Clean Architecture with MVVM pattern
- Offline-first with Room database
- Modern UI with Jetpack Compose and Material 3
- Secure storage with EncryptedSharedPreferences
- Background sync with WorkManager

## Architecture

```
financeapp-mobile/
├── app/                     # Application module
│   └── src/main/java/com/financeapp/
│       ├── di/             # Hilt dependency injection
│       └── navigation/     # Navigation components
├── domain/                  # Domain layer
│   ├── models/             # Domain entities
│   ├── repository/         # Repository interfaces
│   └── usecases/           # Business logic
├── data/                    # Data layer
│   ├── local/              # Room database
│   ├── remote/             # Retrofit API
│   └── repository/         # Repository implementations
└── ui/                      # Presentation layer
    ├── screens/            # Compose screens + ViewModels
    ├── components/         # Reusable components
    └── theme/              # Material theme
```

## Quick Start

### Prerequisites

- Android Studio Hedgehog (2023.1.1) or newer
- JDK 17
- Android SDK 34

### Setup

1. Clone the repository
2. Open in Android Studio
3. Sync Gradle files
4. Create `local.properties` with SDK path
5. Run on device/emulator

### Build Variants

| Variant | Description |
|---------|-------------|
| `debug` | Development build with logging |
| `release` | Production build with ProGuard |

```bash
# Build debug APK
./gradlew assembleDebug

# Build release APK (requires signing config)
./gradlew assembleRelease

# Run tests
./gradlew test
```

## Configuration

### API Configuration

Update `NetworkModule.kt` for API base URL:

```kotlin
private const val BASE_URL = "https://api.financeapp.com/"
```

### Build Configuration

Key configurations in `app/build.gradle.kts`:

```kotlin
android {
    defaultConfig {
        applicationId = "com.financeapp"
        minSdk = 26
        targetSdk = 34
    }
}
```

## Key Features

### Offline-First Sync

1. All data stored in Room database
2. Changes tracked for sync
3. Background sync with WorkManager
4. Conflict resolution on sync

### Security

- Certificate pinning for API calls
- Encrypted token storage
- ProGuard obfuscation in release
- No sensitive data logging

### Modern UI

- Jetpack Compose for all screens
- Material 3 design
- Dark/light theme support
- Responsive layouts

## Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| Compose BOM | 2024.01.00 | UI framework |
| Hilt | 2.50 | Dependency injection |
| Room | 2.6.1 | Local database |
| Retrofit | 2.9.0 | HTTP client |
| OkHttp | 4.12.0 | HTTP client |

## Testing

```bash
# Unit tests
./gradlew test

# Instrumentation tests
./gradlew connectedAndroidTest

# All tests with coverage
./gradlew jacocoTestReport
```

### Test Structure

```
tests/
├── unit/
│   ├── repository/     # Repository tests
│   ├── viewmodel/      # ViewModel tests
│   └── usecase/        # Use case tests
└── integration/
    ├── database/       # Room tests
    └── api/            # API tests
```

## Conventions

See [MOBILE_CONVENTIONS.md](./MOBILE_CONVENTIONS.md) for Kotlin/Android patterns.

## Related Documentation

- [MASTER_CONVENTIONS.md](../MASTER_CONVENTIONS.md) - Cross-platform conventions
- [SECURITY_GUIDELINES.md](../SECURITY_GUIDELINES.md) - Security requirements
- [SCALABILITY_GUIDELINES.md](../SCALABILITY_GUIDELINES.md) - Performance patterns

## Release Process

1. Update version in `build.gradle.kts`
2. Create release branch
3. Build release APK/AAB
4. Test on multiple devices
5. Upload to Play Console

## Troubleshooting

### Build Issues

```bash
# Clean build
./gradlew clean

# Invalidate caches
# File > Invalidate Caches / Restart in Android Studio
```

### Database Issues

```kotlin
// Enable Room logging
Room.databaseBuilder(...)
    .setJournalMode(JournalMode.TRUNCATE)
    .setQueryCallback({ sqlQuery, bindArgs ->
        Log.d("Room", "Query: $sqlQuery")
    }, Executors.newSingleThreadExecutor())
```

## License

Proprietary - All rights reserved
