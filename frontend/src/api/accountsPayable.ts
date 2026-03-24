import api from './client';

export interface SupplierPayment {
  id: number;
  purchase_order_id: number;
  amount: number;
  payment_date: string;
  payment_method: string;
  reference: string | null;
  notes: string | null;
  created_at: string;
  creator_name: string;
}

export interface AccountPayable {
  po_id: number;
  supplier_id: number;
  supplier_name: string;
  supplier_ruc: string | null;
  doc_type: string | null;
  doc_number: string | null;
  supplier_doc: string | null;
  total: number;
  paid: number;
  balance: number;
  received_at: string | null;
  due_date: string | null;
  status: string;
  days_overdue: number;
  moneda: string | null;
  payments: SupplierPayment[];
}

export interface AccountPayableSummary {
  total_debt: number;
  total_overdue: number;
  total_due_soon: number;
  count_pending: number;
  count_overdue: number;
  count_due_soon: number;
}

export interface PaymentCreateData {
  amount: number;
  payment_date: string;
  payment_method: string;
  reference?: string;
  notes?: string;
}

export async function getAccountsPayable(params?: { status_filter?: string; supplier_id?: number }): Promise<AccountPayable[]> {
  const { data } = await api.get('/accounts-payable', { params });
  return data;
}

export async function getAccountsPayableSummary(): Promise<AccountPayableSummary> {
  const { data } = await api.get('/accounts-payable/summary');
  return data;
}

export async function getPayments(poId: number): Promise<SupplierPayment[]> {
  const { data } = await api.get(`/accounts-payable/${poId}/payments`);
  return data;
}

export async function createPayment(poId: number, payload: PaymentCreateData): Promise<SupplierPayment> {
  const { data } = await api.post(`/accounts-payable/${poId}/payments`, payload);
  return data;
}

export async function deletePayment(paymentId: number): Promise<void> {
  await api.delete(`/accounts-payable/payments/${paymentId}`);
}
