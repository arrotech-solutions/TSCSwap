from django.urls import path
from . import views
from .whatsapp_integration import whatsapp_webhook

app_name = 'chat'

urlpatterns = [
    path('send/', views.chat_view, name='send_message'),
    path('webhook/whatsapp/', whatsapp_webhook, name='whatsapp_webhook'),
]
