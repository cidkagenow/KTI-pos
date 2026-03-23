import api from './client';
import type { InventoryItem, InventoryMovement } from '../types';

export async function getInventory(params?: any): Promise<InventoryItem[]> {
  const { data } = await api.get('/inventory', { params });
  return data;
}

export async function getAlerts(params?: any): Promise<InventoryItem[]> {
  const { data } = await api.get('/inventory/alerts', { params });
  return data;
}

export async function adjustStock(adjustData: any): Promise<any> {
  const { data } = await api.post('/inventory/adjust', adjustData);
  return data;
}

export async function transferStock(transferData: any): Promise<any> {
  const { data } = await api.post('/inventory/transfer', transferData);
  return data;
}

export async function getMovements(params?: any): Promise<InventoryMovement[]> {
  const { data } = await api.get('/inventory/movements', { params });
  return data;
}

export async function getKardex(params: {
  product_id: number;
  warehouse_id?: number;
  date_from?: string;
  date_to?: string;
}) {
  const { data } = await api.get('/inventory/kardex', { params });
  return data;
}
