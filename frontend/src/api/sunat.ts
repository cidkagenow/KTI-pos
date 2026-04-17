import api from './client';
import type { SunatDocument, PaginatedResponse } from '../types';

export async function enviarFactura(saleId: number): Promise<SunatDocument> {
  const { data } = await api.post(`/sunat/facturas/${saleId}/enviar`);
  return data;
}

export async function enviarTodasFacturas(): Promise<{ enviadas: number; aceptadas: number; rechazadas: number; errores: number }> {
  const { data } = await api.post('/sunat/facturas/enviar-todas');
  return data;
}

export async function reenviarFactura(saleId: number): Promise<SunatDocument> {
  const { data } = await api.post(`/sunat/facturas/${saleId}/reenviar`);
  return data;
}

export async function enviarResumenBoletas(fecha: string): Promise<SunatDocument> {
  const { data } = await api.post('/sunat/resumen-boletas', { fecha });
  return data;
}

export async function getPendingBoletas(fecha: string): Promise<{ nuevas: number; anuladas: number; total: number }> {
  const { data } = await api.get('/sunat/resumen-boletas/pendientes', { params: { fecha } });
  return data;
}

export async function enviarBaja(saleId: number, motivo: string): Promise<SunatDocument> {
  const { data } = await api.post('/sunat/baja', { sale_id: saleId, motivo });
  return data;
}

export async function enviarBajaMasiva(): Promise<SunatDocument> {
  const { data } = await api.post('/sunat/baja-masiva');
  return data;
}

export interface PendingBaja {
  id: number;
  doc_type: string;
  series: string;
  doc_number: number;
  client_name: string | null;
  total: number;
  status: string;
}

export async function getPendingBajas(): Promise<{ total: number; data: PendingBaja[] }> {
  const { data } = await api.get('/sunat/bajas/pendientes');
  return data;
}

export async function checkTicketStatus(ticket: string): Promise<SunatDocument> {
  const { data } = await api.post(`/sunat/ticket/${ticket}/status`);
  return data;
}

interface SunatFilters {
  doc_category?: string;
  sunat_status?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  limit?: number;
}

export async function getSunatDocumentos(filters: SunatFilters): Promise<PaginatedResponse<SunatDocument>> {
  const { data } = await api.get('/sunat/documentos', { params: filters });
  return data;
}

export async function enviarNotaCredito(saleId: number): Promise<SunatDocument> {
  const { data } = await api.post(`/sunat/nota-credito/${saleId}/enviar`);
  return data;
}

export async function enviarTodasNotasCredito(): Promise<{ enviadas: number; aceptadas: number; rechazadas: number; errores: number }> {
  const { data } = await api.post('/sunat/nota-credito/enviar-todas');
  return data;
}

export interface ResumenBoleta {
  sale_id: number;
  doc_number: string;
  client_name: string;
  total: number;
  condition: string;
  status: string;
}

export async function getResumenBoletas(docId: number): Promise<{ boletas: ResumenBoleta[]; total: number }> {
  const { data } = await api.get(`/sunat/resumen/${docId}/boletas`);
  return data;
}

// ── Settings ─────────────────────────────────────────────────────

export interface SunatSettingsData {
  auto_send_enabled: boolean;
  block_before_10pm: boolean;
}

export async function getSunatSettings(): Promise<SunatSettingsData> {
  const { data } = await api.get('/sunat/settings');
  return data;
}

export async function updateSunatSettings(
  settings: Partial<SunatSettingsData> & { password: string },
): Promise<SunatSettingsData> {
  const { data } = await api.put('/sunat/settings', settings);
  return data;
}

export async function getSunatForSale(saleId: number): Promise<{
  sunat_status: string | null;
  sunat_description: string | null;
  sunat_pdf_url: string | null;
  sunat_xml_url: string | null;
  sunat_cdr_url: string | null;
}> {
  const { data } = await api.get(`/sunat/documentos/sale/${saleId}`);
  return data;
}
