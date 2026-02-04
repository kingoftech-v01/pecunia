#!/usr/bin/env python3
"""
Pecunia Desktop - Main Build Script

Cross-platform build orchestrator for creating distributable packages.
Supports Windows (exe/msi), macOS (app/dmg), and Linux (AppImage/deb).

Usage:
    python scripts/build.py                    # Build for current platform
    python scripts/build.py --platform windows # Build for Windows
    python scripts/build.py --all              # Build for all platforms
    python scripts/build.py --version 1.2.3   # Build with specific version
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# =============================================================================
# Path Configuration
# =============================================================================

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
RESOURCES_DIR = PROJECT_ROOT / "resources"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
INSTALLER_DIR = PROJECT_ROOT / "installer"


# =============================================================================
# Version Management
# =============================================================================

class VersionManager:
    """Manages application version across all project files."""

    VERSION_FILE = PROJECT_ROOT / "VERSION"
    CONSTANTS_FILE = SRC_DIR / "constants.py"
    PYPROJECT_FILE = PROJECT_ROOT / "pyproject.toml"

    def __init__(self):
        self._version: Optional[str] = None

    @property
    def version(self) -> str:
        """Get current version from VERSION file or constants."""
        if self._version:
            return self._version

        # Try VERSION file first
        if self.VERSION_FILE.exists():
            self._version = self.VERSION_FILE.read_text().strip()
            return self._version

        # Fall back to constants.py
        if self.CONSTANTS_FILE.exists():
            content = self.CONSTANTS_FILE.read_text()
            for line in content.splitlines():
                if line.startswith("APP_VERSION"):
                    # Extract version from: APP_VERSION = "1.0.0"
                    self._version = line.split("=")[1].strip().strip('"\'')
                    return self._version

        # Default version
        self._version = "1.0.0"
        return self._version

    @version.setter
    def version(self, value: str) -> None:
        """Set version and update all version files."""
        self._version = value
        self._update_version_files()

    def _update_version_files(self) -> None:
        """Update version in all relevant files."""
        version = self._version

        # Update VERSION file
        self.VERSION_FILE.write_text(f"{version}\n")
        print(f"  Updated: {self.VERSION_FILE}")

        # Update constants.py
        if self.CONSTANTS_FILE.exists():
            content = self.CONSTANTS_FILE.read_text()
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if line.startswith("APP_VERSION"):
                    lines[i] = f'APP_VERSION = "{version}"'
                    break
            self.CONSTANTS_FILE.write_text("\n".join(lines) + "\n")
            print(f"  Updated: {self.CONSTANTS_FILE}")

        # Update pyproject.toml if exists
        if self.PYPROJECT_FILE.exists():
            content = self.PYPROJECT_FILE.read_text()
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if line.strip().startswith("version ="):
                    lines[i] = f'version = "{version}"'
                    break
            self.PYPROJECT_FILE.write_text("\n".join(lines) + "\n")
            print(f"  Updated: {self.PYPROJECT_FILE}")

    def parse_version(self) -> Tuple[int, int, int]:
        """Parse version string into tuple of integers."""
        parts = self.version.split(".")
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2].split("-")[0]) if len(parts) > 2 else 0
        return (major, minor, patch)

    def bump(self, bump_type: str = "patch") -> str:
        """Bump version number."""
        major, minor, patch = self.parse_version()

        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")

        new_version = f"{major}.{minor}.{patch}"
        self.version = new_version
        return new_version


# =============================================================================
# Platform Detection
# =============================================================================

class Platform(Enum):
    """Supported build platforms."""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"

    @classmethod
    def current(cls) -> "Platform":
        """Detect current platform."""
        system = platform.system().lower()
        if system == "windows":
            return cls.WINDOWS
        elif system == "darwin":
            return cls.MACOS
        elif system == "linux":
            return cls.LINUX
        else:
            raise RuntimeError(f"Unsupported platform: {system}")

    @classmethod
    def from_string(cls, name: str) -> "Platform":
        """Convert string to Platform enum."""
        name_lower = name.lower()
        for p in cls:
            if p.value == name_lower:
                return p
        raise ValueError(f"Unknown platform: {name}")


# =============================================================================
# Build Configuration
# =============================================================================

@dataclass
class BuildConfig:
    """Build configuration options."""

    # Target platform
    platform: Platform = field(default_factory=Platform.current)

    # Version to build
    version: str = ""

    # Build modes
    one_file: bool = True
    console: bool = False
    debug: bool = False

    # Compression
    upx_enabled: bool = False
    upx_dir: Optional[Path] = None

    # Code signing
    sign_enabled: bool = False
    sign_identity: Optional[str] = None
    sign_certificate: Optional[Path] = None

    # Installer creation
    create_installer: bool = True

    # Clean build
    clean_before_build: bool = True
    clean_after_build: bool = False

    # Output naming
    output_name: str = "Pecunia"
    include_version_in_name: bool = True

    # Parallel builds
    parallel: bool = False

    def __post_init__(self):
        if not self.version:
            self.version = VersionManager().version

    @property
    def output_filename(self) -> str:
        """Generate output filename based on configuration."""
        name = self.output_name
        if self.include_version_in_name:
            name = f"{name}-{self.version}"

        # Add platform suffix
        if self.platform == Platform.WINDOWS:
            name = f"{name}-win64"
        elif self.platform == Platform.MACOS:
            name = f"{name}-macos"
        elif self.platform == Platform.LINUX:
            name = f"{name}-linux-x86_64"

        return name

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "platform": self.platform.value,
            "version": self.version,
            "one_file": self.one_file,
            "console": self.console,
            "debug": self.debug,
            "upx_enabled": self.upx_enabled,
            "sign_enabled": self.sign_enabled,
            "create_installer": self.create_installer,
            "output_name": self.output_name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuildConfig":
        """Create configuration from dictionary."""
        if "platform" in data and isinstance(data["platform"], str):
            data["platform"] = Platform.from_string(data["platform"])
        return cls(**data)


# =============================================================================
# Build Result
# =============================================================================

@dataclass
class BuildResult:
    """Result of a build operation."""

    success: bool
    platform: Platform
    version: str
    output_path: Optional[Path] = None
    installer_path: Optional[Path] = None
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "platform": self.platform.value,
            "version": self.version,
            "output_path": str(self.output_path) if self.output_path else None,
            "installer_path": str(self.installer_path) if self.installer_path else None,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "warnings": self.warnings,
        }


# =============================================================================
# Build Logger
# =============================================================================

class BuildLogger:
    """Logging utility for build operations."""

    COLORS = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "reset": "\033[0m",
        "bold": "\033[1m",
    }

    def __init__(self, verbose: bool = True, use_colors: bool = True):
        self.verbose = verbose
        self.use_colors = use_colors and self._supports_colors()
        self._indent_level = 0

    @staticmethod
    def _supports_colors() -> bool:
        """Check if terminal supports colors."""
        if os.name == "nt":
            return os.environ.get("TERM") == "xterm" or "ANSICON" in os.environ
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if supported."""
        if self.use_colors and color in self.COLORS:
            return f"{self.COLORS[color]}{text}{self.COLORS['reset']}"
        return text

    def _indent(self) -> str:
        """Get current indentation."""
        return "  " * self._indent_level

    def header(self, text: str) -> None:
        """Print header text."""
        print()
        print(self._colorize("=" * 70, "cyan"))
        print(self._colorize(f"  {text}", "cyan"))
        print(self._colorize("=" * 70, "cyan"))
        print()

    def section(self, text: str) -> None:
        """Print section header."""
        print()
        print(self._colorize(f"{self._indent()}>> {text}", "blue"))
        print(self._colorize(f"{self._indent()}{'-' * (len(text) + 3)}", "blue"))

    def info(self, text: str) -> None:
        """Print info message."""
        print(f"{self._indent()}{text}")

    def success(self, text: str) -> None:
        """Print success message."""
        print(self._colorize(f"{self._indent()}[OK] {text}", "green"))

    def warning(self, text: str) -> None:
        """Print warning message."""
        print(self._colorize(f"{self._indent()}[WARN] {text}", "yellow"))

    def error(self, text: str) -> None:
        """Print error message."""
        print(self._colorize(f"{self._indent()}[ERROR] {text}", "red"))

    def debug(self, text: str) -> None:
        """Print debug message if verbose mode is enabled."""
        if self.verbose:
            print(self._colorize(f"{self._indent()}[DEBUG] {text}", "magenta"))

    def progress(self, current: int, total: int, text: str = "") -> None:
        """Print progress indicator."""
        percent = (current / total) * 100 if total > 0 else 0
        bar_width = 30
        filled = int(bar_width * current / total) if total > 0 else 0
        bar = "=" * filled + "-" * (bar_width - filled)
        print(f"\r{self._indent()}[{bar}] {percent:5.1f}% {text}", end="", flush=True)
        if current >= total:
            print()

    def indent(self) -> None:
        """Increase indentation level."""
        self._indent_level += 1

    def dedent(self) -> None:
        """Decrease indentation level."""
        self._indent_level = max(0, self._indent_level - 1)


