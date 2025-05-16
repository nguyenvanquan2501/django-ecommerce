from django.urls import path
from .views import (
    register_view,
    login_view,
    logout_view,
    profile_view,
    password_change_view,
    cart,
    add_to_cart,
    update_cart_item,
    remove_cart,
    remove_coupon,
    order_history,
    order_details,
    delete_account,
    add_to_wishlist_from_cart,
    shipping_address_list,
    shipping_address_add,
    shipping_address_edit,
    shipping_address_delete,
    shipping_address_set_default,
    initiate_payment,
    vnpay_return,
    checkout,
    payment_success,
    apply_coupon,
    statistics_view,
    view_invoice,
)

app_name = 'accounts'

urlpatterns = [
    # Đăng ký / Đăng nhập / Đăng xuất
    path('register/', register_view, name='register'),
    path('login/',    login_view,    name='login'),
    path('logout/',   logout_view,   name='logout'),

    # Hồ sơ cá nhân
    path('profile/<str:username>/', profile_view, name='profile'),

    # Đổi mật khẩu
    path('password-change/', password_change_view, name='password_change'),

    # Giỏ hàng
    path('cart/',                 cart,              name='cart'),
    path('cart/add/<str:uid>/',   add_to_cart,       name='add_to_cart'),
    path('cart/update/',          update_cart_item,  name='update_cart_item'),
    path('update-cart-item/',     update_cart_item,  name='update_cart_item'),
    path('cart/remove/<str:uid>/', remove_cart,       name='remove_cart'),
    path('cart/coupon/remove/<int:cart_id>/', remove_coupon, name='remove_coupon'),
    path('cart/coupon/apply/', apply_coupon, name='apply_coupon'),
    path('cart/add-to-wishlist/<str:uid>/', add_to_wishlist_from_cart, name='add_to_wishlist_from_cart'),

    # Đơn hàng
    path('orders/history/', order_history, name='order_history'),
    path('orders/<str:order_id>/', order_details, name='order_details'),
    path('orders/<str:order_id>/invoice/', view_invoice, name='view_invoice'),

    # Địa chỉ giao hàng
    path('addresses/', shipping_address_list, name='shipping_address_list'),
    path('addresses/add/', shipping_address_add, name='shipping_address_add'),
    path('addresses/<str:pk>/edit/', shipping_address_edit, name='shipping_address_edit'),
    path('addresses/<str:pk>/delete/', shipping_address_delete, name='shipping_address_delete'),
    path('addresses/<str:pk>/set-default/', shipping_address_set_default, name='shipping_address_set_default'),

    # Xóa tài khoản
    path('account/delete/',       delete_account,    name='delete_account'),

    # Thanh toán
    path('checkout/', checkout, name='checkout'),
    path('payment/initiate/', initiate_payment, name='initiate_payment'),
    path('payment/vnpay-return/', vnpay_return, name='vnpay_return'),
    path('payment/success/<str:order_id>/', payment_success, name='payment_success'),

    # Thống kê
    path('statistics/', statistics_view, name='statistics'),
]
