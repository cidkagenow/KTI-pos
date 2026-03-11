import api from './client';
import type { Trabajador, Asistencia } from '../types';

export async function getTrabajadores(): Promise<Trabajador[]> {
  return (await api.get('/trabajadores')).data;
}

export async function getActiveTrabajadores(): Promise<Trabajador[]> {
  return (await api.get('/trabajadores/active')).data;
}

export async function createTrabajador(data: {
  full_name: string;
  dni: string;
  phone?: string;
  cargo: string;
}): Promise<Trabajador> {
  return (await api.post('/trabajadores', data)).data;
}

export async function updateTrabajador(
  id: number,
  data: Partial<{
    full_name: string;
    dni: string;
    phone: string;
    cargo: string;
    is_active: boolean;
  }>,
): Promise<Trabajador> {
  return (await api.put(`/trabajadores/${id}`, data)).data;
}

export async function deleteTrabajador(id: number): Promise<void> {
  await api.delete(`/trabajadores/${id}`);
}

export async function getAsistencia(fecha: string): Promise<Asistencia[]> {
  return (await api.get('/trabajadores/asistencia', { params: { fecha } })).data;
}

export async function bulkMarkAsistencia(data: {
  date: string;
  items: {
    trabajador_id: number;
    check_in_time?: string | null;
    check_out_time?: string | null;
    status: string;
    notes?: string | null;
  }[];
}): Promise<Asistencia[]> {
  return (await api.post('/trabajadores/asistencia/bulk', data)).data;
}

export async function updateAsistencia(
  id: number,
  data: Partial<{
    check_in_time: string;
    check_out_time: string;
    status: string;
    notes: string;
  }>,
): Promise<Asistencia> {
  return (await api.put(`/trabajadores/asistencia/${id}`, data)).data;
}
