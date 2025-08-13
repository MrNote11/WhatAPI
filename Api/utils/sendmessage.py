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


def get_interactive_list_message(recipient, header, body, button_text, list_items):
    """
    Create interactive list message for WhatsApp
    """
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": header},
            "body": {"text": body},
            "footer": {"text": "Select an option"},
            "action": {
                "button": button_text,
                "sections": [
                    {
                        "title": "Options",
                        "rows": list_items
                    }
                ]
            }
        }
    }


def get_interactive_button_message(recipient, body, buttons):
    """
    Create interactive button message for WhatsApp
    """
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual", 
        "to": recipient,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": buttons
            }
        }
    }


def send_whatsapp_interactive_message(recipient, message_data):
    """
    Send interactive WhatsApp message (list or buttons)
    """
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            settings.WHATSAPP_URL, 
            json=message_data, 
            headers=headers, 
            timeout=10
        )
        
        if response.ok:
            logger.info(f"Interactive WhatsApp message sent successfully to {recipient}")
            return {"status": "success", "data": response.json()}
        else:
            logger.error(f"Failed to send interactive message: {response.status_code} - {response.text}")
            return {
                "status": "error", 
                "error": response.text, 
                "status_code": response.status_code
            }
    except requests.RequestException as e:
        logger.error(f"Network error sending interactive message: {str(e)}")
        return {"status": "error", "error": str(e)}


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


def send_network_selection_menu(wa_id):
    """Send network selection interactive list"""
    list_items = [
        {"id": "mtn", "title": "MTN", "description": "MTN Network"},
        {"id": "airtel", "title": "Airtel", "description": "Airtel Network"}, 
        {"id": "glo", "title": "Glo", "description": "Globacom Network"},
        {"id": "9mobile", "title": "9mobile", "description": "9mobile Network"}
    ]
    
    message_data = get_interactive_list_message(
        wa_id,
        "📡 Network Selection",
        "Please select your network provider from the options below:",
        "Select Network",
        list_items
    )
    
    return send_whatsapp_interactive_message(wa_id, message_data)


def send_amount_selection_menu(wa_id, network):
    """Send amount selection interactive list"""
    list_items = [
        {"id": "100", "title": "₦100", "description": "One Hundred Naira"},
        {"id": "200", "title": "₦200", "description": "Two Hundred Naira"},
        {"id": "500", "title": "₦500", "description": "Five Hundred Naira"},
        {"id": "1000", "title": "₦1000", "description": "One Thousand Naira"}
    ]
    
    message_data = get_interactive_list_message(
        wa_id,
        f"💰 {network.upper()} Amount Selection",
        "Please select the recharge amount:",
        "Select Amount",
        list_items
    )
    
    return send_whatsapp_interactive_message(wa_id, message_data)


def send_confirmation_buttons(wa_id, network, phone, amount):
    """Send confirmation buttons"""
    buttons = [
        {
            "type": "reply",
            "reply": {
                "id": "confirm_yes",
                "title": "✅ Yes, Confirm"
            }
        },
        {
            "type": "reply", 
            "reply": {
                "id": "confirm_no",
                "title": "❌ No, Cancel"
            }
        }
    ]
    
    confirmation_text = (
        f"🔍 *Please Confirm Your Recharge*\n\n"
        f"📡 Network: *{network.upper()}*\n"
        f"📱 Phone Number: *{phone}*\n" 
        f"💰 Amount: *₦{amount}*\n\n"
        f"Do you want to proceed with this recharge?"
    )
    
    message_data = get_interactive_button_message(wa_id, confirmation_text, buttons)
    return send_whatsapp_interactive_message(wa_id, message_data)


