"""Shared Jinja2Templates instance — import this everywhere instead of constructing a new one."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from vayuapi import Jinja2Templates

templates = Jinja2Templates(directory="templates")

templates.env.filters["tojson"] = lambda v: json.dumps(v, default=str)
templates.env.filters["now_year"] = lambda _v=None: datetime.now(timezone.utc).year
