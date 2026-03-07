import { useState, useRef, useEffect, useCallback } from 'react';
import { Button, Input, Spin, theme, Tooltip } from 'antd';
import {
  MessageOutlined,
  SendOutlined,
  DeleteOutlined,
  MinusOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import {
  sendChatMessage,
  getChatHistory,
  clearChatHistory,
  type ChatMessage,
} from '../../api/chat';

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { token: t } = theme.useToken();

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (open && !historyLoaded) {
      getChatHistory()
        .then((msgs) => {
          setMessages(msgs);
          setHistoryLoaded(true);
        })
        .catch(() => setHistoryLoaded(true));
    }
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open, historyLoaded]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput('');
    // Optimistic: add user message
    const tempMsg: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempMsg]);
    setLoading(true);

    try {
      const res = await sendChatMessage(text);
      setMessages(res.messages);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'model',
          content: 'Error al comunicarse con el asistente. Intenta de nuevo.',
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    try {
      await clearChatHistory();
      setMessages([]);
    } catch {
      // ignore
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Simple markdown-like formatting: **bold**, \n → <br>
  const formatContent = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      // Split by newlines
      const lines = part.split('\n');
      return lines.map((line, j) => (
        <span key={`${i}-${j}`}>
          {j > 0 && <br />}
          {line}
        </span>
      ));
    });
  };

  return (
    <>
      {/* Floating button */}
      {!open && (
        <Button
          type="primary"
          shape="circle"
          size="large"
          icon={<MessageOutlined />}
          onClick={() => setOpen(true)}
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            width: 52,
            height: 52,
            zIndex: 1000,
            boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 22,
          }}
        />
      )}

      {/* Chat window */}
      {open && (
        <div
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            width: 380,
            height: 520,
            zIndex: 1000,
            borderRadius: 12,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            background: t.colorBgContainer,
            border: `1px solid ${t.colorBorderSecondary}`,
            boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: '12px 16px',
              background: t.colorPrimary,
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexShrink: 0,
            }}
          >
            <span style={{ fontWeight: 600, fontSize: 14 }}>
              Asistente KTI
            </span>
            <div style={{ display: 'flex', gap: 4 }}>
              <Tooltip title="Limpiar historial">
                <Button
                  type="text"
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={handleClear}
                  style={{ color: '#fff' }}
                />
              </Tooltip>
              <Tooltip title="Minimizar">
                <Button
                  type="text"
                  size="small"
                  icon={<MinusOutlined />}
                  onClick={() => setOpen(false)}
                  style={{ color: '#fff' }}
                />
              </Tooltip>
              <Tooltip title="Cerrar">
                <Button
                  type="text"
                  size="small"
                  icon={<CloseOutlined />}
                  onClick={() => {
                    setOpen(false);
                  }}
                  style={{ color: '#fff' }}
                />
              </Tooltip>
            </div>
          </div>

          {/* Messages */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '12px 16px',
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            {messages.length === 0 && !loading && (
              <div
                style={{
                  textAlign: 'center',
                  color: t.colorTextSecondary,
                  marginTop: 60,
                  fontSize: 13,
                }}
              >
                Hola! Soy el asistente de KTI POS.
                <br />
                Preguntame sobre productos, ventas, clientes o como usar el
                sistema.
              </div>
            )}
            {messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  justifyContent:
                    msg.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    maxWidth: '80%',
                    padding: '8px 12px',
                    borderRadius:
                      msg.role === 'user'
                        ? '12px 12px 2px 12px'
                        : '12px 12px 12px 2px',
                    background:
                      msg.role === 'user'
                        ? t.colorPrimary
                        : t.colorFillSecondary,
                    color:
                      msg.role === 'user' ? '#fff' : t.colorText,
                    fontSize: 13,
                    lineHeight: 1.5,
                    wordBreak: 'break-word',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {formatContent(msg.content)}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                <div
                  style={{
                    padding: '8px 16px',
                    borderRadius: '12px 12px 12px 2px',
                    background: t.colorFillSecondary,
                  }}
                >
                  <Spin size="small" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div
            style={{
              padding: '8px 12px',
              borderTop: `1px solid ${t.colorBorderSecondary}`,
              display: 'flex',
              gap: 8,
              flexShrink: 0,
            }}
          >
            <Input
              ref={inputRef as any}
              placeholder="Escribe tu pregunta..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              style={{ flex: 1 }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              disabled={!input.trim() || loading}
            />
          </div>
        </div>
      )}
    </>
  );
}