# =============================================================================
# Build System
# =============================================================================

class BuildSystem:
    """Main build system orchestrator."""

    def __init__(self, config: Optional[BuildConfig] = None, verbose: bool = True):
        self.config = config or BuildConfig()
        self.logger = BuildLogger(verbose=verbose)
        self.version_manager = VersionManager()

    def check_prerequisites(self) -> bool:
        """Check if all build prerequisites are met."""
        self.logger.section("Checking Prerequisites")
        all_ok = True

        # Check Python version
        py_version = sys.version_info
        if py_version >= (3, 10):
            self.logger.success(f"Python {py_version.major}.{py_version.minor}.{py_version.micro}")
        else:
            self.logger.error(f"Python 3.10+ required, found {py_version.major}.{py_version.minor}")
            all_ok = False

        # Check PyInstaller
        try:
            import PyInstaller
            self.logger.success(f"PyInstaller {PyInstaller.__version__}")
        except ImportError:
            self.logger.error("PyInstaller not installed (pip install pyinstaller)")
            all_ok = False

        # Check PyQt6
        try:
            from PyQt6.QtCore import PYQT_VERSION_STR
            self.logger.success(f"PyQt6 {PYQT_VERSION_STR}")
        except ImportError:
            self.logger.error("PyQt6 not installed (pip install PyQt6)")
            all_ok = False

        # Check main entry point
        main_script = SRC_DIR / "main.py"
        if main_script.exists():
            self.logger.success(f"Entry point: {main_script}")
        else:
            self.logger.error(f"Entry point not found: {main_script}")
            all_ok = False

        # Platform-specific checks
        if self.config.platform == Platform.WINDOWS:
            all_ok = all_ok and self._check_windows_prerequisites()
        elif self.config.platform == Platform.MACOS:
            all_ok = all_ok and self._check_macos_prerequisites()
        elif self.config.platform == Platform.LINUX:
            all_ok = all_ok and self._check_linux_prerequisites()

        return all_ok

    def _check_windows_prerequisites(self) -> bool:
        """Check Windows-specific prerequisites."""
        all_ok = True

        # Check for NSIS if installer creation is enabled
        if self.config.create_installer:
            nsis_path = shutil.which("makensis")
            if nsis_path:
                self.logger.success(f"NSIS: {nsis_path}")
            else:
                # Check common installation paths
                common_paths = [
                    r"C:\Program Files (x86)\NSIS\makensis.exe",
                    r"C:\Program Files\NSIS\makensis.exe",
                ]
                found = False
                for path in common_paths:
                    if Path(path).exists():
                        self.logger.success(f"NSIS: {path}")
                        found = True
                        break
                if not found:
                    self.logger.warning("NSIS not found - installer creation will be skipped")

        # Check for UPX if compression is enabled
        if self.config.upx_enabled:
            upx_path = shutil.which("upx")
            if upx_path:
                self.logger.success(f"UPX: {upx_path}")
            else:
                self.logger.warning("UPX not found - compression will be disabled")
                self.config.upx_enabled = False

        return all_ok

    def _check_macos_prerequisites(self) -> bool:
        """Check macOS-specific prerequisites."""
        all_ok = True

        # Check for create-dmg if installer creation is enabled
        if self.config.create_installer:
            dmg_tool = shutil.which("create-dmg")
            if dmg_tool:
                self.logger.success(f"create-dmg: {dmg_tool}")
            else:
                self.logger.warning("create-dmg not found (brew install create-dmg)")

        # Check for code signing identity
        if self.config.sign_enabled:
            if self.config.sign_identity:
                self.logger.info(f"Code signing identity: {self.config.sign_identity}")
            else:
                self.logger.warning("No code signing identity specified")

        return all_ok

    def _check_linux_prerequisites(self) -> bool:
        """Check Linux-specific prerequisites."""
        all_ok = True

        # Check for appimagetool if AppImage creation is enabled
        if self.config.create_installer:
            appimage_tool = shutil.which("appimagetool")
            if appimage_tool:
                self.logger.success(f"appimagetool: {appimage_tool}")
            else:
                self.logger.warning("appimagetool not found - AppImage creation may fail")

        return all_ok

    def clean(self) -> None:
        """Clean build directories."""
        self.logger.section("Cleaning Build Directories")

        dirs_to_clean = [BUILD_DIR, DIST_DIR]
        for directory in dirs_to_clean:
            if directory.exists():
                self.logger.info(f"Removing: {directory}")
                shutil.rmtree(directory)

        # Remove spec files
        for spec_file in PROJECT_ROOT.glob("*.spec"):
            self.logger.info(f"Removing: {spec_file}")
            spec_file.unlink()

        self.logger.success("Clean complete")

    def build(self) -> BuildResult:
        """Execute the build process."""
        start_time = time.time()

        self.logger.header(f"Building Pecunia Desktop v{self.config.version}")
        self.logger.info(f"Platform: {self.config.platform.value}")
        self.logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Check prerequisites
        if not self.check_prerequisites():
            return BuildResult(
                success=False,
                platform=self.config.platform,
                version=self.config.version,
                error_message="Prerequisites check failed",
            )

        # Clean if requested
        if self.config.clean_before_build:
            self.clean()

        # Create output directories
        DIST_DIR.mkdir(parents=True, exist_ok=True)
        BUILD_DIR.mkdir(parents=True, exist_ok=True)

        # Execute platform-specific build
        try:
            if self.config.platform == Platform.WINDOWS:
                result = self._build_windows()
            elif self.config.platform == Platform.MACOS:
                result = self._build_macos()
            elif self.config.platform == Platform.LINUX:
                result = self._build_linux()
            else:
                raise ValueError(f"Unsupported platform: {self.config.platform}")

        except Exception as e:
            result = BuildResult(
                success=False,
                platform=self.config.platform,
                version=self.config.version,
                error_message=str(e),
            )

        # Calculate duration
        result.duration_seconds = time.time() - start_time

        # Print summary
        self._print_summary(result)

        # Clean after build if requested
        if self.config.clean_after_build and result.success:
            self.logger.section("Post-build Cleanup")
            if BUILD_DIR.exists():
                shutil.rmtree(BUILD_DIR)
                self.logger.info("Removed build directory")

        return result

    def _build_windows(self) -> BuildResult:
        """Execute Windows build."""
        self.logger.section("Building for Windows")

        # Import Windows build module
        try:
            from build_windows import WindowsBuilder
        except ImportError:
            # Try relative import
            sys.path.insert(0, str(SCRIPT_DIR))
            from build_windows import WindowsBuilder

        builder = WindowsBuilder(self.config)
        return builder.build()

    def _build_macos(self) -> BuildResult:
        """Execute macOS build."""
        self.logger.section("Building for macOS")

        try:
            from build_macos import MacOSBuilder
        except ImportError:
            sys.path.insert(0, str(SCRIPT_DIR))
            from build_macos import MacOSBuilder

        builder = MacOSBuilder(self.config)
        return builder.build()

    def _build_linux(self) -> BuildResult:
        """Execute Linux build."""
        self.logger.section("Building for Linux")

        try:
            from build_linux import LinuxBuilder
        except ImportError:
            sys.path.insert(0, str(SCRIPT_DIR))
            from build_linux import LinuxBuilder

        builder = LinuxBuilder(self.config)
        return builder.build()

    def _print_summary(self, result: BuildResult) -> None:
        """Print build summary."""
        self.logger.header("Build Summary")

        if result.success:
            self.logger.success("BUILD SUCCESSFUL")
        else:
            self.logger.error("BUILD FAILED")

        self.logger.info(f"Platform: {result.platform.value}")
        self.logger.info(f"Version: {result.version}")
        self.logger.info(f"Duration: {result.duration_seconds:.2f} seconds")

        if result.output_path:
            self.logger.info(f"Output: {result.output_path}")
            if result.output_path.exists():
                size_mb = result.output_path.stat().st_size / (1024 * 1024)
                self.logger.info(f"Size: {size_mb:.2f} MB")

        if result.installer_path:
            self.logger.info(f"Installer: {result.installer_path}")

        if result.error_message:
            self.logger.error(f"Error: {result.error_message}")

        if result.warnings:
            self.logger.warning("Warnings:")
            for warning in result.warnings:
                self.logger.warning(f"  - {warning}")

    def build_all(self) -> List[BuildResult]:
        """Build for all platforms (cross-compilation)."""
        self.logger.header("Building for All Platforms")
        self.logger.warning("Cross-compilation requires appropriate toolchains")

        results = []
        current_platform = Platform.current()

        for target_platform in Platform:
            if target_platform == current_platform:
                # Can build natively
                self.config.platform = target_platform
                results.append(self.build())
            else:
                self.logger.warning(
                    f"Skipping {target_platform.value} - cross-compilation not supported"
                )
                results.append(BuildResult(
                    success=False,
                    platform=target_platform,
                    version=self.config.version,
                    error_message="Cross-compilation not supported",
                ))

        return results


