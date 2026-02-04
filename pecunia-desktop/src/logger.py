"""
Logging configuration for Pecunia Desktop.

Provides structured logging with rotating file handlers, console output,
and per-module log level configuration.
"""

import os
import sys
import json
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass, field

from config import get_data_dir


# =============================================================================
# Constants
# =============================================================================

DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Log file settings
LOG_DIR_NAME = "logs"
LOG_FILE_NAME = "pecunia.log"
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_FILE_BACKUP_COUNT = 5

# Debug log file (more verbose)
DEBUG_LOG_FILE_NAME = "pecunia_debug.log"
DEBUG_LOG_FILE_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
DEBUG_LOG_FILE_BACKUP_COUNT = 3

# Error log file (errors only)
ERROR_LOG_FILE_NAME = "pecunia_errors.log"
ERROR_LOG_FILE_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
ERROR_LOG_FILE_BACKUP_COUNT = 10


# =============================================================================
# Custom Formatters
# =============================================================================

class StructuredFormatter(logging.Formatter):
    """
    Formatter that outputs structured log records.

    Produces human-readable logs with optional JSON metadata.
    """

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        include_extra: bool = True,
    ):
        super().__init__(fmt or DEFAULT_LOG_FORMAT, datefmt or DEFAULT_DATE_FORMAT)
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with extra fields if present."""
        # Add standard fields
        record.levelname = record.levelname.ljust(8)

        # Format the base message
        message = super().format(record)

        # Add extra fields if present and enabled
        if self.include_extra:
            extra_fields = self._extract_extra(record)
            if extra_fields:
                extra_str = json.dumps(extra_fields, default=str, indent=None)
                message = f"{message} | {extra_str}"

        return message

    def _extract_extra(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Extract extra fields from the log record."""
        standard_attrs = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "exc_info", "exc_text", "thread", "threadName",
            "message", "asctime",
        }

        return {
            key: value
            for key, value in record.__dict__.items()
            if key not in standard_attrs and not key.startswith("_")
        }


class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON-formatted log records.

    Useful for log aggregation systems like ELK stack.
    """

    def __init__(self, include_traceback: bool = True):
        super().__init__()
        self.include_traceback = include_traceback

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
        }

        # Add exception info if present
        if record.exc_info and self.include_traceback:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        extra = StructuredFormatter._extract_extra(self, record)
        if extra:
            log_data["extra"] = extra

        return json.dumps(log_data, default=str)


class ColoredFormatter(logging.Formatter):
    """
    Formatter that adds ANSI color codes to console output.

    Colors are applied based on log level.
    """

    COLORS = {
        logging.DEBUG: "\033[36m",      # Cyan
        logging.INFO: "\033[32m",       # Green
        logging.WARNING: "\033[33m",    # Yellow
        logging.ERROR: "\033[31m",      # Red
        logging.CRITICAL: "\033[35m",   # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        use_colors: bool = True,
    ):
        super().__init__(fmt or DEFAULT_LOG_FORMAT, datefmt or DEFAULT_DATE_FORMAT)
        self.use_colors = use_colors and self._supports_color()

    def _supports_color(self) -> bool:
        """Check if the terminal supports color."""
        # Windows console needs special handling
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
                return True
            except Exception:
                return False

        # Unix-like systems
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with optional colors."""
        if self.use_colors:
            color = self.COLORS.get(record.levelno, self.RESET)
            record.levelname = f"{color}{self.BOLD}{record.levelname.ljust(8)}{self.RESET}"
        else:
            record.levelname = record.levelname.ljust(8)

        return super().format(record)


# =============================================================================
# Custom Handlers
# =============================================================================

class BufferedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    Rotating file handler with buffered writes for better performance.
    """

    def __init__(
        self,
        filename: Union[str, Path],
        mode: str = "a",
        maxBytes: int = 0,
        backupCount: int = 0,
        encoding: str = "utf-8",
        delay: bool = False,
        buffer_size: int = 8192,
    ):
        super().__init__(
            str(filename),
            mode=mode,
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
        )
        self._buffer: list[str] = []
        self._buffer_size = buffer_size
        self._current_size = 0

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record, buffering if appropriate."""
        try:
            msg = self.format(record) + self.terminator
            self._buffer.append(msg)
            self._current_size += len(msg)

            # Flush if buffer is full or if it's an error
            if self._current_size >= self._buffer_size or record.levelno >= logging.ERROR:
                self.flush()

        except Exception:
            self.handleError(record)

    def flush(self) -> None:
        """Flush the buffer to file."""
        if self._buffer:
            self.acquire()
            try:
                if self.stream is None:
                    self.stream = self._open()

                for msg in self._buffer:
                    self.stream.write(msg)

                self.stream.flush()
                self._buffer.clear()
                self._current_size = 0

            finally:
                self.release()


# =============================================================================
# Log Level Configuration
# =============================================================================

@dataclass
class ModuleLogConfig:
    """Configuration for per-module log levels."""

    # Default levels
    default_level: int = logging.INFO

    # Module-specific levels
    module_levels: Dict[str, int] = field(default_factory=lambda: {
        # Third-party libraries (reduce noise)
        "aiohttp": logging.WARNING,
        "asyncio": logging.WARNING,
        "urllib3": logging.WARNING,
        "httpx": logging.WARNING,
        "httpcore": logging.WARNING,
        "PIL": logging.WARNING,

        # PyQt6 (reduce noise)
        "PyQt6": logging.WARNING,

        # Database
        "sqlalchemy": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,

        # Application modules
        "pecunia.api": logging.INFO,
        "pecunia.sync": logging.INFO,
        "pecunia.database": logging.INFO,
        "pecunia.ui": logging.INFO,
    })

    def apply(self) -> None:
        """Apply the configured log levels."""
        for module_name, level in self.module_levels.items():
            logging.getLogger(module_name).setLevel(level)


# =============================================================================
# Logger Setup
# =============================================================================

