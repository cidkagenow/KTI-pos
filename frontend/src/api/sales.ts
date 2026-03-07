import api from './client';
import type { Sale, PaginatedResponse } from '../types';

interface SaleFilters {
  page?: number;
  limit?: number;
  date_from?: string;
  date_to?: string;
  doc_type?: string;
  series?: string;
  client_id?: number;
  warehouse_id?: number;
  seller_id?: number;
  status?: string;
}

export async function getSales(filters: SaleFilters): Promise<PaginatedResponse<Sale>> {
  const { data } = await api.get('/sales', { params: filters });
  return data;
}

export async function getSale(id: number): Promise<Sale> {
  const { data } = await api.get(`/sales/${id}`);
  return data;
}

export async function createSale(saleData: any): Promise<Sale> {
  const { data } = await api.post('/sales', saleData);
  return data;
}

export async function updateSale(id: number, saleData: any): Promise<Sale> {
  const { data } = await api.put(`/sales/${id}`, saleData);
  return data;
}

export async function facturarSale(id: number): Promise<Sale> {
  const { data } = await api.post(`/sales/${id}/facturar`);
  return data;
}

export async function anularSale(id: number, reason: string): Promise<Sale> {
  const { data } = await api.post(`/sales/${id}/anular`, { reason });
  return data;
}

export async function deleteSale(id: number): Promise<void> {
  await api.delete(`/sales/${id}`);
}
