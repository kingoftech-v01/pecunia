#!/usr/bin/env python3
"""
Pecunia Desktop - Linux Build Script

PyInstaller configuration and build process for Linux applications.
Supports AppImage creation, .desktop file generation, and .deb packaging.

Usage:
    python scripts/build_linux.py              # Default build
    python scripts/build_linux.py --appimage   # Create AppImage
    python scripts/build_linux.py --deb        # Create .deb package
    python scripts/build_linux.py --onefile    # Single executable
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
INSTALLER_DIR = PROJECT_ROOT / "installer" / "linux"

# Main entry point
MAIN_SCRIPT = SRC_DIR / "main.py"

# Icon paths
ICON_PNG = RESOURCES_DIR / "icons" / "app_icon.png"
ICON_SVG = RESOURCES_DIR / "icons" / "app_icon.svg"


# =============================================================================
# Application Metadata
# =============================================================================

APP_NAME = "Pecunia"
APP_EXECUTABLE = "pecunia"
APP_DESCRIPTION = "Personal Finance Management Application"
APP_AUTHOR = "Pecunia Inc."
APP_COPYRIGHT = f"Copyright (c) {datetime.now().year} {APP_AUTHOR}"
APP_WEBSITE = "https://pecunia.com"
APP_CATEGORIES = "Office;Finance;"
APP_KEYWORDS = "finance;money;budget;accounting;personal finance;"
APP_MAINTAINER = "Pecunia Team <support@pecunia.com>"


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
    "PyQt6.QtDBus",  # Linux D-Bus integration
    "PyQt6.sip",
    # Database
    "sqlite3",
    "aiosqlite",
    "sqlalchemy.dialects.sqlite",
    # Async
    "asyncio",
    "aiohttp",
    "qasync",
    # Security - Linux specific
    "keyring.backends.SecretService",
    "keyring.backends.kwallet",
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
    # Linux notifications
    "plyer.platforms.linux.notification",
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

# Libraries to bundle
COLLECT_BINARIES: List[str] = [
    # Add any specific libraries needed
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
# Linux Builder
# =============================================================================

class LinuxBuilder:
    """Linux-specific build implementation."""

    def __init__(self, config: Any = None):
        """
        Initialize Linux builder.

        Args:
            config: Build configuration object
        """
        self.config = config
        self._version = getattr(config, "version", "1.0.0") if config else "1.0.0"
        self._one_file = getattr(config, "one_file", False) if config else False
        self._console = getattr(config, "console", False) if config else False
        self._debug = getattr(config, "debug", False) if config else False
        self._create_installer = getattr(config, "create_installer", True) if config else True
        self._create_appimage = getattr(config, "create_appimage", True) if config else True
        self._create_deb = getattr(config, "create_deb", False) if config else False
        self._output_name = getattr(config, "output_name", APP_NAME) if config else APP_NAME
        self.warnings: List[str] = []

    def build(self) -> BuildResult:
        """
        Execute the Linux build process.

        Returns:
            BuildResult with build status and output paths.
        """
        print(f"\n{'='*60}")
        print(f"Linux Build - {APP_NAME} v{self._version}")
        print(f"{'='*60}")
        print(f"Mode: {'One-File' if self._one_file else 'One-Directory'}")
        print(f"AppImage: {'Enabled' if self._create_appimage else 'Disabled'}")
        print(f"DEB: {'Enabled' if self._create_deb else 'Disabled'}")
        print(f"{'='*60}\n")

        try:
            # Verify prerequisites
            if not self._verify_prerequisites():
                return BuildResult(
                    success=False,
                    platform="linux",
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
                    platform="linux",
                    version=self._version,
                    error_message=f"PyInstaller failed: {result.stderr[:500]}",
                    warnings=self.warnings,
                )

            # Determine output path
            if self._one_file:
                output_path = DIST_DIR / self._output_name
            else:
                output_path = DIST_DIR / self._output_name

            if not output_path.exists():
                return BuildResult(
                    success=False,
                    platform="linux",
                    version=self._version,
                    error_message=f"Output not found: {output_path}",
                    warnings=self.warnings,
                )

            # Print output info
            if self._one_file:
                size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"\nExecutable created: {output_path}")
                print(f"Size: {size_mb:.2f} MB")
            else:
                print(f"\nApplication directory created: {output_path}")

            # Create .desktop file
            desktop_file = self._create_desktop_file(output_path)

            # Create installer/package
            installer_path = None
            if self._create_installer:
                if self._create_appimage and not self._one_file:
                    installer_path = self._create_appimage_package(output_path)
                elif self._create_deb:
                    installer_path = self._create_deb_package(output_path)

            print(f"\n{'='*60}")
            print("BUILD SUCCESSFUL!")
            print(f"{'='*60}")

            return BuildResult(
                success=True,
                platform="linux",
                version=self._version,
                output_path=output_path,
                installer_path=installer_path,
                warnings=self.warnings,
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return BuildResult(
                success=False,
                platform="linux",
                version=self._version,
                error_message=str(e),
                warnings=self.warnings,
            )

    def _verify_prerequisites(self) -> bool:
        """Verify all build prerequisites are met."""
        print("Verifying prerequisites...")

        # Check we're on Linux
        if sys.platform not in ("linux", "linux2"):
            print("  [WARN] Not running on Linux - build may fail")
            self.warnings.append("Not running on Linux")

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
        if ICON_PNG.exists():
            print(f"  [OK] Icon: {ICON_PNG}")
        elif ICON_SVG.exists():
            print(f"  [OK] Icon (SVG): {ICON_SVG}")
        else:
            self.warnings.append("No icon found")
            print("  [WARN] No icon found")

        # Check appimagetool for AppImage creation
        if self._create_appimage:
            appimage_tool = shutil.which("appimagetool")
            if appimage_tool:
                print(f"  [OK] appimagetool: {appimage_tool}")
            else:
                # Check for appimagetool-x86_64.AppImage in common locations
                common_paths = [
                    Path.home() / "bin" / "appimagetool",
                    Path("/usr/local/bin/appimagetool"),
                    Path.home() / ".local" / "bin" / "appimagetool",
                ]
                found = False
                for path in common_paths:
                    if path.exists():
                        print(f"  [OK] appimagetool: {path}")
                        found = True
                        break
                if not found:
                    self.warnings.append("appimagetool not found - AppImage creation may fail")
                    print("  [WARN] appimagetool not found")

        # Check dpkg-deb for .deb creation
        if self._create_deb:
            dpkg_deb = shutil.which("dpkg-deb")
            if dpkg_deb:
                print(f"  [OK] dpkg-deb: {dpkg_deb}")
            else:
                self.warnings.append("dpkg-deb not found - .deb creation will fail")
                print("  [WARN] dpkg-deb not found")

        return True

    def _build_pyinstaller_command(self) -> List[str]:
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

        # Icon - use PNG or SVG
        if ICON_PNG.exists():
            cmd.extend(["--icon", str(ICON_PNG)])
        elif ICON_SVG.exists():
            cmd.extend(["--icon", str(ICON_SVG)])

        # Strip binaries to reduce size
        cmd.append("--strip")

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

        # Collect binaries
        for binary in COLLECT_BINARIES:
            cmd.extend(["--collect-binaries", binary])

        # Additional options
        cmd.extend([
            "--noconfirm",
            "--clean",
            "--log-level", "WARN",
        ])

        # Main script
        cmd.append(str(MAIN_SCRIPT))

        return cmd

    def _create_desktop_file(self, app_path: Path) -> Path:
        """
        Create a .desktop file for the application.

        Args:
            app_path: Path to the application.

        Returns:
            Path to created .desktop file.
        """
        print("\nCreating .desktop file...")

        desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={APP_NAME}
GenericName=Finance Manager
Comment={APP_DESCRIPTION}
Exec={app_path / self._output_name if not self._one_file else app_path}
Icon={ICON_PNG if ICON_PNG.exists() else 'pecunia'}
Terminal=false
Categories={APP_CATEGORIES}
Keywords={APP_KEYWORDS}
StartupNotify=true
StartupWMClass={APP_NAME}
MimeType=application/x-pecunia;
Actions=NewWindow;

[Desktop Action NewWindow]
Name=New Window
Exec={app_path / self._output_name if not self._one_file else app_path} --new-window
"""

        # Save to dist directory
        desktop_path = DIST_DIR / f"{APP_EXECUTABLE}.desktop"
        desktop_path.write_text(desktop_content)
        print(f"  [OK] Created: {desktop_path}")

        # Also save to app directory if one-dir mode
        if not self._one_file and app_path.is_dir():
            app_desktop_path = app_path / f"{APP_EXECUTABLE}.desktop"
            app_desktop_path.write_text(desktop_content)
            print(f"  [OK] Created: {app_desktop_path}")

            # Copy icon to app directory
            if ICON_PNG.exists():
                icon_dest = app_path / "icon.png"
                shutil.copy(ICON_PNG, icon_dest)
                print(f"  [OK] Copied icon: {icon_dest}")

        return desktop_path

    def _create_appimage_package(self, app_path: Path) -> Optional[Path]:
        """
        Create an AppImage package.

        Args:
            app_path: Path to the application directory.

        Returns:
            Path to created AppImage, or None if failed.
        """
        print("\nCreating AppImage...")

        # Find appimagetool
        appimage_tool = self._find_appimagetool()
        if not appimage_tool:
            self.warnings.append("appimagetool not found")
            return None

        try:
            # Create AppDir structure
            appdir = BUILD_DIR / f"{APP_NAME}.AppDir"
            if appdir.exists():
                shutil.rmtree(appdir)
            appdir.mkdir(parents=True)

            # Copy application files
            app_dest = appdir / "usr" / "bin"
            app_dest.mkdir(parents=True)
            if app_path.is_dir():
                shutil.copytree(app_path, app_dest / self._output_name)
            else:
                shutil.copy(app_path, app_dest / self._output_name)
                (app_dest / self._output_name).chmod(0o755)

            # Create AppRun
            apprun_content = f"""#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$HERE/usr/bin:$PATH"
export LD_LIBRARY_PATH="$HERE/usr/lib:$LD_LIBRARY_PATH"
export XDG_DATA_DIRS="$HERE/usr/share:$XDG_DATA_DIRS"
exec "$HERE/usr/bin/{self._output_name}/{self._output_name}" "$@"
"""
            apprun_path = appdir / "AppRun"
            apprun_path.write_text(apprun_content)
            apprun_path.chmod(0o755)

            # Create .desktop file in AppDir
            desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={APP_NAME}
