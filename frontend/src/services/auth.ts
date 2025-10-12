import { apiClient } from './api';
import type { User } from '../types';

export interface AuthResponse {
  user: User;
}

class AuthService {
  /**
   * Initiate Google OAuth flow
   */
  loginWithGoogle(): void {
    const baseUrl = apiClient.getBaseUrl();
    window.location.href = `${baseUrl}/api/auth/google/start`;
  }

  /**
   * Initiate HubSpot OAuth flow
   */
  connectHubSpot(): void {
    const baseUrl = apiClient.getBaseUrl();
    window.location.href = `${baseUrl}/api/auth/hubspot/start`;
  }

  /**
   * Get current user session
   */
  async getSession(): Promise<User | null> {
    try {
      const response = await apiClient.get<AuthResponse>('/api/auth/me');
      return response.user;
    } catch (error) {
      return null;
    }
  }

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/auth/logout');
      } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear any local state if needed
      window.location.href = '/login';
    }
  }

  /**
   * Check if user is authenticated
   */
  async isAuthenticated(): Promise<boolean> {
    const user = await this.getSession();
    return user !== null;
  }
}

export const authService = new AuthService();
