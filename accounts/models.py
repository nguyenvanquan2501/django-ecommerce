# accounts/models.py

import os
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

from base.models import BaseModel
from products.models import Product, ColorVariant, SizeVariant


class Profile(BaseModel):
    user              = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    is_email_verified = models.BooleanField(default=False)
    email_token       = models.CharField(max_length=100, null=True, blank=True)
    profile_image     = models.ImageField(upload_to='profile', null=True, blank=True)
    bio               = models.TextField(null=True, blank=True)

    shipping_address = models.ForeignKey(
        "accounts.ShippingAddress",
        on_delete=models.CASCADE,
        related_name="profiles",
        null=True,
        blank=True
    )

    def __str__(self):
        return self.user.username

    def get_cart_count(self):
        # import tại runtime để tránh circular
        from .models import CartItem
        return CartItem.objects.filter(
            cart__is_paid=False,
            cart__user=self.user
        ).count()

    def save(self, *args, **kwargs):
        # Xóa ảnh cũ nếu có thay đổi
        if self.pk:
            try:
                old = Profile.objects.get(pk=self.pk)
                if old.profile_image and old.profile_image != self.profile_image:
                    old_path = os.path.join(settings.MEDIA_ROOT, old.profile_image.path)
                    if os.path.exists(old_path):
                        os.remove(old_path)
            except Profile.DoesNotExist:
                pass

        super(Profile, self).save(*args, **kwargs)


class Cart(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="cart",
        null=True,
        blank=True
    )
    coupon = models.ForeignKey(
        "products.Coupon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    additional_coupons = models.ManyToManyField(
        'products.Coupon',
        related_name='additional_carts',
        blank=True
    )
    is_paid = models.BooleanField(default=False)
    vnpay_transaction_no = models.CharField(max_length=100, null=True, blank=True)
    vnpay_response_code = models.CharField(max_length=2, null=True, blank=True)
    vnpay_secure_hash = models.CharField(max_length=256, null=True, blank=True)

    def get_cart_total(self):
        """Tính tổng tiền giỏ hàng trước khi áp dụng mã giảm giá"""
        total = sum(item.get_product_price() for item in self.cart_items.all())
        return max(total, 0)  # Đảm bảo không âm

    def get_total_discount(self):
        """Tính tổng giảm giá từ tất cả coupon"""
        total_discount = 0
        if self.coupon:
            total_discount += self.coupon.discount_amount
        total_discount += sum(coupon.discount_amount for coupon in self.additional_coupons.all())
        return total_discount

    def get_cart_total_price_after_coupon(self):
        """Tính tổng tiền sau khi áp dụng mã giảm giá"""
        total = self.get_cart_total()
        discount = self.get_total_discount()
        return max(total - discount, 0)  # Đảm bảo không âm

    def __str__(self):
        return f"Cart {self.uid} - User: {self.user.username if self.user else 'Anonymous'}"


