export function formatCurrency(value: number): string {
  return `S/ ${value.toFixed(2)}`;
}

export function formatDate(dateStr: string): string {
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