Comment={APP_DESCRIPTION}
Exec={self._output_name}
Icon={APP_EXECUTABLE}
Terminal=false
Categories={APP_CATEGORIES}
"""
            (appdir / f"{APP_EXECUTABLE}.desktop").write_text(desktop_content)

            # Copy icon
            icon_dest = appdir / f"{APP_EXECUTABLE}.png"
            if ICON_PNG.exists():
                shutil.copy(ICON_PNG, icon_dest)
            else:
                # Create a placeholder icon
                self._create_placeholder_icon(icon_dest)

            # Also place icon in standard locations
            icon_dir = appdir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
            icon_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(icon_dest, icon_dir / f"{APP_EXECUTABLE}.png")

            # Run appimagetool
            appimage_name = f"{self._output_name}-{self._version}-x86_64.AppImage"
            appimage_path = DIST_DIR / appimage_name

            # Set ARCH for appimagetool
            env = os.environ.copy()
            env["ARCH"] = "x86_64"

            cmd = [str(appimage_tool), str(appdir), str(appimage_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)

            if result.returncode == 0 and appimage_path.exists():
                # Make executable
                appimage_path.chmod(0o755)
                size_mb = appimage_path.stat().st_size / (1024 * 1024)
                print(f"  [OK] AppImage created: {appimage_path}")
                print(f"       Size: {size_mb:.2f} MB")
                return appimage_path
            else:
                self.warnings.append(f"appimagetool failed: {result.stderr}")
                print(f"  [ERROR] appimagetool failed: {result.stderr}")
                return None

        except Exception as e:
            self.warnings.append(f"AppImage creation error: {e}")
            print(f"  [ERROR] AppImage creation error: {e}")
            return None

    def _find_appimagetool(self) -> Optional[Path]:
        """Find appimagetool executable."""
        # Check PATH
        tool = shutil.which("appimagetool")
        if tool:
            return Path(tool)

        # Check common locations
        common_paths = [
            Path.home() / "bin" / "appimagetool",
            Path.home() / ".local" / "bin" / "appimagetool",
            Path("/usr/local/bin/appimagetool"),
            Path.home() / "bin" / "appimagetool-x86_64.AppImage",
            Path.home() / ".local" / "bin" / "appimagetool-x86_64.AppImage",
        ]

        for path in common_paths:
            if path.exists():
                return path

        return None

    def _create_deb_package(self, app_path: Path) -> Optional[Path]:
        """
        Create a .deb package.

        Args:
            app_path: Path to the application.

        Returns:
            Path to created .deb file, or None if failed.
        """
        print("\nCreating .deb package...")

        dpkg_deb = shutil.which("dpkg-deb")
        if not dpkg_deb:
            self.warnings.append("dpkg-deb not found")
            return None

        try:
            # Create package structure
            pkg_name = f"{APP_EXECUTABLE}_{self._version}_amd64"
            pkg_dir = BUILD_DIR / pkg_name
            if pkg_dir.exists():
                shutil.rmtree(pkg_dir)

            # Create directories
            (pkg_dir / "DEBIAN").mkdir(parents=True)
            (pkg_dir / "usr" / "bin").mkdir(parents=True)
            (pkg_dir / "usr" / "share" / "applications").mkdir(parents=True)
            (pkg_dir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps").mkdir(parents=True)
            (pkg_dir / "usr" / "share" / "doc" / APP_EXECUTABLE).mkdir(parents=True)

            # Copy application
            if app_path.is_dir():
                app_dest = pkg_dir / "opt" / APP_EXECUTABLE
                app_dest.mkdir(parents=True)
                shutil.copytree(app_path, app_dest, dirs_exist_ok=True)

                # Create symlink in /usr/bin
                symlink = pkg_dir / "usr" / "bin" / APP_EXECUTABLE
                symlink_target = f"/opt/{APP_EXECUTABLE}/{self._output_name}"
                symlink.symlink_to(symlink_target)
            else:
                shutil.copy(app_path, pkg_dir / "usr" / "bin" / APP_EXECUTABLE)
                (pkg_dir / "usr" / "bin" / APP_EXECUTABLE).chmod(0o755)

            # Create control file
            installed_size = self._get_directory_size(app_path) // 1024
            control_content = f"""Package: {APP_EXECUTABLE}
