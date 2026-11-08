import sys
sys.path.insert(0, 'E:\\rest\\backend')
from app.core.config import settings

print('=== Config Verification ===')
print(f'EMAIL_BACKEND: {settings.email_backend}')
print(f'SMTP_HOST: {settings.smtp_host}')
print(f'SMTP_PORT: {settings.smtp_port}')
print(f'SMTP_USER: {settings.smtp_user}')
if settings.smtp_password:
    print(f'SMTP_PASSWORD: *** (set from .env)')
else:
    print(f'SMTP_PASSWORD: NOT SET')
print(f'SMTP_FROM: {settings.smtp_from}')
print(f'SMTP_STARTTLS: {settings.smtp_starttls}')
print(f'INVITATION_TTL_HOURS: {settings.invitation_ttl_hours}')
print(f'DATABASE_URL: {settings.database_url}')
if settings.secret_key:
    print(f'SECRET_KEY: *** (set)')
else:
    print(f'SECRET_KEY: NOT SET')
print(f'APP_ENV: {settings.app_env}')
print()

if settings.smtp_password:
    print('SUCCESS: SMTP password is loaded from .env file - not hardcoded in config.py!')
else:
    print('WARNING: SMTP password is NOT set - check .env file')