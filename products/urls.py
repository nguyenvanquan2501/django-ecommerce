from django.urls import path
from . import views

urlpatterns = [
    # Hiển thị danh sách sản phẩm
    path('', views.product_list, name='product_list'),

    # Hiển thị chi tiết sản phẩm
    path('product/<slug:slug>/', views.get_product, name='get_product'),

    # Hiển thị tất cả các đánh giá của người dùng
    path('reviews/', views.product_reviews, name='product_reviews'),

    # Chỉnh sửa đánh giá
    path('review/edit/<str:review_uid>/', views.edit_review, name='edit_review'),

    # Thích đánh giá
    path('review/like/<str:review_uid>/', views.like_review, name='like_review'),

    # Không thích đánh giá
    path('review/dislike/<str:review_uid>/', views.dislike_review, name='dislike_review'),

    # Xóa đánh giá
    path('review/delete/<str:slug>/<str:review_uid>/', views.delete_review, name='delete_review'),

    # Thêm sản phẩm vào Wishlist
    path('wishlist/add/<str:uid>/', views.add_to_wishlist, name='add_to_wishlist'),

    # Xóa sản phẩm khỏi Wishlist
    path('wishlist/remove/<str:uid>/', views.remove_from_wishlist, name='remove_from_wishlist'),

    # Hiển thị Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),

    # Chuyển sản phẩm từ Wishlist vào Cart
    path('wishlist/move_to_cart/<str:uid>/', views.move_to_cart, name='move_to_cart'),
]
