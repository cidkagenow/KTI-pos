import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import api from '../../api/client';
import type { CatSale } from '../../api/cat';

/**
 * CAT Print Page — prints data overlay on pre-printed AFOCAT paper.
 *
 * The pre-printed A4 sheet has 4 copies (2x2 grid):
 * - Top-left: original
 * - Top-right: vehicle data
 * - Bottom-left: copy
 * - Bottom-right: vehicle data copy
 *
 * Each quadrant is ~148mm x ~148mm.
 * We only print TEXT — the paper already has borders, logos, labels.
 *
 * To calibrate: adjust the top/left values in the field positions below.
 * Print on blank paper and overlay on pre-printed paper against light.
 */

// All positions in mm from top-left of A4 LANDSCAPE paper (297mm x 210mm)
// Pre-printed paper: 3 carbon-copy layers stacked (prints once, copies through)
// Left section (~105mm): certificate info + customer data
// Middle section (~85mm): vehicle data
// Right section (~105mm): sticker (green, for windshield) — not printed
//
// Only ONE set of fields needed — the carbon copies the data to all layers.

const FIELDS = {
  // ═══ LEFT SECTION — Certificate + Customer ═══
  // Certificate number (below QR code area, "Nro del Certificado")
  certNumber: { top: 42, left: 16, width: 55 },
  // Dates (DESDE / HASTA)
  desde: { top: 56, left: 12, width: 40 },
  hasta: { top: 60, left: 12, width: 40 },
  // Customer name (NOMBRE)
  customerName: { top: 73, left: 5, width: 100 },
  // DNI + Phone
  customerDni: { top: 79, left: 5, width: 40 },
  customerPhone: { top: 79, left: 52, width: 40 },
  // Address
  customerAddress: { top: 85, left: 5, width: 100 },
  // Ambito
  ambito: { top: 91, left: 5, width: 60 },

  // ═══ MIDDLE SECTION — Vehicle Data ═══
  placa: { top: 16, left: 117, width: 30 },
  categoriaClase: { top: 16, left: 165, width: 40 },
  añoFab: { top: 24, left: 117, width: 30 },
  marca: { top: 24, left: 165, width: 40 },
  asientos: { top: 32, left: 117, width: 30 },
  modelo: { top: 32, left: 165, width: 40 },
  uso: { top: 40, left: 117, width: 40 },
  vin: { top: 40, left: 165, width: 45 },

  // ═══ BOTTOM OF LEFT — Pricing (Fecha, Precio, Aporte) ═══
  fecha: { top: 94, left: 25, width: 25 },
  precio: { top: 94, left: 68, width: 18 },
  apExtra: { top: 94, left: 85, width: 18 },
  montoTotal: { top: 94, left: 98, width: 18 },
};

function Field({ top, left, width, children, fontSize = 9 }: {
  top: number; left: number; width: number; children: React.ReactNode; fontSize?: number;
}) {
  return (
    <div style={{
      position: 'absolute',
      top: `${top}mm`,
      left: `${left}mm`,
      width: `${width}mm`,
      fontSize: `${fontSize}pt`,
      fontFamily: 'Arial, sans-serif',
      fontWeight: 'bold',
      lineHeight: 1.2,
      overflow: 'hidden',
      whiteSpace: 'nowrap',
    }}>
      {children}
    </div>
  );
}

