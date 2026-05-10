#!/bin/bash
# Script to update Cloudflare DNS with current tunnel URL
# Usage: ./update_cloudflare_dns.sh

set -e

# Configuration (set these in .env or export manually)
CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"
CLOUDFLARE_ZONE_ID="${CLOUDFLARE_ZONE_ID:-}"
DOMAIN_NAME="skastapp.online"
LOG_FILE="/workspace/AI-Assistant/logs/tunnel-chatbot.log"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "🌐 Cloudflare DNS Updater for $DOMAIN_NAME"
echo "=========================================="

# Get current tunnel URL
TUNNEL_URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$LOG_FILE" 2>/dev/null | head -1)

if [ -z "$TUNNEL_URL" ]; then
    echo -e "${RED}❌ No tunnel URL found in $LOG_FILE${NC}"
    echo "Make sure cloudflared tunnel is running first"
    exit 1
fi

# Extract just the hostname (remove https://)
TUNNEL_HOST=$(echo "$TUNNEL_URL" | sed 's|https://||')

echo -e "${GREEN}✅ Current tunnel: $TUNNEL_URL${NC}"
echo -e "   Hostname: $TUNNEL_HOST"
echo ""

# Save to file for reference
echo "$TUNNEL_URL" > /workspace/AI-Assistant/current_tunnel.txt
echo "Saved to: /workspace/AI-Assistant/current_tunnel.txt"
echo ""

# Check if API credentials are set
if [ -z "$CLOUDFLARE_API_TOKEN" ] || [ -z "$CLOUDFLARE_ZONE_ID" ]; then
    echo -e "${YELLOW}⚠️  Cloudflare API credentials not set${NC}"
    echo ""
    echo "To enable automatic DNS updates, set these environment variables:"
    echo "  export CLOUDFLARE_API_TOKEN='your_api_token'"
    echo "  export CLOUDFLARE_ZONE_ID='your_zone_id'"
    echo ""
    echo "Or add them to /workspace/AI-Assistant/.env"
    echo ""
    echo "=========================================="
    echo "📋 MANUAL STEPS:"
    echo "=========================================="
    echo ""
    echo "1. Go to https://dash.cloudflare.com"
    echo "2. Select your domain: $DOMAIN_NAME"
    echo "3. Go to DNS > Records"
    echo "4. Find or create CNAME record:"
    echo "   - Type: CNAME"
    echo "   - Name: @"
    echo "   - Target: $TUNNEL_HOST"
    echo "   - Proxy status: Proxied (orange cloud)"
    echo ""
    echo "5. Optionally add www subdomain:"
    echo "   - Type: CNAME"
    echo "   - Name: www"
    echo "   - Target: $TUNNEL_HOST"
    echo "   - Proxy status: Proxied"
    echo ""
    exit 0
fi

# Function to update DNS record
update_dns_record() {
    local record_name=$1
    local full_name=$2
    
    echo "Checking $full_name..."
    
    # Get existing record
    EXISTING=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records?type=CNAME&name=$full_name" \
        -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
        -H "Content-Type: application/json")
    
    RECORD_ID=$(echo "$EXISTING" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r['result'][0]['id'] if r['result'] else '')" 2>/dev/null)
    
    if [ -n "$RECORD_ID" ]; then
        # Update existing record
        echo "  Updating existing record..."
        RESULT=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records/$RECORD_ID" \
            -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
            -H "Content-Type: application/json" \
            --data "{\"type\":\"CNAME\",\"name\":\"$record_name\",\"content\":\"$TUNNEL_HOST\",\"ttl\":1,\"proxied\":true}")
    else
        # Create new record
        echo "  Creating new record..."
        RESULT=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records" \
            -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
            -H "Content-Type: application/json" \
            --data "{\"type\":\"CNAME\",\"name\":\"$record_name\",\"content\":\"$TUNNEL_HOST\",\"ttl\":1,\"proxied\":true}")
    fi
    
    SUCCESS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)
    
    if [ "$SUCCESS" = "True" ]; then
        echo -e "  ${GREEN}✅ $full_name -> $TUNNEL_HOST${NC}"
    else
        echo -e "  ${RED}❌ Failed to update $full_name${NC}"
        echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"
    fi
}

echo ""
echo "Updating Cloudflare DNS records..."
echo ""

# Update root domain and www
update_dns_record "@" "$DOMAIN_NAME"
update_dns_record "www" "www.$DOMAIN_NAME"

echo ""
echo "=========================================="
echo -e "${GREEN}✅ DNS update complete!${NC}"
echo ""
echo "Your app should be accessible at:"
echo "  - https://$DOMAIN_NAME"
echo "  - https://www.$DOMAIN_NAME"
echo ""
echo "Note: DNS propagation may take a few minutes"
echo "=========================================="
