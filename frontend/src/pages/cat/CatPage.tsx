import { useState } from 'react';
import {
  Typography, Tabs, Card, Input, Button, Form, Row, Col, Tag, Table, Space,
  Statistic, Spin, message, Descriptions, Empty, Badge, Modal, Switch, Select, InputNumber,
} from 'antd';
import {
  SearchOutlined, CarOutlined, UserOutlined, PhoneOutlined,
  PrinterOutlined, WarningOutlined, CheckCircleOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  lookupPlaca, lookupDni, createCatSale, listCatSales, getRenewals,
  type PlacaLookup, type DniLookup,
} from '../../api/cat';
import { formatCurrency } from '../../utils/format';

const { Title, Text } = Typography;

export default function CatPage() {
  const queryClient = useQueryClient();

  // Sale form state
  const [placa, setPlaca] = useState('');
  const [dni, setDni] = useState('');
  const [vehicleData, setVehicleData] = useState<PlacaLookup | null>(null);
  const [customerData, setCustomerData] = useState<DniLookup | null>(null);
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [customerAddress, setCustomerAddress] = useState('');
  const [paradero, setParadero] = useState('');
  const [colorVeh, setColorVeh] = useState('');
  const [distrito, setDistrito] = useState('');
  const [medioPago, setMedioPago] = useState('Efectivo');
  const [montoEfectivo, setMontoEfectivo] = useState(0);
  const [montoDigital, setMontoDigital] = useState(0);
  const [loadingPlaca, setLoadingPlaca] = useState(false);
  const [loadingDni, setLoadingDni] = useState(false);
  const [notes, setNotes] = useState('');
  const [testMode, setTestMode] = useState(false);

  // Queries
  const { data: sales, isLoading: salesLoading } = useQuery({
    queryKey: ['cat-sales'],
    queryFn: listCatSales,
    refetchInterval: 30_000,
  });

  const { data: renewals } = useQuery({
    queryKey: ['cat-renewals'],
    queryFn: () => getRenewals(30),
    refetchInterval: 60_000,
  });

  const saveMutation = useMutation({
    mutationFn: createCatSale,
    onSuccess: (saved) => {
      message.success('CAT registrado exitosamente');
      queryClient.invalidateQueries({ queryKey: ['cat-sales'] });
      queryClient.invalidateQueries({ queryKey: ['cat-renewals'] });
      // Open print page
      window.open(`/cat/${saved.id}/print`, '_blank');
      resetForm();
    },
    onError: () => message.error('Error al registrar CAT'),
  });

  const resetForm = () => {
    setPlaca('');
    setDni('');
    setVehicleData(null);
    setCustomerData(null);
    setCustomerName('');
    setCustomerPhone('');
    setCustomerAddress('');
    setParadero('');
    setColorVeh('');
    setDistrito('');
    setMedioPago('Efectivo');
    setMontoEfectivo(0);
    setMontoDigital(0);
    setNotes('');
  };

  const handleSearchPlaca = async () => {
    if (!placa.trim()) return;
    setLoadingPlaca(true);
    try {
      const result = await lookupPlaca(placa.trim());
      setVehicleData(result);
      if (result.found) {
        setMontoEfectivo(result.precio_total);
        setMontoDigital(0);
        setMedioPago('Efectivo');
      } else {
        message.warning(result.error || 'Vehiculo no encontrado');
      }
    } catch {
      message.error('Error al buscar placa');
    } finally {
      setLoadingPlaca(false);
    }
  };

  const handleSearchDni = async () => {
    if (!dni.trim()) return;
    setLoadingDni(true);
    try {
      const result = await lookupDni(dni.trim());
      setCustomerData(result);
      if (result.found) {
        setCustomerName(result.full_name);
        if (result.telefono) setCustomerPhone(result.telefono);
        if (result.direccion) setCustomerAddress(result.direccion);
      } else {
        message.warning('Cliente no encontrado en AFOCAT — ingrese datos manualmente');
      }
    } catch {
      message.error('Error al buscar DNI');
    } finally {
      setLoadingDni(false);
    }
  };

  const handleSave = () => {
    if (!vehicleData?.found) {
      message.error('Primero busque la placa del vehiculo');
      return;
    }
    if (!customerName.trim()) {
      message.error('Ingrese el nombre del cliente');
      return;
    }
    if (!dni.trim()) {
      message.error('Ingrese el DNI del cliente');
      return;
    }
    if (!customerAddress.trim()) {
      message.error('Ingrese la direccion del cliente');
      return;
    }

    if (testMode) {
      Modal.confirm({
        title: 'MODO PRUEBA — Simular Venta',
        content: (
          <div>
            <p>Se guardara localmente SIN emitir en AFOCAT:</p>
            <p><strong>Placa:</strong> {vehicleData.placa}</p>
            <p><strong>Cliente:</strong> {customerName}</p>
            <p><strong>Total:</strong> S/ {vehicleData.precio_total}</p>
            <p style={{ color: '#52c41a', marginTop: 12 }}>Modo prueba — no se creara certificado real.</p>
          </div>
        ),
        okText: 'Guardar Prueba',
        cancelText: 'Cancelar',
        onOk: doSell,
      });
    } else {
      Modal.confirm({
        title: 'Confirmar Venta de CAT',
        content: (
          <div>
            <p>Se emitira un certificado real en AFOCAT para:</p>
            <p><strong>Placa:</strong> {vehicleData.placa}</p>
            <p><strong>Cliente:</strong> {customerName}</p>
            <p><strong>Total:</strong> S/ {vehicleData.precio_total}</p>
            <p style={{ color: '#faad14', marginTop: 12 }}>Esta accion no se puede deshacer.</p>
          </div>
        ),
        okText: 'Emitir CAT',
        cancelText: 'Cancelar',
        okType: 'primary',
        onOk: doSell,
      });
    }
  };

  const doSell = () => {
    if (!vehicleData?.found) return;

    // Split customer name into parts for AFOCAT API
    const nameParts = customerName.trim().split(' ');
    const ap_paterno = nameParts[0] || '';
    const ap_materno = nameParts[1] || '';
    const nom_razon = nameParts.slice(2).join(' ') || '';

    saveMutation.mutate({
      placa: vehicleData.placa,
      marca: vehicleData.marca,
      modelo: vehicleData.modelo,
      año: vehicleData.año,
      serie_vehiculo: vehicleData.serie,
      asientos: vehicleData.asientos,
      categoria: vehicleData.categoria,
      clase: vehicleData.clase,
      uso: vehicleData.uso,
      idn_tecnica: vehicleData.n_tecnica,
      customer_name: customerName.trim(),
      ap_paterno,
      ap_materno,
      nom_razon,
      customer_dni: dni,
      customer_phone: customerPhone,
      customer_address: customerAddress,
      paradero,
      color_veh: colorVeh,
      precio: vehicleData.precio,
      ap_extra: vehicleData.ap_extra,
      total: vehicleData.precio_total,
      medio_pago: medioPago,
      monto_efectivo: montoEfectivo,
      monto_digital: montoDigital,
      emit_in_afocat: !testMode,
      notes,
    });
  };

  const renewalCount = renewals?.length ?? 0;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          <CarOutlined style={{ marginRight: 8 }} />
          CAT / AFOCAT
          {testMode && <Tag color="orange" style={{ marginLeft: 8, verticalAlign: 'middle' }}>MODO PRUEBA</Tag>}
        </Title>
        <Space>
          <span style={{ fontSize: 12, opacity: 0.5 }}>Modo prueba</span>
          <Switch checked={testMode} onChange={setTestMode} size="small" />
        </Space>
      </div>

      <Tabs
        defaultActiveKey="new"
        items={[
          {
            key: 'new',
            label: 'Nueva Venta',
            children: (
              <Row gutter={24}>
                {/* Left: Form */}
                <Col span={14}>
                  {/* Vehicle lookup */}
                  <Card size="small" title="Datos del Vehiculo" style={{ marginBottom: 16 }}>
                    <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
                      <Input
                        prefix={<CarOutlined />}
                        placeholder="Placa (ej: 2230-1D)"
                        value={placa}
                        onChange={(e) => setPlaca(e.target.value.toUpperCase())}
                        onPressEnter={handleSearchPlaca}
                        style={{ width: '70%' }}
                      />
                      <Button
                        type="primary"
                        icon={<SearchOutlined />}
                        loading={loadingPlaca}
                        onClick={handleSearchPlaca}
                      >
                        Buscar
                      </Button>
                    </Space.Compact>

                    {vehicleData?.found && (
                      <Descriptions size="small" column={2} bordered>
                        <Descriptions.Item label="Placa">{vehicleData.placa}</Descriptions.Item>
                        <Descriptions.Item label="Categoria/Clase">
                          {vehicleData.categoria} / {vehicleData.clase}
                        </Descriptions.Item>
                        <Descriptions.Item label="Marca">{vehicleData.marca}</Descriptions.Item>
                        <Descriptions.Item label="Modelo">{vehicleData.modelo}</Descriptions.Item>
                        <Descriptions.Item label="Año">{vehicleData.año}</Descriptions.Item>
                        <Descriptions.Item label="Asientos">{vehicleData.asientos}</Descriptions.Item>
                        <Descriptions.Item label="Serie/VIN" span={2}>{vehicleData.serie}</Descriptions.Item>
                        <Descriptions.Item label="Uso" span={2}>{vehicleData.uso}</Descriptions.Item>
                        <Descriptions.Item label="AFOCAT Vigente">
                          {vehicleData.vigente ? (
                            <Tag color="green" icon={<CheckCircleOutlined />}>
                              Vigente ({vehicleData.vigencia_dias} dias)
                            </Tag>
                          ) : (
                            <Tag color="red" icon={<WarningOutlined />}>
                              Vencido
                            </Tag>
                          )}
                        </Descriptions.Item>
                      </Descriptions>
                    )}
                  </Card>

                  {/* Customer lookup */}
                  <Card size="small" title="Datos del Cliente" style={{ marginBottom: 16 }}>
                    <Space.Compact style={{ width: '100%', marginBottom: 8 }}>
                      <Input
                        prefix={<UserOutlined />}
                        placeholder="* DNI (8 digitos)"
                        value={dni}
                        onChange={(e) => setDni(e.target.value)}
                        onPressEnter={handleSearchDni}
                        maxLength={8}
                        style={{ width: '70%' }}
                      />
                      <Button
                        icon={<SearchOutlined />}
                        loading={loadingDni}
                        onClick={handleSearchDni}
                      >
                        Buscar
                      </Button>
                    </Space.Compact>

                    <Input
                      placeholder="* Nombres y/o Razon Social"
                      value={customerName}
                      onChange={(e) => setCustomerName(e.target.value)}
                      style={{ marginBottom: 8 }}
                    />

                    <Row gutter={8} style={{ marginBottom: 8 }}>
                      <Col span={12}>
                        <Input
                          prefix={<PhoneOutlined />}
                          placeholder="Telefono"
                          value={customerPhone}
                          onChange={(e) => setCustomerPhone(e.target.value)}
                        />
                      </Col>
                      <Col span={12}>
                        <Input
                          placeholder="Paradero"
                          value={paradero}
                          onChange={(e) => setParadero(e.target.value)}
                        />
                      </Col>
                    </Row>

                    <Row gutter={8} style={{ marginBottom: 8 }}>
                      <Col span={16}>
                        <Input
                          placeholder="* Direccion"
                          value={customerAddress}
                          onChange={(e) => setCustomerAddress(e.target.value)}
                        />
                      </Col>
                      <Col span={8}>
                        <Input
                          placeholder="Distrito"
                          value={distrito}
                          onChange={(e) => setDistrito(e.target.value)}
                        />
                      </Col>
                    </Row>
                  </Card>

                  {/* Vehicle extras */}
                  <Card size="small" title="Datos Adicionales" style={{ marginBottom: 16 }}>
                    <Row gutter={8} style={{ marginBottom: 8 }}>
                      <Col span={8}>
                        <Input
                          placeholder="Color vehiculo"
                          value={colorVeh}
                          onChange={(e) => setColorVeh(e.target.value)}
                        />
                      </Col>
                      <Col span={8}>
                        <Select
                          placeholder="Medio de pago"
                          value={medioPago}
                          onChange={(v) => {
                            setMedioPago(v);
                            const total = vehicleData?.precio_total ?? 0;
                            if (v === 'Efectivo') { setMontoEfectivo(total); setMontoDigital(0); }
                            else if (v === 'YAPE' || v === 'PLIN' || v === 'Transferencia') { setMontoEfectivo(0); setMontoDigital(total); }
                          }}
                          style={{ width: '100%' }}
                          options={[
                            { value: 'Efectivo', label: 'Efectivo' },
                            { value: 'YAPE', label: 'YAPE' },
                            { value: 'PLIN', label: 'PLIN' },
                            { value: 'Transferencia', label: 'Transferencia' },
                          ]}
                        />
                      </Col>
                      <Col span={8}>
                        <InputNumber
                          placeholder={medioPago === 'Efectivo' ? 'Monto efectivo' : 'Monto digital'}
                          value={medioPago === 'Efectivo' ? montoEfectivo : montoDigital}
                          onChange={(v) => {
                            if (medioPago === 'Efectivo') setMontoEfectivo(v ?? 0);
                            else setMontoDigital(v ?? 0);
                          }}
                          prefix="S/"
                          style={{ width: '100%' }}
                        />
                      </Col>
                    </Row>
                  </Card>

                  <Input.TextArea
                    placeholder="Notas (opcional)"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={2}
                    style={{ marginBottom: 16 }}
                  />
                </Col>

                {/* Right: Summary + Actions */}
                <Col span={10}>
                  <Card size="small" title="Resumen" style={{ marginBottom: 16 }}>
                    {vehicleData?.found ? (
                      <>
                        <Statistic
                          title="Placa"
                          value={vehicleData.placa}
                          style={{ marginBottom: 16 }}
                        />
                        <Row gutter={16}>
                          <Col span={12}>
                            <Statistic title="Precio" value={vehicleData.precio} prefix="S/" />
                          </Col>
                          <Col span={12}>
                            <Statistic title="Aporte Extra" value={vehicleData.ap_extra} prefix="S/" />
                          </Col>
                        </Row>
                        <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', marginTop: 16, paddingTop: 16 }}>
                          <Statistic
                            title="TOTAL"
                            value={vehicleData.precio_total}
                            prefix="S/"
                            valueStyle={{ fontSize: 28, fontWeight: 'bold' }}
                          />
                        </div>
                      </>
                    ) : (
                      <div style={{ textAlign: 'center', padding: 32, opacity: 0.3 }}>
                        Busque una placa para ver el resumen
                      </div>
                    )}
                  </Card>

                  <Button
                    type="primary"
                    size="large"
                    block
                    icon={<PrinterOutlined />}
                    disabled={!vehicleData?.found}
                    loading={saveMutation.isPending}
                    onClick={handleSave}
                    style={{ height: 48, marginBottom: 8, background: testMode ? '#faad14' : undefined }}
                  >
                    {testMode ? 'Prueba — Guardar sin emitir' : 'Registrar CAT'}
                  </Button>
                  <Button block onClick={resetForm}>
                    Limpiar
                  </Button>
                </Col>
              </Row>
            ),
          },
          {
            key: 'history',
            label: `Historial (${sales?.length ?? 0})`,
            children: salesLoading ? (
              <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
            ) : (
              <Table
                dataSource={sales}
                rowKey="id"
                size="small"
                pagination={{ pageSize: 20, showSizeChanger: true }}
                columns={[
                  {
                    title: 'Fecha',
                    dataIndex: 'created_at',
                    key: 'created_at',
                    width: 100,
                    render: (v: string) => new Date(v).toLocaleDateString('es-PE'),
                  },
                  { title: 'Placa', dataIndex: 'placa', key: 'placa', width: 90 },
                  {
                    title: 'Vehiculo',
                    key: 'vehiculo',
                    render: (_: unknown, r: any) => `${r.marca || ''} ${r.modelo || ''}`.trim() || '-',
                  },
                  { title: 'Cliente', dataIndex: 'customer_name', key: 'customer_name', ellipsis: true },
                  { title: 'DNI', dataIndex: 'customer_dni', key: 'customer_dni', width: 90 },
                  { title: 'Telefono', dataIndex: 'customer_phone', key: 'customer_phone', width: 100 },
                  {
                    title: 'Total',
                    dataIndex: 'total',
                    key: 'total',
                    width: 90,
                    align: 'right',
                    render: (v: number | null) => v != null ? formatCurrency(v) : '-',
                  },
                  {
                    title: 'Estado',
                    dataIndex: 'status',
                    key: 'status',
                    width: 90,
                    render: (v: string) => (
                      <Tag color={v === 'VENDIDO' ? 'green' : 'red'}>{v}</Tag>
                    ),
                  },
                  {
                    title: 'Cert #',
                    dataIndex: 'certificate_number',
                    key: 'certificate_number',
                    width: 140,
                    render: (v: string | null) => v ? <Tag color="green">{v}</Tag> : <Tag color="orange">TEST</Tag>,
                  },
                  {
                    title: '',
                    key: 'actions',
                    width: 80,
                    render: (_: unknown, r: any) => (
                      <Space size="small">
                        <Button
                          type="link"
                          size="small"
                          icon={<PrinterOutlined />}
                          onClick={() => window.open(`/cat/${r.id}/print`, '_blank')}
                          title="Imprimir"
                        />
                        {r.certificate_number && (
                          <Button
                            type="link"
                            size="small"
                            icon={<CheckCircleOutlined />}
                            onClick={() => {
                              window.open(
                                `https://syserp.afocatpiura.com/mPDF/REPORTES/CAT/${r.certificate_number}.pdf`,
                                '_blank'
                              );
                            }}
                            title="Verificar en AFOCAT"
                            style={{ color: '#52c41a' }}
                          />
                        )}
                      </Space>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: 'renewals',
            label: (
              <span>
                Renovaciones{' '}
                {renewalCount > 0 && <Badge count={renewalCount} size="small" offset={[4, -2]} />}
              </span>
            ),
            children: (
              <>
                {!renewals?.length ? (
                  <Empty description="No hay renovaciones pendientes en los proximos 30 dias" />
                ) : (
                  <>
                    <div style={{ marginBottom: 16, padding: '8px 16px', borderRadius: 8, background: 'rgba(251, 191, 36, 0.1)', border: '1px solid rgba(251, 191, 36, 0.2)' }}>
                      <Text style={{ color: '#fbbf24' }}>
                        {renewalCount} clientes con CAT por vencer en los proximos 30 dias — llamar para renovar
                      </Text>
                    </div>
                    <Table
                      dataSource={renewals}
                      rowKey="id"
                      size="small"
                      pagination={false}
                      columns={[
                        { title: 'Placa', dataIndex: 'placa', key: 'placa', width: 90 },
                        { title: 'Cliente', dataIndex: 'customer_name', key: 'customer_name', ellipsis: true },
                        {
                          title: 'Telefono',
                          dataIndex: 'customer_phone',
                          key: 'customer_phone',
                          width: 120,
                          render: (v: string | null) => v ? (
                            <a href={`tel:${v}`}><PhoneOutlined /> {v}</a>
                          ) : '-',
                        },
                        { title: 'Vence', dataIndex: 'fecha_hasta', key: 'fecha_hasta', width: 100 },
                        {
                          title: 'Dias',
                          dataIndex: 'days_left',
                          key: 'days_left',
                          width: 70,
                          render: (v: number) => (
                            <Tag color={v <= 7 ? 'red' : v <= 14 ? 'orange' : 'blue'}>
                              {v}d
                            </Tag>
                          ),
                        },
                      ]}
                    />
                  </>
                )}
              </>
            ),
          },
        ]}
      />
    </div>
  );
}
