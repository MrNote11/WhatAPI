from django.conf import settings
import requests
import logging
import json
import hashlib
import hmac
import re
from django.core.cache import cache
from rest_framework.response import Response
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import time


# Set up logging
logger = logging.getLogger(__name__)

class WhatsAppBotError(Exception):
    """Custom exception for WhatsApp bot errors"""
    pass


def send_whatsapp_message(recipient, message):
    """
    Send a WhatsApp message to a specific recipient
    """
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = get_text_message_input(recipient, message)
    
    try:
        response = requests.post(
            settings.WHATSAPP_URL, 
            json=data, 
            headers=headers, 
            timeout=10
        )
        
        if response.ok:
            logger.info(f"WhatsApp message sent successfully to {recipient}")
            return {"status": "success", "data": response.json()}
        else:
            logger.error(f"Failed to send WhatsApp message: {response.status_code} - {response.text}")
            return {
                "status": "error", 
                "error": response.text, 
                "status_code": response.status_code
            }
    except requests.RequestException as e:
        logger.error(f"Network error sending WhatsApp message: {str(e)}")
        return {"status": "error", "error": str(e)}


def get_text_message_input(recipient, text):
    """
    Format message data for WhatsApp API
    """
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }


def get_user_state(wa_id):
    """
    Get user's conversation state from cache
    """
    cache_key = f"whatsapp_user_{wa_id}"
    return cache.get(cache_key, {"step": "start"})

def set_user_state(wa_id, state):
    """
    Store user's conversation state in cache (expires in 30 minutes)
    """
    cache_key = f"whatsapp_user_{wa_id}"
    cache.set(cache_key, state, timeout=1800)  # 30 minutes

def clear_user_state(wa_id):
    """
    Clear user's conversation state
    """
    cache_key = f"whatsapp_user_{wa_id}"
    cache.delete(cache_key)


def generate_response(message_body, wa_id):
    """
    Generate response based on user input and conversation state
    """
    try:
        # Normalize input
        response = message_body.strip().lower().replace("_", " ")
        
        # Set up possible values
        networks = ['mtn', 'airtel', 'glo', '9mobile']
        amounts = ['100', '200', '500', '1000']
        
        # Get user state
        user_state = get_user_state(wa_id)
        current_step = user_state.get("step", "start")
        
        # STEP 1: Start
        if current_step == "start":
            if response in ["welcome", "start", "hi", "hello"]:
                set_user_state(wa_id, {"step": "choose_network"})
                return "📡 *Welcome to Airtime Recharge Bot!*\n\nChoose a network:\n• MTN\n• Airtel\n• Glo\n• 9mobile"
            else:
                return "👋 Hello! Please type *welcome* to begin your airtime recharge."

        # STEP 2: Choose Network
        elif current_step == "choose_network":
            if response in networks:
                user_state["network"] = response
                user_state["step"] = "phone_number"
                set_user_state(wa_id, user_state)
                return f"📱 *{response.upper()} selected*\n\nEnter the 11-digit phone number you'd like to recharge:"
            else:
                return f"❌ Invalid network choice.\n\nPlease select one of: *{', '.join([n.upper() for n in networks])}*"

        # STEP 3: Enter Phone Number
        elif current_step == "phone_number":
            # Validate phone number
            clean_phone = re.sub(r'[^\d]', '', response)  # Remove non-digits
            
            if len(clean_phone) == 11 and clean_phone.startswith(('080', '081', '070', '090', '091')):
                user_state["phone"] = clean_phone
                user_state["step"] = "choose_amount"
                set_user_state(wa_id, user_state)
                return f"💰 *Phone number: {clean_phone}*\n\nSelect recharge amount:\n• ₦100\n• ₦200\n• ₦500\n• ₦1000"
            else:
                return "❗ Please enter a valid 11-digit Nigerian phone number starting with 070, 080, 081, 090, or 091."

        # STEP 4: Choose Amount
        elif current_step == "choose_amount":
            # Handle amount with or without ₦ symbol
            amount_str = re.sub(r'[₦,\s]', '', response)
            
            if amount_str in amounts:
                user_state["amount"] = amount_str
                user_state["step"] = "confirm"
                set_user_state(wa_id, user_state)
                
                return (f"✅ *Confirmation Required*\n\n"
                       f"Network: *{user_state['network'].upper()}*\n"
                       f"Phone: *{user_state['phone']}*\n"
                       f"Amount: *₦{amount_str}*\n\n"
                       f"Reply *YES* to confirm or *NO* to cancel.")
            else:
                return f"❌ Invalid amount.\n\nPlease choose from: *₦{', ₦'.join(amounts)}*"

        # STEP 5: Confirmation
        elif current_step == "confirm":
            if response in ["yes", "y", "confirm", "ok"]:
                # Here you would integrate with actual airtime API
                network = user_state.get('network', 'Unknown')
                phone = user_state.get('phone', 'Unknown')
                amount = user_state.get('amount', 'Unknown')
                
                # Clear user state after successful transaction
                clear_user_state(wa_id)
                
                return (f"🎉 *Recharge Successful!*\n\n"
                       f"₦{amount} {network.upper()} airtime has been sent to {phone}\n\n"
                       f"Thank you for using our service! Type *welcome* to make another recharge.")
                
            elif response in ["no", "n", "cancel"]:
                clear_user_state(wa_id)
                return "❌ *Recharge Cancelled*\n\nType *welcome* to start a new recharge."
            else:
                return "Please reply with *YES* to confirm or *NO* to cancel the recharge."

        # Handle reset command at any step
        if response in ["reset", "restart", "start over"]:
            clear_user_state(wa_id)
            return "🔄 *Session Reset*\n\nType *welcome* to begin a new airtime recharge."

        # Fallback for unexpected states
        clear_user_state(wa_id)
        return "❓ Something went wrong. Please type *welcome* to start over."
        
    except Exception as e:
        logger.error(f"Error in generate_response for user {wa_id}: {str(e)}")
        clear_user_state(wa_id)
        return "⚠️ *System Error*\n\nSorry, something went wrong. Please type *welcome* to try again."


