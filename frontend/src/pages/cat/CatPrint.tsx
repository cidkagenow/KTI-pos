import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import api from '../../api/client';
import type { CatSale } from '../../api/cat';

/**
 * CAT Print Page — prints data overlay on pre-printed AFOCAT paper.
 *
 * A4 LANDSCAPE (297mm x 210mm) pre-printed paper layout:
 * ┌──────────────────────────────────────────────────────────┐
 * │  TOP SECTION (full width, ~105mm tall)                   │
 * │  Left: cert info + customer    Right: vehicle + sticker  │
 * ├────────────────────────────┬─────────────────────────────┤
 * │  BOTTOM-LEFT (~148mm wide) │  BOTTOM-RIGHT (~148mm wide) │
 * │  Copy 1 (same fields)     │  Copy 2 (same fields)       │
 * └────────────────────────────┴─────────────────────────────┘
 *
 * Carbon copy layers print through — but bottom copies need separate data
 * because they're in different positions on the same sheet.
 */

// ═══ SECTION ORIGINS (top-left corner of each section) ═══
const SECTIONS = {
  top:         { x: 0,   y: 0   },
  bottomLeft:  { x: 0,   y: 105 },
  bottomRight: { x: 148, y: 105 },
};

// ═══ FIELD POSITIONS relative to section origin ═══
// TOP section is full-width (297mm), bottom sections are half-width (~148mm)
// We define separate field sets for top vs bottom due to different layouts

const TOP_FIELDS = {
  // Vehicle data (right side of top section)
  placa:          { top: 16,  left: 117, width: 30 },
  categoriaClase: { top: 16,  left: 165, width: 40 },
  añoFab:         { top: 24,  left: 117, width: 30 },
  marca:          { top: 24,  left: 165, width: 40 },
  asientos:       { top: 32,  left: 117, width: 30 },
  modelo:         { top: 32,  left: 165, width: 40 },
  uso:            { top: 40,  left: 117, width: 55 },
  vin:            { top: 40,  left: 165, width: 45 },
  // Certificate info (left side)
  certNumber:     { top: 42,  left: 16,  width: 55 },
  desde:          { top: 56,  left: 12,  width: 40 },
  hasta:          { top: 60,  left: 12,  width: 40 },
  // Customer data
  customerName:   { top: 73,  left: 5,   width: 100 },
  customerDni:    { top: 79,  left: 5,   width: 40 },
  customerPhone:  { top: 79,  left: 52,  width: 40 },
  customerAddress:{ top: 85,  left: 5,   width: 100 },
  ambito:         { top: 91,  left: 5,   width: 60 },
  // Pricing
  fecha:          { top: 94,  left: 25,  width: 25 },
  precio:         { top: 94,  left: 68,  width: 18 },
  apExtra:        { top: 94,  left: 85,  width: 18 },
  montoTotal:     { top: 94,  left: 98,  width: 18 },
};

