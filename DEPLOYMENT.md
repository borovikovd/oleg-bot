# OlegBot Deployment Guide

This guide covers deploying OlegBot in production environments.

## Prerequisites

- Docker and Docker Compose
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)  
- OpenAI API Key with GPT-4o access
- Public HTTPS domain for webhooks
- SSL certificate for your domain

## Environment Configuration

### Required Environment Variables

Create a `.env` file with the following required variables:

```bash
# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret_here
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook/telegram

# OpenAI Configuration  
OPENAI_API_KEY=sk-your_openai_key_here
OPENAI_MODEL=gpt-4o

# Bot Behavior (optional, defaults provided)
WINDOW_SIZE=50
REPLY_TARGET_RATIO=0.10
GAP_MIN_SECONDS=20
MAX_RESPONSE_WORDS=100

# Server Configuration (optional)
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

### Getting Your Bot Token

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Use `/newbot` command and follow instructions
3. Save the bot token (format: `123456789:ABCdefGhIjKlMnOpQrStUvWxYz`)
4. Use `/setprivacy` to enable privacy mode (recommended)

### Getting OpenAI API Key

1. Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Ensure you have access to GPT-4o model
4. Set usage limits to control costs

## Deployment Options

### Option 1: Docker Compose (Recommended)

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd oleg-bot
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Deploy with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

3. **With NGINX reverse proxy:**
   ```bash
   # Setup SSL certificates first
   mkdir ssl
   # Copy your SSL certificate files to ssl/cert.pem and ssl/key.pem
   
   # Deploy with NGINX
   docker-compose --profile production up -d
   ```

### Option 2: Manual Docker

1. **Build the image:**
   ```bash
   docker build -t oleg-bot .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name oleg-bot \
     --env-file .env \
     -p 8000:8000 \
     --restart unless-stopped \
     oleg-bot
   ```

### Option 3: Cloud Deployment

#### Google Cloud Run

1. **Build and push image:**
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/oleg-bot
   ```

2. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy oleg-bot \
     --image gcr.io/PROJECT_ID/oleg-bot \
     --platform managed \
     --region us-central1 \
     --set-env-vars ENVIRONMENT=production \
     --set-env-vars TELEGRAM_BOT_TOKEN=your_token \
     --set-env-vars OPENAI_API_KEY=your_key \
     --set-env-vars TELEGRAM_WEBHOOK_URL=https://your-service-url/webhook/telegram
   ```

#### AWS ECS with Fargate

1. **Create task definition:**
   ```json
   {
     "family": "oleg-bot",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "256",
     "memory": "512",
     "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
     "containerDefinitions": [
       {
         "name": "oleg-bot",
         "image": "your-account.dkr.ecr.region.amazonaws.com/oleg-bot:latest",
         "portMappings": [{"containerPort": 8000}],
         "environment": [
           {"name": "ENVIRONMENT", "value": "production"}
         ],
         "secrets": [
           {"name": "TELEGRAM_BOT_TOKEN", "valueFrom": "arn:aws:secretsmanager:..."},
           {"name": "OPENAI_API_KEY", "valueFrom": "arn:aws:secretsmanager:..."}
         ]
       }
     ]
   }
   ```

## Setting Up Webhooks

### Register Webhook with Telegram

Once your bot is deployed and accessible via HTTPS:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourdomain.com/webhook/telegram",
    "secret_token": "your_webhook_secret"
  }'
```

### Verify Webhook

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

Should return:
```json
{
  "ok": true,
  "result": {
    "url": "https://yourdomain.com/webhook/telegram",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

## SSL/TLS Configuration

### Using Let's Encrypt with Certbot

1. **Install Certbot:**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   ```

2. **Obtain certificate:**
   ```bash
   sudo certbot certonly --standalone -d yourdomain.com
   ```

3. **Copy certificates:**
   ```bash
   sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./ssl/cert.pem
   sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./ssl/key.pem
   sudo chown $USER:$USER ./ssl/*.pem
   ```

4. **Setup auto-renewal:**
   ```bash
   sudo crontab -e
   # Add: 0 12 * * * /usr/bin/certbot renew --quiet
   ```

## Monitoring and Health Checks

