# Pecunia Desktop - Python/PyQt6 Application

Offline-first desktop finance application built with Python and PyQt6.

## Overview

Pecunia Desktop provides a native desktop experience with:

- Offline-first architecture with local SQLite database
- Automatic sync with server when online
- Modern UI with Qt6 and custom themes
- Secure token storage via system keyring
- Background sync and notifications

## Architecture

```
pecunia-desktop/
├── src/
│   ├── api/                # API client layer
│   │   ├── client.py      # Base HTTP client (aiohttp)
│   │   ├── auth.py        # Authentication service
│   │   └── transactions.py # Transaction endpoints
│   ├── database/           # SQLAlchemy + SQLite
│   │   ├── connection.py  # Engine configuration
│   │   └── models/        # ORM models
│   ├── sync/              # Offline sync engine
│   │   ├── manager.py     # Sync orchestration
│   │   └── queue.py       # Operation queue
│   ├── ui/                # PyQt6 interface
│   │   ├── pages/         # Full-page views
│   │   └── widgets/       # Reusable components
│   └── main.py            # Application entry
└── resources/             # Icons, styles, etc.
```

## Quick Start

### Prerequisites

- Python 3.11+
- System keyring support (libsecret on Linux)

### Installation

```bash
# Navigate to project
cd pecunia-desktop

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run application
python src/main.py
```

### Development Mode

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run with debug logging
python src/main.py --debug

# Run tests
pytest tests/
```

## Configuration

Configuration is stored in platform-specific locations:

| Platform | Location |
|----------|----------|
| Windows | `%APPDATA%\Pecunia\config.json` |
| macOS | `~/Library/Application Support/Pecunia/config.json` |
| Linux | `~/.config/Pecunia/config.json` |

### Configuration Options

```json
{
  "api": {
    "base_url": "https://api.pecunia.com",
    "timeout": 30,
    "verify_ssl": true
  },
  "ui": {
    "theme": "dark",
    "language": "en",
    "currency": "EUR"
  },
  "sync": {
    "auto_sync_enabled": true,
    "auto_sync_interval": 900
  }
}
```

## Key Features

### Offline-First Sync

The application works fully offline:

1. All data stored in local SQLite database
2. Changes queued for sync when online
3. Conflict resolution with server data
4. Automatic retry on network recovery

### Secure Storage

- Tokens stored in system keyring (Keychain/Credential Manager)
- Database can be encrypted with SQLCipher
- No sensitive data in plain text files

### Background Sync

- Periodic sync every 15 minutes (configurable)
- Immediate sync on data changes when online
- Visual sync status indicator

## Building

### PyInstaller

```bash
# Build executable
pyinstaller build.spec

# Output in dist/Pecunia/
```

### Platform-Specific

```bash
# Windows installer (requires NSIS)
python scripts/build_windows.py

# macOS DMG
python scripts/build_macos.py

# Linux AppImage
python scripts/build_linux.py
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific module tests
pytest tests/test_sync/
```

## Conventions

See [DESKTOP_CONVENTIONS.md](./DESKTOP_CONVENTIONS.md) for Python/PyQt6 patterns.

## Related Documentation

- [MASTER_CONVENTIONS.md](../MASTER_CONVENTIONS.md) - Cross-platform conventions
- [SECURITY_GUIDELINES.md](../SECURITY_GUIDELINES.md) - Security requirements
- [SCALABILITY_GUIDELINES.md](../SCALABILITY_GUIDELINES.md) - Performance patterns

## Troubleshooting

### Keyring Issues (Linux)

```bash
# Install libsecret
sudo apt install libsecret-1-0 libsecret-1-dev

# Install Python bindings
pip install keyring[secretstorage]
```

### Database Corruption

```bash
# Backup current database
cp ~/.pecunia/pecunia.db ~/.pecunia/pecunia.db.bak

# Reset database (will trigger full sync)
rm ~/.pecunia/pecunia.db
```

## License

Proprietary - All rights reserved
