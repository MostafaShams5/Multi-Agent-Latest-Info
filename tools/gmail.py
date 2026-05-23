import os
import base64
import asyncio
from email.message import EmailMessage
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from infrastructure.logger import logger

async def send_gmail_report(to_email: str, subject: str, content: str):
    if not os.path.exists('token.json'):
        logger.error("Gmail Token missing. Run gmail_auth.py first.")
        return

    try:
        creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/gmail.send'])
        service = build('gmail', 'v1', credentials=creds)
        
        message = EmailMessage()
        message.set_content(content)
        message['To'] = to_email
        message['From'] = "me"
        message['Subject'] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        # OFF-THREAD EXECUTION: Prevents the API call from freezing your FastApi server!
        await asyncio.to_thread(
            service.users().messages().send(userId="me", body=create_message).execute
        )
        logger.info(f"📧 [Gmail] Report successfully sent to {to_email}")
        
    except Exception as e:
        logger.error(f"❌ [Gmail] Failed to send email to {to_email}: {e}")
