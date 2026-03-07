import api from './client';
import type { User } from '../types';

export async function getUsers(): Promise<User[]> {
  return (await api.get('/users')).data;
}

export async function createUser(data: any): Promise<User> {
  return (await api.post('/users', data)).data;
}

export async function updateUser(id: number, data: any): Promise<User> {
  return (await api.put(`/users/${id}`, data)).data;
}

export async function changePassword(id: number, newPassword: string): Promise<void> {
  await api.put(`/users/${id}/password`, { new_password: newPassword });
}

export async function deleteUser(id: number): Promise<void> {
  await api.delete(`/users/${id}`);
}
