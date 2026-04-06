# Purple Team GPT - Secrets Management Guide

## Overview

This document provides comprehensive guidance for managing secrets in Purple Team GPT deployments. Proper secrets management is critical for security and compliance.

## Table of Contents

1. [Secret Types](#secret-types)
2. [Generation](#generation)
3. [Storage](#storage)
4. [Deployment](#deployment)
5. [Rotation](#rotation)
6. [Recovery](#recovery)
7. [Audit and Compliance](#audit-and-compliance)

---

## Secret Types

### Application Secrets

| Secret | Purpose | Length | Rotation |
|--------|---------|--------|----------|
| `APP_SECRET_KEY` | JWT token signing | 64 chars (min) | 90 days |
| `API_KEY_SALT` | API key generation | 32 chars | 90 days |
| `APP_JWT_SECRET` | JWT verification | 64 chars (min) | 90 days |

### Database Secrets

| Secret | Purpose | Length | Rotation |
|--------|---------|--------|----------|
| `DB_PASSWORD` | PostgreSQL authentication | 32 chars (min) | 90 days |
| `REDIS_PASSWORD` | Redis authentication | 32 chars (min) | 90 days |
| `CHROMA_AUTH_TOKEN` | ChromaDB authentication | 32 chars (min) | 90 days |

### LLM Provider API Keys

| Secret | Purpose | Rotation |
|--------|---------|----------|
| `LLM_OPENAI_API_KEY` | OpenAI API access | On compromise |
| `LLM_ANTHROPIC_API_KEY` | Anthropic API access | On compromise |
| `LLM_GROQ_API_KEY` | Groq API access | On compromise |
| `LLM_DEEPSEEK_API_KEY` | DeepSeek API access | On compromise |
| `LLM_MISTRAL_API_KEY` | Mistral API access | On compromise |

---

## Generation

### Using the Secrets Generator Script

```bash
# Generate secrets to stdout
./scripts/generate-secrets.sh

# Generate to a file
./scripts/generate-secrets.sh -o .env.production

# Generate in JSON format
./scripts/generate-secrets.sh -f json -o secrets.json

# Generate Docker Compose secrets format
./scripts/generate-secrets.sh -f docker -o docker-secrets.yml
```

### Manual Generation

```bash
# Using Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Using OpenSSL
openssl rand -hex 32

# Using Bash (less secure, not recommended)
head -c 32 /dev/urandom | base64
```

### Password Requirements

All passwords and secrets must:
- Be at least 32 characters (64 recommended for signing keys)
- Use cryptographically secure random generation
- Contain mixed case, numbers, and special characters (if applicable)
- Not be based on dictionary words or patterns
- Be unique per environment

---

## Storage

### Development

For local development, use `.env` files with proper gitignore rules:

```bash
# .gitignore
.env
.env.local
.env.*.local
secrets/
*.pem
*.key
```

**Never commit `.env` files to version control!**

### Production Options

#### Option 1: Docker Secrets (Recommended for Docker Swarm)

```yaml
# docker-compose.prod.yml
services:
  backend:
    secrets:
      - app_secret_key
      - db_password
    environment:
      - APP_SECRET_KEY_FILE=/run/secrets/app_secret_key

secrets:
  app_secret_key:
    external: true
  db_password:
    external: true
```

Create secrets:
```bash
echo "your-secret-key" | docker secret create app_secret_key -
echo "your-db-password" | docker secret create db_password -
```

#### Option 2: HashiCorp Vault

```bash
# Store secrets
vault kv put secret/purple-team-gpt \
  app_secret_key=your-key \
  db_password=your-password

# Retrieve in application
vault kv get -field=app_secret_key secret/purple-team-gpt
```

#### Option 3: AWS Secrets Manager

```bash
# Store secrets
aws secretsmanager create-secret \
  --name purple-team-gpt/app-secret-key \
  --secret-string "your-secret-key"

# Retrieve in application
aws secretsmanager get-secret-value \
  --secret-id purple-team-gpt/app-secret-key
```

#### Option 4: Azure Key Vault

```bash
# Store secret
az keyvault secret set \
  --vault-name purple-team-vault \
  --name app-secret-key \
  --value "your-secret-key"

# Retrieve
az keyvault secret show \
  --vault-name purple-team-vault \
  --name app-secret-key
```

#### Option 5: Kubernetes Secrets

```yaml
# kubernetes/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: purple-team-secrets
type: Opaque
stringData:
  app-secret-key: "your-secret-key"
  db-password: "your-password"
```

```bash
# Create from literal
kubectl create secret generic purple-team-secrets \
  --from-literal=app-secret-key=your-key \
  --from-literal=db-password=your-password
```

---

## Deployment

### CI/CD Pipeline Integration

#### GitHub Actions

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy
        env:
          APP_SECRET_KEY: ${{ secrets.APP_SECRET_KEY }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          # Deploy with secrets
          docker-compose up -d
```

Configure secrets at: `Settings > Secrets and variables > Actions`

#### GitLab CI

```yaml
# .gitlab-ci.yml
deploy:
  script:
    - docker-compose up -d
  variables:
    APP_SECRET_KEY: $APP_SECRET_KEY  # Set in CI/CD variables
```

### Environment Variables Best Practices

1. **Never log secrets** - Ensure logging does not capture environment variables
2. **Use secret references** - Don't copy-paste secrets in configs
3. **Limit access** - Only necessary services should have access to each secret
4. **Encrypt at rest** - Use encrypted storage for secrets
5. **Encrypt in transit** - Use TLS for all secret transmission

### Docker Compose with Secrets

```yaml
# docker-compose.yml (production)
services:
  backend:
    environment:
      - APP_SECRET_KEY_FILE=/run/secrets/app_secret_key
      - DB_PASSWORD_FILE=/run/secrets/db_password
    secrets:
      - app_secret_key
      - db_password
      - redis_password
    volumes:
      - ./secrets:/run/secrets:ro

secrets:
  app_secret_key:
    file: ./secrets/app_secret_key.txt
  db_password:
    file: ./secrets/db_password.txt
  redis_password:
    file: ./secrets/redis_password.txt
```

---

## Rotation

### Rotation Schedule

| Secret Type | Rotation Frequency | Notes |
|-------------|-------------------|-------|
| APP_SECRET_KEY | 90 days | Invalidates all JWTs |
| DB_PASSWORD | 90 days | Requires DB update |
| REDIS_PASSWORD | 90 days | Requires Redis restart |
| API Keys | On compromise | Regenerate immediately |
| LLM API Keys | On compromise | Regenerate via provider |

### Rotation Procedure

#### Application Secret Key

```bash
# 1. Generate new secret
NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# 2. Update in secrets manager
aws secretsmanager update-secret \
  --secret-id purple-team-gpt/app-secret-key \
  --secret-string "$NEW_SECRET"

# 3. Restart application (users will need to re-login)
docker-compose restart backend

# 4. Verify new tokens work
curl -X POST https://api.example.com/api/auth/login \
  -d '{"username":"test","password":"test"}'
```

#### Database Password

```bash
# 1. Generate new password
NEW_PASSWORD=$(openssl rand -hex 32)

# 2. Update PostgreSQL
docker exec -it purple-team-postgres psql -U postgres -c \
  "ALTER USER postgres PASSWORD '$NEW_PASSWORD';"

# 3. Update secrets manager
# 4. Restart services using the password
docker-compose restart backend
```

### Automated Rotation

Set up automated rotation with a cron job or scheduled task:

```bash
# /etc/cron.d/secret-rotation
# Run on the 1st of every month
0 0 1 * * root /opt/purple-team-gpt/scripts/rotate-secrets.sh
```

---

## Recovery

### Secret Recovery Procedure

1. **Identify compromised secret** - Check audit logs
2. **Generate new secret** - Use the secrets generator
3. **Update all systems** - Secrets manager, databases, applications
4. **Invalidate old credentials** - Force re-authentication
5. **Notify affected users** - If applicable
6. **Document incident** - For audit trail

### Backup Procedures

```bash
# Backup secrets to encrypted file (AWS)
aws secretsmanager get-secret-value \
  --secret-id purple-team-gpt/app-secret-key \
  --query SecretString --output text | \
  gpg --symmetric --cipher-algo AES256 \
  -o /backup/app-secret-key.gpg

# Restore from backup
gpg -d /backup/app-secret-key.gpg | \
  aws secretsmanager create-secret \
  --name purple-team-gpt/app-secret-key \
  --secret-string file:///dev/stdin
```

---

## Audit and Compliance

### Audit Logging

Enable audit logging for all secret access:

```yaml
# application config
AUDIT_LOG_ENABLED: true
AUDIT_LOG_SECRET_ACCESS: true
```

### Compliance Requirements

#### SOC 2 Type II
- Secrets encrypted at rest and in transit
- Access logging and monitoring
- Regular rotation (90 days)
- Least privilege access

#### PCI DSS
- Strong cryptography for stored secrets
- Different secrets per environment
- Quarterly secret rotation
- Secure distribution methods

#### HIPAA
- Encrypted secret storage
- Access controls and audit logs
- Regular risk assessments
- Incident response procedures

### Audit Checklist

```bash
# Run security audit
./scripts/security-audit.sh

# Check for exposed secrets
git log -p | grep -E "(password|secret|key|token)" || echo "No secrets found in git history"

# Verify secret file permissions
find . -name "*.env*" -exec ls -la {} \; | grep -v "^-rw-------\|^-r--------"
```

---

## Quick Reference

### Generate New Secrets
```bash
./scripts/generate-secrets.sh -o .env.production
chmod 600 .env.production
```

### Rotate Application Secret
```bash
# Generate and update
NEW_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
sed -i "s/^APP_SECRET_KEY=.*/APP_SECRET_KEY=${NEW_KEY}/" .env.production

# Restart application
docker-compose restart backend
```

### Check Secret Strength
```bash
# Verify secret length
echo -n "your-secret" | wc -c

# Entropy check (should be > 3.0)
python3 -c "
import math
s = 'your-secret'
entropy = -sum(s.count(c)/len(s) * math.log2(s.count(c)/len(s)) for c in set(s))
print(f'Entropy: {entropy:.2f} bits per character')
"
```

---

## Support

For questions about secrets management:
- Review this documentation
- Check the `scripts/generate-secrets.sh` script
- Consult your organization's security team
- Open an issue on GitHub for general questions

**Security incidents should be reported immediately to your security team.**