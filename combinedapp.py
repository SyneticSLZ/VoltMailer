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
from bs4 import BeautifulSoup
import openai
import json
from openai import OpenAI
import asyncio
import time
import stripe
import pickle
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# from Google import Create_Service
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
app = Flask(__name__)
SESSION_FILE_DIR = '/tmp/flask_session/'
if not os.path.exists(SESSION_FILE_DIR):
    os.makedirs(SESSION_FILE_DIR)
    os.chmod(SESSION_FILE_DIR, 0o700)


# SCOPES = ['https://www.googleapis.com/auth/gmail.send']
SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']



openai_api_key = os.getenv('OPENAI_API_KEY')
openai.api_key = openai_api_key
AIclient = OpenAI(api_key=openai_api_key)


ASSISTANT_ID = "asst_shvdCBA7snGDSENhmE5iugIm"
REDIRECT_URI = 'http://localhost:5000/oauth2callback'
COST_FILE = 'costs.json'
TRANSACTIONS_FILE = 'transactions.json'
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'  # You can also use 'redis', 'memcached', etc.
# app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem to store sessions
app.config['SESSION_FILE_DIR'] = '/tmp/flask_session/'  # Ensure this directory exists and is writable
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

Session(app)

CLIENT_SECRETS_FILE = "client_secret.json"
API_NAME = 'gmail'
API_VERSION = 'v1'
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


stripe.api_key = os.getenv('STRIPE_API_KEY')
stripe.billing_portal.Configuration.create(
  business_profile={
    "headline": "Your VoltMailer billing Info",
  },
  features={"invoice_history": {"enabled": True}},
)

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
uri = os.getenv('MONGO_URI')

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
db = client.Volt_Production
customers_collection = db.Customers
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

@app.route('/login-customer', methods=['POST'])
def login_customer():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    result = loginToDatabase(email, password)
    if result == True:
        customer = find_customer(email)
        if customer:
            return redirect(url_for('Db', email=customer['email'], stripeID=customer['stripeID'], total_emails=customer['total_emails'], plan=customer['plan'], priceID=customer['priceID'], name=customer['name'], plan_emails=customer['plan_emails'], password=customer['password']))
            # return redirect(url_for('Dashboard', email=customer['email'], stripeID=customer['stripeID'], total_emails=customer['total_emails'], plan=customer['plan'], priceID=customer['priceID'], name=customer['name'], plan_emails=customer['plan_emails'], password=customer['password']))
        else:
            return render_template('pricing.html', email=email, password=password)
    else:
        return jsonify({"error": result})

def loginToDatabase(email, password):
    customer = find_customer(email)
    if customer:
        if (customer['password']):
            if password == customer['password']:
                return True
            else:
                return 'Wrong Password'
        else:
            return 'please sign in with google'
        
    else: return 'Account Not found'
    
@app.route('/generate_service', methods=['POST'])
def generate_service():
    return Create_Service("client_secret.json", 'gmail', 'v1', ['https://www.googleapis.com/auth/gmail.send'])

def get_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    return service
@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=['https://www.googleapis.com/auth/gmail.send'],
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)

    cred = flow.credentials
    with open(f'token_gmail_v1.pickle', 'wb') as token:
        pickle.dump(cred, token)

    return redirect(url_for('show_form'))

@app.route('/Db', methods=['GET'])
def show_form():
    email = request.args.get('email')
    stripeID = request.args.get('stripeID')
    total_emails = request.args.get('total_emails')
    plan = request.args.get('plan')
    priceID = request.args.get('priceID')
    name = request.args.get('name')
    plan_emails = request.args.get('plan_emails')
    password = request.args.get('password')

    session['email'] = email
    session['stripeID'] = stripeID
    session['total_emails'] = total_emails
    session['plan'] = plan
    session['priceID'] = priceID
    session['name'] = name
    session['plan_emails'] = plan_emails
    session['password'] = password

    return render_template('db.html', email=email, name=name, plan=plan, total_emails=total_emails, plan_emails=plan_emails)

