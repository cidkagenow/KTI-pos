import api from './client';
import type { DashboardStats, SalesByPeriod, TopProduct, ProfitReport } from '../types';

export async function getDashboard(): Promise<DashboardStats> {
  const { data } = await api.get('/reports/dashboard');
  return data;
}

export async function getSalesByPeriod(
  fromDate: string,
  toDate: string,
  groupBy: string,
): Promise<SalesByPeriod[]> {
  const { data } = await api.get('/reports/sales-by-period', {
    params: { from_date: fromDate, to_date: toDate, group_by: groupBy },
  });
  return data;
}

export async function getTopProducts(
  fromDate: string,
  toDate: string,
  limit: number,
): Promise<TopProduct[]> {
  const { data } = await api.get('/reports/top-products', {
    params: { from_date: fromDate, to_date: toDate, limit },
  });
  return data;
}

export async function getProfitReport(
  fromDate: string,
  toDate: string,
): Promise<ProfitReport[]> {
  const { data } = await api.get('/reports/profit-report', {
    params: { from_date: fromDate, to_date: toDate },
  });
  return data;
}

// ─── Registro de Ventas (monthly export for accountant) ───

export async function getRegistroVentasConfig(): Promise<{ accountant_email: string }> {
  const { data } = await api.get('/reports/registro-ventas/config');
  return data;
}

export async function downloadRegistroVentas(year: number, month: number): Promise<void> {
  const res = await api.get('/reports/registro-ventas/download', {
    params: { year, month },
    responseType: 'blob',
  });
  // Extract filename from Content-Disposition or build one
  const cd = (res.headers['content-disposition'] as string | undefined) ?? '';
  const match = cd.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] ?? `Registro_Ventas_${year}${String(month).padStart(2, '0')}.xlsx`;

  const blob = new Blob([res.data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function sendRegistroVentas(
  year: number,
  month: number,
  email?: string,
): Promise<{ ok: boolean; email: string; filename: string }> {
  const { data } = await api.post('/reports/registro-ventas/send-email', {
    year,
    month,
    email,
  });
  return data;
}
