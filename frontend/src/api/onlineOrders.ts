import api from './client';
import type { OnlineOrder, OnlineOrderStats } from '../types';

export async function getOnlineOrders(status?: string): Promise<OnlineOrder[]> {
  const { data } = await api.get('/online-orders', { params: status ? { status } : undefined });
  return data;
}

export async function getOnlineOrder(id: number): Promise<OnlineOrder> {
  const { data } = await api.get(`/online-orders/${id}`);
  return data;
}

export async function getOnlineOrderStats(): Promise<OnlineOrderStats> {
  const { data } = await api.get('/online-orders/stats');
  return data;
}

export async function confirmOrder(id: number): Promise<OnlineOrder> {
  const { data } = await api.post(`/online-orders/${id}/confirm`);
  return data;
}

export async function markReady(id: number): Promise<OnlineOrder> {
  const { data } = await api.post(`/online-orders/${id}/ready`);
  return data;
}

export async function markPickedUp(id: number): Promise<OnlineOrder> {
  const { data } = await api.post(`/online-orders/${id}/picked-up`);
  return data;
}

export async function cancelOrder(id: number, reason: string): Promise<OnlineOrder> {
  const { data } = await api.post(`/online-orders/${id}/cancel`, { reason });
  return data;
}