# def Create_Service(client_secret_file, api_name, api_version, *scopes):
#     CLIENT_SECRET_FILE = client_secret_file
#     API_SERVICE_NAME = api_name
#     API_VERSION = api_version
#     SCOPES = [scope for scope in scopes[0]]

#     cred = None
#     pickle_file = f'token_{API_SERVICE_NAME}_{API_VERSION}.pickle'

#     if os.path.exists(pickle_file):
#         with open(pickle_file, 'rb') as token:
#             cred = pickle.load(token)

#     if not cred or not cred.valid:
#         if cred and cred.expired and cred.refresh_token:
#             cred.refresh(Request())
#         else:
#             flow = Flow.from_client_secrets_file(
#                 CLIENT_SECRET_FILE,
#                 scopes=SCOPES,
#                 redirect_uri=url_for('oauth2callback', _external=True)
#             )
#             authorization_url, state = flow.authorization_url(
#                 access_type='offline',
#                 include_granted_scopes='true'
#             )
#             session['state'] = state
#             return redirect(authorization_url)

#         with open(pickle_file, 'wb') as token:
#             pickle.dump(cred, token)

#     try:
#         service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
#         print(API_SERVICE_NAME, 'service created successfully')
#         return service
#     except Exception as e:
#         print('Unable to connect.')
#         print(e)
#         return None

@app.route('/signup-customer', methods=['POST'])
def signup_customer():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    customer = find_customer(email)
    if customer:
        if (customer['password']):
                return jsonify({"success": False, "error": "User already has an account."})
        else:
           return jsonify({"success": False, "error": "This email is linked to a Google account."})
        
    else: return jsonify({"success": True, "email": email, "password": password})  

@app.route('/add_customer', methods=['POST'])
def add_customer():
    data = request.json
    customer = {
        "stripeID": data.get('stripeID'),
        "email": data.get('email'),
        "plan": data.get('plan'),
        "total_emails": data.get('total_emails'),
        "priceID": data.get('priceID')
    }
    customers_collection.insert_one(customer)
    return jsonify({"message": "Customer added successfully"}), 201


@app.route('/add_and_redirect', methods=['POST'])
def add_and_redirect():
    data = request.json
    customer = {
        "stripeID": data.get('stripeID'),
        "email": data.get('email'),
        "password": data.get('password'),
        "name": data.get('name'),
        "plan": data.get('plan'),
        "plan_emails": data.get('total_emails'),
        "total_emails": data.get('total_emails'),
        "priceID": data.get('priceID')
    }
    result = customers_collection.insert_one(customer)
    # added_customer = {    "stripeID": result.stripeID,
    #         "email": result.email,
    #         "plan": result.plan,
    #         "total_emails": result.total_emails,
    #         "priceID": result.priceID}
    # customer_id = str(result.inserted_id)
    
    # Redirect to the gpy route with the necessary parameters
    return jsonify({
        "message": "Customer added successfully",
        "redirect_url": f"/Db?service={data.get('service')}&customer_id={data.get('stripeID')}&name={data.get('name')}&plan={data.get('plan')}&total_emails={data.get('total_emails')}&email={data.get('email')}&password={data.get('password')}"
    }), 201

@app.route('/Db', methods=['GET'])
def Db():
    email = request.args.get('email')
    service = request.args.get('service')
    password = request.args.get('password')
    # return render_template('db.html', service=service, customer_id=customer_id, product_id=product_id, total_emails=total_emails, email=email, plan=plan, name=name)
    customer = find_customer(email)
    return Dashboard(customer['email'], customer['stripeID'], customer['total_emails'], customer['plan'], customer['priceID'], service, customer['name'], customer['plan_emails'], customer['password'])

# @app.route('/get_customer/<email>', methods=['GET'])
# def get_customer(email):
#     customer = customers_collection.find_one({"email": email})
#     if customer:
#         return jsonify({
#             "stripeID": customer.get('stripeID'),
#             "email": customer.get('email'),
#             "plan": customer.get('plan'),
#             "total_emails": customer.get('total_emails'),
#             "priceID": customer.get('priceID')
#         })
#     return jsonify({"message": "Customer not found"}), 404

