from django.urls import path
from .views import user_login_or_register, user_profile, customer_orders

urlpatterns = [
    path('users/auth', user_login_or_register, name='user_auth'),
    path('users/auth/', user_login_or_register, name='user_auth_slash'),
    path('users/<str:phone>/orders', customer_orders, name='customer_orders'),
    path('users/<str:phone>/orders/', customer_orders, name='customer_orders_slash'),
    path('users/<str:phone>', user_profile, name='user_profile'),
    path('users/<str:phone>/', user_profile, name='user_profile_slash'),
]
