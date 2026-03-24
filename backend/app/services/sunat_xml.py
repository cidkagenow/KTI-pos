"""
UBL 2.1 XML builders for SUNAT electronic invoicing.

Builds Invoice (factura/boleta), SummaryDocuments, and VoidedDocuments XML.
"""
import logging
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from lxml import etree

from app.config import settings
from app.models.sale import Sale

logger = logging.getLogger(__name__)

IGV_FACTOR = Decimal("1.18")
IGV_RATE = Decimal("0.18")

def _empresa():
    """Return empresa data."""
    return settings.EMPRESA_RUC, settings.EMPRESA_RAZON_SOCIAL, settings.EMPRESA_DIRECCION or "-"

# UBL 2.1 Namespaces
NS = {
    "": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "sac": "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1",
}

NS_SUMMARY = {
    "": "urn:sunat:names:specification:ubl:peru:schema:xsd:SummaryDocuments-1",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "sac": "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1",
}

NS_VOIDED = {
    "": "urn:sunat:names:specification:ubl:peru:schema:xsd:VoidedDocuments-1",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "sac": "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1",
}


def _dec(val) -> str:
    """Round to 2 decimal places."""
    return str(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _tag(ns_prefix: str, local_name: str, ns_map: dict) -> str:
    """Build Clark notation tag from prefix and local name."""
    if ns_prefix == "":
        uri = ns_map[""]
    else:
        uri = ns_map[ns_prefix]
    return f"{{{uri}}}{local_name}"


def _sub(parent, ns_prefix: str, local_name: str, text=None, ns_map=None, **attribs):
    """Add a subelement with optional text and attributes."""
    if ns_map is None:
        ns_map = NS
    tag = _tag(ns_prefix, local_name, ns_map)
    el = etree.SubElement(parent, tag, **attribs)
    if text is not None:
        el.text = str(text)
    return el


def _client_doc_type(doc_type: str) -> str:
    """Map KTI doc_type to SUNAT catalog 06."""
    mapping = {"DNI": "1", "RUC": "6", "NONE": "0", "CE": "4", "PASAPORTE": "7"}
    return mapping.get(doc_type, "0")


def _doc_type_code(doc_type: str) -> str:
    """Map KTI doc_type to SUNAT document type code."""
    return "01" if doc_type == "FACTURA" else "03"


def build_invoice_xml(sale: Sale) -> bytes:
    """
    Build UBL 2.1 Invoice XML for factura (01) or boleta (03).
    Returns XML bytes.
    """
    ruc, razon_social, direccion = _empresa()
    tipo_doc = _doc_type_code(sale.doc_type)
    issue = sale.issue_date or date.today()
    client = sale.client

    # Build NSMAP for root element
    nsmap = {None: NS[""]}
    for k, v in NS.items():
        if k:
            nsmap[k] = v

    root = etree.Element(_tag("", "Invoice", NS), nsmap=nsmap)

    # UBLExtensions (placeholder for signature)
    extensions = _sub(root, "ext", "UBLExtensions")
    extension = _sub(extensions, "ext", "UBLExtension")
    _sub(extension, "ext", "ExtensionContent")

    # Header
    _sub(root, "cbc", "UBLVersionID", "2.1")
    _sub(root, "cbc", "CustomizationID", "2.0")
    _sub(root, "cbc", "ID", f"{sale.series}-{sale.doc_number}")
    _sub(root, "cbc", "IssueDate", issue.isoformat())
    _sub(root, "cbc", "IssueTime", "00:00:00")
    _sub(root, "cbc", "InvoiceTypeCode",
         tipo_doc, listID="0101", listAgencyName="PE:SUNAT",
         listName="Tipo de Documento", listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01")
    _sub(root, "cbc", "DocumentCurrencyCode", "PEN",
         listID="ISO 4217 Alpha", listName="Currency", listAgencyName="United Nations Economic Commission for Europe")

    # Signature reference
    sig_ref = _sub(root, "cac", "Signature")
    _sub(sig_ref, "cbc", "ID", f"IDSign{ruc}")
    sig_party = _sub(sig_ref, "cac", "SignatoryParty")
    sig_party_id = _sub(sig_party, "cac", "PartyIdentification")
    _sub(sig_party_id, "cbc", "ID", ruc)
    sig_party_name = _sub(sig_party, "cac", "PartyName")
    _sub(sig_party_name, "cbc", "Name", razon_social)
    sig_attach = _sub(sig_ref, "cac", "DigitalSignatureAttachment")
    sig_ext_ref = _sub(sig_attach, "cac", "ExternalReference")
    _sub(sig_ext_ref, "cbc", "URI", f"#SignatureValue-{ruc}")

    # Supplier (AccountingSupplierParty)
    supplier = _sub(root, "cac", "AccountingSupplierParty")
    supplier_party = _sub(supplier, "cac", "Party")
    supplier_id = _sub(supplier_party, "cac", "PartyIdentification")
    _sub(supplier_id, "cbc", "ID", ruc,
         schemeID="6", schemeName="Documento de Identidad",
         schemeAgencyName="PE:SUNAT", schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06")
    supplier_name = _sub(supplier_party, "cac", "PartyName")
    _sub(supplier_name, "cbc", "Name", razon_social)
    supplier_legal = _sub(supplier_party, "cac", "PartyLegalEntity")
    _sub(supplier_legal, "cbc", "RegistrationName", razon_social)
    supplier_addr = _sub(supplier_legal, "cac", "RegistrationAddress")
    _sub(supplier_addr, "cbc", "AddressTypeCode", "0000")
    _sub(supplier_addr, "cbc", "Line",
         direccion).tag = _tag("cbc", "Line", NS)
    # Fix: use correct address element
    supplier_addr_line = _sub(supplier_addr, "cac", "AddressLine")
    supplier_addr_line_el = supplier_addr_line.getparent()
    supplier_addr.remove(supplier_addr_line)
    # Remove the incorrect Line and use AddressLine properly
    for child in list(supplier_addr):
        if child.tag == _tag("cbc", "Line", NS):
            supplier_addr.remove(child)
    addr_line = _sub(supplier_addr, "cac", "AddressLine")
    _sub(addr_line, "cbc", "Line", direccion)

    # Customer (AccountingCustomerParty)
    customer = _sub(root, "cac", "AccountingCustomerParty")
    customer_party = _sub(customer, "cac", "Party")
    customer_id = _sub(customer_party, "cac", "PartyIdentification")
    client_doc_type = _client_doc_type(client.doc_type)
    _sub(customer_id, "cbc", "ID", client.doc_number or "00000000",
         schemeID=client_doc_type, schemeName="Documento de Identidad",
         schemeAgencyName="PE:SUNAT", schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06")
    customer_legal = _sub(customer_party, "cac", "PartyLegalEntity")
    _sub(customer_legal, "cbc", "RegistrationName", client.business_name)

    # Calculate totals
    total_gravada = Decimal("0")
    total_igv = Decimal("0")
    line_items_data = []

    for item in sale.items:
        qty = Decimal(str(item.quantity))
        price_with_igv = Decimal(str(item.unit_price))
        discount_factor = Decimal("1") - (Decimal(str(item.discount_pct)) / Decimal("100"))
        precio_unitario = (price_with_igv * discount_factor).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        valor_unitario = (precio_unitario / IGV_FACTOR).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        line_gravada = (valor_unitario * qty).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        line_igv = (line_gravada * IGV_RATE).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        total_gravada += line_gravada
        total_igv += line_igv
        line_items_data.append({
            "qty": qty,
            "precio_unitario": precio_unitario,
            "valor_unitario": valor_unitario,
            "line_gravada": line_gravada,
            "line_igv": line_igv,
            "description": item.product_name or "PRODUCTO",
        })

    total = total_gravada + total_igv

    # PaymentTerms (required by SUNAT - error 3244)
    payment_terms = _sub(root, "cac", "PaymentTerms")
    _sub(payment_terms, "cbc", "ID", "FormaPago")
    payment_cond = getattr(sale, "payment_cond", "CONTADO") or "CONTADO"
    if payment_cond.startswith("CREDITO"):
        _sub(payment_terms, "cbc", "PaymentMeansID", "Credito")
        _sub(payment_terms, "cbc", "Amount", _dec(total), currencyID="PEN")
    else:
        _sub(payment_terms, "cbc", "PaymentMeansID", "Contado")

    # TaxTotal
    tax_total = _sub(root, "cac", "TaxTotal")
    _sub(tax_total, "cbc", "TaxAmount", _dec(total_igv), currencyID="PEN")
    tax_subtotal = _sub(tax_total, "cac", "TaxSubtotal")
    _sub(tax_subtotal, "cbc", "TaxableAmount", _dec(total_gravada), currencyID="PEN")
    _sub(tax_subtotal, "cbc", "TaxAmount", _dec(total_igv), currencyID="PEN")
    tax_category = _sub(tax_subtotal, "cac", "TaxCategory")
    tax_scheme = _sub(tax_category, "cac", "TaxScheme")
    _sub(tax_scheme, "cbc", "ID", "1000",
         schemeName="Codigo de tributos", schemeAgencyName="PE:SUNAT",
         schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo05")
    _sub(tax_scheme, "cbc", "Name", "IGV")
    _sub(tax_scheme, "cbc", "TaxTypeCode", "VAT")

    # LegalMonetaryTotal
    monetary = _sub(root, "cac", "LegalMonetaryTotal")
    _sub(monetary, "cbc", "LineExtensionAmount", _dec(total_gravada), currencyID="PEN")
    _sub(monetary, "cbc", "TaxInclusiveAmount", _dec(total), currencyID="PEN")
    _sub(monetary, "cbc", "PayableAmount", _dec(total), currencyID="PEN")

    # InvoiceLines
    for idx, item_data in enumerate(line_items_data, start=1):
        line = _sub(root, "cac", "InvoiceLine")
        _sub(line, "cbc", "ID", str(idx))
        _sub(line, "cbc", "InvoicedQuantity", str(item_data["qty"]),
             unitCode="NIU", unitCodeListID="UN/ECE rec 20",
             unitCodeListAgencyName="United Nations Economic Commission for Europe")
        _sub(line, "cbc", "LineExtensionAmount", _dec(item_data["line_gravada"]),
             currencyID="PEN")

        # PricingReference (price WITH IGV)
        pricing_ref = _sub(line, "cac", "PricingReference")
        alt_price = _sub(pricing_ref, "cac", "AlternativeConditionPrice")
        _sub(alt_price, "cbc", "PriceAmount", _dec(item_data["precio_unitario"]),
             currencyID="PEN")
        _sub(alt_price, "cbc", "PriceTypeCode", "01",
             listName="Tipo de Precio", listAgencyName="PE:SUNAT",
             listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo16")

        # TaxTotal per line
        line_tax = _sub(line, "cac", "TaxTotal")
        _sub(line_tax, "cbc", "TaxAmount", _dec(item_data["line_igv"]), currencyID="PEN")
        line_tax_sub = _sub(line_tax, "cac", "TaxSubtotal")
        _sub(line_tax_sub, "cbc", "TaxableAmount", _dec(item_data["line_gravada"]),
             currencyID="PEN")
        _sub(line_tax_sub, "cbc", "TaxAmount", _dec(item_data["line_igv"]),
             currencyID="PEN")
        line_tax_cat = _sub(line_tax_sub, "cac", "TaxCategory")
        _sub(line_tax_cat, "cbc", "Percent", "18.00")
        _sub(line_tax_cat, "cbc", "TaxExemptionReasonCode", "10",
             listAgencyName="PE:SUNAT",
             listName="Afectacion del IGV",
             listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07")
        line_tax_scheme = _sub(line_tax_cat, "cac", "TaxScheme")
        _sub(line_tax_scheme, "cbc", "ID", "1000",
             schemeName="Codigo de tributos", schemeAgencyName="PE:SUNAT",
             schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo05")
        _sub(line_tax_scheme, "cbc", "Name", "IGV")
        _sub(line_tax_scheme, "cbc", "TaxTypeCode", "VAT")

        # Item description
        line_item = _sub(line, "cac", "Item")
        _sub(line_item, "cbc", "Description", item_data["description"])

        # Price (unit value WITHOUT IGV)
        price = _sub(line, "cac", "Price")
        _sub(price, "cbc", "PriceAmount", _dec(item_data["valor_unitario"]),
             currencyID="PEN")

    xml_bytes = etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                               pretty_print=True)
    return xml_bytes


NS_CREDIT_NOTE = {
    "": "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "sac": "urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1",
}


def build_credit_note_xml(sale: Sale) -> bytes:
    """
    Build UBL 2.1 CreditNote XML for SUNAT (document type 07).
    The sale must have ref_sale loaded with its client.
    Returns XML bytes.
    """
    ruc, razon_social, direccion = _empresa()
    issue = sale.issue_date or date.today()
    client = sale.client
    ref_sale = sale.ref_sale

    nsmap = {None: NS_CREDIT_NOTE[""]}
    for k, v in NS_CREDIT_NOTE.items():
        if k:
            nsmap[k] = v

    root = etree.Element(_tag("", "CreditNote", NS_CREDIT_NOTE), nsmap=nsmap)

    # UBLExtensions (placeholder for signature)
    extensions = _sub(root, "ext", "UBLExtensions", ns_map=NS_CREDIT_NOTE)
    extension = _sub(extensions, "ext", "UBLExtension", ns_map=NS_CREDIT_NOTE)
    _sub(extension, "ext", "ExtensionContent", ns_map=NS_CREDIT_NOTE)

    # Header
    _sub(root, "cbc", "UBLVersionID", "2.1", ns_map=NS_CREDIT_NOTE)
    _sub(root, "cbc", "CustomizationID", "2.0", ns_map=NS_CREDIT_NOTE)
    _sub(root, "cbc", "ID", f"{sale.series}-{int(sale.doc_number):08d}", ns_map=NS_CREDIT_NOTE)
    _sub(root, "cbc", "IssueDate", issue.isoformat(), ns_map=NS_CREDIT_NOTE)
    _sub(root, "cbc", "IssueTime", "00:00:00", ns_map=NS_CREDIT_NOTE)
    _sub(root, "cbc", "DocumentCurrencyCode", "PEN",
         listID="ISO 4217 Alpha", listName="Currency",
         listAgencyName="United Nations Economic Commission for Europe",
         ns_map=NS_CREDIT_NOTE)

    # DiscrepancyResponse — reason for the credit note
    discrepancy = _sub(root, "cac", "DiscrepancyResponse", ns_map=NS_CREDIT_NOTE)
    # Reference to original document
    ref_doc_type = _doc_type_code(ref_sale.doc_type) if ref_sale else "01"
    ref_doc_id = f"{ref_sale.series}-{ref_sale.doc_number}" if ref_sale else ""
    _sub(discrepancy, "cbc", "ReferenceID", ref_doc_id, ns_map=NS_CREDIT_NOTE)
    _sub(discrepancy, "cbc", "ResponseCode", sale.nc_motivo_code or "01",
         listAgencyName="PE:SUNAT",
         listName="Tipo de nota de credito",
         listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo09",
         ns_map=NS_CREDIT_NOTE)
    _sub(discrepancy, "cbc", "Description", sale.nc_motivo_text or "Anulacion de la operacion",
         ns_map=NS_CREDIT_NOTE)

    # BillingReference — original document
    billing_ref = _sub(root, "cac", "BillingReference", ns_map=NS_CREDIT_NOTE)
    invoice_doc_ref = _sub(billing_ref, "cac", "InvoiceDocumentReference", ns_map=NS_CREDIT_NOTE)
    _sub(invoice_doc_ref, "cbc", "ID", ref_doc_id, ns_map=NS_CREDIT_NOTE)
    _sub(invoice_doc_ref, "cbc", "DocumentTypeCode", ref_doc_type,
         listAgencyName="PE:SUNAT",
         listName="Tipo de Documento",
         listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo01",
         ns_map=NS_CREDIT_NOTE)

    # Signature reference
    sig_ref = _sub(root, "cac", "Signature", ns_map=NS_CREDIT_NOTE)
    _sub(sig_ref, "cbc", "ID", f"IDSign{ruc}", ns_map=NS_CREDIT_NOTE)
    sig_party = _sub(sig_ref, "cac", "SignatoryParty", ns_map=NS_CREDIT_NOTE)
    sig_party_id = _sub(sig_party, "cac", "PartyIdentification", ns_map=NS_CREDIT_NOTE)
    _sub(sig_party_id, "cbc", "ID", ruc, ns_map=NS_CREDIT_NOTE)
    sig_party_name = _sub(sig_party, "cac", "PartyName", ns_map=NS_CREDIT_NOTE)
    _sub(sig_party_name, "cbc", "Name", razon_social, ns_map=NS_CREDIT_NOTE)
    sig_attach = _sub(sig_ref, "cac", "DigitalSignatureAttachment", ns_map=NS_CREDIT_NOTE)
    sig_ext_ref = _sub(sig_attach, "cac", "ExternalReference", ns_map=NS_CREDIT_NOTE)
    _sub(sig_ext_ref, "cbc", "URI", f"#SignatureValue-{ruc}", ns_map=NS_CREDIT_NOTE)

    # Supplier (AccountingSupplierParty)
    supplier = _sub(root, "cac", "AccountingSupplierParty", ns_map=NS_CREDIT_NOTE)
    supplier_party = _sub(supplier, "cac", "Party", ns_map=NS_CREDIT_NOTE)
    supplier_id = _sub(supplier_party, "cac", "PartyIdentification", ns_map=NS_CREDIT_NOTE)
    _sub(supplier_id, "cbc", "ID", ruc,
         schemeID="6", schemeName="Documento de Identidad",
         schemeAgencyName="PE:SUNAT",
         schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06",
         ns_map=NS_CREDIT_NOTE)
    supplier_name = _sub(supplier_party, "cac", "PartyName", ns_map=NS_CREDIT_NOTE)
    _sub(supplier_name, "cbc", "Name", razon_social, ns_map=NS_CREDIT_NOTE)
    supplier_legal = _sub(supplier_party, "cac", "PartyLegalEntity", ns_map=NS_CREDIT_NOTE)
    _sub(supplier_legal, "cbc", "RegistrationName", razon_social, ns_map=NS_CREDIT_NOTE)
    supplier_addr = _sub(supplier_legal, "cac", "RegistrationAddress", ns_map=NS_CREDIT_NOTE)
    _sub(supplier_addr, "cbc", "AddressTypeCode", "0000", ns_map=NS_CREDIT_NOTE)
    addr_line = _sub(supplier_addr, "cac", "AddressLine", ns_map=NS_CREDIT_NOTE)
    _sub(addr_line, "cbc", "Line", direccion, ns_map=NS_CREDIT_NOTE)

    # Customer (AccountingCustomerParty)
    customer = _sub(root, "cac", "AccountingCustomerParty", ns_map=NS_CREDIT_NOTE)
    customer_party = _sub(customer, "cac", "Party", ns_map=NS_CREDIT_NOTE)
    customer_id = _sub(customer_party, "cac", "PartyIdentification", ns_map=NS_CREDIT_NOTE)
    client_doc_type = _client_doc_type(client.doc_type)
    _sub(customer_id, "cbc", "ID", client.doc_number or "00000000",
         schemeID=client_doc_type, schemeName="Documento de Identidad",
         schemeAgencyName="PE:SUNAT",
         schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06",
         ns_map=NS_CREDIT_NOTE)
    customer_legal = _sub(customer_party, "cac", "PartyLegalEntity", ns_map=NS_CREDIT_NOTE)
    _sub(customer_legal, "cbc", "RegistrationName", client.business_name, ns_map=NS_CREDIT_NOTE)

    # Calculate totals
    total_gravada = Decimal("0")
    total_igv = Decimal("0")
    line_items_data = []

    for item in sale.items:
        qty = Decimal(str(item.quantity))
        price_with_igv = Decimal(str(item.unit_price))
        discount_factor = Decimal("1") - (Decimal(str(item.discount_pct)) / Decimal("100"))
        precio_unitario = (price_with_igv * discount_factor).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        valor_unitario = (precio_unitario / IGV_FACTOR).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        line_gravada = (valor_unitario * qty).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        line_igv = (line_gravada * IGV_RATE).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        total_gravada += line_gravada
        total_igv += line_igv
        line_items_data.append({
            "qty": qty,
            "precio_unitario": precio_unitario,
            "valor_unitario": valor_unitario,
            "line_gravada": line_gravada,
            "line_igv": line_igv,
            "description": item.product_name or "PRODUCTO",
        })

    total = total_gravada + total_igv

    # TaxTotal
    tax_total = _sub(root, "cac", "TaxTotal", ns_map=NS_CREDIT_NOTE)
    _sub(tax_total, "cbc", "TaxAmount", _dec(total_igv), currencyID="PEN", ns_map=NS_CREDIT_NOTE)
    tax_subtotal = _sub(tax_total, "cac", "TaxSubtotal", ns_map=NS_CREDIT_NOTE)
    _sub(tax_subtotal, "cbc", "TaxableAmount", _dec(total_gravada), currencyID="PEN", ns_map=NS_CREDIT_NOTE)
    _sub(tax_subtotal, "cbc", "TaxAmount", _dec(total_igv), currencyID="PEN", ns_map=NS_CREDIT_NOTE)
    tax_category = _sub(tax_subtotal, "cac", "TaxCategory", ns_map=NS_CREDIT_NOTE)
    tax_scheme = _sub(tax_category, "cac", "TaxScheme", ns_map=NS_CREDIT_NOTE)
    _sub(tax_scheme, "cbc", "ID", "1000",
         schemeName="Codigo de tributos", schemeAgencyName="PE:SUNAT",
         schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo05",
         ns_map=NS_CREDIT_NOTE)
    _sub(tax_scheme, "cbc", "Name", "IGV", ns_map=NS_CREDIT_NOTE)
    _sub(tax_scheme, "cbc", "TaxTypeCode", "VAT", ns_map=NS_CREDIT_NOTE)

    # LegalMonetaryTotal
    monetary = _sub(root, "cac", "LegalMonetaryTotal", ns_map=NS_CREDIT_NOTE)
    _sub(monetary, "cbc", "LineExtensionAmount", _dec(total_gravada), currencyID="PEN", ns_map=NS_CREDIT_NOTE)
    _sub(monetary, "cbc", "TaxInclusiveAmount", _dec(total), currencyID="PEN", ns_map=NS_CREDIT_NOTE)
    _sub(monetary, "cbc", "PayableAmount", _dec(total), currencyID="PEN", ns_map=NS_CREDIT_NOTE)

    # CreditNoteLines
    for idx, item_data in enumerate(line_items_data, start=1):
        line = _sub(root, "cac", "CreditNoteLine", ns_map=NS_CREDIT_NOTE)
        _sub(line, "cbc", "ID", str(idx), ns_map=NS_CREDIT_NOTE)
        _sub(line, "cbc", "CreditedQuantity", str(item_data["qty"]),
             unitCode="NIU", unitCodeListID="UN/ECE rec 20",
             unitCodeListAgencyName="United Nations Economic Commission for Europe",
             ns_map=NS_CREDIT_NOTE)
        _sub(line, "cbc", "LineExtensionAmount", _dec(item_data["line_gravada"]),
             currencyID="PEN", ns_map=NS_CREDIT_NOTE)

        # PricingReference (price WITH IGV)
        pricing_ref = _sub(line, "cac", "PricingReference", ns_map=NS_CREDIT_NOTE)
        alt_price = _sub(pricing_ref, "cac", "AlternativeConditionPrice", ns_map=NS_CREDIT_NOTE)
        _sub(alt_price, "cbc", "PriceAmount", _dec(item_data["precio_unitario"]),
             currencyID="PEN", ns_map=NS_CREDIT_NOTE)
        _sub(alt_price, "cbc", "PriceTypeCode", "01",
             listName="Tipo de Precio", listAgencyName="PE:SUNAT",
             listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo16",
             ns_map=NS_CREDIT_NOTE)

        # TaxTotal per line
        line_tax = _sub(line, "cac", "TaxTotal", ns_map=NS_CREDIT_NOTE)
        _sub(line_tax, "cbc", "TaxAmount", _dec(item_data["line_igv"]),
             currencyID="PEN", ns_map=NS_CREDIT_NOTE)
        line_tax_sub = _sub(line_tax, "cac", "TaxSubtotal", ns_map=NS_CREDIT_NOTE)
        _sub(line_tax_sub, "cbc", "TaxableAmount", _dec(item_data["line_gravada"]),
             currencyID="PEN", ns_map=NS_CREDIT_NOTE)
        _sub(line_tax_sub, "cbc", "TaxAmount", _dec(item_data["line_igv"]),
             currencyID="PEN", ns_map=NS_CREDIT_NOTE)
        line_tax_cat = _sub(line_tax_sub, "cac", "TaxCategory", ns_map=NS_CREDIT_NOTE)
        _sub(line_tax_cat, "cbc", "Percent", "18.00", ns_map=NS_CREDIT_NOTE)
        _sub(line_tax_cat, "cbc", "TaxExemptionReasonCode", "10",
             listAgencyName="PE:SUNAT",
             listName="Afectacion del IGV",
             listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo07",
             ns_map=NS_CREDIT_NOTE)
        line_tax_scheme = _sub(line_tax_cat, "cac", "TaxScheme", ns_map=NS_CREDIT_NOTE)
        _sub(line_tax_scheme, "cbc", "ID", "1000",
             schemeName="Codigo de tributos", schemeAgencyName="PE:SUNAT",
             schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo05",
             ns_map=NS_CREDIT_NOTE)
        _sub(line_tax_scheme, "cbc", "Name", "IGV", ns_map=NS_CREDIT_NOTE)
        _sub(line_tax_scheme, "cbc", "TaxTypeCode", "VAT", ns_map=NS_CREDIT_NOTE)

        # Item description
        line_item = _sub(line, "cac", "Item", ns_map=NS_CREDIT_NOTE)
        _sub(line_item, "cbc", "Description", item_data["description"], ns_map=NS_CREDIT_NOTE)

        # Price (unit value WITHOUT IGV)
        price = _sub(line, "cac", "Price", ns_map=NS_CREDIT_NOTE)
        _sub(price, "cbc", "PriceAmount", _dec(item_data["valor_unitario"]),
             currencyID="PEN", ns_map=NS_CREDIT_NOTE)

    xml_bytes = etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                               pretty_print=True)
    return xml_bytes


def get_credit_note_filename(sale: Sale) -> str:
    """Get SUNAT standard filename for a credit note (tipo 07)."""
    ruc, _, _ = _empresa()
    return f"{ruc}-07-{sale.series}-{int(sale.doc_number):08d}"


def build_summary_xml(fecha: date, sales: list[Sale], correlativo: int = 1,
                      condition_codes: dict[int, str] | None = None) -> bytes:
    """
    Build SummaryDocuments XML (resumen diario de boletas).
    condition_codes: dict mapping sale.id -> ConditionCode (1=Adicionar, 3=Anulado).
    Defaults to "1" for all sales if not provided.
    Returns XML bytes.
    """
    ruc, razon_social, _ = _empresa()
    today = date.today()

    nsmap = {None: NS_SUMMARY[""]}
    for k, v in NS_SUMMARY.items():
        if k:
            nsmap[k] = v

    root = etree.Element(_tag("", "SummaryDocuments", NS_SUMMARY), nsmap=nsmap)

    # UBLExtensions (placeholder for signature)
    extensions = _sub(root, "ext", "UBLExtensions", ns_map=NS_SUMMARY)
    extension = _sub(extensions, "ext", "UBLExtension", ns_map=NS_SUMMARY)
    _sub(extension, "ext", "ExtensionContent", ns_map=NS_SUMMARY)

    # Header
    _sub(root, "cbc", "UBLVersionID", "2.0", ns_map=NS_SUMMARY)
    _sub(root, "cbc", "CustomizationID", "1.1", ns_map=NS_SUMMARY)

    # ID: RC-YYYYMMDD-#####
    summary_id = f"RC-{today.strftime('%Y%m%d')}-{str(correlativo).zfill(5)}"
    _sub(root, "cbc", "ID", summary_id, ns_map=NS_SUMMARY)
    _sub(root, "cbc", "ReferenceDate", fecha.isoformat(), ns_map=NS_SUMMARY)
    _sub(root, "cbc", "IssueDate", today.isoformat(), ns_map=NS_SUMMARY)

    # Signature reference
    sig_ref = _sub(root, "cac", "Signature", ns_map=NS_SUMMARY)
    _sub(sig_ref, "cbc", "ID", f"IDSign{ruc}", ns_map=NS_SUMMARY)
    sig_party = _sub(sig_ref, "cac", "SignatoryParty", ns_map=NS_SUMMARY)
    sig_party_id = _sub(sig_party, "cac", "PartyIdentification", ns_map=NS_SUMMARY)
    _sub(sig_party_id, "cbc", "ID", ruc, ns_map=NS_SUMMARY)
    sig_party_name = _sub(sig_party, "cac", "PartyName", ns_map=NS_SUMMARY)
    _sub(sig_party_name, "cbc", "Name", razon_social, ns_map=NS_SUMMARY)
    sig_attach = _sub(sig_ref, "cac", "DigitalSignatureAttachment", ns_map=NS_SUMMARY)
    sig_ext_ref = _sub(sig_attach, "cac", "ExternalReference", ns_map=NS_SUMMARY)
    _sub(sig_ext_ref, "cbc", "URI", f"#SignatureValue-{ruc}", ns_map=NS_SUMMARY)

    # Supplier
    supplier = _sub(root, "cac", "AccountingSupplierParty", ns_map=NS_SUMMARY)
    _sub(supplier, "cbc", "CustomerAssignedAccountID", ruc, ns_map=NS_SUMMARY)
    _sub(supplier, "cbc", "AdditionalAccountID", "6", ns_map=NS_SUMMARY)
    supplier_party = _sub(supplier, "cac", "Party", ns_map=NS_SUMMARY)
    supplier_legal = _sub(supplier_party, "cac", "PartyLegalEntity", ns_map=NS_SUMMARY)
    _sub(supplier_legal, "cbc", "RegistrationName", razon_social, ns_map=NS_SUMMARY)

    # Summary lines (v1.1 format)
    for idx, sale in enumerate(sales, start=1):
        total_with_igv = Decimal(str(sale.total))
        gravada = (total_with_igv / IGV_FACTOR).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        igv = (gravada * IGV_RATE).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_calc = gravada + igv

        line = _sub(root, "sac", "SummaryDocumentsLine", ns_map=NS_SUMMARY)
        _sub(line, "cbc", "LineID", str(idx), ns_map=NS_SUMMARY)

        # Document type: 03=boleta, 07=nota de credito
        doc_type_code = "07" if sale.doc_type == "NOTA_CREDITO" else "03"
        _sub(line, "cbc", "DocumentTypeCode", doc_type_code, ns_map=NS_SUMMARY)

        # v1.1: full document ID
        doc_id = f"{sale.series}-{sale.doc_number}"
        _sub(line, "cbc", "ID", doc_id, ns_map=NS_SUMMARY)

        # v1.1: customer wrapped in AccountingCustomerParty
        client_doc_type = _client_doc_type(sale.client.doc_type)
        acct_customer = _sub(line, "cac", "AccountingCustomerParty", ns_map=NS_SUMMARY)
        _sub(acct_customer, "cbc", "CustomerAssignedAccountID",
             sale.client.doc_number or "00000000", ns_map=NS_SUMMARY)
        _sub(acct_customer, "cbc", "AdditionalAccountID", client_doc_type, ns_map=NS_SUMMARY)

        # Status (1=Adicionar, 2=Modificar, 3=Anulado)
        cond_code = (condition_codes or {}).get(sale.id, "1")
        status_el = _sub(line, "cac", "Status", ns_map=NS_SUMMARY)
        _sub(status_el, "cbc", "ConditionCode", cond_code, ns_map=NS_SUMMARY)

        # Total amount
        _sub(line, "sac", "TotalAmount", _dec(total_calc),
             currencyID="PEN", ns_map=NS_SUMMARY)

        # Billing payment (gravada)
        billing = _sub(line, "sac", "BillingPayment", ns_map=NS_SUMMARY)
        _sub(billing, "cbc", "PaidAmount", _dec(gravada),
             currencyID="PEN", ns_map=NS_SUMMARY)
        _sub(billing, "cbc", "InstructionID", "01", ns_map=NS_SUMMARY)

        # Tax total (IGV)
        tax_total = _sub(line, "cac", "TaxTotal", ns_map=NS_SUMMARY)
        _sub(tax_total, "cbc", "TaxAmount", _dec(igv),
             currencyID="PEN", ns_map=NS_SUMMARY)
        tax_subtotal = _sub(tax_total, "cac", "TaxSubtotal", ns_map=NS_SUMMARY)
        _sub(tax_subtotal, "cbc", "TaxAmount", _dec(igv),
             currencyID="PEN", ns_map=NS_SUMMARY)
        tax_category = _sub(tax_subtotal, "cac", "TaxCategory", ns_map=NS_SUMMARY)
        _sub(tax_category, "cbc", "Percent", "18.00", ns_map=NS_SUMMARY)
        tax_scheme = _sub(tax_category, "cac", "TaxScheme", ns_map=NS_SUMMARY)
        _sub(tax_scheme, "cbc", "ID", "1000", ns_map=NS_SUMMARY)
        _sub(tax_scheme, "cbc", "Name", "IGV", ns_map=NS_SUMMARY)
        _sub(tax_scheme, "cbc", "TaxTypeCode", "VAT", ns_map=NS_SUMMARY)

    xml_bytes = etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                               pretty_print=True)
    return xml_bytes


def build_voided_xml(fecha: date, sales: list[Sale], correlativo: int = 1,
                     motivo: str = "ANULACION DE OPERACION") -> bytes:
    """
    Build VoidedDocuments XML (comunicacion de baja).
    Returns XML bytes.
    """
    ruc, razon_social, _ = _empresa()
    today = date.today()

    nsmap = {None: NS_VOIDED[""]}
    for k, v in NS_VOIDED.items():
        if k:
            nsmap[k] = v

    root = etree.Element(_tag("", "VoidedDocuments", NS_VOIDED), nsmap=nsmap)

    # UBLExtensions (placeholder for signature)
    extensions = _sub(root, "ext", "UBLExtensions", ns_map=NS_VOIDED)
    extension = _sub(extensions, "ext", "UBLExtension", ns_map=NS_VOIDED)
    _sub(extension, "ext", "ExtensionContent", ns_map=NS_VOIDED)

    # Header
    _sub(root, "cbc", "UBLVersionID", "2.0", ns_map=NS_VOIDED)
    _sub(root, "cbc", "CustomizationID", "1.0", ns_map=NS_VOIDED)

    # ID: RA-YYYYMMDD-#####
    voided_id = f"RA-{today.strftime('%Y%m%d')}-{str(correlativo).zfill(5)}"
    _sub(root, "cbc", "ID", voided_id, ns_map=NS_VOIDED)
    _sub(root, "cbc", "ReferenceDate", fecha.isoformat(), ns_map=NS_VOIDED)
    _sub(root, "cbc", "IssueDate", today.isoformat(), ns_map=NS_VOIDED)

    # Signature reference
    sig_ref = _sub(root, "cac", "Signature", ns_map=NS_VOIDED)
    _sub(sig_ref, "cbc", "ID", f"IDSign{ruc}", ns_map=NS_VOIDED)
    sig_party = _sub(sig_ref, "cac", "SignatoryParty", ns_map=NS_VOIDED)
    sig_party_id = _sub(sig_party, "cac", "PartyIdentification", ns_map=NS_VOIDED)
    _sub(sig_party_id, "cbc", "ID", ruc, ns_map=NS_VOIDED)
    sig_party_name = _sub(sig_party, "cac", "PartyName", ns_map=NS_VOIDED)
    _sub(sig_party_name, "cbc", "Name", razon_social, ns_map=NS_VOIDED)
    sig_attach = _sub(sig_ref, "cac", "DigitalSignatureAttachment", ns_map=NS_VOIDED)
    sig_ext_ref = _sub(sig_attach, "cac", "ExternalReference", ns_map=NS_VOIDED)
    _sub(sig_ext_ref, "cbc", "URI", f"#SignatureValue-{ruc}", ns_map=NS_VOIDED)

    # Supplier
    supplier = _sub(root, "cac", "AccountingSupplierParty", ns_map=NS_VOIDED)
    _sub(supplier, "cbc", "CustomerAssignedAccountID", ruc, ns_map=NS_VOIDED)
    _sub(supplier, "cbc", "AdditionalAccountID", "6", ns_map=NS_VOIDED)
    supplier_party = _sub(supplier, "cac", "Party", ns_map=NS_VOIDED)
    supplier_legal = _sub(supplier_party, "cac", "PartyLegalEntity", ns_map=NS_VOIDED)
    _sub(supplier_legal, "cbc", "RegistrationName", razon_social, ns_map=NS_VOIDED)

    # Voided lines
    for idx, sale in enumerate(sales, start=1):
        tipo_doc = _doc_type_code(sale.doc_type)

        line = _sub(root, "sac", "VoidedDocumentsLine", ns_map=NS_VOIDED)
        _sub(line, "cbc", "LineID", str(idx), ns_map=NS_VOIDED)
        _sub(line, "cbc", "DocumentTypeCode", tipo_doc, ns_map=NS_VOIDED)
        _sub(line, "sac", "DocumentSerialID", sale.series, ns_map=NS_VOIDED)
        _sub(line, "sac", "DocumentNumberID", str(sale.doc_number), ns_map=NS_VOIDED)
        _sub(line, "sac", "VoidReasonDescription", motivo, ns_map=NS_VOIDED)

    xml_bytes = etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                               pretty_print=True)
    return xml_bytes


def get_invoice_filename(sale: Sale) -> str:
    """Get SUNAT standard filename for an invoice."""
    ruc, _, _ = _empresa()
    tipo_doc = _doc_type_code(sale.doc_type)
    return f"{ruc}-{tipo_doc}-{sale.series}-{sale.doc_number}"


def get_summary_filename(correlativo: int = 1) -> str:
    """Get SUNAT standard filename for a summary document."""
    ruc, _, _ = _empresa()
    today = date.today()
    return f"{ruc}-RC-{today.strftime('%Y%m%d')}-{str(correlativo).zfill(5)}"


def get_voided_filename(correlativo: int = 1) -> str:
    """Get SUNAT standard filename for a voided document."""
    ruc, _, _ = _empresa()
    today = date.today()
    return f"{ruc}-RA-{today.strftime('%Y%m%d')}-{str(correlativo).zfill(5)}"