# =============================================================================
# Command Line Interface
# =============================================================================

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Pecunia Desktop Build System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build.py                          # Build for current platform
  python build.py --platform windows       # Build for Windows
  python build.py --platform macos         # Build for macOS
  python build.py --platform linux         # Build for Linux
  python build.py --all                    # Build for all platforms
  python build.py --version 1.2.3          # Build with specific version
  python build.py --bump patch             # Bump version and build
  python build.py --onedir                 # One-directory build
  python build.py --console                # Enable console window
  python build.py --debug                  # Debug build
  python build.py --no-installer           # Skip installer creation
  python build.py --clean-only             # Only clean build directories
        """
    )

    # Platform selection
    parser.add_argument(
        "--platform", "-p",
        choices=["windows", "macos", "linux"],
        help="Target platform (default: current platform)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Build for all platforms"
    )

    # Version management
    parser.add_argument(
        "--version", "-v",
        help="Version to build (e.g., 1.2.3)"
    )
    parser.add_argument(
        "--bump",
        choices=["major", "minor", "patch"],
        help="Bump version before building"
    )

    # Build modes
    parser.add_argument(
        "--onefile",
        action="store_true",
        default=True,
        help="Create single executable file (default)"
    )
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Create directory with executable and dependencies"
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Show console window (for debugging)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    # Compression
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

    # Code signing
    parser.add_argument(
        "--sign",
        action="store_true",
        help="Enable code signing"
    )
    parser.add_argument(
        "--sign-identity",
        help="Code signing identity (macOS)"
    )
    parser.add_argument(
        "--sign-cert",
        type=Path,
        help="Path to signing certificate (Windows)"
    )

    # Installer
    parser.add_argument(
        "--no-installer",
        action="store_true",
        help="Skip installer creation"
    )

    # Clean
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean before building (default)"
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not clean before building"
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Only clean build directories"
    )
    parser.add_argument(
        "--clean-after",
        action="store_true",
        help="Clean build directory after successful build"
    )

    # Output
    parser.add_argument(
        "--output-name",
        default="Pecunia",
        help="Output executable name"
    )
    parser.add_argument(
        "--no-version-suffix",
        action="store_true",
        help="Do not include version in output filename"
    )

    # Misc
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Verbose output (default)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    # Handle version bumping first
    version_manager = VersionManager()
    if args.bump:
        print(f"Bumping version ({args.bump})...")
        new_version = version_manager.bump(args.bump)
        print(f"New version: {new_version}")

    # Create build configuration
    config = BuildConfig(
        platform=Platform.from_string(args.platform) if args.platform else Platform.current(),
        version=args.version or version_manager.version,
        one_file=not args.onedir,
        console=args.console,
        debug=args.debug,
        upx_enabled=args.upx,
        upx_dir=args.upx_dir,
        sign_enabled=args.sign,
        sign_identity=args.sign_identity,
        sign_certificate=args.sign_cert,
        create_installer=not args.no_installer,
        clean_before_build=not args.no_clean,
        clean_after_build=args.clean_after,
        output_name=args.output_name,
        include_version_in_name=not args.no_version_suffix,
    )

    # Create build system
    build_system = BuildSystem(config=config, verbose=not args.quiet)

    # Handle clean-only
    if args.clean_only:
        build_system.clean()
        return 0

    # Execute build
    if args.all:
        results = build_system.build_all()
        success = all(r.success for r in results)
    else:
        result = build_system.build()
        results = [result]
        success = result.success

    # Output JSON if requested
    if args.json:
        output = {
            "results": [r.to_dict() for r in results],
            "overall_success": success,
        }
        print(json.dumps(output, indent=2))

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
