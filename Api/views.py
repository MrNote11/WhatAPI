from django.shortcuts import render, HttpResponse
from rest_framework.views import APIView
from django.conf import settings
import logging
from .decorators_security.security import signature_required
import json
from .utils.sendmessage import *
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from twilio.rest import Client
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.messaging_response import MessagingResponse

# Create your views here.
class HomeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return HttpResponse('Welcome to our app message us through this number: +1 555 630 8775')
        

class TwilioWhatsAppMessageBodyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        account_sid = settings.TWILIO_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            to="whatsapp:+2349126709734",
            from_="whatsapp:+14155238886",
            body="Welcome to MyApp"
        )
        print(message.body)

        return Response({"message": message.body})



class TwilioWhatsAppWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Log the incoming webhook data
        print("WhatsApp webhook received:", request.data)

        # Create Twilio XML response
        response = MessagingResponse()
        twilio_msg = "Webhook received successfully!"
        response.message(twilio_msg)

        # Return TwiML as an XML HTTP response
        return HttpResponse(response.to_xml(), content_type='application/xml')
        


class FacebookWebhookView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return verify_webhook(request)
    
    @csrf_exempt
    @method_decorator(signature_required)
    def post(self, request):
        return handle_message(request)


# Flow endpoint for handling Flow interactions
@csrf_exempt  
@require_http_methods(["POST"])
def flow_endpoint(request):
    """
    Handle WhatsApp Flow interactions and validations
    """
    try:
        # Parse the request body
        body = json.loads(request.body.decode("utf-8"))
        
        # Extract flow data
        flow_token = body.get("flow_token", "")
        screen = body.get("screen", "")
        data = body.get("data", {})
        action = body.get("action", "")
        
        logger.info(f"Flow interaction: screen={screen}, action={action}")
        
        if screen == "amount_selection_screen":
            if action == "data_exchange":
                # Return the flow screen configuration
                return JsonResponse({
                    "version": "3.0",
                    "screen": "amount_selection_screen",
                    "data": {
                        "preset_amounts": [
                            {"value": "100", "label": "₦100"},
                            {"value": "200", "label": "₦200"},
                            {"value": "500", "label": "₦500"},
                            {"value": "1000", "label": "₦1,000"},
                            {"value": "2000", "label": "₦2,000"},
                            {"value": "5000", "label": "₦5,000"}
                        ],
                        "min_amount": 50,
                        "max_amount": 50000,
                        "currency": "₦",
                        "network": data.get("network", "")
                    }
                })
            elif action == "INIT":
                # Initialize the flow
                return JsonResponse({
                    "version": "3.0",
                    "screen": "amount_selection_screen",
                    "data": data
                })
        
        # Default response for unknown actions
        return JsonResponse({
            "version": "3.0",
            "screen": screen,
            "data": data
        })
        
    except Exception as e:
        logger.error(f"Error in flow endpoint: {str(e)}")
        return JsonResponse({
            "error": "Internal server error"
        }, status=500)

    # def post(self, request):
    #     # Handle incoming messages here
    #     data1 = request.body
    #     data2 = request.data
    #     data_load = json.loads(data1)
    #     data_load1 = json.load(data2) 
    #     print(f"data_load: {data_load}")
    #     print(f"data_load1: {data_load1}")
    #     data_load1 = json.load(data2) 
    #     # if "object" in data1 and "entry" in data1:
    #     #     if data1["object"] == "abeg work":
    #     #         try:
    #     #             for entry in data1["entry"]:
    #     #                 phonenumber = entry['changes'][0]['value']['metadata']['display_phone_number']
    #     #                 phonenumber = "2349126709734"
        
    #     return Response({'Message received': data_load1,
    #                      'Raw data': data_load}, status=status.HTTP_200_OK) 