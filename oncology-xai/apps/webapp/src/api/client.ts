import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

// API Gateway base URL - can be configured via environment variable
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';

// Keycloak configuration (for future implementation)
const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8081';
const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM || 'oncology-xai';
const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'webapp';

// For MVP/dev mode: hardcoded token
// TODO: Replace with Keycloak PKCE flow in production
const DEV_TOKEN = 'dev-token-12345';

class ApiClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = this.getToken();
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          this.clearToken();
          // In production, redirect to login
          console.error('Authentication failed');
        }
        return Promise.reject(error);
      }
    );

    // Initialize with dev token
    this.setToken(DEV_TOKEN);
  }

  private getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('auth_token');
    }
    return this.token;
  }

  private setToken(token: string): void {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }

  private clearToken(): void {
    this.token = null;
    localStorage.removeItem('auth_token');
  }

  // Auth methods (placeholder for Keycloak PKCE)
  async login(): Promise<void> {
    // TODO: Implement Keycloak PKCE flow
    console.log('Login with Keycloak PKCE - Not implemented');
    this.setToken(DEV_TOKEN);
  }

  async logout(): Promise<void> {
    this.clearToken();
    // TODO: Redirect to Keycloak logout
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  // Case Management APIs
  async getCases() {
    const response = await this.client.get('/cases');
    return response.data;
  }

  async getCase(caseId: string) {
    const response = await this.client.get(`/cases/${caseId}`);
    return response.data;
  }

  async createCase(data: { patientId: string; description?: string }) {
    const response = await this.client.post('/cases', data);
    return response.data;
  }

  async deleteCase(caseId: string) {
    const response = await this.client.delete(`/cases/${caseId}`);
    return response.data;
  }

  // Image Processing APIs
  async getImages(caseId: string) {
    const response = await this.client.get(`/cases/${caseId}/images`);
    return response.data;
  }

  async uploadImage(caseId: string, file: File, metadata?: any) {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    const response = await this.client.post(`/cases/${caseId}/images`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async processImage(caseId: string, imageId: string) {
    const response = await this.client.post(`/cases/${caseId}/images/${imageId}/process`);
    return response.data;
  }

  async getImageResults(caseId: string, imageId: string) {
    const response = await this.client.get(`/cases/${caseId}/images/${imageId}/results`);
    return response.data;
  }

  // EHR Processing APIs
  async getEHR(caseId: string) {
    const response = await this.client.get(`/cases/${caseId}/ehr`);
    return response.data;
  }

  async submitEHR(caseId: string, ehrText: string) {
    const response = await this.client.post(`/cases/${caseId}/ehr`, { text: ehrText });
    return response.data;
  }

  async extractEntities(caseId: string) {
    const response = await this.client.post(`/cases/${caseId}/ehr/extract`);
    return response.data;
  }

  async getEntities(caseId: string) {
    const response = await this.client.get(`/cases/${caseId}/ehr/entities`);
    return response.data;
  }

  // Knowledge Graph APIs
  async getGraph(caseId: string) {
    const response = await this.client.get(`/cases/${caseId}/graph`);
    return response.data;
  }

  async getGraphData(caseId: string) {
    const response = await this.client.get(`/cases/${caseId}/graph/data`);
    return response.data;
  }

  // Ontology Management APIs
  async getOntologies() {
    const response = await this.client.get('/ontologies');
    return response.data;
  }

  async getOntology(ontologyId: string) {
    const response = await this.client.get(`/ontologies/${ontologyId}`);
    return response.data;
  }

  async createProposal(data: any) {
    const response = await this.client.post('/ontologies/proposals', data);
    return response.data;
  }

  async getProposals() {
    const response = await this.client.get('/ontologies/proposals');
    return response.data;
  }

  async approveProposal(proposalId: string) {
    const response = await this.client.post(`/ontologies/proposals/${proposalId}/approve`);
    return response.data;
  }

  async publishOntology(ontologyId: string) {
    const response = await this.client.post(`/ontologies/${ontologyId}/publish`);
    return response.data;
  }
}

// Export singleton instance
const apiClient = new ApiClient();
export default apiClient;
