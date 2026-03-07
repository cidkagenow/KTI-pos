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

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  const { data } = await api.post('/chat', { message });
  return data;
}

export async function getChatHistory(): Promise<ChatMessage[]> {
  const { data } = await api.get('/chat/history');
  return data;
}

export async function clearChatHistory(): Promise<void> {
  await api.delete('/chat/history');
}
