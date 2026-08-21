"""Order number generation."""

from __future__ import annotations
import time
import random
import string


def generate_order_number() -> str:
    """Return a unique order number like AP-20240801-A4B2."""
    from datetime import datetime
    date_part = datetime.utcnow().strftime("%Y%m%d")
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"AP-{date_part}-{rand_part}"
