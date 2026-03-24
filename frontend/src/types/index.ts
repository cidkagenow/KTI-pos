export interface User {
  id: number;
  username: string;
  full_name: string;
  role: 'ADMIN' | 'VENTAS';
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Client {
  id: number;
  doc_type: string;
  doc_number: string | null;
  business_name: string;
  ref_comercial: string | null;
  address: string | null;
  zona: string | null;
  phone: string | null;
  email: string | null;
  comentario: string | null;
  credit_limit: number | null;
  credit_days: number | null;
  is_walk_in: boolean;
  is_active: boolean;
}

export interface Brand {
  id: number;
  name: string;
  is_active: boolean;
}

export interface Category {
  id: number;
  name: string;
  is_active: boolean;
}

export interface Product {
  id: number;
  code: string;
  name: string;
  brand_id: number | null;
  category_id: number | null;
  brand_name: string | null;
  category_name: string | null;
  presentation: string | null;
  unit_price: number;
  wholesale_price: number | null;
  cost_price: number | null;
  min_stock: number;
  comentario: string | null;
  total_stock: number;
  on_order_qty: number | null;
  on_order_eta: string | null;
  is_active: boolean;
  is_online: boolean;
  image_url: string | null;
}

export interface ProductSearch {
  id: number;
  code: string;
  name: string;
  brand_name: string | null;
  presentation: string | null;
  unit_price: number;
  wholesale_price: number | null;
  cost_price: number | null;
  stock: number;
  on_order_qty: number | null;
  on_order_eta: string | null;
}

export interface Warehouse {
  id: number;
  name: string;
  address: string | null;
  is_active: boolean;
}

export interface DocumentSeries {
  id: number;
  doc_type: string;
  series: string;
  next_number: number;
  is_active: boolean;
  is_default: boolean;
}

export interface SaleItem {
  id?: number;
  product_id: number;
  quantity: number;
  unit_price: number;
  discount_pct: number;
  line_total: number;
  product_code: string;
  product_name: string;
  brand_name: string | null;
  presentation: string | null;
}

export interface Trabajador {
  id: number;
  full_name: string;
  dni: string;
  phone: string | null;
  cargo: string;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface Asistencia {
  id: number;
  trabajador_id: number;
  trabajador_name: string;
  date: string;
  check_in_time: string | null;
  check_out_time: string | null;
  status: string;
  notes: string | null;
  created_at: string;
}

export interface Sale {
  id: number;
  doc_type: string;
  series: string;
  doc_number: number | null;
  client_id: number;
  client_name: string;
  client_doc_type: string | null;
  client_doc_number: string | null;
  client_address: string | null;
  warehouse_id: number;
  seller_id: number | null;
  trabajador_id: number | null;
  seller_name: string;
  payment_cond: string;
  payment_method: string | null;
  cash_received: number | null;
  cash_change: number | null;
  max_discount_pct: number | null;
  subtotal: number;
  igv_amount: number;
  total: number;
  status: string;
  notes: string | null;
  issue_date: string;
  created_at: string;
  updated_at: string | null;
  items: SaleItem[];
  sunat_status?: string | null;
  sunat_description?: string | null;
  sunat_hash?: string | null;
  ref_sale_id?: number | null;
  ref_sale_series?: string | null;
  ref_sale_doc_number?: number | null;
  nc_motivo_code?: string | null;
  nc_motivo_text?: string | null;
}

export interface NotaCreditoCreate {
  ref_sale_id: number;
  nc_motivo_code: string;
  nc_motivo_text: string;
  items: { product_id: number; quantity: number; unit_price: number; discount_pct: number }[];
}

export interface SunatDocument {
  id: number;
  sale_id: number | null;
  doc_category: string;
  reference_date: string | null;
  ticket: string | null;
  sunat_status: string;
  sunat_description: string | null;
  sunat_hash: string | null;
  sunat_cdr_url: string | null;
  sunat_xml_url: string | null;
  sunat_pdf_url: string | null;
  attempt_count: number;
  last_attempt_at: string | null;
  sent_by: number | null;
  created_at: string;
  doc_type: string | null;
  series: string | null;
  doc_number: number | null;
  client_name: string | null;
  total: number | null;
}

export interface InventoryItem {
  id: number;
  product_id: number;
  product_code: string;
  product_name: string;
  warehouse_id: number;
  warehouse_name: string;
  quantity: number;
}

export interface InventoryMovement {
  id: number;
  product_id: number;
  product_name: string;
  warehouse_id: number;
  warehouse_name: string;
  movement_type: string;
  quantity: number;
  reference_type: string | null;
  reference_id: number | null;
  notes: string | null;
  created_at: string;
}

export interface Supplier {
  id: number;
  ruc: string | null;
  business_name: string;
  city: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  is_active: boolean;
}

export interface PurchaseOrderItem {
  id?: number;
  product_id: number;
  product_code?: string;
  product_name?: string;
  quantity: number;
  unit_cost: number;
  discount_pct1: number;
  discount_pct2: number;
  discount_pct3: number;
  flete_unit: number;
  line_total: number;
}

export interface PurchaseOrder {
  id: number;
  supplier_id: number;
  supplier_name: string;
  supplier_ruc: string | null;
  warehouse_id: number;
  status: string;
  doc_type: string | null;
  doc_number: string | null;
  supplier_doc: string | null;
  condicion: string | null;
  moneda: string | null;
  tipo_cambio: number | null;
  igv_included: boolean | null;
  subtotal: number | null;
  igv_amount: number | null;
  total: number | null;
  flete: number | null;
  grr_number: string | null;
  notes: string | null;
  issue_date: string | null;
  received_at: string | null;
  expected_delivery_date: string | null;
  created_at: string;
  items: PurchaseOrderItem[];
}

export interface DashboardStats {
  today_sales: number;
  today_total: number;
  week_sales: number;
  week_total: number;
  month_sales: number;
  month_total: number;
  low_stock_count: number;
}

export interface SalesByPeriod {
  period: string;
  count: number;
  total: number;
}

export interface TopProduct {
  product_name: string;
  quantity_sold: number;
  total_revenue: number;
}

export interface ProfitReport {
  product_code: string;
  product_name: string;
  brand_name: string | null;
  quantity_sold: number;
  total_revenue: number;
  total_cost: number;
  profit: number;
  profit_margin: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
}

// Online Orders
export interface OnlineOrderItem {
  id: number;
  product_id: number;
  quantity: number;
  unit_price: number;
  line_total: number;
  product_code: string;
  product_name: string;
  brand_name: string | null;
  presentation: string | null;
}

export interface OnlineOrder {
  id: number;
  order_code: string;
  customer_name: string;
  customer_phone: string;
  customer_email: string | null;
  payment_method: string;
  payment_reference: string | null;
  subtotal: number;
  igv_amount: number;
  total: number;
  status: string;
  confirmed_at: string | null;
  ready_at: string | null;
  picked_up_at: string | null;
  cancelled_at: string | null;
  cancel_reason: string | null;
  created_at: string;
  items: OnlineOrderItem[];
}

export interface OnlineOrderStats {
  pendiente: number;
  confirmado: number;
  listo: number;
  recogido: number;
  cancelado: number;
}