def generate_response(message_body, wa_id, message_type="text"):
    """
    Generate response based on user input and conversation state
    """
    try:
        # Handle different message types
        if message_type == "interactive":
            # Extract the selection from interactive message
            response = message_body  # This will be the ID from the selected option
        else:
            # Normalize text input
            response = message_body.strip().lower().replace("_", " ")
        
        # Set up possible values
        networks = ['mtn', 'airtel', 'glo', '9mobile']
        amounts = ['100', '200', '500', '1000']
        
        # Get user state
        user_state = get_user_state(wa_id)
        current_step = user_state.get("step", "start")
        
        # STEP 1: Start
        if current_step == "start":
            if response in ["welcome", "start", "hi", "hello"] or message_type == "interactive":
                set_user_state(wa_id, {"step": "choose_network"})
                
                # Send welcome message first
                welcome_text = "🤖 *Welcome to Airtime Recharge Bot!*\n\nI'll help you recharge your phone with airtime quickly and easily."
                send_result = send_whatsapp_message(wa_id, welcome_text)
                
                # Then send network selection menu
                menu_result = send_network_selection_menu(wa_id)
                
                if menu_result["status"] == "success":
                    return None  # Don't send additional text message
                else:
                    return "❌ Error sending network menu. Please type the network name: MTN, Airtel, Glo, or 9mobile"
            else:
                return "👋 Hello! Please type *welcome* to begin your airtime recharge."

        # STEP 2: Choose Network
        elif current_step == "choose_network":
            if response in networks:
                user_state["network"] = response
                user_state["step"] = "phone_number"
                set_user_state(wa_id, user_state)
                return f"📱 *{response.upper()} Network Selected*\n\nPlease enter the 11-digit phone number you'd like to recharge:\n\n_Example: 08012345678_"
            else:
                # Resend network menu
                menu_result = send_network_selection_menu(wa_id)
                if menu_result["status"] == "success":
                    return None
                else:
                    return f"❌ Invalid network choice. Please select: *{', '.join([n.upper() for n in networks])}*"

        # STEP 3: Enter Phone Number
        elif current_step == "phone_number":
            # Validate phone number
            # clean_phone = re.sub(r'[^\d]', '', response)  # Remove non-digits

            if len(response) == 11 and response.startswith(('080', '081', '070', '090', '091')) and response.isdigit():
                user_state["phone"] = response
                user_state["step"] = "choose_amount"
                set_user_state(wa_id, user_state)
                
                # Send amount selection menu
                network = user_state["network"]
                menu_result = send_amount_selection_menu(wa_id, network)
                
                if menu_result["status"] == "success":
                    return None  # Don't send additional text message
                else:
                    return f"💰 *Phone Number: {response}*\n\nSelect amount: ₦100, ₦200, ₦500, or ₦1000"
            elif len(response) > 11 or len(response) < 11:
                return "Input the right amount of digits"
            else:
                return "❗ *Invalid Phone Number*\n\nPlease enter a valid 11-digit Nigerian phone number starting with:\n• 070, 080, 081, 090, or 091\n\n_Example: 08012345678_"

        # STEP 4: Choose Amount
        elif current_step == "choose_amount":
            # Handle amount selection
            amount_str = response.replace('₦', '').strip()
            
            if amount_str in amounts:
                user_state["amount"] = amount_str
                user_state["step"] = "confirm"
                set_user_state(wa_id, user_state)
                
                # Send confirmation buttons
                network = user_state["network"]
                phone = user_state["phone"]
                button_result = send_confirmation_buttons(wa_id, network, phone, amount_str)
                
                if button_result["status"] == "success":
                    return None  # Don't send additional text message
                else:
                    return (f"✅ *Please Confirm*\n\n"
                           f"Network: *{network.upper()}*\n"
                           f"Phone: *{phone}*\n"
                           f"Amount: *₦{amount_str}*\n\n"
                           f"Reply *YES* to confirm or *NO* to cancel.")
            else:
                # Resend amount menu
                network = user_state.get("network", "")
                menu_result = send_amount_selection_menu(wa_id, network)
                if menu_result["status"] == "success":
                    return None
                else:
                    return f"❌ Invalid amount. Please choose: *₦100, ₦200, ₦500, or ₦1000*"

        # STEP 5: Confirmation
        elif current_step == "confirm":
            if response in ["confirm_yes", "yes", "y", "confirm", "ok"]:
                # Process the recharge
                network = user_state.get('network', 'Unknown')
                phone = user_state.get('phone', 'Unknown')
                amount = user_state.get('amount', 'Unknown')
                
                # Here you would integrate with actual airtime API
                # For now, we'll simulate a successful recharge
                
                # Clear user state after successful transaction
                clear_user_state(wa_id)
                
                return (f"🎉 *Recharge Successful!*\n\n"
                       f"✅ ₦{amount} {network.upper()} airtime has been sent to *{phone}*\n\n"
                       f"📱 Your airtime should arrive within 2-5 minutes.\n\n"
                       f"Thank you for using our service! 🙏\n"
                       f"Type *welcome* to make another recharge.")
                
            elif response in ["confirm_no", "no", "n", "cancel"]:
                clear_user_state(wa_id)
                return "❌ *Recharge Cancelled*\n\nNo charges have been made.\nType *welcome* to start a new recharge."
            else:
                # Resend confirmation buttons
                network = user_state.get('network', 'Unknown')
                phone = user_state.get('phone', 'Unknown')
                amount = user_state.get('amount', 'Unknown')
                
                button_result = send_confirmation_buttons(wa_id, network, phone, amount)
                if button_result["status"] == "success":
                    return None
                else:
                    return "Please click *Yes* to confirm or *No* to cancel the recharge."

        # Handle reset command at any step
        if response in ["reset", "restart", "start over", "menu"]:
            clear_user_state(wa_id)
            set_user_state(wa_id, {"step": "choose_network"})
            
            reset_text = "🔄 *Session Reset*\n\nLet's start fresh!"
            send_whatsapp_message(wa_id, reset_text)
            
            menu_result = send_network_selection_menu(wa_id)
            if menu_result["status"] == "success":
                return None
            else:
                return "Please select your network: MTN, Airtel, Glo, or 9mobile"

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
            return wa_id, name, message_body, "text"
            
        elif message_type == "interactive":
            # Handle interactive message responses (list/button selections)
            interactive = message["interactive"]
            interactive_type = interactive.get("type")
            
            if interactive_type == "list_reply":
                # User selected from a list
                message_body = interactive["list_reply"]["id"]  # Get the ID of selected item
                return wa_id, name, message_body, "interactive"
                
            elif interactive_type == "button_reply":
                # User clicked a button
                message_body = interactive["button_reply"]["id"]  # Get the button ID
                return wa_id, name, message_body, "interactive"
                
        elif message_type == "button":
            # Legacy button response (for older button format)
            message_body = message["button"]["payload"]
            return wa_id, name, message_body, "interactive"
            
        elif message_type in ["image", "video", "audio", "document"]:
            return wa_id, name, None, "media"  # Handle media messages
            
        else:
            return wa_id, name, None, "unsupported"
            
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Error extracting message data: {str(e)}")
        raise WhatsAppBotError(f"Invalid message structure: {str(e)}")


