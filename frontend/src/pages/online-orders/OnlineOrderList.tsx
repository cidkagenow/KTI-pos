import { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Typography,
  Row,
  Col,
  Tabs,
  Modal,
  Input,
  Descriptions,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  GiftOutlined,
  ShoppingOutlined,
  CloseCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getOnlineOrders,
  confirmOrder,
  markReady,
  markPickedUp,
  cancelOrder,
} from '../../api/onlineOrders';
import { formatCurrency } from '../../utils/format';
import type { OnlineOrder } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

const STATUS_COLORS: Record<string, string> = {
  PENDIENTE: 'orange',
  CONFIRMADO: 'blue',
  LISTO: 'green',
  RECOGIDO: 'default',
  CANCELADO: 'red',
};

const PAYMENT_LABELS: Record<string, string> = {
  EN_TIENDA: 'En Tienda',
  YAPE: 'Yape',
  PLIN: 'Plin',
  TRANSFERENCIA: 'Transferencia',
};

export default function OnlineOrderList() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('PENDIENTE');
  const [detailOrder, setDetailOrder] = useState<OnlineOrder | null>(null);
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  const { data: orders, isLoading } = useQuery({
    queryKey: ['online-orders', activeTab],
    queryFn: () => getOnlineOrders(activeTab !== 'TODOS' ? activeTab : undefined),
    refetchInterval: 15_000,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['online-orders'] });

  const confirmMutation = useMutation({
    mutationFn: confirmOrder,
    onSuccess: () => { message.success('Pedido confirmado'); invalidate(); },
    onError: () => message.error('Error al confirmar'),
  });

  const readyMutation = useMutation({
    mutationFn: markReady,
    onSuccess: () => { message.success('Pedido listo para recoger'); invalidate(); },
    onError: () => message.error('Error al marcar como listo'),
  });

  const pickedUpMutation = useMutation({
    mutationFn: markPickedUp,
    onSuccess: () => { message.success('Pedido recogido'); invalidate(); },
    onError: () => message.error('Error al marcar como recogido'),
  });

  const cancelMutation = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) => cancelOrder(id, reason),
    onSuccess: () => {
      message.success('Pedido cancelado');
      setCancelModalOpen(false);
      setCancelReason('');
      setCancellingId(null);
      invalidate();
    },
    onError: () => message.error('Error al cancelar'),
  });

  const openCancel = (id: number) => {
    setCancellingId(id);
    setCancelReason('');
    setCancelModalOpen(true);
  };

  const handleCancel = () => {
    if (cancellingId && cancelReason.trim()) {
      cancelMutation.mutate({ id: cancellingId, reason: cancelReason.trim() });
    }
  };

  const columns: ColumnsType<OnlineOrder> = [
    { title: 'Codigo', dataIndex: 'order_code', key: 'order_code', width: 120 },
    { title: 'Cliente', dataIndex: 'customer_name', key: 'customer_name' },
    { title: 'Telefono', dataIndex: 'customer_phone', key: 'customer_phone', width: 120 },
    {
      title: 'Pago',
      dataIndex: 'payment_method',
      key: 'payment_method',
      width: 120,
      render: (v: string) => PAYMENT_LABELS[v] || v,
    },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      width: 100,
      align: 'right',
      render: (v: number) => formatCurrency(v),
    },
    {
      title: 'Estado',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (s: string) => <Tag color={STATUS_COLORS[s]}>{s}</Tag>,
    },
    {
      title: 'Fecha',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (v: string) => new Date(v).toLocaleString('es-PE'),
    },
    {
      title: 'Acciones',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: OnlineOrder) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => setDetailOrder(record)} />
          {record.status === 'PENDIENTE' && (
            <>
              <Button
                type="link"
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={() => confirmMutation.mutate(record.id)}
                loading={confirmMutation.isPending}
              >
                Confirmar
              </Button>
              <Button
                type="link"
                size="small"
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => openCancel(record.id)}
              >
                Cancelar
              </Button>
            </>
          )}
          {record.status === 'CONFIRMADO' && (
            <>
              <Button
                type="link"
                size="small"
                icon={<GiftOutlined />}
                onClick={() => readyMutation.mutate(record.id)}
                loading={readyMutation.isPending}
              >
                Listo
              </Button>
              <Button
                type="link"
                size="small"
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => openCancel(record.id)}
              >
                Cancelar
              </Button>
            </>
          )}
          {record.status === 'LISTO' && (
            <Button
              type="link"
              size="small"
              icon={<ShoppingOutlined />}
              onClick={() => pickedUpMutation.mutate(record.id)}
              loading={pickedUpMutation.isPending}
            >
              Recogido
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const tabs = [
    { key: 'PENDIENTE', label: 'Pendientes' },
    { key: 'CONFIRMADO', label: 'Confirmados' },
    { key: 'LISTO', label: 'Listos' },
    { key: 'RECOGIDO', label: 'Recogidos' },
    { key: 'CANCELADO', label: 'Cancelados' },
    { key: 'TODOS', label: 'Todos' },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>Pedidos Online</Title>
        </Col>
      </Row>

      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabs} />

      <Table
        columns={columns}
        dataSource={orders ?? []}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 20, showSizeChanger: true }}
      />

      {/* Detail Modal */}
      <Modal
        title={`Pedido ${detailOrder?.order_code}`}
        open={!!detailOrder}
        onCancel={() => setDetailOrder(null)}
        footer={null}
        width={600}
      >
        {detailOrder && (
          <>
            <Descriptions column={2} size="small" bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Cliente">{detailOrder.customer_name}</Descriptions.Item>
              <Descriptions.Item label="Telefono">{detailOrder.customer_phone}</Descriptions.Item>
              <Descriptions.Item label="Email">{detailOrder.customer_email || '-'}</Descriptions.Item>
              <Descriptions.Item label="Pago">{PAYMENT_LABELS[detailOrder.payment_method] || detailOrder.payment_method}</Descriptions.Item>
              {detailOrder.payment_reference && (
                <Descriptions.Item label="Ref. Pago" span={2}>{detailOrder.payment_reference}</Descriptions.Item>
              )}
              <Descriptions.Item label="Estado">
                <Tag color={STATUS_COLORS[detailOrder.status]}>{detailOrder.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Fecha">{new Date(detailOrder.created_at).toLocaleString('es-PE')}</Descriptions.Item>
              {detailOrder.cancel_reason && (
                <Descriptions.Item label="Motivo Cancelacion" span={2}>{detailOrder.cancel_reason}</Descriptions.Item>
              )}
            </Descriptions>
            <Table
              size="small"
              dataSource={detailOrder.items}
              rowKey="id"
              pagination={false}
              columns={[
                { title: 'Codigo', dataIndex: 'product_code', key: 'code', width: 80 },
                { title: 'Producto', dataIndex: 'product_name', key: 'name' },
                { title: 'Marca', dataIndex: 'brand_name', key: 'brand', width: 100, render: (v) => v || '-' },
                { title: 'Cant.', dataIndex: 'quantity', key: 'qty', width: 60, align: 'right' },
                { title: 'P.Unit', dataIndex: 'unit_price', key: 'price', width: 90, align: 'right', render: (v: number) => formatCurrency(v) },
                { title: 'Total', dataIndex: 'line_total', key: 'total', width: 90, align: 'right', render: (v: number) => formatCurrency(v) },
              ]}
              summary={() => (
                <Table.Summary>
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={4} />
                    <Table.Summary.Cell index={1} align="right"><strong>Subtotal</strong></Table.Summary.Cell>
                    <Table.Summary.Cell index={2} align="right">{formatCurrency(detailOrder.subtotal)}</Table.Summary.Cell>
                  </Table.Summary.Row>
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={4} />
                    <Table.Summary.Cell index={1} align="right"><strong>IGV</strong></Table.Summary.Cell>
                    <Table.Summary.Cell index={2} align="right">{formatCurrency(detailOrder.igv_amount)}</Table.Summary.Cell>
                  </Table.Summary.Row>
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={4} />
                    <Table.Summary.Cell index={1} align="right"><strong>Total</strong></Table.Summary.Cell>
                    <Table.Summary.Cell index={2} align="right"><strong>{formatCurrency(detailOrder.total)}</strong></Table.Summary.Cell>
                  </Table.Summary.Row>
                </Table.Summary>
              )}
            />
          </>
        )}
      </Modal>

      {/* Cancel Modal */}
      <Modal
        title="Cancelar Pedido"
        open={cancelModalOpen}
        onOk={handleCancel}
        onCancel={() => { setCancelModalOpen(false); setCancellingId(null); }}
        okText="Cancelar Pedido"
        okButtonProps={{ danger: true, disabled: !cancelReason.trim() }}
        confirmLoading={cancelMutation.isPending}
      >
        <Input.TextArea
          rows={3}
          placeholder="Motivo de cancelacion..."
          value={cancelReason}
          onChange={(e) => setCancelReason(e.target.value)}
        />
      </Modal>
    </div>
  );
}
