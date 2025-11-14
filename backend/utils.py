import re
from typing import Optional
from models import TShirtSize


def calculate_tshirt_size(man_weeks: float) -> TShirtSize:
    if man_weeks < 2:
        return TShirtSize.XS
    elif man_weeks < 4:
        return TShirtSize.S
    elif man_weeks < 8:
        return TShirtSize.M
    elif man_weeks <= 16:
        return TShirtSize.L
    elif man_weeks <= 26:
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