# def check_user_subscription(email):
#     # Implement your logic to check if the user has a subscription
#     # Return True if subscribed, False otherwise
#     return False


@app.route('/update_customer_plan', methods=['POST'])
def update_customer_plan():
    data = request.json
    email = data.get('email')
    new_plan = data.get('new_plan')
    result = customers_collection.update_one(
        {"email": email},
        {"$set": {"plan": new_plan}}
    )
    if result.matched_count:
        return jsonify({"message": "Customer plan updated successfully"})
    return jsonify({"message": "Customer not found"}), 404

@app.route('/remaining_emails/<email>', methods=['GET'])
def remaining_emails(email):
    customer = customers_collection.find_one({"email": email})
    if customer:
        return jsonify({"email": email, "remaining_emails": customer.get('total_emails')})
    return jsonify({"message": "Customer not found"}), 404


# @app.route('/use_email', methods=['POST'])
# def use_email():
#     data = request.json
#     email = data.get('email')
#     customer = customers_collection.find_one({"email": email})
#     if customer and customer['total_emails'] > 0:
#         new_total_emails = customer['total_emails'] - 1
#         customers_collection.update_one(
#             {"email": email},
#             {"$set": {"total_emails": new_total_emails}}
#         )
#         return jsonify({"message": f"Email used! {new_total_emails} emails left."})
#     return jsonify({"message": "No emails left or customer not found"}), 400

@app.route('/use_email', methods=['POST'])
def use_email():
    data = request.json
    email = data.get('email')
    emails_to_use = data.get('emails_to_use', 1)  # Default to 1 if not provided
    customer = customers_collection.find_one({"email": email})
    if customer and customer['total_emails'] >= emails_to_use:
        new_total_emails = customer['total_emails'] - emails_to_use
        customers_collection.update_one(
            {"email": email},
            {"$set": {"total_emails": new_total_emails}}
        )
        return jsonify({"message": f"Emails used! {new_total_emails} emails left."})
    return jsonify({"message": "Not enough emails left or customer not found"}), 400



# @app.route('/create-checkout-session', methods=['POST'])
# def create_checkout_session():
#     # data = request.json
#     # try:
#      stripe.checkout.Session.create(
#   mode="subscription",
#   line_items=[{"price": 'price_1PJsseKJeZAyw8f4UVbMQfRa', "quantity": 1}],
#   ui_mode="embedded",
#   return_url="http://localhost:5000/templates/gpy?session_id={CHECKOUT_SESSION_ID}",
# )
#     return jsonify({'clientSecret': session.client_secret})
#     `except Exception as e:
#         return jsonify(error=str(e)), 403

# @app.route('/create-checkout-session', methods=['POST'])
# def create_checkout_session():
#     # data = request.get_json()
#     try:
#         session = stripe.checkout.Session.create(
#             mode='subscription',
#             line_items=[{"price": 'price_1PJsseKJeZAyw8f4UVbMQfRa', "quantity": 1}],
#             ui_mode='embedded',
#             return_url='http://localhost:5000/templates/success.html?session_id={CHECKOUT_SESSION_ID}', 
#         )
#         return jsonify({'clientSecret': session.client_secret})
#     except Exception as e:
#         return jsonify(error=str(e)), 403
# @app.route('/free-trial', methods=['POST'])
# def freeTrial():
#     data = request.get_json()
#     customer_email = data.get('email')  # Get the customer email from the request body
#     print(data)
#     customer = stripe.Customer.create( email=customer_email)
    
#     subscription = stripe.Subscription.create(
#     customer=customer.id,
#     items=[{"price": "prod_QB14JP8pGUK7pe"}],
#     )
#     if subscription:
#         return render_template('gpy.html', customer_id=customer.id, subscriptionid=subscription.id, productid='prod_QB14JP8pGUK7pe', totalemails=20 )

# @app.route('/free-trial', methods=['POST'])
# def free_trial():
#     data = request.get_json()
#     customer_email = data.get('email')  # Get the customer email from the request body
#     print(data)
#     try:
#         customer = stripe.Customer.create(email=customer_email)
#         subscription = stripe.Subscription.create(
#             customer=customer.id,
#             items=[{"price": "price_1PKf2PKJeZAyw8f418JphiK0"}],
#         )
#         if subscription:

