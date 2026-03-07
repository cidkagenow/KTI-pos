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

export async function deletePurchaseOrder(id: number): Promise<void> {
  await api.delete(`/purchase-orders/${id}`);
}
