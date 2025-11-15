# Estimation Tool Frontend

A modern React + TypeScript SPA for generating Business Analyst estimation notes and PERT estimates.

## Tech Stack

- React 18
- TypeScript
- Vite (build tool)
- Tailwind CSS
- Shadcn UI components
- Axios (HTTP client)
- WebSocket (real-time updates)

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Environment Variables

Create a `.env` file:

```
VITE_API_BASE_URL=http://localhost:8000
```

For production deployment, set this to your API Gateway URL.

## Project Structure

```
src/
├── components/
│   ├── ui/              # Shadcn UI components
│   ├── EstimationForm.tsx
│   └── ResultsTable.tsx
├── hooks/
│   └── useEstimationWebSocket.ts
├── lib/
│   └── utils.ts
├── types.ts
├── config.ts
└── App.tsx
```

## Key Features

- Real-time progress updates via WebSocket
- Auto-fetch page titles from Confluence and Jira
- Export estimations to Confluence
- Download BA notes and PERT estimates
- Responsive design
- T-shirt size calculation and visualization

## Deployment

See the [System Administrator Guide](../doc/Sysadminguide.md) for production deployment instructions.
