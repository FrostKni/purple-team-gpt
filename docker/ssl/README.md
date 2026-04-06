# SSL/TLS Certificates Directory

This directory contains SSL/TLS certificates for HTTPS.

## Development (Self-Signed)

Generate self-signed certificates for local development:

```bash
./scripts/setup-ssl.sh
```

## Production (Let's Encrypt)

Generate certificates using Let's Encrypt:

```bash
./scripts/setup-letsencrypt.sh -d your-domain.com -e admin@your-domain.com
```

## Files

- `fullchain.pem` - Full certificate chain
- `privkey.pem` - Private key
- `dhparam.pem` - Diffie-Hellman parameters (optional, for PFS)

## Security

- Never commit private keys to version control
- Keep private key permissions at 600
- Rotate certificates before expiration
- Use Let's Encrypt auto-renewal in production