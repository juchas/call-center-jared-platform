# Call Center Jared Platform

Open-source multi-tenant SaaS wrapper around [CallCenterJared](https://github.com/YourJared/CallCenterJared).

Each tenant provides their own OpenAI and ServiceNow credentials. The platform provisions a dedicated [Koyeb](https://koyeb.com) service per tenant and returns a unique Twilio webhook URL.

## Architecture

```
Next.js frontend  →  Control plane (FastAPI)  ↔  PostgreSQL
                           ↓
                       Koyeb API
                      ↙    ↓    ↘
               Tenant A  Tenant B  Tenant C
               (CCJ app) (CCJ app) (CCJ app)
                    ↑
                 Twilio inbound calls
```

## Getting started

### Prerequisites
- Docker & Docker Compose
- Koyeb account + API token
- PostgreSQL (or use the included compose service)

### 1. Clone and configure

```bash
git clone https://github.com/juchas/call-center-jared-platform
cd call-center-jared-platform
cp .env.example .env
# Fill in KOYEB_TOKEN, ENCRYPTION_KEY, DATABASE_URL
```

Generate an encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Run locally

```bash
docker compose up
```

- Control plane: http://localhost:8000
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

### 3. Create a tenant

```bash
curl -X POST http://localhost:8000/api/tenants \
  -H 'Content-Type: application/json' \
  -d '{
    "label": "My Company",
    "openai_key": "sk-...",
    "sn_instance": "myinstance",
    "sn_user": "admin",
    "sn_pass": "secret"
  }'
```

The response includes `webhook_url` — point your Twilio number's voice webhook to this URL.

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/tenants` | Create tenant + deploy Koyeb service |
| `GET` | `/api/tenants` | List all tenants |
| `GET` | `/api/tenants/:id` | Get tenant status |
| `PUT` | `/api/tenants/:id` | Update credentials (re-deploys) |
| `DELETE` | `/api/tenants/:id` | Tear down service + delete tenant |

## Contributing

PRs welcome. Please open an issue first for significant changes.

## License

MIT
