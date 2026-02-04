#!/usr/bin/env python3
"""
Pecunia Desktop - Version Management Script

Handles version bumping, changelog generation, and release preparation.
Supports semantic versioning (major.minor.patch) and pre-release versions.

Usage:
    python scripts/version.py                    # Show current version
    python scripts/version.py --bump patch       # Bump patch version
    python scripts/version.py --bump minor       # Bump minor version
    python scripts/version.py --bump major       # Bump major version
    python scripts/version.py --set 2.0.0        # Set specific version
    python scripts/version.py --changelog        # Generate changelog
    python scripts/version.py --release          # Prepare release
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# Path Configuration
# =============================================================================

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

# Version file locations
VERSION_FILE = PROJECT_ROOT / "VERSION"
CONSTANTS_FILE = SRC_DIR / "constants.py"
PYPROJECT_FILE = PROJECT_ROOT / "pyproject.toml"
PACKAGE_JSON = PROJECT_ROOT / "package.json"  # If using any JS tools
CHANGELOG_FILE = PROJECT_ROOT / "CHANGELOG.md"


# =============================================================================
# Semantic Version
# =============================================================================

class BumpType(Enum):
    """Version bump types."""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"
    BUILD = "build"


@dataclass
class SemanticVersion:
    """
    Represents a semantic version (SemVer 2.0.0).

    Format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
    Examples:
        - 1.0.0
        - 2.1.3-alpha.1
        - 3.0.0-beta.2+build.123
    """

    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    VERSION_PATTERN = re.compile(
        r'^(?P<major>0|[1-9]\d*)'
        r'\.(?P<minor>0|[1-9]\d*)'
        r'\.(?P<patch>0|[1-9]\d*)'
        r'(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)'
        r'(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?'
        r'(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
    )

    @classmethod
    def parse(cls, version_string: str) -> "SemanticVersion":
        """
        Parse a version string into a SemanticVersion object.

        Args:
            version_string: Version string to parse.

        Returns:
            SemanticVersion object.

        Raises:
            ValueError: If the version string is invalid.
        """
        version_string = version_string.strip().lstrip('v')
        match = cls.VERSION_PATTERN.match(version_string)

        if not match:
            raise ValueError(f"Invalid semantic version: {version_string}")

        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("prerelease"),
            build=match.group("build"),
        )

    def __str__(self) -> str:
        """Return the version as a string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __eq__(self, other: object) -> bool:
        """Check equality (ignoring build metadata per SemVer spec)."""
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __lt__(self, other: "SemanticVersion") -> bool:
        """Compare versions for ordering."""
        if not isinstance(other, SemanticVersion):
            return NotImplemented

        # Compare major.minor.patch
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

        # Pre-release has lower precedence than release
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        if self.prerelease and other.prerelease:
            return self._compare_prerelease(self.prerelease, other.prerelease) < 0

        return False

    @staticmethod
    def _compare_prerelease(a: str, b: str) -> int:
        """Compare pre-release identifiers."""
        parts_a = a.split(".")
        parts_b = b.split(".")

        for pa, pb in zip(parts_a, parts_b):
            # Numeric identifiers have lower precedence
            a_numeric = pa.isdigit()
            b_numeric = pb.isdigit()

            if a_numeric and b_numeric:
                diff = int(pa) - int(pb)
                if diff != 0:
                    return diff
            elif a_numeric:
                return -1
            elif b_numeric:
                return 1
            else:
                if pa < pb:
                    return -1
                if pa > pb:
                    return 1

        return len(parts_a) - len(parts_b)

    def bump(self, bump_type: BumpType, prerelease_id: Optional[str] = None) -> "SemanticVersion":
        """
        Create a new version with the specified bump.

        Args:
            bump_type: Type of version bump.
            prerelease_id: Pre-release identifier (e.g., "alpha", "beta", "rc").

        Returns:
            New SemanticVersion with bumped version.
        """
        if bump_type == BumpType.MAJOR:
            return SemanticVersion(
                major=self.major + 1,
                minor=0,
                patch=0,
                prerelease=f"{prerelease_id}.1" if prerelease_id else None,
            )
        elif bump_type == BumpType.MINOR:
            return SemanticVersion(
                major=self.major,
                minor=self.minor + 1,
                patch=0,
                prerelease=f"{prerelease_id}.1" if prerelease_id else None,
            )
        elif bump_type == BumpType.PATCH:
            return SemanticVersion(
                major=self.major,
                minor=self.minor,
                patch=self.patch + 1,
                prerelease=f"{prerelease_id}.1" if prerelease_id else None,
            )
        elif bump_type == BumpType.PRERELEASE:
            if self.prerelease:
                # Increment pre-release number
                parts = self.prerelease.rsplit(".", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    new_prerelease = f"{parts[0]}.{int(parts[1]) + 1}"
                else:
                    new_prerelease = f"{self.prerelease}.1"
            else:
                new_prerelease = f"{prerelease_id or 'alpha'}.1"

            return SemanticVersion(
                major=self.major,
                minor=self.minor,
                patch=self.patch,
                prerelease=new_prerelease,
            )
        else:
            raise ValueError(f"Unsupported bump type: {bump_type}")

    @property
    def is_prerelease(self) -> bool:
        """Check if this is a pre-release version."""
        return self.prerelease is not None

    @property
    def base_version(self) -> str:
        """Get the base version without pre-release or build metadata."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def as_tuple(self) -> Tuple[int, int, int]:
        """Return version as tuple (major, minor, patch)."""
        return (self.major, self.minor, self.patch)


# =============================================================================
# Version Manager
# =============================================================================

class VersionManager:
    """Manages version across all project files."""

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize version manager.

        Args:
            project_root: Path to project root directory.
        """
        self.project_root = project_root or PROJECT_ROOT
        self._version: Optional[SemanticVersion] = None

    def get_version(self) -> SemanticVersion:
        """
        Get the current version from project files.

        Returns:
            Current SemanticVersion.
        """
        if self._version:
            return self._version

        version_string = None

        # Try VERSION file first
        version_file = self.project_root / "VERSION"
        if version_file.exists():
            version_string = version_file.read_text().strip()

        # Try constants.py
        if not version_string:
            constants_file = self.project_root / "src" / "constants.py"
            if constants_file.exists():
                content = constants_file.read_text()
                match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    version_string = match.group(1)

        # Try pyproject.toml
        if not version_string:
            pyproject_file = self.project_root / "pyproject.toml"
            if pyproject_file.exists():
                content = pyproject_file.read_text()
                match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
                if match:
                    version_string = match.group(1)

        # Default
        if not version_string:
            version_string = "1.0.0"

        self._version = SemanticVersion.parse(version_string)
        return self._version

    def set_version(self, version: SemanticVersion) -> None:
        """
        Set version in all project files.

        Args:
            version: New version to set.
        """
        version_string = str(version)
        self._version = version

        print(f"Setting version to {version_string}")

        # Update VERSION file
        version_file = self.project_root / "VERSION"
        version_file.write_text(f"{version_string}\n")
        print(f"  Updated: {version_file}")

        # Update constants.py
        constants_file = self.project_root / "src" / "constants.py"
        if constants_file.exists():
            content = constants_file.read_text()
            content = re.sub(
                r'(APP_VERSION\s*=\s*["\'])[^"\']+(["\'])',
                rf'\g<1>{version_string}\g<2>',
                content,
            )
            constants_file.write_text(content)
            print(f"  Updated: {constants_file}")

        # Update pyproject.toml
        pyproject_file = self.project_root / "pyproject.toml"
        if pyproject_file.exists():
            content = pyproject_file.read_text()
            content = re.sub(
                r'^(version\s*=\s*["\'])[^"\']+(["\'])',
                rf'\g<1>{version_string}\g<2>',
                content,
                flags=re.MULTILINE,
            )
            pyproject_file.write_text(content)
            print(f"  Updated: {pyproject_file}")

        # Update Info.plist (macOS)
        info_plist = self.project_root / "installer" / "macos" / "Info.plist"
        if info_plist.exists():
            content = info_plist.read_text()
            # Update CFBundleVersion and CFBundleShortVersionString
            content = re.sub(
                r'(<key>CFBundleVersion</key>\s*<string>)[^<]+(</string>)',
                rf'\g<1>{version_string}\g<2>',
                content,
            )
            content = re.sub(
                r'(<key>CFBundleShortVersionString</key>\s*<string>)[^<]+(</string>)',
                rf'\g<1>{version_string}\g<2>',
                content,
            )
            info_plist.write_text(content)
            print(f"  Updated: {info_plist}")

    def bump_version(
        self,
        bump_type: BumpType,
        prerelease_id: Optional[str] = None,
    ) -> SemanticVersion:
        """
        Bump the version and update all files.

        Args:
            bump_type: Type of version bump.
            prerelease_id: Pre-release identifier for pre-release bumps.

        Returns:
            New version after bump.
        """
        current = self.get_version()
        new_version = current.bump(bump_type, prerelease_id)
        self.set_version(new_version)
        return new_version


# =============================================================================
# Changelog Generator
# =============================================================================

@dataclass
class ChangelogEntry:
    """Represents a single changelog entry."""
    type: str  # feat, fix, docs, style, refactor, perf, test, chore
    scope: Optional[str]
    description: str
    breaking: bool = False
    commit_hash: Optional[str] = None
    author: Optional[str] = None


class ChangelogGenerator:
    """Generates changelog from git commits."""

    # Conventional commit pattern
    COMMIT_PATTERN = re.compile(
        r'^(?P<type>\w+)'
        r'(?:\((?P<scope>[^)]+)\))?'
        r'(?P<breaking>!)?\s*:\s*'
        r'(?P<description>.+)$'
    )

    TYPE_LABELS = {
        "feat": "Features",
        "fix": "Bug Fixes",
        "docs": "Documentation",
        "style": "Styles",
        "refactor": "Code Refactoring",
        "perf": "Performance Improvements",
        "test": "Tests",
        "build": "Build System",
        "ci": "Continuous Integration",
        "chore": "Chores",
        "revert": "Reverts",
    }

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize changelog generator."""
        self.project_root = project_root or PROJECT_ROOT

    def get_git_log(
        self,
        since_tag: Optional[str] = None,
        until_tag: Optional[str] = None,
    ) -> List[ChangelogEntry]:
        """
        Get git log entries as changelog entries.

        Args:
            since_tag: Start from this tag (exclusive).
            until_tag: End at this tag (inclusive).

        Returns:
            List of changelog entries.
        """
        # Build git log command
        cmd = ["git", "log", "--pretty=format:%H|%an|%s"]

        if since_tag and until_tag:
            cmd.append(f"{since_tag}..{until_tag}")
        elif since_tag:
            cmd.append(f"{since_tag}..HEAD")
        elif until_tag:
            cmd.append(until_tag)

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            return []
        except FileNotFoundError:
            print("Warning: git not found, cannot generate changelog")
            return []

        entries = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|", 2)
            if len(parts) != 3:
                continue

            commit_hash, author, message = parts
            entry = self._parse_commit_message(message)

            if entry:
                entry.commit_hash = commit_hash[:8]
                entry.author = author
                entries.append(entry)

        return entries

    def _parse_commit_message(self, message: str) -> Optional[ChangelogEntry]:
        """Parse a commit message into a changelog entry."""
        match = self.COMMIT_PATTERN.match(message)
        if not match:
            return None

        return ChangelogEntry(
            type=match.group("type"),
            scope=match.group("scope"),
            description=match.group("description"),
            breaking=bool(match.group("breaking")),
        )

    def generate_changelog(
        self,
        version: str,
        entries: List[ChangelogEntry],
        date: Optional[datetime] = None,
    ) -> str:
        """
        Generate changelog markdown for a version.

        Args:
            version: Version string.
            entries: List of changelog entries.
            date: Release date (default: now).

        Returns:
            Changelog markdown string.
        """
        if date is None:
            date = datetime.now()

        lines = [
            f"## [{version}] - {date.strftime('%Y-%m-%d')}",
            "",
        ]

        # Group entries by type
        by_type: Dict[str, List[ChangelogEntry]] = {}
        breaking_changes: List[ChangelogEntry] = []

        for entry in entries:
            if entry.breaking:
                breaking_changes.append(entry)
            if entry.type not in by_type:
                by_type[entry.type] = []
            by_type[entry.type].append(entry)

        # Add breaking changes section
        if breaking_changes:
            lines.append("### BREAKING CHANGES")
            lines.append("")
            for entry in breaking_changes:
                scope_str = f"**{entry.scope}:** " if entry.scope else ""
                lines.append(f"* {scope_str}{entry.description}")
            lines.append("")

        # Add sections by type
        for type_key, label in self.TYPE_LABELS.items():
            type_entries = by_type.get(type_key, [])
            if type_entries:
                lines.append(f"### {label}")
                lines.append("")
                for entry in type_entries:
                    scope_str = f"**{entry.scope}:** " if entry.scope else ""
                    hash_str = f" ({entry.commit_hash})" if entry.commit_hash else ""
                    lines.append(f"* {scope_str}{entry.description}{hash_str}")
                lines.append("")

        return "\n".join(lines)

    def update_changelog_file(
        self,
        version: str,
        entries: List[ChangelogEntry],
        changelog_path: Optional[Path] = None,
    ) -> None:
        """
        Update the CHANGELOG.md file with new version.

        Args:
            version: Version string.
            entries: List of changelog entries.
            changelog_path: Path to changelog file.
        """
        changelog_path = changelog_path or CHANGELOG_FILE
        new_content = self.generate_changelog(version, entries)

        if changelog_path.exists():
            existing = changelog_path.read_text()
            # Find the first version header and insert before it
            match = re.search(r'^## \[', existing, re.MULTILINE)
            if match:
                content = existing[:match.start()] + new_content + "\n" + existing[match.start():]
            else:
                content = existing + "\n" + new_content
        else:
            # Create new changelog
            content = f"""# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

{new_content}
"""

        changelog_path.write_text(content)
        print(f"Updated: {changelog_path}")


# =============================================================================
# Release Manager
# =============================================================================

class ReleaseManager:
    """Manages the release process."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize release manager."""
        self.project_root = project_root or PROJECT_ROOT
        self.version_manager = VersionManager(project_root)
        self.changelog_generator = ChangelogGenerator(project_root)

    def prepare_release(
        self,
        bump_type: BumpType,
        prerelease_id: Optional[str] = None,
        skip_changelog: bool = False,
        skip_git: bool = False,
    ) -> SemanticVersion:
        """
        Prepare a new release.

        Args:
            bump_type: Type of version bump.
            prerelease_id: Pre-release identifier.
            skip_changelog: Skip changelog generation.
            skip_git: Skip git operations.

        Returns:
            New version.
        """
        print("\n" + "=" * 60)
        print("Preparing Release")
        print("=" * 60 + "\n")

        # Get current version and calculate new version
        current_version = self.version_manager.get_version()
        print(f"Current version: {current_version}")

        new_version = current_version.bump(bump_type, prerelease_id)
        print(f"New version: {new_version}")

        # Update version in all files
        print("\nUpdating version files...")
        self.version_manager.set_version(new_version)

        # Generate changelog
        if not skip_changelog:
            print("\nGenerating changelog...")
            # Get last tag
            try:
                result = subprocess.run(
                    ["git", "describe", "--tags", "--abbrev=0"],
                    cwd=str(self.project_root),
                    capture_output=True,
                    text=True,
                )
                last_tag = result.stdout.strip() if result.returncode == 0 else None
            except:
                last_tag = None

            entries = self.changelog_generator.get_git_log(since_tag=last_tag)
            if entries:
                self.changelog_generator.update_changelog_file(str(new_version), entries)
            else:
                print("  No changelog entries found")

        # Git operations
        if not skip_git:
            print("\nGit operations...")
            try:
                # Stage changes
                subprocess.run(
                    ["git", "add", "-A"],
                    cwd=str(self.project_root),
                    check=True,
                )

                # Commit
                subprocess.run(
                    ["git", "commit", "-m", f"chore(release): {new_version}"],
                    cwd=str(self.project_root),
                    check=True,
                )
                print(f"  Created commit: chore(release): {new_version}")

                # Tag
                tag_name = f"v{new_version}"
                subprocess.run(
                    ["git", "tag", "-a", tag_name, "-m", f"Release {new_version}"],
                    cwd=str(self.project_root),
                    check=True,
                )
                print(f"  Created tag: {tag_name}")

            except subprocess.CalledProcessError as e:
                print(f"  Warning: Git operation failed: {e}")
            except FileNotFoundError:
                print("  Warning: git not found")

        print("\n" + "=" * 60)
        print(f"Release {new_version} prepared successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Review changes: git diff HEAD~1")
        print("  2. Push changes: git push && git push --tags")
        print("  3. Build release: python scripts/build.py")
        print()

        return new_version


# =============================================================================
# Command Line Interface
# =============================================================================

def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Version management for Pecunia Desktop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python version.py                         # Show current version
  python version.py --bump patch            # Bump patch: 1.0.0 -> 1.0.1
  python version.py --bump minor            # Bump minor: 1.0.0 -> 1.1.0
  python version.py --bump major            # Bump major: 1.0.0 -> 2.0.0
  python version.py --bump patch --pre beta # Bump with pre-release: 1.0.0 -> 1.0.1-beta.1
  python version.py --set 2.0.0             # Set specific version
  python version.py --changelog             # Generate changelog
  python version.py --release               # Full release process
        """
    )

    parser.add_argument(
        "--bump", "-b",
        choices=["major", "minor", "patch", "prerelease"],
        help="Bump version by specified type"
    )
    parser.add_argument(
        "--pre", "--prerelease",
        help="Pre-release identifier (alpha, beta, rc, etc.)"
    )
    parser.add_argument(
        "--set", "-s",
        dest="set_version",
        help="Set specific version"
    )
    parser.add_argument(
        "--changelog", "-c",
        action="store_true",
        help="Generate changelog"
    )
    parser.add_argument(
        "--release", "-r",
        action="store_true",
        help="Prepare full release (bump, changelog, git)"
    )
    parser.add_argument(
        "--skip-git",
        action="store_true",
        help="Skip git operations in release"
    )
    parser.add_argument(
        "--skip-changelog",
        action="store_true",
        help="Skip changelog in release"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    version_manager = VersionManager()

    # Show current version if no action specified
    if not any([args.bump, args.set_version, args.changelog, args.release]):
        version = version_manager.get_version()
        if args.json:
            print(json.dumps({
                "version": str(version),
                "major": version.major,
                "minor": version.minor,
                "patch": version.patch,
                "prerelease": version.prerelease,
                "build": version.build,
            }, indent=2))
        else:
            print(f"Current version: {version}")
        return 0

    # Set specific version
    if args.set_version:
        try:
            version = SemanticVersion.parse(args.set_version)
            version_manager.set_version(version)
            print(f"Version set to: {version}")
            return 0
        except ValueError as e:
            print(f"Error: {e}")
            return 1

    # Bump version
    if args.bump:
        bump_type = BumpType(args.bump)
        new_version = version_manager.bump_version(bump_type, args.pre)
        if args.json:
            print(json.dumps({"version": str(new_version)}, indent=2))
        else:
            print(f"Version bumped to: {new_version}")
        return 0

    # Generate changelog
    if args.changelog:
        generator = ChangelogGenerator()
        version = version_manager.get_version()
        entries = generator.get_git_log()
        if entries:
            changelog = generator.generate_changelog(str(version), entries)
            print(changelog)
        else:
            print("No changelog entries found")
        return 0

    # Full release
    if args.release:
        if not args.bump:
            print("Error: --release requires --bump")
            return 1

        release_manager = ReleaseManager()
        bump_type = BumpType(args.bump)
        release_manager.prepare_release(
            bump_type=bump_type,
            prerelease_id=args.pre,
            skip_changelog=args.skip_changelog,
            skip_git=args.skip_git,
        )
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
