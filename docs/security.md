# Security

The API uses Argon2id passwords, cryptographically random opaque session cookies, hashed server-side tokens, rolling refresh, and expiration. Cookies are HTTP-only and SameSite=Lax. Set secure cookies when using HTTPS. State-changing browser requests enforce the configured application origin. Password-reset and verification links use single-use tokens when SMTP is configured.

Organization-scoped resource access and administrator checks guard settings. Atomic quotas are shared through PostgreSQL. Use per-client limits at the ingress for shared deployments behind the same proxy. Admin uploads are bounded and validated before database writes. Custom provider origins require server approval, redirects are disabled, and cloud DNS is resolved and checked before the connection is pinned. Secrets are omitted from client API results. Do not commit `.env`.

Use `scripts/create-admin.py` to provision a platform administrator into a migrated database. For shared or production deployment, follow [deployment](deployment.md) and disable open registration and demo access unless intended.