#             return jsonify({
#                 'customer_id': customer.id,
#                 'subscription_id': subscription.id,
#                 'product_id': 'price_1PKf2PKJeZAyw8f418JphiK0',
#                 'total_emails': 20,
#                 'email': customer_email
#             })
#     except Exception as e:
#         return jsonify(error=str(e)), 400

@app.route('/free-trial', methods=['POST'])
def free_trial():
    data = request.get_json()
    customer_email = data.get('email')  # Get the customer email from the request body
    name = data.get('name')
    print(data)
    try:
        customer = stripe.Customer.create(email=customer_email)
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": "price_1PKf2PKJeZAyw8f418JphiK0"}],
        )
        if subscription:
            customer_data = {
                'stripeID': customer.id,
                'email': customer_email,
                'name': name,
                'plan': 'free-trial',
                'total_emails': 20,
                'priceID': 'price_1PKf2PKJeZAyw8f418JphiK0'
            }
            add_customer_to_db(customer_data)
            return jsonify({
                'customer_id': customer.id,
                'subscription_id': subscription.id,
                'name': name,
                'product_id': 'price_1PKf2PKJeZAyw8f418JphiK0',
                'total_emails': 20,
                'email': customer_email
            })
    except Exception as e:
        return jsonify(error=str(e)), 400

def add_customer_to_db(data):
    customer = {
        "stripeID": data.get('stripeID'),
        "email": data.get('email'),
        "plan": data.get('plan'),
        "total_emails": data.get('total_emails'),
        "priceID": data.get('priceID')
    }
    customers_collection.insert_one(customer)



@app.route('/session-status', methods=['GET'])
def session_status():
    session_id = request.args.get('session_id')
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return jsonify({
                'status': session.status,
                'customer_id': session.customer if session.customer else "N/A",
                'customer_email': session.customer_details.email if session.customer_details else "N/A"
            })
        except Exception as e:
            return jsonify(error=str(e)), 400
    else:
        return jsonify(error="No session ID provided"), 400
    

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    data = request.get_json()
    service = data.get('service')
    customer_email = data.get('email')  # Get the customer email from the request body
    password = data.get('password')
    print(data)
    try:
        session = stripe.checkout.Session.create(
            mode='subscription',
            line_items=[{"price": 'price_1PJsseKJeZAyw8f4UVbMQfRa', "quantity": 1}],
            customer_email=customer_email,
            ui_mode='embedded',
            return_url=url_for('payment_status', _external=True, _scheme='http') + f'?session_id={{CHECKOUT_SESSION_ID}}&email={customer_email}&service={service}&password={password}'
        )
        return jsonify({'clientSecret': session.client_secret})
    except Exception as e:
        return jsonify(error=str(e)), 403

@app.route('/payment-status', methods=['GET'])
def payment_status():
    session_id = request.args.get('session_id')
    email = request.args.get('email')
    password = request.args.get('password')
    if session_id:
        return render_template('payment_status.html', session_id=session_id, email=email, password=password)
    
    else:
        return "No session ID provided", 400

# @app.route('/free-trial-pm', methods=['POST'])
# def free_trialpm():
#     data = request.json
#     email = data.get('email')  # Use the provided email or a default value
#     return render_template('payment_status.html', trial=True, email=email)
    

# @app.route('/gpy', methods=['GET'])
# def gpy():
#     customer_id = request.args.get('customer_id')
#     # subscription_id = request.args.get('subscription_id')
#     email = request.args.get('email')
#     product_id = request.args.get('product_id')
#     total_emails = request.args.get('total_emails')
#     return render_template('gpy.html', customer_id=customer_id, product_id=product_id, total_emails=total_emails, email=email)
    

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/cancel')
def cancel():
    return 'Payment canceled.'

@app.route('/create-thread', methods=['POST'])
def CreateThread():
    thread = AIclient.beta.threads.create()
    print(thread.id)
    return jsonify({'thread_id': thread.id})
    # return thread.id

