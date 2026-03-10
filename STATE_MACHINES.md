# KTI-POS State Machines

## 1. Sale (Venta) Lifecycle

```mermaid
stateDiagram-v2
    [*] --> PREVENTA: POST /sales

    state PREVENTA {
        note right of PREVENTA
            Actions available:
            - Edit (admin)
            - Print
        end note
    }

    PREVENTA --> PREVENTA: PUT /sales/{id}\n(edit items, client, etc.)
    PREVENTA --> FACTURADO: POST /sales/{id}/facturar\n[admin, RUC if FACTURA]
    PREVENTA --> ELIMINADO: DELETE /sales/{id}\n[admin] → returns stock
    PREVENTA --> ANULADO: POST /sales/{id}/anular\n[admin] → returns stock

    FACTURADO --> ANULADO: POST /sales/{id}/anular\n[admin] → returns stock

    ELIMINADO --> [*]
    ANULADO --> [*]

    note right of FACTURADO
        - SUNAT submission triggered
        - issue_date set
        - Can create Nota de Credito
    end note

    note right of ANULADO
        - voided_by, voided_at recorded
        - Stock returned (if not NOTA_VENTA)
    end note

    note right of ELIMINADO
        - Soft delete (stays in DB)
        - Stock returned (if not NOTA_VENTA)
    end note
```

## 2. Nota de Venta → Emitir / Convertir Flow

```mermaid
stateDiagram-v2
    [*] --> NOTA_VENTA_PREVENTA: POST /sales\n(doc_type=NOTA_VENTA)\n⚠️ NO stock deducted

    NOTA_VENTA_PREVENTA --> NOTA_VENTA_EMITIDO: POST /sales/{id}/emitir-nv\n→ Assigns doc_number\n→ Printable (non-fiscal)\n⚠️ NO stock deducted

    NOTA_VENTA_PREVENTA --> BOLETA_PREVENTA: POST /sales/{id}/convertir\n[admin, stock check]\n✅ Stock deducted now
    NOTA_VENTA_PREVENTA --> FACTURA_PREVENTA: POST /sales/{id}/convertir\n[admin, client RUC required]\n✅ Stock deducted now

    NOTA_VENTA_EMITIDO --> BOLETA_PREVENTA: POST /sales/{id}/convertir\n[admin, stock check]\n✅ Stock deducted now
    NOTA_VENTA_EMITIDO --> FACTURA_PREVENTA: POST /sales/{id}/convertir\n[admin, client RUC required]\n✅ Stock deducted now

    BOLETA_PREVENTA --> FACTURADO: POST /sales/{id}/facturar
    FACTURA_PREVENTA --> FACTURADO: POST /sales/{id}/facturar

    NOTA_VENTA_PREVENTA --> ELIMINADO: DELETE /sales/{id}\n(no stock to return)
    NOTA_VENTA_EMITIDO --> ELIMINADO: DELETE /sales/{id}\n(no stock to return)
    NOTA_VENTA_EMITIDO --> ANULADO: POST /sales/{id}/anular\n(no stock to return)
```

## 3. Nota de Credito (Credit Note) Flow

```mermaid
stateDiagram-v2
    SALE_FACTURADO: Referenced Sale\n(FACTURADO)

    [*] --> NC_PREVENTA: POST /sales/nota-credito\n[admin, items ⊆ original sale]
    SALE_FACTURADO --> [*]: ref_sale_id

    NC_PREVENTA --> NC_FACTURADO: POST /sales/{id}/facturar\n→ Sends NC to SUNAT

    state nc_stock <<choice>>
    NC_FACTURADO --> nc_stock
    nc_stock --> STOCK_RETURNED: motivo 01 (devolución)\nor motivo 04 (descuento)
    nc_stock --> NO_STOCK_CHANGE: other motivo codes

    NC_PREVENTA --> NC_ANULADO: POST /sales/{id}/anular
    NC_FACTURADO --> NC_ANULADO: POST /sales/{id}/anular
```

## 4. Purchase Order (Orden de Compra) Lifecycle

```mermaid
stateDiagram-v2
    [*] --> DRAFT: POST /purchase-orders\n[admin]

    DRAFT --> DRAFT: PUT /purchase-orders/{id}\n(edit items, supplier, etc.)
    DRAFT --> RECEIVED: POST /purchase-orders/{id}/receive\n[admin]\n→ Stock added to inventory\n→ Updates product cost_price
    DRAFT --> CANCELLED: DELETE /purchase-orders/{id}\n[admin]\n→ No inventory impact

    RECEIVED --> [*]
    CANCELLED --> [*]

    note right of RECEIVED
        - received_at timestamp set
        - InventoryMovement(PURCHASE) created
        - product.cost_price updated
    end note
```

