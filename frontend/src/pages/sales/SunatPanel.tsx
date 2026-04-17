import { useState } from 'react';
import {
  Tabs,
  Table,
  Tag,
  Button,
  Space,
  DatePicker,
  Select,
  Row,
  Col,
  Typography,
  message,
  Modal,
  Input,
  Switch,
  Card,
  Tooltip,
} from 'antd';
import {
  SendOutlined,
  ReloadOutlined,
  FilePdfOutlined,
  FileTextOutlined,
  SafetyCertificateOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  LockOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getSunatDocumentos,
  reenviarFactura,
  enviarResumenBoletas,
  enviarBaja,
  checkTicketStatus,
  getPendingBoletas,
  enviarNotaCredito,
  enviarTodasNotasCredito,
  getResumenBoletas,
  enviarBajaMasiva,
  getPendingBajas,
  enviarTodasFacturas,
  getSunatSettings,
  updateSunatSettings,
} from '../../api/sunat';
import type { PendingBaja } from '../../api/sunat';
import type { ResumenBoleta } from '../../api/sunat';
import { getSales } from '../../api/sales';
import { formatCurrency, formatDateTime } from '../../utils/format';
import type { SunatDocument, Sale } from '../../types';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Title } = Typography;

const SUNAT_STATUS_COLORS: Record<string, string> = {
  ACEPTADO: 'green',
  PENDIENTE: 'orange',
  RECHAZADO: 'red',
  ERROR: 'red',
  NO_ENVIADA: 'default',
};

function FacturasTab() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  const { data, isLoading } = useQuery({
    queryKey: ['sunat-docs', 'FACTURA', statusFilter, page],
    queryFn: () =>
      getSunatDocumentos({
        doc_category: 'FACTURA',
        sunat_status: statusFilter,
        page,
        limit: 20,
      }),
  });

  const reenviarMut = useMutation({
    mutationFn: (saleId: number) => reenviarFactura(saleId),
    onSuccess: (doc) => {
      if (doc.sunat_status === 'ACEPTADO') {
        message.success('Factura aceptada por SUNAT');
      } else if (doc.sunat_status === 'ERROR' || doc.sunat_status === 'RECHAZADO') {
        message.error(`SUNAT: ${doc.sunat_description || 'Error'}`);
      } else {
        message.info(`Estado SUNAT: ${doc.sunat_status}`);
      }
      queryClient.invalidateQueries({ queryKey: ['sunat-docs'] });
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.detail || 'Error al reenviar factura');
    },
  });

  const enviarTodasMut = useMutation({
    mutationFn: () => enviarTodasFacturas(),
    onSuccess: (result) => {
      message.success(
        `Enviadas: ${result.enviadas} | Aceptadas: ${result.aceptadas} | Rechazadas: ${result.rechazadas} | Errores: ${result.errores}`
      );
      queryClient.invalidateQueries({ queryKey: ['sunat-docs'] });
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.detail || 'Error al enviar facturas');
    },
  });

  const columns: ColumnsType<SunatDocument> = [
    {
      title: 'Documento',
      key: 'doc',
      width: 180,
      render: (_: unknown, r: SunatDocument) =>
        r.series && r.doc_number
          ? `FACTURA/${r.series}-${String(r.doc_number).padStart(7, '0')}`
          : '-',
    },
    {
      title: 'Cliente',
      dataIndex: 'client_name',
      key: 'client_name',
      ellipsis: true,
    },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      width: 110,
      align: 'right',
      render: (val: number | null) => (val != null ? formatCurrency(val) : '-'),
    },
    {
      title: 'Estado SUNAT',
      dataIndex: 'sunat_status',
      key: 'sunat_status',
      width: 130,
      render: (status: string) => (
        <Tag color={SUNAT_STATUS_COLORS[status] || 'default'}>{status}</Tag>
      ),
    },
    {
      title: 'Descripcion',
      dataIndex: 'sunat_description',
      key: 'sunat_description',
      ellipsis: true,
      width: 200,
    },
    {
      title: 'Intentos',
      dataIndex: 'attempt_count',
      key: 'attempt_count',
      width: 80,
      align: 'center',
    },
    {
      title: 'Ultimo Envio',
      dataIndex: 'last_attempt_at',
      key: 'last_attempt_at',
      width: 160,
      render: (val: string | null) => (val ? formatDateTime(val) : '-'),
    },
    {
      title: 'Acciones',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: SunatDocument) => (
        <Space size="small">
          {record.sunat_status !== 'ACEPTADO' && record.sale_id && (
            <Button
              type="link"
              size="small"
              icon={<ReloadOutlined />}
              loading={reenviarMut.isPending}
              onClick={() => reenviarMut.mutate(record.sale_id!)}
            >
              Reenviar
            </Button>
          )}
          {record.sunat_pdf_url && (
            <Button
              type="link"
              size="small"
              icon={<FilePdfOutlined />}
              href={record.sunat_pdf_url}
              target="_blank"
            >
              PDF
            </Button>
          )}
          {record.sunat_xml_url && (
            <Button
              type="link"
              size="small"
              icon={<FileTextOutlined />}
              href={record.sunat_xml_url}
              target="_blank"
            >
              XML
            </Button>
          )}
          {record.sunat_cdr_url && (
            <Button
              type="link"
              size="small"
              icon={<SafetyCertificateOutlined />}
              href={record.sunat_cdr_url}
              target="_blank"
            >
              CDR
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col>
          <Select
            allowClear
            placeholder="Estado SUNAT"
            style={{ width: 160 }}
            onChange={(val) => {
              setStatusFilter(val);
              setPage(1);
            }}
            options={[
              { value: 'ACEPTADO', label: 'Aceptado' },
              { value: 'PENDIENTE', label: 'Pendiente' },
              { value: 'ERROR', label: 'Error' },
              { value: 'RECHAZADO', label: 'Rechazado' },
            ]}
          />
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<SendOutlined />}
            loading={enviarTodasMut.isPending}
            onClick={() =>
              Modal.confirm({
                title: 'Enviar todas las facturas pendientes a SUNAT?',
                onOk: () => enviarTodasMut.mutate(),
              })
            }
          >
            Enviar Todas las Pendientes
          </Button>
        </Col>
      </Row>
      <Table
        columns={columns}
        dataSource={data?.data ?? []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize: 20,
          total: data?.total ?? 0,
          showTotal: (total) => `Total: ${total}`,
          onChange: (p) => setPage(p),
        }}
        scroll={{ x: 1200 }}
        size="small"
      />
    </div>
  );
}

