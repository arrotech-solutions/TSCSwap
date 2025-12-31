import os
import requests
import json
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class WhatsAppClient:
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v17.0"
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "test123")
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def send_text_message(self, to_number, message_text):
        """Send a text message to a WhatsApp user."""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_text
            }
        }
        
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error sending message: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response content: {e.response.text}")
            return None

# Initialize the WhatsApp client
whatsapp_client = WhatsAppClient()

@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """Handle incoming WhatsApp messages and webhook verification."""
    print("\n=== Incoming Webhook Request ===")
    print(f"Method: {request.method}")
    print(f"GET params: {dict(request.GET)}")
    print(f"Headers: {dict(request.headers)}")
    
    if request.method == "GET":
        # Handle webhook verification
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        
        print(f"\n--- Webhook Verification ---")
        print(f"Mode: {mode}")
        print(f"Token received: {token}")
        print(f"Expected token: {whatsapp_client.verify_token}")
        print(f"Challenge: {challenge}")
        
        if mode == "subscribe" and token == whatsapp_client.verify_token:
            print("✅ Webhook verification successful!")
            return HttpResponse(challenge, status=200)
        else:
            print("❌ Webhook verification failed!")
            if mode != "subscribe":
                print(f"Expected mode 'subscribe', got: {mode}")
            if token != whatsapp_client.verify_token:
                print(f"Token mismatch. Expected: '{whatsapp_client.verify_token}', got: '{token}'")
            return HttpResponse("Verification token mismatch", status=403)
    
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            print("Received webhook data:", json.dumps(data, indent=2))
            
            # Process the webhook event
            entry = data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])
            
            if messages:
                message = messages[0]
                if message.get("type") == "text":
                    phone_number = message["from"]
                    message_text = message["text"]["body"]
                    
                    # Echo the message back
                    response_text = f"You said: {message_text}"
                    whatsapp_client.send_text_message(phone_number, response_text)
            
            return JsonResponse({"status": "success"}, status=200)
            
        except Exception as e:
            print(f"Error processing webhook: {str(e)}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
    return JsonResponse({"status": "method not allowed"}, status=405)
