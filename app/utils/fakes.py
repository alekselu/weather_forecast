import numpy as np
from datetime import date


def fake_temperature_by_date(date: date):
    values = dict(enumerate(-10.0 * np.cos(np.pi * np.arange(12) / 6)))
    return values[date.month]
