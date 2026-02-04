"""
Form Validators Module

Custom QValidator implementations for form input validation.
Provides real-time validation with error messages for common input types.
"""

from PyQt6.QtGui import QValidator, QRegularExpressionValidator
from PyQt6.QtCore import QRegularExpression, QDate, QLocale
from typing import Optional, Tuple, Callable, List
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
import re


class ValidationResult:
    """
    Result container for validation operations.

    Provides a unified way to return validation state and messages.
    """

    def __init__(self, is_valid: bool, message: str = "", value: str = ""):
        self.is_valid = is_valid
        self.message = message
        self.value = value

    def __bool__(self) -> bool:
        return self.is_valid

    @classmethod
    def valid(cls, value: str = "") -> 'ValidationResult':
        """Create a valid result."""
        return cls(True, "", value)

    @classmethod
    def invalid(cls, message: str, value: str = "") -> 'ValidationResult':
        """Create an invalid result with error message."""
        return cls(False, message, value)

    @classmethod
    def intermediate(cls, value: str = "") -> 'ValidationResult':
        """Create an intermediate result (partial valid input)."""
        result = cls(False, "", value)
        result._intermediate = True
        return result

    @property
    def is_intermediate(self) -> bool:
        """Check if this is an intermediate validation state."""
        return getattr(self, '_intermediate', False)


