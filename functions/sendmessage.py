from django.conf import settings
import requests

def send_whatsapp_messages(phonenumber, message):
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
               "Content-Type": settings.WHATSAPP_CONTENT_TYPE }
        
    payload = {
        "messaging_product": "whatsapp",
        "to": phonenumber,  # e.g., "2349126709734"
        "type": "template",
        "template": {
            "name": "hello_world",  # ✅ Must match a real template
            "language": {
                "code": "en_US"
            }
        }
    }


    response = requests.post(settings.WHATSAPP_URL, json=payload, headers=headers)

    return response.json()


phonenumber = "2349126709734"
message = "Hello there governor, \n This our first test..."

ans = send_whatsapp_messages(phonenumber, message)