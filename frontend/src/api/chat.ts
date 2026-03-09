import api from './client';

export interface ChatMessage {
  id: number;
  role: 'user' | 'model';
  content: string;
  created_at: string;
}

interface ChatResponse {
  reply: string;
  messages: ChatMessage[];
}

export async function sendChatMessage(
  message: string,
  session_id?: string,
): Promise<ChatResponse> {
  const { data } = await api.post('/chat', { message, session_id });
  return data;
}

export async function getChatHistory(
  session_id?: string,
): Promise<ChatMessage[]> {
  const { data } = await api.get('/chat/history', {
    params: session_id ? { session_id } : undefined,
  });
  return data;
}

export async function clearChatHistory(): Promise<void> {
  await api.delete('/chat/history');
}

// ── Admin ───────────────────────────────────────────────────────────

export interface ChatSession {
  user_id: number;
  username: string;
  full_name: string;
  session_id: string | null;
  user_agent: string | null;
  message_count: number;
  last_message_at: string;
}

export interface ChatMessageAdmin {
  id: number;
  user_id: number;
  username: string;
  full_name: string;
  role: string;
  content: string;
  session_id: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface AdminHistoryFilters {
  user_id?: number;
  session_id?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  limit?: number;
}

export interface PaginatedAdminHistory {
  data: ChatMessageAdmin[];
  total: number;
  page: number;
  limit: number;
}

export async function getChatAdminSessions(): Promise<ChatSession[]> {
  const { data } = await api.get('/chat/admin/sessions');
  return data;
}

export async function getChatAdminHistory(
  filters: AdminHistoryFilters,
): Promise<PaginatedAdminHistory> {
  const { data } = await api.get('/chat/admin/history', { params: filters });
  return data;
}
