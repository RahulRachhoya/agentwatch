# Security Documentation

AgentWatch implements multiple layers of security to protect your monitoring infrastructure and prevent unauthorized access.

## Security Controls

### 1. API Key Authentication

**Enforcement:** All HTTP endpoints (except `/health`) and WebSocket connections require authentication.

**Configuration:**

```bash
export AGENTWATCH_API_KEY="your-secret-key-here"
```

**Behavior:**
- If `AGENTWATCH_API_KEY` is not set: Authentication is disabled (development mode)
- If set: All requests must include `X-API-Key` header matching the configured value

**Protected Endpoints:**
- `POST /v1/runs`
- `PATCH /v1/runs/{run_id}`
- `GET /v1/runs`
- `GET /v1/runs/{run_id}`
- `POST /v1/spans/batch`
- `POST /v1/traces` (OTLP ingestion)
- `WebSocket /ws`

**Unprotected Endpoints:**
- `GET /health` (health check)

**Example:**

```bash
# Without API key (will fail if AGENTWATCH_API_KEY is set)
curl http://localhost:8000/v1/runs

# With API key
curl -H "X-API-Key: your-secret-key-here" http://localhost:8000/v1/runs
```

**Implementation Details:**
- Uses `secrets.compare_digest()` for timing-safe comparison
- Prevents timing attacks that could leak key information
- Returns HTTP 401 with "Unauthorized" message on failure

---

### 2. WebSocket Authentication

**Enforcement:** WebSocket connections at `/ws` require `X-API-Key` header during handshake.

**Configuration:**

Same as HTTP authentication. Uses `AGENTWATCH_API_KEY` environment variable.

**Behavior:**
- Connection rejected with code 1008 (policy violation) if:
  - `X-API-Key` header is missing
  - `X-API-Key` header doesn't match configured value
- Connection accepted if authentication passes or auth is disabled

**Example (Python):**

```python
from websockets.sync.client import connect

# Connect with authentication
with connect(
    "ws://localhost:8000/ws",
    additional_headers={"X-API-Key": "your-secret-key-here"}
) as websocket:
    # Connection established
    pass
```

**Example (JavaScript):**

```javascript
const ws = new WebSocket('ws://localhost:8000/ws', {
    headers: {
        'X-API-Key': 'your-secret-key-here'
    }
});
```

---

### 3. Rate Limiting

**Enforcement:** Per-IP rate limits prevent abuse and DoS attacks.

**Configuration:**

Rate limits are hardcoded in the application. To modify, edit `backend/main.py`:

```python
@limiter.limit("1000/minute")  # Adjust this value
async def create_spans(...):
    ...
```

**Current Limits:**
- `POST /v1/spans/batch`: 1000 requests per minute per IP

**Behavior:**
- Exceeding rate limit returns HTTP 429 (Too Many Requests)
- Rate limit window resets after 1 minute
- Each IP address has independent rate limit counter

**Implementation:**
- Uses `slowapi` library
- Rate limiting based on client IP address (`get_remote_address`)
- Stateless (in-memory) rate limiting suitable for single-instance deployments

**Future Enhancements:**
- Redis-backed distributed rate limiting for multi-instance deployments
- Per-API-key rate limiting
- Configurable rate limits via environment variables

---

### 4. CORS Configuration

**Purpose:** Control which web origins can access the API from browsers.

**Configuration:**

```bash
# Development (default): Allow all origins
# ALLOWED_ORIGINS is not set or set to "*"

# Production: Restrict to specific origins
export ALLOWED_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
```

**Behavior:**
- If `ALLOWED_ORIGINS` contains `*`: All origins allowed (logs warning)
- If set to specific origins: Only listed origins allowed
- Origins are comma-separated
- Preflight requests (OPTIONS) are handled automatically

**Recommended Settings:**

| Environment | Configuration | Rationale |
|-------------|---------------|-----------|
| Local Dev | `*` or `http://localhost:3000` | Convenience |
| Staging | Specific staging domains | Security + testing |
| Production | **Only production domains** | Security |

**Security Warning:**

Using `ALLOWED_ORIGINS=*` in production allows any website to call your API from JavaScript. This can lead to:
- Cross-site request forgery (CSRF) if combined with weak authentication
- Data exposure if API keys are leaked
- Unintended API usage from untrusted origins

**Example:**

```bash
# Good (production)
ALLOWED_ORIGINS="https://agentwatch.example.com"

# Bad (production)
ALLOWED_ORIGINS="*"
```

---

### 5. Error Message Sanitization

**Purpose:** Prevent information disclosure through error messages.

**Implementation:**
- Global exception handler intercepts unhandled exceptions
- Returns generic "Internal server error" message to clients
- Logs full error details server-side for debugging
- Never exposes stack traces, file paths, or internal details

