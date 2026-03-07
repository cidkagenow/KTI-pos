import api from './client';
import type { SunatDocument, PaginatedResponse } from '../types';

export async function enviarFactura(saleId: number): Promise<SunatDocument> {
  const { data } = await api.post(`/sunat/facturas/${saleId}/enviar`);
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

export async function enviarBaja(saleId: number, motivo: string): Promise<SunatDocument> {
  const { data } = await api.post('/sunat/baja', { sale_id: saleId, motivo });
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
