from decimal import Decimal, ROUND_HALF_UP
from app.config import settings

IGV_RATE = Decimal(str(settings.IGV_RATE))
IGV_FACTOR = Decimal("1") + IGV_RATE

def calc_igv(total_with_igv: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    """Given a total that includes IGV, return (base, igv, total)."""
    base = (total_with_igv / IGV_FACTOR).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    igv = total_with_igv - base
    return base, igv, total_with_igv

def calc_line_total(quantity: int, unit_price: Decimal, discount_pct: Decimal) -> Decimal:
    """Calculate line total: qty * price * (1 - discount/100)."""
    discount_factor = Decimal("1") - (discount_pct / Decimal("100"))
    return (Decimal(str(quantity)) * unit_price * discount_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