### Health Check Endpoint

The bot provides a health check endpoint at `/health`:

```bash
curl https://yourdomain.com/health
# Returns: {"status": "healthy", "service": "oleg-bot"}
```

### Log Monitoring

View container logs:
```bash
docker-compose logs -f oleg-bot
```

Key log messages to monitor:
- ✅ Configuration validation messages
- ⚠️ API failures or rate limits
- 🔴 Critical errors or crashes

### Basic Monitoring Script

```bash
#!/bin/bash
# health-check.sh

HEALTH_URL="https://yourdomain.com/health"
WEBHOOK_URL="https://hooks.slack.com/services/..." # Optional Slack webhook

if ! curl -f -s "$HEALTH_URL" > /dev/null; then
    echo "Health check failed!"
    # Optional: Send alert to Slack
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 OlegBot health check failed!"}' \
        "$WEBHOOK_URL"
    exit 1
fi

echo "Health check passed"
```

Add to crontab for regular monitoring:
```bash
*/5 * * * * /path/to/health-check.sh
```

## Security Best Practices

### Environment Security

1. **Use webhook secrets:**
   ```bash
   TELEGRAM_WEBHOOK_SECRET=$(openssl rand -hex 32)
   ```

2. **Restrict network access:**
   - Only allow HTTPS traffic on port 443
   - Block direct access to port 8000
   - Use firewall rules or security groups

3. **Regular updates:**
   ```bash
   # Update base image regularly
   docker-compose pull
   docker-compose up -d
   ```

### API Key Security

1. **Use environment variables, never hardcode keys**
2. **Rotate keys regularly**
3. **Set OpenAI usage limits**
4. **Monitor API usage and costs**

### Container Security

1. **Run as non-root user** (already configured in Dockerfile)
2. **Keep base images updated**
3. **Scan for vulnerabilities:**
   ```bash
   docker scout cves oleg-bot
   ```

## Scaling and Performance

### Horizontal Scaling

For high-traffic bots, deploy multiple instances behind a load balancer:

```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  oleg-bot:
    # ... same config
    deploy:
      replicas: 3
  
  nginx:
    # Configure upstream with multiple backends
```

### Resource Limits

Set appropriate resource limits:

```yaml
services:
  oleg-bot:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
```

### Performance Tuning

1. **Adjust bot behavior settings:**
   - Lower `REPLY_TARGET_RATIO` for less frequent responses
   - Increase `GAP_MIN_SECONDS` to reduce API calls
   - Decrease `MAX_RESPONSE_WORDS` to reduce token usage

2. **Monitor OpenAI costs:**
   - Set up billing alerts
   - Track token usage via logs
   - Consider using GPT-4o-mini for cost savings

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

## Backup and Recovery

### Configuration Backup

```bash
# Backup environment configuration
cp .env .env.backup.$(date +%Y%m%d)

# Backup SSL certificates
tar -czf ssl-backup-$(date +%Y%m%d).tar.gz ssl/
```

### Disaster Recovery

```bash
# Quick recovery steps
git pull
cp .env.backup.YYYYMMDD .env
docker-compose up -d
```

## Cost Management

### OpenAI Cost Estimation

- GPT-4o: ~$10 per 1M tokens
- Average message: ~50-100 tokens  
- 1000 responses/day ≈ $0.50-1.00/day

### Cost Optimization

1. **Use GPT-4o-mini** for lower costs:
   ```bash
   OPENAI_MODEL=gpt-4o-mini
   ```

2. **Adjust response frequency:**
   ```bash
   REPLY_TARGET_RATIO=0.05  # Reply to 5% instead of 10%
   GAP_MIN_SECONDS=60       # Wait 1 minute between replies
   ```

3. **Monitor usage:**
   ```bash
   # Check bot statistics
   curl https://yourdomain.com/webhook/telegram -X POST \
     -H "Content-Type: application/json" \
     -d '{"message": {"text": "/stats", "from": {"id": YOUR_USER_ID}}}'
   ```

## Support

For deployment issues:
1. Check logs: `docker-compose logs oleg-bot`
2. Verify configuration: Environment variables and webhook setup
3. Test endpoints: `/health` and `/`
4. Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md)