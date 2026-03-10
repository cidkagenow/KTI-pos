import { useState, useEffect } from 'react';
import {
  Select,
  InputNumber,
  Button,
  Table,
  Row,
  Col,
  Card,
  Typography,
  message,
  Space,
  Checkbox,
  Descriptions,
  Tag,
} from 'antd';
import { CheckOutlined } from '@ant-design/icons';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getSale, createNotaCredito, facturarSale } from '../../api/sales';
import { calcLineTotal, calcIGV, formatCurrency } from '../../utils/format';
import type { Sale } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import useEnterNavigation from '../../hooks/useEnterNavigation';

const { Title, Text } = Typography;

const NC_MOTIVOS = [
  { code: '01', label: '01 - Anulacion de la operacion', text: 'Anulacion de la operacion' },
  { code: '02', label: '02 - Correccion por error en la descripcion', text: 'Correccion por error en la descripcion' },
  { code: '03', label: '03 - Descuento global', text: 'Descuento global' },
  { code: '04', label: '04 - Devolucion total o parcial', text: 'Devolucion total o parcial' },
  { code: '06', label: '06 - Ajuste de precio', text: 'Ajuste de precio' },
];

interface NCLineItem {
  key: number;
  product_id: number;
  product_code: string;
  product_name: string;
  brand_name: string | null;
  presentation: string | null;
  unit_price: number;
  discount_pct: number;
  orig_quantity: number;
  new_quantity: number;  // what customer keeps
  selected: boolean;
}

