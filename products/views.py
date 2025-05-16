import random
from .forms import ReviewForm
from django.urls import reverse
from django.contrib import messages
from accounts.models import Cart, CartItem
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from products.models import Product, SizeVariant, ProductReview, Wishlist
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie


# Hiển thị chi tiết sản phẩm
@ensure_csrf_cookie
def get_product(request, slug):
    product = get_object_or_404(Product, slug=slug)
    sorted_size_variants = product.size_variant.all().order_by('size_name')
    related_products = list(product.category.products.filter(parent=None).exclude(uid=product.uid))

    # Tính tỷ lệ đánh giá
    rating_percentage = 0
    if product.reviews.exists():
        rating_percentage = (product.get_rating() / 5) * 100

    # Xử lý đánh giá từ người dùng
    if request.method == 'POST' and request.user.is_authenticated:
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Review added successfully!")
            return redirect('products:get_product', slug=slug)
        else:
            messages.warning(request, "Invalid review content. Please check your input.")
    else:
        review_form = ReviewForm()

    # Lọc sản phẩm liên quan
    if len(related_products) >= 4:
        related_products = random.sample(related_products, 4)

    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    # Context dữ liệu truyền vào template
    context = {
        'product': product,
        'sorted_size_variants': sorted_size_variants,
        'related_products': related_products,
        'review_form': review_form,
        'rating_percentage': rating_percentage,
        'in_wishlist': in_wishlist,
    }

    # Cập nhật giá khi người dùng chọn kích cỡ
    if request.GET.get('size'):
        size = request.GET.get('size')
        price = product.get_product_price_by_size(size)
        context['selected_size'] = size
        context['updated_price'] = price

    return render(request, 'product/product.html', context=context)


# Hiển thị các đánh giá của người dùng
@csrf_protect
@login_required
def product_reviews(request):
    reviews = ProductReview.objects.filter(
        user=request.user).select_related('product').order_by('-date_added')
    return render(request, 'product/all_product_reviews.html', {'reviews': reviews})


# Chỉnh sửa đánh giá
@csrf_protect
@login_required
def edit_review(request, review_uid):
    review = ProductReview.objects.filter(uid=review_uid, user=request.user).first()
    if not review:
        return JsonResponse({"detail": "Review not found"}, status=404)

    if request.method == "POST":
        stars = request.POST.get("stars")
        content = request.POST.get("content")
        review.stars = stars
        review.content = content
        review.save()
        messages.success(request, "Your review has been updated successfully.")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    return JsonResponse({"detail": "Invalid request"}, status=400)


# Thích đánh giá
@csrf_protect
@login_required
def like_review(request, review_uid):
    review = ProductReview.objects.filter(uid=review_uid).first()

    if request.user in review.likes.all():
        review.likes.remove(request.user)
    else:
        review.likes.add(request.user)
        review.dislikes.remove(request.user)
    return JsonResponse({'likes': review.like_count(), 'dislikes': review.dislike_count()})


# Không thích đánh giá
@csrf_protect
@login_required
def dislike_review(request, review_uid):
    review = ProductReview.objects.filter(uid=review_uid).first()

    if request.user in review.dislikes.all():
        review.dislikes.remove(request.user)
    else:
        review.dislikes.add(request.user)
        review.likes.remove(request.user)
    return JsonResponse({'likes': review.like_count(), 'dislikes': review.dislike_count()})


# Xóa đánh giá
@csrf_protect
@login_required
def delete_review(request, slug, review_uid):
    if not request.user.is_authenticated:
        messages.warning(request, "You need to be logged in to delete a review.")
        return redirect('accounts:login')

    review = ProductReview.objects.filter(uid=review_uid, product__slug=slug, user=request.user).first()

    if not review:
        messages.error(request, "Review not found.")
        return redirect('products:get_product', slug=slug)

    review.delete()
    messages.success(request, "Your review has been deleted.")
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


# Thêm sản phẩm vào Wishlist
@csrf_protect
@login_required
def add_to_wishlist(request, uid):
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'error',
                'message': 'Vui lòng đăng nhập để thêm vào yêu thích'
            }, status=401)

        product = get_object_or_404(Product, uid=uid)
        
        # Kiểm tra sản phẩm có tồn tại không
        if not product:
            return JsonResponse({
                'status': 'error',
                'message': 'Không tìm thấy sản phẩm'
            }, status=404)
            
        # Kiểm tra sản phẩm có còn hoạt động không
        if not product.stock > 0:
            return JsonResponse({
                'status': 'error',
                'message': 'Sản phẩm này hiện không còn bán'
            }, status=400)

        wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
        
        if wishlist_item:
            # Nếu sản phẩm đã có trong wishlist thì xóa đi
            wishlist_item.delete()
            message = "Đã xóa khỏi danh sách yêu thích"
            in_wishlist = False
        else:
            try:
                # Nếu chưa có thì thêm vào
                Wishlist.objects.create(user=request.user, product=product)
                message = "Đã thêm vào danh sách yêu thích"
                in_wishlist = True
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Không thể thêm vào danh sách yêu thích'
                }, status=500)
        
        # Lấy tổng số lượng wishlist của user
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': message,
                'in_wishlist': in_wishlist,
                'wishlist_count': wishlist_count
            })
        
        messages.success(request, message)
        return redirect(request.META.get('HTTP_REFERER', reverse('products:wishlist')))
        
    except Product.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Không tìm thấy sản phẩm'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'Có lỗi xảy ra, vui lòng thử lại sau'
        }, status=500)


# Xóa sản phẩm khỏi Wishlist
@csrf_protect
@login_required
def remove_from_wishlist(request, uid):
    product = get_object_or_404(Product, uid=uid)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    messages.success(request, "Sản phẩm đã được xóa khỏi Wishlist!")
    return redirect(reverse('products:wishlist'))


# Hiển thị Wishlist
@ensure_csrf_cookie
@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'product/wishlist.html', {'wishlist_items': wishlist_items})


# Chuyển sản phẩm từ Wishlist vào Cart
@csrf_protect
@login_required
def move_to_cart(request, uid):
    product = get_object_or_404(Product, uid=uid)
    wishlist = Wishlist.objects.filter(user=request.user, product=product).first()

    if not wishlist:
        messages.error(request, "Không tìm thấy sản phẩm trong Wishlist.")
        return redirect('products:wishlist')

    cart, created = Cart.objects.get_or_create(user=request.user, is_paid=False)
    
    # Tìm tất cả CartItem có cùng sản phẩm
    cart_items = CartItem.objects.filter(cart=cart, product=product)
    
    if cart_items.exists():
        # Nếu đã có CartItem, cộng số lượng vào item đầu tiên và xóa các item trùng
        cart_item = cart_items.first()
        cart_item.quantity += 1
        cart_item.save()
        # Xóa các CartItem trùng lặp khác
        cart_items.exclude(uid=cart_item.uid).delete()
    else:
        # Nếu chưa có CartItem nào, tạo mới
        CartItem.objects.create(cart=cart, product=product, quantity=1)

    wishlist.delete()
    messages.success(request, "Sản phẩm đã được chuyển vào giỏ hàng!")
    return redirect('accounts:cart')


def product_list(request):
    products = Product.objects.filter(parent=None).order_by('-created_at')
    
    # Phân trang
    paginator = Paginator(products, 12)  # 12 sản phẩm mỗi trang
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    return render(request, 'product/product_list.html', {
        'products': products,
    })
