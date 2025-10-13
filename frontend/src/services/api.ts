import axios, { AxiosError } from 'axios';
import type { AxiosInstance } from 'axios';
import type { ApiError } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      withCredentials: true, // Important: send httpOnly cookies
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest', // CSRF protection
      },
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        if (error.response?.status === 401) {
          // Unauthorized - redirect to login
          if (!window.location.pathname.includes('/login')) {
            const basename = '/financial-advisor-ai-app';
            window.location.href = `${basename}/login`;
          }
        }
        return Promise.reject(error);
      }
    );
  }

  async get<T>(url: string, params?: any): Promise<T> {
    const response = await this.client.get<T>(url, { params });
    return response.data;
  }

  async post<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.post<T>(url, data);
    return response.data;
  }

  async put<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.put<T>(url, data);
    return response.data;
  }

  async delete<T>(url: string): Promise<T> {
    const response = await this.client.delete<T>(url);
    return response.data;
  }

  // Ingestion endpoints
  async ingestGmail(gmailQuery?: string): Promise<any> {
    const params = gmailQuery ? { gmail_query: gmailQuery } : {};
    return this.post('/api/ingest/gmail', params);
  }

  async ingestHubspot(): Promise<any> {
    return this.post('/api/ingest/hubspot');
  }

  async getIngestStatus(): Promise<any> {
    return this.get('/api/ingest/status');
  }

  getBaseUrl(): string {
    return API_BASE_URL;
  }
}

export const apiClient = new ApiClient();