def process_whatsapp_message(body):
    """
    Process incoming WhatsApp message
    """
    
    try:
        wa_id, name, message_body, message_type = extract_message_data(body)
        
        if message_type == "media":
            # Handle media messages
            response_text = "📷 *Media Not Supported*\n\nPlease use the interactive menus or send text messages only.\n\nType *welcome* to start."
            result = send_whatsapp_message(wa_id, response_text)
            return {"status": "media_not_supported", "wa_id": wa_id}
            
        elif message_type == "unsupported":
            # Handle unsupported message types
            response_text = "❓ *Message Type Not Supported*\n\nPlease use the interactive menus or send text messages.\n\nType *welcome* to start."
            result = send_whatsapp_message(wa_id, response_text)
            return {"status": "unsupported_message", "wa_id": wa_id}
        
        # Log the message (different for interactive vs text)
        if message_type == "interactive":
            logger.info(f"Received interactive selection from {name} ({wa_id}): {message_body}")
        else:
            logger.info(f"Received text message from {name} ({wa_id}): {message_body}")
        
        # Generate response based on conversation flow
        response_text = generate_response(message_body, wa_id, message_type)
        
        # Only send response if there's text to send (some responses send interactive messages directly)
        if response_text:
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
                "message_type": message_type,
                "wa_id": wa_id,
                "name": name,
                "response_sent": bool(response_text)
            }
        }
        
    except WhatsAppBotError as e:
        logger.error(f"WhatsApp bot error: {str(e)}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error processing message: {str(e)}")
        return {"status": "error", "message": "Internal server error"}


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
        
        # Parse JSON body
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