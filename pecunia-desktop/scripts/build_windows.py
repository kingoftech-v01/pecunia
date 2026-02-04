#!/usr/bin/env python3
"""
Pecunia Desktop - Windows Build Script

PyInstaller configuration and build process for Windows executables.
Supports one-file/one-directory builds, UPX compression, code signing,
and NSIS installer creation.

Usage:
    python scripts/build_windows.py              # Default build
    python scripts/build_windows.py --onedir     # One-directory build
    python scripts/build_windows.py --upx        # With UPX compression
    python scripts/build_windows.py --sign       # With code signing
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# Path Configuration
# =============================================================================

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
RESOURCES_DIR = PROJECT_ROOT / "resources"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
INSTALLER_DIR = PROJECT_ROOT / "installer" / "windows"

# Main entry point
MAIN_SCRIPT = SRC_DIR / "main.py"

# Icon paths
ICON_ICO = RESOURCES_DIR / "icons" / "app_icon.ico"
ICON_PNG = RESOURCES_DIR / "icons" / "app_icon.png"


# =============================================================================
# Application Metadata
# =============================================================================

APP_NAME = "Pecunia"
APP_DESCRIPTION = "Personal Finance Management Application"
APP_AUTHOR = "Pecunia Inc."
APP_COMPANY = "Pecunia Inc."
APP_COPYRIGHT = f"Copyright (c) {datetime.now().year} {APP_AUTHOR}"
APP_WEBSITE = "https://pecunia.com"


# =============================================================================
# PyInstaller Configuration
# =============================================================================

# Data files to include (source, destination)
DATA_FILES: List[Tuple[Path, str]] = [
    (RESOURCES_DIR / "icons", "resources/icons"),
    (RESOURCES_DIR / "styles", "resources/styles"),
    (SRC_DIR / "i18n" / "translations", "i18n/translations"),
]

# Hidden imports that PyInstaller might miss
HIDDEN_IMPORTS: List[str] = [
    # PyQt6 modules
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtCharts",
    "PyQt6.QtNetwork",
    "PyQt6.sip",
    # Database
    "sqlite3",
    "aiosqlite",
    "sqlalchemy.dialects.sqlite",
    # Async
    "asyncio",
    "aiohttp",
    "qasync",
    # Security
    "keyring.backends.Windows",
    "cryptography",
    "cryptography.fernet",
    # Export
    "reportlab",
    "reportlab.graphics",
    "reportlab.lib",
    "reportlab.platypus",
    "openpyxl",
    # Data processing
    "pandas",
    "pandas._libs.tslibs.timedeltas",
    "python_dateutil",
    # Standard library
    "json",
    "csv",
    "decimal",
    "datetime",
    "logging",
    "configparser",
    "pathlib",
    "typing",
    # Pydantic
    "pydantic",
    "pydantic_settings",
    "pydantic.deprecated.decorator",
]

# Modules to exclude (reduce size)
EXCLUDED_MODULES: List[str] = [
    "tkinter",
    "matplotlib",
    "scipy",
    "PIL",
    "cv2",
    "tensorflow",
    "torch",
    "pytest",
    "unittest",
    "test",
    "tests",
    "_pytest",
    "IPython",
    "jupyter",
    "notebook",
]

# Binary files to collect
COLLECT_BINARIES: List[str] = [
    # Add any DLLs or binary dependencies
]

# Runtime hooks
RUNTIME_HOOKS: List[Path] = [
    # Add any runtime hook scripts
]


# =============================================================================
# Build Result (imported from build.py or defined here)
# =============================================================================

@dataclass
class BuildResult:
    """Result of a build operation."""
    success: bool
    platform: str
    version: str
    output_path: Optional[Path] = None
    installer_path: Optional[Path] = None
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


# =============================================================================
# Windows Builder
# =============================================================================

class WindowsBuilder:
    """Windows-specific build implementation."""

    def __init__(self, config: Any = None):
        """
        Initialize Windows builder.

        Args:
            config: Build configuration object
        """
        self.config = config
        self._version = getattr(config, "version", "1.0.0") if config else "1.0.0"
        self._one_file = getattr(config, "one_file", True) if config else True
        self._console = getattr(config, "console", False) if config else False
        self._debug = getattr(config, "debug", False) if config else False
        self._upx_enabled = getattr(config, "upx_enabled", False) if config else False
        self._upx_dir = getattr(config, "upx_dir", None) if config else None
        self._sign_enabled = getattr(config, "sign_enabled", False) if config else False
        self._sign_cert = getattr(config, "sign_certificate", None) if config else None
        self._create_installer = getattr(config, "create_installer", True) if config else True
        self._output_name = getattr(config, "output_name", APP_NAME) if config else APP_NAME
        self.warnings: List[str] = []

    def build(self) -> BuildResult:
        """
        Execute the Windows build process.

        Returns:
            BuildResult with build status and output paths.
        """
        print(f"\n{'='*60}")
        print(f"Windows Build - {APP_NAME} v{self._version}")
        print(f"{'='*60}")
        print(f"Mode: {'One-File' if self._one_file else 'One-Directory'}")
        print(f"Console: {'Enabled' if self._console else 'Disabled'}")
        print(f"UPX: {'Enabled' if self._upx_enabled else 'Disabled'}")
        print(f"Sign: {'Enabled' if self._sign_enabled else 'Disabled'}")
        print(f"{'='*60}\n")

        try:
            # Verify prerequisites
            if not self._verify_prerequisites():
                return BuildResult(
                    success=False,
                    platform="windows",
                    version=self._version,
                    error_message="Prerequisites verification failed",
                    warnings=self.warnings,
                )

            # Create version info file
            version_file = self._create_version_file()

            # Build PyInstaller command
            cmd = self._build_pyinstaller_command(version_file)

            # Execute PyInstaller
            print("Running PyInstaller...")
            result = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print(f"PyInstaller STDERR:\n{result.stderr}")
                return BuildResult(
                    success=False,
                    platform="windows",
                    version=self._version,
                    error_message=f"PyInstaller failed: {result.stderr[:500]}",
                    warnings=self.warnings,
                )

            # Determine output path
            if self._one_file:
                output_path = DIST_DIR / f"{self._output_name}.exe"
            else:
                output_path = DIST_DIR / self._output_name / f"{self._output_name}.exe"

            if not output_path.exists():
                return BuildResult(
                    success=False,
                    platform="windows",
                    version=self._version,
                    error_message=f"Output not found: {output_path}",
                    warnings=self.warnings,
                )

            # Print executable info
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"\nExecutable created: {output_path}")
            print(f"Size: {size_mb:.2f} MB")

            # Sign executable if enabled
            if self._sign_enabled:
                self._sign_executable(output_path)

            # Create installer if enabled
            installer_path = None
            if self._create_installer:
                installer_path = self._create_nsis_installer(output_path)

            print(f"\n{'='*60}")
            print("BUILD SUCCESSFUL!")
            print(f"{'='*60}")

            return BuildResult(
                success=True,
                platform="windows",
                version=self._version,
                output_path=output_path,
                installer_path=installer_path,
                warnings=self.warnings,
            )

        except Exception as e:
            return BuildResult(
                success=False,
                platform="windows",
                version=self._version,
                error_message=str(e),
                warnings=self.warnings,
            )

    def _verify_prerequisites(self) -> bool:
        """Verify all build prerequisites are met."""
        print("Verifying prerequisites...")

        # Check main script
        if not MAIN_SCRIPT.exists():
            print(f"ERROR: Main script not found: {MAIN_SCRIPT}")
            return False
        print(f"  [OK] Main script: {MAIN_SCRIPT}")

        # Check PyInstaller
        try:
            import PyInstaller
            print(f"  [OK] PyInstaller: {PyInstaller.__version__}")
        except ImportError:
            print("  [ERROR] PyInstaller not installed")
            return False

        # Check icon
        if ICON_ICO.exists():
            print(f"  [OK] Icon: {ICON_ICO}")
        else:
            self.warnings.append(f"Icon not found: {ICON_ICO}")
            print(f"  [WARN] Icon not found: {ICON_ICO}")

        # Check UPX if enabled
        if self._upx_enabled:
            upx_path = self._upx_dir or shutil.which("upx")
            if upx_path:
                print(f"  [OK] UPX: {upx_path}")
            else:
                self.warnings.append("UPX not found, compression disabled")
                print("  [WARN] UPX not found, disabling compression")
                self._upx_enabled = False

        return True

    def _create_version_file(self) -> Path:
        """Create Windows version info file for the executable."""
        print("Creating version info file...")

        version_parts = self._version.split(".")
        while len(version_parts) < 4:
            version_parts.append("0")
        version_tuple = ", ".join(version_parts[:4])

        version_info = f'''# UTF-8
#
# Windows Version Information
# Generated by Pecunia build system
#
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
        [StringStruct(u'CompanyName', u'{APP_COMPANY}'),
        StringStruct(u'FileDescription', u'{APP_DESCRIPTION}'),
        StringStruct(u'FileVersion', u'{self._version}'),
        StringStruct(u'InternalName', u'{APP_NAME}'),
        StringStruct(u'LegalCopyright', u'{APP_COPYRIGHT}'),
        StringStruct(u'OriginalFilename', u'{APP_NAME}.exe'),
        StringStruct(u'ProductName', u'{APP_NAME}'),
        StringStruct(u'ProductVersion', u'{self._version}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''

        version_file = BUILD_DIR / "version_info.txt"
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(version_info, encoding="utf-8")

        print(f"  Created: {version_file}")
        return version_file

    def _build_pyinstaller_command(self, version_file: Path) -> List[str]:
        """Build the PyInstaller command line."""
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--name", self._output_name,
            "--distpath", str(DIST_DIR),
            "--workpath", str(BUILD_DIR),
            "--specpath", str(PROJECT_ROOT),
        ]

        # One-file or one-directory
        if self._one_file:
            cmd.append("--onefile")
        else:
            cmd.append("--onedir")

        # Console or windowed
        if self._console:
            cmd.append("--console")
        else:
            cmd.append("--windowed")

        # Debug mode
        if self._debug:
            cmd.append("--debug=all")

        # UPX compression
        if self._upx_enabled and self._upx_dir:
            cmd.extend(["--upx-dir", str(self._upx_dir)])
        elif not self._upx_enabled:
            cmd.append("--noupx")

        # Icon
        if ICON_ICO.exists():
            cmd.extend(["--icon", str(ICON_ICO)])

        # Version info
        if version_file.exists():
            cmd.extend(["--version-file", str(version_file)])

        # Add data files
        print("\nIncluding data files:")
        separator = ";" if sys.platform == "win32" else ":"
        for source, dest in DATA_FILES:
            if source.exists():
                cmd.extend(["--add-data", f"{source}{separator}{dest}"])
                print(f"  + {source} -> {dest}")
            else:
                self.warnings.append(f"Data path not found: {source}")
                print(f"  - [WARN] Not found: {source}")

        # Hidden imports
        print("\nAdding hidden imports...")
        for module in HIDDEN_IMPORTS:
            cmd.extend(["--hidden-import", module])

        # Excluded modules
        print("Excluding modules...")
        for module in EXCLUDED_MODULES:
            cmd.extend(["--exclude-module", module])

        # Collect binaries
        for binary in COLLECT_BINARIES:
            cmd.extend(["--collect-binaries", binary])

        # Runtime hooks
        for hook in RUNTIME_HOOKS:
            if hook.exists():
                cmd.extend(["--runtime-hook", str(hook)])

        # Additional options
        cmd.extend([
            "--noconfirm",  # Replace existing build
            "--clean",      # Clean cache
            "--log-level", "WARN",
        ])

        # Main script
        cmd.append(str(MAIN_SCRIPT))

        return cmd

    def _sign_executable(self, exe_path: Path) -> bool:
        """
        Sign the executable with a code signing certificate.

        Args:
            exe_path: Path to the executable to sign.

        Returns:
            True if signing succeeded.
        """
        print("\nSigning executable...")

        # Find signtool
        signtool = self._find_signtool()
        if not signtool:
            self.warnings.append("signtool.exe not found, skipping signing")
            print("  [WARN] signtool.exe not found")
            return False

        if not self._sign_cert or not self._sign_cert.exists():
            self.warnings.append("Signing certificate not found")
            print("  [WARN] Signing certificate not specified or not found")
            return False

        # Build signtool command
        cmd = [
            str(signtool),
            "sign",
            "/f", str(self._sign_cert),
            "/t", "http://timestamp.digicert.com",
            "/d", APP_NAME,
            str(exe_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  [OK] Signed: {exe_path}")
                return True
            else:
                self.warnings.append(f"Signing failed: {result.stderr}")
                print(f"  [ERROR] Signing failed: {result.stderr}")
                return False
        except Exception as e:
            self.warnings.append(f"Signing error: {e}")
            print(f"  [ERROR] Signing error: {e}")
            return False

    def _find_signtool(self) -> Optional[Path]:
        """Find Windows SDK signtool.exe."""
        # Check PATH first
        signtool = shutil.which("signtool")
        if signtool:
            return Path(signtool)

        # Check common locations
        sdk_paths = [
            r"C:\Program Files (x86)\Windows Kits\10\bin",
            r"C:\Program Files\Windows Kits\10\bin",
        ]

        for sdk_path in sdk_paths:
            sdk_dir = Path(sdk_path)
            if sdk_dir.exists():
                # Find latest version
                versions = sorted(sdk_dir.glob("10.*/x64/signtool.exe"), reverse=True)
                if versions:
                    return versions[0]

        return None

    def _create_nsis_installer(self, exe_path: Path) -> Optional[Path]:
        """
        Create NSIS installer.

        Args:
            exe_path: Path to the main executable.

        Returns:
            Path to created installer, or None if failed.
        """
        print("\nCreating NSIS installer...")

        # Find makensis
        makensis = self._find_makensis()
        if not makensis:
            self.warnings.append("NSIS not found, skipping installer creation")
            print("  [WARN] makensis not found")
            return None

        # Check for NSI script
        nsi_script = INSTALLER_DIR / "installer.nsi"
        if not nsi_script.exists():
            self.warnings.append(f"NSIS script not found: {nsi_script}")
            print(f"  [WARN] NSIS script not found: {nsi_script}")
            return None

        # Determine output path
        installer_name = f"{self._output_name}-{self._version}-Setup.exe"
        installer_path = DIST_DIR / installer_name

        # Build makensis command
        cmd = [
            str(makensis),
            f"/DVERSION={self._version}",
            f"/DEXE_PATH={exe_path}",
            f"/DOUTPUT_PATH={installer_path}",
            f"/DAPP_NAME={APP_NAME}",
            str(nsi_script),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and installer_path.exists():
                size_mb = installer_path.stat().st_size / (1024 * 1024)
                print(f"  [OK] Installer created: {installer_path}")
                print(f"       Size: {size_mb:.2f} MB")
                return installer_path
            else:
                self.warnings.append(f"NSIS failed: {result.stderr}")
                print(f"  [ERROR] NSIS failed: {result.stderr}")
                return None
        except Exception as e:
            self.warnings.append(f"NSIS error: {e}")
            print(f"  [ERROR] NSIS error: {e}")
            return None

    def _find_makensis(self) -> Optional[Path]:
        """Find NSIS makensis executable."""
        # Check PATH first
        makensis = shutil.which("makensis")
        if makensis:
            return Path(makensis)

        # Check common locations
        common_paths = [
            r"C:\Program Files (x86)\NSIS\makensis.exe",
            r"C:\Program Files\NSIS\makensis.exe",
        ]

        for path in common_paths:
            if Path(path).exists():
                return Path(path)

        return None

    def generate_spec_file(self) -> Path:
        """
        Generate a PyInstaller .spec file for advanced customization.

        Returns:
            Path to generated spec file.
        """
        print("Generating PyInstaller spec file...")

        # Build data files for spec
        datas_str = "[\n"
        separator = ";" if sys.platform == "win32" else ":"
        for source, dest in DATA_FILES:
            if source.exists():
                datas_str += f"    (r'{source}', r'{dest}'),\n"
        datas_str += "]"

        # Build hidden imports for spec
        hiddenimports_str = "[\n"
        for module in HIDDEN_IMPORTS:
            hiddenimports_str += f"    '{module}',\n"
        hiddenimports_str += "]"

        # Build excludes for spec
        excludes_str = "[\n"
        for module in EXCLUDED_MODULES:
            excludes_str += f"    '{module}',\n"
        excludes_str += "]"

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
datas = {datas_str}

# Binaries
binaries = []

# Hidden imports
hiddenimports = {hiddenimports_str}

# Excluded modules
excludes = {excludes_str}

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
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{self._output_name}',
    debug={self._debug},
    bootloader_ignore_signals=False,
    strip=False,
    upx={'True' if self._upx_enabled else 'False'},
    upx_exclude=[],
    runtime_tmpdir=None,
    console={self._console},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'{ICON_ICO}' if Path(r'{ICON_ICO}').exists() else None,
    version=r'{BUILD_DIR / "version_info.txt"}',
)

# Uncomment for one-directory build
# exe_onedir = EXE(
#     pyz,
#     a.scripts,
#     [],
#     exclude_binaries=True,
#     name='{self._output_name}',
#     debug={self._debug},
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx={'True' if self._upx_enabled else 'False'},
#     console={self._console},
#     disable_windowed_traceback=False,
#     argv_emulation=False,
#     target_arch=None,
#     codesign_identity=None,
#     entitlements_file=None,
#     icon=r'{ICON_ICO}' if Path(r'{ICON_ICO}').exists() else None,
# )
#
# coll = COLLECT(
#     exe_onedir,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx={'True' if self._upx_enabled else 'False'},
#     upx_exclude=[],
#     name='{self._output_name}',
# )
'''

        spec_path = PROJECT_ROOT / f"{self._output_name}.spec"
        spec_path.write_text(spec_content, encoding="utf-8")

        print(f"  Created: {spec_path}")
        return spec_path


# =============================================================================
# Command Line Interface
# =============================================================================

def main() -> int:
    """Main entry point for Windows build."""
    import argparse

    parser = argparse.ArgumentParser(
        description=f"Build {APP_NAME} for Windows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version", "-v",
        default="1.0.0",
        help="Version to build"
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        default=True,
        help="Create single executable (default)"
    )
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Create directory with executable"
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Show console window"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--upx",
        action="store_true",
        help="Enable UPX compression"
    )
    parser.add_argument(
        "--upx-dir",
        type=Path,
        help="Path to UPX directory"
    )
    parser.add_argument(
        "--sign",
        action="store_true",
        help="Sign the executable"
    )
    parser.add_argument(
        "--sign-cert",
        type=Path,
        help="Path to signing certificate"
    )
    parser.add_argument(
        "--no-installer",
        action="store_true",
        help="Skip installer creation"
    )
    parser.add_argument(
        "--spec-only",
        action="store_true",
        help="Generate spec file only"
    )
    parser.add_argument(
        "--output-name",
        default=APP_NAME,
        help="Output executable name"
    )

    args = parser.parse_args()

    # Create simple config object
    class Config:
        pass

    config = Config()
    config.version = args.version
    config.one_file = not args.onedir
    config.console = args.console
    config.debug = args.debug
    config.upx_enabled = args.upx
    config.upx_dir = args.upx_dir
    config.sign_enabled = args.sign
    config.sign_certificate = args.sign_cert
    config.create_installer = not args.no_installer
    config.output_name = args.output_name

    builder = WindowsBuilder(config)

    if args.spec_only:
        builder.generate_spec_file()
        return 0

    result = builder.build()
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
