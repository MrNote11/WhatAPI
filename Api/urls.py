from django.urls import path, include
from . import views

app_name = 'home'
urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('6c8c4825-dcba-4eec-be36-9bb19da00871', views.WebhookView.as_view(), name='webhook'),
]

#6c8c4825-dcba-4eec-be36-9bb19da00871 # This is the webhook URL that you will set in your WhatsApp Business API settings.
#b83eb537-1571-48a1-a78e-f10283965a83 #This is a verify token that you can use to verify the webhook.