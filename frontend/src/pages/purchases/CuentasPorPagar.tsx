import { useState } from 'react';
import {
  Table, Tag, Button, Card, Row, Col, Typography, message, Modal, Form,
  InputNumber, DatePicker, Select, Input, Statistic, Space, Popconfirm,
} from 'antd';
import {
  DollarOutlined, WarningOutlined, ClockCircleOutlined,
  PlusOutlined, DeleteOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getAccountsPayable, getAccountsPayableSummary, createPayment, deletePayment,
} from '../../api/accountsPayable';
import type { AccountPayable, SupplierPayment, PaymentCreateData } from '../../api/accountsPayable';
import { formatCurrency, formatDate } from '../../utils/format';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Title } = Typography;

const STATUS_COLORS: Record<string, string> = {
  PENDIENTE: 'blue',
  PARCIAL: 'gold',
  VENCIDO: 'red',
  PAGADO: 'green',
};

export default function CuentasPorPagar() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [payModalOpen, setPayModalOpen] = useState(false);
  const [payRecord, setPayRecord] = useState<AccountPayable | null>(null);
  const [form] = Form.useForm();

  const { data: payables, isLoading } = useQuery({
    queryKey: ['accounts-payable', statusFilter],
    queryFn: () => getAccountsPayable({ status_filter: statusFilter }),
  });

  const { data: summary } = useQuery({
    queryKey: ['accounts-payable-summary'],
    queryFn: getAccountsPayableSummary,
  });

  const payMut = useMutation({
    mutationFn: ({ poId, data }: { poId: number; data: PaymentCreateData }) =>
      createPayment(poId, data),
    onSuccess: () => {
      message.success('Pago registrado');
      setPayModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['accounts-payable'] });
      queryClient.invalidateQueries({ queryKey: ['accounts-payable-summary'] });
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.detail || 'Error al registrar pago');
    },
  });

  const deleteMut = useMutation({
    mutationFn: (paymentId: number) => deletePayment(paymentId),
    onSuccess: () => {
      message.success('Pago eliminado');
      queryClient.invalidateQueries({ queryKey: ['accounts-payable'] });
      queryClient.invalidateQueries({ queryKey: ['accounts-payable-summary'] });
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.detail || 'Error al eliminar pago');
    },
  });

  const handlePay = (record: AccountPayable) => {
    setPayRecord(record);
    form.setFieldsValue({
      amount: record.balance,
      payment_date: dayjs(),
      payment_method: 'EFECTIVO',
    });
    setPayModalOpen(true);
  };

  const handlePaySubmit = () => {
    form.validateFields().then((values) => {
      if (!payRecord) return;
      payMut.mutate({
        poId: payRecord.po_id,
        data: {
          amount: values.amount,
          payment_date: values.payment_date.format('YYYY-MM-DD'),
          payment_method: values.payment_method,
          reference: values.reference,
          notes: values.notes,
        },
      });
    });
  };

  const columns: ColumnsType<AccountPayable> = [
    {
      title: 'Proveedor',
      key: 'supplier',
      render: (_: unknown, r: AccountPayable) => (
        <div>
          <div style={{ fontWeight: 500 }}>{r.supplier_name}</div>
          {r.supplier_ruc && <div style={{ fontSize: 11, opacity: 0.6 }}>{r.supplier_ruc}</div>}
        </div>
      ),
      ellipsis: true,
    },
    {
      title: 'OC#',
      dataIndex: 'po_id',
      key: 'po_id',
      width: 60,
      align: 'center',
    },
    {
      title: 'Documento',
      key: 'doc',
      width: 150,
      render: (_: unknown, r: AccountPayable) =>
        r.doc_type && r.doc_number ? `${r.doc_type} ${r.doc_number}` : r.supplier_doc || '-',
    },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      width: 110,
      align: 'right',
      render: (val: number) => formatCurrency(val),
    },
    {
      title: 'Pagado',
      dataIndex: 'paid',
      key: 'paid',
      width: 110,
      align: 'right',
      render: (val: number) => <span style={{ color: val > 0 ? '#52c41a' : undefined }}>{formatCurrency(val)}</span>,
    },
    {
      title: 'Saldo',
      dataIndex: 'balance',
      key: 'balance',
      width: 110,
      align: 'right',
      render: (val: number, r: AccountPayable) => (
        <span style={{ fontWeight: 600, color: r.status === 'VENCIDO' ? '#ff4d4f' : undefined }}>
          {formatCurrency(val)}
        </span>
      ),
    },
    {
      title: 'Recepcion',
      key: 'received_at',
      width: 110,
      render: (_: unknown, r: AccountPayable) =>
        r.received_at ? formatDate(r.received_at.substring(0, 10)) : '-',
    },
    {
      title: 'Vencimiento',
      key: 'due_date',
      width: 110,
      render: (_: unknown, r: AccountPayable) => {
        if (!r.due_date) return '-';
        const color = r.status === 'VENCIDO' ? '#ff4d4f' : r.days_overdue < 0 ? undefined : undefined;
        return <span style={{ color }}>{formatDate(r.due_date)}</span>;
      },
    },
    {
      title: 'Estado',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (val: string, r: AccountPayable) => (
        <Tag color={STATUS_COLORS[val] || 'default'}>
          {val}{r.days_overdue > 0 ? ` (${r.days_overdue}d)` : ''}
        </Tag>
      ),
    },
    {
      title: '',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: AccountPayable) =>
        record.status !== 'PAGADO' && (
          <Button
            type="primary"
            size="small"
            icon={<PlusOutlined />}
            onClick={() => handlePay(record)}
          >
            Pagar
          </Button>
        ),
    },
  ];

  const paymentColumns: ColumnsType<SupplierPayment> = [
    { title: 'Fecha', dataIndex: 'payment_date', key: 'date', width: 100, render: (v: string) => formatDate(v) },
    { title: 'Monto', dataIndex: 'amount', key: 'amount', width: 100, align: 'right', render: (v: number) => formatCurrency(v) },
    { title: 'Metodo', dataIndex: 'payment_method', key: 'method', width: 110 },
    { title: 'Referencia', dataIndex: 'reference', key: 'ref', width: 120, ellipsis: true },
    { title: 'Nota', dataIndex: 'notes', key: 'notes', ellipsis: true },
    { title: 'Registrado por', dataIndex: 'creator_name', key: 'creator', width: 130 },
    {
      title: '',
      key: 'del',
      width: 50,
      render: (_: unknown, p: SupplierPayment) => (
        <Popconfirm title="Eliminar este pago?" onConfirm={() => deleteMut.mutate(p.id)} okText="Si" cancelText="No">
          <Button type="link" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>Cuentas por Pagar</Title>

      {/* Summary cards */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="Total Deuda"
              value={summary?.total_debt ?? 0}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="PEN"
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title={`Vencido (${summary?.count_overdue ?? 0})`}
              value={summary?.total_overdue ?? 0}
              precision={2}
              prefix={<WarningOutlined />}
              suffix="PEN"
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title={`Por Vencer 7d (${summary?.count_due_soon ?? 0})`}
              value={summary?.total_due_soon ?? 0}
              precision={2}
              prefix={<ClockCircleOutlined />}
              suffix="PEN"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col>
          <Select
            allowClear
            placeholder="Estado"
            style={{ width: 140 }}
            value={statusFilter}
            onChange={setStatusFilter}
            options={[
              { value: 'PENDIENTE', label: 'Pendiente' },
              { value: 'PARCIAL', label: 'Parcial' },
              { value: 'VENCIDO', label: 'Vencido' },
              { value: 'PAGADO', label: 'Pagado' },
            ]}
          />
        </Col>
      </Row>

      {/* Main table */}
      <Table
        columns={columns}
        dataSource={payables ?? []}
        rowKey="po_id"
        loading={isLoading}
        size="small"
        expandable={{
          expandedRowRender: (record) =>
            record.payments.length > 0 ? (
              <Table
                columns={paymentColumns}
                dataSource={record.payments}
                rowKey="id"
                size="small"
                pagination={false}
              />
            ) : (
              <span style={{ color: '#999' }}>Sin pagos registrados</span>
            ),
        }}
        pagination={{ pageSize: 20, showTotal: (t) => `Total: ${t}` }}
      />

      {/* Payment modal */}
      <Modal
        title={`Registrar Pago — OC #${payRecord?.po_id} (${payRecord?.supplier_name})`}
        open={payModalOpen}
        onCancel={() => setPayModalOpen(false)}
        onOk={handlePaySubmit}
        okText="Registrar Pago"
        confirmLoading={payMut.isPending}
      >
        {payRecord && (
          <div style={{ marginBottom: 16 }}>
            <p>Saldo pendiente: <strong>{formatCurrency(payRecord.balance)}</strong></p>
          </div>
        )}
        <Form form={form} layout="vertical">
          <Form.Item name="amount" label="Monto" rules={[{ required: true }]}>
            <InputNumber
              min={0.01}
              max={payRecord?.balance ?? 99999}
              step={0.01}
              style={{ width: '100%' }}
              prefix="S/"
            />
          </Form.Item>
          <Form.Item name="payment_date" label="Fecha" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
          </Form.Item>
          <Form.Item name="payment_method" label="Metodo" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'EFECTIVO', label: 'Efectivo' },
                { value: 'TRANSFERENCIA', label: 'Transferencia' },
                { value: 'YAPE', label: 'Yape' },
              ]}
            />
          </Form.Item>
          <Form.Item name="reference" label="Referencia (opcional)">
            <Input placeholder="Nro de operacion" />
          </Form.Item>
          <Form.Item name="notes" label="Nota (opcional)">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
