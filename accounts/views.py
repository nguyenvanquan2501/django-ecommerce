import os
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_protect
from products.models import Product, Wishlist
from accounts.models import Profile, Cart, CartItem, Order, OrderItem, ShippingAddress, District, Ward, City
from accounts.forms import (
    UserUpdateForm,
    UserProfileForm,
    ShippingAddressForm,
    CustomPasswordChangeForm,
)
import json
from django.core.cache import cache
from .utils import get_client_ip, create_vnpay_url, verify_vnpay_response
import uuid
from datetime import datetime
import pytz
from django.utils import timezone
from products.models import Coupon
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth, TruncDay
from datetime import timedelta
from django.core.exceptions import ValidationError


@csrf_protect
def register_view(request):
    if request.method == 'POST':
        username   = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name  = request.POST.get('last_name')
        email      = request.POST.get('email')
        password   = request.POST.get('password')

        # Kiểm tra tồn tại
        if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
            messages.info(request, 'Tên đăng nhập hoặc email đã tồn tại!')
            return HttpResponseRedirect(request.path_info)

        # Tạo user
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email
        )
        user.set_password(password)
        user.save()

        # Không cần tạo Profile tại đây vì signal đã lo rồi
        messages.success(request, "Tài khoản của bạn đã được tạo thành công!")
        return redirect('accounts:login')

    return render(request, 'accounts/register.html')

@csrf_protect
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, "Đăng nhập thành công!")
            return redirect("home:index")
        else:
            messages.warning(request, "Tên đăng nhập hoặc mật khẩu không chính xác.")

    return render(request, "accounts/login.html")


@login_required
def logout_view(request):
    logout(request)
    messages.warning(request, "Đã đăng xuất thành công!")
    return redirect('accounts:login')


@login_required
def profile_view(request, username):
    user_obj = get_object_or_404(User, username=username)
    profile = get_object_or_404(Profile, user=user_obj)

    if request.method == 'POST':
        if 'update_image' in request.POST:
            # Xử lý cập nhật ảnh đại diện
            if request.FILES.get('profile_image'):
                # Xóa ảnh cũ nếu có
                if profile.profile_image:
                    if os.path.exists(profile.profile_image.path):
                        os.remove(profile.profile_image.path)
                # Lưu ảnh mới
                profile.profile_image = request.FILES['profile_image']
                profile.save()
                messages.success(request, 'Ảnh đại diện đã được cập nhật!')
            return redirect('accounts:profile', username=user_obj.username)
            
        elif 'update_profile' in request.POST:
            # Xử lý cập nhật thông tin
            user_form = UserUpdateForm(request.POST, instance=user_obj)
            profile_form = UserProfileForm(request.POST, instance=profile)
            
            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                messages.success(request, 'Thông tin cá nhân đã được cập nhật!')
                return redirect('accounts:profile', username=user_obj.username)
            else:
                messages.warning(request, 'Vui lòng sửa lỗi trong biểu mẫu.')
    else:
        user_form = UserUpdateForm(instance=user_obj)
        profile_form = UserProfileForm(instance=profile)

    return render(request, 'accounts/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })


@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, 'Mật khẩu của bạn đã được thay đổi!')
            return redirect('accounts:profile', username=request.user.username)
        else:
            messages.warning(request, 'Vui lòng sửa lỗi dưới đây.')
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def cart(request):
    cart = Cart.objects.filter(is_paid=False, user=request.user).first()
    
    if cart:
        # Thêm thông tin wishlist cho mỗi sản phẩm trong giỏ hàng
        for cart_item in cart.cart_items.all():
            try:
                cart_item.product.in_wishlist = Wishlist.objects.filter(
                    user=request.user, 
                    product=cart_item.product
                ).exists()
            except Exception:
                # Nếu có lỗi khi kiểm tra wishlist, mặc định là False
                cart_item.product.in_wishlist = False
    
    context = {
        'cart': cart
    }
    return render(request, 'accounts/cart.html', context)


