import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import { getSale } from '../../api/sales';
import { formatCurrency } from '../../utils/format';
import type { Sale } from '../../types';

const EMPRESA_RUC = '20525996957';
const EMPRESA_RAZON_SOCIAL = 'INVERSIONES KTI D & E E.I.R.L.';
const EMPRESA_DIRECCIONES = [
  'JR. JOSEFINA RAMIS DE COX 453 - CATACAOS',
  'AV. GRAU 1346 - PIURA',
];

/** Convert a number to Spanish words for Peruvian receipts */
function numberToWords(n: number): string {
  const units = ['', 'UN', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE'];
  const teens = ['DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE',
    'DIECISEIS', 'DIECISIETE', 'DIECIOCHO', 'DIECINUEVE'];
  const tens = ['', '', 'VEINTE', 'TREINTA', 'CUARENTA', 'CINCUENTA',
    'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA'];
  const hundreds = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS',
    'QUINIENTOS', 'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS'];

  if (n === 0) return 'CERO';
  if (n === 100) return 'CIEN';

  const convert = (num: number): string => {
    if (num === 0) return '';
    if (num === 100) return 'CIEN';
    if (num < 10) return units[num];
    if (num < 20) return teens[num - 10];
    if (num < 30 && num > 20) return 'VEINTI' + units[num - 20].toLowerCase();
    if (num === 20) return 'VEINTE';
    if (num < 100) {
      const t = Math.floor(num / 10);
      const u = num % 10;
      return u === 0 ? tens[t] : `${tens[t]} Y ${units[u]}`;
    }
    if (num < 1000) {
      const h = Math.floor(num / 100);
      const rest = num % 100;
      return rest === 0 ? hundreds[h] : `${hundreds[h]} ${convert(rest)}`;
    }
    if (num < 1000000) {
      const thousands = Math.floor(num / 1000);
      const rest = num % 1000;
      const prefix = thousands === 1 ? 'MIL' : `${convert(thousands)} MIL`;
      return rest === 0 ? prefix : `${prefix} ${convert(rest)}`;
    }
    return String(num);
  };

  const intPart = Math.floor(n);
  const decPart = Math.round((n - intPart) * 100);
  const decStr = String(decPart).padStart(2, '0');
  return `${convert(intPart)} Y ${decStr}/100 SOLES`;
}

