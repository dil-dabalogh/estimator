import re
from typing import Optional
from models import TShirtSize


def calculate_tshirt_size(man_weeks: float) -> TShirtSize:
    if man_weeks < 2:
        return TShirtSize.XS
    elif man_weeks < 16:
        return TShirtSize.S
    elif man_weeks < 25:
        return TShirtSize.M
    elif man_weeks < 40:
        return TShirtSize.L
    elif man_weeks < 60:
        return TShirtSize.XL
    else:
        return TShirtSize.XXL


def normalize_duration_to_weeks(value: float, unit: str) -> float:
    """
    Convert duration from any time unit to manweeks.
    
    Conversion factors (approximate):
    - 1 day = 0.2 weeks (5 working days per week)
    - 1 week = 1 week
    - 1 month = 4.33 weeks (average)
    - 1 quarter = 13 weeks
    - 1 year = 52 weeks
    """
    unit_lower = unit.lower().strip()
    
    # Days
    if 'day' in unit_lower:
        return value * 0.2
    # Weeks (including manweeks, person-weeks, etc.)
    elif 'week' in unit_lower:
        return value
    # Months
    elif 'month' in unit_lower:
        return value * 4.33
    # Quarters
    elif 'quarter' in unit_lower or 'q' == unit_lower:
        return value * 13
    # Years
    elif 'year' in unit_lower or 'yr' in unit_lower:
        return value * 52
    else:
        # Default to weeks if unit is unclear
        return value


def parse_man_weeks_from_pert(pert_markdown: str) -> Optional[float]:
    """
    Extract total duration from PERT markdown and normalize to manweeks.
    
    Looks for patterns like:
    - "Total: 30 manweeks"
    - "Grand Total: 6 months"
    - "Overall: 45 weeks"
    - "Expected (E): 12 weeks"
    
    Supports time units: days, weeks, months, quarters, years
    """
    # Pattern to capture: number + time unit
    # Looks for "total", "overall", "sum", "grand", or "expected/e" followed by value and unit
    patterns = [
        r"(?:grand\s+)?(?:total|overall|sum)[\s:=]+(\d+(?:\.\d+)?)\s*(man[\s-]?weeks?|weeks?|months?|days?|quarters?|years?|yrs?)",
        r"(?:expected|e)[\s:=\(]+(\d+(?:\.\d+)?)\s*(man[\s-]?weeks?|weeks?|months?|days?|quarters?|years?|yrs?)",
        r"(\d+(?:\.\d+)?)\s*(man[\s-]?weeks?|weeks?|months?|days?|quarters?|years?|yrs?)\s*(?:total|overall|grand)",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, pert_markdown, re.IGNORECASE)
        if matches:
            try:
                # matches is a list of tuples: [(value, unit), ...]
                # Take the last match (most likely the grand total)
                value_str, unit = matches[-1]
                value = float(value_str)
                weeks = normalize_duration_to_weeks(value, unit)
                return weeks
            except (ValueError, IndexError):
                continue
    
    return None

