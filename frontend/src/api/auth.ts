import api from './client';
import type { LoginResponse } from '../types';

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', { username, password });
  return data;
}

export async function getMe() {
  const { data } = await api.get('/auth/me');
  return data;
}
