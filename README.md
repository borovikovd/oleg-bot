# OlegBot

Witty, stateless GPT-4o-powered Telegram bot that joins conversations naturally.

## Features

- **Smart participation**: Responds to mentions and joins hot topics (~10% of traffic)
- **Language-aware**: Detects conversation language and adapts tone
- **Stateless**: No persistent database, uses sliding window (50 messages)
- **Rate-limited**: 20s gap between messages, respects quotas
- **Production-ready**: Health checks, metrics, comprehensive logging

## Quick Start

1. **Setup**
   ```bash
   git clone <repo>
   cd oleg-bot
   cp .env.example .env
   # Edit .env with your tokens
   ```

2. **Install**
   ```bash
   uv sync
   ```

3. **Run**
   ```bash
   uv run python -m oleg_bot.main
   ```

## Configuration

Required environment variables in `.env`:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook/telegram
OPENAI_API_KEY=your_openai_api_key_here

# Optional
TELEGRAM_WEBHOOK_SECRET=webhook_secret
REPLY_TARGET_RATIO=0.10
GAP_MIN_SECONDS=20
```

## Bot Setup

1. **Create bot**: Message [@BotFather](https://t.me/botfather)
2. **Set webhook**: `POST https://api.telegram.org/bot<TOKEN>/setWebhook`
   ```json
   {
     "url": "https://yourdomain.com/webhook/telegram",
     "secret_token": "your_webhook_secret"
   }
   ```
3. **Add to groups**: Invite bot, give admin permissions for reactions

## Deployment

### Docker
```bash
docker build -t oleg-bot .
docker run -p 8000:8000 --env-file .env oleg-bot
```

### Production
- Set `DEBUG=false`
- Use HTTPS for webhook URL
- Monitor `/health` and `/metrics` endpoints
- Configure reverse proxy (nginx/caddy)

## Admin Commands

- `/setquota 0.15` - Change reply percentage
- `/setgap 30` - Change minimum seconds between replies  
- `/stats` - Show usage statistics

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Lint & format
uv run ruff check src/
uv run ruff format src/
uv run mypy src/

# Coverage
uv run pytest --cov
```

## Architecture

- **FastAPI**: Webhook server with async processing
- **Sliding Window**: In-memory message storage per chat
- **GPT-4o**: Dynamic response generation with context
- **Prometheus**: Metrics collection at `/metrics`