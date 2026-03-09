import { useState } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Space,
  Tag,
  Typography,
  Row,
  Col,
  message,
  Popconfirm,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, KeyOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getUsers, createUser, updateUser, deleteUser, changePassword } from '../../api/users';
import type { User } from '../../types';
import type { ColumnsType } from 'antd/es/table';
import useEnterNavigation from '../../hooks/useEnterNavigation';

const { Title } = Typography;

export default function UserList() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [passwordUserId, setPasswordUserId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [passwordForm] = Form.useForm();
  const enterNavRef = useEnterNavigation(() => handleSubmit());
  const passwordEnterNavRef = useEnterNavigation(() => handlePasswordChange());

  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: getUsers,
  });

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      message.success('Usuario creado');
      queryClient.invalidateQueries({ queryKey: ['users'] });
      closeModal();
    },
    onError: () => message.error('Error al crear usuario'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => updateUser(id, data),
    onSuccess: () => {
      message.success('Usuario actualizado');
      queryClient.invalidateQueries({ queryKey: ['users'] });
      closeModal();
    },
    onError: () => message.error('Error al actualizar usuario'),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => {
      message.success('Usuario eliminado');
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: () => message.error('Error al eliminar usuario'),
  });

  const passwordMutation = useMutation({
    mutationFn: ({ id, password }: { id: number; password: string }) => changePassword(id, password),
    onSuccess: () => {
      message.success('Contrasena actualizada');
      setPasswordModalOpen(false);
      passwordForm.resetFields();
    },
    onError: () => message.error('Error al cambiar contrasena'),
  });

  const openCreate = () => {
    setEditingUser(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (user: User) => {
    setEditingUser(user);
    form.setFieldsValue({
      username: user.username,
      full_name: user.full_name,
      role: user.role,
    });
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingUser(null);
    form.resetFields();
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingUser) {
        const { password: _pwd, ...updateData } = values;
        updateMutation.mutate({ id: editingUser.id, data: updateData });
      } else {
        createMutation.mutate(values);
      }
    } catch {
      // validation failed
    }
  };

  const handlePasswordChange = async () => {
    try {
      const values = await passwordForm.validateFields();
      if (passwordUserId) {
        passwordMutation.mutate({ id: passwordUserId, password: values.new_password });
      }
    } catch {
      // validation failed
    }
  };

  const columns: ColumnsType<User> = [
    { title: 'Usuario', dataIndex: 'username', key: 'username', width: 150 },
    { title: 'Nombre', dataIndex: 'full_name', key: 'full_name', ellipsis: true },
    {
      title: 'Rol',
      dataIndex: 'role',
      key: 'role',
      width: 100,
      render: (role: string) => (
        <Tag color={role === 'ADMIN' ? 'purple' : 'blue'}>{role}</Tag>
      ),
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
    {
      title: 'Acciones',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: User) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          <Button
            type="link"
            size="small"
            icon={<KeyOutlined />}
            onClick={() => {
              setPasswordUserId(record.id);
              passwordForm.resetFields();
              setPasswordModalOpen(true);
            }}
          />
          <Popconfirm
            title="Desactivar usuario?"
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="Si"
            cancelText="No"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>Usuarios</Title>
        </Col>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nuevo Usuario
          </Button>
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={users ?? []}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={false}
      />

      <Modal
        title={editingUser ? 'Editar Usuario' : 'Nuevo Usuario'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={closeModal}
        okText="Guardar"
        cancelText="Cancelar"
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <div ref={enterNavRef}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="username" label="Usuario" rules={[{ required: true, message: 'Requerido' }]}>
            <Input disabled={!!editingUser} />
          </Form.Item>
          {!editingUser && (
            <Form.Item name="password" label="Contrasena" rules={[{ required: true, message: 'Requerido' }]}>
              <Input.Password />
            </Form.Item>
          )}
          <Form.Item name="full_name" label="Nombre Completo" rules={[{ required: true, message: 'Requerido' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="Rol" rules={[{ required: true, message: 'Requerido' }]}>
            <Select
              placeholder="Seleccionar"
              options={[
                { value: 'ADMIN', label: 'Administrador' },
                { value: 'VENTAS', label: 'Ventas' },
              ]}
            />
          </Form.Item>
        </Form>
        </div>
      </Modal>

      <Modal
        title="Cambiar Contrasena"
        open={passwordModalOpen}
        onOk={handlePasswordChange}
        onCancel={() => { setPasswordModalOpen(false); passwordForm.resetFields(); }}
        okText="Cambiar"
        cancelText="Cancelar"
        confirmLoading={passwordMutation.isPending}
      >
        <div ref={passwordEnterNavRef}>
        <Form form={passwordForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="new_password"
            label="Nueva Contrasena"
            rules={[
              { required: true, message: 'Requerido' },
              { min: 6, message: 'Minimo 6 caracteres' },
            ]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            name="confirm_password"
            label="Confirmar Contrasena"
            dependencies={['new_password']}
            rules={[
              { required: true, message: 'Requerido' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('Las contrasenas no coinciden'));
                },
              }),
            ]}
          >
            <Input.Password />
          </Form.Item>
        </Form>
        </div>
      </Modal>
    </div>
  );
}
