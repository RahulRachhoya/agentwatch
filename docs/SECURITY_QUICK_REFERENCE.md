# Security Quick Reference

One-page reference for AgentWatch security controls.

---

## Environment Variables

```bash
# Required for production
export AGENTWATCH_API_KEY="$(openssl rand -hex 32)"
export ALLOWED_ORIGINS="https://yourdomain.com"

# Optional
export DATABASE_URL="postgresql+asyncpg://user:pass@host/db"
```

---

## HTTP Endpoints

### Authentication Required
All endpoints except `/health` require `X-API-Key` header:

```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/v1/runs
```

### Rate Limits
- `POST /v1/spans/batch`: 1000 requests/minute per IP

---

## WebSocket

### Connection
Requires `X-API-Key` header during handshake:

**Python:**
```python
from websockets.sync.client import connect

with connect(
    "ws://localhost:8000/ws",
    additional_headers={"X-API-Key": "your-secret-key"}
) as ws:
    data = ws.recv()
```

**JavaScript:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws', {
    headers: { 'X-API-Key': 'your-secret-key' }
});
```

**CLI (wscat):**
```bash
wscat -c ws://localhost:8000/ws -H "X-API-Key: your-secret-key"
```

---

## Error Responses

### Authentication Errors
```json
// 401 Unauthorized
{
    "detail": "Unauthorized: Missing API Key"
}
```

### Rate Limit Exceeded
```json
// 429 Too Many Requests
{
    "error": "Rate limit exceeded"
}
```

### Internal Errors
```json
// 500 Internal Server Error
{
    "error": "Internal server error",
    "message": "An unexpected error occurred. Please contact support if the issue persists."
}
```

---

## Production Deployment Checklist

- [ ] Set `AGENTWATCH_API_KEY` (minimum 32 characters)
- [ ] Set `ALLOWED_ORIGINS` to specific domains (not `*`)
- [ ] Enable HTTPS via reverse proxy
- [ ] Configure firewall to restrict port 8000
- [ ] Set up SSL/TLS certificates
- [ ] Configure monitoring and alerts
- [ ] Test all security controls
- [ ] Document API key location and rotation schedule

---

## Security Testing

### Quick Tests

**1. Test API Key Auth:**
```bash
# Should fail (401)
curl http://localhost:8000/v1/runs

# Should succeed (200)
curl -H "X-API-Key: your-key" http://localhost:8000/v1/runs
```

**2. Test WebSocket Auth:**
```bash
# Should fail
wscat -c ws://localhost:8000/ws

# Should succeed
wscat -c ws://localhost:8000/ws -H "X-API-Key: your-key"
```

**3. Test Rate Limiting:**
```bash
# Send 1001 requests
for i in {1..1001}; do
    curl -H "X-API-Key: your-key" \
         -X POST http://localhost:8000/v1/spans/batch \
         -d '{"spans":[]}'
done
# Should see 429 after 1000 requests
```

### Automated Tests

```bash
# Static validation (no server needed)
python3 tests/validate_security_changes.py

# Full test suite (requires running server)
python3 tests/test_security.py

# Manual tests (requires running server)
python3 tests/manual_security_test.py
```

---

## Common Issues

### Issue: WebSocket Connection Refused
**Cause:** Missing or invalid `X-API-Key` header  
**Fix:** Add `X-API-Key` header to WebSocket connection

### Issue: 401 Unauthorized on All Requests
**Cause:** `AGENTWATCH_API_KEY` environment variable not set or wrong  
**Fix:** Verify environment variable matches request header

### Issue: 429 Rate Limit Exceeded
**Cause:** Too many requests from same IP  
**Fix:** Wait 1 minute or increase rate limit in code

### Issue: CORS Error in Browser
**Cause:** Origin not in `ALLOWED_ORIGINS`  
**Fix:** Add your frontend domain to `ALLOWED_ORIGINS`

---

## Security Contacts

**Report vulnerabilities:** [maintainer email]  
**Documentation:** `/docs/SECURITY.md`  
**Implementation details:** `/docs/SECURITY_CHANGES.md`

---

## Quick Commands

```bash
# Generate secure API key
openssl rand -hex 32

# Start server with security enabled
export AGENTWATCH_API_KEY="your-secret-key"
export ALLOWED_ORIGINS="http://localhost:3000"
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000

# Check server health (no auth required)
curl http://localhost:8000/health

# List runs (auth required)
curl -H "X-API-Key: your-secret-key" http://localhost:8000/v1/runs

# Connect to WebSocket
wscat -c ws://localhost:8000/ws -H "X-API-Key: your-secret-key"
```

---

**Last Updated:** 2026-05-30  
**Version:** 1.0.0
