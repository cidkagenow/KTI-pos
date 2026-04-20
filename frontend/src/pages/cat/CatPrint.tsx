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

// All positions in mm from top-left of paper
// These need calibration with actual pre-printed paper
const FIELDS = {
  // ═══ TOP-LEFT QUADRANT (Certificate + Customer) ═══
  // Certificate number (Nro del Certificado)
  certNumber1: { top: 61, left: 24, width: 50 },
  // Dates
  desde1: { top: 72, left: 18, width: 35 },
  hasta1: { top: 75, left: 18, width: 35 },
  // Customer name
  customerName1: { top: 86, left: 8, width: 130 },
  // DNI + Phone
  customerDni1: { top: 93, left: 8, width: 50 },
  customerPhone1: { top: 93, left: 70, width: 50 },
  // Address
  customerAddress1: { top: 100, left: 8, width: 130 },
  // Ambito
  ambito1: { top: 107, left: 8, width: 80 },
  // Price fields (bottom of left quadrant)
  precio1: { top: 92, left: 118, width: 20 },
  apExtra1: { top: 92, left: 132, width: 20 },

  // ═══ TOP-RIGHT QUADRANT (Vehicle Data) ═══
  placa1: { top: 26, left: 180, width: 30 },
  categoriaClase1: { top: 26, left: 240, width: 50 },
  añoFab1: { top: 33, left: 180, width: 30 },
  marca1: { top: 33, left: 240, width: 50 },
  asientos1: { top: 40, left: 180, width: 30 },
  modelo1: { top: 40, left: 240, width: 50 },
  uso1: { top: 47, left: 180, width: 50 },
  vin1: { top: 47, left: 240, width: 55 },

  // ═══ BOTTOM-LEFT QUADRANT (Certificate + Customer copy) ═══
  certNumber2: { top: 209, left: 24, width: 50 },
  desde2: { top: 220, left: 18, width: 35 },
  hasta2: { top: 223, left: 18, width: 35 },
  customerName2: { top: 234, left: 8, width: 130 },
  customerDni2: { top: 241, left: 8, width: 50 },
  customerPhone2: { top: 241, left: 70, width: 50 },
  customerAddress2: { top: 248, left: 8, width: 130 },
  ambito2: { top: 255, left: 8, width: 80 },
  precio2: { top: 240, left: 118, width: 20 },
  apExtra2: { top: 240, left: 132, width: 20 },

  // ═══ BOTTOM-RIGHT QUADRANT (Vehicle Data copy) ═══
  placa2: { top: 174, left: 180, width: 30 },
  categoriaClase2: { top: 174, left: 240, width: 50 },
  añoFab2: { top: 181, left: 180, width: 30 },
  marca2: { top: 181, left: 240, width: 50 },
  asientos2: { top: 188, left: 180, width: 30 },
  modelo2: { top: 188, left: 240, width: 50 },
  uso2: { top: 195, left: 180, width: 50 },
  vin2: { top: 195, left: 240, width: 55 },
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
          @page { size: A4; margin: 0; }
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
        {/* TOP-LEFT: Certificate + Customer */}
        <Field {...FIELDS.certNumber1}>{certNum}</Field>
        <Field {...FIELDS.desde1}>{desde}</Field>
        <Field {...FIELDS.hasta1}>{hasta}</Field>
        <Field {...FIELDS.customerName1}>{sale.customer_name}</Field>
        <Field {...FIELDS.customerDni1}>{sale.customer_dni}</Field>
        <Field {...FIELDS.customerPhone1}>{sale.customer_phone}</Field>
        <Field {...FIELDS.customerAddress1}>{sale.customer_address}</Field>
        <Field {...FIELDS.ambito1}>PIURA</Field>
        <Field {...FIELDS.precio1}>S/{sale.precio}</Field>
        <Field {...FIELDS.apExtra1}>S/{sale.ap_extra}</Field>

        {/* TOP-RIGHT: Vehicle Data */}
        <Field {...FIELDS.placa1}>{sale.placa}</Field>
        <Field {...FIELDS.categoriaClase1}>{sale.categoria} / {sale.clase}</Field>
        <Field {...FIELDS.añoFab1}>{sale.año}</Field>
        <Field {...FIELDS.marca1}>{sale.marca}</Field>
        <Field {...FIELDS.asientos1}>{sale.asientos}</Field>
        <Field {...FIELDS.modelo1}>{sale.modelo}</Field>
        <Field {...FIELDS.uso1}>{sale.uso}</Field>
        <Field {...FIELDS.vin1} fontSize={7}>{sale.serie_vehiculo}</Field>

        {/* BOTTOM-LEFT: Certificate + Customer copy */}
        <Field {...FIELDS.certNumber2}>{certNum}</Field>
        <Field {...FIELDS.desde2}>{desde}</Field>
        <Field {...FIELDS.hasta2}>{hasta}</Field>
        <Field {...FIELDS.customerName2}>{sale.customer_name}</Field>
        <Field {...FIELDS.customerDni2}>{sale.customer_dni}</Field>
        <Field {...FIELDS.customerPhone2}>{sale.customer_phone}</Field>
        <Field {...FIELDS.customerAddress2}>{sale.customer_address}</Field>
        <Field {...FIELDS.ambito2}>PIURA</Field>
        <Field {...FIELDS.precio2}>S/{sale.precio}</Field>
        <Field {...FIELDS.apExtra2}>S/{sale.ap_extra}</Field>

        {/* BOTTOM-RIGHT: Vehicle Data copy */}
        <Field {...FIELDS.placa2}>{sale.placa}</Field>
        <Field {...FIELDS.categoriaClase2}>{sale.categoria} / {sale.clase}</Field>
        <Field {...FIELDS.añoFab2}>{sale.año}</Field>
        <Field {...FIELDS.marca2}>{sale.marca}</Field>
        <Field {...FIELDS.asientos2}>{sale.asientos}</Field>
        <Field {...FIELDS.modelo2}>{sale.modelo}</Field>
        <Field {...FIELDS.uso2}>{sale.uso}</Field>
        <Field {...FIELDS.vin2} fontSize={7}>{sale.serie_vehiculo}</Field>
      </div>
    </>
  );
}
