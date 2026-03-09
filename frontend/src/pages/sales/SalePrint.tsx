import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getSale } from '../../api/sales';
import { formatCurrency, formatDateTime } from '../../utils/format';
import type { Sale } from '../../types';

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
        ? 'BOLETA DE VENTA'
        : 'FACTURA';
  const docNumber = sale.doc_number
    ? `${sale.series}-${String(sale.doc_number).padStart(7, '0')}`
    : `PRE-${sale.id}`;

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
          line-height: 1.4;
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
          margin: 6px 0;
        }
        .row {
          display: flex;
          justify-content: space-between;
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
        td { padding: 2px 0; }
        .total-section { margin-top: 6px; }
        .total-row {
          display: flex;
          justify-content: space-between;
          padding: 1px 0;
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
        <div className="center" style={{ marginBottom: 6 }}>
          <img src="/kti-logo.png" alt="KTI" style={{ height: 110, objectFit: 'contain' }} />
        </div>
        <div className="center bold" style={{ fontSize: 13 }}>
          INVERSIONES KTI D & E E.I.R.L.
        </div>
        {sale.doc_type !== 'NOTA_VENTA' && (
          <>
            <div className="center" style={{ fontSize: 10, marginTop: 4 }}>
              RUC: 20XXXXXXXXX
            </div>
            <div className="center" style={{ fontSize: 10 }}>
              Direccion de la empresa
            </div>
          </>
        )}

        <hr className="divider" />

        <div className="center bold" style={{ fontSize: 13 }}>
          {docLabel}
        </div>
        <div className="center bold">{docNumber}</div>

        {sale.doc_type === 'NOTA_VENTA' && (
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

        <div style={{ fontSize: 11 }}>
          <div className="row">
            <span>Fecha:</span>
            <span>{formatDateTime(sale.created_at)}</span>
          </div>
          <div className="row">
            <span>Cliente:</span>
            <span>{sale.client_name}</span>
          </div>
          <div className="row">
            <span>Vendedor:</span>
            <span>{sale.seller_name}</span>
          </div>
          <div className="row">
            <span>Condicion:</span>
            <span>{sale.payment_cond}</span>
          </div>
        </div>

        <hr className="divider" />

        <table>
          <thead>
            <tr>
              <th>Articulo</th>
              <th>P.U.</th>
              <th>Cant</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {sale.items.map((item, i) => (
              <tr key={i}>
                <td style={{ maxWidth: 140 }}>
                  {item.product_code} {item.product_name}
                  {item.discount_pct > 0 && (
                    <span style={{ fontSize: 9 }}> (-{item.discount_pct}%)</span>
                  )}
                </td>
                <td>{item.unit_price.toFixed(2)}</td>
                <td>{item.quantity}</td>
                <td>{item.line_total.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="total-section">
          <hr className="divider" />
          {sale.doc_type !== 'NOTA_VENTA' && (
            <>
              <div className="total-row">
                <span>SubTotal:</span>
                <span>{formatCurrency(sale.subtotal)}</span>
              </div>
              <div className="total-row">
                <span>IGV (18%):</span>
                <span>{formatCurrency(sale.igv_amount)}</span>
              </div>
            </>
          )}
          <div className="total-row grand-total">
            <span>TOTAL:</span>
            <span>{formatCurrency(sale.total)}</span>
          </div>
        </div>

        <hr className="divider" />

        {sale.doc_type === 'NOTA_VENTA' ? (
          <>
            <div className="center" style={{ fontSize: 9, marginTop: 6 }}>
              Este documento no es comprobante de pago
            </div>
            <div className="center" style={{ fontSize: 9, marginTop: 2 }}>
              {sale.items.length} articulo(s)
            </div>
          </>
        ) : (
          <>
            <div className="center" style={{ fontSize: 10, marginTop: 6 }}>
              Gracias por su compra!
            </div>
            <div className="center" style={{ fontSize: 9, marginTop: 2 }}>
              {sale.items.length} articulo(s)
            </div>
          </>
        )}
      </div>
    </>
  );
}
