import smtplib
from email.mime.text import MIMEText
import os

# Load SMTP details from environment variables or hardcode for testing
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtps.aruba.it')
SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', 'support@adeste.com')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', 'G+*4EjMg3GUJv$V')  # Set your password here for testing
FROM_EMAIL = os.getenv('FROM_EMAIL', 'support@adeste.com')
SMTP_USE_SSL = os.getenv('SMTP_USE_SSL', 'True').lower() in ['true', '1', 'yes']

TO_EMAIL = os.getenv('TO_EMAIL', 'rdhar8502@gmail.com')  # Send to self for test

# Compose a simple test email
msg = MIMEText('This is a test email from SMTP test script.')
msg['Subject'] = 'SMTP Test Email'
msg['From'] = FROM_EMAIL
msg['To'] = TO_EMAIL

try:
    if SMTP_USE_SSL:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
    else:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    server.sendmail(FROM_EMAIL, [TO_EMAIL], msg.as_string())
    print('Test email sent successfully!')
    server.quit()
except Exception as e:
    print(f'Failed to send email: {e}')
