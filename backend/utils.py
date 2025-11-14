import re
from typing import Optional, Dict
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


# Conversion factors: time unit -> manweeks multiplier
DURATION_TO_WEEKS: Dict[str, float] = {
    'day': 0.2,      # 5 working days per week
    'week': 1.0,     # base unit
    'month': 4.33,   # average month
    'quarter': 13.0, # 13 weeks per quarter
    'year': 52.0,    # 52 weeks per year
    'yr': 52.0,      # abbreviation
}


def normalize_duration_to_weeks(value: float, unit: str) -> float:
    """
    Convert duration from any time unit to manweeks using standardized conversion factors.
    
    Args:
        value: Numeric duration value
        unit: Time unit (e.g., 'days', 'weeks', 'months', 'quarters', 'years')
    
    Returns:
        Duration in manweeks
    """
    unit_normalized = unit.lower().strip().rstrip('s')  # normalize plurals
    
    # Check each known unit pattern
    for unit_key, multiplier in DURATION_TO_WEEKS.items():
        if unit_key in unit_normalized or unit_normalized == unit_key:
            return value * multiplier
    
    # Default to weeks if unit is unrecognized
    return value


def parse_man_weeks_from_pert(pert_markdown: str) -> Optional[float]:
    """
    Extract total duration from PERT markdown and normalize to manweeks.
    
    Searches for duration patterns near total/summary keywords:
    - "Total: 30 manweeks"
    - "Grand Total: 6 months" 
    - "Expected (E): 12 weeks"
    
    Returns:
        Duration in manweeks, or None if not found
    """
    # Build unit pattern dynamically from known units
    unit_pattern = r'(?:man[\s-]?)?(?:' + '|'.join(DURATION_TO_WEEKS.keys()) + r')s?'
    
    # Keywords that indicate a total/summary line
    total_keywords = r'(?:grand\s+)?(?:total|overall|sum|expected|e)'
    
    # Comprehensive pattern: keyword + optional separator + number + unit
    pattern = rf'{total_keywords}[\s:=\(]*(\d+(?:\.\d+)?)\s*({unit_pattern})'
    
    # Find all matches
    matches = re.findall(pattern, pert_markdown, re.IGNORECASE)
    
    if matches:
        try:
            # Take the last match (most likely the grand total)
            value_str, unit = matches[-1]
            value = float(value_str)
            return normalize_duration_to_weeks(value, unit)
        except (ValueError, IndexError):
            pass
    
    return None