class CartItem(BaseModel):
    cart          = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cart_items")
    product       = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    color_variant = models.ForeignKey(ColorVariant, on_delete=models.SET_NULL, null=True, blank=True)
    size_variant  = models.ForeignKey(SizeVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity      = models.IntegerField(default=1, validators=[MinValueValidator(1)])

    def clean(self):
        if self.quantity < 1:
            raise ValidationError("Số lượng sản phẩm không được nhỏ hơn 1")
        if self.product and self.quantity > self.product.stock:
            raise ValidationError(f"Số lượng vượt quá tồn kho (còn {self.product.stock} sản phẩm)")

    def get_unit_price(self):
        price = self.product.price if self.product else 0
        if self.color_variant:
            price += self.color_variant.price
        if self.size_variant:
            price += self.size_variant.price
        return max(price, 0)

    def get_product_price(self):
        return self.get_unit_price() * self.quantity

    def adjust_quantity(self, new_quantity):
        """Điều chỉnh số lượng sản phẩm theo quy tắc:
        - Nếu số lượng < 1: về 1
        - Nếu số lượng > tồn kho: về tồn kho
        """
        if not self.product:
            return 1
            
        try:
            new_qty = int(new_quantity)
            if new_qty < 1:
                return 1
            if new_qty > self.product.stock:
                return self.product.stock
            return new_qty
        except (ValueError, TypeError):
            return 1

    def save(self, *args, **kwargs):
        # Luôn đảm bảo số lượng hợp lệ trước khi lưu
        self.quantity = self.adjust_quantity(self.quantity)
        self.clean()  # Kiểm tra validation
        super().save(*args, **kwargs)


class Order(BaseModel):
    STATUS_CHOICES = (
        ('pending', 'Chờ xác nhận'),
        ('confirmed', 'Đã xác nhận'),
        ('shipping', 'Đang giao hàng'),
        ('completed', 'Đã hoàn thành'),
        ('cancelled', 'Đã hủy'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Chờ thanh toán'),
        ('completed', 'Đã thanh toán'),
        ('failed', 'Thanh toán thất bại'),
        ('refunded', 'Đã hoàn tiền'),
    )
    PAYMENT_METHOD_CHOICES = (
        ('cod', 'Thanh toán khi nhận hàng'),
        ('vnpay', 'Thanh toán qua VNPay'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders"
    )
    order_id = models.CharField(max_length=100, unique=True)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cod'
    )
    shipping_address = models.ForeignKey(
        "accounts.ShippingAddress",
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders'
    )
    order_note = models.TextField(blank=True, null=True)
    order_total_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon = models.ForeignKey(
        "accounts.Coupon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Thông tin thanh toán VNPay
    vnpay_transaction_no = models.CharField(max_length=100, null=True, blank=True)
    vnpay_transaction_status = models.CharField(max_length=20, null=True, blank=True)
    vnpay_payment_date = models.DateTimeField(null=True, blank=True)
    vnpay_secure_hash = models.CharField(max_length=256, null=True, blank=True)

    def __str__(self):
        return f"Đơn hàng {self.order_id} của {self.user.username}"

    def get_order_total_price(self):
        return max(self.order_total_price, 0)

    def get_grand_total(self):
        return max(self.grand_total, 0)

    def get_status_display_class(self):
        status_classes = {
            'pending': 'warning',
            'confirmed': 'info',
            'shipping': 'primary',
            'completed': 'success',
            'cancelled': 'danger'
        }
        return status_classes.get(self.status, 'secondary')

    def get_payment_status_display_class(self):
        status_classes = {
            'pending': 'warning',
            'completed': 'success', 
            'failed': 'danger',
            'refunded': 'info'
        }
        return status_classes.get(self.payment_status, 'secondary')

    def has_deleted_products(self):
        """Kiểm tra xem đơn hàng có sản phẩm nào đã bị xóa không"""
        return self.order_items.filter(product__isnull=True).exists()

    @property
    def payment_mode(self):
        """Compatibility property for templates"""
        return self.get_payment_method_display()


class OrderItem(BaseModel):
    order         = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    product       = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    
    # Thông tin sản phẩm được lưu lại
    product_name = models.CharField(max_length=255, null=True)
    product_image = models.ImageField(upload_to='order_items', null=True, blank=True)
    product_description = models.TextField(null=True)
    
    size_variant  = models.ForeignKey(SizeVariant, on_delete=models.SET_NULL, null=True, blank=True)
    size_name = models.CharField(max_length=50, null=True, blank=True)  # Lưu tên size
    size_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Lưu giá size
    
    color_variant = models.ForeignKey(ColorVariant, on_delete=models.SET_NULL, null=True, blank=True)
    color_name = models.CharField(max_length=50, null=True, blank=True)  # Lưu tên màu
    color_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Lưu giá màu
    
    quantity      = models.PositiveIntegerField(default=1)
    product_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    def save(self, *args, **kwargs):
        # Lưu thông tin sản phẩm khi tạo mới OrderItem
        if self.product and not self.product_name:
            self.product_name = self.product.product_name
            self.product_description = self.product.product_description
            if self.product.product_images.exists():
                # Lưu ảnh đầu tiên của sản phẩm
                first_image = self.product.product_images.first()
                if first_image and first_image.image:
                    # Tạo bản sao của ảnh
                    from django.core.files.base import ContentFile
                    from django.core.files.storage import default_storage
                    import os
                    
                    # Tạo tên file mới
                    original_name = os.path.basename(first_image.image.name)
                    new_name = f'order_items/{self.uid}_{original_name}'
                    
                    # Sao chép file ảnh
                    if default_storage.exists(new_name):
                        default_storage.delete(new_name)
                    default_storage.save(new_name, ContentFile(first_image.image.read()))
                    self.product_image = new_name

        # Lưu thông tin variant
        if self.size_variant and not self.size_name:
            self.size_name = self.size_variant.size_name
            self.size_price = self.size_variant.price

        if self.color_variant and not self.color_name:
            self.color_name = self.color_variant.color_name
            self.color_price = self.color_variant.price

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_name if self.product_name else 'Deleted Product'} ({self.quantity})"

    def get_total_price(self):
        if self.product_price:
            return self.product_price * self.quantity
        return 0

    def get_product_image_url(self):
        if self.product_image:
            return self.product_image.url
        elif self.product and self.product.product_images.exists():
            return self.product.product_images.first().image.url
        return None  # Hoặc trả về URL ảnh mặc định


class Coupon(BaseModel):
    coupon_code     = models.CharField(max_length=10)
    is_expired      = models.BooleanField(default=False)
    discount_amount = models.IntegerField(default=100)
    minimum_amount  = models.IntegerField(default=500)

    def __str__(self):
        return self.coupon_code


class City(BaseModel):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Cities"

class District(BaseModel):
    name = models.CharField(max_length=100)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='districts')
    
    def __str__(self):
        return f"{self.name} - {self.city.name}"

class Ward(BaseModel):
    name = models.CharField(max_length=100)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='wards')
    
    def __str__(self):
        return f"{self.name} - {self.district.name}"

class ShippingAddress(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shipping_addresses')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    street = models.CharField(max_length=200)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True)
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True)
    phone = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.street}, {self.ward}, {self.district}, {self.city}"

    def save(self, *args, **kwargs):
        if self.is_default:
            # Đặt tất cả các địa chỉ khác của user thành không mặc định
            ShippingAddress.objects.filter(user=self.user).update(is_default=False)
        super().save(*args, **kwargs)