export default function CatPrint() {
  const { id } = useParams<{ id: string }>();
  const [sale, setSale] = useState<CatSale | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    // Test mode: /cat/test/print uses dummy data (no backend needed)
    if (id === 'test') {
      setSale({
        id: 0,
        certificate_number: '003149-2026',
        placa: '2230-1D',
        marca: 'SAKIMOTO',
        modelo: 'SK-150',
        año: 2015,
        serie_vehiculo: 'BS9MTD150F2B24029',
        asientos: 3,
        categoria: 'L5',
        clase: 'TRIMOVIL',
        uso: 'SERVICIO PUBLICO URBANO',
        customer_name: 'CESAR AUGUSTO QUINDE VALDIVIEZO',
        customer_dni: '02701532',
        customer_phone: '',
        customer_address: 'JR.MARIANO DIAZ 1348 - CATACAOS',
        fecha_desde: '20/04/2026',
        fecha_hasta: '20/04/2027',
        precio: 100,
        ap_extra: 50,
        total: 150,
        status: 'VENDIDO',
        sold_by: null,
        notes: null,
        created_at: new Date().toISOString(),
      });
      return;
    }

    if (!id) return;
    api.get(`/cat`)
      .then((res) => {
        const found = res.data.find((s: CatSale) => s.id === Number(id));
        if (found) {
          setSale(found);
          setTimeout(() => window.print(), 500);
        } else {
          setError('CAT no encontrado');
        }
      })
      .catch(() => setError('Error al cargar datos'));
  }, [id]);

  if (error) return <div style={{ padding: 40, textAlign: 'center', color: 'red' }}>{error}</div>;
  if (!sale) return <div style={{ padding: 40, textAlign: 'center' }}>Cargando...</div>;

  const today = new Date();
  const nextYear = new Date(today);
  nextYear.setFullYear(nextYear.getFullYear() + 1);
  const desde = sale.fecha_desde || today.toLocaleDateString('es-PE');
  const hasta = sale.fecha_hasta || nextYear.toLocaleDateString('es-PE');
  const certNum = sale.certificate_number || '';

  return (
    <>
      <style>{`
        @media print {
          @page { size: A4 landscape; margin: 0; }
          body { margin: 0; padding: 0; }
          .no-print { display: none !important; }
        }
        @media screen {
          body { background: #eee; }
          .print-page { background: white; box-shadow: 0 2px 10px rgba(0,0,0,0.2); margin: 20px auto; }
        }
      `}</style>

      {/* Calibration help — only visible on screen, not printed */}
      <div className="no-print" style={{ padding: 16, textAlign: 'center', background: '#fff3cd', color: '#856404' }}>
        Vista previa — imprima en papel blanco y compare con el papel pre-impreso.
        Ajuste las posiciones en CatPrint.tsx si no alinea.
        <button onClick={() => window.print()} style={{ marginLeft: 16, padding: '4px 16px', cursor: 'pointer' }}>
          Imprimir
        </button>
      </div>

      <div className="print-page" style={{ position: 'relative', width: '297mm', height: '210mm', overflow: 'hidden' }}>
        {/* LEFT: Certificate + Customer */}
        <Field {...FIELDS.certNumber}>{certNum}</Field>
        <Field {...FIELDS.desde}>{desde}</Field>
        <Field {...FIELDS.hasta}>{hasta}</Field>
        <Field {...FIELDS.customerName}>{sale.customer_name}</Field>
        <Field {...FIELDS.customerDni}>{sale.customer_dni}</Field>
        <Field {...FIELDS.customerPhone}>{sale.customer_phone}</Field>
        <Field {...FIELDS.customerAddress}>{sale.customer_address}</Field>
        <Field {...FIELDS.ambito}>PIURA</Field>

        {/* MIDDLE: Vehicle Data */}
        <Field {...FIELDS.placa}>{sale.placa}</Field>
        <Field {...FIELDS.categoriaClase}>{sale.categoria} / {sale.clase}</Field>
        <Field {...FIELDS.añoFab}>{sale.año}</Field>
        <Field {...FIELDS.marca}>{sale.marca}</Field>
        <Field {...FIELDS.asientos}>{sale.asientos}</Field>
        <Field {...FIELDS.modelo}>{sale.modelo}</Field>
        <Field {...FIELDS.uso}>{sale.uso}</Field>
        <Field {...FIELDS.vin} fontSize={7}>{sale.serie_vehiculo}</Field>

        {/* BOTTOM: Pricing */}
        <Field {...FIELDS.fecha}>{desde}</Field>
        <Field {...FIELDS.precio}>S/{sale.precio}</Field>
        <Field {...FIELDS.apExtra}>S/{sale.ap_extra}</Field>
        <Field {...FIELDS.montoTotal}>S/{sale.total}</Field>
      </div>
    </>
  );
}
