import { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Select,
  Input,
  Tag,
  Typography,
  Row,
  Col,
  DatePicker,
  TimePicker,
  message,
} from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getActiveTrabajadores, getAsistencia, bulkMarkAsistencia } from '../../api/trabajadores';
import type { Trabajador, Asistencia } from '../../types';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Title } = Typography;

interface AttendanceRow {
  trabajador_id: number;
  trabajador_name: string;
  check_in_time: string | null;
  check_out_time: string | null;
  status: string;
  notes: string | null;
  existing_id?: number;
}

const STATUS_OPTIONS = [
  { value: 'PRESENTE', label: 'Presente' },
  { value: 'TARDANZA', label: 'Tardanza' },
  { value: 'AUSENTE', label: 'Ausente' },
];

const STATUS_COLORS: Record<string, string> = {
  PRESENTE: 'green',
  TARDANZA: 'orange',
  AUSENTE: 'red',
};

export default function AsistenciaPage() {
  const queryClient = useQueryClient();
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [rows, setRows] = useState<AttendanceRow[]>([]);

  const fechaStr = selectedDate.format('YYYY-MM-DD');

  const { data: trabajadores } = useQuery({
    queryKey: ['trabajadores-active'],
    queryFn: getActiveTrabajadores,
  });

  const { data: asistencia, isLoading } = useQuery({
    queryKey: ['asistencia', fechaStr],
    queryFn: () => getAsistencia(fechaStr),
  });

  // Build rows when data changes
  useEffect(() => {
    if (!trabajadores) return;
    const asistMap = new Map<number, Asistencia>();
    (asistencia ?? []).forEach((a) => asistMap.set(a.trabajador_id, a));

    const newRows: AttendanceRow[] = trabajadores.map((t: Trabajador) => {
      const existing = asistMap.get(t.id);
      return {
        trabajador_id: t.id,
        trabajador_name: t.full_name,
        check_in_time: existing?.check_in_time ?? null,
        check_out_time: existing?.check_out_time ?? null,
        status: existing?.status ?? 'PRESENTE',
        notes: existing?.notes ?? null,
        existing_id: existing?.id,
      };
    });
    setRows(newRows);
  }, [trabajadores, asistencia]);

  const updateRow = (idx: number, field: keyof AttendanceRow, value: string | null) => {
    setRows((prev) => {
      const updated = [...prev];
      updated[idx] = { ...updated[idx], [field]: value };
      return updated;
    });
  };

  const bulkMutation = useMutation({
    mutationFn: bulkMarkAsistencia,
    onSuccess: () => {
      message.success('Asistencia guardada');
      queryClient.invalidateQueries({ queryKey: ['asistencia', fechaStr] });
    },
    onError: () => message.error('Error al guardar asistencia'),
  });

  const handleSave = () => {
    bulkMutation.mutate({
      date: fechaStr,
      items: rows.map((r) => ({
        trabajador_id: r.trabajador_id,
        check_in_time: r.check_in_time,
        check_out_time: r.check_out_time,
        status: r.status,
        notes: r.notes,
      })),
    });
  };

  const columns: ColumnsType<AttendanceRow> = [
    {
      title: 'Trabajador',
      dataIndex: 'trabajador_name',
      key: 'trabajador_name',
      width: 200,
    },
    {
      title: 'Estado',
      key: 'status',
      width: 140,
      render: (_: unknown, record: AttendanceRow, idx: number) => (
        <Select
          value={record.status}
          onChange={(val) => updateRow(idx, 'status', val)}
          options={STATUS_OPTIONS}
          style={{ width: '100%' }}
          size="small"
        />
      ),
    },
    {
      title: 'Entrada',
      key: 'check_in_time',
      width: 120,
      render: (_: unknown, record: AttendanceRow, idx: number) => (
        <TimePicker
          value={record.check_in_time ? dayjs(record.check_in_time, 'HH:mm') : null}
          onChange={(val) => updateRow(idx, 'check_in_time', val ? val.format('HH:mm') : null)}
          format="HH:mm"
          size="small"
          style={{ width: '100%' }}
          minuteStep={5}
        />
      ),
    },
    {
      title: 'Salida',
      key: 'check_out_time',
      width: 120,
      render: (_: unknown, record: AttendanceRow, idx: number) => (
        <TimePicker
          value={record.check_out_time ? dayjs(record.check_out_time, 'HH:mm') : null}
          onChange={(val) => updateRow(idx, 'check_out_time', val ? val.format('HH:mm') : null)}
          format="HH:mm"
          size="small"
          style={{ width: '100%' }}
          minuteStep={5}
        />
      ),
    },
    {
      title: 'Notas',
      key: 'notes',
      render: (_: unknown, record: AttendanceRow, idx: number) => (
        <Input
          value={record.notes || ''}
          onChange={(e) => updateRow(idx, 'notes', e.target.value || null)}
          size="small"
          placeholder="Opcional"
        />
      ),
    },
    {
      title: 'Vista',
      key: 'preview',
      width: 100,
      render: (_: unknown, record: AttendanceRow) => (
        <Tag color={STATUS_COLORS[record.status] || 'default'}>
          {record.status}
        </Tag>
      ),
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>Control de Asistencia</Title>
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={bulkMutation.isPending}
            disabled={rows.length === 0}
          >
            Guardar
          </Button>
        </Col>
      </Row>

      <Row style={{ marginBottom: 16 }}>
        <Col>
          <DatePicker
            value={selectedDate}
            onChange={(val) => val && setSelectedDate(val)}
            format="DD/MM/YYYY"
            allowClear={false}
          />
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={rows}
        rowKey="trabajador_id"
        loading={isLoading}
        size="small"
        pagination={false}
      />
    </div>
  );
}
