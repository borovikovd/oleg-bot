# OlegBot

Witty, stateless GPT-4o-powered Telegram bot with OpenRouter support.

## Features

- **Smart participation**: Responds to mentions and joins hot topics (~10% of traffic)
- **OpenRouter integration**: Uses Gemini free for testing, GPT-4o for production
- **Language-aware**: Detects conversation language and adapts tone
- **Memory managed**: LRU eviction, sliding window (50 messages per chat)
- **Production-ready**: Rate limiting, retry logic, webhook validation, monitoring

## Quick Deploy to Hetzner

1. **Clone & Configure**
   ```bash
   git clone <repo>
   cd oleg-bot
   cp .env.example .env
   nano .env  # Edit with your values
   ```

2. **Deploy with Docker**
   ```bash
   docker compose up -d
   ```

3. **Verify**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/bot/status
   ```

## Configuration

Required in `.env`:

```bash
# Telegram Bot (get from @BotFather)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIjKlMnOpQrStUvWxYz
TELEGRAM_WEBHOOK_URL=https://yourdomain.com
TELEGRAM_WEBHOOK_SECRET=$(openssl rand -hex 32)

# OpenRouter API (for LLM access)
OPENAI_API_KEY=sk-or-v1-your-openrouter-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=gpt-4o

# Admin Users (optional - for /stats, /setquota commands)
ADMIN_USER_IDS=123456789,987654321

# Production Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false
```

## Bot Setup

1. **Create bot**: Message [@BotFather](https://t.me/botfather)
2. **Webhook auto-registers** on startup (no manual setup needed)
3. **Add to groups**: Invite bot, give admin permissions for reactions

## Production Setup (Hetzner)

### Option 1: Docker Compose (Recommended)
```bash
# Clone and configure
git clone <repo> && cd oleg-bot
cp .env.example .env && nano .env

# Deploy
docker compose up -d

# Check status
docker compose logs -f oleg-bot
```

### Option 2: Direct with uv
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup
git clone <repo> && cd oleg-bot
cp .env.example .env && nano .env
uv sync

# Run
uv run uvicorn src.oleg_bot.main:app --host 0.0.0.0 --port 8000
```

### Reverse Proxy (nginx)
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Monitoring

- Health: `GET /health`
- Bot status: `GET /bot/status`
- Error stats: `GET /webhook/errors`
- Memory stats: `GET /webhook/memory`

## Admin Commands

Add your Telegram user ID to `ADMIN_USER_IDS` in `.env`:

- `/stats` - Usage statistics
- `/setquota 0.15` - Change reply percentage (1-50%)
- `/setgap 30` - Change seconds between replies (5-300s)
- `/help` - Show available commands

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Lint & type check
uv run ruff check && uv run mypy src/oleg_bot

# Run locally
uv run uvicorn src.oleg_bot.main:app --reload
```

## Troubleshooting

**Bot not responding?**
- Check `GET /bot/status` - webhook should be registered
- Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_URL`
- Check logs: `docker compose logs oleg-bot`

**OpenRouter errors?**
- Verify `OPENAI_API_KEY` starts with `sk-or-v1-`
- Check model availability at https://openrouter.ai/models

**Rate limited?**
- Check `/webhook/errors` for rate limit info
- Adjust `GAP_MIN_SECONDS` and `REPLY_TARGET_RATIO`

## Architecture

- **FastAPI**: Webhook server with rate limiting
- **Telegram API**: Real message/reaction sending (not just logging)
- **OpenRouter**: LLM provider with model flexibility
- **Memory Management**: LRU eviction, cleanup of inactive chats
- **Error Handling**: Comprehensive tracking and fallback responses