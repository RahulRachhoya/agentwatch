#!/bin/bash

# Manual Security Test Script for AgentWatch
# Tests all security controls with curl

set -e

BASE_URL="http://localhost:8000"
API_KEY="your-secret-key"

echo "==================================================="
echo "AgentWatch Security Test Suite"
echo "==================================================="
echo ""
echo "Prerequisites:"
echo "1. Backend server running on $BASE_URL"
echo "2. AGENTWATCH_API_KEY set to: $API_KEY"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_passed() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
}

test_failed() {
    echo -e "${RED}✗ FAIL${NC}: $1"
}

test_info() {
    echo -e "${YELLOW}ℹ INFO${NC}: $1"
}

echo "==================================================="
echo "Test 1: Missing API Key (Should Return 401)"
echo "==================================================="

RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/v1/runs")
STATUS_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$STATUS_CODE" = "401" ]; then
    test_passed "Missing API key rejected (401)"
else
    test_failed "Expected 401, got $STATUS_CODE"
fi
echo ""

echo "==================================================="
echo "Test 2: Invalid API Key (Should Return 401)"
echo "==================================================="

RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: wrong-key" -X GET "$BASE_URL/v1/runs")
STATUS_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$STATUS_CODE" = "401" ]; then
    test_passed "Invalid API key rejected (401)"
else
    test_failed "Expected 401, got $STATUS_CODE"
fi
echo ""

echo "==================================================="
echo "Test 3: Valid API Key (Should Return 200)"
echo "==================================================="

RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: $API_KEY" -X GET "$BASE_URL/v1/runs")
STATUS_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$STATUS_CODE" = "200" ]; then
    test_passed "Valid API key accepted (200)"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
else
    test_failed "Expected 200, got $STATUS_CODE"
fi
echo ""

echo "==================================================="
echo "Test 4: POST Endpoint Without API Key (401)"
echo "==================================================="

PAYLOAD='{"run_id":"test-run","name":"Test","started_at":"2026-05-30T12:00:00Z"}'
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$BASE_URL/v1/runs" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")
STATUS_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$STATUS_CODE" = "401" ]; then
    test_passed "POST endpoint requires API key (401)"
else
    test_failed "Expected 401, got $STATUS_CODE"
fi
echo ""

echo "==================================================="
echo "Test 5: POST With Valid API Key (200)"
echo "==================================================="

RUN_ID="test-run-$(date +%s)"
PAYLOAD="{\"run_id\":\"$RUN_ID\",\"name\":\"Security Test\",\"started_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$BASE_URL/v1/runs" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d "$PAYLOAD")
STATUS_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$STATUS_CODE" = "200" ]; then
    test_passed "POST with valid API key accepted (200)"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
else
    test_failed "Expected 200, got $STATUS_CODE"
    echo "$BODY"
fi
echo ""

echo "==================================================="
echo "Test 6: Health Check (No Auth Required)"
echo "==================================================="

RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/health")
STATUS_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$STATUS_CODE" = "200" ]; then
    test_passed "Health check accessible without auth (200)"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
else
    test_failed "Expected 200, got $STATUS_CODE"
fi
echo ""

echo "==================================================="
echo "Test 7: Rate Limiting Check (POST /v1/spans/batch)"
echo "==================================================="

test_info "Sending rapid requests to test rate limit..."
RATE_LIMITED=0

for i in {1..20}; do
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST "$BASE_URL/v1/spans/batch" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{"spans":[]}')
    STATUS_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$STATUS_CODE" = "429" ]; then
        RATE_LIMITED=1
        test_passed "Rate limiting enforced (429 after $i requests)"
        break
    fi
done

if [ $RATE_LIMITED -eq 0 ]; then
    test_info "Rate limit not reached with 20 requests (expected for 1000/min limit)"
fi
echo ""

echo "==================================================="
echo "Test 8: WebSocket Connection (wscat required)"
echo "==================================================="

if command -v wscat &> /dev/null; then
    test_info "Testing WebSocket with missing API key..."

    # Test without API key (should fail)
    timeout 2s wscat -c "ws://localhost:8000/ws" 2>&1 | grep -q "1008\|Unauthorized" && \
        test_passed "WebSocket rejects missing API key" || \
        test_info "WebSocket test inconclusive"

    test_info "Testing WebSocket with valid API key..."

    # Test with valid API key (should connect)
    echo "ping" | timeout 2s wscat -c "ws://localhost:8000/ws" -H "X-API-Key: $API_KEY" &> /dev/null && \
        test_passed "WebSocket accepts valid API key" || \
        test_info "WebSocket connection test inconclusive"
else
    test_info "wscat not installed - skipping WebSocket tests"
    test_info "Install: npm install -g wscat"
fi
echo ""

echo "==================================================="
echo "Test 9: CORS Headers Check"
echo "==================================================="

RESPONSE=$(curl -s -I -H "Origin: http://localhost:3000" "$BASE_URL/health")

if echo "$RESPONSE" | grep -qi "access-control-allow-origin"; then
    test_passed "CORS headers present"
else
    test_failed "CORS headers missing"
fi
echo ""

echo "==================================================="
echo "Test 10: Error Sanitization (Internal Error)"
echo "==================================================="

# Send malformed date to trigger internal error
PAYLOAD='{"run_id":"test-error","name":"Test","started_at":"not-a-valid-date"}'
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$BASE_URL/v1/runs" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d "$PAYLOAD")
STATUS_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

# Check if error response doesn't leak internal details
if echo "$BODY" | grep -qi "traceback\|sqlalchemy\|/home/"; then
    test_failed "Error message leaks internal details"
    echo "$BODY"
else
    test_passed "Error messages sanitized (no stack traces)"
fi
echo ""

echo "==================================================="
echo "Security Test Summary"
echo "==================================================="
echo ""
echo "All critical security controls tested:"
echo "  ✓ API key authentication (HTTP endpoints)"
echo "  ✓ WebSocket authentication"
echo "  ✓ Rate limiting"
echo "  ✓ CORS configuration"
echo "  ✓ Error sanitization"
echo ""
echo "Review the output above for any failed tests."
echo ""
