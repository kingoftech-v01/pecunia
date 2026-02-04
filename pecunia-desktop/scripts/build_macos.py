#!/usr/bin/env python3
"""
Pecunia Desktop - macOS Build Script

PyInstaller configuration and build process for macOS applications.
Creates .app bundles with proper Info.plist, code signing support,
and DMG disk image creation.

Usage:
    python scripts/build_macos.py              # Default build
    python scripts/build_macos.py --sign       # With code signing
    python scripts/build_macos.py --notarize   # With Apple notarization
    python scripts/build_macos.py --dmg        # Create DMG installer
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
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
INSTALLER_DIR = PROJECT_ROOT / "installer" / "macos"

# Main entry point
MAIN_SCRIPT = SRC_DIR / "main.py"

# Icon paths
ICON_ICNS = RESOURCES_DIR / "icons" / "app_icon.icns"
ICON_PNG = RESOURCES_DIR / "icons" / "app_icon.png"


# =============================================================================
# Application Metadata
# =============================================================================

APP_NAME = "Pecunia"
APP_BUNDLE_NAME = "Pecunia Desktop"
APP_BUNDLE_ID = "com.pecunia.desktop"
APP_DESCRIPTION = "Personal Finance Management Application"
APP_AUTHOR = "Pecunia Inc."
APP_COPYRIGHT = f"Copyright (c) {datetime.now().year} {APP_AUTHOR}"
APP_WEBSITE = "https://pecunia.com"
APP_CATEGORY = "public.app-category.finance"
MINIMUM_MACOS_VERSION = "10.15"


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
    # Security - macOS specific
    "keyring.backends.macOS",
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

# Frameworks to collect for macOS
COLLECT_FRAMEWORKS: List[str] = [
    # Add any frameworks needed
]


# =============================================================================
# Build Result
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
# macOS Builder
# =============================================================================

class MacOSBuilder:
    """macOS-specific build implementation."""

    def __init__(self, config: Any = None):
        """
        Initialize macOS builder.

        Args:
            config: Build configuration object
        """
        self.config = config
        self._version = getattr(config, "version", "1.0.0") if config else "1.0.0"
        self._debug = getattr(config, "debug", False) if config else False
        self._sign_enabled = getattr(config, "sign_enabled", False) if config else False
        self._sign_identity = getattr(config, "sign_identity", None) if config else None
        self._notarize = getattr(config, "notarize", False) if config else False
        self._apple_id = getattr(config, "apple_id", None) if config else None
        self._team_id = getattr(config, "team_id", None) if config else None
        self._create_installer = getattr(config, "create_installer", True) if config else True
        self._output_name = getattr(config, "output_name", APP_NAME) if config else APP_NAME
        self.warnings: List[str] = []

    def build(self) -> BuildResult:
        """
        Execute the macOS build process.

        Returns:
            BuildResult with build status and output paths.
        """
        print(f"\n{'='*60}")
        print(f"macOS Build - {APP_NAME} v{self._version}")
        print(f"{'='*60}")
        print(f"Bundle ID: {APP_BUNDLE_ID}")
        print(f"Sign: {'Enabled' if self._sign_enabled else 'Disabled'}")
        print(f"Notarize: {'Enabled' if self._notarize else 'Disabled'}")
        print(f"{'='*60}\n")

        try:
            # Verify prerequisites
            if not self._verify_prerequisites():
                return BuildResult(
                    success=False,
                    platform="macos",
                    version=self._version,
                    error_message="Prerequisites verification failed",
                    warnings=self.warnings,
                )

            # Build PyInstaller command
            cmd = self._build_pyinstaller_command()

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
                    platform="macos",
                    version=self._version,
                    error_message=f"PyInstaller failed: {result.stderr[:500]}",
                    warnings=self.warnings,
                )

            # Determine output path
            app_path = DIST_DIR / f"{self._output_name}.app"

            if not app_path.exists():
                return BuildResult(
                    success=False,
                    platform="macos",
                    version=self._version,
                    error_message=f"App bundle not found: {app_path}",
                    warnings=self.warnings,
                )

            # Update Info.plist
            self._update_info_plist(app_path)

            # Print app info
            print(f"\nApp bundle created: {app_path}")

            # Sign app bundle if enabled
            if self._sign_enabled:
                self._sign_app(app_path)

            # Notarize if enabled
            if self._notarize and self._sign_enabled:
                self._notarize_app(app_path)

            # Create DMG if enabled
            dmg_path = None
            if self._create_installer:
                dmg_path = self._create_dmg(app_path)

            print(f"\n{'='*60}")
            print("BUILD SUCCESSFUL!")
            print(f"{'='*60}")

            return BuildResult(
                success=True,
                platform="macos",
                version=self._version,
                output_path=app_path,
                installer_path=dmg_path,
                warnings=self.warnings,
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return BuildResult(
                success=False,
                platform="macos",
                version=self._version,
                error_message=str(e),
                warnings=self.warnings,
            )

    def _verify_prerequisites(self) -> bool:
        """Verify all build prerequisites are met."""
        print("Verifying prerequisites...")

        # Check we're on macOS
        if sys.platform != "darwin":
            print("  [WARN] Not running on macOS - build may fail")
            self.warnings.append("Not running on macOS")

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
        if ICON_ICNS.exists():
            print(f"  [OK] Icon: {ICON_ICNS}")
        elif ICON_PNG.exists():
            print(f"  [WARN] Using PNG icon (ICNS recommended)")
            self.warnings.append("Using PNG icon instead of ICNS")
        else:
            self.warnings.append("No icon found")
            print("  [WARN] No icon found")

        # Check code signing identity
        if self._sign_enabled:
            if self._sign_identity:
                # Verify identity exists
                result = subprocess.run(
                    ["security", "find-identity", "-v", "-p", "codesigning"],
                    capture_output=True,
                    text=True,
                )
                if self._sign_identity in result.stdout:
                    print(f"  [OK] Code signing identity: {self._sign_identity}")
                else:
                    self.warnings.append(f"Code signing identity not found: {self._sign_identity}")
                    print(f"  [WARN] Identity not found: {self._sign_identity}")
            else:
                self.warnings.append("No code signing identity specified")
                print("  [WARN] No code signing identity specified")

        # Check create-dmg for installer creation
        if self._create_installer:
            create_dmg = shutil.which("create-dmg")
            if create_dmg:
                print(f"  [OK] create-dmg: {create_dmg}")
            else:
                self.warnings.append("create-dmg not found (brew install create-dmg)")
                print("  [WARN] create-dmg not found")

        return True

    def _build_pyinstaller_command(self) -> List[str]:
        """Build the PyInstaller command line."""
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--name", self._output_name,
            "--distpath", str(DIST_DIR),
            "--workpath", str(BUILD_DIR),
            "--specpath", str(PROJECT_ROOT),
            "--windowed",  # Always windowed for macOS app
            "--onedir",    # Required for .app bundle
        ]

        # Debug mode
        if self._debug:
            cmd.append("--debug=all")

        # Icon
        if ICON_ICNS.exists():
            cmd.extend(["--icon", str(ICON_ICNS)])
        elif ICON_PNG.exists():
            cmd.extend(["--icon", str(ICON_PNG)])

        # macOS specific options
        cmd.extend([
            "--osx-bundle-identifier", APP_BUNDLE_ID,
        ])

        # Entitlements for hardened runtime
        entitlements_file = INSTALLER_DIR / "entitlements.plist"
        if entitlements_file.exists():
            cmd.extend(["--osx-entitlements-file", str(entitlements_file)])

        # Add data files
        print("\nIncluding data files:")
        separator = ":"
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

        # Collect frameworks
        for framework in COLLECT_FRAMEWORKS:
            cmd.extend(["--collect-all", framework])

        # Additional options
        cmd.extend([
            "--noconfirm",
            "--clean",
            "--log-level", "WARN",
        ])

        # Main script
        cmd.append(str(MAIN_SCRIPT))

        return cmd

    def _update_info_plist(self, app_path: Path) -> None:
        """
        Update the Info.plist with proper metadata.

        Args:
            app_path: Path to the .app bundle.
        """
        print("\nUpdating Info.plist...")

        info_plist_path = app_path / "Contents" / "Info.plist"

        if not info_plist_path.exists():
            self.warnings.append("Info.plist not found in app bundle")
            return

        # Read existing plist
        with open(info_plist_path, "rb") as f:
            info = plistlib.load(f)

        # Update with our metadata
        info.update({
            "CFBundleName": APP_BUNDLE_NAME,
            "CFBundleDisplayName": APP_BUNDLE_NAME,
            "CFBundleIdentifier": APP_BUNDLE_ID,
            "CFBundleVersion": self._version,
            "CFBundleShortVersionString": self._version,
            "CFBundleExecutable": self._output_name,
            "CFBundlePackageType": "APPL",
            "CFBundleSignature": "????",
            "CFBundleInfoDictionaryVersion": "6.0",
            "NSHumanReadableCopyright": APP_COPYRIGHT,
            "LSMinimumSystemVersion": MINIMUM_MACOS_VERSION,
            "LSApplicationCategoryType": APP_CATEGORY,
            "NSHighResolutionCapable": True,
            "NSSupportsAutomaticGraphicsSwitching": True,

            # Privacy permissions
            "NSAppleEventsUsageDescription": f"{APP_NAME} needs to send Apple events.",

            # URL schemes (for deep linking)
            "CFBundleURLTypes": [
                {
                    "CFBundleURLName": APP_BUNDLE_ID,
                    "CFBundleURLSchemes": ["pecunia"],
                }
            ],

            # Document types
            "CFBundleDocumentTypes": [
                {
                    "CFBundleTypeName": "Pecunia Data File",
                    "CFBundleTypeExtensions": ["pecunia", "fad"],
                    "CFBundleTypeRole": "Editor",
                    "LSHandlerRank": "Owner",
                }
            ],
        })

        # Write updated plist
        with open(info_plist_path, "wb") as f:
            plistlib.dump(info, f)

        print(f"  [OK] Updated: {info_plist_path}")

    def _sign_app(self, app_path: Path) -> bool:
        """
        Code sign the application bundle.

        Args:
            app_path: Path to the .app bundle.

        Returns:
            True if signing succeeded.
        """
        print("\nCode signing application...")

        if not self._sign_identity:
            self.warnings.append("No signing identity specified")
            return False

        # Build codesign command
        cmd = [
            "codesign",
            "--force",
            "--deep",
            "--options", "runtime",  # Hardened runtime
            "--sign", self._sign_identity,
        ]

        # Add entitlements if available
        entitlements_file = INSTALLER_DIR / "entitlements.plist"
        if entitlements_file.exists():
            cmd.extend(["--entitlements", str(entitlements_file)])

        cmd.append(str(app_path))

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  [OK] Signed: {app_path}")

                # Verify signature
                verify_cmd = ["codesign", "--verify", "--verbose=2", str(app_path)]
                verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
                if verify_result.returncode == 0:
                    print("  [OK] Signature verified")
                else:
                    self.warnings.append(f"Signature verification failed: {verify_result.stderr}")
                    print(f"  [WARN] Verification failed: {verify_result.stderr}")

                return True
            else:
                self.warnings.append(f"Signing failed: {result.stderr}")
                print(f"  [ERROR] Signing failed: {result.stderr}")
                return False
        except Exception as e:
            self.warnings.append(f"Signing error: {e}")
            print(f"  [ERROR] Signing error: {e}")
            return False

    def _notarize_app(self, app_path: Path) -> bool:
        """
        Submit app for Apple notarization.

        Args:
            app_path: Path to the signed .app bundle.

        Returns:
            True if notarization succeeded.
        """
        print("\nSubmitting for notarization...")

        if not self._apple_id or not self._team_id:
            self.warnings.append("Apple ID or Team ID not specified for notarization")
            return False

        # Create ZIP for submission
        zip_path = app_path.with_suffix(".zip")
        zip_cmd = [
            "ditto", "-c", "-k", "--keepParent",
            str(app_path), str(zip_path)
        ]

        try:
            subprocess.run(zip_cmd, check=True)
            print(f"  [OK] Created archive: {zip_path}")
        except subprocess.CalledProcessError as e:
            self.warnings.append(f"Failed to create archive: {e}")
            return False

        # Submit for notarization
        notarize_cmd = [
            "xcrun", "notarytool", "submit",
            str(zip_path),
            "--apple-id", self._apple_id,
            "--team-id", self._team_id,
            "--wait",
        ]

        try:
            result = subprocess.run(notarize_cmd, capture_output=True, text=True)
            if "status: Accepted" in result.stdout:
                print("  [OK] Notarization accepted")

                # Staple the notarization ticket
                staple_cmd = ["xcrun", "stapler", "staple", str(app_path)]
                staple_result = subprocess.run(staple_cmd, capture_output=True, text=True)
                if staple_result.returncode == 0:
                    print("  [OK] Notarization ticket stapled")
                else:
                    self.warnings.append("Failed to staple notarization ticket")

                return True
            else:
                self.warnings.append(f"Notarization failed: {result.stdout}")
                print(f"  [ERROR] Notarization failed: {result.stdout}")
                return False
        except Exception as e:
            self.warnings.append(f"Notarization error: {e}")
            print(f"  [ERROR] Notarization error: {e}")
            return False
        finally:
            # Clean up ZIP
            if zip_path.exists():
                zip_path.unlink()

    def _create_dmg(self, app_path: Path) -> Optional[Path]:
        """
        Create a DMG disk image installer.

        Args:
            app_path: Path to the .app bundle.

        Returns:
            Path to created DMG, or None if failed.
        """
        print("\nCreating DMG installer...")

        # Determine output path
        dmg_name = f"{self._output_name}-{self._version}-macos"
        dmg_path = DIST_DIR / f"{dmg_name}.dmg"

        # Check for create-dmg tool
        create_dmg = shutil.which("create-dmg")

        if create_dmg:
            return self._create_dmg_with_tool(app_path, dmg_path)
        else:
            return self._create_dmg_manual(app_path, dmg_path)

    def _create_dmg_with_tool(self, app_path: Path, dmg_path: Path) -> Optional[Path]:
        """Create DMG using create-dmg tool."""
        print("  Using create-dmg tool...")

        # Create background image directory if needed
        dmg_resources = INSTALLER_DIR / "dmg"

        cmd = [
            "create-dmg",
            "--volname", APP_BUNDLE_NAME,
            "--volicon", str(ICON_ICNS) if ICON_ICNS.exists() else "",
            "--window-pos", "200", "120",
            "--window-size", "600", "400",
            "--icon-size", "100",
            "--icon", f"{self._output_name}.app", "150", "190",
            "--app-drop-link", "450", "190",
            "--hide-extension", f"{self._output_name}.app",
        ]

        # Add background if exists
        background = dmg_resources / "background.png"
        if background.exists():
            cmd.extend(["--background", str(background)])

        cmd.extend([str(dmg_path), str(app_path)])

        try:
            # Remove filter for volicon if no icon
            if not ICON_ICNS.exists():
                cmd = [c for c in cmd if c != "--volicon" and c != ""]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and dmg_path.exists():
                size_mb = dmg_path.stat().st_size / (1024 * 1024)
                print(f"  [OK] DMG created: {dmg_path}")
                print(f"       Size: {size_mb:.2f} MB")
                return dmg_path
            else:
                self.warnings.append(f"create-dmg failed: {result.stderr}")
                print(f"  [ERROR] create-dmg failed: {result.stderr}")
                # Fall back to manual creation
                return self._create_dmg_manual(app_path, dmg_path)
        except Exception as e:
            self.warnings.append(f"create-dmg error: {e}")
            return self._create_dmg_manual(app_path, dmg_path)

    def _create_dmg_manual(self, app_path: Path, dmg_path: Path) -> Optional[Path]:
        """Create DMG manually using hdiutil."""
        print("  Creating DMG manually with hdiutil...")

        try:
            # Create temporary directory for DMG contents
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                staging = temp_path / "staging"
                staging.mkdir()

                # Copy app to staging
                shutil.copytree(app_path, staging / app_path.name)

                # Create Applications symlink
                (staging / "Applications").symlink_to("/Applications")

                # Create DMG
                cmd = [
                    "hdiutil", "create",
                    "-volname", APP_BUNDLE_NAME,
                    "-srcfolder", str(staging),
                    "-ov",
                    "-format", "UDZO",  # Compressed
                    str(dmg_path),
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and dmg_path.exists():
                    size_mb = dmg_path.stat().st_size / (1024 * 1024)
                    print(f"  [OK] DMG created: {dmg_path}")
                    print(f"       Size: {size_mb:.2f} MB")
                    return dmg_path
                else:
                    self.warnings.append(f"hdiutil failed: {result.stderr}")
                    print(f"  [ERROR] hdiutil failed: {result.stderr}")
                    return None

        except Exception as e:
            self.warnings.append(f"DMG creation error: {e}")
            print(f"  [ERROR] DMG creation error: {e}")
            return None

    def create_entitlements(self) -> Path:
        """
        Create entitlements.plist for hardened runtime.

        Returns:
            Path to created entitlements file.
        """
        print("Creating entitlements.plist...")

        entitlements = {
            # Allow JIT for better performance
            "com.apple.security.cs.allow-jit": True,
            # Allow unsigned executable memory (needed for some Python packages)
            "com.apple.security.cs.allow-unsigned-executable-memory": True,
            # Allow loading plugins
            "com.apple.security.cs.disable-library-validation": True,
            # Network access
            "com.apple.security.network.client": True,
            # File access
            "com.apple.security.files.user-selected.read-write": True,
            "com.apple.security.files.downloads.read-write": True,
        }

        entitlements_path = INSTALLER_DIR / "entitlements.plist"
        entitlements_path.parent.mkdir(parents=True, exist_ok=True)

        with open(entitlements_path, "wb") as f:
            plistlib.dump(entitlements, f)

        print(f"  [OK] Created: {entitlements_path}")
        return entitlements_path


# =============================================================================
# Command Line Interface
# =============================================================================

def main() -> int:
    """Main entry point for macOS build."""
    import argparse

    parser = argparse.ArgumentParser(
        description=f"Build {APP_NAME} for macOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version", "-v",
        default="1.0.0",
        help="Version to build"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--sign",
        action="store_true",
        help="Sign the application"
    )
    parser.add_argument(
        "--sign-identity",
        help="Code signing identity (e.g., 'Developer ID Application: Company Name')"
    )
    parser.add_argument(
        "--notarize",
        action="store_true",
        help="Submit for Apple notarization"
    )
    parser.add_argument(
        "--apple-id",
        help="Apple ID for notarization"
    )
    parser.add_argument(
        "--team-id",
        help="Team ID for notarization"
    )
    parser.add_argument(
        "--no-dmg",
        action="store_true",
        help="Skip DMG creation"
    )
    parser.add_argument(
        "--output-name",
        default=APP_NAME,
        help="Output application name"
    )
    parser.add_argument(
        "--create-entitlements",
        action="store_true",
        help="Create entitlements.plist only"
    )

    args = parser.parse_args()

    # Create simple config object
    class Config:
        pass

    config = Config()
    config.version = args.version
    config.debug = args.debug
    config.sign_enabled = args.sign
    config.sign_identity = args.sign_identity
    config.notarize = args.notarize
    config.apple_id = args.apple_id
    config.team_id = args.team_id
    config.create_installer = not args.no_dmg
    config.output_name = args.output_name

    builder = MacOSBuilder(config)

    if args.create_entitlements:
        builder.create_entitlements()
        return 0

    result = builder.build()
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