def process_text_for_whatsapp(text):
    """
    Process text for WhatsApp formatting
    """
    # Remove content in brackets
    text = re.sub(r"\【.*?\】", "", text).strip()
    
    # Convert double asterisks to single (Markdown to WhatsApp format)
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)
    
    return text


def validate_message_structure(body):
    """
    Validate that the webhook contains a valid WhatsApp message
    """
    try:
        entry = body.get("entry", [])
        if not entry:
            return False
            
        changes = entry[0].get("changes", [])
        if not changes:
            return False
            
        value = changes[0].get("value", {})
        messages = value.get("messages")
        
        return messages and len(messages) > 0
    except (IndexError, KeyError, TypeError):
        return False


def extract_message_data(body):
    """
    Extract message data from webhook payload
    """
    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        # Extract contact info
        contacts = value.get("contacts", [])
        if not contacts:
            raise WhatsAppBotError("No contact information found")
            
        contact = contacts[0]
        wa_id = contact["wa_id"]
        name = contact.get("profile", {}).get("name", "Unknown")
        
        # Extract message
        messages = value["messages"]
        message = messages[0]
        
        # Handle different message types
        message_type = message.get("type")
        
        if message_type == "text":
            message_body = message["text"]["body"]
        elif message_type == "button":
            message_body = message["button"]["text"]
        elif message_type in ["image", "video", "audio", "document"]:
            return None, None, None, "media"  # Handle media messages
        else:
            return None, None, None, "unsupported"
            
        return wa_id, name, message_body, message_type
        
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Error extracting message data: {str(e)}")
        raise WhatsAppBotError(f"Invalid message structure: {str(e)}")


# def verify_webhook_signature(payload, signature):
#     """
#     Verify webhook signature from WhatsApp (if configured)
#     """
#     if not hasattr(settings, 'APP_SECRET') or not settings.APP_SECRET:
#         return True  # Skip verification if no secret configured
        
#     try:
#         expected_signature = hmac.new(
#             settings.APP_SECRET.encode(),
#             payload,
#             hashlib.sha256
#         ).hexdigest()
        
#         return hmac.compare_digest(f"sha256={expected_signature}", signature)
#     except Exception as e:
#         logger.error(f"Error verifying webhook signature: {str(e)}")
#         return False


