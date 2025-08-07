from django.conf import settings
import requests
import logging
import json
from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import re
from Api.service.openai_service import *

def send_whatsapp_messages(data):
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
               "Content-Type": settings.WHATSAPP_CONTENT_TYPE }
        
    # payload = {
    #     "messaging_product": "whatsapp",
    #     "to": settings.WHATSAPP_RECIPIENT_NUMBER_ID,  # e.g., "2349126709734"
    #     "type": "template",
    #     "template": {
    #         "name": "hello_world\nwhats up",  # ✅ Must match a real template
    #         "language": {
    #             "code": "en_US"
    #         }
    #     }
    # }


    response = requests.post(settings.WHATSAPP_URL, json=data, headers=headers, timeout=10)
    if response.ok:
        logging.info("WhatsApp message sent successfully.")
        return {"status": "success", "data": response.json()}
    else:
        logging.error(f"Failed to send WhatsApp message: {response.status_code} - {response.text}")
        return {"status": "error", "error": response.text, "status_code": response.status_code}
    




def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    
def generate_response(response, request):
    response = response.strip().lower().replace("_", " ")  # normalize input like 'Start', 'WELCOME', 'glo_mobile'

    # Set up possible values
    networks = ['mtn', 'airtel', 'glo', '9mobile']
    amounts = ['100', '200', '500', '1000']
    confirmations = ['yes', 'no']

    # Initialize session state if not present
    if "step" not in request.session:
        request.session['step'] = "start"
        request.session.modified = True

    # STEP 1: Start
    if request.session["step"] == "start":
        if response == "welcome":
            request.session["step"] = "choose_network"
            return "📡 Choose a network: MTN, Airtel, Glo, or 9mobile"
        else:
            return "👋 Hello! Please type *welcome* to begin."

    # STEP 2: Choose Network
    elif request.session["step"] == "choose_network":
        if response in networks:
            request.session["network"] = response
            request.session["step"] = "phone_number"
            return "📱 Enter the phone number you'd like to recharge (11 digits):"
        else:
            return f"❌ Invalid choice. Pick one: {', '.join(networks)}"

    # STEP 3: Enter Phone Number
    elif request.session["step"] == "phone_number":
        if response.isdigit() and len(response) == 11:
            request.session["phone"] = response
            request.session["step"] = "choose_amount"
            return f"💵 Enter amount: {', '.join(amounts)}"
        else:
            return "❗ Enter a valid 11-digit phone number."

    # STEP 4: Choose Amount
    elif request.session["step"] == "choose_amount":
        if response in amounts:
            request.session["amount"] = response
            request.session["step"] = "confirm"
            return (f"✅ Confirm recharge of ₦{response} on {request.session['network']} "
                    f"to {request.session['phone']}? (yes/no)")
        else:
            return f"❌ Invalid amount. Choose from: {', '.join(amounts)}"

    # STEP 5: Confirmation
    elif request.session["step"] == "confirm":
        if response == "yes":
            request.session.flush()
            return "🎉 Recharge successful!"
        elif response == "no":
            request.session.flush()
            return "❌ Recharge cancelled."
        else:
            return "Please reply with *yes* or *no*."

    # Catch-all fallback
    return "👋 Please type *welcome* to begin."



def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def process_whatsapp_message(body,request):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_body = message["text"]["body"]
    logging.info(f"Received message from {name} ({wa_id}): {message_body}")
    # TODO: implement custom function here
    response = generate_response(message_body, request)
    # response = process_text_for_whatsapp(response)

    data = get_text_message_input(settings.WHATSAPP_RECIPIENT_NUMBER_ID, response)
    send_whatsapp_messages(data)
    return Response({
        "data": [{
            "message_body":message_body,
            "wa_id":wa_id,
            "name":name
        }]
    }, status=200)
    



def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
    
    
@csrf_exempt
def handle_message(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
        
        statuses = (
            body.get("entry", [{}])[0].
            get("changes", [{}])[0].
            get("value", {}).
            get("statuses", [])
        )
        if statuses:
            logging.info("Recived a WhatsApp status update")
            return Response({"status":"ok"}, status=200)
        
        try:
            if is_valid_whatsapp_message(body):
                process_whatsapp_message(body, request)
                return Response({"status":"message_successful"}, status=200)
            else:
                return Response({
                    "status":"error",
                    "message": "Not a WhatsApp API event"
                }, status= 404)
        except json.JSONDecodeError:
            logging.error("Failed to decode JSON")
            return Response({"status":"error",
                             "message":"Invalid Json provided"})
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        return Response({"status": "error", "message": "Failed to process message"}, status=400)

def verify(request):
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
            logging.info("WEBHOOK_VERIFIED")
            return HttpResponse(challenge, status=200)
        else:
            logging.info("VERIFICATION_FAILED")
            print(f"mode: {mode} - token: {token}")
            print(f"whatsapp_token: {settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN}")
            return JsonResponse({"status": "error", "message": "Verification failed"}, status=403)
    else:
        logging.info("MISSING_PARAMETER")
        return JsonResponse({"status": "error", "message": "Missing parameters"}, status=400)

phonenumber = "2349126709734"
message = "Hello there governor, \n This our first test..."

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting WhatsApp message sender...") 
    payload = json.loads(get_text_message_input(phonenumber, message))
    ans = send_whatsapp_messages(payload)
    if ans.get("status") == "success":
        print("Message sent successfully!")
    else:
        print("Failed to send message:", ans.get("error", "Unknown error"))