from django.shortcuts import render, HttpResponse
from rest_framework.views import APIView
from django.conf import settings
import logging
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
        

class WhatsAppMessageBodyView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        account_sid = settings.SID
        auth_token = settings.AUTHTOKEN
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            to="whatsapp:+2349126709734",
            from_="whatsapp:+14155238886",
            body="Welcome to MyApp"
        )
        print(message.body)

        return Response({"message": message.body})



class WhatsAppWebhookView(APIView):
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
        


@method_decorator(csrf_exempt, name='dispatch')
class FacebookWebhookView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        verify_token = settings.WEBHOOK_VERIFY_TOKEN
        mode = request.query_params.get('hub.mode')
        challenge = request.query_params.get('hub.challenge')
        token = request.query_params.get('hub.verify_token')

        print(f"Incoming GET: mode={mode}, token={token}, challenge={challenge}")
        print(f"Expected token: {verify_token}")
        logger = logging.getLogger(__name__)
        logger.info(f"Webhook GET called with token={token}")
        if mode == 'subscribe' and token == verify_token:
            return HttpResponse(challenge, content_type="text/plain", status=200)

        return HttpResponse("Verification failed", status=403)
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