def process_whatsapp_message(body):
    """
    Process incoming WhatsApp message
    """
    
    try:
        wa_id, name, message_body, message_type = extract_message_data(body)
        
        if message_type == "media":
            # Handle media messages
            response_text = "📷 Media messages are not supported. Please send text messages only."
            result = send_whatsapp_message(wa_id, response_text)
            return {"status": "media_not_supported", "wa_id": wa_id}
            
        elif message_type == "unsupported":
            # Handle unsupported message types
            response_text = "❓ Message type not supported. Please send text messages only."
            result = send_whatsapp_message(wa_id, response_text)
            return {"status": "unsupported_message", "wa_id": wa_id}
        
        logger.info(f"Received message from {name} ({wa_id}): {message_body}")
        
        # Generate response based on conversation flow
        response_text = generate_response(message_body, wa_id)
        
        # Process text for WhatsApp formatting
        response_text = process_text_for_whatsapp(response_text)
        
        # Send response
        result = send_whatsapp_message(wa_id, response_text)
        
        if result["status"] != "success":
            logger.error(f"Failed to send response to {wa_id}: {result.get('error')}")
            return {"status": "send_failed", "error": result.get("error")}
            
        return {
            "status": "success",
            "data": {
                "message_body": message_body,
                "wa_id": wa_id,
                "name": name,
                "response": response_text
            }
        }
        
    except WhatsAppBotError as e:
        logger.error(f"WhatsApp bot error: {str(e)}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error processing message: {str(e)}")
        return {"status": "error", "message": "Internal server error"}


# @csrf_exempt
# @require_http_methods(["GET", "POST"])
# def webhook(request):
#     """
#     Main webhook endpoint for WhatsApp
#     """
#     if request.method == "GET":
#         return verify_webhook(request)
#     else:
#         return handle_message(request)


def verify_webhook(request):
    """
    Verify webhook subscription (GET request)
    """
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
            logger.info("Webhook verified successfully")
            return JsonResponse({"challenge": challenge}, status=200)
        else:
            logger.warning(f"Webhook verification failed - mode: {mode}, token: {token}")
            return JsonResponse({
                "status": "error", 
                "message": "Verification failed"
            }, status=403)
    else:
        logger.warning("Missing parameters in webhook verification")
        return JsonResponse({
            "status": "error", 
            "message": "Missing parameters"
        }, status=400)


def handle_message(request):
    """
    Handle incoming webhook messages (POST request)
    """
    try:
        #--- Verify signature if configured ---
        # signature = request.headers.get('X-Hub-Signature-256', '')
        # if not verify_webhook_signature(request.body, signature):
        #     logger.warning("Invalid webhook signature")
        #     return JsonResponse({
        #         "status": "error",
        #         "message": "Invalid signature"
        #     }, status=403)
        
        #--- Parse JSON body --- 
        try:
            body = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON from webhook")
            return JsonResponse({
                "status": "error",
                "message": "Invalid JSON"
            }, status=400)
        
        # Handle status updates (delivery receipts, etc.)
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        
        if value.get("statuses"):
            logger.info("Received WhatsApp status update")
            return JsonResponse({"status": "ok"}, status=200)
        
        # Validate message structure
        if not validate_message_structure(body):
            logger.warning("Invalid WhatsApp message structure")
            return JsonResponse({
                "status": "error",
                "message": "Not a valid WhatsApp message"
            }, status=400)
        
        # Process the message
        result = process_whatsapp_message(body)
        
        if result["status"] == "success":
            return JsonResponse({
                "status": "message_processed",
                "data": result["data"]
            }, status=200)
        else:
            return JsonResponse({
                "status": "processing_failed",
                "message": result.get("message", "Unknown error")
            }, status=400)
            
    except Exception as e:
        logger.error(f"Unexpected error in webhook handler: {str(e)}")
        return JsonResponse({
            "status": "error",
            "message": "Internal server error"
        }, status=500)


# Test function for development
def test_send_message():
    """
    Test function to send a WhatsApp message
    """
    phone_number = "2349126709734"  # Replace with test number
    message = "🤖 *WhatsApp Bot Test*\n\nHello! This is a test message from the improved WhatsApp bot.\n\nType *welcome* to start using the airtime recharge service."
    
    result = send_whatsapp_message(phone_number, message)
    
    if result.get("status") == "success":
        print("✅ Test message sent successfully!")
        return True
    else:
        print(f"❌ Failed to send test message: {result.get('error', 'Unknown error')}")
        return False

if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting WhatsApp Bot test...")
    test_send_message()