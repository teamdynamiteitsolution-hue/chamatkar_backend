from django.urls import path
from . import views

urlpatterns = [
    path('ai/assistant', views.ai_assistant_view, name='ai_assistant'),
]
