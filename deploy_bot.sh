#!/bin/bash

# VPN Bot Deployment Script
# This script deploys the VPN bot using Docker

set -e

echo "🚀 VPN Bot Deployment"
echo "===================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${RED}❗ Please edit .env file with your configuration before continuing${NC}"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed${NC}"

# Create necessary directories
mkdir -p data logs

# Set permissions
chmod 755 data logs

echo -e "${GREEN}✓ Directories created${NC}"

# Build and start the bot
echo "Building Docker image..."
docker-compose build --no-cache

echo "Starting bot container..."
docker-compose up -d

# Wait for container to start
sleep 3

# Check container status
if docker ps | grep -q marzban_vpn_bot; then
    echo -e "${GREEN}✅ Bot deployed successfully!${NC}"
    echo ""
    echo "View logs: docker-compose logs -f"
    echo "Stop bot: docker-compose down"
    echo "Restart bot: docker-compose restart"
else
    echo -e "${RED}❌ Bot failed to start. Check logs: docker-compose logs${NC}"
    exit 1
fi
