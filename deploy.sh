#!/bin/bash
# ============================================================
# Nexus Finance MCP Server - VPS Deploy Script
# Target: Contabo VPS (62.171.141.206)
# ============================================================
set -e

DEPLOY_DIR="/root/nexus-finance-mcp"
SERVICE_NAME="nexus-finance-mcp"
PORT=8100

echo "========================================="
echo "  Nexus Finance MCP Server - Deploy"
echo "========================================="

# 1. Install system dependencies
echo "[1/6] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq python3-pip python3-venv > /dev/null 2>&1

# 2. Setup directory
echo "[2/6] Setting up directory..."
mkdir -p $DEPLOY_DIR
cd $DEPLOY_DIR

# 3. Install Python dependencies
echo "[3/6] Installing Python dependencies..."
pip install -r requirements.txt --break-system-packages -q

# 4. Verify .env
echo "[4/6] Checking .env..."
if [ ! -f .env ]; then
    echo "  ⚠ .env not found! Copy from .env.template and fill API keys:"
    echo "    cp .env.template .env"
    echo "    nano .env"
    exit 1
fi

# Check required keys
source .env
MISSING=0
for KEY in BOK_ECOS_API_KEY DART_API_KEY; do
    if [ -z "${!KEY}" ]; then
        echo "  ⚠ Missing: $KEY"
        MISSING=1
    else
        echo "  ✓ $KEY set"
    fi
done
for KEY in KOSIS_API_KEY RONE_API_KEY FRED_API_KEY; do
    if [ -z "${!KEY}" ]; then
        echo "  ○ Optional missing: $KEY"
    else
        echo "  ✓ $KEY set"
    fi
done

# 5. Install systemd service
echo "[5/6] Installing systemd service..."
cp $DEPLOY_DIR/$SERVICE_NAME.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

# 6. Verify
echo "[6/6] Verifying..."
sleep 3
if systemctl is-active --quiet $SERVICE_NAME; then
    echo ""
    echo "========================================="
    echo "  ✓ Server is RUNNING on port $PORT"
    echo "========================================="
    echo ""
    echo "  Endpoints:"
    echo "    Streamable HTTP: http://62.171.141.206:$PORT/mcp"
    echo "    SSE:             http://62.171.141.206:$PORT/sse"
    echo "    Health:          http://62.171.141.206:$PORT/"
    echo ""
    echo "  Logs:  journalctl -u $SERVICE_NAME -f"
    echo "  Stop:  systemctl stop $SERVICE_NAME"
    echo ""
    # Quick health check
    curl -s http://localhost:$PORT/ 2>/dev/null | head -5 || echo "  (health endpoint check pending)"
else
    echo "  ✗ Server failed to start"
    echo "  Check logs: journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi
