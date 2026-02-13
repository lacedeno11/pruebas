# PEI Platform Frontend - DERCAS TO-BE AGÉNTICO

Modern React-based frontend for the Plataforma de Coordinación de Equipos de Instalación (PEI), featuring drag & drop work order management, geographic visualization, and AI-powered chat interface.

## Features

- **📋 Kanban Board**: Drag and drop work orders (OTs) between status columns for visual workflow management
- **🗺️ Geographic Map**: Real-time visualization of OTs and team locations using interactive OpenStreetMap
- **🤖 AI Assistant**: Chat-based interface powered by LangGraph for intelligent system operations
- **⚡ Real-time Updates**: React Query for automatic data refresh and state synchronization
- **📱 Responsive Design**: Mobile-friendly interface that works on all screen sizes
- **🎨 Professional UI**: TELCONET branding colors with modern component design
- **🔄 Optimistic Updates**: Immediate UI feedback with automatic rollback on errors

## Prerequisites

- **Node.js** 18+ 
- **npm** 9+
- **Backend Server** running at http://localhost:8000 (see backend README)

## Installation

### 1. Install Dependencies

```bash
npm install
```

This will install all required packages including:
- **react** & **react-dom** - UI framework
- **@dnd-kit** - Drag and drop functionality
- **react-leaflet** - Map visualization
- **@tanstack/react-query** - Data fetching and caching
- **axios** - HTTP client
- **react-toastify** - Toast notifications
- **vite** - Build tool and dev server

### 2. Configuration

The frontend is configured to automatically proxy API requests to the backend:
- Development: `http://localhost:5173` → API requests to `http://localhost:8000/api`
- See `vite.config.js` for proxy configuration

No additional `.env` file is needed for basic development. For custom API endpoints, you can modify `src/services/api.js`.

## Running the Application

### Development Mode

Start the development server with hot module reloading:

```bash
npm run dev
```

The application will be available at **http://localhost:5173**

Features in dev mode:
- Hot reload on file changes
- Full source maps for debugging
- Unminified code for easy inspection
- React DevTools support

### Production Build

Create an optimized production bundle:

```bash
npm run build
```

This creates a `dist/` folder with minified and optimized assets.

### Preview Production Build

