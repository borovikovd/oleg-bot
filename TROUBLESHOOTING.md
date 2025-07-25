# OlegBot Troubleshooting Guide

This guide helps diagnose and resolve common issues with OlegBot deployment and operation.

## Quick Diagnostic Commands

```bash
# Check if container is running
docker ps | grep oleg-bot

# View recent logs
docker-compose logs --tail=50 oleg-bot

# Check health endpoint
curl -i https://yourdomain.com/health

# Verify webhook status
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

## Common Issues and Solutions

### 1. Bot Not Responding to Messages

#### Symptoms
- Bot appears online but doesn't respond
- No log entries for incoming messages
- Webhook info shows pending updates

#### Diagnostic Steps

1. **Check webhook registration:**
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
   ```
   
   Expected response:
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

2. **Test webhook endpoint manually:**
   ```bash
   curl -X POST https://yourdomain.com/webhook/telegram \
     -H "Content-Type: application/json" \
     -d '{"update_id": 1, "message": {"message_id": 1, "date": 1234567890, "chat": {"id": 123}, "from": {"id": 456}, "text": "test"}}'
   ```

3. **Check application logs:**
   ```bash
   docker-compose logs -f oleg-bot
   ```

#### Solutions

- **Webhook not registered:** Re-register webhook with correct URL
- **SSL certificate issues:** Verify HTTPS works and certificate is valid
- **Wrong webhook secret:** Update webhook secret in both Telegram and environment
- **Firewall blocking requests:** Check network security groups/firewall rules

### 2. Configuration Validation Errors

#### Symptoms
- Container exits immediately after start
- Error logs show "Production configuration errors"
- Health check endpoint not accessible

#### Common Error Messages

**"TELEGRAM_BOT_TOKEN is required in production"**
```bash
# Solution: Set the bot token
echo "TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIjKlMnOpQrStUvWxYz" >> .env
docker-compose restart oleg-bot
```

**"Webhook URL must use HTTPS in production"**
```bash
# Solution: Use HTTPS URL
echo "TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook/telegram" >> .env
docker-compose restart oleg-bot
```

**"Invalid bot token format"**
```bash
# Solution: Verify token format (should contain exactly one colon)
# Correct: 123456789:ABCdefGhIjKlMnOpQrStUvWxYz
# Incorrect: 123456789-ABCdefGhIjKlMnOpQrStUvWxYz
```

**"OpenAI API key must start with 'sk-'"**
```bash
# Solution: Verify OpenAI API key format
echo "OPENAI_API_KEY=sk-proj-..." >> .env
docker-compose restart oleg-bot
```

### 3. OpenAI API Issues

#### Symptoms
- Bot responds with emoji reactions only
- Logs show "Failed to generate response"
- Fallback responses being used

#### Diagnostic Steps

1. **Check API key validity:**
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

2. **Monitor rate limits:**
   Look for HTTP 429 errors in logs

3. **Check model access:**
   Verify GPT-4o access in OpenAI dashboard

#### Solutions

- **Invalid API key:** Generate new key from OpenAI dashboard
- **Insufficient credits:** Add billing information to OpenAI account
- **Rate limiting:** Reduce request frequency or upgrade OpenAI plan
- **Model access:** Ensure GPT-4o access or switch to gpt-4o-mini

### 4. SSL/TLS Certificate Issues

#### Symptoms
- Webhook registration fails
- "SSL certificate verify failed" errors
- Telegram shows webhook as unhealthy

#### Diagnostic Steps

1. **Test SSL certificate:**
   ```bash
   openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
   ```

2. **Check certificate expiration:**
   ```bash
   echo | openssl s_client -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
   ```

3. **Verify certificate chain:**
   ```bash
   curl -I https://yourdomain.com/health
   ```

#### Solutions

- **Expired certificate:** Renew certificate and restart containers
- **Wrong domain:** Ensure certificate matches your domain
- **Missing intermediate certificates:** Include full certificate chain
- **Self-signed certificate:** Use proper CA-signed certificate for production

### 5. Memory and Performance Issues

#### Symptoms
- Container restarts frequently
- Slow response times
- High memory usage

#### Diagnostic Steps

1. **Check container resources:**
   ```bash
   docker stats oleg-bot
   ```

2. **Monitor memory usage:**
   ```bash
   docker-compose logs oleg-bot | grep -i "memory\|oom"
   ```

3. **Check response times:**
   ```bash
   time curl https://yourdomain.com/health
   ```

#### Solutions

- **Increase memory limits:** Update docker-compose.yml
- **Optimize message window:** Reduce WINDOW_SIZE
- **Reduce response frequency:** Lower REPLY_TARGET_RATIO
- **Use smaller model:** Switch to gpt-4o-mini

### 6. Network and Connectivity Issues

#### Symptoms
- Intermittent webhook failures
- Timeout errors in logs
- Cannot reach health check endpoint

#### Diagnostic Steps

1. **Test network connectivity:**
   ```bash
   # From container
   docker exec oleg-bot curl -I https://api.telegram.org
   docker exec oleg-bot curl -I https://api.openai.com
   ```

2. **Check DNS resolution:**
   ```bash
   nslookup yourdomain.com
   ```

