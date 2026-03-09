import { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Select,
  DatePicker,
  Space,
  Spin,
  Empty,
  theme,
  Typography,
} from 'antd';
import dayjs from 'dayjs';
import { getUsers } from '../../api/users';
import {
  getChatAdminSessions,
  getChatAdminHistory,
  type ChatSession,
  type ChatMessageAdmin,
} from '../../api/chat';
import type { User } from '../../types';

const { RangePicker } = DatePicker;
const { Text } = Typography;

function parseDevice(ua: string | null): string {
  if (!ua) return 'Desconocido';
  const isMobile = /Mobile|Android|iPhone|iPad/i.test(ua);
  const type = isMobile ? 'Movil' : 'PC';
  if (ua.includes('Edg')) return `Edge ${type}`;
  if (ua.includes('Chrome') && !ua.includes('Edg')) return `Chrome ${type}`;
  if (ua.includes('Safari') && !ua.includes('Chrome')) return `Safari ${type}`;
  if (ua.includes('Firefox')) return `Firefox ${type}`;
  return type;
}

export default function ChatHistory() {
  const { token: t } = theme.useToken();
  const [users, setUsers] = useState<User[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [filterUserId, setFilterUserId] = useState<number | undefined>();
  const [filterDates, setFilterDates] = useState<
    [dayjs.Dayjs, dayjs.Dayjs] | null
  >(null);

  const [selectedSession, setSelectedSession] = useState<ChatSession | null>(
    null,
  );
  const [messages, setMessages] = useState<ChatMessageAdmin[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);

  useEffect(() => {
    Promise.all([getUsers(), getChatAdminSessions()]).then(([u, s]) => {
      setUsers(u);
      setSessions(s);
      setLoadingSessions(false);
    });
  }, []);

  const loadMessages = useCallback(
    async (session: ChatSession) => {
      setSelectedSession(session);
      setLoadingMessages(true);
      const res = await getChatAdminHistory({
        user_id: session.user_id,
        session_id: session.session_id ?? undefined,
        limit: 200,
      });
      setMessages(res.data);
      setLoadingMessages(false);
    },
    [],
  );

  const filteredSessions = sessions.filter((s) => {
    if (filterUserId && s.user_id !== filterUserId) return false;
    if (filterDates) {
      const last = dayjs(s.last_message_at);
      if (last.isBefore(filterDates[0], 'day') || last.isAfter(filterDates[1], 'day'))
        return false;
    }
    return true;
  });

  const columns = [
    {
      title: 'Usuario',
      dataIndex: 'full_name',
      key: 'full_name',
      width: 150,
    },
    {
      title: 'Dispositivo',
      key: 'device',
      width: 130,
      render: (_: unknown, r: ChatSession) => parseDevice(r.user_agent),
    },
    {
      title: 'Msgs',
      dataIndex: 'message_count',
      key: 'message_count',
      width: 70,
      align: 'center' as const,
    },
    {
      title: 'Ultimo mensaje',
      key: 'last_message_at',
      width: 150,
      render: (_: unknown, r: ChatSession) =>
        dayjs(r.last_message_at).format('DD/MM/YY HH:mm'),
    },
  ];

  return (
    <div>
      <h2 style={{ marginTop: 0, marginBottom: 16 }}>Historial de Chat</h2>

      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          allowClear
          placeholder="Filtrar por usuario"
          style={{ width: 200 }}
          value={filterUserId}
          onChange={(v) => setFilterUserId(v)}
          options={users.map((u) => ({
            value: u.id,
            label: u.full_name,
          }))}
        />
        <RangePicker
          format="DD/MM/YYYY"
          value={filterDates}
          onChange={(vals) =>
            setFilterDates(vals as [dayjs.Dayjs, dayjs.Dayjs] | null)
          }
        />
      </Space>

      <div style={{ display: 'flex', gap: 16, minHeight: 500 }}>
        {/* Left: Sessions list */}
        <Card
          style={{ flex: '0 0 520px', overflow: 'auto', maxHeight: 'calc(100vh - 250px)' }}
          styles={{ body: { padding: 0 } }}
        >
          <Table
            dataSource={filteredSessions}
            columns={columns}
            rowKey={(r) => `${r.user_id}-${r.session_id ?? 'null'}`}
            size="small"
            loading={loadingSessions}
            pagination={false}
            onRow={(record) => ({
              onClick: () => loadMessages(record),
              style: {
                cursor: 'pointer',
                background:
                  selectedSession &&
                  selectedSession.user_id === record.user_id &&
                  selectedSession.session_id === record.session_id
                    ? t.colorPrimaryBg
                    : undefined,
              },
            })}
          />
        </Card>

        {/* Right: Conversation */}
        <Card
          style={{
            flex: 1,
            overflow: 'auto',
            maxHeight: 'calc(100vh - 250px)',
          }}
          title={
            selectedSession
              ? `${selectedSession.full_name} — ${parseDevice(selectedSession.user_agent)}`
              : 'Selecciona una sesion'
          }
        >
          {!selectedSession && (
            <Empty description="Selecciona una sesion para ver la conversacion" />
          )}
          {loadingMessages && (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin />
            </div>
          )}
          {selectedSession && !loadingMessages && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
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
                      maxWidth: '75%',
                      padding: '8px 12px',
                      borderRadius:
                        msg.role === 'user'
                          ? '12px 12px 2px 12px'
                          : '12px 12px 12px 2px',
                      background:
                        msg.role === 'user'
                          ? t.colorPrimary
                          : t.colorFillSecondary,
                      color: msg.role === 'user' ? '#fff' : t.colorText,
                      fontSize: 13,
                      lineHeight: 1.5,
                      wordBreak: 'break-word',
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {msg.content}
                    <div
                      style={{
                        fontSize: 10,
                        opacity: 0.6,
                        marginTop: 4,
                        textAlign: 'right',
                      }}
                    >
                      {dayjs(msg.created_at).format('DD/MM HH:mm')}
                    </div>
                  </div>
                </div>
              ))}
              {messages.length === 0 && (
                <Text type="secondary">Sin mensajes en esta sesion.</Text>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
