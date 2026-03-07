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
