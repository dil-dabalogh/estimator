# Development Guide

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn
- Git

### Clone and Install

```bash
git clone <repository-url>
cd Estimation

# Backend dependencies
pip install -r backend/requirements.txt

# Frontend dependencies
cd frontend
npm install
cd ..
```

### Environment Configuration

Create `backend/.env`:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.2

ATLASSIAN_URL=https://your-domain.atlassian.net/wiki
ATLASSIAN_USER_EMAIL=you@company.com
ATLASSIAN_API_TOKEN=your-token-here
```

## Running Locally

### Both Frontend and Backend

```bash
npm run dev
```

This starts:
- Backend on `http://localhost:8000`
- Frontend on `http://localhost:5173`

### Backend Only

```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Only

```bash
cd frontend
npm run dev
```

## Project Architecture

### Backend Structure

```
backend/
├── app.py                  # FastAPI app and endpoints
├── models.py               # Pydantic models
├── config.py               # Configuration management
├── worker.py               # Async batch processor
├── websocket_manager.py    # WebSocket connection manager
├── estimation_service.py   # Core estimation logic
├── confluence_client.py    # Confluence/Jira API client
├── llm_service.py          # LLM provider abstraction
├── utils.py                # Utility functions
└── lambda_handler.py       # AWS Lambda entry point
```

### Frontend Structure

```
frontend/src/
├── components/
│   ├── ui/                 # Shadcn UI components
│   ├── EstimationForm.tsx  # URL input form
│   └── ResultsTable.tsx    # Results display
├── hooks/
│   └── useEstimationWebSocket.ts  # WebSocket hook
├── lib/
│   └── utils.ts            # Utility functions
├── types.ts                # TypeScript types
├── config.ts               # Configuration
└── App.tsx                 # Main component
```

## API Endpoints

### POST /api/estimations/batch

Submit batch estimation request.

**Request:**
```json
{
  "items": [
    {
      "url": "https://...",
      "name": "Feature-A",
      "ballpark": "30 manweeks"
    }
  ]
}
```

**Response:**
```json
{
  "session_id": "uuid"
}
```

### WS /ws/{session_id}

WebSocket endpoint for real-time updates.

**Messages:**
```json
{
  "session_id": "uuid",
  "results": [
    {
      "name": "Feature-A",
      "status": "completed",
      "tshirt_size": "M",
      "man_weeks": 8.5,
      "ba_notes_available": true,
      "pert_available": true
    }
  ]
}
```

### GET /api/estimations/{session_id}/{name}/ba-notes

Download BA notes as Markdown.

### GET /api/estimations/{session_id}/{name}/pert

Download PERT estimate as Markdown.

## Adding Features

### Backend

1. Define models in `models.py`
2. Add endpoint in `app.py`
3. Implement logic in appropriate service module
4. Update tests

### Frontend

1. Add types in `types.ts`
2. Create component in `components/`
3. Update `App.tsx` if needed
4. Style with Tailwind classes

## Testing

### Backend

```bash
cd backend
pytest
```

### Frontend

```bash
cd frontend
npm test
```

## Code Style

- No emojis in code
- Minimal comments (only for tricky logic)
- Type hints for all public functions
- Clean, self-documenting code

## Building for Production

### Frontend

```bash
cd frontend
npm run build
# Output in frontend/dist/
```

### Backend

Backend is deployed as-is to Lambda. No build step required.

## Deployment

See [Sysadminguide.md](Sysadminguide.md) for deployment instructions.

## Troubleshooting

### Backend won't start

- Check Python version (3.11+)
- Verify all dependencies installed
- Check `.env` file exists and has correct values

### Frontend won't start

- Check Node version (18+)
- Run `npm install` again
- Clear `node_modules` and reinstall

### WebSocket connection fails

- Ensure backend is running
- Check browser console for errors
- Verify Vite proxy configuration

### LLM API errors

- Verify API keys in `.env`
- Check API rate limits
- Monitor CloudWatch logs in production

