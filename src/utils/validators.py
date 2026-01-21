import re
from datetime import datetime
from typing import Any, List, Optional, Tuple


class ValidationError(Exception):
    """Custom exception for validation errors."""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class Validator:
    """
    Validator class for input validation.

    Provides static methods for validating common input types.
    Demonstrates Part 5: Best Practices concepts.
    """

    @staticmethod
    def required(value: Any, field_name: str) -> Any:
        """Validate that a value is not None or empty."""
        if value is None:
            raise ValidationError(field_name, "This field is required")

        if isinstance(value, str) and not value.strip():
            raise ValidationError(field_name, "This field cannot be empty")

        return value

    @staticmethod
    def string_length(
        value: str, field_name: str, min_length: int = 0, max_length: int = 1000
    ) -> str:
        """Validate string length constraints."""
        if not isinstance(value, str):
            raise ValidationError(field_name, "Must be a string")

        length = len(value)

        if length < min_length:
            raise ValidationError(
                field_name, f"Must be at least {min_length} characters"
            )

        if length > max_length:
            raise ValidationError(
                field_name, f"Must be at most {max_length} characters"
            )

        return value

    @staticmethod
    def email(value: str, field_name: str = "email") -> str:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(pattern, value):
            raise ValidationError(field_name, "Invalid email format")

        return value.lower()

    @staticmethod
    def positive_number(value: Any, field_name: str, allow_zero: bool = True) -> float:
        """Validate that a value is a positive number."""
        try:
            num = float(value)
        except (ValueError, TypeError):
            raise ValidationError(field_name, "Must be a number")

        if allow_zero:
            if num < 0:
                raise ValidationError(field_name, "Must be zero or positive")
        else:
            if num <= 0:
                raise ValidationError(field_name, "Must be positive")

        return num

    @staticmethod
    def in_list(value: Any, allowed_values: List[Any], field_name: str) -> Any:
        """Validate that a value is in a list of allowed values."""
        if value not in allowed_values:
            allowed_str = ", ".join(str(v) for v in allowed_values)
            raise ValidationError(field_name, f"Must be one of: {allowed_str}")

        return value

    @staticmethod
    def date_string(value: str, field_name: str, format: str = "%Y-%m-%d") -> datetime:
        """Validate and parse a date string."""
        try:
            return datetime.strptime(value, format)
        except ValueError:
            raise ValidationError(
                field_name, f"Invalid date format. Expected: {format}"
            )

    @staticmethod
    def list_of_strings(value: Any, field_name: str, max_items: int = 100) -> List[str]:
        """Validate a list of strings."""
        if not isinstance(value, list):
            raise ValidationError(field_name, "Must be a list")

        if len(value) > max_items:
            raise ValidationError(
                field_name, f"Cannot have more than {max_items} items"
            )

        result = []
        for i, item in enumerate(value):
            if not isinstance(item, str):
                raise ValidationError(f"{field_name}[{i}]", "All items must be strings")
            result.append(item.strip())

        return result

    @classmethod
    def validate_experiment_data(cls, data: dict) -> Tuple[bool, Optional[str]]:
        """Validate experiment creation/update data."""
        try:
            cls.required(data.get("name"), "name")
            cls.string_length(data["name"], "name", min_length=1, max_length=200)

            if "description" in data:
                cls.string_length(data["description"], "description", max_length=5000)

            if "status" in data:
                cls.in_list(
                    data["status"],
                    ["planned", "running", "completed", "failed", "paused"],
                    "status",
                )

            if "tags" in data:
                cls.list_of_strings(data["tags"], "tags", max_items=20)

            return True, None

        except ValidationError as e:
            return False, str(e)
