from django.shortcuts import render, HttpResponse
from rest_framework.views import APIView
from settings.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response


# Create your views here.
class HomeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        
        return HttpResponse('Welcome to our app message us through this number: +1 555 630 8775')
    
    
class WebhookView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # Verify the webhook
        if request.GET.get('hub.mode') == 'subscribe' and request.GET.get('hub.verify_token') == settings.WEBHOOK_VERIFY_TOKEN:
            return Response({'message':request.GET.get('hub.challenge')}, status=status.HTTP_200_OK)
        else:
            return Response({'message':'Verification failed'}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        # Handle incoming messages here
        data1 = request.body
        data2 = request.data
        data_load = json.loads(data1)
        data_load1 = json.load(data2) 
        print(f"data_load: {data_load}")
        print(f"data_load1: {data_load1}")
        data_load1 = json.load(data2) 
        # if "object" in data1 and "entry" in data1:
        #     if data1["object"] == "abeg work":
        #         try:
        #             for entry in data1["entry"]:
        #                 phonenumber = entry['changes'][0]['value']['metadata']['display_phone_number']
        #                 phonenumber = "2349126709734"
        
        return Response({'Message received': data_load1,
                         'Raw data': data_load}, status=status.HTTP_200_OK)