function ResumenBoletasTab() {
  const queryClient = useQueryClient();
  const [fecha, setFecha] = useState<dayjs.Dayjs>(dayjs());
  const [page, setPage] = useState(1);
  const [boletasModalOpen, setBoletasModalOpen] = useState(false);
  const [boletasModalData, setBoletasModalData] = useState<ResumenBoleta[]>([]);
  const [boletasModalLoading, setBoletasModalLoading] = useState(false);

  const fechaStr = fecha.format('YYYY-MM-DD');

  // Show boletas + NC-boletas for the selected date
  const { data: boletasData, isLoading: loadingBoletas } = useQuery({
    queryKey: ['boletas-dia', fechaStr],
    queryFn: async () => {
      const [boletas, ncs] = await Promise.all([
        getSales({ doc_type: 'BOLETA', status: 'FACTURADO,ANULADO', date_from: fechaStr, date_to: fechaStr, limit: 200 }),
        getSales({ doc_type: 'NOTA_CREDITO', status: 'FACTURADO', date_from: fechaStr, date_to: fechaStr, limit: 200 }),
      ]);
      // Only include NC-boletas (B-series)
      const ncBoletas = (ncs.data || []).filter((s: Sale) => s.series?.startsWith('B'));
      return { ...boletas, data: [...(boletas.data || []), ...ncBoletas] };
    },
  });

  // Get pending boletas count from backend (filters already-sent ones)
  const { data: pendingData } = useQuery({
    queryKey: ['pending-boletas', fechaStr],
    queryFn: () => getPendingBoletas(fechaStr),
  });

  // Show existing resumen documents
  const { data: resumenDocs } = useQuery({
    queryKey: ['sunat-docs', 'RESUMEN', page],
    queryFn: () =>
      getSunatDocumentos({ doc_category: 'RESUMEN', page, limit: 10 }),
  });

  const ticketMut = useMutation({
    mutationFn: (ticket: string) => checkTicketStatus(ticket),
    onSuccess: (doc) => {
      if (doc.sunat_status === 'ACEPTADO') {
        message.success('Resumen diario aceptado por SUNAT');
      } else if (doc.sunat_status === 'PENDIENTE') {
        message.info('Aun en proceso. Intente consultar en unos segundos.');
      } else {
        message.error(`SUNAT: ${doc.sunat_description || 'Rechazado'}`);
      }
      queryClient.invalidateQueries({ queryKey: ['sunat-docs'] });
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.detail || 'Error al consultar ticket');
    },
  });

  const resumenMut = useMutation({
    mutationFn: () => enviarResumenBoletas(fechaStr),
    onSuccess: (doc) => {
      if (doc.sunat_status === 'ACEPTADO') {
        message.success('Resumen diario aceptado por SUNAT');
      } else if (doc.sunat_status === 'PENDIENTE' && doc.ticket) {
        message.info(`Resumen enviado. Ticket: ${doc.ticket}. Use "Consultar" para verificar.`);
      } else if (doc.sunat_status === 'ERROR' || doc.sunat_status === 'RECHAZADO') {
        message.error(`SUNAT: ${doc.sunat_description || 'Error'}`);
      } else {
        message.info(`Estado SUNAT: ${doc.sunat_status}`);
      }
      queryClient.invalidateQueries({ queryKey: ['sunat-docs'] });
      queryClient.invalidateQueries({ queryKey: ['pending-boletas'] });
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.detail || 'Error al enviar resumen');
    },
  });

  const handleViewBoletas = async (docId: number) => {
    setBoletasModalLoading(true);
    setBoletasModalOpen(true);
    try {
      const result = await getResumenBoletas(docId);
      setBoletasModalData(result.boletas);
    } catch {
      message.error('Error al cargar boletas del resumen');
      setBoletasModalData([]);
    } finally {
      setBoletasModalLoading(false);
    }
  };

  const boletaColumns: ColumnsType<Sale> = [
    {
      title: 'Documento',
      key: 'doc',
      render: (_: unknown, r: Sale) => {
        const prefix = r.doc_type === 'NOTA_CREDITO' ? 'N.CREDITO' : 'BOLETA';
        return `${prefix}/${r.series}-${String(r.doc_number).padStart(7, '0')}`;
      },
      width: 200,
    },
    {
      title: 'Referencia',
      key: 'ref',
      width: 180,
      render: (_: unknown, r: Sale) => {
        if (r.doc_type === 'NOTA_CREDITO' && r.ref_sale_series && r.ref_sale_doc_number) {
          return `BOLETA/${r.ref_sale_series}-${String(r.ref_sale_doc_number).padStart(7, '0')}`;
        }
        return '-';
      },
    },
    {
      title: 'Cliente',
      dataIndex: 'client_name',
      key: 'client_name',
      ellipsis: true,
    },
    {
      title: 'Estado',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => (
        <Tag color={status === 'ANULADO' ? 'red' : 'green'}>{status}</Tag>
      ),
    },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      width: 110,
      align: 'right',
      render: (val: number) => formatCurrency(val),
    },
  ];

  const resumenColumns: ColumnsType<SunatDocument> = [
    {
      title: 'Fecha Referencia',
      dataIndex: 'reference_date',
      key: 'reference_date',
      width: 160,
      render: (val: string | null) => (val ? dayjs(val.substring(0, 10)).format('DD/MM/YYYY') : '-'),
    },
    {
      title: 'Estado',
      dataIndex: 'sunat_status',
      key: 'sunat_status',
      width: 120,
      render: (status: string) => (
        <Tag color={SUNAT_STATUS_COLORS[status] || 'default'}>{status}</Tag>
      ),
    },
    {
      title: 'Ticket',
      dataIndex: 'ticket',
      key: 'ticket',
      width: 180,
    },
    {
      title: 'Descripcion',
      dataIndex: 'sunat_description',
      key: 'sunat_description',
      ellipsis: true,
    },
    {
      title: 'Enviado',
      dataIndex: 'last_attempt_at',
      key: 'last_attempt_at',
      width: 160,
      render: (val: string | null) => (val ? formatDateTime(val) : '-'),
    },
    {
      title: 'Acciones',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: SunatDocument) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewBoletas(record.id)}
          >
            Ver
          </Button>
          {record.sunat_status === 'PENDIENTE' && record.ticket && (
            <Button
              type="link"
              size="small"
              icon={<ReloadOutlined />}
              loading={ticketMut.isPending}
              onClick={() => ticketMut.mutate(record.ticket!)}
            >
              Consultar
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // Exclude boletas anuladas before being sent to SUNAT (NO_ENVIADA) — SUNAT never knew about them
  const boletas = (boletasData?.data ?? []).filter(
    (s: Sale) => !(s.status === 'ANULADO' && s.sunat_status === 'NO_ENVIADA'),
  );

  return (
    <div>
      <Row gutter={16} align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <DatePicker
            value={fecha}
            onChange={(d) => d && setFecha(d)}
            format="DD/MM/YYYY"
          />
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={() => resumenMut.mutate()}
            loading={resumenMut.isPending}
            disabled={!pendingData || pendingData.total === 0}
          >
            Enviar Resumen Diario ({pendingData?.nuevas ?? 0} boletas{(pendingData?.anuladas ?? 0) > 0 ? `, ${pendingData?.anuladas} anuladas` : ''})
          </Button>
        </Col>
      </Row>

      <Title level={5}>Boletas y NC-Boletas del {fecha.format('DD/MM/YYYY')}</Title>
      <Table
        columns={boletaColumns}
        dataSource={boletas}
        rowKey="id"
        loading={loadingBoletas}
        pagination={false}
        size="small"
        style={{ marginBottom: 24 }}
      />

      <Title level={5}>Resumenes Enviados</Title>
      <Table
        columns={resumenColumns}
        dataSource={resumenDocs?.data ?? []}
        rowKey="id"
        pagination={{
          current: page,
          pageSize: 10,
          total: resumenDocs?.total ?? 0,
          onChange: (p) => setPage(p),
        }}
        size="small"
      />

      <Modal
        title="Boletas del Resumen"
        open={boletasModalOpen}
        onCancel={() => setBoletasModalOpen(false)}
        footer={null}
        width={700}
      >
        <Table
          columns={[
            {
              title: 'Documento',
              dataIndex: 'doc_number',
              key: 'doc_number',
              width: 180,
              render: (val: string) => `BOLETA/${val}`,
            },
            {
              title: 'Cliente',
              dataIndex: 'client_name',
              key: 'client_name',
              ellipsis: true,
            },
            {
              title: 'Condicion',
              dataIndex: 'condition',
              key: 'condition',
              width: 100,
              render: (val: string) => (
                <Tag color={val === 'Anulada' ? 'red' : 'green'}>{val}</Tag>
              ),
            },
            {
              title: 'Total',
              dataIndex: 'total',
              key: 'total',
              width: 110,
              align: 'right',
              render: (val: number) => formatCurrency(val),
            },
          ]}
          dataSource={boletasModalData}
          rowKey="sale_id"
          loading={boletasModalLoading}
          pagination={false}
          size="small"
        />
      </Modal>
    </div>
  );
}

function BajasTab() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);

  const { data: bajaDocs, isLoading } = useQuery({
    queryKey: ['sunat-docs', 'BAJA', page],
    queryFn: () => getSunatDocumentos({ doc_category: 'BAJA', page, limit: 20 }),
  });

  // Get only facturas pending baja (filtered by backend)
  const { data: pendingBajasData } = useQuery({
    queryKey: ['pending-bajas'],
    queryFn: () => getPendingBajas(),
  });

  const bajaTicketMut = useMutation({
    mutationFn: (ticket: string) => checkTicketStatus(ticket),
    onSuccess: (doc) => {
      if (doc.sunat_status === 'ACEPTADO') {
        message.success('Comunicacion de baja aceptada por SUNAT');
      } else if (doc.sunat_status === 'PENDIENTE') {
        message.info('Aun en proceso. Intente consultar en unos segundos.');
      } else {
        message.error(`SUNAT: ${doc.sunat_description || 'Rechazado'}`);
      }
      queryClient.invalidateQueries({ queryKey: ['sunat-docs'] });
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.detail || 'Error al consultar ticket');
    },
  });

  const bajaMut = useMutation({
    mutationFn: ({ saleId, motivo }: { saleId: number; motivo: string }) =>
      enviarBaja(saleId, motivo),
    onSuccess: (doc) => {
      if (doc.sunat_status === 'ACEPTADO') {
        message.success('Comunicacion de baja aceptada por SUNAT');
      } else if (doc.sunat_status === 'PENDIENTE' && doc.ticket) {
        message.info(`Baja enviada. Ticket: ${doc.ticket}. Use "Consultar" para verificar.`);
      } else {
        message.error(`SUNAT: ${doc.sunat_description || 'Error'}`);
      }
      queryClient.invalidateQueries({ queryKey: ['sunat-docs'] });
      queryClient.invalidateQueries({ queryKey: ['pending-bajas'] });
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.detail || 'Error al enviar baja');
    },
  });

  const bajaMasivaMut = useMutation({
    mutationFn: () => enviarBajaMasiva(),
    onSuccess: (doc) => {
      if (doc.sunat_status === 'ACEPTADO') {
        message.success('Todas las bajas aceptadas por SUNAT');
      } else if (doc.sunat_status === 'PENDIENTE' && doc.ticket) {
        message.info(`Bajas enviadas. Ticket: ${doc.ticket}. Use "Consultar" para verificar.`);
      } else {
        message.error(`SUNAT: ${doc.sunat_description || 'Error'}`);
      }
      queryClient.invalidateQueries({ queryKey: ['sunat-docs'] });
      queryClient.invalidateQueries({ queryKey: ['pending-bajas'] });
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.detail || 'Error al enviar bajas');
    },
  });

  const handleBaja = (sale: PendingBaja) => {
    let motivo = 'ANULACION DE OPERACION';
    Modal.confirm({
      title: 'Enviar Comunicacion de Baja',
      content: (
        <div>
          <p>
            Enviar baja a SUNAT para {sale.doc_type}/{sale.series}-
            {String(sale.doc_number).padStart(7, '0')}?
          </p>
          <Input.TextArea
            placeholder="Motivo"
            defaultValue={motivo}
            onChange={(e) => (motivo = e.target.value)}
            rows={2}
          />
        </div>
      ),
      okText: 'Enviar Baja',
      cancelText: 'Cancelar',
      onOk: () => bajaMut.mutateAsync({ saleId: sale.id, motivo }),
    });
  };

  const bajaColumns: ColumnsType<SunatDocument> = [
    {
      title: 'Documento',
      key: 'doc',
      width: 200,
      render: (_: unknown, r: SunatDocument) =>
        r.doc_type && r.series && r.doc_number
          ? `${r.doc_type}/${r.series}-${String(r.doc_number).padStart(7, '0')}`
          : '-',
    },
    {
      title: 'Cliente',
      dataIndex: 'client_name',
      key: 'client_name',
      ellipsis: true,
    },
    {
      title: 'Estado',
      dataIndex: 'sunat_status',
      key: 'sunat_status',
      width: 120,
      render: (status: string) => (
        <Tag color={SUNAT_STATUS_COLORS[status] || 'default'}>{status}</Tag>
      ),
    },
    {
      title: 'Ticket',
      dataIndex: 'ticket',
      key: 'ticket',
      width: 150,
    },
    {
      title: 'Descripcion',
      dataIndex: 'sunat_description',
      key: 'sunat_description',
      ellipsis: true,
    },
    {
      title: 'Enviado',
      dataIndex: 'last_attempt_at',
      key: 'last_attempt_at',
      width: 160,
      render: (val: string | null) => (val ? formatDateTime(val) : '-'),
    },
    {
      title: 'Acciones',
      key: 'actions',
      width: 140,
      render: (_: unknown, record: SunatDocument) => (
        <Space size="small">
          {record.sunat_status === 'PENDIENTE' && record.ticket && (
            <Button
              type="link"
              size="small"
              icon={<ReloadOutlined />}
              loading={bajaTicketMut.isPending}
              onClick={() => bajaTicketMut.mutate(record.ticket!)}
            >
              Consultar
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const anuladas = pendingBajasData?.data ?? [];

  return (
    <div>
      {anuladas.length > 0 && (
        <>
          <Row justify="space-between" align="middle" style={{ marginBottom: 8 }}>
            <Col>
              <Title level={5} style={{ margin: 0 }}>Ventas Anuladas (enviar baja)</Title>
            </Col>
            <Col>
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={() => bajaMasivaMut.mutate()}
                loading={bajaMasivaMut.isPending}
              >
                Enviar Todas las Bajas ({anuladas.length})
              </Button>
            </Col>
          </Row>
          <Table
            columns={[
              {
                title: 'Documento',
                key: 'doc',
                render: (_: unknown, r: PendingBaja) =>
                  `${r.doc_type}/${r.series}-${String(r.doc_number).padStart(7, '0')}`,
                width: 200,
              },
              {
                title: 'Cliente',
                dataIndex: 'client_name',
                key: 'client_name',
                ellipsis: true,
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
                title: '',
                key: 'action',
                width: 150,
                render: (_: unknown, record: PendingBaja) => (
                  <Button
                    type="link"
                    size="small"
                    icon={<CloseCircleOutlined />}
                    onClick={() => handleBaja(record)}
                    loading={bajaMut.isPending}
                  >
                    Enviar Baja
                  </Button>
                ),
              },
            ]}
            dataSource={anuladas}
            rowKey="id"
            pagination={false}
            size="small"
            style={{ marginBottom: 24 }}
          />
        </>
      )}

      <Title level={5}>Bajas Enviadas</Title>
      <Table
        columns={bajaColumns}
        dataSource={(bajaDocs?.data ?? []).filter((d) => d.sale_id != null)}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize: 20,
          total: bajaDocs?.total ?? 0,
          onChange: (p) => setPage(p),
        }}
        size="small"
      />
    </div>
  );
}

function NotasCreditoTab() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  const { data, isLoading } = useQuery({
    queryKey: ['sunat-docs', 'NOTA_CREDITO', statusFilter, page],
    queryFn: () =>
      getSunatDocumentos({
        doc_category: 'NOTA_CREDITO',
        sunat_status: statusFilter,
        page,
        limit: 20,
      }),
  });

  const enviarMut = useMutation({
    mutationFn: (saleId: number) => enviarNotaCredito(saleId),
    onSuccess: (doc) => {
      if (doc.sunat_status === 'ACEPTADO') {
        message.success('Nota de Credito aceptada por SUNAT');
      } else if (doc.sunat_status === 'ERROR' || doc.sunat_status === 'RECHAZADO') {
        message.error(`SUNAT: ${doc.sunat_description || 'Error'}`);
      } else {
        message.info(`Estado SUNAT: ${doc.sunat_status}`);
      }
      queryClient.invalidateQueries({ queryKey: ['sunat-docs'] });
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.detail || 'Error al enviar nota de credito');
    },
  });

  const enviarTodasNCMut = useMutation({
    mutationFn: () => enviarTodasNotasCredito(),
    onSuccess: (result) => {
      message.success(
        `Enviadas: ${result.enviadas} | Aceptadas: ${result.aceptadas} | Rechazadas: ${result.rechazadas} | Errores: ${result.errores}`
      );
      queryClient.invalidateQueries({ queryKey: ['sunat-docs'] });
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.detail || 'Error al enviar notas de credito');
    },
  });

  const columns: ColumnsType<SunatDocument> = [
    {
      title: 'Documento',
      key: 'doc',
      width: 200,
      render: (_: unknown, r: SunatDocument) =>
        r.series && r.doc_number
          ? `N.CREDITO/${r.series}-${String(r.doc_number).padStart(7, '0')}`
          : '-',
    },
    {
      title: 'Cliente',
      dataIndex: 'client_name',
      key: 'client_name',
      ellipsis: true,
    },
    {
      title: 'Total',
      dataIndex: 'total',
      key: 'total',
      width: 110,
      align: 'right',
      render: (val: number | null) => (val != null ? formatCurrency(val) : '-'),
    },
    {
      title: 'Estado SUNAT',
      dataIndex: 'sunat_status',
      key: 'sunat_status',
      width: 130,
      render: (status: string) => (
        <Tag color={SUNAT_STATUS_COLORS[status] || 'default'}>{status}</Tag>
      ),
    },
    {
      title: 'Descripcion',
      dataIndex: 'sunat_description',
      key: 'sunat_description',
      ellipsis: true,
      width: 200,
    },
    {
      title: 'Intentos',
      dataIndex: 'attempt_count',
      key: 'attempt_count',
      width: 80,
      align: 'center',
    },
    {
      title: 'Ultimo Envio',
      dataIndex: 'last_attempt_at',
      key: 'last_attempt_at',
      width: 160,
      render: (val: string | null) => (val ? formatDateTime(val) : '-'),
    },
    {
      title: 'Acciones',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: SunatDocument) => (
        <Space size="small">
          {record.sunat_status !== 'ACEPTADO' && record.sale_id && (
            <Button
              type="link"
              size="small"
              icon={<ReloadOutlined />}
              loading={enviarMut.isPending}
              onClick={() => enviarMut.mutate(record.sale_id!)}
            >
              Reenviar
            </Button>
          )}
          {record.sunat_pdf_url && (
            <Button
              type="link"
              size="small"
              icon={<FilePdfOutlined />}
              href={record.sunat_pdf_url}
              target="_blank"
            >
              PDF
            </Button>
          )}
          {record.sunat_xml_url && (
            <Button
              type="link"
              size="small"
              icon={<FileTextOutlined />}
              href={record.sunat_xml_url}
              target="_blank"
            >
              XML
            </Button>
          )}
          {record.sunat_cdr_url && (
            <Button
              type="link"
              size="small"
              icon={<SafetyCertificateOutlined />}
              href={record.sunat_cdr_url}
              target="_blank"
            >
              CDR
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col>
          <Select
            allowClear
            placeholder="Estado SUNAT"
            style={{ width: 160 }}
            onChange={(val) => {
              setStatusFilter(val);
              setPage(1);
            }}
            options={[
              { value: 'ACEPTADO', label: 'Aceptado' },
              { value: 'PENDIENTE', label: 'Pendiente' },
              { value: 'ERROR', label: 'Error' },
              { value: 'RECHAZADO', label: 'Rechazado' },
            ]}
          />
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<SendOutlined />}
            loading={enviarTodasNCMut.isPending}
            onClick={() =>
              Modal.confirm({
                title: 'Enviar todas las notas de credito pendientes a SUNAT?',
                onOk: () => enviarTodasNCMut.mutate(),
              })
            }
          >
            Enviar Todas las Pendientes
          </Button>
        </Col>
      </Row>
      <p style={{ marginBottom: 12, color: '#888', fontSize: 12 }}>
        Solo NC de facturas (F-series). Las NC de boletas (B-series) se envian en el Resumen Diario.
      </p>
      <Table
        columns={columns}
        dataSource={(data?.data ?? []).filter((d: SunatDocument) => !d.series || !d.series.startsWith('B'))}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize: 20,
          total: data?.total ?? 0,
          showTotal: (total) => `Total: ${total}`,
          onChange: (p) => setPage(p),
        }}
        scroll={{ x: 1200 }}
        size="small"
      />
    </div>
  );
}