# def CreateThread():
#     thread = client.beta.threads.create()
#     print(thread)
#     return thread

@app.route('/add-messages-to-thread', methods=['POST'])
def add_messages_to_thread_api():
    data = request.json
    thread_id = data['thread_id']
    website_content = data['website_content']
    user_pitch = data['user_pitch']
    To = data['To']
    Me = data['Me']
    email_content = asyncio.run(AddMessagesToThread(thread_id, website_content, user_pitch, To, Me))
    return jsonify({'email_content': email_content})

async def AddMessagesToThread(ThreadId, website_content, user_pitch, To, Me):
    # Create a message in the thread
    message = AIclient.beta.threads.messages.create(
        thread_id=ThreadId,
        role="user",
        # content=f"Generate a custom pitch email for a company with this website content: '{website_content}' and this user pitch: '{user_pitch}' ti gurantee them a 10x ROI on all ad spend done for them. "
        content=f"I'm selling '{user_pitch}', This is the data I have on the company and what they do from their website '{website_content}'.And this is the users pitch: '{user_pitch}' This is the name you should use to adress them in the email '{To}' from me, '{Me}' i want you to create the email wher the first lin is the subject line and then the greeting and content follows."
    )
    print("Message created")

    # Run the assistant to generate a response
    run = AIclient.beta.threads.runs.create(
        thread_id=ThreadId,
        assistant_id=ASSISTANT_ID
    )
    print("Run created")

    # # Retrieve the run results ( while )
    # run_res = await client.beta.threads.runs.retrieve(
    #     thread_id=ThreadId.id,
    #     run_id=run.id
    # )
    # print("Run results retrieved")
    timeElapsed = 0
    timeout = 60
    interval = 5
    while (timeElapsed < timeout) :

        run_res = AIclient.beta.threads.runs.retrieve(
            thread_id=ThreadId,
            run_id=run.id
        )

        if (run_res.status == 'completed'):

            # List all messages in the thread
            messages = AIclient.beta.threads.messages.list(
                thread_id=ThreadId
            )
            print("Messages listed")

            # Print messages in reverse order
            # for message in reversed(messages.data):
            #     print(message.role + ": " + message.content[0].text.value)
            print(messages.data[0].content[0].text.value)
            return messages.data[0].content[0].text.value
            # break

        time.sleep(interval)  # Wait for the specified interval
        timeElapsed += interval

    if timeElapsed >= timeout:
        print("Timeout reached without completion")
        return "not able to fetch response from assistant"
    


    # # List all messages in the thread
    # messages = await client.beta.threads.messages.list(
    #     thread_id=ThreadId.id
    # )
    # print("Messages listed")

    # # Print messages in reverse order
    # for message in reversed(messages.data):
    #     print(message.role + ": " + message.content[0].text.value)



# # Load data from files
# def load_data():
#     try:
#         with open(COST_FILE, 'r') as file:
#             costs = json.load(file)
#     except (FileNotFoundError, json.JSONDecodeError):
#         costs = {"total": 0.0}

#     try:
#         with open(TRANSACTIONS_FILE, 'r') as file:
#             transactions = json.load(file)
#     except (FileNotFoundError, json.JSONDecodeError):
#         transactions = []

#     return costs, transactions

# costs, transactions = load_data()

# # Save costs to file
# def save_costs():
#     with open(COST_FILE, 'w') as file:
#         json.dump(costs, file)

# # Save transactions to file
# def save_transactions():
#     with open(TRANSACTIONS_FILE, 'w') as file:
#         json.dump(transactions, file)


@app.route('/connect_gmail')
def connect_gmail():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

# @app.route('/oauth2callback')
# def oauth2callback():
#     state = session['state']
#     flow = InstalledAppFlow.from_client_secrets_file(
#         'credentials.json', SCOPES, state=state)
#     flow.redirect_uri = url_for('oauth2callback', _external=True)
#     authorization_response = request.url
#     flow.fetch_token(authorization_response=authorization_response)

#     creds = flow.credentials
#     session['credentials'] = {
#         'token': creds.token,
#         'refresh_token': creds.refresh_token,
#         'token_uri': creds.token_uri,
#         'client_id': creds.client_id,
#         'client_secret': creds.client_secret,
#         'scopes': creds.scopes
#     }

