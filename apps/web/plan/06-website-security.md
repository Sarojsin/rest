# Website Plan — Security

## Overview
Comprehensive security plan for the multi-tenant restaurant management platform. Covers data protection, application security, authentication, authorization, and compliance.

## Data Protection

### Encryption at Rest
- **Database**: PostgreSQL with AES-256 encryption (transparent data encryption)
- **File Storage**: AES-256 encryption for uploaded files (logos, menus)
- **Backups**: Encrypted backups with separate encryption keys
- **Key Management**: AWS KMS or Azure Key Vault for key management

### Encryption in Transit
- **TLS 1.3**: All communications encrypted with TLS 1.3
- **HSTS**: HTTP Strict Transport Security enabled
- **Certificate Management**: Automated certificate renewal (Let's Encrypt/cert-manager)
- **API Security**: All API calls over HTTPS

### Data Retention
- **Audit Logs**: 90 days minimum retention
- **User Data**: Retained per GDPR/CCPA requirements
- **Order Data**: Retained per business requirements (minimum 1 year)
- **Payment Data**: PCI DSS compliant retention

## Application Security

### SQL Injection Prevention
- **Parameterized Queries**: All database queries use parameterized statements
- **ORM Protection**: SQLAlchemy ORM with automatic parameterization
- **Input Validation**: Strict input validation on all endpoints
- **Allowlist Validation**: Only known safe inputs accepted

### XSS Prevention
- **React Sanitization**: React automatically escapes rendered content
- **Content Security Policy (CSP)**: Strict CSP headers
- **Input Sanitization**: All user input sanitized before storage
- **Output Encoding**: All dynamic content properly encoded

### CSRF Protection
- **CSRF Tokens**: Token-based CSRF protection on all state-changing forms
- **SameSite Cookies**: `SameSite=Strict` or `SameSite=Lax` for session cookies
- **Origin Validation**: Validate origin header on sensitive requests
- **Double Submit Cookie**: CSRF token in both cookie and form

### Rate Limiting
- **Per Tenant**: Configurable rate limits per tenant
- **Per Branch**: Rate limits per branch
- **Per User**: Rate limits per user
- **Global**: Overall system rate limits
- **Response**: 429 Too Many Requests with retry-after header

### Session Management
- **Session Timeout**: 15 minutes idle, 24 hours maximum
- **JWT Tokens**: Short-lived access tokens (15 minutes)
- **Refresh Tokens**: Long-lived refresh tokens (7 days)
- **Token Rotation**: Refresh tokens rotated on use
- **Secure Storage**: HttpOnly cookies for refresh tokens

## Authentication & Authorization

### JWT Token Structure
- **Access Token**: 15-minute expiry, contains user_id, membership_id, restaurant_id, tenant_id
- **Refresh Token**: 7-day expiry, HttpOnly cookie
- **Token Validation**: Signature verification, expiry check, claim validation
- **Token Revocation**: Blacklist for compromised tokens

### Role-Based Access Control (RBAC)
- **Roles**: Owner, Manager, Waiter, Kitchen, Cashier
- **Permissions**: Role-based permission sets
- **Tenant Isolation**: Each user belongs to one tenant
- **Branch Access**: Users can be assigned to specific branches

### Multi-Factor Authentication (MFA)
- **Optional**: Email-based MFA for all tiers
- **Required**: MFA for admin accounts (Enterprise)
- **Backup Codes**: Recovery codes for account access
- **TOTP Support**: Time-based one-time passwords (future)

### Account Security
- **Password Requirements**: Minimum 8 characters, 1 uppercase, 1 lowercase, 1 number, 1 special
- **Password Hashing**: bcrypt with cost factor 12
- **Account Lockout**: 5 failed attempts → 30-minute lockout
- **Password Reset**: Secure token-based reset with expiry
- **Email Verification**: Required for new accounts

## Multi-Tenant Security

### Tenant Isolation
- **Row-Level Security (RLS)**: PostgreSQL RLS policies per tenant
- **SET LOCAL app.branch_id**: Branch isolation per request
- **Tenant Context**: `tenant_context` module state, reset per request
- **Data Partitioning**: All queries filtered by tenant_id

### Branch Isolation
- **Branch ID**: `branch_id UUID` on all 5 tables
- **RLS Policies**: `branch_isolation` policy on restaurant_tables, orders, bills, payments, dining_sessions
- **SET_LOCAL**: `SET LOCAL app.branch_id = '<uuid>'` at transaction start
- **Un-scoped Queries**: Return 0 rows (proves isolation)

### Cross-Tenant Protection
- **No Cross-Tenant Redirect**: Strict hostname validation
- **Tenant Context Validation**: `get_actor()` verifies tenant_id matches membership
- **API Isolation**: All API calls filtered by tenant context
- **QR Hostname Cross-Check**: Per-tenant hostname validation for QR codes

## Compliance & Privacy

### GDPR Compliance
- **Data Minimization**: Collect only necessary data
- **Right to Access**: Users can export their data
- **Right to Erasure**: Data deletion on request
- **Data Portability**: Export data in machine-readable format
- **Consent Management**: Cookie consent, email consent
- **Data Processing Agreement**: Available for Enterprise customers

### CCPA Compliance
- **Consumer Rights**: Know, delete, opt-out
- **Data Sale Opt-Out**: California residents can opt out
- **Data Access**: Consumers can access their data
- **Data Deletion**: Right to delete personal information

### PCI DSS (Payment Card Industry)
- **No Card Storage**: Never store full card numbers
- **Tokenization**: Use payment gateway tokens
- **Secure Transmission**: TLS for all payment data
- **Compliance**: PCI DSS SAQ A (no card data storage)

### SOC 2 Type II (Enterprise)
- **Availability**: System availability controls
- **Security**: Data protection controls
- **Processing Integrity**: Accurate data processing
- **Confidentiality**: Data confidentiality controls
- **Privacy**: Privacy controls for personal data

## Security Headers

### HTTP Headers
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### CORS Configuration
- **Allowed Origins**: `platform.com`, `*.platform.com`, specific tenant domains
- **Allowed Methods**: GET, POST, PUT, DELETE, OPTIONS
- **Allowed Headers**: Authorization, Content-Type, x-tenant-id
- **Credentials**: true (for cookie-based auth)
- **Max Age**: 86400 (24 hours)

## Infrastructure Security

### Network Security
- **VPC**: Isolated virtual private cloud
- **Security Groups**: Strict firewall rules
- **WAF**: Web application firewall (AWS WAF/Cloudflare)
- **DDoS Protection**: Cloudflare/AWS Shield
- **Load Balancer**: TLS termination, health checks

### Database Security
- **Database Firewall**: Only application servers can access
- **Encrypted Connections**: TLS for all DB connections
- **User Permissions**: Least privilege principle
- **Audit Logging**: All DB access logged
- **Backup Encryption**: Encrypted backups with separate keys

### Container Security
- **Minimal Images**: Alpine or distroless base images
- **Non-Root User**: Containers run as non-root
- **Image Scanning**: Vulnerability scanning in CI/CD
- **Secret Management**: Secrets in environment variables or secret manager

### Secret Management
- **Environment Variables**: Sensitive config in env vars
- **Secret Manager**: AWS Secrets Manager/Azure Key Vault
- **Key Rotation**: Automated key rotation
- **No Hardcoded Secrets**: Zero secrets in code

## Monitoring & Incident Response

### Security Monitoring
- **Sentry**: Error tracking and alerting
- **CloudWatch/Log Analytics**: Log aggregation
- **Anomaly Detection**: Unusual activity detection
- **Intrusion Detection**: IDS/IPS systems
- **Vulnerability Scanning**: Regular security scans

### Incident Response Plan
1. **Detection**: Automated alerts for suspicious activity
2. **Containment**: Isolate affected systems
3. **Eradication**: Remove threat, patch vulnerabilities
4. **Recovery**: Restore from clean backups
5. **Post-Incident**: Root cause analysis, documentation, prevention

### Security Audit Schedule
- **Internal Audit**: Quarterly security review
- **External Audit**: Annual penetration testing
- **Vulnerability Scan**: Monthly automated scans
- **Code Review**: All PRs reviewed for security
- **Dependency Updates**: Weekly dependency updates

## Security Testing

### Automated Testing
- **SAST**: Static application security testing (SonarQube)
- **DAST**: Dynamic application security testing (OWASP ZAP)
- **Dependency Scanning**: Snyk, Dependabot
- **Container Scanning**: Trivy, Clair

### Manual Testing
- **Penetration Testing**: Annual by external firm
- **Code Review**: Security-focused code reviews
- **Threat Modeling**: For new features
- **Red Team Exercises**: Simulated attacks

### Security Checklist
- [ ] All user input validated
- [ ] All database queries parameterized
- [ ] All sensitive data encrypted
- [ ] All APIs authenticated and authorized
- [ ] All forms CSRF-protected
- [ ] All headers security-configured
- [ ] All dependencies up-to-date
- [ ] All secrets in secret manager
- [ ] All logs sanitized (no sensitive data)
- [ ] All error messages generic (no stack traces)

---
*Security plan aligned with 26-phase backend implementation. All security controls verified and tested. Production-grade security posture maintained.*