@login_required
def add_to_cart(request, uid):
    try:
        product = get_object_or_404(Product, uid=uid)
        
        # Kiểm tra tồn kho
        if product.stock <= 0:
            messages.error(request, "Sản phẩm đã hết hàng!")
            return redirect(request.META.get('HTTP_REFERER', 'products:product_list'))
            
        size = request.GET.get('size')
        
        try:
            quantity = int(request.GET.get('quantity', 1))
            if quantity < 1:
                messages.error(request, "Số lượng sản phẩm không được nhỏ hơn 1!")
                return redirect(request.META.get('HTTP_REFERER', 'products:product_list'))
        except (ValueError, TypeError):
            messages.error(request, "Số lượng không hợp lệ!")
            return redirect(request.META.get('HTTP_REFERER', 'products:product_list'))

        if quantity > product.stock:
            messages.error(request, f"Chỉ còn {product.stock} sản phẩm trong kho!")
            return redirect(request.META.get('HTTP_REFERER', 'products:product_list'))
        
        cart, _ = Cart.objects.get_or_create(user=request.user, is_paid=False)
        
        # Tìm CartItem với cùng product và size
        cart_item = CartItem.objects.filter(
            cart=cart,
            product=product,
            size_variant__size_name=size if size else None
        ).first()
        
        if cart_item:
            # Kiểm tra tổng số lượng sau khi thêm
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.stock:
                messages.error(
                    request, 
                    f"Tổng số lượng ({new_quantity}) vượt quá số lượng trong kho ({product.stock})!"
                )
                return redirect('accounts:cart')
                
            cart_item.quantity = new_quantity
            try:
                cart_item.full_clean()  # Validate trước khi lưu
                cart_item.save()
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect('accounts:cart')
        else:
            # Tạo mới CartItem
            cart_item = CartItem(
                cart=cart,
                product=product,
                quantity=quantity
            )
            
            if size:
                size_variant = product.size_variant.filter(size_name=size).first()
                if size_variant:
                    cart_item.size_variant = size_variant
            
            try:
                cart_item.full_clean()  # Validate trước khi lưu
                cart_item.save()
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect('accounts:cart')
        
        messages.success(request, f"Đã thêm {quantity} {product.product_name} vào giỏ hàng!")
        return redirect('accounts:cart')
        
    except Exception as e:
        messages.error(request, f"Có lỗi xảy ra: {str(e)}")
        return redirect('accounts:cart')


@csrf_protect
@login_required
def update_cart_item(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cart_item_id = data.get('cart_item_id')
            quantity = int(data.get('quantity', 1))
            action = data.get('action', 'update')
            
            cart_item = get_object_or_404(CartItem, uid=cart_item_id, cart__user=request.user)
            
            # Kiểm tra số lượng
            if quantity < 1:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Số lượng không được nhỏ hơn 1'
                })
            
            if quantity > cart_item.product.stock:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Chỉ còn {cart_item.product.stock} sản phẩm trong kho'
                })
            
            # Cập nhật số lượng
            cart_item.quantity = quantity
            cart_item.save()
            
            # Tính toán các giá trị mới
            item_total = cart_item.get_product_price()
            cart_total = cart_item.cart.get_cart_total()
            cart_total_with_coupon = cart_item.cart.get_cart_total_price_after_coupon()
            
            return JsonResponse({
                'status': 'success',
                'quantity': cart_item.quantity,
                'item_total': item_total,
                'cart_total': cart_total,
                'cart_total_with_coupon': cart_total_with_coupon
            })
                
        except CartItem.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Không tìm thấy sản phẩm trong giỏ hàng'
            })
        except (ValueError, TypeError):
            return JsonResponse({
                'status': 'error',
                'message': 'Số lượng không hợp lệ'
            })
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Dữ liệu không hợp lệ'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Phương thức không được hỗ trợ'
    })


@csrf_protect
@login_required
def remove_cart(request, uid):
    cart_item = get_object_or_404(CartItem, uid=uid, cart__user=request.user, cart__is_paid=False)
    cart_item.delete()
    messages.success(request, 'Đã xóa sản phẩm khỏi giỏ hàng.')
    return redirect('accounts:cart')