export default function SalePrint() {
  const { id } = useParams<{ id: string }>();
  const [sale, setSale] = useState<Sale | null>(null);

  useEffect(() => {
    if (id) {
      getSale(Number(id)).then((data) => {
        setSale(data);
        setTimeout(() => window.print(), 500);
      });
    }
  }, [id]);

  if (!sale) return <div style={{ padding: 40, textAlign: 'center' }}>Cargando...</div>;

  const docLabel = sale.doc_type === 'NOTA_CREDITO'
    ? 'NOTA DE CREDITO'
    : sale.doc_type === 'NOTA_VENTA'
      ? 'NOTA DE VENTA'
      : sale.doc_type === 'BOLETA'
        ? 'BOLETA DE VENTA ELECTRONICA'
        : 'FACTURA ELECTRONICA';
  const docNumber = sale.doc_number
    ? `${sale.series}-${String(sale.doc_number).padStart(7, '0')}`
    : `PRE-${sale.id}`;

  const issueDate = new Date(sale.created_at);
  const dateStr = issueDate.toLocaleDateString('es-PE');
  const timeStr = issueDate.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });

  const isNotaVenta = sale.doc_type === 'NOTA_VENTA';

  // QR data for SUNAT (facturas=01, boletas=03, NC=07)
  const docTypeCode = sale.doc_type === 'FACTURA' ? '01'
    : sale.doc_type === 'BOLETA' ? '03'
    : sale.doc_type === 'NOTA_CREDITO' ? '07' : '';
  const clientDocTypeCode = sale.client_doc_type === 'RUC' ? '6'
    : sale.client_doc_type === 'DNI' ? '1'
    : sale.client_doc_type === 'CE' ? '4'
    : sale.client_doc_type === 'PASAPORTE' ? '7' : '0';
  const hasHash = !isNotaVenta && sale.sunat_hash;
  const qrData = hasHash
    ? [
        EMPRESA_RUC,
        docTypeCode,
        sale.series,
        sale.doc_number ? String(sale.doc_number).padStart(7, '0') : '',
        sale.igv_amount.toFixed(2),
        sale.total.toFixed(2),
        dateStr,
        clientDocTypeCode,
        sale.client_doc_number || '',
        sale.sunat_hash,
      ].join('|')
    : '';

  return (
    <>
      <style>{`
        @media print {
          body { margin: 0; }
          .no-print { display: none !important; }
          @page { size: 80mm auto; margin: 4mm; }
        }
        html, body {
          font-family: 'Courier New', monospace;
          font-size: 13px;
          line-height: 1.2;
          color: #000 !important;
          background: #fff !important;
          -webkit-print-color-adjust: exact;
          print-color-adjust: exact;
        }
        .receipt, .receipt * {
          font-weight: 600;
        }
        .bold { font-weight: 900 !important; }
        .receipt {
          max-width: 302px;
          margin: 0 auto;
          padding: 10px;
        }
        .center { text-align: center; }
        .divider {
          border: none;
          border-top: 1px dashed #000;
          margin: 3px 0;
        }
        .row {
          display: flex;
          justify-content: space-between;
        }
        .info-line {
          font-size: 11px;
          margin: 1px 0;
          word-wrap: break-word;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 12px;
        }
        th {
          text-align: left;
          border-bottom: 1px solid #000;
          padding: 2px 0;
          font-size: 11px;
        }
        th:last-child, td:last-child { text-align: right; }
        th:nth-child(3), td:nth-child(3) { text-align: center; }
        td { padding: 2px 0; vertical-align: top; }
        .total-section { margin-top: 3px; }
        .total-row {
          display: flex;
          justify-content: space-between;
          padding: 1px 0;
          font-size: 12px;
        }
        .grand-total {
          font-size: 14px;
          font-weight: bold;
          border-top: 1px solid #000;
          padding-top: 4px;
          margin-top: 2px;
        }
        .btn-bar {
          max-width: 302px;
          margin: 20px auto;
          display: flex;
          gap: 10px;
          justify-content: center;
        }
        .btn-bar button {
          padding: 8px 20px;
          font-size: 14px;
          cursor: pointer;
          border: 1px solid #ccc;
          border-radius: 4px;
          background: #fff;
        }
        .btn-bar button.primary {
          background: #1a3a8f;
          color: #fff;
          border-color: #1a3a8f;
        }
      `}</style>

      <div className="no-print">
        <div className="btn-bar">
          <button className="primary" onClick={() => window.print()}>Imprimir</button>
          <button onClick={() => window.close()}>Cerrar</button>
        </div>
      </div>

      <div className="receipt">
        {/* Company header */}
        <div className="center" style={{ marginBottom: -10 }}>
          <img src="/kti-logo.png" alt="KTI" style={{ height: 70, objectFit: 'contain' }} />
        </div>
        <div className="center bold" style={{ fontSize: 13 }}>
          {EMPRESA_RAZON_SOCIAL}
        </div>
        {!isNotaVenta && (
          <>
            <div className="center" style={{ fontSize: 10, marginTop: 4 }}>
              RUC: {EMPRESA_RUC}
            </div>
            {EMPRESA_DIRECCIONES.map((dir, i) => (
              <div key={i} className="center" style={{ fontSize: 10 }}>
                {dir}
              </div>
            ))}
          </>
        )}

        <hr className="divider" />

        {/* Document title */}
        <div className="center bold" style={{ fontSize: 13 }}>
          {docLabel}
        </div>
        <div className="center bold">N° {docNumber}</div>

        {isNotaVenta && (
          <div className="center" style={{ fontSize: 9, marginTop: 4, border: '1px dashed #000', padding: '2px 4px' }}>
            DOCUMENTO NO FISCAL
          </div>
        )}

        {sale.doc_type === 'NOTA_CREDITO' && (
          <>
            <div className="center" style={{ fontSize: 10, marginTop: 4 }}>
              Motivo: {sale.nc_motivo_code} - {sale.nc_motivo_text}
            </div>
            {sale.ref_sale_id && (
              <div className="center" style={{ fontSize: 10 }}>
                Ref: Documento original #{sale.ref_sale_id}
              </div>
            )}
          </>
        )}

        <hr className="divider" />

        {/* Sale info */}
        <div>
          <div className="info-line row">
            <span>Fecha Emision: {dateStr}</span>
            <span>Hora: {timeStr}</span>
          </div>
          <div className="info-line row">
            <span>Condicion: {sale.payment_cond}</span>
            <span>Moneda: SOLES</span>
          </div>
          <div className="info-line">
            Cliente: {sale.client_name}
          </div>
          {sale.client_doc_type && sale.client_doc_number && (
            <div className="info-line">
              Doc: {sale.client_doc_type} - {sale.client_doc_number}
            </div>
          )}
          {sale.client_address && (
            <div className="info-line">
              Dir: {sale.client_address}
            </div>
          )}
        </div>

        <hr className="divider" />

        {/* Items table */}
        <table>
          <thead>
            <tr>
              <th>Descripcion</th>
              <th style={{ textAlign: 'center' }}>Cant.</th>
              <th style={{ textAlign: 'center' }}>Present.</th>
              <th style={{ textAlign: 'right' }}>Precio</th>
              <th style={{ textAlign: 'right' }}>Importe</th>
            </tr>
          </thead>
          <tbody>
            {sale.items.map((item, i) => (
              <tr key={i}>
                <td style={{ maxWidth: 120, fontSize: 11 }}>
                  {item.product_name}
                  {item.discount_pct > 0 && (
                    <span style={{ fontSize: 9 }}> (-{item.discount_pct}%)</span>
                  )}
                </td>
                <td style={{ textAlign: 'center' }}>{item.quantity}</td>
                <td style={{ textAlign: 'center', fontSize: 10 }}>{item.presentation || 'UND'}</td>
                <td style={{ textAlign: 'right' }}>{item.unit_price.toFixed(2)}</td>
                <td style={{ textAlign: 'right' }}>{item.line_total.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Totals */}
        <div className="total-section">
          <hr className="divider" />
          {!isNotaVenta && (
            <>
              <div className="total-row">
                <span>Op. Gravadas (S/):</span>
                <span>{sale.subtotal.toFixed(2)}</span>
              </div>
              <div className="total-row">
                <span>I.G.V. 18% (S/):</span>
                <span>{sale.igv_amount.toFixed(2)}</span>
              </div>
            </>
          )}
          <div className="total-row grand-total">
            <span>IMPORTE TOTAL (S/):</span>
            <span>{sale.total.toFixed(2)}</span>
          </div>
          {sale.payment_method === 'EFECTIVO' && sale.cash_received != null && (
            <>
              <div className="total-row" style={{ marginTop: 4 }}>
                <span>Efectivo:</span>
                <span>{sale.cash_received.toFixed(2)}</span>
              </div>
              <div className="total-row">
                <span>Vuelto:</span>
                <span>{Math.max(0, sale.cash_received - sale.total).toFixed(2)}</span>
              </div>
            </>
          )}
          {sale.payment_method === 'TARJETA' && (
            <div className="total-row" style={{ marginTop: 4 }}>
              <span>Pago:</span>
              <span>TARJETA</span>
            </div>
          )}
        </div>

        <hr className="divider" />

        {/* Amount in words */}
        <div style={{ fontSize: 10, marginTop: 2 }}>
          Son: {numberToWords(sale.total)}
        </div>

        <hr className="divider" />

        {/* Footer */}
        <div style={{ fontSize: 10, marginTop: 2 }}>
          Vendedor: {sale.seller_name}
        </div>

        {isNotaVenta ? (
          <>
            <div className="center" style={{ fontSize: 9, marginTop: 4 }}>
              Este documento no es comprobante de pago
            </div>
            <div className="center" style={{ fontSize: 9, marginTop: 1 }}>
              {sale.items.length} articulo(s)
            </div>
          </>
        ) : (
          <>
            <div className="center" style={{ fontSize: 9, marginTop: 4 }}>
              Repres. impresa de comprobante electronico.
            </div>
            {hasHash && (
              <>
                <div style={{ fontSize: 9, marginTop: 2, wordBreak: 'break-all' }}>
                  HASH: {sale.sunat_hash}
                </div>
                <div className="center" style={{ marginTop: 4 }}>
                  <QRCodeSVG value={qrData} size={100} />
                </div>
              </>
            )}
            <div className="center" style={{ fontSize: 9, marginTop: 2 }}>
              {sale.items.length} articulo(s)
            </div>
          </>
        )}
      </div>
    </>
  );
}