function SunatSettingsPanel() {
  const queryClient = useQueryClient();
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [pendingToggle, setPendingToggle] = useState<{
    field: 'auto_send_enabled' | 'block_before_10pm';
    value: boolean;
  } | null>(null);
  const [password, setPassword] = useState('');

  const { data: settings } = useQuery({
    queryKey: ['sunat-settings'],
    queryFn: getSunatSettings,
  });

  const updateMut = useMutation({
    mutationFn: updateSunatSettings,
    onSuccess: (result) => {
      message.success('Configuracion actualizada');
      queryClient.setQueryData(['sunat-settings'], result);
      setPasswordModalOpen(false);
      setPassword('');
      setPendingToggle(null);
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.detail || 'Error al actualizar');
    },
  });

  const handleToggle = (field: 'auto_send_enabled' | 'block_before_10pm', value: boolean) => {
    setPendingToggle({ field, value });
    setPassword('');
    setPasswordModalOpen(true);
  };

  const handleConfirm = () => {
    if (!pendingToggle || !password) return;
    updateMut.mutate({
      [pendingToggle.field]: pendingToggle.value,
      password,
    });
  };

  const toggleLabel = pendingToggle
    ? pendingToggle.field === 'auto_send_enabled'
      ? pendingToggle.value
        ? 'activar envio automatico'
        : 'desactivar envio automatico'
      : pendingToggle.value
        ? 'activar bloqueo antes de 10 PM'
        : 'desactivar bloqueo antes de 10 PM'
    : '';

  return (
    <>
      <Card
        size="small"
        style={{ marginBottom: 16 }}
        title={
          <span>
            <SettingOutlined style={{ marginRight: 8 }} />
            Configuracion SUNAT
          </span>
        }
      >
        <Row gutter={32} align="middle">
          <Col>
            <Space>
              <Tooltip title="Enviar automaticamente facturas, boletas, NC a SUNAT a las 11:00 PM">
                <span>Envio automatico (11 PM)</span>
              </Tooltip>
              <Switch
                checked={settings?.auto_send_enabled ?? true}
                onChange={(checked) => handleToggle('auto_send_enabled', checked)}
              />
            </Space>
          </Col>
          <Col>
            <Space>
              <Tooltip title="Bloquear envio manual antes de las 10:00 PM hora Lima">
                <span>Bloqueo antes de 10 PM</span>
              </Tooltip>
              <Switch
                checked={settings?.block_before_10pm ?? true}
                onChange={(checked) => handleToggle('block_before_10pm', checked)}
              />
            </Space>
          </Col>
        </Row>
      </Card>

      <Modal
        title={
          <span>
            <LockOutlined style={{ marginRight: 8 }} />
            Confirmar cambio
          </span>
        }
        open={passwordModalOpen}
        onCancel={() => {
          setPasswordModalOpen(false);
          setPassword('');
          setPendingToggle(null);
        }}
        onOk={handleConfirm}
        okText="Confirmar"
        cancelText="Cancelar"
        confirmLoading={updateMut.isPending}
        okButtonProps={{ disabled: !password }}
      >
        <p>
          Ingrese su contraseña de administrador para <strong>{toggleLabel}</strong>:
        </p>
        <Input.Password
          prefix={<LockOutlined />}
          placeholder="Contraseña de administrador"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onPressEnter={handleConfirm}
          autoFocus
        />
      </Modal>
    </>
  );
}

export default function SunatPanel() {
  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>
        Envio SUNAT
      </Title>
      <SunatSettingsPanel />
      <Tabs
        defaultActiveKey="facturas"
        items={[
          {
            key: 'facturas',
            label: 'Facturas',
            children: <FacturasTab />,
          },
          {
            key: 'resumen',
            label: 'Resumen Boletas',
            children: <ResumenBoletasTab />,
          },
          {
            key: 'notas-credito',
            label: 'Notas de Credito',
            children: <NotasCreditoTab />,
          },
          {
            key: 'bajas',
            label: 'Bajas',
            children: <BajasTab />,
          },
        ]}
      />
    </div>
  );
}