Version: {self._version}
Section: office
Priority: optional
Architecture: amd64
Installed-Size: {installed_size}
Maintainer: {APP_MAINTAINER}
Description: {APP_DESCRIPTION}
 {APP_NAME} is a comprehensive personal finance management
 application that helps you track expenses, manage budgets,
 and analyze your financial health.
Homepage: {APP_WEBSITE}
"""
            (pkg_dir / "DEBIAN" / "control").write_text(control_content)

            # Create .desktop file
            exec_path = f"/opt/{APP_EXECUTABLE}/{self._output_name}" if app_path.is_dir() else f"/usr/bin/{APP_EXECUTABLE}"
            desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={APP_NAME}
Comment={APP_DESCRIPTION}
Exec={exec_path}
Icon={APP_EXECUTABLE}
Terminal=false
Categories={APP_CATEGORIES}
Keywords={APP_KEYWORDS}
"""
            (pkg_dir / "usr" / "share" / "applications" / f"{APP_EXECUTABLE}.desktop").write_text(desktop_content)

            # Copy icon
            if ICON_PNG.exists():
                shutil.copy(
                    ICON_PNG,
                    pkg_dir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps" / f"{APP_EXECUTABLE}.png"
                )

            # Create copyright file
            copyright_content = f"""Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: {APP_NAME}
Upstream-Contact: {APP_MAINTAINER}
Source: {APP_WEBSITE}

Files: *
Copyright: {APP_COPYRIGHT}
License: Proprietary
"""
            (pkg_dir / "usr" / "share" / "doc" / APP_EXECUTABLE / "copyright").write_text(copyright_content)

            # Create postinst script (optional)
            postinst_content = """#!/bin/bash
set -e

# Update icon cache
if command -v update-icon-caches &>/dev/null; then
    update-icon-caches /usr/share/icons/hicolor || true
fi

# Update desktop database
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications || true
fi

exit 0
"""
            postinst_path = pkg_dir / "DEBIAN" / "postinst"
            postinst_path.write_text(postinst_content)
            postinst_path.chmod(0o755)

            # Build .deb package
            deb_path = DIST_DIR / f"{pkg_name}.deb"
            cmd = ["dpkg-deb", "--build", str(pkg_dir), str(deb_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and deb_path.exists():
                size_mb = deb_path.stat().st_size / (1024 * 1024)
                print(f"  [OK] DEB package created: {deb_path}")
                print(f"       Size: {size_mb:.2f} MB")
                return deb_path
            else:
                self.warnings.append(f"dpkg-deb failed: {result.stderr}")
                print(f"  [ERROR] dpkg-deb failed: {result.stderr}")
                return None

        except Exception as e:
            self.warnings.append(f"DEB creation error: {e}")
            print(f"  [ERROR] DEB creation error: {e}")
            return None

    def _get_directory_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        if path.is_file():
            return path.stat().st_size

        total = 0
        for entry in path.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
        return total

    def _create_placeholder_icon(self, path: Path) -> None:
        """Create a simple placeholder icon."""
        # Create a minimal valid PNG (1x1 blue pixel)
        # This is a base64-decoded minimal PNG
        import base64
        minimal_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAD"
            "hgJ/hzDZ1wAAAABJRU5ErkJggg=="
        )
        path.write_bytes(minimal_png)

    def create_install_script(self) -> Path:
        """
        Create an install.sh script for manual installation.

        Returns:
            Path to created script.
        """
        print("Creating install script...")

        script_content = f"""#!/bin/bash
# Install script for {APP_NAME}
# Run with: sudo ./install.sh

set -e

APP_NAME="{APP_NAME}"
APP_EXEC="{APP_EXECUTABLE}"
VERSION="{self._version}"
INSTALL_DIR="/opt/$APP_EXEC"
BIN_LINK="/usr/local/bin/$APP_EXEC"

echo "Installing $APP_NAME v$VERSION..."

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./install.sh)"
    exit 1
fi

# Create install directory
echo "Creating installation directory..."
mkdir -p "$INSTALL_DIR"

# Copy files
echo "Copying application files..."
cp -r ./* "$INSTALL_DIR/"

# Make executable
chmod +x "$INSTALL_DIR/$APP_EXEC"

# Create symlink
echo "Creating symlink..."
ln -sf "$INSTALL_DIR/$APP_EXEC" "$BIN_LINK"

# Install desktop file
echo "Installing desktop entry..."
cp "$INSTALL_DIR/$APP_EXEC.desktop" /usr/share/applications/ 2>/dev/null || true

# Install icon
echo "Installing icon..."
mkdir -p /usr/share/icons/hicolor/256x256/apps/
cp "$INSTALL_DIR/icon.png" "/usr/share/icons/hicolor/256x256/apps/$APP_EXEC.png" 2>/dev/null || true

# Update caches
echo "Updating system caches..."
update-icon-caches /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database /usr/share/applications 2>/dev/null || true

echo ""
echo "Installation complete!"
echo "You can now run '$APP_EXEC' from the terminal or find '$APP_NAME' in your applications menu."
echo ""
"""

        script_path = DIST_DIR / "install.sh"
        script_path.write_text(script_content)
        script_path.chmod(0o755)

        print(f"  [OK] Created: {script_path}")
        return script_path

    def create_uninstall_script(self) -> Path:
        """
        Create an uninstall.sh script.

        Returns:
            Path to created script.
        """
        print("Creating uninstall script...")

        script_content = f"""#!/bin/bash
# Uninstall script for {APP_NAME}
# Run with: sudo ./uninstall.sh

set -e

APP_NAME="{APP_NAME}"
APP_EXEC="{APP_EXECUTABLE}"
INSTALL_DIR="/opt/$APP_EXEC"
BIN_LINK="/usr/local/bin/$APP_EXEC"

echo "Uninstalling $APP_NAME..."

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./uninstall.sh)"
    exit 1
fi

# Remove symlink
echo "Removing symlink..."
rm -f "$BIN_LINK"

# Remove desktop file
echo "Removing desktop entry..."
rm -f "/usr/share/applications/$APP_EXEC.desktop"

# Remove icon
echo "Removing icon..."
rm -f "/usr/share/icons/hicolor/256x256/apps/$APP_EXEC.png"

# Remove installation directory
echo "Removing installation directory..."
rm -rf "$INSTALL_DIR"

# Update caches
echo "Updating system caches..."
update-icon-caches /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database /usr/share/applications 2>/dev/null || true

echo ""
echo "Uninstallation complete!"
echo ""
"""

        script_path = DIST_DIR / "uninstall.sh"
        script_path.write_text(script_content)
        script_path.chmod(0o755)

        print(f"  [OK] Created: {script_path}")
        return script_path


# =============================================================================
# Command Line Interface
# =============================================================================

def main() -> int:
    """Main entry point for Linux build."""
    import argparse

    parser = argparse.ArgumentParser(
        description=f"Build {APP_NAME} for Linux",
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
        help="Create single executable"
    )
    parser.add_argument(
        "--onedir",
        action="store_true",
        default=True,
        help="Create directory with executable (default, required for AppImage)"
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
        "--appimage",
        action="store_true",
        default=True,
        help="Create AppImage (default)"
    )
    parser.add_argument(
        "--no-appimage",
        action="store_true",
        help="Skip AppImage creation"
    )
    parser.add_argument(
        "--deb",
        action="store_true",
        help="Create .deb package"
    )
    parser.add_argument(
        "--no-installer",
        action="store_true",
        help="Skip installer creation"
    )
    parser.add_argument(
        "--output-name",
        default=APP_NAME,
        help="Output executable name"
    )
    parser.add_argument(
        "--create-scripts",
        action="store_true",
        help="Create install/uninstall scripts only"
    )

    args = parser.parse_args()

    # Create simple config object
    class Config:
        pass

    config = Config()
    config.version = args.version
    config.one_file = args.onefile and not args.onedir
    config.console = args.console
    config.debug = args.debug
    config.create_installer = not args.no_installer
    config.create_appimage = args.appimage and not args.no_appimage
    config.create_deb = args.deb
    config.output_name = args.output_name

    builder = LinuxBuilder(config)

    if args.create_scripts:
        builder.create_install_script()
        builder.create_uninstall_script()
        return 0

    result = builder.build()
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
