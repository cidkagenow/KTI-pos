import { useState } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Input,
  Select,
  DatePicker,
  Checkbox,
  Row,
  Col,
  Modal,
  Typography,
  message,
} from 'antd';
import {
  PlusOutlined,
  EyeOutlined,
  EditOutlined,
  StopOutlined,
  DeleteOutlined,
  PrinterOutlined,
  CloudOutlined,
  RollbackOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getSales, anularSale, deleteSale, convertirSale, facturarSale } from '../../api/sales';
import { getWarehouses, getDocumentSeries } from '../../api/catalogs';
import { getUsers } from '../../api/users';
import { formatCurrency, formatDate } from '../../utils/format';
import { useAuth } from '../../contexts/AuthContext';
import type { Sale } from '../../types';
import type { ColumnsType } from 'antd/es/table';
import useEnterNavigation from '../../hooks/useEnterNavigation';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Title } = Typography;

const STATUS_COLORS: Record<string, string> = {
  PREVENTA: 'blue',
  FACTURADO: 'green',
  ANULADO: 'red',
  ELIMINADO: 'default',
};

export default function SalesList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAdmin } = useAuth();

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);
  const [docType, setDocType] = useState<string | undefined>(undefined);
  const [warehouseId, setWarehouseId] = useState<number | undefined>(undefined);
  const [sellerId, setSellerId] = useState<number | undefined>(undefined);
  const [statusFilters, setStatusFilters] = useState<string[]>([]);
  const [voidReason, setVoidReason] = useState('');
  const [convertirModalOpen, setConvertirModalOpen] = useState(false);
  const [convertirSaleRecord, setConvertirSaleRecord] = useState<Sale | null>(null);
  const [convertirTargetType, setConvertirTargetType] = useState<string>('BOLETA');
  const [convertirTargetSeries, setConvertirTargetSeries] = useState<string>('');
  const enterNavRef = useEnterNavigation();

  const filters = {
    page,
    limit: pageSize,
    date_from: dateRange?.[0]?.format('YYYY-MM-DD'),
    date_to: dateRange?.[1]?.format('YYYY-MM-DD'),
    doc_type: docType,
    warehouse_id: warehouseId,
    seller_id: sellerId,
    status: statusFilters.length === 1 ? statusFilters[0] : undefined,
  };

  const { data, isLoading } = useQuery({
    queryKey: ['sales', filters],
    queryFn: () => getSales(filters),
  });

  const { data: warehouses } = useQuery({
    queryKey: ['warehouses'],
    queryFn: getWarehouses,
  });

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: getUsers,
  });

  const { data: docSeries } = useQuery({
    queryKey: ['doc-series'],
    queryFn: getDocumentSeries,
  });

  const anularMutation = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) => anularSale(id, reason),
    onSuccess: () => {
      message.success('Venta anulada correctamente');
      queryClient.invalidateQueries({ queryKey: ['sales'] });
    },
    onError: () => message.error('Error al anular la venta'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteSale(id),
    onSuccess: () => {
      message.success('Venta eliminada correctamente');
      queryClient.invalidateQueries({ queryKey: ['sales'] });
    },
    onError: () => message.error('Error al eliminar la venta'),
  });

  const convertirMutation = useMutation({
    mutationFn: ({ id, targetDocType, targetSeries }: { id: number; targetDocType: string; targetSeries: string }) =>
      convertirSale(id, targetDocType, targetSeries),
    onSuccess: () => {
      message.success('Nota de Venta convertida correctamente');
      queryClient.invalidateQueries({ queryKey: ['sales'] });
      setConvertirModalOpen(false);
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail;
      message.error(detail || 'Error al convertir la nota de venta');
    },
  });

  const handleConvertir = (sale: Sale) => {
    setConvertirSaleRecord(sale);
    setConvertirTargetType('BOLETA');
    setConvertirTargetSeries('');
    setConvertirModalOpen(true);
  };

  const handleVoid = (sale: Sale) => {
    setVoidReason('');
    Modal.confirm({
      title: 'Anular Venta',
      content: (
        <div>
          <p>Esta seguro de anular la venta {sale.doc_number !== null ? `${sale.doc_type}/${sale.series}-${String(sale.doc_number).padStart(7, '0')}` : `PRE-${sale.id}`}?</p>
          <Input.TextArea
            placeholder="Motivo de anulacion"
            onChange={(e) => setVoidReason(e.target.value)}
            rows={3}
          />
        </div>
      ),
      okText: 'Anular',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: () => anularMutation.mutateAsync({ id: sale.id, reason: voidReason }),
    });
  };

  const handleDelete = (sale: Sale) => {
    Modal.confirm({
      title: 'Eliminar Venta',
      content: `Esta seguro de eliminar la preventa ${sale.doc_number !== null ? `${sale.doc_type}/${sale.series}-${String(sale.doc_number).padStart(7, '0')}` : `PRE-${sale.id}`}?`,
      okText: 'Eliminar',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: () => deleteMutation.mutateAsync(sale.id),
    });
  };

  const columns: ColumnsType<Sale> = [
    {
      title: 'Fecha',
      dataIndex: 'issue_date',
      key: 'issue_date',
      render: (date: string) => formatDate(date),
      width: 100,
    },
    {
      title: 'Documento',
      key: 'documento',
      render: (_: unknown, record: Sale) => {
        if (record.doc_number === null) {
          return <><Tag color="orange">PREVENTA</Tag>PRE-{record.id}</>;
        }
        const docNum = `${record.series}-${String(record.doc_number).padStart(7, '0')}`;
        if (record.doc_type === 'NOTA_CREDITO') {
          return <><Tag color="purple">N.CREDITO</Tag>{docNum}</>;
        }
        if (record.doc_type === 'NOTA_VENTA') {
          return <><Tag color="cyan">N.VENTA</Tag>{docNum}</>;
        }
        return `${record.doc_type}/${docNum}`;
      },
      width: 200,
    },
    {
      title: 'Cliente',
      dataIndex: 'client_name',
      key: 'client_name',
      ellipsis: true,
    },
    {
      title: 'SubTotal',
      dataIndex: 'subtotal',
      key: 'subtotal',
      render: (val: number) => formatCurrency(val),
      align: 'right',
      width: 110,
    },
    {
      title: 'IGV',
      dataIndex: 'igv_amount',
      key: 'igv_amount',
      render: (val: number) => formatCurrency(val),
      align: 'right',
      width: 100,
    },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      render: (val: number) => formatCurrency(val),
      align: 'right',
      width: 110,
    },
    {
      title: 'Condicion',
      dataIndex: 'payment_cond',
      key: 'payment_cond',
      width: 110,
    },
    {
      title: 'Vendedor',
      dataIndex: 'seller_name',
      key: 'seller_name',
      width: 120,
      ellipsis: true,
    },
    {
      title: 'Estado',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status] || 'default'}>{status}</Tag>
      ),
      width: 110,
    },
    {
      title: 'SUNAT',
      dataIndex: 'sunat_status',
      key: 'sunat_status',
      width: 100,
      render: (status: string | null | undefined) => {
        if (!status) return <Tag icon={<CloudOutlined />}>-</Tag>;
        const colors: Record<string, string> = {
          ACEPTADO: 'green',
          PENDIENTE: 'orange',
          ERROR: 'red',
          RECHAZADO: 'red',
        };
        return <Tag color={colors[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: 'Acciones',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: Sale) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/sales/${record.id}`)}
          />
          {record.status === 'PREVENTA' && (
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => navigate(`/sales/${record.id}`)}
            />
          )}
          {isAdmin && record.doc_type === 'NOTA_VENTA' && record.status === 'PREVENTA' && (
            <Button
              type="link"
              size="small"
              icon={<SwapOutlined />}
              title="Convertir a Boleta/Factura"
              onClick={() => handleConvertir(record)}
            />
          )}
          {isAdmin && record.status === 'FACTURADO' && record.doc_type !== 'NOTA_CREDITO' && (
            <Button
              type="link"
              size="small"
              icon={<RollbackOutlined />}
              title="Nota de Credito"
              onClick={() => navigate(`/sales/nota-credito/new?ref_sale_id=${record.id}`)}
            />
          )}
          {isAdmin && (record.status === 'PREVENTA' || record.status === 'FACTURADO') && (
            <Button
              type="link"
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() => handleVoid(record)}
            />
          )}
          {isAdmin && record.status === 'PREVENTA' && (
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
            />
          )}
          <Button
            type="link"
            size="small"
            icon={<PrinterOutlined />}
            disabled={
              record.status === 'PREVENTA' &&
              record.payment_method === 'EFECTIVO' &&
              (record.cash_received ?? 0) < record.total
            }
            title={
              record.status === 'PREVENTA' &&
              record.payment_method === 'EFECTIVO' &&
              (record.cash_received ?? 0) < record.total
                ? 'Efectivo insuficiente'
                : undefined
            }
            onClick={async () => {
              if (record.status === 'PREVENTA') {
                try {
                  await facturarSale(record.id);
                  message.success('Venta facturada');
                  queryClient.invalidateQueries({ queryKey: ['sales'] });
                } catch (err: any) {
                  message.error(err?.response?.data?.detail || 'Error al facturar');
                  return;
                }
              }
              window.open(`/sales/${record.id}/print`, '_blank');
            }}
          />
        </Space>
      ),
    },
  ];

  const salesData = data?.data ?? [];
  const filteredData =
    statusFilters.length > 1
      ? salesData.filter((s) => statusFilters.includes(s.status))
      : salesData;

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            Ventas
          </Title>
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/sales')}
          >
            Nueva Venta
          </Button>
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col>
          <RangePicker
            onChange={(dates) =>
              setDateRange(dates as [dayjs.Dayjs | null, dayjs.Dayjs | null] | null)
            }
            placeholder={['Fecha desde', 'Fecha hasta']}
          />
        </Col>
        <Col>
          <Select
            allowClear
            placeholder="Tipo doc."
            style={{ width: 130 }}
            onChange={(val) => setDocType(val)}
            options={[
              { value: 'BOLETA', label: 'Boleta' },
              { value: 'FACTURA', label: 'Factura' },
              { value: 'NOTA_CREDITO', label: 'N. Credito' },
              { value: 'NOTA_VENTA', label: 'N. Venta' },
            ]}
          />
        </Col>
        <Col>
          <Select
            allowClear
            placeholder="Almacen"
            style={{ width: 150 }}
            onChange={(val) => setWarehouseId(val)}
            options={warehouses?.map((w) => ({ value: w.id, label: w.name }))}
          />
        </Col>
        <Col>
          <Select
            allowClear
            placeholder="Vendedor"
            style={{ width: 150 }}
            onChange={(val) => setSellerId(val)}
            options={users?.map((u) => ({ value: u.id, label: u.full_name }))}
          />
        </Col>
        <Col>
          <Checkbox.Group
            options={[
              { label: 'Preventa', value: 'PREVENTA' },
              { label: 'Facturado', value: 'FACTURADO' },
              { label: 'Anulado', value: 'ANULADO' },
              { label: 'Eliminado', value: 'ELIMINADO' },
            ]}
            value={statusFilters}
            onChange={(vals) => setStatusFilters(vals as string[])}
          />
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={filteredData}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize,
          total: data?.total ?? 0,
          showSizeChanger: true,
          showTotal: (total) => `Total: ${total} ventas`,
          onChange: (p, ps) => {
            setPage(p);
            setPageSize(ps);
          },
        }}
        scroll={{ x: 1200 }}
        size="small"
      />

      <Modal
        title="Convertir Nota de Venta"
        open={convertirModalOpen}
        onCancel={() => setConvertirModalOpen(false)}
        onOk={() => {
          if (!convertirSaleRecord || !convertirTargetSeries) {
            message.warning('Seleccione una serie de destino');
            return;
          }
          convertirMutation.mutate({
            id: convertirSaleRecord.id,
            targetDocType: convertirTargetType,
            targetSeries: convertirTargetSeries,
          });
        }}
        okText="Convertir"
        cancelText="Cancelar"
        confirmLoading={convertirMutation.isPending}
      >
        {convertirSaleRecord && (
          <div ref={enterNavRef} style={{ marginTop: 16 }}>
            <p>
              Convertir <strong>{convertirSaleRecord.doc_number !== null ? `${convertirSaleRecord.series}-${String(convertirSaleRecord.doc_number).padStart(7, '0')}` : `PRE-${convertirSaleRecord.id}`}</strong> a:
            </p>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', marginBottom: 4 }}>Tipo de documento:</label>
              <Select
                value={convertirTargetType}
                onChange={(val) => { setConvertirTargetType(val); setConvertirTargetSeries(''); }}
                style={{ width: '100%' }}
                options={[
                  { value: 'BOLETA', label: 'Boleta' },
                  { value: 'FACTURA', label: 'Factura' },
                ]}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 4 }}>Serie:</label>
              <Select
                value={convertirTargetSeries || undefined}
                onChange={(val) => setConvertirTargetSeries(val)}
                style={{ width: '100%' }}
                placeholder="Seleccionar serie"
                options={(docSeries ?? [])
                  .filter((s) => s.is_active && s.doc_type === convertirTargetType)
                  .map((s) => ({ value: s.series, label: `${s.series} (Sig: ${s.next_number})` }))}
              />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