export default function NotaCreditoForm() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isAdmin } = useAuth();
  const refSaleId = searchParams.get('ref_sale_id');

  const [motivoCode, setMotivoCode] = useState<string>('04');
  const [items, setItems] = useState<NCLineItem[]>([]);
  const [saving, setSaving] = useState(false);
  const enterNavRef = useEnterNavigation(() => handleFacturar());

  const { data: refSale, isLoading } = useQuery({
    queryKey: ['sale', refSaleId],
    queryFn: () => getSale(Number(refSaleId)),
    enabled: !!refSaleId,
  });

  // Initialize items — all unselected, new_quantity = orig (no return)
  useEffect(() => {
    if (refSale?.items) {
      setItems(
        refSale.items.map((item, idx) => ({
          key: item.id ?? idx,
          product_id: item.product_id,
          product_code: item.product_code,
          product_name: item.product_name,
          brand_name: item.brand_name,
          presentation: item.presentation,
          unit_price: item.unit_price,
          discount_pct: item.discount_pct,
          orig_quantity: item.quantity,
          new_quantity: item.quantity, // keeps all = no return
          selected: false,
        })),
      );
    }
  }, [refSale]);

  // Devolucion for an item = orig - new
  const getDevolucion = (item: NCLineItem) => item.orig_quantity - item.new_quantity;
  const getLineTotal = (item: NCLineItem) => {
    const dev = getDevolucion(item);
    return dev > 0 ? calcLineTotal(dev, item.unit_price, item.discount_pct) : 0;
  };

  const selectedItems = items.filter((i) => i.selected && getDevolucion(i) > 0);
  const grandTotal = selectedItems.reduce((sum, i) => sum + getLineTotal(i), 0);
  const { base: subtotal, igv: igvAmount, total } = calcIGV(grandTotal);
  const totalDevolucion = selectedItems.reduce((sum, i) => sum + getDevolucion(i), 0);

  const motivo = NC_MOTIVOS.find((m) => m.code === motivoCode);

  const createMutation = useMutation({ mutationFn: createNotaCredito });
  const facturarMutation = useMutation({ mutationFn: facturarSale });

  const handleToggleItem = (key: number, checked: boolean) => {
    setItems((prev) =>
      prev.map((i) => {
        if (i.key !== key) return i;
        // Check: default to returning 1 item (new_qty = orig - 1)
        // Uncheck: keep all (new_qty = orig)
        const newQty = checked ? i.orig_quantity - 1 : i.orig_quantity;
        return { ...i, selected: checked, new_quantity: newQty };
      }),
    );
  };

  const handleNewQuantityChange = (key: number, val: number | null) => {
    setItems((prev) =>
      prev.map((i) => {
        if (i.key !== key) return i;
        const newQty = Math.min(Math.max(val ?? i.orig_quantity, 0), i.orig_quantity - 1);
        const hasDevolucion = newQty < i.orig_quantity;
        return { ...i, new_quantity: newQty, selected: hasDevolucion };
      }),
    );
  };

  const buildPayload = () => ({
    ref_sale_id: Number(refSaleId),
    nc_motivo_code: motivoCode,
    nc_motivo_text: motivo?.text || '',
    // Send devolucion quantity (what's returned), not the new quantity
    items: selectedItems.map((i) => ({
      product_id: i.product_id,
      quantity: getDevolucion(i),
      unit_price: i.unit_price,
      discount_pct: i.discount_pct,
    })),
  });

  const handleFacturar = async () => {
    if (!selectedItems.length) {
      message.warning('Seleccione al menos un item con devolucion');
      return;
    }
    setSaving(true);
    try {
      const nc = await createMutation.mutateAsync(buildPayload());
      await facturarMutation.mutateAsync(nc.id);
      message.success('Nota de Credito facturada correctamente');
      navigate('/sales/list');
    } catch (err: any) {
      message.error(err?.response?.data?.detail || 'Error al procesar Nota de Credito');
    } finally {
      setSaving(false);
    }
  };

  if (!refSaleId) {
    return <div style={{ padding: 40 }}>Falta ref_sale_id en la URL</div>;
  }

  if (isLoading) {
    return <div style={{ padding: 40, textAlign: 'center' }}>Cargando venta original...</div>;
  }

  if (!refSale) {
    return <div style={{ padding: 40 }}>Venta original no encontrada</div>;
  }

  const columns = [
    {
      title: '',
      dataIndex: 'selected',
      key: 'selected',
      width: 40,
      render: (_: boolean, record: NCLineItem) => (
        <Checkbox
          checked={record.selected}
          onChange={(e) => handleToggleItem(record.key, e.target.checked)}
        />
      ),
    },
    {
      title: 'Codigo',
      dataIndex: 'product_code',
      key: 'product_code',
      width: 90,
    },
    {
      title: 'Producto',
      dataIndex: 'product_name',
      key: 'product_name',
      ellipsis: true,
    },
    {
      title: 'P.U.',
      dataIndex: 'unit_price',
      key: 'unit_price',
      width: 90,
      align: 'right' as const,
      render: (val: number) => val.toFixed(2),
    },
    {
      title: 'Cant. Orig.',
      dataIndex: 'orig_quantity',
      key: 'orig_quantity',
      width: 90,
      align: 'center' as const,
    },
    {
      title: 'Nueva Cant.',
      key: 'new_quantity',
      width: 110,
      render: (_: unknown, record: NCLineItem) => (
        <InputNumber
          min={0}
          max={record.orig_quantity - 1}
          value={record.new_quantity}
          size="small"
          onChange={(val) => handleNewQuantityChange(record.key, val)}
        />
      ),
    },
    {
      title: 'Devolucion',
      key: 'devolucion',
      width: 90,
      align: 'center' as const,
      render: (_: unknown, record: NCLineItem) => {
        const dev = getDevolucion(record);
        return dev > 0 ? <Tag color="orange">{dev}</Tag> : '-';
      },
    },
    {
      title: 'Total NC',
      key: 'line_total',
      width: 110,
      align: 'right' as const,
      render: (_: unknown, record: NCLineItem) => {
        const dev = getDevolucion(record);
        return dev > 0 ? formatCurrency(getLineTotal(record)) : '-';
      },
    },
  ];

  const refDocNumber = refSale.doc_number
    ? `${refSale.doc_type}/${refSale.series}-${String(refSale.doc_number).padStart(7, '0')}`
    : `PRE-${refSale.id}`;

  return (
    <div ref={enterNavRef}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            Nueva Nota de Credito
          </Title>
        </Col>
        <Col>
          <Space>
            <Button onClick={() => navigate('/sales/list')}>Cancelar</Button>
            {isAdmin && (
              <Button
                type="primary"
                icon={<CheckOutlined />}
                onClick={handleFacturar}
                loading={saving}
                disabled={!selectedItems.length}
              >
                Facturar
              </Button>
            )}
          </Space>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={16}>
          <Card title="Items de la Nota de Credito" size="small">
            <Table
              columns={columns}
              dataSource={items}
              rowKey="key"
              pagination={false}
              size="small"
              rowClassName={(record) => (!record.selected ? 'ant-table-row-dimmed' : '')}
            />
          </Card>
        </Col>

        <Col span={8}>
          <Card title="Documento de Referencia" size="small" style={{ marginBottom: 16 }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Documento">{refDocNumber}</Descriptions.Item>
              <Descriptions.Item label="Cliente">{refSale.client_name}</Descriptions.Item>
              <Descriptions.Item label="Total">{formatCurrency(refSale.total)}</Descriptions.Item>
              <Descriptions.Item label="Estado">
                <Tag color="green">{refSale.status}</Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="Motivo" size="small" style={{ marginBottom: 16 }}>
            <Select
              value={motivoCode}
              onChange={setMotivoCode}
              style={{ width: '100%' }}
              options={NC_MOTIVOS.map((m) => ({
                value: m.code,
                label: m.label,
              }))}
            />
            {(motivoCode === '01' || motivoCode === '04') && (
              <div style={{ marginTop: 8 }}>
                <Tag color="blue">Devuelve stock al almacen</Tag>
              </div>
            )}
          </Card>

          <Card title="Resumen" size="small">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <Text>Items con devolucion:</Text>
              <Text strong>{selectedItems.length}</Text>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <Text>Total unidades devueltas:</Text>
              <Text strong>{totalDevolucion}</Text>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <Text>Op. Gravada:</Text>
              <Text>{formatCurrency(subtotal)}</Text>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <Text>IGV (18%):</Text>
              <Text>{formatCurrency(igvAmount)}</Text>
            </div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                borderTop: '1px solid #303030',
                paddingTop: 8,
                marginTop: 4,
              }}
            >
              <Text strong style={{ fontSize: 16 }}>TOTAL NC:</Text>
              <Text strong style={{ fontSize: 16 }}>{formatCurrency(total)}</Text>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
