import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# We only need permission to SEND emails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def authenticate_gmail():
    creds = None
    # Check if we already have a token
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no valid credentials, log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            # This will pop open a browser window on your Ubuntu machine
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run so the server doesn't ask again
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    print("✅ Gmail Authentication Successful! token.json generated.")

if __name__ == '__main__':
    authenticate_gmail()
