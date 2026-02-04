#!/usr/bin/env python
"""
PyInstaller Build Script for Finance Desktop Application.

This script provides configuration and utilities for building a Windows
executable using PyInstaller, including options for one-file and one-directory
builds, resource inclusion, and code signing preparation.
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

# ============================================================================
# Configuration
# ============================================================================

# Application metadata
APP_NAME = "Pecunia"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Personal Finance Management Application"
APP_AUTHOR = "Pecunia Team"
APP_COPYRIGHT = f"Copyright (c) {datetime.now().year} {APP_AUTHOR}"

# Path configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
RESOURCES_DIR = PROJECT_ROOT / "resources"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"

# Main entry point
MAIN_SCRIPT = SRC_DIR / "main.py"

# Icon configuration
ICON_PATH = RESOURCES_DIR / "icons" / "app_icon.ico"

# Additional data files to include
DATA_FILES = [
    # (source, destination_folder)
    (RESOURCES_DIR / "icons", "resources/icons"),
    (RESOURCES_DIR / "themes", "resources/themes"),
    (RESOURCES_DIR / "fonts", "resources/fonts"),
    (PROJECT_ROOT / "config", "config"),
]

# Hidden imports that PyInstaller might miss
HIDDEN_IMPORTS = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtCharts",
    "openpyxl",
    "reportlab",
    "reportlab.graphics",
    "reportlab.lib",
    "reportlab.platypus",
    "sqlite3",
    "json",
    "csv",
    "decimal",
    "datetime",
    "logging",
    "configparser",
    "cryptography",
    "requests",
]

# Modules to exclude (reduce size)
EXCLUDED_MODULES = [
    "tkinter",
    "matplotlib",
    "numpy",
    "pandas",
    "scipy",
    "PIL",
    "cv2",
    "tensorflow",
    "torch",
    "pytest",
    "unittest",
]

# Binaries to include (DLLs, etc.)
ADDITIONAL_BINARIES = [
    # (source_path, destination_folder)
]


# ============================================================================
# Version Info for Windows
# ============================================================================

def create_version_file(output_path: Path) -> None:
    """
    Create a version info file for Windows executable.

    Args:
        output_path: Path to write the version file
    """
    version_parts = APP_VERSION.split('.')
    while len(version_parts) < 4:
        version_parts.append('0')

    version_tuple = ', '.join(version_parts[:4])

    version_info = f'''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_tuple}),
    prodvers=({version_tuple}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{APP_AUTHOR}'),
        StringStruct(u'FileDescription', u'{APP_DESCRIPTION}'),
        StringStruct(u'FileVersion', u'{APP_VERSION}'),
        StringStruct(u'InternalName', u'{APP_NAME}'),
        StringStruct(u'LegalCopyright', u'{APP_COPYRIGHT}'),
        StringStruct(u'OriginalFilename', u'{APP_NAME}.exe'),
        StringStruct(u'ProductName', u'{APP_NAME}'),
        StringStruct(u'ProductVersion', u'{APP_VERSION}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(version_info)

    print(f"Created version file: {output_path}")


# ============================================================================
# Build Functions
# ============================================================================

def check_pyinstaller() -> bool:
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("ERROR: PyInstaller is not installed.")
        print("Install with: pip install pyinstaller")
        return False


def clean_build_directories() -> None:
    """Remove previous build artifacts."""
    print("\nCleaning build directories...")

    for directory in [BUILD_DIR, DIST_DIR]:
        if directory.exists():
            print(f"  Removing: {directory}")
            shutil.rmtree(directory)

    # Remove .spec file
    spec_file = PROJECT_ROOT / f"{APP_NAME}.spec"
    if spec_file.exists():
        print(f"  Removing: {spec_file}")
        spec_file.unlink()

    print("Clean complete.")


def build_data_args() -> List[str]:
    """Build --add-data arguments for PyInstaller."""
    args = []

    for source, dest in DATA_FILES:
        source_path = Path(source)
        if source_path.exists():
            # Windows uses ; as separator, Unix uses :
            separator = ';' if sys.platform == 'win32' else ':'
            args.extend(['--add-data', f'{source_path}{separator}{dest}'])
            print(f"  Including data: {source_path} -> {dest}")
        else:
            print(f"  WARNING: Data path not found: {source_path}")

    return args


def build_binary_args() -> List[str]:
    """Build --add-binary arguments for PyInstaller."""
    args = []

    for source, dest in ADDITIONAL_BINARIES:
        source_path = Path(source)
        if source_path.exists():
            separator = ';' if sys.platform == 'win32' else ':'
            args.extend(['--add-binary', f'{source_path}{separator}{dest}'])
            print(f"  Including binary: {source_path} -> {dest}")
        else:
            print(f"  WARNING: Binary path not found: {source_path}")

    return args


def build_hidden_import_args() -> List[str]:
    """Build --hidden-import arguments for PyInstaller."""
    args = []
    for module in HIDDEN_IMPORTS:
        args.extend(['--hidden-import', module])
    return args


def build_exclude_args() -> List[str]:
    """Build --exclude-module arguments for PyInstaller."""
    args = []
    for module in EXCLUDED_MODULES:
        args.extend(['--exclude-module', module])
    return args


def build_executable(
    one_file: bool = True,
    console: bool = False,
    debug: bool = False,
    clean: bool = True,
    upx: bool = False,
    sign: bool = False
) -> bool:
    """
    Build the Windows executable using PyInstaller.

    Args:
        one_file: Create a single executable file (vs directory)
        console: Show console window (for debugging)
        debug: Enable PyInstaller debug mode
        clean: Clean build directories before building
        upx: Use UPX compression (if available)
        sign: Prepare for code signing (placeholder)

    Returns:
        True if build succeeded, False otherwise
    """
    if not check_pyinstaller():
        return False

    if clean:
        clean_build_directories()

    print(f"\n{'='*60}")
    print(f"Building {APP_NAME} v{APP_VERSION}")
    print(f"{'='*60}")
    print(f"Mode: {'One-File' if one_file else 'One-Directory'}")
    print(f"Console: {'Enabled' if console else 'Disabled'}")
    print(f"Debug: {'Enabled' if debug else 'Disabled'}")
    print(f"{'='*60}\n")

    # Verify main script exists
    if not MAIN_SCRIPT.exists():
        print(f"ERROR: Main script not found: {MAIN_SCRIPT}")
        return False

    # Create version file
    version_file = BUILD_DIR / "version_info.txt"
    create_version_file(version_file)

    # Build PyInstaller command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name', APP_NAME,
        '--distpath', str(DIST_DIR),
        '--workpath', str(BUILD_DIR),
        '--specpath', str(PROJECT_ROOT),
    ]

    # One-file or one-directory
    if one_file:
        cmd.append('--onefile')
    else:
        cmd.append('--onedir')

    # Console or windowed
    if console:
        cmd.append('--console')
    else:
        cmd.append('--windowed')

    # Debug mode
    if debug:
        cmd.append('--debug=all')

    # UPX compression
    if upx:
        cmd.append('--upx-dir=upx')
    else:
        cmd.append('--noupx')

    # Icon
    if ICON_PATH.exists():
        cmd.extend(['--icon', str(ICON_PATH)])
        print(f"Using icon: {ICON_PATH}")
    else:
        print(f"WARNING: Icon not found: {ICON_PATH}")

    # Version info (Windows only)
    if sys.platform == 'win32' and version_file.exists():
        cmd.extend(['--version-file', str(version_file)])

    # Add data files
    print("\nIncluding data files:")
    cmd.extend(build_data_args())

    # Add binaries
    print("\nIncluding binaries:")
    cmd.extend(build_binary_args())

    # Hidden imports
    cmd.extend(build_hidden_import_args())

    # Excluded modules
    cmd.extend(build_exclude_args())

    # Additional options
    cmd.extend([
        '--noconfirm',  # Replace existing build without asking
        '--clean',      # Clean PyInstaller cache
    ])

    # Main script
    cmd.append(str(MAIN_SCRIPT))

    print(f"\nRunning PyInstaller...")
    print(f"Command: {' '.join(cmd[:10])}...")  # Show partial command
    print()

    # Execute build
    try:
        result = subprocess.run(cmd, check=True)

        # Determine output path
        if one_file:
            exe_path = DIST_DIR / f"{APP_NAME}.exe"
        else:
            exe_path = DIST_DIR / APP_NAME / f"{APP_NAME}.exe"

        if exe_path.exists():
            file_size = exe_path.stat().st_size / (1024 * 1024)  # MB
            print(f"\n{'='*60}")
            print(f"BUILD SUCCESSFUL!")
            print(f"{'='*60}")
            print(f"Output: {exe_path}")
            print(f"Size: {file_size:.2f} MB")

            if sign:
                print(f"\n{'='*60}")
                print("CODE SIGNING PREPARATION")
                print(f"{'='*60}")
                prepare_code_signing(exe_path)

            return True
        else:
            print(f"\nERROR: Expected output not found: {exe_path}")
            return False

    except subprocess.CalledProcessError as e:
        print(f"\nBUILD FAILED: {e}")
        return False
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return False


# ============================================================================
# Code Signing (Placeholder)
# ============================================================================

def prepare_code_signing(exe_path: Path) -> None:
    """
    Prepare executable for code signing.

    This is a placeholder for code signing integration.
    Actual implementation depends on your signing certificate and tools.

    Args:
        exe_path: Path to the executable to sign
    """
    print("\nCode signing preparation:")
    print("-" * 40)
    print("NOTE: Code signing requires a valid certificate.")
    print()
    print("For Windows code signing, you will need:")
    print("  1. A code signing certificate (.pfx or .p12 file)")
    print("  2. Windows SDK with signtool.exe")
    print()
    print("Example signtool command:")
    print(f'  signtool sign /f "certificate.pfx" /p "password" /t http://timestamp.digicert.com /d "{APP_NAME}" "{exe_path}"')
    print()
    print("For EV certificates with hardware tokens:")
    print(f'  signtool sign /n "Your Company Name" /t http://timestamp.digicert.com /d "{APP_NAME}" "{exe_path}"')
    print()

    # Create signing script template
    sign_script = DIST_DIR / "sign_executable.bat"
    sign_content = f'''@echo off
REM Code Signing Script for {APP_NAME}
REM Replace the placeholder values with your actual certificate details

SET SIGNTOOL="C:\\Program Files (x86)\\Windows Kits\\10\\bin\\x64\\signtool.exe"
SET CERT_PATH="path\\to\\your\\certificate.pfx"
SET CERT_PASSWORD="your_password"
SET TIMESTAMP_URL="http://timestamp.digicert.com"
SET EXE_PATH="{exe_path}"

echo Signing %EXE_PATH%...
%SIGNTOOL% sign /f %CERT_PATH% /p %CERT_PASSWORD% /t %TIMESTAMP_URL% /d "{APP_NAME}" %EXE_PATH%

IF %ERRORLEVEL% EQU 0 (
    echo.
    echo Signing successful!
    %SIGNTOOL% verify /pa %EXE_PATH%
) ELSE (
    echo.
    echo Signing failed with error code %ERRORLEVEL%
)

pause
'''

    with open(sign_script, 'w') as f:
        f.write(sign_content)

    print(f"Created signing script template: {sign_script}")
    print("Edit the script with your certificate details before running.")


# ============================================================================
# Spec File Generation
# ============================================================================

def generate_spec_file() -> Path:
    """
    Generate a custom .spec file for more control over the build.

    Returns:
        Path to the generated spec file
    """
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for {APP_NAME}
# Generated: {datetime.now().isoformat()}

import os
import sys
from pathlib import Path

block_cipher = None

# Paths
PROJECT_ROOT = Path(r'{PROJECT_ROOT}')
SRC_DIR = PROJECT_ROOT / 'src'
RESOURCES_DIR = PROJECT_ROOT / 'resources'

# Data files
datas = [
'''

    # Add data files
    for source, dest in DATA_FILES:
        source_path = Path(source)
        if source_path.exists():
            spec_content += f"    (r'{source_path}', r'{dest}'),\n"

    spec_content += ''']

# Binaries
binaries = [
'''

    # Add binaries
    for source, dest in ADDITIONAL_BINARIES:
        source_path = Path(source)
        if source_path.exists():
            spec_content += f"    (r'{source_path}', r'{dest}'),\n"

    spec_content += f''']

# Hidden imports
hiddenimports = {HIDDEN_IMPORTS}

# Excluded modules
excludes = {EXCLUDED_MODULES}

a = Analysis(
    [r'{MAIN_SCRIPT}'],
    pathex=[r'{SRC_DIR}'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# One-file executable
exe_onefile = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{APP_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'{ICON_PATH}' if Path(r'{ICON_PATH}').exists() else None,
)

# One-directory build (alternative)
exe_onedir = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{APP_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'{ICON_PATH}' if Path(r'{ICON_PATH}').exists() else None,
)

coll = COLLECT(
    exe_onedir,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='{APP_NAME}_dir',
)
'''

    spec_path = PROJECT_ROOT / f"{APP_NAME}.spec"
    with open(spec_path, 'w') as f:
        f.write(spec_content)

    print(f"Generated spec file: {spec_path}")
    return spec_path


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for the build script."""
    parser = argparse.ArgumentParser(
        description=f"Build {APP_NAME} Windows Executable",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_exe.py                    # Default one-file build
  python build_exe.py --onedir           # One-directory build
  python build_exe.py --console --debug  # Debug build with console
  python build_exe.py --sign             # Build with signing preparation
  python build_exe.py --spec-only        # Generate spec file only
        """
    )

    parser.add_argument(
        '--onefile',
        action='store_true',
        default=True,
        help='Create a single executable file (default)'
    )
    parser.add_argument(
        '--onedir',
        action='store_true',
        help='Create a directory with executable and dependencies'
    )
    parser.add_argument(
        '--console',
        action='store_true',
        help='Show console window (useful for debugging)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable PyInstaller debug mode'
    )
    parser.add_argument(
        '--no-clean',
        action='store_true',
        help='Skip cleaning build directories'
    )
    parser.add_argument(
        '--upx',
        action='store_true',
        help='Use UPX compression (requires UPX installed)'
    )
    parser.add_argument(
        '--sign',
        action='store_true',
        help='Prepare for code signing after build'
    )
    parser.add_argument(
        '--spec-only',
        action='store_true',
        help='Generate spec file only, do not build'
    )
    parser.add_argument(
        '--clean-only',
        action='store_true',
        help='Only clean build directories'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'{APP_NAME} Build Script v{APP_VERSION}'
    )

    args = parser.parse_args()

    # Handle clean-only
    if args.clean_only:
        clean_build_directories()
        return 0

    # Handle spec-only
    if args.spec_only:
        generate_spec_file()
        return 0

    # Determine build mode
    one_file = not args.onedir

    # Run build
    success = build_executable(
        one_file=one_file,
        console=args.console,
        debug=args.debug,
        clean=not args.no_clean,
        upx=args.upx,
        sign=args.sign
    )

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
