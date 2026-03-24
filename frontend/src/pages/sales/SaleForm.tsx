import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Form,
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
  AutoComplete,
  Divider,
  Spin,
  Input,
  Radio,
  Tag,
  DatePicker,
  Modal,
  Tabs,
} from 'antd';
import { PlusOutlined, DeleteOutlined, SaveOutlined, CheckOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { createSale, updateSale, getSale, facturarSale, emitirNotaVenta, emitirProforma, deleteSale } from '../../api/sales';
import { searchProducts } from '../../api/products';
import { searchClients, createClient, lookupRUC, lookupDNI } from '../../api/clients';
import { getWarehouses, getDocumentSeries } from '../../api/catalogs';
import { getActiveTrabajadores } from '../../api/trabajadores';
import { calcLineTotal, calcIGV, formatCurrency, round2 } from '../../utils/format';
import { tokenizedFilter, tokenizedFilterSort } from '../../utils/search';
import type { ProductSearch, Client } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import useEnterNavigation from '../../hooks/useEnterNavigation';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

interface LineItem {
  key: string;
  product_id: number | null;
  product_code: string;
  product_name: string;
  brand_name: string | null;
  presentation: string | null;
  quantity: number;
  unit_price: number;
  wholesale_price: number | null;
  cost_price: number | null;
  discount_pct: number;
  line_total: number;
  stock: number;
}

function newLineItem(): LineItem {
  return {
    key: crypto.randomUUID(),
    product_id: null,
    product_code: '',
    product_name: '',
    brand_name: null,
    presentation: null,
    quantity: 1,
    unit_price: 0,
    wholesale_price: null,
    cost_price: null,
    discount_pct: 0,
    line_total: 0,
    stock: 0,
  };
}

export default function SaleForm() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEditing = Boolean(id);
  const { isAdmin } = useAuth();
  const [form] = Form.useForm();
  const facturarRef = useRef<HTMLButtonElement>(null);
  const autoAddRowRef = useRef<() => void>(() => {});
  const enterNavRef = useEnterNavigation(() => facturarRef.current?.focus(), () => autoAddRowRef.current());
  const [items, setItems] = useState<LineItem[]>([newLineItem()]);
  const [productOptions, setProductOptions] = useState<{ value: string; label: string; product: ProductSearch; disabled?: boolean }[]>([]);
  const [clientOptions, setClientOptions] = useState<{ value: number; label: string }[]>([]);
  const [clientSearch, setClientSearch] = useState('');
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);
  const [paymentMethod, setPaymentMethod] = useState<'EFECTIVO' | 'TARJETA'>('EFECTIVO');
  const [cashReceived, setCashReceived] = useState<number>(0);
  const [clientModalOpen, setClientModalOpen] = useState(false);
  const [clientModalLoading, setClientModalLoading] = useState(false);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [clientForm] = Form.useForm();
  const clientEnterNavRef = useEnterNavigation(() => handleCreateClient());

  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: getWarehouses });
  const { data: trabajadores } = useQuery({ queryKey: ['trabajadores-active'], queryFn: getActiveTrabajadores });
  const { data: docSeries } = useQuery({ queryKey: ['doc-series'], queryFn: getDocumentSeries });

  const { data: existingSale, isLoading: loadingSale } = useQuery({
    queryKey: ['sale', id],
    queryFn: () => getSale(Number(id)),
    enabled: isEditing,
  });

  useEffect(() => {
    if (existingSale) {
      form.setFieldsValue({
        doc_type_series: `${existingSale.doc_type}|${existingSale.series}`,
        client_id: existingSale.client_id,
        warehouse_id: existingSale.warehouse_id,
        trabajador_id: existingSale.trabajador_id ?? existingSale.seller_id,
        payment_cond: existingSale.payment_cond,
        max_discount_pct: existingSale.max_discount_pct ?? 0,
        issue_date: existingSale.issue_date ? dayjs(existingSale.issue_date) : dayjs(),
      });
      setClientOptions([{ value: existingSale.client_id, label: existingSale.client_name }]);
      if (existingSale.payment_method) {
        setPaymentMethod(existingSale.payment_method as 'EFECTIVO' | 'TARJETA');
      }
      if (existingSale.cash_received != null) {
        setCashReceived(existingSale.cash_received);
      }
      const lineItems: LineItem[] = existingSale.items.map((item) => ({
        key: crypto.randomUUID(),
        product_id: item.product_id,
        product_code: item.product_code,
        product_name: item.product_name,
        brand_name: item.brand_name,
        presentation: item.presentation,
        quantity: item.quantity,
        unit_price: item.unit_price,
        wholesale_price: null,
        cost_price: null,
        discount_pct: item.discount_pct,
        line_total: item.line_total,
        stock: 0,
      }));
      setItems(lineItems);

      // Fetch stock for each product
      Promise.all(
        existingSale.items
          .filter((item) => item.product_id)
          .map((item) => searchProducts(item.product_code || String(item.product_id)))
      ).then((results) => {
        setItems((prev) =>
          prev.map((lineItem) => {
            const found = results.flat().find((p) => p.id === lineItem.product_id);
            return found ? { ...lineItem, stock: found.stock, wholesale_price: found.wholesale_price, cost_price: found.cost_price } : lineItem;
          })
        );
      });
    }
  }, [existingSale, form]);

  // Set defaults for new sales
  useEffect(() => {
    if (isEditing) return;
    if (!docSeries || !warehouses) return;

    // Serie: single global default, or first active BOLETA series
    const globalDefault = docSeries.find((s) => s.is_active && s.is_default);
    const firstBoleta = docSeries.find((s) => s.is_active && s.doc_type === 'BOLETA');
    const selectedSeries = globalDefault || firstBoleta;
    if (selectedSeries) {
      form.setFieldValue('doc_type_series', `${selectedSeries.doc_type}|${selectedSeries.series}`);
    }

    // Almacen: first warehouse matching "principal", else first
    if (warehouses.length > 0) {
      const principal = warehouses.find((w) => w.name.toLowerCase().includes('principal'));
      form.setFieldValue('warehouse_id', principal ? principal.id : warehouses[0].id);
    }

    // Condicion de pago: CONTADO
    form.setFieldValue('payment_cond', 'CONTADO');
  }, [isEditing, docSeries, warehouses, form]);

  // Auto-search and pre-select "CLIENTES VARIOS" for new sales
  useEffect(() => {
    if (isEditing) return;
    searchClients('CLIENTES VARIOS').then((results) => {
      if (results.length > 0) {
        const c = results[0];
        setClientOptions([{
          value: c.id,
          label: `${c.doc_number ? c.doc_number + ' - ' : ''}${c.business_name}`,
        }]);
        form.setFieldValue('client_id', c.id);
      }
    }).catch(() => {});
  }, [isEditing, form]);

  const handleProductSearch = useCallback(async (searchText: string) => {
    if (searchText.length < 2) {
      setProductOptions([]);
      return;
    }
    try {
      const results = await searchProducts(searchText);
      const searchLower = searchText.toLowerCase();
      setProductOptions(
        results
          .sort((a, b) => {
            // Primary: in-stock first
            const stockDiff = (b.stock > 0 ? 1 : 0) - (a.stock > 0 ? 1 : 0);
            if (stockDiff !== 0) return stockDiff;
            // Secondary: name starts with search term first
            const aName = a.name.toLowerCase();
            const bName = b.name.toLowerCase();
            const aStarts = aName.startsWith(searchLower) ? 0 : 1;
            const bStarts = bName.startsWith(searchLower) ? 0 : 1;
            if (aStarts !== bStarts) return aStarts - bStarts;
            // Tertiary: position of search term in name
            const aPos = aName.indexOf(searchLower);
            const bPos = bName.indexOf(searchLower);
            return aPos - bPos;
          })
          .map((p) => {
            const outOfStock = p.stock <= 0;
            let stockLabel: string;
            if (outOfStock && p.on_order_qty) {
              const etaStr = p.on_order_eta
                ? `, llega ${new Date(p.on_order_eta).toLocaleDateString('es-PE')}`
                : '';
              stockLabel = `SIN STOCK - En Pedido (${p.on_order_qty})${etaStr}`;
            } else if (outOfStock) {
              stockLabel = 'SIN STOCK - Agotado';
            } else {
              stockLabel = `Stock: ${p.stock}`;
            }
            return {
              value: `${p.id}`,
              label: `${p.code} - ${p.name} [${stockLabel}]`,
              product: p,
              disabled: outOfStock,
            };
          })
      );
    } catch {
      setProductOptions([]);
    }
  }, []);

  const handleClientSearch = useCallback(async (searchText: string) => {
    setClientSearch(searchText);
    if (searchText.length < 2) {
      setClientOptions([]);
      return;
    }
    try {
      const results = await searchClients(searchText);
      const searchLower = searchText.toLowerCase();
      setClientOptions(
        results
          .sort((a, b) => {
            const aName = a.business_name.toLowerCase();
            const bName = b.business_name.toLowerCase();
            const aStarts = aName.startsWith(searchLower) ? 0 : 1;
            const bStarts = bName.startsWith(searchLower) ? 0 : 1;
            if (aStarts !== bStarts) return aStarts - bStarts;
            const aPos = aName.indexOf(searchLower);
            const bPos = bName.indexOf(searchLower);
            return aPos - bPos;
          })
          .map((c: Client) => ({
            value: c.id,
            label: `${c.doc_number ? c.doc_number + ' - ' : ''}${c.business_name}`,
          }))
      );
    } catch {
      setClientOptions([]);
    }
  }, []);

  const handleLookup = async () => {
    const docType = clientForm.getFieldValue('doc_type');
    const docNumber = clientForm.getFieldValue('doc_number');
    if (!docType || !docNumber) return;
    setLookupLoading(true);
    try {
      if (docType === 'RUC') {
        const result = await lookupRUC(docNumber);
        clientForm.setFieldsValue({ business_name: result.business_name, address: result.address });
      } else if (docType === 'DNI') {
        const result = await lookupDNI(docNumber);
        clientForm.setFieldsValue({ business_name: result.business_name });
      }
    } catch {
      message.error('No se pudo consultar el documento');
    } finally {
      setLookupLoading(false);
    }
  };

  const handleCreateClient = async () => {
    try {
      const values = await clientForm.validateFields();
      setClientModalLoading(true);
      const created = await createClient(values);
      setClientOptions((prev) => [
        ...prev,
        { value: created.id, label: `${created.doc_number ? created.doc_number + ' - ' : ''}${created.business_name}` },
      ]);
      form.setFieldValue('client_id', created.id);
      setClientModalOpen(false);
      clientForm.resetFields();
      message.success('Cliente creado');
    } catch (err: any) {
      if (err?.response?.data?.detail) {
        message.error(err.response.data.detail);
      }
    } finally {
      setClientModalLoading(false);
    }
  };

  const handleProductSelect = (value: string, idx: number) => {
    const option = productOptions.find((o) => o.value === value);
    if (!option) return;
    const p = option.product;
    setItems((prev) => {
      const updated = [...prev];
      updated[idx] = {
        ...updated[idx],
        product_id: p.id,
        product_code: p.code,
        product_name: p.name,
        brand_name: p.brand_name,
        presentation: p.presentation,
        unit_price: p.unit_price,
        wholesale_price: p.wholesale_price,
        cost_price: p.cost_price,
        stock: p.stock,
        line_total: calcLineTotal(updated[idx].quantity, p.unit_price, updated[idx].discount_pct),
      };
      return updated;
    });
  };

  const updateItem = (idx: number, field: keyof LineItem, value: number) => {
    setItems((prev) => {
      const updated = [...prev];
      const item = { ...updated[idx], [field]: value };
      item.line_total = calcLineTotal(item.quantity, item.unit_price, item.discount_pct);
      updated[idx] = item;
      return updated;
    });
  };

  const addRow = () => setItems((prev) => [...prev, newLineItem()]);
  autoAddRowRef.current = addRow;

  const removeRow = (idx: number) => {
    setItems((prev) => {
      if (prev.length <= 1) return prev;
      return prev.filter((_, i) => i !== idx);
    });
  };

  const totalWithIGV = round2(items.reduce((sum, item) => sum + item.line_total, 0));
  const { base: subtotal, igv: igvAmount, total } = calcIGV(totalWithIGV);
  const cashChange = paymentMethod === 'EFECTIVO' ? Math.max(0, cashReceived - total) : 0;
  const cashInsufficient = paymentMethod === 'EFECTIVO' && total > 0 && cashReceived < total;

  const buildPayload = () => {
    const values = form.getFieldsValue();
    const [docType, series] = (values.doc_type_series || '').split('|');
    return {
      doc_type: docType,
      series,
      client_id: values.client_id,
      warehouse_id: values.warehouse_id,
      trabajador_id: values.trabajador_id,
      payment_cond: values.payment_cond,
      max_discount_pct: values.max_discount_pct ?? 0,
      issue_date: values.issue_date ? dayjs(values.issue_date).format('YYYY-MM-DD') : null,
      payment_method: paymentMethod,
      cash_received: paymentMethod === 'EFECTIVO' ? cashReceived : null,
      cash_change: paymentMethod === 'EFECTIVO' ? cashChange : null,
      items: items
        .filter((item) => item.product_id)
        .map((item) => ({
          product_id: item.product_id,
          quantity: item.quantity,
          unit_price: item.unit_price,
          discount_pct: item.discount_pct,
          line_total: item.line_total,
        })),
    };
  };

  const handleSavePreVenta = async () => {
    if (savingRef.current) return;
    try {
      await form.validateFields();
    } catch {
      return;
    }
    const validItems = items.filter((item) => item.product_id);
    if (validItems.length === 0) {
      message.error('Agregue al menos un producto');
      return;
    }
    savingRef.current = true;
    setSaving(true);
    try {
      const payload = { ...buildPayload(), status: 'PREVENTA' };
      if (isEditing) {
        await updateSale(Number(id), payload);
        message.success('Preventa actualizada');
      } else {
        await createSale(payload);
        message.success('Preventa creada');
      }
      navigate('/sales/list');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      message.error(detail || 'Error al guardar la venta');
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  const handleFacturar = async () => {
    if (savingRef.current) return;
    try {
      await form.validateFields();
    } catch {
      return;
    }
    const validItems = items.filter((item) => item.product_id);
    if (validItems.length === 0) {
      message.error('Agregue al menos un producto');
      return;
    }
    savingRef.current = true;
    setSaving(true);
    try {
      let saleId: number;
      const payload = { ...buildPayload(), status: 'FACTURADO' };
      if (isEditing) {
        await updateSale(Number(id), payload);
        const result = await facturarSale(Number(id));
        saleId = Number(id);
        if ((result as any).sunat_status === 'ACEPTADO') {
          message.success('Venta facturada y aceptada por SUNAT');
        } else if ((result as any).sunat_status === 'ERROR') {
          message.warning('Venta facturada pero SUNAT devolvio error. Puede reintentar desde el panel SUNAT.');
        }
      } else {
        const created = await createSale(payload);
        try {
          const result = await facturarSale(created.id);
          saleId = created.id;
          // Check SUNAT status from facturar response
          if ((result as any).sunat_status === 'ACEPTADO') {
            message.success('Venta facturada y aceptada por SUNAT');
          } else if ((result as any).sunat_status === 'ERROR') {
            message.warning('Venta facturada pero SUNAT devolvio error. Puede reintentar desde el panel SUNAT.');
          } else if ((result as any).sunat_status) {
            message.info(`Venta facturada. Estado SUNAT: ${(result as any).sunat_status}`);
          }
        } catch (facturarErr) {
          // Facturar failed — delete the orphan PREVENTA
          try { await deleteSale(created.id); } catch { /* ignore */ }
          throw facturarErr;
        }
      }
      if (!saleId) message.success('Venta facturada');
      window.open(`/sales/${saleId}/print`, '_blank');
      navigate('/sales/list');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const sunatDesc = err?.response?.data?.sunat_description;
      const statusCode = err?.response?.status;
      const networkMsg = !err?.response ? `Error de conexión: ${err?.message || 'servidor no responde'}` : null;
      message.error(networkMsg || detail || sunatDesc || `Error al facturar (${statusCode || 'desconocido'})`, 10);
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  const handleEmitirNV = async () => {
    if (savingRef.current) return;
    try {
      await form.validateFields();
    } catch {
      return;
    }
    const validItems = items.filter((item) => item.product_id);
    if (validItems.length === 0) {
      message.error('Agregue al menos un producto');
      return;
    }
    savingRef.current = true;
    setSaving(true);
    try {
      let saleId: number;
      const payload = buildPayload();
      if (isEditing) {
        await updateSale(Number(id), payload);
        saleId = Number(id);
      } else {
        const created = await createSale(payload);
        saleId = created.id;
      }
      // Only call emitir if not already emitted
      if (!isEditing || existingSale?.status === 'PREVENTA') {
        await emitirNotaVenta(saleId);
      }
      message.success('Nota de Venta emitida');
      if (isAdmin) {
        window.open(`/sales/${saleId}/print`, '_blank');
      }
      navigate('/sales/list');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      message.error(detail || 'Error al emitir la Nota de Venta');
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  const handleEmitirProforma = async () => {
    if (savingRef.current) return;
    try {
      await form.validateFields();
    } catch {
      return;
    }
    const validItems = items.filter((item) => item.product_id);
    if (validItems.length === 0) {
      message.error('Agregue al menos un producto');
      return;
    }
    savingRef.current = true;
    setSaving(true);
    try {
      let saleId: number;
      const payload = buildPayload();
      if (isEditing) {
        await updateSale(Number(id), payload);
        saleId = Number(id);
      } else {
        const created = await createSale(payload);
        saleId = created.id;
      }
      // Only call emitir if not already emitted
      if (!isEditing || existingSale?.status === 'PREVENTA') {
        await emitirProforma(saleId);
      }
      message.success('Proforma emitida');
      if (isAdmin) {
        window.open(`/sales/${saleId}/print`, '_blank');
      }
      navigate('/sales/list');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      message.error(detail || 'Error al emitir la Proforma');
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  const seriesOptions = (docSeries ?? [])
    .filter((s) => s.is_active && s.doc_type !== 'NOTA_CREDITO')
    .map((s) => ({
      value: `${s.doc_type}|${s.series}`,
      label: `${{ BOLETA: 'BV', FACTURA: 'FT', NOTA_CREDITO: 'NC', NOTA_VENTA: 'NV', PROFORMA: 'PF' }[s.doc_type] || s.doc_type} / ${s.series}`,
    }));

  const maxDiscountPct = Form.useWatch('max_discount_pct', form) ?? 0;
  const docTypeSeries = Form.useWatch('doc_type_series', form) ?? '';
  const currentDocType = docTypeSeries.split('|')[0];

  const itemColumns = [
    {
      title: '#',
      width: 40,
      render: (_: unknown, __: unknown, idx: number) => idx + 1,
    },
    {
      title: 'Producto',
      key: 'product',
      width: 300,
      render: (_: unknown, record: LineItem, idx: number) => (
        <AutoComplete
          value={record.product_id ? `${record.product_code} - ${record.product_name}` : record.product_code || undefined}
          options={productOptions}
          onSearch={handleProductSearch}
          onSelect={(val: string) => handleProductSelect(val, idx)}
          onChange={(val: string) => {
            if (record.product_id) {
              // User is editing a selected product — clear it so they can search again
              const newItems = [...items];
              newItems[idx] = { ...newItems[idx], product_id: null, product_code: val || '', product_name: '', brand_name: null, presentation: null, unit_price: 0, wholesale_price: null, cost_price: null, stock: 0 };
              setItems(newItems);
              if (val && val.length >= 2) handleProductSearch(val);
            } else if (!val || val.trim() === '') {
              const newItems = [...items];
              newItems[idx] = { ...newItems[idx], product_code: '' };
              setItems(newItems);
            } else {
              const newItems = [...items];
              newItems[idx] = { ...newItems[idx], product_code: val };
              setItems(newItems);
            }
          }}
          allowClear
          placeholder="Buscar por codigo o nombre"
          popupMatchSelectWidth={500}
          style={{ width: '100%' }}
        />
      ),
    },
    {
      title: 'Marca',
      dataIndex: 'brand_name',
      key: 'brand_name',
      width: 90,
      render: (val: string | null) => val || '-',
    },
    {
      title: 'Presentacion',
      dataIndex: 'presentation',
      key: 'presentation',
      width: 90,
      render: (val: string | null) => val || '-',
    },
    {
      title: 'Stock',
      dataIndex: 'stock',
      key: 'stock',
      width: 70,
      align: 'center' as const,
      render: (val: number, record: LineItem) => {
        if (!record.product_id) return '-';
        const isLow = record.quantity > val;
        return (
          <Tag color={isLow ? 'red' : val <= 5 ? 'orange' : 'green'}>
            {val}
          </Tag>
        );
      },
    },
    {
      title: 'Cantidad',
      key: 'quantity',
      width: 100,
      render: (_: unknown, record: LineItem, idx: number) => {
        const exceedsStock = record.product_id !== null && record.quantity > record.stock;
        return (
          <InputNumber
            min={1}
            value={record.quantity}
            onChange={(val) => updateItem(idx, 'quantity', val ?? 1)}
            style={{
              width: '100%',
              backgroundColor: exceedsStock ? '#fffbe6' : undefined,
              borderColor: exceedsStock ? '#faad14' : undefined,
            }}
            status={exceedsStock ? 'warning' : undefined}
          />
        );
      },
    },
    {
      title: 'P.V.P',
      key: 'unit_price',
      width: 110,
      render: (_: unknown, record: LineItem, idx: number) => {
        const belowCost = record.cost_price != null && record.unit_price < record.cost_price;
        return (
          <span data-enter-add-row>
            <InputNumber
              min={record.cost_price ?? 0}
              step={0.01}
              value={record.unit_price}
              onChange={(val) => updateItem(idx, 'unit_price', val ?? 0)}
              style={{ width: '100%' }}
              prefix="S/"
              status={belowCost ? 'error' : undefined}
            />
          </span>
        );
      },
    },
    {
      title: 'P.May',
      dataIndex: 'wholesale_price',
      key: 'wholesale_price',
      width: 90,
      align: 'right' as const,
      render: (val: number | null) => val != null ? `S/ ${val.toFixed(2)}` : '-',
    },
    {
      title: 'Desc.%',
      key: 'discount_pct',
      width: 80,
      render: (_: unknown, record: LineItem, idx: number) => {
        const exceedsMax = maxDiscountPct > 0 && record.discount_pct > maxDiscountPct;
        return (
          <span data-enter-skip>
            <InputNumber
              min={0}
              max={100}
              value={record.discount_pct}
              onChange={(val) => updateItem(idx, 'discount_pct', val ?? 0)}
              style={{ width: '100%' }}
              status={exceedsMax ? 'error' : undefined}
            />
          </span>
        );
      },
    },
    {
      title: 'Total',
      key: 'line_total',
      width: 110,
      align: 'right' as const,
      render: (_: unknown, record: LineItem) => formatCurrency(record.line_total),
    },
    {
      title: '',
      key: 'actions',
      width: 50,
      render: (_: unknown, __: unknown, idx: number) => (
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={() => removeRow(idx)}
          disabled={items.length <= 1}
        />
      ),
    },
  ];

  if (isEditing && loadingSale) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div ref={enterNavRef}>
      <Title level={3}>{isEditing ? 'Editar Venta' : 'NUEVA PRE-VENTA'}</Title>

      <Form form={form} layout="vertical" initialValues={{ max_discount_pct: 0 }}>
        <Row gutter={16} data-enter-skip>
          <Col xs={24} sm={8} md={4}>
            <Form.Item
              name="doc_type_series"
              label="Tipo / Serie"
              rules={[{ required: true, message: 'Requerido' }]}
            >
              <Select
                placeholder="Seleccionar"
                options={seriesOptions}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8} md={5}>
            <Form.Item label="Cliente" required>
              <Space.Compact style={{ width: '100%' }}>
                <Form.Item
                  name="client_id"
                  noStyle
                  rules={[{ required: true, message: 'Requerido' }]}
                >
                  <Select
                    showSearch
                    filterOption={false}
                    onSearch={handleClientSearch}
                    options={clientOptions}
                    placeholder="Buscar cliente..."
                    popupMatchSelectWidth={400}
                    notFoundContent={clientSearch.length >= 2 ? 'Sin resultados' : 'Escriba para buscar'}
                    style={{ width: '100%' }}
                  />
                </Form.Item>
                <Button icon={<PlusOutlined />} onClick={() => { clientForm.resetFields(); setClientModalOpen(true); }} />
              </Space.Compact>
            </Form.Item>
          </Col>
          <Col xs={24} sm={8} md={3}>
            <Form.Item
              name="warehouse_id"
              label="Almacen"
              rules={[{ required: true, message: 'Requerido' }]}
            >
              <Select
                showSearch
                filterOption={tokenizedFilter}
                filterSort={(a, b, info) => tokenizedFilterSort(a, b, info)}
                placeholder="Seleccionar"
                options={warehouses?.map((w) => ({ value: w.id, label: w.name }))}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8} md={4}>
            <Form.Item
              name="trabajador_id"
              label="Vendedor"
              rules={[{ required: true, message: 'Requerido' }]}
            >
              <Select
                showSearch
                filterOption={tokenizedFilter}
                filterSort={(a, b, info) => tokenizedFilterSort(a, b, info)}
                placeholder="Seleccionar"
                options={trabajadores?.map((t) => ({ value: t.id, label: t.full_name }))}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8} md={4} data-enter-skip>
            <Form.Item
              name="payment_cond"
              label="Condicion de Pago"
              rules={[{ required: true, message: 'Requerido' }]}
            >
              <Select
                placeholder="Seleccionar"
                options={[
                  { value: 'CONTADO', label: 'Contado' },
                  { value: 'CREDITO_30', label: 'Credito 30 dias' },
                  { value: 'CREDITO_60', label: 'Credito 60 dias' },
                ]}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8} md={2} data-enter-skip>
            <Form.Item
              name="max_discount_pct"
              label="Max Dcto %"
            >
              <InputNumber min={0} max={100} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8} md={3} data-enter-skip>
            <Form.Item
              name="issue_date"
              label="Fecha"
              initialValue={dayjs()}
            >
              <DatePicker
                format="DD/MM/YYYY"
                style={{ width: '100%' }}
                disabled={!isAdmin || (isEditing && existingSale?.status !== 'PREVENTA')}
                allowClear={false}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8} md={2} data-enter-skip>
            <Form.Item label="Pago">
              <Radio.Group
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
                size="small"
              >
                <Radio.Button value="EFECTIVO">EFECT</Radio.Button>
                <Radio.Button value="TARJETA">TARJ</Radio.Button>
              </Radio.Group>
            </Form.Item>
          </Col>
        </Row>
      </Form>

      <Divider style={{ margin: '8px 0 16px' }} />

      <Row gutter={16}>
        <Col xs={24} lg={17}>
          <Table
            columns={itemColumns}
            dataSource={items}
            rowKey="key"
            pagination={false}
            size="small"
            scroll={{ x: 1100 }}
            rowClassName={(record: LineItem) => {
              if (record.product_id && record.quantity > record.stock) {
                return 'row-stock-warning';
              }
              return '';
            }}
            footer={() => (
              <Button type="dashed" onClick={addRow} icon={<PlusOutlined />} block>
                Agregar Producto
              </Button>
            )}
          />
        </Col>
        <Col xs={24} lg={7}>
          <Card
            size="small"
            title="Resumen"
            styles={{ header: { fontWeight: 600 } }}
          >
            <Row justify="space-between" style={{ marginBottom: 4 }}>
              <Text type="secondary">Op. Gravada:</Text>
              <Text>{formatCurrency(subtotal)}</Text>
            </Row>
            <Row justify="space-between" style={{ marginBottom: 4 }}>
              <Text type="secondary">IGV (18%):</Text>
              <Text>{formatCurrency(igvAmount)}</Text>
            </Row>
            <Divider style={{ margin: '8px 0' }} />
            <Row justify="space-between" style={{ marginBottom: 12 }}>
              <Text strong style={{ fontSize: 18 }}>TOTAL:</Text>
              <Text strong style={{ fontSize: 18 }}>{formatCurrency(total)}</Text>
            </Row>

            {paymentMethod === 'EFECTIVO' && (
              <>
                <Divider style={{ margin: '8px 0' }} />
                <Row justify="space-between" align="middle" style={{ marginBottom: 8 }}>
                  <Text>Efectivo:</Text>
                  <InputNumber
                    min={0}
                    step={0.5}
                    value={cashReceived}
                    onChange={(val) => setCashReceived(val ?? 0)}
                    style={{ width: 140 }}
                    prefix="S/"
                    size="middle"
                  />
                </Row>
                <Row justify="space-between" align="middle">
                  <Text>Vuelto:</Text>
                  <Text
                    strong
                    style={{
                      fontSize: 16,
                      color: cashReceived >= total ? '#52c41a' : '#ff4d4f',
                    }}
                  >
                    {formatCurrency(cashChange)}
                  </Text>
                </Row>
              </>
            )}

            {paymentMethod === 'TARJETA' && (
              <>
                <Divider style={{ margin: '8px 0' }} />
                <Row justify="center">
                  <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
                    PAGO CON TARJETA
                  </Tag>
                </Row>
              </>
            )}
          </Card>

          <div style={{ marginTop: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {currentDocType !== 'NOTA_VENTA' && currentDocType !== 'PROFORMA' && (
                <Button
                  icon={<SaveOutlined />}
                  onClick={handleSavePreVenta}
                  loading={saving}
                  disabled={!isAdmin && cashInsufficient}
                  block
                  size="large"
                >
                  Guardar como PreVenta
                </Button>
              )}
              {(currentDocType === 'NOTA_VENTA' || currentDocType === 'PROFORMA') && isEditing && (
                <Button
                  icon={<SaveOutlined />}
                  onClick={handleSavePreVenta}
                  loading={saving}
                  block
                  size="large"
                >
                  Guardar
                </Button>
              )}
              {currentDocType === 'NOTA_VENTA' && (
                <Button
                  ref={facturarRef}
                  type="primary"
                  icon={<CheckOutlined />}
                  onClick={handleEmitirNV}
                  loading={saving}
                  block
                  size="large"
                >
                  Emitir Nota de Venta
                </Button>
              )}
              {currentDocType === 'PROFORMA' && (
                <Button
                  ref={facturarRef}
                  type="primary"
                  icon={<CheckOutlined />}
                  onClick={handleEmitirProforma}
                  loading={saving}
                  block
                  size="large"
                >
                  Emitir Proforma
                </Button>
              )}
              {isAdmin && currentDocType !== 'NOTA_VENTA' && currentDocType !== 'PROFORMA' && (
                <Button
                  ref={facturarRef}
                  type="primary"
                  icon={<CheckOutlined />}
                  onClick={handleFacturar}
                  loading={saving}
                  disabled={cashInsufficient}
                  block
                  size="large"
                >
                  Facturar
                </Button>
              )}
              <Button onClick={() => navigate('/sales/list')} block>
                Cancelar
              </Button>
            </Space>
          </div>
        </Col>
      </Row>

      <style>{`
        .row-stock-warning td {
          background-color: #fffbe6 !important;
        }
      `}</style>

      <Modal
        title="Nuevo Cliente"
        open={clientModalOpen}
        onOk={handleCreateClient}
        onCancel={() => setClientModalOpen(false)}
        okText="Guardar"
        cancelText="Cancelar"
        confirmLoading={clientModalLoading}
        width={500}
        destroyOnClose
      >
        <div ref={clientEnterNavRef}>
        <Form form={clientForm} layout="vertical" style={{ marginTop: 16 }}>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="doc_type" label="Tipo Doc." rules={[{ required: true, message: 'Requerido' }]}>
                <Select placeholder="Seleccionar">
                  <Select.Option value="DNI">DNI</Select.Option>
                  <Select.Option value="RUC">RUC</Select.Option>
                  <Select.Option value="NONE">NINGUNO</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="doc_number" label="Nro. Documento">
                <Input />
              </Form.Item>
            </Col>
            <Col span={4} style={{ display: 'flex', alignItems: 'end', paddingBottom: 24 }}>
              <Button onClick={handleLookup} loading={lookupLoading} size="small">
                Buscar
              </Button>
            </Col>
          </Row>
          <Form.Item name="business_name" label="Nombre / Razón Social" rules={[{ required: true, message: 'Requerido' }]}>
            <Input />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="phone" label="Teléfono">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="email" label="Email">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="address" label="Dirección">
            <Input />
          </Form.Item>
        </Form>
        </div>
      </Modal>
    </div>
  );
}
