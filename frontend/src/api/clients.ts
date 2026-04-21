import api from './client';
import type { Client } from '../types';

export async function getClients(params?: any): Promise<Client[]> {
  const { data } = await api.get('/clients', { params });
  return data;
}

export async function getClient(id: number): Promise<Client> {
  const { data } = await api.get(`/clients/${id}`);
  return data;
}

export async function createClient(clientData: any): Promise<Client> {
  const { data } = await api.post('/clients', clientData);
  return data;
}

export async function updateClient(id: number, clientData: any): Promise<Client> {
  const { data } = await api.put(`/clients/${id}`, clientData);
  return data;
}

export async function deleteClient(id: number): Promise<void> {
  await api.delete(`/clients/${id}`);
}

export async function searchClients(q: string): Promise<Client[]> {
  const { data } = await api.get('/clients/search', { params: { q } });
  return data;
}

export async function lookupRUC(ruc: string): Promise<{ business_name: string; address: string; departamento?: string; provincia?: string; distrito?: string }> {
  const { data } = await api.get(`/lookup/ruc/${ruc}`);
  return data;
}

export async function lookupDNI(dni: string): Promise<{ business_name: string }> {
  const { data } = await api.get(`/lookup/dni/${dni}`);
  return data;
}
