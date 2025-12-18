import requests
import base64
import os
import json
import re
from django.conf import settings
from dotenv import load_dotenv

def get_kra_access_token(consumer_key=None, consumer_secret=None):
    """
    Get access token from KRA API using consumer key and secret
    
    Args:
        consumer_key (str): The KRA API consumer key
        consumer_secret (str): The KRA API consumer secret
        
    Returns:
        tuple: (access_token, error_message)
    """
    if not consumer_key or not consumer_secret:
        return None, 'Missing API credentials'
    
    if not consumer_key or not consumer_secret:
        return None, 'API credentials not configured'
    
    # Create Basic Auth token
    auth_string = f"{consumer_key}:{consumer_secret}"
    auth_token = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Use production KRA API endpoint
        response = requests.get(
            'https://api.kra.go.ke/v1/token/generate?grant_type=client_credentials',
            headers=headers,
            verify=True  # Enable SSL verification for production
        )
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            # Log the first 5 and last 5 characters of the token for debugging
            if access_token:
                masked_token = f"{access_token[:5]}...{access_token[-5:]}"
                print(f"\n=== KRA Access Token ===")
                print(f"Status Code: {response.status_code}")
                print(f"Token: {masked_token}")
                print(f"Expires In: {data.get('expires_in', 'N/A')} seconds")
                print("======================\n")
            return access_token, None
        else:
            print(f"\n=== KRA Token Error ===")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            print("====================\n")
            return None, f"Failed to get access token: {response.status_code} - {response.text}"
    except Exception as e:
        return None, f"Error getting access token: {str(e)}"

def verify_kra_details(kra_pin):
    """
    Verify KRA details using KRA API
    
    Args:
        kra_pin (str): The KRA PIN to verify
        
    Returns:
        dict: A dictionary containing the verification status and data if successful
        {
            'success': bool,
            'data': dict,  # Contains the KRA details if verification is successful
            'message': str  # Status message
        }
    """
    import os
    from dotenv import load_dotenv
    
    # Load environment variables directly
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    load_dotenv(dotenv_path=env_path, override=True)
    
    # Get credentials directly from environment
    api_key = os.getenv('GAVACONNECT_API_KEY')
    api_secret = os.getenv('GAVACONNECT_API_SECRET')
    
    print(f"\n=== Verifying KRA PIN: {kra_pin} ===")
    print(f"Using API Key: {'*' * 10}{api_key[-4:] if api_key else 'Not found'}")
    
    if not api_key or not api_secret:
        return {
            'success': False,
            'message': 'API credentials not properly configured in .env file'
        }
    
    # Get the access token using the credentials
    access_token, error = get_kra_access_token(api_key, api_secret)
    if not access_token:
        return {
            'success': False,
            'message': f'Failed to authenticate with KRA API: {error}'
        }
    
    # Prepare the request to verify KRA details
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    payload = {
        'TaxpayerType': 'KE',  # Default to Kenyan resident
        'TaxpayerID': kra_pin.strip()
    }
    
    try:
        # Make API request to production KRA API
        response = requests.post(
            'https://api.kra.go.ke/checker/v1/pin',
            headers=headers,
            json=payload,
            verify=True  # Enable SSL verification for production
        )
        
        # Log the complete response for debugging
        print("\n=== KRA API Response ===")
        print(f"Status Code: {response.status_code}")
        print("Headers:", dict(response.headers))
        print("Response:", response.text)
        print("======================\n")
        
        # Parse the response
        try:
            data = response.json()
            print("\n=== KRA API Response Data ===")
            print(f"Response: {data}")
            print("==========================\n")
            
            # Check if the response contains an error
            if 'ErrorCode' in data:
                error_msg = data.get('ErrorMessage', 'KRA verification failed')
                print(f"\n=== KRA Verification Failed ===")
                print(f"Error: {error_msg}")
                print("============================\n")
                return {
                    'success': False,
                    'data': data,
                    'message': error_msg
                }
            
            # Check if we have valid taxpayer data
            if data.get('TaxpayerName'):
                print("\n=== KRA Verification Success ===")
                print(f"Taxpayer Name: {data.get('TaxpayerName')}")
                print(f"Taxpayer PIN: {data.get('TaxpayerPIN')}")
                print("============================\n")
                
                return {
                    'success': True,
                    'data': {
                        'name': data.get('TaxpayerName'),
                        'pin': data.get('TaxpayerPIN'),
                        'full_name': data.get('TaxpayerName')  # Add full_name for compatibility
                    },
                    'message': 'KRA verification successful'
                }
            else:
                error_msg = 'No taxpayer information found for this ID'
                print(f"\n=== KRA Verification Failed ===")
                print(f"Error: {error_msg}")
                print("============================\n")
                return {
                    'success': False,
                    'data': data,
                    'message': error_msg
                }
        except Exception as e:
            print(f"\n=== Error Parsing Response ===")
            print(f"Error: {str(e)}")
            print("Raw Response:", response.text)
            print("==========================\n")
            return {
                'success': False,
                'message': 'Error parsing KRA API response'
            }
        else:
            error_data = response.json()
            error_msg = error_data.get('ErrorMessage', 'Unknown error')
            return {
                'success': False,
                'message': f'KRA verification failed: {error_msg}'
            }
            
    except requests.exceptions.RequestException as e:
        import socket
        import sys
        import json
        
        # Get detailed error information
        error_type = type(e).__name__
        error_details = str(e)
        
        # Print debug information
        print("\n=== KRA API Request Details ===")
        print(f"URL: https://sbx.kra.go.ke/checker/v1/pin")
        print(f"Headers: {headers}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        # Additional diagnostics
        try:
            # Try to resolve the production hostname
            api_host = 'api.kra.go.ke'
            resolved_ip = socket.gethostbyname(api_host)
            dns_status = f"Resolved {api_host} to {resolved_ip}"
            print(f"DNS Resolution: {dns_status}")
            
            # Test connection to KRA server
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((resolved_ip, 443))
            kra_status = "KRA server is reachable" if result == 0 else f"KRA server connection failed with code {result}"
            print(f"KRA Server Status: {kra_status}")
            sock.close()
            
        except Exception as dns_error:
            print(f"DNS/Connection Test Failed: {str(dns_error)}")
        
        # Print system info
        print("\n=== System Information ===")
        print(f"Python Version: {sys.version}")
        print(f"Requests Version: {requests.__version__}")
        
        # Test internet connectivity
        try:
            test_response = requests.get('https://www.google.com', timeout=5)
            print(f"Internet Connectivity: ✅ (Status: {test_response.status_code})")
        except Exception as test_error:
            print(f"Internet Connectivity: ❌ ({str(test_error)})")
        
        print("\n=== Error Details ===")
        print(f"Error Type: {error_type}")
        print(f"Error Details: {error_details}")
        
        # If we have a response object, log its details
        if hasattr(e, 'response') and e.response is not None:
            print("\n=== API Response ===")
            print(f"Status Code: {e.response.status_code}")
            try:
                print(f"Response: {e.response.text}")
            except:
                print("Could not decode response")
        
        return {
            'success': False,
            'message': f'Error connecting to KRA API. Please check your internet connection and try again.\nError details: {error_type} - {error_details}'
        }


