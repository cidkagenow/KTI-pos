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

export function calcIGV(totalWithIGV: number): { base: number; igv: number; total: number } {
  const base = Math.round((totalWithIGV / 1.18) * 100) / 100;
  const igv = Math.round((totalWithIGV - base) * 100) / 100;
  return { base, igv, total: totalWithIGV };
}

export function calcLineTotal(quantity: number, unitPrice: number, discountPct: number): number {
  return Math.round(quantity * unitPrice * (1 - discountPct / 100) * 100) / 100;
}
