"""Settings loading."""

import json
import os
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Settings:
    base_currency: str
    inputs: list
    fx_rates: dict


def load_settings(path):
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    base = os.path.dirname(os.path.abspath(path))
    return Settings(
        base_currency=raw["base_currency"],
        inputs=[os.path.normpath(os.path.join(base, p)) for p in raw["inputs"]],
        fx_rates={code: Decimal(rate) for code, rate in raw["fx_rates"].items()},
    )
