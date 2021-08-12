from Google import Create_Service
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


CLIENT_SECRET_FILE = 'client_secret_755007453906-0clc8nlprjohas353ggcm86qmvpcuucr.apps.googleusercontent.com (1).json'
API_NAME = 'gmail'
API_VERSION = 'v1'
SCOPES = ['https://mail.google.com/']
service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)

SUBJECT_TEXT = "A Message from the Blog Capstone Project "