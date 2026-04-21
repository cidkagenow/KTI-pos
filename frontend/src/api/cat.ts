import api from './client';

export interface PlacaLookup {
  found: boolean;
  placa: string;
  año: number | null;
  marca: string;
  modelo: string;
  asientos: number | null;
  serie: string;
  categoria: string;
  clase: string;
  uso: string;
  precio: number;
  ap_extra: number;
  precio_total: number;
  vigencia_dias: number;
  vigente: boolean;
  n_tecnica: number | null;
  error: string | null;
}

export interface DniLookup {
  found: boolean;
  ap_paterno: string;
  ap_materno: string;
  nombre: string;
  full_name: string;
  telefono: string;
  direccion: string;
  error: string | null;
}

export interface CatSale {
  id: number;
  certificate_number: string | null;
  placa: string;
  marca: string | null;
  modelo: string | null;
  año: number | null;
  serie_vehiculo: string | null;
  asientos: number | null;
  categoria: string | null;
  clase: string | null;
  uso: string | null;
  customer_name: string;
  customer_dni: string | null;
  customer_phone: string | null;
  customer_address: string | null;
  fecha_desde: string | null;
  fecha_hasta: string | null;
  precio: number | null;
  ap_extra: number | null;
  total: number | null;
  status: string;
  sold_by: number | null;
  notes: string | null;
  created_at: string;
}

export interface Renewal {
  id: number;
  placa: string;
  customer_name: string;
  customer_phone: string | null;
  fecha_hasta: string;
  days_left: number;
}

export async function lookupPlaca(placa: string): Promise<PlacaLookup> {
  return (await api.get('/cat/lookup-placa', { params: { placa } })).data;
}

export async function lookupDni(dni: string): Promise<DniLookup> {
  return (await api.get('/cat/lookup-dni', { params: { dni } })).data;
}

export async function createCatSale(data: any): Promise<CatSale> {
  return (await api.post('/cat', data)).data;
}

export async function listCatSales(): Promise<CatSale[]> {
  return (await api.get('/cat')).data;
}

export async function getRenewals(days: number = 30): Promise<Renewal[]> {
  return (await api.get('/cat/renewals', { params: { days } })).data;
}
