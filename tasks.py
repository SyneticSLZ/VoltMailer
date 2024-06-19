from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_session import Session
import json
import pandas as pd
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from email.mime.text import MIMEText
import base64
import os
import requests
from celery_config import celery_init_app
from bs4 import BeautifulSoup
import openai
import json
from openai import OpenAI
import asyncio
import time
import pickle
from dotenv import load_dotenv
from celery import Celery
from celery import shared_task

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']
openai_api_key = os.getenv('OPENAI_API_KEY')
openai.api_key = openai_api_key
AIclient = OpenAI(api_key=openai_api_key)
ASSISTANT_ID = "asst_shvdCBA7snGDSENhmE5iugIm"

@shared_task
def send_email(credentials_dict, subject, message_text, to):
    credentials = Credentials(**credentials_dict)
    service = build('gmail', 'v1', credentials=credentials)

    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = 'me'
    message['subject'] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    message = {
        'raw': raw
    }
    try:
        message = (service.users().messages().send(userId="me", body=message).execute())
        print(f"Message Id: {message['id']}")
        return message
    except Exception as error:
        print(f"An error occurred: {error}")
        return None

@shared_task
def send_emails(credentials_dict, submitted_data, user_pitch, Uname):
    SENT_EMAILS = 0
    threadID = create_thread()
    for index, data in enumerate(submitted_data):
        try:
            print(f'Starting send to {data["email"]}')

            # Get the website content
            description_response = requests.post(
                'http://127.0.0.1:5000/get-site-description-auto',
                json={'url': data['website']}
            )
            description_data = description_response.json()
            website_content = description_data['description']

            To = data['name']

            print(f'Email: {data["email"]}, Website Content: {website_content}, Uname: {Uname}, To: {To}')

            # Personalize message
            email_content_response = requests.post(
                'http://127.0.0.1:5000/add-messages-to-thread-auto',
                json={
                    'thread_id': threadID,
                    'website_content': website_content,
                    'user_pitch': user_pitch,
                    'To': To,
                    'Me': Uname
                }
            )
            email_content_data = email_content_response.json()
            email_content = email_content_data['email_content']
            lines = email_content.split('\n')
            subject_line = lines[0].replace('Subject: ', '')
            main_message = '\n'.join(lines[1:]).strip()

            print(f'Email: {data["email"]}, Subject: {subject_line}, Message: {main_message}')

            # Send the email using Gmail API
            result = send_email(credentials_dict, subject_line, main_message, data['email'])
            print(f'Message to {data["email"]} successfully sent: {result}')
            SENT_EMAILS += 1
        except Exception as e:
            print(f'Error processing email for {data["email"]}: {e}')
            # Handle the exception (log it, update status, etc.)

    return {'status': 'completed', 'sent_emails': SENT_EMAILS}

@shared_task
def create_thread():
    # Your AIclient logic to create a thread
    thread = AIclient.beta.threads.create()
    print(thread.id)
    return thread.id

@shared_task
async def add_messages_to_thread(ThreadId, website_content, user_pitch, To, Me):
    # Create a message in the thread
    message = AIclient.beta.threads.messages.create(
        thread_id=ThreadId,
        role="user",
        content=f"I'm selling '{user_pitch}', This is the data I have on the company and what they do from their website '{website_content}'.And this is the users pitch: '{user_pitch}' This is the name you should use to address them in the email '{To}' from me, '{Me}' i want you to create the email where the first line is the subject line and then the greeting and content follows."
    )
    print("Message created")

    # Run the assistant to generate a response
    run = AIclient.beta.threads.runs.create(
        thread_id=ThreadId,
        assistant_id=ASSISTANT_ID
    )
    print("Run created")

    timeElapsed = 0
    timeout = 60
    interval = 5
    while timeElapsed < timeout:
        run_res = AIclient.beta.threads.runs.retrieve(
            thread_id=ThreadId,
            run_id=run.id
        )

        if run_res.status == 'completed':
            messages = AIclient.beta.threads.messages.list(
                thread_id=ThreadId
            )
            print("Messages listed")
            return messages.data[0].content[0].text.value

        time.sleep(interval)  # Wait for the specified interval
        timeElapsed += interval

    if timeElapsed >= timeout:
        print("Timeout reached without completion")
        return "not able to fetch response from assistant"

@shared_task
def get_site_description(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        meta_description = soup.find('meta', attrs={'name': 'description'})
        if meta_description and 'content' in meta_description.attrs:
            return meta_description['content']
        main_content = soup.find('main') or soup.find(id='content') or soup.body
        if main_content:
            headers = main_content.find_all(['h1', 'h2'], limit=1)
            if headers:
                return headers[0].get_text(strip=True)
            first_para = main_content.find('p')
            if first_para:
                return first_para.get_text(strip=True)
        return "No description or primary content found."
    except requests.RequestException as e:
        return f"Failed to retrieve or parse website due to: {e}"
    
@shared_task
def get_site_description_api(url):
    description = get_site_description(url)
    return description