@csrf_protect
@login_required
def remove_coupon(request, coupon_id):
    cart = get_object_or_404(Cart, user=request.user, is_paid=False)
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if cart.coupon == coupon:
        cart.coupon = None
        cart.save()
    else:
        cart.additional_coupons.remove(coupon)
    
    messages.success(request, 'Đã xóa mã giảm giá.')
    return redirect('accounts:cart')


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    return render(request, 'accounts/order_history.html', {'orders': orders})


@login_required
def order_details(request, order_id):
    try:
        order = get_object_or_404(Order, order_id=order_id)
        
        # Kiểm tra quyền xem đơn hàng
        if not request.user.is_staff and order.user != request.user:
            messages.error(request, 'Bạn không có quyền xem đơn hàng này!')
            return redirect('accounts:order_history')
            
        order_items = order.order_items.select_related(
            'product', 
            'size_variant',
            'color_variant'
        ).all()
        
        # Kiểm tra và thông báo nếu có sản phẩm đã bị xóa
        if order.has_deleted_products():
            messages.warning(
                request, 
                'Một số sản phẩm trong đơn hàng này đã bị xóa khỏi hệ thống.'
            )
        
        context = {
            'order': order,
            'order_items': order_items,
        }
        return render(request, 'accounts/order_details.html', context)
        
    except Order.DoesNotExist:
        messages.error(request, 'Không tìm thấy đơn hàng!')
        return redirect('accounts:order_history')
    except Exception as e:
        messages.error(request, f'Có lỗi xảy ra: {str(e)}')
        return redirect('accounts:order_history')


@csrf_protect
@login_required
def delete_account(request):
    user = request.user
    logout(request)
    user.delete()
    messages.success(request, 'Tài khoản của bạn đã được xóa.')
    return redirect('home:index')


@csrf_protect
@login_required
def add_to_wishlist_from_cart(request, uid):
    try:
        cart_item = CartItem.objects.get(uid=uid)
        product = cart_item.product

        # Kiểm tra xem sản phẩm đã có trong wishlist chưa
        wishlist_exists = Wishlist.objects.filter(
            user=request.user,
            product=product
        ).exists()

        if wishlist_exists:
            messages.warning(request, 'Sản phẩm đã có trong danh sách yêu thích!')
        else:
            # Thêm vào wishlist
            Wishlist.objects.create(
                user=request.user,
                product=product
            )
            messages.success(request, 'Đã thêm sản phẩm vào danh sách yêu thích!')

    except CartItem.DoesNotExist:
        messages.error(request, 'Không tìm thấy sản phẩm trong giỏ hàng!')
    except Exception as e:
        messages.error(request, 'Có lỗi xảy ra khi thêm vào danh sách yêu thích!')

    return redirect('accounts:cart')


@login_required
def shipping_address_list(request):
    addresses = ShippingAddress.objects.filter(user=request.user)\
        .select_related('city', 'district', 'ward')\
        .order_by('-is_default', '-created_at')
    return render(request, 'accounts/shipping_address_list.html', {'addresses': addresses})

@csrf_protect
@login_required
def shipping_address_add(request):
    if request.method == 'POST':
        form = ShippingAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            
            # Tự động set city là Hà Nội
            hanoi = City.objects.filter(name__icontains='Hà Nội').first()
            if hanoi:
                address.city = hanoi
            
            # Nếu là địa chỉ đầu tiên hoặc được chọn làm mặc định
            if not ShippingAddress.objects.filter(user=request.user).exists() or form.cleaned_data['is_default']:
                # Đặt tất cả địa chỉ khác thành không mặc định
                ShippingAddress.objects.filter(user=request.user).update(is_default=False)
                address.is_default = True
                
            address.save()
            messages.success(request, 'Đã thêm địa chỉ mới thành công!')
            return redirect('accounts:shipping_address_list')
    else:
        form = ShippingAddressForm()

    return render(request, 'accounts/shipping_address_form.html', {
        'form': form,
        'title': 'Thêm địa chỉ mới'
    })

