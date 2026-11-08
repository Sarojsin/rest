import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "letsoit69960@gmail.com"
SMTP_PASSWORD = "hpzrghzjehqwazsj"  # No spaces - Gmail app password format
SMTP_FROM = "letsoit69960@gmail.com"
TO_EMAIL = "sagardhami84@gmail.com"

print("=== Testing SMTP Email Delivery (No spaces in password) ===")
print(f"SMTP Host: {SMTP_HOST}:{SMTP_PORT}")
print(f"SMTP User: {SMTP_USER}")
print(f"SMTP Password: {SMTP_PASSWORD}")
print(f"To: {TO_EMAIL}")
print()

try:
    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = TO_EMAIL
    msg["Subject"] = "Test: Restaurant Platform Invitation Email"
    msg.set_content("""Hello,

This is a test invitation email from the Restaurant Management Platform.

Restaurant: Test Restaurant
Account: sagardhami84@gmail.com
Role: Owner

Click the secure link below to verify your email and create your password:
http://192.168.1.5:5173/auth/invitations/TEST_TOKEN_12345

This link expires after 72 hours.

If you did not sign up for this, you can ignore this email.
""")

    print(f"Connecting to {SMTP_HOST}:{SMTP_PORT}...")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
        print("Connected to SMTP server.")
        smtp.starttls()
        print("STARTTLS enabled.")
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        print("Logged in successfully.")
        smtp.send_message(msg)
        print(f"Email sent successfully to {TO_EMAIL}!")

except smtplib.SMTPAuthenticationError as e:
    print(f"SMTP Authentication Error: {e}")
except smtplib.SMTPConnectError as e:
    print(f"SMTP Connection Error: {e}")
except smtplib.SMTPException as e:
    print(f"SMTP Error: {e}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")