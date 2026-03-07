import api from './client';
import type { Brand, Category, Warehouse, DocumentSeries, Supplier } from '../types';

export async function getBrands(): Promise<Brand[]> {
  return (await api.get('/catalogs/brands')).data;
}

export async function createBrand(data: any): Promise<Brand> {
  return (await api.post('/catalogs/brands', data)).data;
}

export async function updateBrand(id: number, data: any): Promise<Brand> {
  return (await api.put(`/catalogs/brands/${id}`, data)).data;
}

export async function deleteBrand(id: number): Promise<void> {
  await api.delete(`/catalogs/brands/${id}`);
}

export async function getCategories(): Promise<Category[]> {
  return (await api.get('/catalogs/categories')).data;
}

export async function createCategory(data: any): Promise<Category> {
  return (await api.post('/catalogs/categories', data)).data;
}

export async function updateCategory(id: number, data: any): Promise<Category> {
  return (await api.put(`/catalogs/categories/${id}`, data)).data;
}

export async function deleteCategory(id: number): Promise<void> {
  await api.delete(`/catalogs/categories/${id}`);
}

export async function getWarehouses(): Promise<Warehouse[]> {
  return (await api.get('/catalogs/warehouses')).data;
}

export async function createWarehouse(data: any): Promise<Warehouse> {
  return (await api.post('/catalogs/warehouses', data)).data;
}

export async function updateWarehouse(id: number, data: any): Promise<Warehouse> {
  return (await api.put(`/catalogs/warehouses/${id}`, data)).data;
}

export async function deleteWarehouse(id: number): Promise<void> {
  await api.delete(`/catalogs/warehouses/${id}`);
}

export async function getDocumentSeries(): Promise<DocumentSeries[]> {
  return (await api.get('/catalogs/document-series')).data;
}

export async function createDocumentSeries(data: any): Promise<DocumentSeries> {
  return (await api.post('/catalogs/document-series', data)).data;
}

export async function updateDocumentSeries(id: number, data: any): Promise<DocumentSeries> {
  return (await api.put(`/catalogs/document-series/${id}`, data)).data;
}

export async function getSuppliers(): Promise<Supplier[]> { return (await api.get('/catalogs/suppliers')).data; }
export async function createSupplier(data: any): Promise<Supplier> { return (await api.post('/catalogs/suppliers', data)).data; }
export async function updateSupplier(id: number, data: any): Promise<Supplier> { return (await api.put(`/catalogs/suppliers/${id}`, data)).data; }
export async function deleteSupplier(id: number): Promise<void> { await api.delete(`/catalogs/suppliers/${id}`); }