Preview the production build locally before deployment:

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/           # React components
│   │   ├── OTCard.jsx       # Individual work order card (draggable)
│   │   ├── KanbanBoard.jsx  # Main Kanban board with columns
│   │   ├── DetencionModal.jsx # Modal for detention reason capture
│   │   ├── MapView.jsx       # Geographic map visualization
│   │   └── ChatSidebar.jsx   # AI assistant chat interface
│   ├── hooks/               # Custom React hooks
│   │   ├── useDragDrop.js   # Drag & drop logic
│   │   ├── useWebSocket.js  # WebSocket for real-time updates (stub)
│   │   └── index.js         # Hook exports
│   ├── services/            # API communication
│   │   └── api.js           # Axios client with API endpoints
│   ├── types/               # Type definitions (JSDoc)
│   │   └── index.js         # OT, Cuadrilla types and enums
│   ├── App.jsx              # Main application component
│   ├── App.css              # Global styles
│   ├── main.jsx             # Application entry point
│   └── index.html           # HTML template
├── vite.config.js           # Vite build configuration
├── package.json             # Dependencies and scripts
├── .gitignore              # Git ignore patterns
└── README.md               # This file
```

## Features Explained

### 📋 Kanban Board

The main work order management interface:

- **6 Status Columns**: PREPLANIFICADA → PLANIFICADA → ASIGNADO_TAREA → DETENIDA → ANULADA → FINALIZADA
- **Drag & Drop**: Move OTs between columns to change their status
- **Color-Coded Badges**: 
  - 🟨 PREPLANIFICADA (Yellow) - Awaiting planning
  - 🔵 PLANIFICADA (Blue) - Planned but not assigned
  - 🟣 ASIGNADO_TAREA (Purple) - Task assigned to team
  - 🟠 DETENIDA (Orange) - Work halted/paused
  - 🔴 ANULADA (Red) - Cancelled
  - 🟢 FINALIZADA (Green) - Completed
- **Real-time Updates**: Data refreshes every 30 seconds
- **Detention Modal**: Capture reason when moving OT to DETENIDA status
- **OT Information**: Each card displays:
  - External ID (unique identifier)
  - Customer ID (cliente_id)
  - Status badge with color
  - Project type (PUBLICO/PRIVADO/TERCERIZADO)
  - Geographic coordinates or error indicator
  - Assigned team (cuadrilla) or "Unassigned" badge
  - Creation date

### 🗺️ Geographic Map

Real-time visualization of work order and team locations:

- **Map Center**: Ecuador (-1.831239, -78.183406)
- **Zoom Level**: 7 (regional view)
- **OT Markers**:
  - Color-coded by status (matching Kanban colors)
  - Labeled with project type (P=PUBLICO, R=PRIVADO, T=TERCERIZADO)
  - Click for popup with detailed information
  - Filtered to show only OTs with valid coordinates
- **Team Markers**:
  - Blue "T" markers showing team (cuadrilla) centroid positions
  - Displays team name, type, current load vs capacity, load percentage
- **Legend**: Shows all status colors with OT count per status
- **Warning**: Info box alerts about OTs with missing location data

### 🤖 AI Assistant Chat

Conversational interface for system operations:

- **Floating Button**: Bottom-right corner with chat emoji (💬)
- **Sliding Sidebar**: Opens from right with full chat history
- **Message Types**:
  - 👤 User messages (blue) - Your questions/commands
  - 🤖 Agent messages (gray) - Assistant responses
  - ⚠️ Error messages (red) - Failed operations
- **Features**:
  - Auto-scroll to latest message
  - Typing indicator animation
  - Auto-focus on open
  - Keyboard shortcuts (Enter to send, Shift+Enter for new line)
- **Clear History**: Reset conversation with trash button
- **Responsive**: Works on mobile with scrollable message area

## API Integration

### Base Configuration

All API calls are automatically proxied to the backend:

```javascript
// Development: requests to /api/* → http://localhost:8000/api/*
// Production: requests to /api/* → your-domain/api/*
```

### Available Endpoints

The frontend integrates with these backend endpoints:

**OT Management**:
- `GET /api/ots` - List work orders with filters
- `GET /api/ots/{id}` - Get specific OT
- `POST /api/ots` - Create new OT
- `PUT /api/ots/{id}` - Update OT
- `PUT /api/ots/{id}/status` - Change OT status

**Team Management**:
- `GET /api/cuadrillas` - List all teams
- `GET /api/cuadrillas/{id}` - Get specific team
- `GET /api/cuadrillas/{id}/ots` - Get team's assigned OTs

**Agent Operations**:
- `POST /api/agents/chat` - Send message to AI assistant
- `POST /api/agents/plan` - Trigger planning agent
- `GET /api/agents/logs` - Get agent action logs

**Mock Endpoints** (SYSTEM_MODE=MOCK only):
- `GET /api/mock/telcos/ots` - Get mock OT data
- `POST /api/mock/telcos/update_status` - Update mock OT status
- `GET /api/mock/telcodrive/documents` - Get mock document count

### Error Handling

API errors are automatically displayed as toast notifications:

```javascript
// Toast notifications appear for:
// - Network errors
// - Validation errors
// - Server errors (5xx)
// - Timeout errors
```

## Development Workflow

### Adding a New Component

1. Create file in `src/components/MyComponent.jsx`
2. Import required hooks and styles
3. Export as default
4. Import and use in parent components

Example:
```jsx
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchOTs } from '../services/api'

export function MyComponent() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['ots'],
    queryFn: () => fetchOTs({})
  })

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error: {error.message}</div>

  return <div>{/* Component JSX */}</div>
}

export default MyComponent
```

### Making API Calls

Use the pre-configured axios client in `src/services/api.js`:

```javascript
import { fetchOTs, updateOTStatus } from '../services/api'

// Fetch OTs with filters
const { data } = await fetchOTs({ status: 'PREPLANIFICADA' })

// Update OT status
await updateOTStatus(otId, 'PLANIFICADA')
```

### Managing State

Use React Query for server state and React hooks for UI state:

```javascript
// Server state (data from API)
const { data, isLoading } = useQuery({
  queryKey: ['ots'],
  queryFn: () => fetchOTs({})
})

// UI state (local component state)
const [isOpen, setIsOpen] = useState(false)
```

### Styling

Choose any of these approaches:

1. **Inline Styles** (in component files)
2. **Global CSS** (App.css)
3. **CSS Modules** (create `.module.css` files)
4. **Tailwind CSS** (add to build if preferred)

## Build and Deployment

### Building for Production

```bash
npm run build
```

Output:
- Minified JavaScript and CSS
- Optimized assets
- Source maps (optional)
- Bundle in `dist/` folder

### Serving Static Build

The built frontend can be served by any web server:

```bash
# Using Node.js
npx http-server dist

# Using Python
python -m http.server --directory dist 8000

