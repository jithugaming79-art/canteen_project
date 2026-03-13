from django.urls import path
from . import views

urlpatterns = [
    path('chat/api/', views.chat_api, name='chat_api'),
]
