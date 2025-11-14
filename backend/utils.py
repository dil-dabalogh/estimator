import re
from typing import Optional
from backend.models import TShirtSize


def calculate_tshirt_size(man_weeks: float) -> TShirtSize:
    if man_weeks < 1:
        return TShirtSize.XS
    elif man_weeks < 6:
        return TShirtSize.S
    elif man_weeks < 12:
        return TShirtSize.M
    elif man_weeks < 40:
        return TShirtSize.L
    elif man_weeks < 60:
        return TShirtSize.XL
    else:
        return TShirtSize.XXL


def parse_man_weeks_from_pert(pert_markdown: str) -> Optional[float]:
    patterns = [
        r"(?:total|overall|sum).*?(\d+(?:\.\d+)?)\s*(?:man[\s-]?weeks?|weeks?)",
        r"(?:expected|e).*?(\d+(?:\.\d+)?)\s*(?:man[\s-]?weeks?|weeks?)",
        r"(\d+(?:\.\d+)?)\s*(?:man[\s-]?weeks?|weeks?)\s*(?:total|overall)",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, pert_markdown, re.IGNORECASE)
        if matches:
            try:
                return float(matches[-1])
            except ValueError:
                continue
    
    return None

