import MockApiService from './MockApiService';
import env from '../config/environment';

export interface ApiServiceInterface {
  getOTs(): Promise<any[]>;
  updateOTStatus(otId: string, newStatus: string): Promise<{ success: boolean; message: string }>;
  getDocumentStatus(otId: string): Promise<any>;
}

class RealApiService implements ApiServiceInterface {
  async getOTs(): Promise<any[]> {
    throw new Error('RealApiService not yet implemented');
  }

  async updateOTStatus(otId: string, newStatus: string): Promise<{ success: boolean; message: string }> {
    throw new Error('RealApiService not yet implemented');
  }

  async getDocumentStatus(otId: string): Promise<any> {
    throw new Error('RealApiService not yet implemented');
  }
}

export function createApiService(): ApiServiceInterface {
  if (env.SYSTEM_MODE === 'MOCK') {
    return new MockApiService();
  } else {
    return new RealApiService();
  }
}

export default createApiService;