class LoggerSetup:
    """
    Centralized logger configuration and management.

    Provides methods for setting up various logging handlers
    and configuring log levels.
    """

    _instance: Optional["LoggerSetup"] = None
    _initialized: bool = False

    def __new__(cls):
        """Singleton pattern for logger setup."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._log_dir: Optional[Path] = None
            self._root_logger: logging.Logger = logging.getLogger()
            self._handlers: Dict[str, logging.Handler] = {}
            self._module_config = ModuleLogConfig()
            LoggerSetup._initialized = True

    @property
    def log_dir(self) -> Path:
        """Get or create the log directory."""
        if self._log_dir is None:
            self._log_dir = get_data_dir() / LOG_DIR_NAME
            self._log_dir.mkdir(parents=True, exist_ok=True)
        return self._log_dir

    def setup(
        self,
        level: int = DEFAULT_LOG_LEVEL,
        enable_console: bool = True,
        enable_file: bool = True,
        enable_debug_file: bool = False,
        enable_error_file: bool = True,
        colored_console: bool = True,
        structured_logs: bool = True,
    ) -> None:
        """
        Configure the logging system.

        Args:
            level: Default log level.
            enable_console: Enable console output.
            enable_file: Enable main log file.
            enable_debug_file: Enable debug log file (verbose).
            enable_error_file: Enable error-only log file.
            colored_console: Use colored output in console.
            structured_logs: Use structured log format.
        """
        # Clear existing handlers
        self._clear_handlers()

        # Set root logger level
        self._root_logger.setLevel(level)

        # Add handlers
        if enable_console:
            self._add_console_handler(level, colored_console, structured_logs)

        if enable_file:
            self._add_file_handler(level, structured_logs)

        if enable_debug_file:
            self._add_debug_file_handler()

        if enable_error_file:
            self._add_error_file_handler()

        # Apply module-specific levels
        self._module_config.apply()

        logging.info("Logging system initialized")

    def _clear_handlers(self) -> None:
        """Remove all existing handlers."""
        for handler in self._root_logger.handlers[:]:
            handler.close()
            self._root_logger.removeHandler(handler)
        self._handlers.clear()

    def _add_console_handler(
        self,
        level: int,
        colored: bool,
        structured: bool,
    ) -> None:
        """Add console handler."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        if colored:
            formatter = ColoredFormatter(include_extra=structured)
        elif structured:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)

        handler.setFormatter(formatter)
        self._root_logger.addHandler(handler)
        self._handlers["console"] = handler

    def _add_file_handler(self, level: int, structured: bool) -> None:
        """Add main rotating file handler."""
        log_file = self.log_dir / LOG_FILE_NAME

        handler = BufferedRotatingFileHandler(
            filename=log_file,
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setLevel(level)

        if structured:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)

        handler.setFormatter(formatter)
        self._root_logger.addHandler(handler)
        self._handlers["file"] = handler

    def _add_debug_file_handler(self) -> None:
        """Add debug rotating file handler with JSON format."""
        log_file = self.log_dir / DEBUG_LOG_FILE_NAME

        handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=DEBUG_LOG_FILE_MAX_BYTES,
            backupCount=DEBUG_LOG_FILE_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(JSONFormatter())

        self._root_logger.addHandler(handler)
        self._handlers["debug_file"] = handler

    def _add_error_file_handler(self) -> None:
        """Add error-only rotating file handler."""
        log_file = self.log_dir / ERROR_LOG_FILE_NAME

        handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=ERROR_LOG_FILE_MAX_BYTES,
            backupCount=ERROR_LOG_FILE_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setLevel(logging.ERROR)
        handler.setFormatter(StructuredFormatter(include_extra=True))

        self._root_logger.addHandler(handler)
        self._handlers["error_file"] = handler

    def set_level(self, level: Union[int, str]) -> None:
        """
        Set the root log level.

        Args:
            level: Log level (int or string like 'DEBUG', 'INFO', etc.).
        """
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)

        self._root_logger.setLevel(level)
        for handler in self._handlers.values():
            if handler.level < logging.ERROR:  # Don't change error-only handlers
                handler.setLevel(level)

    def set_module_level(self, module: str, level: Union[int, str]) -> None:
        """
        Set the log level for a specific module.

        Args:
            module: Module name.
            level: Log level.
        """
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)

        self._module_config.module_levels[module] = level
        logging.getLogger(module).setLevel(level)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger with the specified name.

        Args:
            name: Logger name.

        Returns:
            Configured logger instance.
        """
        return logging.getLogger(name)

    def shutdown(self) -> None:
        """Shutdown the logging system."""
        logging.info("Shutting down logging system")

        for handler in self._handlers.values():
            handler.flush()
            handler.close()

        self._clear_handlers()


# =============================================================================
# Module-Level Functions
# =============================================================================

_logger_setup: Optional[LoggerSetup] = None


def setup_logging(
    level: int = DEFAULT_LOG_LEVEL,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_debug_file: bool = False,
    enable_error_file: bool = True,
    colored_console: bool = True,
    structured_logs: bool = True,
) -> LoggerSetup:
    """
    Set up the logging system.

    Args:
        level: Default log level.
        enable_console: Enable console output.
        enable_file: Enable main log file.
        enable_debug_file: Enable debug log file.
        enable_error_file: Enable error-only log file.
        colored_console: Use colored output in console.
        structured_logs: Use structured log format.

    Returns:
        The LoggerSetup instance.
    """
    global _logger_setup
    _logger_setup = LoggerSetup()
    _logger_setup.setup(
        level=level,
        enable_console=enable_console,
        enable_file=enable_file,
        enable_debug_file=enable_debug_file,
        enable_error_file=enable_error_file,
        colored_console=colored_console,
        structured_logs=structured_logs,
    )
    return _logger_setup


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name.

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)


def get_logger_setup() -> Optional[LoggerSetup]:
    """Get the global LoggerSetup instance."""
    return _logger_setup


def shutdown_logging() -> None:
    """Shutdown the logging system."""
    if _logger_setup:
        _logger_setup.shutdown()
