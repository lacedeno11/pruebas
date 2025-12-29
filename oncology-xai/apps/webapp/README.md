# Oncology XAI WebApp

React-based web application for the Oncology XAI system, providing an intuitive interface for medical imaging analysis, EHR data processing, knowledge graph visualization, and ontology management.

## Features

- **Case Management**: Create and manage patient cases
- **Image Analysis**: Upload medical images, process them with AI models, and view detection results
- **EHR Processing**: Extract medical entities from electronic health records with ontology mapping
- **Knowledge Graph**: Visualize integrated knowledge graphs combining imaging, EHR, and ontology data
- **Admin Panel**: Manage ontologies, create proposals, and approve changes

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **TailwindCSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **vis-network** - Graph visualization

## Prerequisites

- Node.js 18+ and npm
- Docker (optional, for containerized deployment)

## Getting Started

### Local Development

1. Install dependencies:
```bash
npm install
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Start development server:
```bash
npm run dev
```

The application will be available at http://localhost:3000

### Production Build

```bash
npm run build
npm run preview
```

### Docker Deployment

Build and run the Docker container:

```bash
docker build -t oncology-xai-webapp .
docker run -p 3000:3000 oncology-xai-webapp
```

## Project Structure

```
src/
├── api/
│   └── client.ts          # API client with axios
├── components/
│   └── Layout.tsx         # Main layout with navigation
├── pages/
│   ├── CaseSelector.tsx   # Case management page
│   ├── ImagePanel.tsx     # Image analysis page
│   ├── EHRPanel.tsx       # EHR processing page
│   ├── GraphPanel.tsx     # Knowledge graph visualization
│   └── AdminPanel.tsx     # Ontology administration
├── App.tsx                # Root component with routing
├── main.tsx              # Application entry point
└── index.css             # Global styles with Tailwind
```

## Configuration

### Environment Variables

- `VITE_API_URL`: API Gateway base URL (default: http://localhost:8080/api/v1)
- `VITE_KEYCLOAK_URL`: Keycloak server URL (default: http://localhost:8081)
- `VITE_KEYCLOAK_REALM`: Keycloak realm name (default: oncology-xai)
- `VITE_KEYCLOAK_CLIENT_ID`: Keycloak client ID (default: webapp)

### Authentication

Currently uses a hardcoded dev token for MVP purposes. Production deployment should implement Keycloak PKCE flow for secure authentication.

## API Integration

The webapp communicates with the API Gateway which routes requests to appropriate microservices:

- `/cases/*` - Case management service
- `/cases/*/images/*` - Image processing service
- `/cases/*/ehr/*` - EHR service
- `/cases/*/graph/*` - Knowledge graph service
- `/ontologies/*` - Ontology management service

## Development Notes

- Mock data is used when API endpoints are unavailable
- All pages include loading states and error handling
- TailwindCSS classes are used for styling
- TypeScript ensures type safety across the application

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

Proprietary - Oncology XAI System
