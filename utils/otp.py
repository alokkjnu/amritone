"""OTP generation helpers."""

from __future__ import annotations
import random
import string
from config.settings import settings


def generate_otp(length: int = settings.OTP_LENGTH) -> str:
    """Return a numeric OTP of *length* digits."""
    return "".join(random.choices(string.digits, k=length))