@csrf_protect
@login_required
def shipping_address_edit(request, pk):
    address = get_object_or_404(ShippingAddress, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = ShippingAddressForm(request.POST, instance=address)
        if form.is_valid():
            # Tự động set city là Hà Nội
            hanoi = City.objects.filter(name__icontains='Hà Nội').first()
            if hanoi:
                form.instance.city = hanoi
                
            # Nếu đang edit địa chỉ mặc định hoặc được chọn làm mặc định
            if address.is_default or form.cleaned_data['is_default']:
                # Đặt tất cả địa chỉ khác thành không mặc định
                ShippingAddress.objects.filter(user=request.user).exclude(pk=pk).update(is_default=False)
                form.instance.is_default = True
                
            form.save()
            messages.success(request, 'Đã cập nhật địa chỉ thành công!')
            return redirect('accounts:shipping_address_list')
    else:
        form = ShippingAddressForm(instance=address)

    return render(request, 'accounts/shipping_address_form.html', {
        'form': form,
        'title': 'Chỉnh sửa địa chỉ',
        'address': address
    })

@csrf_protect
@login_required
def shipping_address_delete(request, pk):
    address = get_object_or_404(ShippingAddress, pk=pk, user=request.user)
    address.delete()
    messages.success(request, 'Đã xóa địa chỉ thành công!')
    return redirect('accounts:shipping_address_list')

@csrf_protect
@login_required
def shipping_address_set_default(request, pk):
    address = get_object_or_404(ShippingAddress, pk=pk, user=request.user)
    address.is_default = True
    address.save()
    messages.success(request, 'Đã đặt địa chỉ mặc định thành công!')
    return redirect('accounts:shipping_address_list')

@csrf_protect
@login_required
def initiate_payment(request):
    cart = get_object_or_404(Cart, user=request.user, is_paid=False)
    
    if not cart.cart_items.exists():
        messages.error(request, "Giỏ hàng của bạn đang trống!")
        return redirect('accounts:cart')

    # Tạo mã đơn hàng
    order_id = str(uuid.uuid4().int)[:10]
    
    # Tạo thông tin đơn hàng
    order_info = f"Thanh toan don hang #{order_id}"
    
    # Lấy tổng tiền từ giỏ hàng
    total_amount = cart.get_cart_total_price_after_coupon()
    
    # Lấy IP của khách hàng
    client_ip = get_client_ip(request)
    
    # Tạo URL thanh toán VNPay
    payment_url = create_vnpay_url(
        order_id=order_id,
        total_amount=total_amount,
        order_info=order_info,
        client_ip=client_ip
    )
    
    # Lưu mã đơn hàng vào session để kiểm tra khi VNPay callback
    request.session['vnpay_order_id'] = order_id
    
    return redirect(payment_url)

@csrf_protect
@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user, is_paid=False)
    
    if not cart.cart_items.exists():
        messages.error(request, "Giỏ hàng của bạn đang trống!")
        return redirect('accounts:cart')
    
    # Lấy địa chỉ giao hàng mặc định hoặc địa chỉ đầu tiên
    shipping_address = ShippingAddress.objects.filter(
        user=request.user, is_default=True
    ).first() or ShippingAddress.objects.filter(user=request.user).first()

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        shipping_address_id = request.POST.get('shipping_address')
        order_note = request.POST.get('order_note', '')

        if not shipping_address_id:
            messages.error(request, "Vui lòng chọn địa chỉ giao hàng!")
            return redirect('accounts:checkout')

        shipping_address = get_object_or_404(ShippingAddress, uid=shipping_address_id, user=request.user)
        
        # Tạo mã đơn hàng
        order_id = str(uuid.uuid4().int)[:10]
        
        # Tính phí vận chuyển (có thể thay đổi logic theo yêu cầu)
        shipping_fee = 30000  # VNĐ
        
        # Tạo đơn hàng
        order = Order.objects.create(
            user=request.user,
            order_id=order_id,
            shipping_address=shipping_address,
            order_note=order_note,
            payment_method=payment_method,
            order_total_price=cart.get_cart_total(),
            shipping_fee=shipping_fee,
            coupon=cart.coupon,
            grand_total=cart.get_cart_total_price_after_coupon() + shipping_fee,
            status='pending',
            payment_status='pending'
        )

        # Chuyển các sản phẩm từ giỏ hàng sang đơn hàng
        for cart_item in cart.cart_items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                size_variant=cart_item.size_variant,
                color_variant=cart_item.color_variant,
                quantity=cart_item.quantity,
                product_price=cart_item.get_product_price()
            )

        if payment_method == 'vnpay':
            # Tạo URL thanh toán VNPay
            order_info = f"Thanh toan don hang #{order_id}"
            client_ip = get_client_ip(request)
            payment_url = create_vnpay_url(
                order_id=order_id,
                total_amount=order.grand_total,
                order_info=order_info,
                client_ip=client_ip
            )
            
            # Lưu mã đơn hàng vào session
            request.session['vnpay_order_id'] = order_id
            
            return redirect(payment_url)
        else:  # COD
            # Cập nhật trạng thái đơn hàng COD
            order.status = 'confirmed'  # Đơn hàng đã xác nhận
            order.save()
            
            # Đánh dấu giỏ hàng đã thanh toán
            cart.is_paid = True
            cart.save()
            
            messages.success(request, "Đặt hàng thành công! Cảm ơn bạn đã mua hàng.")
            return redirect('accounts:payment_success', order_id=order.order_id)

    shipping_addresses = ShippingAddress.objects.filter(user=request.user)
    
    context = {
        'cart': cart,
        'shipping_addresses': shipping_addresses,
        'default_address': shipping_address,
    }
    
    return render(request, 'accounts/checkout.html', context)

