import api from './client';
import type { Product, ProductSearch } from '../types';

export async function getProducts(params?: any): Promise<Product[]> {
  const { data } = await api.get('/products', { params });
  return data;
}

export async function getProduct(id: number): Promise<Product> {
  const { data } = await api.get(`/products/${id}`);
  return data;
}

export async function createProduct(productData: any): Promise<Product> {
  const { data } = await api.post('/products', productData);
  return data;
}

export async function updateProduct(id: number, productData: any): Promise<Product> {
  const { data } = await api.put(`/products/${id}`, productData);
  return data;
}

export async function deleteProduct(id: number): Promise<void> {
  await api.delete(`/products/${id}`);
}

export async function getNextProductCode(): Promise<string> {
  const { data } = await api.get('/products/next-code');
  return data.code;
}

export async function searchProducts(q: string): Promise<ProductSearch[]> {
  const { data } = await api.get('/products/search', { params: { q } });
  return data;
}

export async function syncOnlineProducts(): Promise<{ synced_products: number }> {
  const { data } = await api.post('/products/sync-online');
  return data;
}

export async function uploadProductImage(productId: number, file: File): Promise<Product> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post(`/products/${productId}/image`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}
