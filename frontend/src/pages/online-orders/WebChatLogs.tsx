import { useState } from 'react';
import { Table, Typography, Tag, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import api from '../../api/client';
import { formatDateTime } from '../../utils/format';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

interface ChatLog {
  id: number;
  session_id: string;
  role: string;
  message: string;
  created_at: string;
}

async function fetchChatLogs(): Promise<ChatLog[]> {
  const { data } = await api.get('/online-orders/chat-logs');
  return data;
}

export default function WebChatLogs() {
  const [limit] = useState(200);
  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ['web-chat-logs', limit],
    queryFn: fetchChatLogs,
  });

  const columns: ColumnsType<ChatLog> = [
    {
      title: 'Fecha',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (val: string) => val ? formatDateTime(val) : '-',
    },
    {
      title: 'Sesion',
      dataIndex: 'session_id',
      key: 'session_id',
      width: 90,
      render: (val: string) => <Tag>{val}</Tag>,
    },
    {
      title: 'Rol',
      dataIndex: 'role',
      key: 'role',
      width: 80,
      render: (val: string) => (
        <Tag color={val === 'user' ? 'blue' : 'green'}>
          {val === 'user' ? 'Cliente' : 'Bot'}
        </Tag>
      ),
    },
    {
      title: 'Mensaje',
      dataIndex: 'message',
      key: 'message',
      render: (val: string) => (
        <div style={{ whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto', fontSize: 13 }}>
          {val}
        </div>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>Chat Web - Historial</Title>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>Actualizar</Button>
      </div>
      <Table
        columns={columns}
        dataSource={logs ?? []}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 50, showSizeChanger: true }}
        scroll={{ x: 800 }}
      />
    </div>
  );
}