@login_required
def vnpay_return(request):
    # Lấy thông tin từ VNPay trả về
    response_data = request.GET.dict()
    
    # Kiểm tra tính hợp lệ của response
    if not verify_vnpay_response(response_data):
        messages.error(request, "Thông tin thanh toán không hợp lệ!")
        return redirect('accounts:cart')
    
    # Lấy thông tin thanh toán
    vnp_response_code = response_data.get('vnp_ResponseCode')
    vnp_transaction_no = response_data.get('vnp_TransactionNo')
    vnp_amount = int(response_data.get('vnp_Amount', 0)) / 100  # Chuyển về VNĐ
    vnp_payment_date = datetime.fromtimestamp(
        int(response_data.get('vnp_PayDate', '0')) / 1000,
        tz=pytz.timezone('Asia/Ho_Chi_Minh')
    )
    
    # Kiểm tra mã đơn hàng
    order_id = response_data.get('vnp_TxnRef')
    session_order_id = request.session.get('vnpay_order_id')
    
    if order_id != session_order_id:
        messages.error(request, "Mã đơn hàng không khớp!")
        return redirect('accounts:cart')
    
    # Xóa mã đơn hàng khỏi session
    del request.session['vnpay_order_id']
    
    # Lấy đơn hàng
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    # Lấy giỏ hàng
    cart = get_object_or_404(Cart, user=request.user, is_paid=False)
    
    if vnp_response_code == '00':
        # Thanh toán thành công
        # Cập nhật thông tin đơn hàng
        order.status = 'confirmed'  # Đơn hàng đã xác nhận
        order.payment_status = 'completed'  # Thanh toán đã hoàn thành
        order.vnpay_transaction_no = vnp_transaction_no
        order.vnpay_transaction_status = vnp_response_code
        order.vnpay_payment_date = vnp_payment_date
        order.vnpay_secure_hash = response_data.get('vnp_SecureHash')
        order.save()
        
        # Đánh dấu giỏ hàng đã thanh toán
        cart.is_paid = True
        cart.save()
        
        messages.success(request, "Thanh toán thành công!")
        return redirect('accounts:payment_success', order_id=order.order_id)
    else:
        # Thanh toán thất bại
        order.payment_status = 'failed'  # Thanh toán thất bại
        order.save()
        
        messages.error(request, "Thanh toán thất bại! Vui lòng thử lại sau.")
        return redirect('accounts:cart')

