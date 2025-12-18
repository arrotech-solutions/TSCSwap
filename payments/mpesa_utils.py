import base64
import json
import requests
import datetime
from datetime import datetime
from django.conf import settings
from requests.auth import HTTPBasicAuth
from .models import MpesaTransaction

def get_access_token():
    """Generate access token for M-Pesa API"""
    consumer_key = settings.MPESA_CONSUMER_KEY
    consumer_secret = settings.MPESA_CONSUMER_SECRET
    api_url = settings.MPESA_AUTH_URL
    
    try:
        print(f"Getting access token from: {api_url}")
        print(f"Using consumer key: {consumer_key[:5]}...{consumer_key[-5:] if consumer_key else ''}")
        
        response = requests.get(
            api_url,
            auth=HTTPBasicAuth(consumer_key, consumer_secret),
            timeout=30
        )
        
        # Log the response status and content for debugging
        print(f"Auth response status: {response.status_code}")
        print(f"Auth response content: {response.text}")
        
        response.raise_for_status()
        
        access_token = response.json().get('access_token')
        if not access_token:
            print("Error: No access token in response")
            return None
            
        print("Successfully retrieved access token")
        return access_token
        
    except requests.exceptions.RequestException as e:
        print(f"Request error getting access token: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
    except Exception as e:
        print(f"Unexpected error getting access token: {str(e)}")
        
    return None

def generate_timestamp():
    """Generate timestamp in the format: YYYYMMDDHHMMSS"""
    return datetime.now().strftime('%Y%m%d%H%M%S')

def generate_password(shortcode, passkey, timestamp):
    """Generate password for M-Pesa API"""
    data = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(data.encode()).decode()

def stk_push(phone_number, amount, account_reference, description, user=None):
    """Initiate STK push to customer's phone"""
    # Use the provided description or default to a generic one
    if not description:
        description = 'TSC Service Fee'
    
    # Ensure amount is a float and format to 2 decimal places
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        amount = 1.0  # Default to 1 KES if amount is invalid
    
    # Format account reference as TSC{user.id} if user is provided
    if user and user.is_authenticated:
        account_reference = f'TSC{user.id}'
    elif not account_reference.startswith('TSC'):
        account_reference = f'TSC{account_reference}'
    
    print(f"[STK_PUSH] Amount set to: {amount} KES")
    
    # Get M-Pesa configuration from settings
    business_shortcode = settings.MPESA_PAYBILL
    passkey = settings.MPESA_PASSKEY
    callback_url = settings.MPESA_CALLBACK_URL
    stk_push_url = settings.MPESA_STK_PUSH_URL
    
    print(f"Initiating STK push with:")
    print(f"- Business Shortcode: {business_shortcode}")
    print(f"- Callback URL: {callback_url}")
    print(f"- Phone: {phone_number}")
    print(f"- Amount: {amount}")
    print(f"- Reference: {account_reference}")
    print(f"- Description: {description}")
    
    # Get access token
    access_token = get_access_token()
    if not access_token:
        error_msg = "Failed to get access token from M-Pesa API"
        print(error_msg)
        return {"error": error_msg}
        
    timestamp = generate_timestamp()
    password = generate_password(business_shortcode, passkey, timestamp)
    
    # Format phone number (add country code if not present)
    if not phone_number.startswith('254'):
        if phone_number.startswith('0'):
            phone_number = f"254{phone_number[1:]}"
        else:
            phone_number = f"254{phone_number}"
    
    # Convert amount to integer for M-Pesa API (1 KSH = 1 unit)
    try:
        amount_int = int(amount)
        print(f"[STK_PUSH] Using amount: {amount_int} KSH for M-Pesa request")
    except (TypeError, ValueError):
        amount_int = 1  # Default to 1 KSH if conversion fails
        print(f"[STK_PUSH] Invalid amount '{amount}', defaulting to {amount_int} KSH")
    
    payload = {
        "BusinessShortCode": business_shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount_int,  # Use the provided amount
        "PartyA": phone_number,
        "PartyB": business_shortcode,
        "PhoneNumber": phone_number,
        "CallBackURL": callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": f'TSC {description[:20]}',  # Truncate if too long
    }
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(
            getattr(settings, 'MPESA_STK_PUSH_URL', 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'),
            headers=headers,
            json=payload
        )
        response_data = response.json()
        
        # Save transaction to database
        transaction = MpesaTransaction.objects.create(
            user=user,
            phone_number=phone_number,
            amount=amount,
            account_reference=account_reference,
            transaction_desc=description,
            merchant_request_id=response_data.get('MerchantRequestID'),
            checkout_request_id=response_data.get('CheckoutRequestID'),
            status='pending'
        )
        
        return {
            "success": True,
            "transaction_id": transaction.id,
            "checkout_request_id": transaction.checkout_request_id,
            "merchant_request_id": transaction.merchant_request_id,
            "response": response_data
        }
    except Exception as e:
        return {"error": str(e)}
