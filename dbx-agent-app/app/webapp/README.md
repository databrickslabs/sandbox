# Multi-Agent Registry - React Webapp

Production-ready React + Vite application for the Multi-Agent Registry UI.

## Features

- **React 19.2** with TypeScript for type safety
- **React Router** for client-side navigation
- **Axios** for API communication
- **Vite** for fast development and optimized builds
- Three main pages: Discover, Collections, and Chat
- API client with error handling and interceptors
- TypeScript types matching backend Pydantic schemas

## Prerequisites

- Node.js 20+
- npm or yarn

## Installation

```bash
npm install
```

## Development

Start the development server with hot reload:

```bash
npm run dev
```

The app will be available at http://localhost:3000

## Build

Create production build:

```bash
npm run build
```

Build output will be in the `dist/` directory.

## Preview Production Build

Preview the production build locally:

```bash
npm run preview
```

## Project Structure

```
webapp/
├── src/
│   ├── api/
│   │   ├── client.ts          # Axios clients with interceptors
│   │   ├── registry.ts        # Registry API endpoints
│   │   └── supervisor.ts      # Supervisor API endpoints
│   ├── components/
│   │   └── layout/
│   │       ├── Layout.tsx     # Main layout with navigation
│   │       └── Layout.css
│   ├── pages/
│   │   ├── DiscoverPage.tsx   # Browse tools/servers
│   │   ├── CollectionsPage.tsx # Manage collections
│   │   └── ChatPage.tsx       # Chat interface
│   ├── types/
│   │   └── index.ts           # TypeScript interfaces
│   ├── App.tsx                # Root component with routing
│   ├── App.css                # Global styles
│   └── main.tsx               # Entry point
├── public/                    # Static assets
├── index.html                 # HTML entry point
├── vite.config.ts             # Vite configuration
├── tsconfig.json              # TypeScript configuration
└── package.json
```

## Environment Configuration

Create a `.env` file based on `.env.example`:

```bash
VITE_REGISTRY_API_URL=/api
VITE_SUPERVISOR_URL=/supervisor
VITE_DEBUG=true
```

For production deployment:

```bash
VITE_REGISTRY_API_URL=https://<workspace-host>/api/registry-api
VITE_SUPERVISOR_URL=https://<workspace-host>/api/supervisor
VITE_DEBUG=false
```

## API Client

The app includes two Axios clients:

### Registry Client

Connects to the Registry API for:
- Discovering apps, servers, and tools
- Managing collections
- Generating supervisors

### Supervisor Client

Connects to the Supervisor API for:
- Chat interactions
- Trace retrieval
- Real-time event streaming (future)

## TypeScript Types

All types in `src/types/index.ts` match the backend Pydantic schemas:

- `App` - Databricks App metadata
- `MCPServer` - MCP server configuration
- `Tool` - Individual tool definition
- `Collection` - User collection
- `CollectionItem` - Collection membership
- `Message` - Chat message
- `TraceEvent` - Trace event
- `Span` - MLflow span

## Development Proxy

Vite dev server proxies API requests:

- `/api/*` → `http://localhost:8000`
- `/supervisor/*` → `http://localhost:8001`

This avoids CORS issues during development.

## Next Steps

### Phase 4.2: Discover Page Enhancement

- Add search and filter functionality
- Implement card components
- Add detail modals
- Quick actions (add to collection)

### Phase 4.3: Collections Page Enhancement

- Collection editor component
- Item selector with search
- Supervisor generation UI
- Drag-and-drop item organization

### Phase 4.4: Chat Page - Three-Panel Layout

- Implement three-panel layout
- Add trace timeline with SSE
- Inspector panel for event details
- Real-time streaming support

## Testing

```bash
npm run lint
```

## Architecture

Built according to specifications in:
- `docs/architecture/ARCHITECTURE.md` (Part 3: React Webapp)

## Support

Part of the Guidepoint Multi-Agent Registry project.
