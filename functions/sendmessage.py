from django.conf import settings
import requests
import logging
import json
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import re


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

    return response.json()




def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def generate_response(response):
    # Return text in uppercase
    return response.upper()


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


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_body = message["text"]["body"]

    # TODO: implement custom function here
    response = generate_response(message_body)

    # OpenAI Integration
    # response = generate_response(message_body, wa_id, name)
    # response = process_text_for_whatsapp(response)

    data = get_text_message_input(settings.WHATSAPP_RECIPIENT_NUMBER_ID, response)
    send_whatsapp_messages(data)


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
                process_whatsapp_message(body)
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
        return Response({"status": "error", "message": "Failed to process message"}), 400


def verify(request):
    # Parse params from the webhook verification request
    mode = request.POST.get("hub.mode")
    token = request.POST.get("hub.verify_token")
    challenge = request.POST.get("hub.challenge")
    # Check if a token and mode were sent
    if mode and token:
        # Check the mode and token sent are correct
        if mode == "subscribe" and token == settings.WEBHOOK_VERIFY_TOKEN:
            # Respond with 200 OK and challenge token from the request
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            # Responds with '403 Forbidden' if verify tokens do not match
            logging.info("VERIFICATION_FAILED")
            return Response({"status": "error", "message": "Verification failed"}), 403
    else:
        # Responds with '400 Bad Request' if verify tokens do not match
        logging.info("MISSING_PARAMETER")
        return Response({"status": "error", "message": "Missing parameters"}), 400

phonenumber = "2349126709734"
message = "Hello there governor, \n This our first test..."

ans = send_whatsapp_messages(phonenumber, message)