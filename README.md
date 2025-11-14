# Estimation Tool

A modern web application for generating Business Analyst (BA) estimation notes and PERT estimates from Confluence or Jira URLs using AI.

## Features

- Modern, responsive SPA built with React and Shadcn UI
- Real-time progress updates via WebSocket
- Parallel processing of multiple estimations
- Support for both Confluence pages and Jira issues
- **Auto-fetch page titles from Confluence and Jira URLs**
- T-shirt size calculation (XS, S, M, L, XL, XXL)
- Man-week estimates from PERT analysis
- Download generated BA notes and PERT estimates as Markdown files
- **Export estimations directly to Confluence pages**
- FastAPI backend deployable to AWS Lambda
- Support for OpenAI and AWS Bedrock LLM providers

## Quick Start

### Local Development

```bash
# Install backend dependencies
pip install -r backend/requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Set up environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your credentials

# Run both backend and frontend
npm run dev
```

The application will be available at `http://localhost:5173`

## T-shirt Size Thresholds

- XS: < 2 weeks
- S: < 16 weeks
- M: < 25 weeks
- L: < 40 weeks
- XL: < 60 weeks
- XXL: ≥ 60 weeks

## Documentation

- [User Guide](Userguide.md) - How to use the web application
- [System Administrator Guide](Sysadminguide.md) - Deployment to AWS Lambda
- [Environment Variables Guide](ENVIRONMENT_VARIABLES.md) - How to configure environment variables for AWS deployment
- [Development Guide](Developmentguide.md) - Local development and architecture
- [Confluence Export Implementation](CONFLUENCE_EXPORT_IMPLEMENTATION.md) - Details on the Confluence export feature
- [Auto-Fetch Title Implementation](AUTO_FETCH_TITLE_IMPLEMENTATION.md) - Details on the auto-fetch title feature

## Technology Stack

**Backend:**
- FastAPI (Python 3.11+)
- WebSocket support for real-time updates
- Async parallel processing
- AWS Lambda deployment via Mangum

**Frontend:**
- React 18 + TypeScript
- Vite build tool
- Shadcn UI + Tailwind CSS
- Axios for HTTP requests
- Native WebSocket API

**LLM Providers:**
- OpenAI (GPT-4, GPT-5)
- AWS Bedrock (Anthropic Claude)

## Project Structure

```
/
├── backend/              # FastAPI application
│   ├── app.py            # Main FastAPI app
│   ├── models.py         # Pydantic models
│   ├── worker.py         # Async batch processor
│   ├── estimation_service.py  # Core estimation logic
│   └── lambda_handler.py # AWS Lambda handler
├── frontend/             # React + Vite application
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom hooks
│   │   └── lib/          # Utilities
├── infrastructure/       # AWS SAM deployment
│   ├── template.yaml     # CloudFormation template
│   └── deploy.sh         # Deployment script
├── scripts/              # Legacy CLI tools
├── personas/             # AI personas for BA and Engineer
└── templates/            # PERT template
```

## License

Internal use only.
