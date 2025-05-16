from django.urls import path
from home import views

app_name = 'home'

urlpatterns = [
    path('', views.index, name="index"),
    path('search/', views.product_search, name='product_search'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('terms-and-conditions/', views.terms_and_conditions, name='terms-and-conditions'),
    path('privacy-policy/', views.privacy_policy, name='privacy-policy'),
    path('shipping-address/', views.shipping_address, name='shipping-address'),

    # Các URL cho tài khoản và giỏ hàng (nếu chưa include từ accounts)
    path('order-history/', views.order_history, name='order_history'),
    path('cart/', views.cart_view, name='cart'),
    path('login/', views.login_view, name='login'),
]
