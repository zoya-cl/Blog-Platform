import type { BlogListResponse, BlogDetail, BlogUpdateRequest } from './types';

const API_BASE = '/api';

export async function fetchBlogs(
  category?: string,
  status?: string,
  approved?: string,
  skip = 0,
  limit = 50
): Promise<BlogListResponse> {
  const params = new URLSearchParams();
  if (category) params.append('category', category);
  if (status) params.append('status', status);
  if (approved) params.append('approved', approved);
  params.append('skip', skip.toString());
  params.append('limit', limit.toString());

  const res = await fetch(`${API_BASE}/blogs?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch blogs: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchBlogBySlug(slug: string): Promise<BlogDetail> {
  const res = await fetch(`${API_BASE}/blogs/${slug}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch blog '${slug}': ${res.statusText}`);
  }
  return res.json();
}

export async function updateBlog(slug: string, body: BlogUpdateRequest): Promise<any> {
  const res = await fetch(`${API_BASE}/blogs/${slug}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`Failed to update blog '${slug}': ${res.statusText}`);
  }
  return res.json();
}

export async function approveBlog(slug: string, approved: 'yes' | 'no'): Promise<any> {
  const res = await fetch(`${API_BASE}/blogs/${slug}/approve`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approved }),
  });
  if (!res.ok) {
    throw new Error(`Failed to set approval for '${slug}': ${res.statusText}`);
  }
  return res.json();
}

export async function generateBlog(category?: string, topic?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/blogs/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category, topic }),
  });
  if (!res.ok) {
    throw new Error(`Failed to initiate blog generation: ${res.statusText}`);
  }
  return res.json();
}

export async function deleteBlog(slug: string): Promise<any> {
  const res = await fetch(`${API_BASE}/blogs/${slug}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error(`Failed to delete blog '${slug}': ${res.statusText}`);
  }
  return res.json();
}