@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    return render(request, 'accounts/payment_success.html', {'order': order})

@csrf_protect
@login_required
def apply_coupon(request):
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code')
        if not coupon_code:
            messages.error(request, 'Vui lòng nhập mã giảm giá!')
            return redirect('accounts:cart')

        cart = get_object_or_404(Cart, user=request.user, is_paid=False)
        
        try:
            # Kiểm tra mã giảm giá có tồn tại và còn hiệu lực
            coupon = Coupon.objects.get(
                coupon_code=coupon_code,
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now()
            )
            
            # Kiểm tra giá trị đơn hàng có đủ điều kiện
            cart_total = cart.get_cart_total()
            if cart_total < coupon.minimum_amount:
                messages.error(
                    request, 
                    f'Giá trị đơn hàng tối thiểu để sử dụng mã giảm giá là {coupon.minimum_amount:,} VNĐ!'
                )
                return redirect('accounts:cart')
            
            # Kiểm tra coupon đã được sử dụng chưa
            if cart.coupon == coupon or cart.additional_coupons.filter(id=coupon.id).exists():
                messages.error(request, 'Mã giảm giá này đã được sử dụng!')
                return redirect('accounts:cart')
            
            # Thêm coupon vào giỏ hàng
            if not cart.coupon:
                cart.coupon = coupon
                cart.save()
            else:
                cart.additional_coupons.add(coupon)
            
            # Kiểm tra tổng tiền sau khi áp dụng coupon có bị âm không
            if cart.get_cart_total_price_after_coupon() < 0:
                if cart.coupon == coupon:
                    cart.coupon = None
                    cart.save()
                else:
                    cart.additional_coupons.remove(coupon)
                messages.error(request, 'Không thể áp dụng mã giảm giá này vì sẽ làm tổng tiền bị âm!')
                return redirect('accounts:cart')
            
            messages.success(
                request, 
                f'Áp dụng mã giảm giá thành công! Bạn được giảm {coupon.discount_amount:,} VNĐ'
            )
            
        except Coupon.DoesNotExist:
            messages.error(request, 'Mã giảm giá không hợp lệ hoặc đã hết hạn!')
            
    return redirect('accounts:cart')

@login_required
def statistics_view(request):
    # Lấy thời gian hiện tại
    now = timezone.now()
    
    # Thống kê theo tháng (6 tháng gần nhất)
    monthly_stats = Order.objects.filter(
        order_date__gte=now - timedelta(days=180),
        payment_status='completed'
    ).annotate(
        month=TruncMonth('order_date')
    ).values('month').annotate(
        total_orders=Count('id'),
        total_revenue=Sum('grand_total')
    ).order_by('month')

    # Thống kê theo ngày (30 ngày gần nhất)
    daily_stats = Order.objects.filter(
        order_date__gte=now - timedelta(days=30),
        payment_status='completed'
    ).annotate(
        day=TruncDay('order_date')
    ).values('day').annotate(
        total_orders=Count('id'),
        total_revenue=Sum('grand_total')
    ).order_by('day')

    # Thống kê theo phương thức thanh toán
    payment_stats = Order.objects.filter(
        payment_status='completed'
    ).values('payment_method').annotate(
        total_orders=Count('id'),
        total_revenue=Sum('grand_total')
    )

    context = {
        'monthly_stats': monthly_stats,
        'daily_stats': daily_stats,
        'payment_stats': payment_stats,
    }
    
    return render(request, 'accounts/statistics.html', context)

@login_required
def view_invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    items = OrderItem.objects.filter(order=order)
    context = {
        'order': order,
        'items': items
    }
    return render(request, 'accounts/invoice.html', context)
