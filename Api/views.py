from django.shortcuts import render, HttpResponse
from rest_framework.views import APIView
# Create your views here.
class HomeView(APIView):
    permission_classes = []

    def get(self, request):
        
        return HttpResponse('Welcome to our app message us through this number: +1 555 630 8775')