#     service = build('gmail', 'v1', credentials=creds)
#     profile = service.users().getProfile(userId='me').execute()
#     user_email = profile['emailAddress']

#     user_id = creds.id_token['sub']
#     if user_id not in users:
#         users[user_id] = {'email': user_email}
#         return jsonify({'email': user_email, 'new_user': True})
#     else:
#         return jsonify({'email': user_email, 'new_user': False})

# @app.route('/select_plan')
# def select_plan():
#     return render_template('payment.html')

# @app.route('/payment', methods=['POST'])
# def payment():
#     plan = request.form['plan']
#     email = request.form['email']
#     customer = stripe.Customer.create(email=email)
#     subscription = stripe.Subscription.create(
#         customer=customer.id,
#         items=[{'plan': plan}]
#     )
#     user_id = session['credentials']['id_token']['sub']
#     users[user_id].update({
#         'subscription_id': subscription.id,
#         'credentials': session['credentials']
#     })
#     return redirect(url_for('form'))

# @app.route('/form')
# def form():
#     credentials = session.get('credentials')
#     if not credentials:
#         return redirect(url_for('index'))
#     return render_template('form.html')

# def get_gmail_service():
#     creds = None
#     if 'credentials' in session:
#         creds_data = session['credentials']
#         creds = Credentials(
#             token=creds_data['token'],
#             refresh_token=creds_data['refresh_token'],
#             token_uri=creds_data['token_uri'],
#             client_id=creds_data['client_id'],
#             client_secret=creds_data['client_secret'],
#             scopes=creds_data['scopes']
#         )
#         try:
#             if creds and creds.expired and creds.refresh_token:
#                 creds.refresh(Request())
#                 session['credentials']['token'] = creds.token
#         except RefreshError:
#             session.pop('credentials', None)
#             return redirect(url_for('connect_gmail'))
#     if not creds:
#         return redirect(url_for('connect_gmail'))
#     service = build('gmail', 'v1', credentials=creds)
#     return service

# @app.route('/connect_gmail')
# def get_gmail_service():
#     creds = None
#     if os.path.exists('token.json'):
#         creds = Credentials.from_authorized_user_file('token.json', SCOPES)
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
#             creds = flow.run_local_server(port=0)
#         with open('token.json', 'w') as token:
#             token.write(creds.to_json())
#     service = build('gmail', 'v1', credentials=creds)
#     return service
@app.route('/connect')
def connect():
    #  GetService()
    return render_template('login.html')
    # session.clear()
    # flow = Flow.from_client_secrets_file(
    #     CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    # authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    # session['state'] = state
    # print(f"Session state set: {state}")
    # return redirect(authorization_url)


# def credentials_to_dict(credentials):
#     return {
#         'token': credentials.token,
#         'refresh_token': credentials.refresh_token,
#         'token_uri': credentials.token_uri,
#         'client_id': credentials.client_id,
#         'client_secret': credentials.client_secret,
#         'scopes': credentials.scopes
#     }

# def get_gmail_service():
    # return Create_Service("client_secret.json", 'gmail', 'v1', ['https://www.googleapis.com/auth/gmail.send'])
    # if 'state' not in session:
        # return "Session state not found", 400
    
    # if 'credentials' not in session:
        # raise Exception("User must be authenticated")

    # state = session['state']
    # if request.args.get('state') != state:
        # print(f"State mismatch: session state: {state}, request state: {request.args.get('state')}")
        # return "State mismatch error", 400

    # credentials_data = session['credentials']
    # credentials = dict_to_credentials(credentials_data)
    # service = build('gmail', 'v1', credentials=credentials)
    # return service
    


# def get_gmail_service():
#     credentials = service_account.Credentials.from_service_account_file(
#         SERVICE_ACCOUNT_FILE, scopes=SCOPES)
#     service = build('gmail', 'v1', credentials=credentials)
#     return service

# @app.route('/oauth2callback')
# def oauth2callback():
#     if 'state' not in session:
#         return "Session state not found", 400
    