class BaseValidator(QValidator):
    """
    Base class for custom validators.

    Provides common functionality and error message support.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._error_message: str = ""
        self._custom_message: Optional[str] = None

    @property
    def error_message(self) -> str:
        """Get the current error message."""
        return self._custom_message or self._error_message

    def set_custom_message(self, message: str):
        """Set a custom error message."""
        self._custom_message = message

    def clear_custom_message(self):
        """Clear custom error message."""
        self._custom_message = None

    def validate_value(self, value: str) -> ValidationResult:
        """
        Validate a value and return detailed result.

        Override in subclasses for specific validation logic.
        """
        return ValidationResult.valid(value)

    def validate(self, input_str: str, pos: int) -> Tuple[QValidator.State, str, int]:
        """QValidator interface implementation."""
        result = self.validate_value(input_str)

        if result.is_valid:
            return (QValidator.State.Acceptable, input_str, pos)
        elif result.is_intermediate:
            return (QValidator.State.Intermediate, input_str, pos)
        else:
            self._error_message = result.message
            return (QValidator.State.Invalid, input_str, pos)


class RequiredValidator(BaseValidator):
    """
    Validates that a field is not empty.

    Supports trimming whitespace and custom empty value check.
    """

    def __init__(
        self,
        parent=None,
        trim_whitespace: bool = True,
        allow_whitespace_only: bool = False,
        min_length: int = 1
    ):
        super().__init__(parent)
        self._trim_whitespace = trim_whitespace
        self._allow_whitespace_only = allow_whitespace_only
        self._min_length = min_length

    def validate_value(self, value: str) -> ValidationResult:
        """Validate that value is not empty."""
        check_value = value.strip() if self._trim_whitespace else value

        if not check_value:
            return ValidationResult.invalid("This field is required")

        if not self._allow_whitespace_only and value.strip() == "" and value != "":
            return ValidationResult.invalid("Value cannot be only whitespace")

        if len(check_value) < self._min_length:
            return ValidationResult.invalid(
                f"Minimum {self._min_length} character(s) required"
            )

        return ValidationResult.valid(value)

    def validate(self, input_str: str, pos: int) -> Tuple[QValidator.State, str, int]:
        """Allow empty during typing but mark as intermediate."""
        if not input_str:
            return (QValidator.State.Intermediate, input_str, pos)
        return super().validate(input_str, pos)


class AmountValidator(BaseValidator):
    """
    Validates monetary/currency amounts.

    Supports configurable decimal places, range limits, and locale formatting.
    """

    def __init__(
        self,
        parent=None,
        decimal_places: int = 2,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
        allow_negative: bool = True,
        allow_zero: bool = True,
        locale: Optional[QLocale] = None
    ):
        super().__init__(parent)
        self._decimal_places = decimal_places
        self._minimum = minimum
        self._maximum = maximum
        self._allow_negative = allow_negative
        self._allow_zero = allow_zero
        self._locale = locale or QLocale.system()

        # Build regex pattern for amount validation
        self._build_pattern()

    def _build_pattern(self):
        """Build the regex pattern for amount validation."""
        # Get locale decimal separator
        decimal_sep = self._locale.decimalPoint()
        decimal_sep_escaped = re.escape(decimal_sep)

        # Build pattern
        sign_part = "-?" if self._allow_negative else ""
        integer_part = r"\d{1,15}"  # Up to 15 digits before decimal
        decimal_part = f"({decimal_sep_escaped}\\d{{0,{self._decimal_places}}})?"

        self._pattern = re.compile(f"^{sign_part}{integer_part}{decimal_part}$")
        self._partial_pattern = re.compile(f"^{sign_part}\\d*{decimal_sep_escaped}?\\d*$")

    def validate_value(self, value: str) -> ValidationResult:
        """Validate amount value."""
        if not value or value == "-":
            return ValidationResult.intermediate(value)

        # Normalize decimal separator
        decimal_sep = self._locale.decimalPoint()
        normalized = value.replace(decimal_sep, ".")

        try:
            amount = Decimal(normalized)
        except InvalidOperation:
            return ValidationResult.invalid("Invalid amount format")

        # Check zero
        if not self._allow_zero and amount == 0:
            return ValidationResult.invalid("Amount cannot be zero")

        # Check negative
        if not self._allow_negative and amount < 0:
            return ValidationResult.invalid("Amount cannot be negative")

        # Check range
        if self._minimum is not None and float(amount) < self._minimum:
            return ValidationResult.invalid(
                f"Amount must be at least {self._format_amount(self._minimum)}"
            )

        if self._maximum is not None and float(amount) > self._maximum:
            return ValidationResult.invalid(
                f"Amount cannot exceed {self._format_amount(self._maximum)}"
            )

        # Check decimal places
        decimal_str = normalized.split(".")[-1] if "." in normalized else ""
        if len(decimal_str) > self._decimal_places:
            return ValidationResult.invalid(
                f"Maximum {self._decimal_places} decimal places allowed"
            )

        return ValidationResult.valid(value)

    def _format_amount(self, amount: float) -> str:
        """Format amount for display in messages."""
        return f"{amount:,.{self._decimal_places}f}"

    def validate(self, input_str: str, pos: int) -> Tuple[QValidator.State, str, int]:
        """Validate with support for partial input."""
        if not input_str:
            return (QValidator.State.Intermediate, input_str, pos)

        # Check for partial valid input (e.g., "-", "12.", etc.)
        if self._partial_pattern.match(input_str):
            result = self.validate_value(input_str)
            if result.is_valid:
                return (QValidator.State.Acceptable, input_str, pos)
            elif result.is_intermediate or input_str in ["-", ".", "-."]:
                return (QValidator.State.Intermediate, input_str, pos)
            else:
                self._error_message = result.message
                return (QValidator.State.Invalid, input_str, pos)

        return (QValidator.State.Invalid, input_str, pos)

    def set_range(self, minimum: Optional[float], maximum: Optional[float]):
        """Set the valid range."""
        self._minimum = minimum
        self._maximum = maximum

    def get_decimal_value(self, value: str) -> Optional[Decimal]:
        """Parse and return the decimal value."""
        if not value:
            return None

        decimal_sep = self._locale.decimalPoint()
        normalized = value.replace(decimal_sep, ".")

        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None


class DateValidator(BaseValidator):
    """
    Validates date strings in various formats.

    Supports multiple date formats, range constraints, and locale awareness.
    """

    # Common date formats to try
    DEFAULT_FORMATS = [
        "%Y-%m-%d",      # ISO format: 2024-01-15
        "%d/%m/%Y",      # European: 15/01/2024
        "%m/%d/%Y",      # US: 01/15/2024
        "%d-%m-%Y",      # Alternative: 15-01-2024
        "%d.%m.%Y",      # German style: 15.01.2024
        "%Y/%m/%d",      # Alternative ISO: 2024/01/15
    ]

    def __init__(
        self,
        parent=None,
        date_format: str = "%Y-%m-%d",
        formats: Optional[List[str]] = None,
        minimum_date: Optional[date] = None,
        maximum_date: Optional[date] = None,
        allow_future: bool = True,
        allow_past: bool = True
    ):
        super().__init__(parent)
        self._primary_format = date_format
        self._formats = formats or [date_format]
        self._minimum_date = minimum_date
        self._maximum_date = maximum_date
        self._allow_future = allow_future
        self._allow_past = allow_past

    def validate_value(self, value: str) -> ValidationResult:
        """Validate date string."""
        if not value.strip():
            return ValidationResult.intermediate(value)

        # Try to parse with configured formats
        parsed_date = None
        for fmt in self._formats:
            try:
                parsed_date = datetime.strptime(value.strip(), fmt).date()
                break
            except ValueError:
                continue

        if parsed_date is None:
            return ValidationResult.invalid(
                f"Invalid date format. Use {self._primary_format}"
            )

        today = date.today()

        # Check future dates
        if not self._allow_future and parsed_date > today:
            return ValidationResult.invalid("Future dates are not allowed")

        # Check past dates
        if not self._allow_past and parsed_date < today:
            return ValidationResult.invalid("Past dates are not allowed")

        # Check minimum date
        if self._minimum_date and parsed_date < self._minimum_date:
            return ValidationResult.invalid(
                f"Date must be on or after {self._minimum_date.strftime(self._primary_format)}"
            )

        # Check maximum date
        if self._maximum_date and parsed_date > self._maximum_date:
            return ValidationResult.invalid(
                f"Date must be on or before {self._maximum_date.strftime(self._primary_format)}"
            )

        return ValidationResult.valid(value)

    def validate(self, input_str: str, pos: int) -> Tuple[QValidator.State, str, int]:
        """Allow partial input during typing."""
        # Allow partial date entry
        if not input_str or len(input_str) < len(self._primary_format):
            # Check if it could be a valid partial date
            if re.match(r'^[\d\-/\.]*$', input_str):
                return (QValidator.State.Intermediate, input_str, pos)

        return super().validate(input_str, pos)

    def set_date_range(self, minimum: Optional[date], maximum: Optional[date]):
        """Set the valid date range."""
        self._minimum_date = minimum
        self._maximum_date = maximum

    def parse_date(self, value: str) -> Optional[date]:
        """Parse a date string and return a date object."""
        for fmt in self._formats:
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
        return None


class EmailValidator(BaseValidator):
    """
    Validates email addresses.

    Uses RFC 5322 compliant pattern with optional strict mode.
    """

    # Basic email pattern (covers most cases)
    BASIC_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    # More strict RFC 5322 pattern
    STRICT_PATTERN = (
        r"^(?:[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*"
        r'|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]'
        r'|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@'
        r'(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z0-9]'
        r'(?:[a-zA-Z0-9-]*[a-zA-Z0-9])?'
        r'|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?'
        r'|[a-zA-Z0-9-]*[a-zA-Z0-9]:'
        r'(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]'
        r'|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])$'
    )

    def __init__(
        self,
        parent=None,
        strict: bool = False,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None
    ):
        super().__init__(parent)
        self._strict = strict
        self._allowed_domains = allowed_domains
        self._blocked_domains = blocked_domains or []

        pattern = self.STRICT_PATTERN if strict else self.BASIC_PATTERN
        self._pattern = re.compile(pattern, re.IGNORECASE)

    def validate_value(self, value: str) -> ValidationResult:
        """Validate email address."""
        if not value.strip():
            return ValidationResult.intermediate(value)

        email = value.strip().lower()

        # Check basic format
        if not self._pattern.match(email):
            return ValidationResult.invalid("Please enter a valid email address")

        # Extract domain
        try:
            domain = email.split('@')[1]
        except IndexError:
            return ValidationResult.invalid("Invalid email format")

        # Check allowed domains
        if self._allowed_domains:
            if not any(domain.endswith(d.lower()) for d in self._allowed_domains):
                return ValidationResult.invalid(
                    f"Email must be from: {', '.join(self._allowed_domains)}"
                )

        # Check blocked domains
        if any(domain.endswith(d.lower()) for d in self._blocked_domains):
            return ValidationResult.invalid("This email domain is not allowed")

        return ValidationResult.valid(value)

    def validate(self, input_str: str, pos: int) -> Tuple[QValidator.State, str, int]:
        """Allow partial input during typing."""
        if not input_str or '@' not in input_str:
            # Still typing, allow partial
            if re.match(r'^[a-zA-Z0-9._%+-]*@?[a-zA-Z0-9.-]*$', input_str):
                return (QValidator.State.Intermediate, input_str, pos)

        return super().validate(input_str, pos)


class PasswordValidator(BaseValidator):
    """
    Validates password strength and format.

    Configurable requirements for length, character types, and complexity.
    """

    def __init__(
        self,
        parent=None,
        min_length: int = 8,
        max_length: int = 128,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = False,
        special_chars: str = "!@#$%^&*()_+-=[]{}|;':\",./<>?",
        forbidden_patterns: Optional[List[str]] = None,
        custom_rules: Optional[List[Callable[[str], Tuple[bool, str]]]] = None
    ):
        super().__init__(parent)
        self._min_length = min_length
        self._max_length = max_length
        self._require_uppercase = require_uppercase
        self._require_lowercase = require_lowercase
        self._require_digit = require_digit
        self._require_special = require_special
        self._special_chars = special_chars
        self._forbidden_patterns = forbidden_patterns or []
        self._custom_rules = custom_rules or []

    def validate_value(self, value: str) -> ValidationResult:
        """Validate password strength."""
        if not value:
            return ValidationResult.intermediate(value)

        errors = []

        # Check length
        if len(value) < self._min_length:
            errors.append(f"At least {self._min_length} characters required")

        if len(value) > self._max_length:
            errors.append(f"Maximum {self._max_length} characters allowed")

        # Check uppercase
        if self._require_uppercase and not re.search(r'[A-Z]', value):
            errors.append("At least one uppercase letter required")

        # Check lowercase
        if self._require_lowercase and not re.search(r'[a-z]', value):
            errors.append("At least one lowercase letter required")

        # Check digit
        if self._require_digit and not re.search(r'\d', value):
            errors.append("At least one number required")

        # Check special character
        if self._require_special:
            special_pattern = f'[{re.escape(self._special_chars)}]'
            if not re.search(special_pattern, value):
                errors.append("At least one special character required")

        # Check forbidden patterns
        for pattern in self._forbidden_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                errors.append(f"Password contains forbidden pattern")
                break

        # Run custom rules
        for rule in self._custom_rules:
            is_valid, message = rule(value)
            if not is_valid:
                errors.append(message)

        if errors:
            return ValidationResult.invalid(errors[0])

        return ValidationResult.valid(value)

    def validate(self, input_str: str, pos: int) -> Tuple[QValidator.State, str, int]:
        """Allow typing with intermediate states."""
        if not input_str:
            return (QValidator.State.Intermediate, input_str, pos)

        if len(input_str) < self._min_length:
            return (QValidator.State.Intermediate, input_str, pos)

        return super().validate(input_str, pos)

    def get_strength(self, password: str) -> Tuple[int, str]:
        """
        Calculate password strength score.

        Returns:
            Tuple of (score 0-100, strength label)
        """
        if not password:
            return (0, "Empty")

        score = 0

        # Length contribution (up to 30 points)
        length_score = min(len(password) * 2, 30)
        score += length_score

        # Character variety contribution (up to 40 points)
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(f'[{re.escape(self._special_chars)}]', password):
            score += 10

        # Entropy bonus (up to 30 points)
        unique_chars = len(set(password))
        entropy_score = min(unique_chars * 2, 30)
        score += entropy_score

        # Determine strength label
        if score < 30:
            label = "Weak"
        elif score < 50:
            label = "Fair"
        elif score < 70:
            label = "Good"
        elif score < 90:
            label = "Strong"
        else:
            label = "Very Strong"

        return (min(score, 100), label)

    def get_requirements_text(self) -> str:
        """Get a human-readable list of password requirements."""
        requirements = []

        requirements.append(f"At least {self._min_length} characters")

        if self._require_uppercase:
            requirements.append("At least one uppercase letter")

        if self._require_lowercase:
            requirements.append("At least one lowercase letter")

        if self._require_digit:
            requirements.append("At least one number")

        if self._require_special:
            requirements.append("At least one special character")

        return "\n".join(f"- {req}" for req in requirements)


class PhoneValidator(BaseValidator):
    """
    Validates phone numbers.

    Supports various international formats.
    """

    def __init__(
        self,
        parent=None,
        allow_international: bool = True,
        country_code: str = "US",
        require_country_code: bool = False
    ):
        super().__init__(parent)
        self._allow_international = allow_international
        self._country_code = country_code
        self._require_country_code = require_country_code

        # Basic patterns for common formats
        self._patterns = [
            r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$',  # US
            r'^\+?[0-9]{1,4}[-.\s]?[0-9]{6,14}$',  # International
        ]

    def validate_value(self, value: str) -> ValidationResult:
        """Validate phone number."""
        if not value.strip():
            return ValidationResult.intermediate(value)

        # Remove common formatting characters for validation
        cleaned = re.sub(r'[\s\-\.\(\)]', '', value.strip())

        # Check minimum digits
        digits_only = re.sub(r'\D', '', cleaned)
        if len(digits_only) < 10:
            return ValidationResult.invalid("Phone number too short")

        if len(digits_only) > 15:
            return ValidationResult.invalid("Phone number too long")

        # Check country code if required
        if self._require_country_code and not cleaned.startswith('+'):
            return ValidationResult.invalid("Country code required (e.g., +1)")

        # Validate format
        for pattern in self._patterns:
            if re.match(pattern, value.strip()):
                return ValidationResult.valid(value)

        return ValidationResult.invalid("Invalid phone number format")


class URLValidator(BaseValidator):
    """
    Validates URLs.

    Supports various URL formats with configurable schemes.
    """

    def __init__(
        self,
        parent=None,
        allowed_schemes: Optional[List[str]] = None,
        require_scheme: bool = True
    ):
        super().__init__(parent)
        self._allowed_schemes = allowed_schemes or ['http', 'https']
        self._require_scheme = require_scheme

        # URL pattern
        scheme_part = f"({'|'.join(self._allowed_schemes)})://" if require_scheme else f"(({'|'.join(self._allowed_schemes)})://)?"
        self._pattern = re.compile(
            f"^{scheme_part}"
            r"[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?"
            r"(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*"
            r"(:[0-9]+)?"
            r"(/[a-zA-Z0-9._~:/?#\[\]@!$&'()*+,;=-]*)?$",
            re.IGNORECASE
        )

    def validate_value(self, value: str) -> ValidationResult:
        """Validate URL."""
        if not value.strip():
            return ValidationResult.intermediate(value)

        url = value.strip()

        if not self._pattern.match(url):
            return ValidationResult.invalid("Please enter a valid URL")

        return ValidationResult.valid(value)


class CustomValidator(BaseValidator):
    """
    Wrapper for custom validation functions.

    Allows using any callable as a validator.
    """

    def __init__(
        self,
        parent=None,
        validation_func: Optional[Callable[[str], Tuple[bool, str]]] = None,
        error_message: str = "Invalid input"
    ):
        super().__init__(parent)
        self._validation_func = validation_func
        self._default_error = error_message

    def set_validation_func(self, func: Callable[[str], Tuple[bool, str]]):
        """Set the validation function."""
        self._validation_func = func

    def validate_value(self, value: str) -> ValidationResult:
        """Run custom validation function."""
        if not value:
            return ValidationResult.intermediate(value)

        if self._validation_func:
            is_valid, message = self._validation_func(value)
            if is_valid:
                return ValidationResult.valid(value)
            return ValidationResult.invalid(message or self._default_error)

        return ValidationResult.valid(value)


class CompositeValidator(BaseValidator):
    """
    Combines multiple validators.

    All validators must pass for the input to be valid.
    """

    def __init__(self, parent=None, validators: Optional[List[BaseValidator]] = None):
        super().__init__(parent)
        self._validators = validators or []

    def add_validator(self, validator: BaseValidator):
        """Add a validator to the composite."""
        self._validators.append(validator)

    def remove_validator(self, validator: BaseValidator):
        """Remove a validator from the composite."""
        if validator in self._validators:
            self._validators.remove(validator)

    def clear_validators(self):
        """Remove all validators."""
        self._validators.clear()

    def validate_value(self, value: str) -> ValidationResult:
        """Run all validators and return first failure or success."""
        for validator in self._validators:
            result = validator.validate_value(value)
            if not result.is_valid and not result.is_intermediate:
                return result

        return ValidationResult.valid(value)

    def validate(self, input_str: str, pos: int) -> Tuple[QValidator.State, str, int]:
        """Run all validators."""
        for validator in self._validators:
            state, text, new_pos = validator.validate(input_str, pos)
            if state == QValidator.State.Invalid:
                self._error_message = validator.error_message
                return (state, text, new_pos)

        return (QValidator.State.Acceptable, input_str, pos)


# Convenience factory functions
def create_required_validator(
    min_length: int = 1,
    trim_whitespace: bool = True
) -> RequiredValidator:
    """Create a required field validator."""
    return RequiredValidator(
        trim_whitespace=trim_whitespace,
        min_length=min_length
    )


def create_amount_validator(
    minimum: Optional[float] = 0,
    maximum: Optional[float] = None,
    decimal_places: int = 2,
    allow_negative: bool = False
) -> AmountValidator:
    """Create a monetary amount validator."""
    return AmountValidator(
        minimum=minimum,
        maximum=maximum,
        decimal_places=decimal_places,
        allow_negative=allow_negative
    )


def create_email_validator(strict: bool = False) -> EmailValidator:
    """Create an email validator."""
    return EmailValidator(strict=strict)


def create_password_validator(
    min_length: int = 8,
    require_special: bool = False
) -> PasswordValidator:
    """Create a password validator."""
    return PasswordValidator(
        min_length=min_length,
        require_special=require_special
    )


def create_date_validator(
    date_format: str = "%Y-%m-%d",
    allow_future: bool = True,
    allow_past: bool = True
) -> DateValidator:
    """Create a date validator."""
    return DateValidator(
        date_format=date_format,
        allow_future=allow_future,
        allow_past=allow_past
    )