# Using Docker
docker run -p 80:80 -v $(pwd)/dist:/usr/share/nginx/html nginx
```

### Environment Configuration

For production deployment, update `vite.config.js` proxy or use environment variables:

```javascript
// vite.config.js
server: {
  proxy: {
    '/api': {
      target: 'https://your-production-api.com',
      changeOrigin: true
    }
  }
}
```

## Troubleshooting

### Port Already in Use

If port 5173 is already in use:

```bash
# macOS/Linux: Find and kill process
lsof -i :5173
kill -9 <PID>

# Or specify different port in vite.config.js
server: {
  port: 5174
}
```

### API Connection Errors

If you see "Failed to connect to API":

1. **Check backend is running**: `http://localhost:8000/docs` should be accessible
2. **Verify proxy configuration**: Check `vite.config.js` for correct target
3. **Check CORS settings**: Backend should have `CORS_ORIGINS` including `http://localhost:5173`

### Blank Page or Build Errors

```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf .vite

# Restart dev server
npm run dev
```

### Hot Module Reload Not Working

Vite's HMR might fail behind proxies. Update `vite.config.js`:

```javascript
server: {
  hmr: {
    host: 'localhost',
    port: 5173
  }
}
```

## Performance Optimization

### React Query Configuration

```javascript
// Configured for good UX and server load balance
staleTime: 30000,        // 30 seconds before data is stale
gcTime: 60000,           // 60 seconds before garbage collection
retry: 1,                // Retry failed requests once
refetchOnWindowFocus: false // Don't refetch when window regains focus
```

Adjust these values based on your needs.

### Bundle Analysis

To analyze bundle size:

```bash
npm install --save-dev rollup-plugin-visualizer

# Add to vite.config.js
import { visualizer } from 'rollup-plugin-visualizer'

export default defineConfig({
  plugins: [react(), visualizer()]
})

# Then run build and open stats.html
npm run build
open dist/stats.html
```

## Browser Support

- Chrome/Edge 88+
- Firefox 85+
- Safari 14+
- Mobile browsers (iOS Safari 14+, Chrome Android)

## Contributing

When contributing to the frontend:

1. Follow existing code style and patterns
2. Use React hooks for state management
3. Add JSDoc comments for complex functions
4. Test responsiveness on mobile (375px, 768px, 1024px viewports)
5. Ensure accessibility with proper ARIA labels
6. Update this README if adding new features

## Dependencies Overview

| Package | Purpose | Version |
|---------|---------|---------|
| react | UI framework | ^18 |
| react-dom | DOM rendering | ^18 |
| @dnd-kit/core | Drag & drop | ^6 |
| @dnd-kit/sortable | Sortable drag & drop | ^8 |
| react-leaflet | Map component | ^4 |
| leaflet | Map library | ^1 |
| @tanstack/react-query | Data fetching | ^5 |
| axios | HTTP client | ^1 |
| react-toastify | Toast notifications | ^10 |
| vite | Build tool | ^5 |

## Resources

- [React Documentation](https://react.dev)
- [Vite Documentation](https://vitejs.dev)
- [React Query Docs](https://tanstack.com/query/latest)
- [Leaflet Documentation](https://leafletjs.com)
- [Drag & Drop Kit Docs](https://docs.dndkit.com)

## License

Part of the DERCAS TO-BE AGÉNTICO PEI Platform project.

## Support

For issues or questions:

1. Check this README's Troubleshooting section
2. Review the backend README for backend-related issues
3. Check browser console for JavaScript errors
4. Enable Network tab in DevTools to inspect API calls
5. Create an issue in the project repository

## Quick Reference

### Common Commands

```bash
# Development
npm run dev          # Start dev server at http://localhost:5173

# Building
npm run build        # Create production bundle
npm run preview      # Preview production build

# Linting
npm run lint         # Run ESLint (if configured)

# Dependencies
npm install          # Install/update dependencies
npm outdated         # Check for outdated packages
npm audit            # Check for security vulnerabilities
```

### Environment Variables (if needed)

Create a `.env.local` file in the frontend root:

```env
VITE_API_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
```

Access in code:
```javascript
const apiUrl = import.meta.env.VITE_API_URL || '/api'
```

### Project Conventions

- **File naming**: PascalCase for components (`.jsx`), camelCase for utilities (`.js`)
- **Component structure**: Functional components with hooks
- **State management**: React Query for server state, useState for UI state
- **Styling**: Global CSS (App.css) + component inline styles
- **Comments**: JSDoc for functions, inline comments for complex logic

## Next Steps

After starting the dev server:

1. Open http://localhost:5173 in your browser
2. You should see the PEI Platform header
3. Click on "Kanban Board" to view work orders (in MOCK mode)
4. Click on "Geographic View" to see the map
5. Click the chat icon to interact with the AI assistant

Enjoy using the PEI Platform! 🚀