**Example:**

```python
# If an internal error occurs (e.g., database connection failure)
# Client receives:
{
    "error": "Internal server error",
    "message": "An unexpected error occurred. Please contact support if the issue persists."
}

# Server logs contain full error details:
# ERROR: Unhandled exception: sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) ...
```

**Protected Information:**
- Stack traces
- File system paths (`/home/user/...`)
- Database error messages
- Library versions
- Internal variable names

**Validation Errors:**

Validation errors (e.g., malformed JSON, missing required fields) return detailed error messages because they are client-side errors, not security issues.

---

## Security Best Practices

### Deployment

1. **Always set `AGENTWATCH_API_KEY` in production**
   ```bash
   export AGENTWATCH_API_KEY=$(openssl rand -hex 32)
   ```

2. **Restrict CORS to your frontend domain**
   ```bash
   export ALLOWED_ORIGINS="https://yourdomain.com"
   ```

3. **Use HTTPS in production**
   - Terminate TLS at reverse proxy (nginx, Caddy, CloudFlare)
   - Never send API keys over plain HTTP

4. **Rotate API keys regularly**
   - Treat API keys like passwords
   - Rotate if compromised or quarterly

5. **Monitor rate limit violations**
   - Check logs for HTTP 429 responses
   - Investigate repeated violations (may indicate attack)

### Secret Management

**Bad:**
```python
# Hardcoded secret in code
AGENTWATCH_API_KEY = "secret-key-12345"
```

**Good:**
```python
# Load from environment
AGENTWATCH_API_KEY = os.getenv("AGENTWATCH_API_KEY")
```

**Better:**
```bash
# Use secret manager (AWS Secrets Manager, HashiCorp Vault, etc.)
export AGENTWATCH_API_KEY=$(aws secretsmanager get-secret-value --secret-id agentwatch-api-key --query SecretString --output text)
```

### Network Security

1. **Firewall rules:** Restrict access to port 8000 to trusted networks
2. **VPN/VPC:** Deploy AgentWatch inside private network
3. **Reverse proxy:** Use nginx/Caddy for TLS termination and additional security headers

**Example nginx configuration:**

```nginx
server {
    listen 443 ssl http2;
    server_name agentwatch.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## Testing Security Controls

### Manual Testing

**1. Test API Key Authentication:**

```bash
# Should return 401
curl http://localhost:8000/v1/runs

# Should return 200
curl -H "X-API-Key: your-secret-key" http://localhost:8000/v1/runs
```

**2. Test WebSocket Authentication:**

```bash
# Install wscat
npm install -g wscat

# Should be rejected
wscat -c ws://localhost:8000/ws

# Should connect
wscat -c ws://localhost:8000/ws -H "X-API-Key: your-secret-key"
```

**3. Test Rate Limiting:**

```bash
# Send rapid requests
for i in {1..1100}; do
    curl -H "X-API-Key: your-secret-key" \
         -X POST http://localhost:8000/v1/spans/batch \
         -H "Content-Type: application/json" \
         -d '{"spans":[]}'
done
# Should see 429 responses after 1000 requests
```

### Automated Testing

**Run security test suite:**

```bash
# Python test suite
cd tests
python test_security.py

# Shell script (requires curl, jq, wscat)
./manual_security_test.sh

# Python manual test script
python manual_security_test.py
```

---

## Security Checklist

Before deploying to production:

- [ ] `AGENTWATCH_API_KEY` is set and stored securely
- [ ] `ALLOWED_ORIGINS` is set to specific domains (not `*`)
- [ ] HTTPS is enabled (via reverse proxy)
- [ ] Firewall rules restrict access to trusted networks
- [ ] Rate limiting is configured appropriately
- [ ] Security tests pass
- [ ] Error logs are monitored but not exposed to clients
- [ ] API keys are rotated regularly
- [ ] Database credentials are stored securely
- [ ] Backup and disaster recovery plan is in place

---

## Vulnerability Reporting

If you discover a security vulnerability in AgentWatch, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Email security details to: [maintainer email]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you to address the issue.

---

## Security Roadmap

Planned security enhancements:

- [ ] JWT-based authentication with token expiration
- [ ] Role-based access control (RBAC)
- [ ] Audit logging for sensitive operations
- [ ] Redis-backed distributed rate limiting
- [ ] API key scoping (read-only vs. read-write)
- [ ] IP whitelisting
- [ ] Request signing (HMAC-SHA256)
- [ ] Automatic secret rotation
- [ ] Security scanning in CI/CD pipeline

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [WebSocket Security](https://owasp.org/www-community/vulnerabilities/WebSocket_security)
- [Rate Limiting Best Practices](https://cloud.google.com/architecture/rate-limiting-strategies-techniques)
