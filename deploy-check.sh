#!/bin/bash
# Deployment verification script for OlegBot

set -e

echo "🚀 OlegBot Deployment Check"
echo "=========================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found"
    echo "   Run: cp .env.example .env && nano .env"
    exit 1
fi

# Check required environment variables
echo "📋 Checking configuration..."

required_vars=(
    "TELEGRAM_BOT_TOKEN"
    "TELEGRAM_WEBHOOK_URL" 
    "OPENAI_API_KEY"
)

for var in "${required_vars[@]}"; do
    if grep -q "^${var}=" .env && grep -q "^${var}=.*[^=]" .env; then
        echo "✅ $var configured"
    else
        echo "❌ $var missing or empty in .env"
        exit 1
    fi
done

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found"
    echo "   Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found"
    echo "   Install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose available"

# Build and test
echo "🔨 Building container..."
docker build -t oleg-bot . --quiet

echo "🧪 Testing container..."
# Start container in background, test health, then stop
container_id=$(docker run -d --env-file .env -p 8000:8000 oleg-bot)

# Wait for startup
echo "   Waiting for startup..."
sleep 10

# Test health endpoint
if curl -f http://localhost:8000/health &> /dev/null; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    docker logs $container_id
    docker stop $container_id &> /dev/null
    docker rm $container_id &> /dev/null
    exit 1
fi

# Test bot status
if curl -f http://localhost:8000/bot/status &> /dev/null; then
    echo "✅ Bot status endpoint working"
else
    echo "⚠️  Bot status endpoint failed (expected - needs valid tokens)"
fi

# Cleanup
docker stop $container_id &> /dev/null
docker rm $container_id &> /dev/null

echo ""
echo "🎉 Deployment check completed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Set your domain in TELEGRAM_WEBHOOK_URL"
echo "   2. Deploy: docker compose up -d"
echo "   3. Check logs: docker compose logs -f oleg-bot"
echo "   4. Test: curl http://localhost:8000/health"
echo ""
echo "🔧 Monitoring endpoints:"
echo "   Health: http://localhost:8000/health"
echo "   Bot status: http://localhost:8000/bot/status"
echo "   Error stats: http://localhost:8000/webhook/errors"
echo "   Memory stats: http://localhost:8000/webhook/memory"