// Bottom copies are smaller (~148mm x 105mm) — same fields, adjusted positions
const BOTTOM_FIELDS = {
  // Vehicle data (right portion of each bottom copy)
  placa:          { top: 16,  left: 68,  width: 25 },
  categoriaClase: { top: 16,  left: 110, width: 35 },
  añoFab:         { top: 24,  left: 68,  width: 25 },
  marca:          { top: 24,  left: 110, width: 35 },
  asientos:       { top: 32,  left: 68,  width: 25 },
  modelo:         { top: 32,  left: 110, width: 35 },
  uso:            { top: 40,  left: 68,  width: 45 },
  vin:            { top: 40,  left: 110, width: 38 },
  // Certificate info (left side)
  certNumber:     { top: 42,  left: 10,  width: 45 },
  desde:          { top: 56,  left: 8,   width: 35 },
  hasta:          { top: 60,  left: 8,   width: 35 },
  // Customer data
  customerName:   { top: 73,  left: 3,   width: 80 },
  customerDni:    { top: 79,  left: 3,   width: 30 },
  customerPhone:  { top: 79,  left: 40,  width: 30 },
  customerAddress:{ top: 85,  left: 3,   width: 80 },
  ambito:         { top: 91,  left: 3,   width: 50 },
  // Pricing
  fecha:          { top: 94,  left: 18,  width: 20 },
  precio:         { top: 94,  left: 50,  width: 15 },
  apExtra:        { top: 94,  left: 65,  width: 15 },
  montoTotal:     { top: 94,  left: 78,  width: 15 },
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

function SectionFields({
  sale, desde, hasta, certNum, fields, origin, fontSize = 9,
}: {
  sale: CatSale; desde: string; hasta: string; certNum: string;
  fields: typeof TOP_FIELDS; origin: { x: number; y: number }; fontSize?: number;
}) {
  const f = (field: { top: number; left: number; width: number }) => ({
    top: field.top + origin.y,
    left: field.left + origin.x,
    width: field.width,
  });

  return (
    <>
      {/* Vehicle Data */}
      <Field {...f(fields.placa)} fontSize={fontSize}>{sale.placa}</Field>
      <Field {...f(fields.categoriaClase)} fontSize={fontSize}>{sale.categoria} / {sale.clase}</Field>
      <Field {...f(fields.añoFab)} fontSize={fontSize}>{sale.año}</Field>
      <Field {...f(fields.marca)} fontSize={fontSize}>{sale.marca}</Field>
      <Field {...f(fields.asientos)} fontSize={fontSize}>{sale.asientos}</Field>
      <Field {...f(fields.modelo)} fontSize={fontSize}>{sale.modelo}</Field>
      <Field {...f(fields.uso)} fontSize={fontSize}>{sale.uso}</Field>
      <Field {...f(fields.vin)} fontSize={Math.max(fontSize - 2, 6)}>{sale.serie_vehiculo}</Field>

      {/* Certificate Info */}
      <Field {...f(fields.certNumber)} fontSize={fontSize}>{certNum}</Field>
      <Field {...f(fields.desde)} fontSize={fontSize}>{desde}</Field>
      <Field {...f(fields.hasta)} fontSize={fontSize}>{hasta}</Field>

      {/* Customer Data */}
      <Field {...f(fields.customerName)} fontSize={fontSize}>{sale.customer_name}</Field>
      <Field {...f(fields.customerDni)} fontSize={fontSize}>{sale.customer_dni}</Field>
      <Field {...f(fields.customerPhone)} fontSize={fontSize}>{sale.customer_phone}</Field>
      <Field {...f(fields.customerAddress)} fontSize={fontSize}>{sale.customer_address}</Field>
      <Field {...f(fields.ambito)} fontSize={fontSize}>PIURA</Field>

      {/* Pricing */}
      <Field {...f(fields.fecha)} fontSize={fontSize}>{desde}</Field>
      <Field {...f(fields.precio)} fontSize={fontSize}>S/{sale.precio}</Field>
      <Field {...f(fields.apExtra)} fontSize={fontSize}>S/{sale.ap_extra}</Field>
      <Field {...f(fields.montoTotal)} fontSize={fontSize}>S/{sale.total}</Field>
    </>
  );
}

export default function CatPrint() {
  const { id } = useParams<{ id: string }>();
  const [sale, setSale] = useState<CatSale | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
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
        customer_phone: '987654321',
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

      <div className="no-print" style={{ padding: 16, textAlign: 'center', background: '#fff3cd', color: '#856404' }}>
        Vista previa — imprima en papel blanco y compare con el papel pre-impreso.
        <button onClick={() => window.print()} style={{ marginLeft: 16, padding: '4px 16px', cursor: 'pointer' }}>
          Imprimir
        </button>
      </div>

      <div className="print-page" style={{ position: 'relative', width: '297mm', height: '210mm', overflow: 'hidden' }}>
        {/* TOP SECTION — full width */}
        <SectionFields
          sale={sale} desde={desde} hasta={hasta} certNum={certNum}
          fields={TOP_FIELDS} origin={SECTIONS.top} fontSize={9}
        />

        {/* BOTTOM-LEFT COPY */}
        <SectionFields
          sale={sale} desde={desde} hasta={hasta} certNum={certNum}
          fields={BOTTOM_FIELDS} origin={SECTIONS.bottomLeft} fontSize={8}
        />

        {/* BOTTOM-RIGHT COPY */}
        <SectionFields
          sale={sale} desde={desde} hasta={hasta} certNum={certNum}
          fields={BOTTOM_FIELDS} origin={SECTIONS.bottomRight} fontSize={8}
        />
      </div>
    </>
  );
}
