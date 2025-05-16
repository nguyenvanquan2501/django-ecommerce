from django.db.models import Q
from django.shortcuts import render, redirect
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from products.models import Product, Category
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.forms import ShippingAddressForm
from accounts.models import ShippingAddress

# Trang chủ
def index(request):
    query = Product.objects.all().order_by('uid')
    categories = Category.objects.all()
    selected_sort = request.GET.get('sort')
    selected_category = request.GET.get('category')

    # Lọc theo danh mục nếu có
    if selected_category:
        query = query.filter(category__category_name=selected_category)

    # Lọc theo kiểu sắp xếp
    if selected_sort:
        if selected_sort == 'newest':
            query = query.filter(newest_product=True).order_by('category_id')
        elif selected_sort == 'priceAsc':
            query = query.order_by('price')
        elif selected_sort == 'priceDesc':
            query = query.order_by('-price')

    # Phân trang sản phẩm
    page = request.GET.get('page', 1)
    paginator = Paginator(query, 20)  # 20 sản phẩm trên mỗi trang
    
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    except Exception as e:
        print(f"Lỗi phân trang: {e}")
        products = paginator.page(1)  # Mặc định trang 1 nếu có lỗi

    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'selected_sort': selected_sort,
    }
    return render(request, 'home/index.html', context)


# Tìm kiếm sản phẩm
def product_search(request):
    query = request.GET.get('q', '')

    if query:
        # Tìm sản phẩm có tên chứa chuỗi tìm kiếm
        products = Product.objects.filter(
            Q(product_name__icontains=query) |
            Q(product_name__istartswith=query)
        )
    else:
        products = Product.objects.none()

    context = {'query': query, 'products': products}
    return render(request, 'home/search.html', context)


# Liên hệ
def contact(request):
    context = {"form_id": "xgvvlrvn"}
    return render(request, 'home/contact.html', context)


# Giới thiệu
def about(request):
    return render(request, 'home/about.html')


# Điều khoản sử dụng
def terms_and_conditions(request):
    return render(request, 'home/terms_and_conditions.html')


# Chính sách bảo mật
def privacy_policy(request):
    return render(request, 'home/privacy_policy.html')


# Trang Delivery / Shipping Address
@login_required
def shipping_address(request):
    shipping_addr = ShippingAddress.objects.get_or_create(user=request.user)[0]
    
    if request.method == 'POST':
        form = ShippingAddressForm(request.POST, instance=shipping_addr)
        if form.is_valid():
            addr = form.save(commit=False)
            addr.user = request.user
            addr.save()
            messages.success(request, 'Địa chỉ giao hàng đã được cập nhật!')
            return redirect('home:shipping-address')
    else:
        form = ShippingAddressForm(instance=shipping_addr)

    context = {
        'user': request.user,
        'form': form,
    }
    return render(request, 'accounts/shipping_address_form.html', context)


# Lịch sử đơn hàng (chuyển tiếp sang accounts)
def order_history(request):
    return render(request, 'accounts/order_history.html')


# Giỏ hàng (chuyển tiếp sang accounts)
def cart_view(request):
    return render(request, 'accounts/cart.html')


# Đăng nhập (chuyển tiếp sang accounts)
def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home:index')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})
