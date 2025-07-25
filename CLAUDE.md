# Claude Code Context

## Project: OlegBot - Telegram Bot

### Overview
OlegBot is a witty Telegram bot powered by GPT-4o that participates in group conversations with personality and humor.

### Key Technical Details

#### Architecture
- **FastAPI** web server with webhook-based Telegram integration
- **OpenAI API** for text generation (GPT-4o production)
- **Docker** containerized deployment with nginx reverse proxy
- **Rate limiting** with slowapi and memory management with LRU eviction

#### Environment Configuration
- Production: GPT-4o via OpenAI API (supports OpenRouter for alternative models)
- Testing: All API calls are mocked - no real API keys needed
- Package manager: **uv** (not pip/poetry)

#### Critical Commands
```bash
# Development
uv run pytest                    # Run all tests
uv run ruff check --fix         # Lint and fix
uv run mypy src/                # Type checking

# Deployment verification
./deploy-check.sh               # Pre-deployment validation

# Docker deployment
docker compose up -d            # Deploy to production
docker compose logs -f oleg-bot # Monitor logs
```

#### Key Security Features
- Webhook secret validation
- Rate limiting (10 req/s webhook, various limits on admin endpoints)
- Admin user restrictions
- Memory limits with automatic cleanup
- HTTPS with security headers via nginx

#### Monitoring Endpoints
- `/health` - Health check
- `/bot/status` - Bot status and webhook info
- `/webhook/errors` - Error statistics
- `/webhook/memory` - Memory usage stats

#### Recent Major Changes
- Fixed Telegram API integration (was only logging, now actually sends messages)
- Added webhook registration on startup
- Implemented proper retry logic with tenacity
- Added memory management with LRU chat eviction
- Updated all dependencies to latest versions (Python 3.13.5, FastAPI 0.116.1, etc.)
- Created comprehensive E2E tests
- Fixed all linting and type checking issues

#### Testing Strategy
- Unit tests for individual components
- Integration tests for webhook handling
- E2E tests with mock Telegram server
- Docker container validation in deploy-check.sh

#### Deployment Target
Hetzner server with Docker Compose setup including nginx reverse proxy with SSL termination and rate limiting.