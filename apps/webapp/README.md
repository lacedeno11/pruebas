# WebApp - React Frontend

React + Vite frontend application with 5 main panels for the DERCAS-ONCO-XAI platform.

## Features

- **Case Selector Panel**: Create/list patients and cases
- **Image Panel**: Upload, process, view overlays for 5 patterns + genetic mutations
- **EHR Panel**: Text input, entity extraction, ontology mapping display
- **Graph Panel**: Interactive visualization using vis-network or d3 with nodes/edges/provenance
- **Admin Panel**: Ontology proposal creation, validation, approval, publishing
- Keycloak OIDC integration (PKCE flow)
- Role-based UI rendering
- Real-time job status updates
- Responsive design with proper error handling and loading states

## Technology Stack

- React 18
- Vite
- TypeScript
- Tailwind CSS
- React Query for state management
- Keycloak JS for authentication
- vis-network/d3 for graph visualization

## Development

```bash
cd apps/webapp
npm install
npm run dev
```

## Build

```bash
npm run build
npm run preview
```

## Environment Variables

Create `.env.local`:

```
VITE_API_URL=http://localhost:8080
VITE_KEYCLOAK_URL=http://localhost:8081
VITE_KEYCLOAK_REALM=oncology-realm
VITE_KEYCLOAK_CLIENT_ID=oncology-client
```