#     state = session['state']
#     request_state = request.args.get('state')

#     if  request_state != state:
#         print(f"State mismatch: session state: {state}, request state: {request.args.get('state')}")
#         return "State mismatch error ", 400
    
#     flow = Flow.from_client_secrets_file(
#         CLIENT_SECRETS_FILE, scopes=SCOPES, state=state, redirect_uri=REDIRECT_URI
#     )
#         # Debugging information
#     print(f"Authorization response URL: {request.url}")
#     print(f"Session state: {session['state']}")

#     try:
#         flow.fetch_token(authorization_response=request.url)
#     except Exception as e:
#         print(f"Error fetching token: {e}")
#         return f"Error fetching token: {e}", 400
#     # flow.fetch_token(authorization_response=request.url)

#     credentials = flow.credentials
#     session['credentials'] = credentials_to_dict(credentials)

# #     return redirect(url_for('dashboard'))

# # @app.route('/dashboard')
# # def dashboard():
# #     if 'credentials' not in session:
# #         return redirect(url_for('connect'))

# #     credentials = dict_to_credentials(session['credentials'])
# #     service = build('gmail', 'v1', credentials=credentials)
# #     user_info = service.users().getProfile(userId='me').execute()
# #     email_address = user_info['emailAddress']
# #     return f"User email: {email_address}"

#     service = build('gmail', 'v1', credentials=credentials)
#     user_info = service.users().getProfile(userId='me').execute()
#     email_address = user_info['emailAddress']

#     # if check_user_subscription(email_address):
#     #     return render_template('form.html', email=email_address)
#     # else:
#     #     return render_template('pricing.html', email=email_address)
#     customer = find_customer(email_address)
#     if customer:
#         return Dashboard(customer['email'], customer['stripeID'], customer['total_emails'], customer['plan'], customer['priceID'], service, customer['name'], customer['plan_emails'])
#     else:
#         return render_template('pricing.html', email=email_address, service=service)
    
@app.route('/Dashboard', methods=['GET'])
def Dashboard(email, customer_id, total_emails, plan, product_id, service, name, plan_emails, password):
    return render_template('db.html', customer_id=customer_id, product_id=product_id, total_emails=total_emails, email=email, plan=plan, service=service, name=name, plan_emails=plan_emails, password=password)


def find_customer(email):
    customer = customers_collection.find_one({"email": email})
    if customer:
        return {
            "stripeID": customer.get('stripeID'),
            "password": customer.get('password'),
            "email": customer.get('email'),
            "plan": customer.get('plan'),
            "total_emails": customer.get('total_emails'),
            "priceID": customer.get('priceID'),
            "name": customer.get('name'),
            "plan_emails": customer.get('plan_emails')
        }
    return None

# ###########################################################################

def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}

# def dict_to_credentials(credentials_dict):
#     from google.oauth2.credentials import Credentials
#     return Credentials(**credentials_dict)

@app.route('/send_email', methods=['POST'])
def send_email():
    if 'credentials' not in session:
        return redirect('connect')

    credentials = Credentials(**session['credentials'])
    service = build('gmail', 'v1', credentials=credentials)
    email = request.form['email']
    subject = request.form['subject']
    message_text = request.form['message']

    message = create_message('me', email, subject, message_text)
    send_message(service, 'me', message)

    return 'Email sent successfully!'

@app.route('/create-message', methods=['POST'])
def create_msg():
    data = request.json
    sender = data['sender']
    to = data['to']
    subject = data['subject']
    message_text = data['message_text']
    
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}


def create_message(sender, to, subject, message_text):
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}


# @app.route('/send_msg', methods=['POST'])
# def snd_msg():
#         data = request.json
#         servicee = get_gmail_service()
#         user_id = data['user_id'],
#         content = data['message']
#         message = servicee.users().messages().send(userId='me', body=content).execute()
#         print('Message Id: %s' % message['id'])
#         return message


