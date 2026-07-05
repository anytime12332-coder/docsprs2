import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { TokenResponse } from './types';

// On Railway: frontend calls backend directly via NEXT_PUBLIC_API_URL
// Locally: defaults to empty string (same origin) or localhost
const API_BASE_RAW = typeof window !== 'undefined'
  ? (process.env.NEXT_PUBLIC_API_URL || '')
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');
const API_BASE = API_BASE_RAW.replace(/\/+$/, '');

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE}/api`,
      headers: { 'Content-Type': 'application/json' },
      timeout: 120000, // 2 min timeout for document processing
    });

    this.client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      if (typeof window !== 'undefined') {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401 && typeof window !== 'undefined') {
          const refreshToken = localStorage.getItem('refresh_token');
          if (refreshToken && !error.config._retry) {
            error.config._retry = true;
            try {
              const { data } = await axios.post<TokenResponse>(
                `${API_BASE}/api/auth/refresh`,
                { refresh_token: refreshToken }
              );
              localStorage.setItem('access_token', data.access_token);
              localStorage.setItem('refresh_token', data.refresh_token);
              error.config.headers.Authorization = `Bearer ${data.access_token}`;
              return this.client(error.config);
            } catch {
              localStorage.removeItem('access_token');
              localStorage.removeItem('refresh_token');
              window.location.href = '/login';
            }
          } else {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth
  login(email: string, password: string) {
    return this.client.post<TokenResponse>('/auth/login', { email, password });
  }

  getMe() {
    return this.client.get('/auth/me');
  }

  changePassword(currentPassword: string, newPassword: string) {
    return this.client.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  // Documents
  uploadDocument(file: File, options?: { tags?: string; notes?: string; autoProcess?: boolean; templateId?: string }) {
    const formData = new FormData();
    formData.append('file', file);
    if (options?.tags) formData.append('tags', options.tags);
    if (options?.notes) formData.append('notes', options.notes);
    if (options?.autoProcess) formData.append('auto_process', 'true');
    if (options?.templateId) formData.append('template_id', options.templateId);
    return this.client.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000, // 5 min for large uploads
    });
  }

  listDocuments(params?: Record<string, any>) {
    return this.client.get('/documents', { params });
  }

  getDocument(id: string) {
    return this.client.get(`/documents/${id}`);
  }

  updateDocument(id: string, data: Record<string, any>) {
    return this.client.patch(`/documents/${id}`, data);
  }

  deleteDocument(id: string) {
    return this.client.delete(`/documents/${id}`);
  }

  processDocument(id: string, options?: Record<string, any>) {
    return this.client.post(`/documents/${id}/process`, options || {});
  }

  processDocumentSync(id: string, options?: Record<string, any>) {
    return this.client.post(`/documents/process/sync/${id}`, options || {}, {
      timeout: 300000, // 5 min for processing
    });
  }

  bulkProcess(documentIds: string[], options?: Record<string, any>) {
    return this.client.post('/documents/bulk/process', {
      document_ids: documentIds,
      ...options,
    });
  }

  getDocumentStats() {
    return this.client.get('/documents/stats');
  }

  downloadDocument(id: string) {
    return this.client.get(`/documents/${id}/download`, { responseType: 'blob' });
  }

  // Extractions
  getDocumentExtractions(documentId: string) {
    return this.client.get(`/extractions/document/${documentId}`);
  }

  getExtraction(id: string) {
    return this.client.get(`/extractions/${id}`);
  }

  correctFields(corrections: { field_id: string; corrected_value: string }[]) {
    return this.client.post('/extractions/correct', { corrections });
  }

  validateExtraction(extractionId: string, corrections?: any[]) {
    return this.client.post('/extractions/validate', {
      extraction_id: extractionId,
      corrections,
    });
  }

  exportExtraction(id: string, format: string = 'json') {
    return this.client.get(`/extractions/${id}/export`, { params: { format } });
  }

  // Templates
  listTemplates(params?: Record<string, any>) {
    return this.client.get('/templates', { params });
  }

  getTemplate(id: string) {
    return this.client.get(`/templates/${id}`);
  }

  createTemplate(data: Record<string, any>) {
    return this.client.post('/templates', data);
  }

  updateTemplate(id: string, data: Record<string, any>) {
    return this.client.patch(`/templates/${id}`, data);
  }

  deleteTemplate(id: string) {
    return this.client.delete(`/templates/${id}`);
  }

  addTemplateField(templateId: string, data: Record<string, any>) {
    return this.client.post(`/templates/${templateId}/fields`, data);
  }

  removeTemplateField(fieldId: string) {
    return this.client.delete(`/templates/fields/${fieldId}`);
  }

  // Webhooks
  listWebhooks() {
    return this.client.get('/webhooks');
  }

  createWebhook(data: Record<string, any>) {
    return this.client.post('/webhooks', data);
  }

  updateWebhook(id: string, data: Record<string, any>) {
    return this.client.patch(`/webhooks/${id}`, data);
  }

  deleteWebhook(id: string) {
    return this.client.delete(`/webhooks/${id}`);
  }

  testWebhook(id: string) {
    return this.client.post(`/webhooks/${id}/test`);
  }

  getWebhookDeliveries(id: string) {
    return this.client.get(`/webhooks/${id}/deliveries`);
  }

  // Admin
  getSystemStats() {
    return this.client.get('/admin/stats');
  }

  listUsers(params?: Record<string, any>) {
    return this.client.get('/admin/users', { params });
  }

  createUser(data: Record<string, any>) {
    return this.client.post('/admin/users', data);
  }

  updateUser(id: string, data: Record<string, any>) {
    return this.client.patch(`/admin/users/${id}`, data);
  }

  deleteUser(id: string) {
    return this.client.delete(`/admin/users/${id}`);
  }

  getAuditLogs(params?: Record<string, any>) {
    return this.client.get('/admin/audit-logs', { params });
  }

  getSystemConfig() {
    return this.client.get('/admin/config');
  }
}

export const api = new ApiClient();
