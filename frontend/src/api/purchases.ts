import api from './client';
import type { PurchaseOrder } from '../types';

export async function getPurchaseOrders(params?: any): Promise<PurchaseOrder[]> {
  return (await api.get('/purchase-orders', { params })).data;
}

export async function getPurchaseOrder(id: number): Promise<PurchaseOrder> {
  return (await api.get(`/purchase-orders/${id}`)).data;
}

export async function createPurchaseOrder(data: any): Promise<PurchaseOrder> {
  return (await api.post('/purchase-orders', data)).data;
}

export async function updatePurchaseOrder(id: number, data: any): Promise<PurchaseOrder> {
  return (await api.put(`/purchase-orders/${id}`, data)).data;
}

export async function receivePurchaseOrder(id: number): Promise<PurchaseOrder> {
  return (await api.post(`/purchase-orders/${id}/receive`)).data;
}

export async function cancelPurchaseOrder(id: number): Promise<PurchaseOrder> {
  return (await api.post(`/purchase-orders/${id}/cancel`)).data;
}

export async function deletePurchaseOrder(id: number): Promise<void> {
  await api.delete(`/purchase-orders/${id}`);
}

export async function getRestockSuggestions(warehouseId?: number): Promise<any[]> {
  const params = warehouseId ? { warehouse_id: warehouseId } : {};
  return (await api.get('/purchase-orders/restock-suggestions', { params })).data;
}

export async function getDemandAnalysis(warehouseId?: number, days: number = 90): Promise<any[]> {
  const params: Record<string, unknown> = { days };
  if (warehouseId) params.warehouse_id = warehouseId;
  return (await api.get('/purchase-orders/demand-analysis', { params })).data;
}

export async function getPriceOptimization(warehouseId?: number, days: number = 90): Promise<any[]> {
  const params: Record<string, unknown> = { days };
  if (warehouseId) params.warehouse_id = warehouseId;
  return (await api.get('/purchase-orders/price-optimization', { params })).data;
}
