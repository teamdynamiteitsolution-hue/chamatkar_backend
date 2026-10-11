from django.urls import path
from . import views

urlpatterns = [
    path('translator/translate', views.translate_single, name='translate_single'),
    path('translator/translate/', views.translate_single, name='translate_single_slash'),
    path('translator/batch', views.translate_batch, name='translate_batch'),
    path('translator/batch/', views.translate_batch, name='translate_batch_slash'),
    path('translator/status', views.translator_status, name='translator_status'),
    path('translator/status/', views.translator_status, name='translator_status_slash'),
]
