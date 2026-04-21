import { useState, useMemo } from 'react';
import {
  Table,
  Button,
  Input,
  Modal,
  Form,
  Select,
  InputNumber,
  Space,
  Tag,
  Typography,
  Row,
  Col,
  message,
  Popconfirm,
  Tabs,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, LoadingOutlined } from '@ant-design/icons';
import SearchInput from '../../components/SearchInput';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getClients, createClient, updateClient, deleteClient, lookupRUC, lookupDNI } from '../../api/clients';
import { useAuth } from '../../contexts/AuthContext';
import useEnterNavigation from '../../hooks/useEnterNavigation';
import useFuzzyFilter from '../../hooks/useFuzzyFilter';
import ubigeoData from '../../data/ubigeo.json';
import type { Client } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

function DireccionTab({ form }: { form: any }) {
  const dep = Form.useWatch('departamento', form);
  const prov = Form.useWatch('provincia', form);

  const depOptions = useMemo(
    () => ubigeoData.departamentos.map((d: any) => ({ value: d.name, label: d.name })),
    []
  );

  const provOptions = useMemo(() => {
    if (!dep) return [];
    const depEntry = ubigeoData.departamentos.find((d: any) => d.name === dep);
    if (!depEntry) return [];
    const provs = (ubigeoData.provincias as any)[depEntry.id] || [];
    return provs.map((p: any) => ({ value: p.name, label: p.name }));
  }, [dep]);

  const distOptions = useMemo(() => {
    if (!dep || !prov) return [];
    const depEntry = ubigeoData.departamentos.find((d: any) => d.name === dep);
    if (!depEntry) return [];
    const provs = (ubigeoData.provincias as any)[depEntry.id] || [];
    const provEntry = provs.find((p: any) => p.name === prov);
    if (!provEntry) return [];
    const dists = (ubigeoData.distritos as any)[provEntry.id] || [];
    return dists.map((d: any) => ({ value: d.name, label: d.name, ubigeo: d.id }));
  }, [dep, prov]);

  const handleDepChange = (val: string) => {
    form.setFieldsValue({ departamento: val, provincia: undefined, distrito: undefined, ubigeo: undefined, zona: undefined });
  };

  const handleProvChange = (val: string) => {
    form.setFieldsValue({ provincia: val, distrito: undefined, ubigeo: undefined, zona: undefined });
  };

  const handleDistChange = (val: string) => {
    const opt = distOptions.find((d: any) => d.value === val);
    form.setFieldsValue({ distrito: val, ubigeo: opt?.ubigeo || '', zona: val });
  };

  return (
    <>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item name="departamento" label="Departamento">
            <Select
              showSearch
              allowClear
              placeholder="Seleccionar"
              options={depOptions}
              onChange={handleDepChange}
              filterOption={(input, option) =>
                (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="provincia" label="Provincia">
            <Select
              showSearch
              allowClear
              placeholder="Seleccionar"
              options={provOptions}
              onChange={handleProvChange}
              disabled={!dep}
              filterOption={(input, option) =>
                (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="distrito" label="Distrito">
            <Select
              showSearch
              allowClear
              placeholder="Seleccionar"
              options={distOptions}
              onChange={handleDistChange}
              disabled={!prov}
              filterOption={(input, option) =>
                (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
        </Col>
      </Row>
      <Form.Item name="address" label="Direccion">
        <Input placeholder="Calle, Avenida, Jiron, etc." />
      </Form.Item>
      <Form.Item name="zona" label="Zona" tooltip="Se auto-completa con el distrito seleccionado">
        <Input />
      </Form.Item>
      <Form.Item name="ubigeo" hidden>
        <Input />
      </Form.Item>
    </>
  );
}

export default function ClientList() {
  const queryClient = useQueryClient();
  const { isAdmin } = useAuth();
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<Client | null>(null);
  const [activeTab, setActiveTab] = useState('datos');
  const [lookupLoading, setLookupLoading] = useState(false);
  const [form] = Form.useForm();
  const enterNavRef = useEnterNavigation(() => handleSubmit());

  const docType = Form.useWatch('doc_type', form);
  const docNumber = Form.useWatch('doc_number', form);

  const canLookup =
    (docType === 'RUC' && docNumber?.length === 11) ||
    (docType === 'DNI' && docNumber?.length === 8);

  const handleLookup = async () => {
    setLookupLoading(true);
    try {
      if (docType === 'RUC') {
        const result = await lookupRUC(docNumber);
        const fields: any = { business_name: result.business_name, address: result.address };
        // Auto-fill ubigeo fields from SUNAT response
        if (result.departamento) fields.departamento = result.departamento;
        if (result.provincia) fields.provincia = result.provincia;
        if (result.distrito) {
          fields.distrito = result.distrito;
          fields.zona = result.distrito;
        }
        form.setFieldsValue(fields);
      } else {
        const result = await lookupDNI(docNumber);
        form.setFieldsValue({ business_name: result.business_name });
      }
      message.success('Datos obtenidos correctamente');
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Error al consultar';
      message.error(detail);
    } finally {
      setLookupLoading(false);
    }
  };

  const { data: allClients, isLoading } = useQuery({
    queryKey: ['clients'],
    queryFn: () => getClients(),
    refetchInterval: 30_000,
  });

  const clients = useFuzzyFilter(allClients ?? [], search, (c) =>
    `${c.business_name} ${c.doc_number || ''} ${c.zona || ''}`
  );

  const createMutation = useMutation({
    mutationFn: createClient,
    onSuccess: () => {
      message.success('Cliente creado');
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      closeModal();
    },
    onError: () => message.error('Error al crear cliente'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => updateClient(id, data),
    onSuccess: () => {
      message.success('Cliente actualizado');
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      closeModal();
    },
    onError: () => message.error('Error al actualizar cliente'),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteClient,
    onSuccess: () => {
      message.success('Cliente eliminado');
      queryClient.invalidateQueries({ queryKey: ['clients'] });
    },
    onError: () => message.error('Error al eliminar cliente'),
  });

  const openCreate = () => {
    setEditingClient(null);
    form.resetFields();
    setActiveTab('datos');
    setModalOpen(true);
  };

  const openEdit = (client: Client) => {
    setEditingClient(client);
    form.setFieldsValue({
      doc_type: client.doc_type,
      doc_number: client.doc_number,
      business_name: client.business_name,
      ref_comercial: client.ref_comercial,
      phone: client.phone,
      email: client.email,
      comentario: client.comentario,
      address: client.address,
      departamento: client.departamento,
      provincia: client.provincia,
      distrito: client.distrito,
      ubigeo: client.ubigeo,
      zona: client.zona,
      credit_limit: client.credit_limit,
      credit_days: client.credit_days,
    });
    setActiveTab('datos');
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingClient(null);
    form.resetFields();
    setActiveTab('datos');
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingClient) {
        updateMutation.mutate({ id: editingClient.id, data: values });
      } else {
        createMutation.mutate(values);
      }
    } catch {
      // validation failed — switch to the tab that has the error
      try {
        await form.validateFields(['doc_type', 'business_name']);
      } catch {
        setActiveTab('datos');
        return;
      }
    }
  };

  const columns: ColumnsType<Client> = [
    {
      title: 'Tipo Doc',
      dataIndex: 'doc_type',
      key: 'doc_type',
      width: 90,
    },
    {
      title: 'Nro Doc',
      dataIndex: 'doc_number',
      key: 'doc_number',
      width: 120,
      render: (v) => v || '-',
    },
    {
      title: 'Razon Social',
      dataIndex: 'business_name',
      key: 'business_name',
      ellipsis: true,
    },
    {
      title: 'Direccion',
      dataIndex: 'address',
      key: 'address',
      ellipsis: true,
      render: (v) => v || '-',
    },
    {
      title: 'Telefono',
      dataIndex: 'phone',
      key: 'phone',
      width: 120,
      render: (v) => v || '-',
    },
    {
      title: 'Zona',
      dataIndex: 'zona',
      key: 'zona',
      width: 120,
      render: (v) => v || '-',
    },
    {
      title: 'Estado',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>{active ? 'Activo' : 'Inactivo'}</Tag>
      ),
    },
    ...(isAdmin
      ? [
          {
            title: 'Acciones',
            key: 'actions',
            width: 100,
            render: (_: unknown, record: Client) => (
              <Space size="small">
                <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
                <Popconfirm
                  title="Eliminar cliente?"
                  onConfirm={() => deleteMutation.mutate(record.id)}
                  okText="Si"
                  cancelText="No"
                >
                  <Button type="link" size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </Space>
            ),
          },
        ]
      : []),
  ];

  const tabItems = [
    {
      key: 'datos',
      label: 'Datos Personales',
      children: (
        <>
          <Row gutter={16}>
            <Col span={10}>
              <Form.Item
                name="doc_type"
                label="Tipo Documento"
                rules={[{ required: true, message: 'Requerido' }]}
              >
                <Select
                  placeholder="Seleccionar"
                  options={[
                    { value: 'DNI', label: 'DNI' },
                    { value: 'RUC', label: 'RUC' },
                    { value: 'NONE', label: 'Sin documento' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={14}>
              <Form.Item name="doc_number" label="Nro Documento">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          {docType && docType !== 'NONE' && (
            <Form.Item>
              <Button
                type="default"
                icon={lookupLoading ? <LoadingOutlined /> : <SearchOutlined />}
                onClick={handleLookup}
                disabled={!canLookup || lookupLoading}
                loading={lookupLoading}
                size="small"
              >
                {docType === 'RUC' ? 'Consultar SUNAT' : 'Consultar RENIEC'}
              </Button>
            </Form.Item>
          )}
          <Form.Item
            name="business_name"
            label="Razon Social / Nombre"
            rules={[{ required: true, message: 'Requerido' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="ref_comercial" label="Ref. Comercial">
            <Input />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="phone" label="Telefono">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="email" label="Email">
                <Input type="email" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="comentario" label="Comentario">
            <Input.TextArea rows={3} />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'direccion',
      label: 'Direccion',
      children: <DireccionTab form={form} />,
    },
    {
      key: 'credito',
      label: 'Credito',
      children: (
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="credit_limit" label="Limite de Credito">
              <InputNumber
                prefix="S/"
                style={{ width: '100%' }}
                min={0}
                precision={2}
                placeholder="0.00"
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="credit_days" label="Dias de Credito">
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                precision={0}
                placeholder="0"
              />
            </Form.Item>
          </Col>
        </Row>
      ),
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>Clientes</Title>
        </Col>
        <Col>
          <Space>
            <SearchInput
              value={search}
              onChange={setSearch}
              suggestion={clients.length > 0 ? clients[0].business_name : undefined}
              placeholder="Buscar clientes..."
              style={{ width: 250 }}
              autoFocus
            />
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              Nuevo Cliente
            </Button>
          </Space>
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={clients ?? []}
        rowKey="id"
        loading={isLoading}
        size="small"
        scroll={{ x: 900 }}
        pagination={{ pageSize: 20, showSizeChanger: true }}
      />

      <Modal
        title={editingClient ? 'Editar Cliente' : 'Nuevo Cliente'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={closeModal}
        okText="Guardar"
        cancelText="Cancelar"
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={600}
        destroyOnClose
      >
        <div ref={enterNavRef}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
        </Form>
        </div>
      </Modal>
    </div>
  );
}
