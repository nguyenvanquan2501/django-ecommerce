from django.contrib import admin
from django.core.exceptions import ValidationError
from .models import Category, Coupon, Product, ProductImage, ColorVariant, SizeVariant, ProductReview
from django import forms
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

# Hàm kiểm tra giá và số lượng không âm
def validate_positive_price(value):
    if value < 0:
        raise ValidationError("Giá phải lớn hơn hoặc bằng 0, không được âm.")

def validate_positive_quantity(value):
    if value < 0:
        raise ValidationError("Số lượng phải lớn hơn hoặc bằng 0, không được âm.")

# Đăng ký các model: Category
admin.site.register(Category)

class CouponAdminForm(forms.ModelForm):
    valid_from = forms.DateTimeField(
        label='Thời gian bắt đầu',
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'vDateTime'
            },
            format='%Y-%m-%dT%H:%M'
        )
    )
    
    valid_to = forms.DateTimeField(
        label='Thời gian kết thúc',
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'vDateTime'
            },
            format='%Y-%m-%dT%H:%M'
        )
    )

    class Meta:
        model = Coupon
        fields = '__all__'
        widgets = {
            'coupon_code': forms.TextInput(attrs={
                'placeholder': 'Nhập mã giảm giá (ít nhất 3 ký tự)'
            }),
            'discount_amount': forms.NumberInput(attrs={
                'placeholder': 'Nhập số tiền giảm giá'
            }),
            'minimum_amount': forms.NumberInput(attrs={
                'placeholder': 'Nhập số tiền tối thiểu'
            }),
            'quantity': forms.NumberInput(attrs={
                'placeholder': 'Nhập số lượng (0 = không giới hạn)'
            })
        }

    def clean_coupon_code(self):
        code = self.cleaned_data.get('coupon_code')
        if not code:
            raise forms.ValidationError("Vui lòng nhập mã giảm giá")
        if len(code) < 3:
            raise forms.ValidationError("Mã giảm giá phải có ít nhất 3 ký tự")
        return code.upper()  # Chuyển mã thành chữ hoa

    def clean_discount_amount(self):
        amount = self.cleaned_data.get('discount_amount')
        if amount is None:
            raise forms.ValidationError("Vui lòng nhập số tiền giảm giá")
        if amount < 0:
            raise forms.ValidationError("Số tiền giảm giá không được âm")
        return amount

    def clean_minimum_amount(self):
        amount = self.cleaned_data.get('minimum_amount')
        if amount is None:
            raise forms.ValidationError("Vui lòng nhập số tiền tối thiểu")
        if amount < 0:
            raise forms.ValidationError("Số tiền tối thiểu không được âm")
        return amount

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is None:
            raise forms.ValidationError("Vui lòng nhập số lượng")
        if quantity < 0:
            raise forms.ValidationError("Số lượng không được âm (0 = không giới hạn)")
        return quantity

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        
        if not valid_from:
            raise forms.ValidationError({
                'valid_from': "Vui lòng nhập thời gian bắt đầu"
            })
        if not valid_to:
            raise forms.ValidationError({
                'valid_to': "Vui lòng nhập thời gian kết thúc"
            })
            
        if valid_from and valid_to and valid_from > valid_to:
            raise forms.ValidationError({
                'valid_to': "Thời gian kết thúc phải sau thời gian bắt đầu"
            })
            
        return cleaned_data

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    form = CouponAdminForm
    list_display = ['coupon_code', 'discount_amount', 'minimum_amount', 'quantity', 'used_count', 'is_active', 'valid_from', 'valid_to']
    list_filter = ['is_active']
    search_fields = ['coupon_code']
    readonly_fields = ['used_count']
    
    fieldsets = (
        ('Thông tin mã giảm giá', {
            'fields': ('coupon_code', 'discount_amount', 'minimum_amount', 'quantity', 'is_active'),
            'description': 'Nhập thông tin cơ bản của mã giảm giá'
        }),
        ('Thống kê sử dụng', {
            'fields': ('used_count',),
            'classes': ('collapse',),
            'description': 'Thống kê số lần sử dụng mã giảm giá'
        }),
        ('Thời gian hiệu lực', {
            'fields': ('valid_from', 'valid_to'),
            'description': 'Chọn thời gian bắt đầu và kết thúc từ lịch'
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Đang chỉnh sửa
            return self.readonly_fields + ('coupon_code',)
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        if obj.valid_from >= obj.valid_to:
            raise ValidationError("Thời gian bắt đầu phải trước thời gian kết thúc")
        if obj.discount_amount < 0:
            raise ValidationError("Số tiền giảm giá không được âm")
        if obj.minimum_amount < 0:
            raise ValidationError("Số tiền tối thiểu không được âm")
        super().save_model(request, obj, form, change)

# Class ProductImageAdmin để hiển thị hình ảnh sản phẩm
class ProductImageAdmin(admin.StackedInline):
    model = ProductImage
    extra = 1  # Số lượng hình ảnh mặc định cho mỗi sản phẩm

# Đảm bảo kiểm tra giá và số lượng trong ProductAdmin
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'price', 'category', 'stock', 'created_at', 'updated_at']
    list_filter = ['category']  # Lọc sản phẩm theo danh mục
    search_fields = ['product_name', 'product_description']  # Tìm kiếm theo tên và mô tả sản phẩm
    prepopulated_fields = {'slug': ('product_name',)}  # Tự động tạo slug từ tên sản phẩm
    inlines = [ProductImageAdmin]  # Cho phép thêm hình ảnh cho sản phẩm

    def save_model(self, request, obj, form, change):
        if obj.price < 0:
            raise ValidationError("Giá không được âm.")
        if obj.stock < 0:
            raise ValidationError("Số lượng sản phẩm không được âm.")
        super().save_model(request, obj, form, change)

@admin.register(ColorVariant)
class ColorVariantAdmin(admin.ModelAdmin):
    list_display = ['color_name', 'price']

    def save_model(self, request, obj, form, change):
        if obj.price < 0:
            raise ValidationError("Giá màu sắc không được âm.")
        super().save_model(request, obj, form, change)

@admin.register(SizeVariant)
class SizeVariantAdmin(admin.ModelAdmin):
    list_display = ['size_name', 'price', 'order']

    def save_model(self, request, obj, form, change):
        if obj.price < 0:
            raise ValidationError("Giá kích thước không được âm.")
        super().save_model(request, obj, form, change)

# Đăng ký các model còn lại
admin.site.register(ProductImage)
admin.site.register(ProductReview)
