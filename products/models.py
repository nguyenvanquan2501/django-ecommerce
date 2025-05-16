from django.db import models
from base.models import BaseModel
from django.utils.text import slugify
from django.utils.html import mark_safe
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime
import pytz
from django.utils import timezone
from django.core.exceptions import ValidationError

# Create your models here.


class Category(BaseModel):
    category_name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, null=True, blank=True)
    category_image = models.ImageField(upload_to="categories")

    def save(self, *args, **kwargs):
        self.slug = slugify(self.category_name)
        super(Category, self).save(*args, **kwargs)

    def __str__(self) -> str:
        return self.category_name


class ColorVariant(BaseModel):
    color_name = models.CharField(max_length=100)
    price = models.IntegerField(default=0, validators=[MinValueValidator(0)])  # Giá không âm

    def __str__(self) -> str:
        return self.color_name


class SizeVariant(BaseModel):
    size_name = models.CharField(max_length=100)
    price = models.IntegerField(default=0, validators=[MinValueValidator(0)])  # Giá không âm
    order = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    def __str__(self) -> str:
        return self.size_name


class Product(BaseModel):
    parent = models.ForeignKey(
        'self', related_name='variants', on_delete=models.CASCADE, blank=True, null=True)
    product_name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    price = models.IntegerField(validators=[MinValueValidator(0)])  # Giá không âm
    product_description = models.TextField()
    color_variant = models.ManyToManyField(ColorVariant, blank=True)
    size_variant = models.ManyToManyField(SizeVariant, blank=True)
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])  # Giá trị mặc định là 0 và không âm
    newest_product = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.product_name)
            slug = base_slug
            counter = 1
            # Kiểm tra xem slug đã tồn tại chưa
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super(Product, self).save(*args, **kwargs)

    def __str__(self) -> str:
        return self.product_name

    def get_product_price_by_size(self, size_name):
        try:
            size_variant = self.size_variant.get(size_name=size_name)
            return self.price + size_variant.price
        except SizeVariant.DoesNotExist:
            return self.price

    def get_order_count(self):
        """Đếm số đơn hàng có sản phẩm này"""
        from accounts.models import OrderItem
        return OrderItem.objects.filter(product=self).count()

    def get_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(review.stars for review in reviews) / len(reviews)
        return 0


class ProductImage(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_images')
    image = models.ImageField(upload_to='product')

    def img_preview(self):
        return mark_safe(f'<img src="{self.image.url}" width="500"/>')


def get_default_valid_to():
    return timezone.now() + timezone.timedelta(days=30)

class Coupon(BaseModel):
    coupon_code = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)
    discount_amount = models.IntegerField(default=100, validators=[MinValueValidator(0)])
    minimum_amount = models.IntegerField(default=500, validators=[MinValueValidator(0)])
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(0)])
    used_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    
    def __str__(self):
        return self.coupon_code
    
    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active 
            and self.valid_from <= now <= self.valid_to
            and (self.quantity == 0 or self.used_count < self.quantity)  # quantity = 0 means unlimited
        )

    def can_use(self):
        """Kiểm tra xem coupon còn có thể sử dụng không"""
        if not self.is_active:
            return False, "Mã giảm giá không còn hoạt động"
        
        now = timezone.now()
        if now < self.valid_from:
            return False, "Mã giảm giá chưa có hiệu lực"
        if now > self.valid_to:
            return False, "Mã giảm giá đã hết hạn"
            
        if self.quantity > 0 and self.used_count >= self.quantity:
            return False, "Mã giảm giá đã hết lượt sử dụng"
            
        return True, "Mã giảm giá hợp lệ"

    def use_coupon(self):
        """Đánh dấu coupon đã được sử dụng một lần"""
        if self.is_valid():
            self.used_count += 1
            if self.quantity > 0 and self.used_count >= self.quantity:
                self.is_active = False
            self.save()
            return True
        return False

    def clean(self):
        super().clean()
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValidationError("Thời gian kết thúc phải sau thời gian bắt đầu")


class ProductReview(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    stars = models.IntegerField(default=3, choices=[(i, i) for i in range(1, 6)], validators=[MinValueValidator(1), MaxValueValidator(5)])  # Rating từ 1 đến 5 sao
    content = models.TextField(blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name="liked_reviews", blank=True)
    dislikes = models.ManyToManyField(User, related_name="disliked_reviews", blank=True)

    def like_count(self):
        return self.likes.count()

    def dislike_count(self):
        return self.dislikes.count()


class Wishlist(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")
    added_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self) -> str:
        return f'{self.user.username} - {self.product.product_name}'
