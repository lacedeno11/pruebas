export interface MockOT {
  external_id: string;
  cliente: string;
  login: string;
  lat: number;
  long: number;
  project_type: 'PUBLICO' | 'PRIVADO' | 'TERCERIZADO';
  status: string;
}

// Ecuador city coordinates
const ECUADOR_CITIES = [
  { name: 'Quito', lat: -0.2198, long: -78.5096 },
  { name: 'Guayaquil', lat: -2.1894, long: -79.8623 },
  { name: 'Cuenca', lat: -2.9001, long: -78.9994 },
  { name: 'Ambato', lat: -1.2264, long: -78.6355 },
  { name: 'Latacunga', lat: -0.9325, long: -78.6117 },
];

const DOCUMENT_NAMES = [
  'Acta de Inicio',
  'Plano As-Built',
  'Certificado de Fusión',
  'Reporte de Instalación',
  'Fotografía Punto 1',
  'Fotografía Punto 2',
  'Fotografía Punto 3',
  'Acta de Entrega',
  'Formulario de Conformidad',
  'Prueba de Continuidad',
  'Reporte de Potencia',
  'Análisis de Pérdida',
  'Calibración de Equipos',
  'Certificado de Seguridad',
  'Documento de Autorización',
  'Registro de Personal',
  'Acta de Verificación',
  'Inspección de Sitio',
  'Prueba de Rendimiento',
  'Medición de Distancia',
  'Evaluación de Riesgos',
  'Plan de Mantenimiento',
  'Documento de Aceptación',
  'Reporte Técnico',
  'Certificado de Calidad',
  'Documento de Entrega de Equipos',
  'Factura de Materiales',
  'Comprobante de Pago',
  'Fotografía de Cierre',
];

export class MockApiService {
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async getOTs(): Promise<MockOT[]> {
    await this.delay(500);

    const projectTypes: Array<'PUBLICO' | 'PRIVADO' | 'TERCERIZADO'> = [
      'PUBLICO',
      'PRIVADO',
      'TERCERIZADO',
    ];

    const ots: MockOT[] = [];

    for (let i = 1; i <= 20; i++) {
      const city = ECUADOR_CITIES[Math.floor(Math.random() * ECUADOR_CITIES.length)];
      const latOffset = (Math.random() - 0.5) * 0.2;
      const longOffset = (Math.random() - 0.5) * 0.2;

      // Distribution: 30% PUBLICO, 50% PRIVADO, 20% TERCERIZADO
      let projectType: 'PUBLICO' | 'PRIVADO' | 'TERCERIZADO';
      const rand = Math.random();
      if (rand < 0.3) {
        projectType = 'PUBLICO';
      } else if (rand < 0.8) {
        projectType = 'PRIVADO';
      } else {
        projectType = 'TERCERIZADO';
      }

      ots.push({
        external_id: `OT-${Date.now()}-${i}`,
        cliente: `Cliente ${i}`,
        login: `LOGIN-${i}`,
        lat: city.lat + latOffset,
        long: city.long + longOffset,
        project_type: projectType,
        status: 'PREPLANIFICADA',
      });
    }

    return ots;
  }

  async updateOTStatus(
    otId: string,
    newStatus: string
  ): Promise<{ success: boolean; message: string }> {
    await this.delay(500);

    const successProbability = Math.random();

    if (successProbability >= 0.1) {
      return {
        success: true,
        message: `Estado de OT ${otId} actualizado a ${newStatus}`,
      };
    }

    const errorMessages = [
      'Documento faltante',
      'Coordenadas inválidas',
      'Cuadrilla no disponible',
    ];
    const errorMessage =
      errorMessages[Math.floor(Math.random() * errorMessages.length)];

    return {
      success: false,
      message: errorMessage,
    };
  }

  async getDocumentStatus(otId: string): Promise<{
    otId: string;
    documentCount: number;
    requiredCount: number;
    documents: Array<{ name: string; uploaded: boolean }>;
  }> {
    await this.delay(500);

    const uploadedCount = Math.floor(Math.random() * (29 - 17 + 1)) + 17; // 60-100% = 17-29 documents
    const documents = DOCUMENT_NAMES.map((name, index) => ({
      name,
      uploaded: index < uploadedCount,
    }));

    return {
      otId,
      documentCount: uploadedCount,
      requiredCount: 29,
      documents,
    };
  }
}

export default MockApiService;

