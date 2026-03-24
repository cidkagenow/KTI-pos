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
} from 'antd';
import {
  SendOutlined,
  ReloadOutlined,
  FilePdfOutlined,
  FileTextOutlined,
  SafetyCertificateOutlined,
  CloseCircleOutlined,
  EyeOutlined,
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

  // Show boletas for the selected date (both facturado and anulado)
  const { data: boletasData, isLoading: loadingBoletas } = useQuery({
    queryKey: ['boletas-dia', fechaStr],
    queryFn: () =>
      getSales({
        doc_type: 'BOLETA',
        status: 'FACTURADO,ANULADO',
        date_from: fechaStr,
        date_to: fechaStr,
        limit: 200,
      }),
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
      render: (_: unknown, r: Sale) =>
        `BOLETA/${r.series}-${String(r.doc_number).padStart(7, '0')}`,
      width: 200,
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

      <Title level={5}>Boletas del {fecha.format('DD/MM/YYYY')}</Title>
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

export default function SunatPanel() {
  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>
        Envio SUNAT
      </Title>
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
