export function formatCurrency(value: number): string {
  return `S/ ${value.toFixed(2)}`;
}

export function formatDate(dateStr: string): string {
  // Date-only strings (YYYY-MM-DD) are parsed as UTC by JS, causing
  // day shift in negative UTC offsets (e.g. Peru UTC-5). Parse as local instead.
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    const [y, m, d] = dateStr.split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString('es-PE');
  }
  return new Date(dateStr).toLocaleDateString('es-PE');
}

export function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('es-PE');
}

/** Round to 2 decimal places (avoids floating point accumulation errors) */
export function round2(n: number): number {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

export function calcIGV(totalWithIGV: number): { base: number; igv: number; total: number } {
  const total = round2(totalWithIGV);
  const base = round2(total / 1.18);
  const igv = round2(total - base);
  return { base, igv, total };
}

export function calcLineTotal(quantity: number, unitPrice: number, discountPct: number): number {
  return round2(quantity * unitPrice * (1 - discountPct / 100));
}