3. **Verify port accessibility:**
   ```bash
   telnet yourdomain.com 443
   ```

#### Solutions

- **Firewall issues:** Configure security groups/firewall rules
- **DNS problems:** Update DNS records or use IP addresses
- **Network timeouts:** Increase timeout values in configuration

### 7. Docker and Container Issues

#### Symptoms
- Container won't start
- Build failures
- Permission errors

#### Common Issues

**"Permission denied" errors:**
```bash
# Solution: Fix file permissions
sudo chown -R $USER:$USER .
chmod +x scripts/*.sh
```

**"No space left on device":**
```bash
# Solution: Clean up Docker resources
docker system prune -a
docker volume prune
```

**"Port already in use":**
```bash
# Solution: Find and stop conflicting process
sudo lsof -i :8000
sudo kill -9 <PID>
```

**Image build failures:**
```bash
# Solution: Clear build cache and rebuild
docker-compose build --no-cache oleg-bot
```

## Debugging Commands

### Comprehensive Health Check

```bash
#!/bin/bash
# debug-health.sh

echo "=== OlegBot Health Check ==="

# Container status
echo "Container Status:"
docker ps | grep oleg-bot || echo "Container not running!"

# Health endpoint
echo -e "\nHealth Endpoint:"
curl -s https://yourdomain.com/health | jq '.' || echo "Health check failed!"

# Webhook info  
echo -e "\nWebhook Status:"
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo" | jq '.result'

# Recent logs
echo -e "\nRecent Logs:"
docker-compose logs --tail=10 oleg-bot

# Resource usage
echo -e "\nResource Usage:"
docker stats --no-stream oleg-bot
```

### Log Analysis

```bash
# Find error patterns
docker-compose logs oleg-bot | grep -i "error\|exception\|failed"

# Check for specific issues
docker-compose logs oleg-bot | grep -i "openai\|telegram\|webhook"

# Monitor real-time logs
docker-compose logs -f oleg-bot | grep -v "health"
```

### Configuration Validation

```bash
# Validate environment variables
docker exec oleg-bot python -c "
from src.oleg_bot.config import settings
print('Environment:', settings.environment)
print('Bot token configured:', bool(settings.telegram_bot_token))
print('OpenAI key configured:', bool(settings.openai_api_key))
print('Webhook URL:', settings.telegram_webhook_url)
errors = settings.validate_production_config()
if errors:
    print('Validation errors:')
    for error in errors:
        print(f'  - {error}')
else:
    print('Configuration valid!')
"
```

## Performance Optimization

### Resource Tuning

```yaml
# docker-compose.yml
services:
  oleg-bot:
    deploy:
      resources:
        limits:
          memory: 512M      # Adjust based on usage
          cpus: '0.5'       # Adjust based on load
    environment:
      - WINDOW_SIZE=30      # Reduce memory usage
      - GAP_MIN_SECONDS=30  # Reduce API calls
```

### Cost Optimization

```bash
# Monitor token usage
docker-compose logs oleg-bot | grep "tokens_used" | tail -10

# Adjust model for cost savings
echo "OPENAI_MODEL=gpt-4o-mini" >> .env
docker-compose restart oleg-bot
```

## Emergency Procedures

### Quick Recovery

```bash
#!/bin/bash
# emergency-restart.sh

echo "Emergency OlegBot recovery starting..."

# Stop services
docker-compose down

# Clear any corrupted containers
docker system prune -f

# Restart services
docker-compose up -d

# Wait for startup
sleep 30

# Verify health
curl -f https://yourdomain.com/health && echo "Recovery successful!" || echo "Recovery failed!"
```

### Rollback Procedure

```bash
# If you need to rollback to a previous version
git log --oneline -10  # Find previous commit
git checkout <previous-commit-hash>
docker-compose build
docker-compose up -d
```

### Emergency Contacts

When all else fails:

1. **Check service status pages:**
   - [Telegram Status](https://telegram.org/status)
   - [OpenAI Status](https://status.openai.com/)

2. **Review recent changes:**
   - Check git commits
   - Verify environment changes
   - Review infrastructure changes

3. **Gather diagnostic information:**
   ```bash
   # Create diagnostic bundle
   mkdir oleg-bot-debug
   docker-compose logs oleg-bot > oleg-bot-debug/container.log
   curl -s https://yourdomain.com/health > oleg-bot-debug/health.json
   curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo" > oleg-bot-debug/webhook.json
   tar -czf oleg-bot-debug-$(date +%Y%m%d-%H%M).tar.gz oleg-bot-debug/
   ```

## Getting Help

### Before Asking for Help

1. **Collect diagnostic information:**
   - Error messages from logs
   - Configuration (without sensitive data)
   - Steps to reproduce the issue
   - Expected vs actual behavior

2. **Try basic troubleshooting:**
   - Restart the container
   - Check configuration
   - Verify network connectivity
   - Review recent changes

### Useful Log Patterns

```bash
# Find configuration issues
grep -i "validation\|config" logs

# Find API issues  
grep -i "openai\|telegram\|api" logs

# Find performance issues
grep -i "timeout\|memory\|slow" logs

# Find webhook issues
grep -i "webhook\|update" logs
```

Remember: Most issues are configuration-related. Double-check your environment variables and webhook setup first!