## 5. SUNAT Document Lifecycle

```mermaid
stateDiagram-v2
    [*] --> PENDIENTE: Sale facturada\n→ XML built → signed → sent

    PENDIENTE --> ACEPTADO: SUNAT CDR OK\n→ auto-email to client
    PENDIENTE --> RECHAZADO: SUNAT CDR rejected
    PENDIENTE --> ERROR: System/network error

    ERROR --> PENDIENTE: Retry submission

    ACEPTADO --> [*]
    RECHAZADO --> [*]

    note right of ACEPTADO
        - sunat_hash stored
        - CDR XML archived
        - PDF generated
        - Email sent (if client has email)
    end note
```

## 6. Inventory Movement Types (Audit Trail)

```mermaid
stateDiagram-v2
    direction LR

    state "Stock Changes" as stock {
        SALE: SALE\n(stock -)
        PURCHASE: PURCHASE\n(stock +)
        VOID_RETURN: VOID_RETURN\n(stock +)
        NC_RETURN: NC_RETURN\n(stock +)
    }

    note right of SALE: Sale created (non-NOTA_VENTA)\nor NOTA_VENTA converted
    note right of PURCHASE: PO received
    note right of VOID_RETURN: Sale voided or deleted
    note right of NC_RETURN: Nota Credito facturada\n(motivo 01 or 04)
```

## 7. Complete System Overview

```mermaid
flowchart TB
    subgraph Sales["Sale Lifecycle"]
        S1([Create]) --> S2[PREVENTA]
        S2 -->|facturar| S3[FACTURADO]
        S2 -->|delete| S4[ELIMINADO]
        S2 -->|anular| S5[ANULADO]
        S3 -->|anular| S5
    end

    subgraph NV["Nota Venta Path"]
        NV1[NOTA_VENTA] -->|convertir| NV2[BOLETA / FACTURA]
        NV2 --> S2
    end

    subgraph NC["Nota Credito"]
        S3 -.->|create NC| NC1[NC PREVENTA]
        NC1 -->|facturar| NC2[NC FACTURADO]
    end

    subgraph PO["Purchase Orders"]
        P1([Create]) --> P2[DRAFT]
        P2 -->|receive| P3[RECEIVED]
        P2 -->|cancel| P4[CANCELLED]
    end

    subgraph SUNAT["SUNAT Integration"]
        SU1[PENDIENTE] --> SU2[ACEPTADO]
        SU1 --> SU3[RECHAZADO]
        SU1 --> SU4[ERROR]
    end

    subgraph Inventory["Inventory"]
        INV[Stock Level]
    end

    S3 -->|auto-submit| SU1
    NC2 -->|auto-submit| SU1
    S2 -->|stock -| INV
    S4 -->|stock +| INV
    S5 -->|stock +| INV
    NC2 -->|stock + if devolución| INV
    P3 -->|stock +| INV
    NV2 -->|stock -| INV
```

## Action Permissions Matrix

| Action | Endpoint | Role | Valid From States |
|--------|----------|------|-------------------|
| Create Sale | `POST /sales` | any auth | — |
| Edit Sale | `PUT /sales/{id}` | admin | PREVENTA, EMITIDO |
| Facturar | `POST /sales/{id}/facturar` | admin | PREVENTA |
| Emitir NV | `POST /sales/{id}/emitir-nv` | any auth | PREVENTA (NOTA_VENTA only) |
| Anular | `POST /sales/{id}/anular` | admin | PREVENTA, EMITIDO, FACTURADO |
| Delete Sale | `DELETE /sales/{id}` | admin | PREVENTA, EMITIDO |
| Convertir NV | `POST /sales/{id}/convertir` | admin | PREVENTA, EMITIDO (NOTA_VENTA only) |
| Create NC | `POST /sales/nota-credito` | admin | ref sale = FACTURADO |
| Create PO | `POST /purchase-orders` | admin | — |
| Edit PO | `PUT /purchase-orders/{id}` | admin | DRAFT |
| Receive PO | `POST /purchase-orders/{id}/receive` | admin | DRAFT |
| Cancel PO | `DELETE /purchase-orders/{id}` | admin | DRAFT |