@app.route('/snd_msg', methods=['POST'])
def snd_msg():
    data = request.json
    sender = data['sender']
    to = data['to']
    subject = data['subject']
    message_text = data['message_text']
    
    # Create the message
    message_content = create_message(sender, to, subject, message_text)
    
    # Send the message
    service = get_service()
    message = service.users().messages().send(userId='me', body=message_content).execute()
    print('Message Id: %s' % message['id'])
    
    return jsonify(message)



def send_message(service, user_id, message):
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        print('Message Id: %s' % message['id'])
        return message
    except Exception as error:
        print(f'An error occurred: {error}')

def scrape_website(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        main_content = soup.find('main') or soup.body
        text = ' '.join(main_content.stripped_strings)
        return text
    except requests.RequestException as e:
        return "Failed to scrape website"

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
    
@app.route('/get-site-description', methods=['POST'])
def get_site_description_api():
    url = request.json.get('url')
    description = get_site_description(url)
    return jsonify({'description': description})   

def generate_pitch(email, website_content, user_pitch):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a highly skilled assistant tasked with generating a custom email pitch."},
                {"role": "user", "content": f"Generate a custom pitch email for a company with this website content: '{website_content}' and this user pitch: '{user_pitch}'"}
            ],
            max_tokens=200
        )
        message_text = response['choices'][0]['message']['content']
        subject = "Regarding: " + user_pitch[:30]
        return email, subject, message_text.strip()
    except Exception as e:
        print(f"An error occurred: {e}")
        return email, "Error", "Failed to generate pitch due to an error"

# @app.route('/cost', methods=['GET'])
# def get_cost():
#     return jsonify(costs)

# @app.route('/log_transaction', methods=['POST'])
# def log_transaction(data=None):
#     if data is None:
#         data = request.json
#     costs["total"] += data["cost"]
#     transactions.append(data)
#     save_costs()
#     save_transactions()
#     return jsonify({"message": "Transaction logged", "total_cost": costs["total"]})

# @app.route('/transactions', methods=['GET'])
# def get_transactions():
#     return jsonify(transactions)

@app.route('/', methods=['GET', 'POST'])
def index():
    # service = get_gmail_service()
    if request.method == 'POST':
        user_pitch = request.form.get('user_pitch', '')
        ThreadId = CreateThread()
        if 'file' in request.files and request.files['file'].filename != '':

            file = request.files['file']
            df = pd.read_csv(file)
            results = []

            for index, row in df.iterrows():

                content = scrape_website(row['website'])

                # email, subject, message = generate_pitch(row['email'], content, user_pitch)
                email_content = asyncio.run(AddMessagesToThread(ThreadId, content, user_pitch))

                lines = email_content.split('\n')

                # The first line is the subject
                subject_line = lines[0].replace("**Subject:** ", "").strip()

                # The rest is the main message
                main_message = "\n".join(lines[1:]).strip() 

                results.append([email, subject_line, main_message])

                log_data = {"email": email, "message": main_message[:50], "cost": 0.01}
                log_transaction(log_data)

            result_df = pd.DataFrame(results, columns=['email', 'subject', 'message'])
            result_df.to_csv('updated_output.csv', index=False)
            service = get_gmail_service()

            for index, row in result_df.iterrows():
                message = create_message('me', row['email'], row['subject'], row['message'])
                send_message(service, 'me', message)
            return jsonify('Emails sent successfully!')
        
        else:
            email = request.form['email']
            website = request.form['website']
            content = get_site_description(website)
            # email, subject, message = generate_pitch(email, content, user_pitch)
            # AddMessagesToThread(ThreadId, content, user_pitch)
            # Run the async function
            email_content = asyncio.run(AddMessagesToThread(ThreadId, content, user_pitch))

            lines = email_content.split('\n')
            # The first line is the subject
            subject_line = lines[0].replace("**Subject:** ", "").strip()
            # The rest is the main message
            main_message = "\n".join(lines[1:]).strip()
            log_data = {"email": email, "message": main_message[:50], "cost": 0.01}
            log_transaction(log_data)
            service = get_gmail_service()
            message = create_message('me', email, subject_line, main_message)
            send_message(service, 'me', message)
            return jsonify('Email sent successfully!')
        
    return render_template('index.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)

    
# if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

