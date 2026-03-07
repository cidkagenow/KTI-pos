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

export async function searchProducts(q: string): Promise<ProductSearch[]> {
  const { data } = await api.get('/products/search', { params: { q } });
  return data;
}
