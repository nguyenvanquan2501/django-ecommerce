from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from accounts.models import Profile, ShippingAddress, District, Ward, City


# Form cho phép người dùng cập nhật thông tin cá nhân
class UserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        label='Tên',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label='Họ',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name']

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name.replace(' ', '').isalpha():
            raise forms.ValidationError("Tên chỉ được chứa chữ cái")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name.replace(' ', '').isalpha():
            raise forms.ValidationError("Họ chỉ được chứa chữ cái")
        return last_name


# Form cho phép người dùng cập nhật mô tả
class UserProfileForm(forms.ModelForm):
    bio = forms.CharField(
        label='Giới thiệu',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Viết gì đó về bạn...'
        })
    )

    class Meta:
        model = Profile
        fields = ['bio']


# Form cập nhật địa chỉ giao hàng
class ShippingAddressForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = ['first_name', 'last_name', 'street', 'phone', 'is_default']
        labels = {
            'first_name': 'Tên',
            'last_name': 'Họ',
            'street': 'Địa chỉ đường',
            'phone': 'Số điện thoại',
            'is_default': 'Đặt làm địa chỉ mặc định'
        }
        widgets = {
            'street': forms.TextInput(attrs={'placeholder': 'Nhập địa chỉ đường'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Nhập số điện thoại'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Thêm class form-control cho tất cả các fields
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # Kiểm tra số điện thoại chỉ chứa số
        if not phone.isdigit():
            raise forms.ValidationError("Số điện thoại chỉ được chứa chữ số")
        # Kiểm tra độ dài số điện thoại
        if len(phone) != 10:
            raise forms.ValidationError("Số điện thoại phải có 10 chữ số")
        # Kiểm tra số điện thoại bắt đầu bằng 0
        if not phone.startswith('0'):
            raise forms.ValidationError("Số điện thoại phải bắt đầu bằng số 0")
        return phone

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name.replace(' ', '').isalpha():
            raise forms.ValidationError("Tên chỉ được chứa chữ cái")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name.replace(' ', '').isalpha():
            raise forms.ValidationError("Họ chỉ được chứa chữ cái")
        return last_name


# Form thay đổi mật khẩu
class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Mật khẩu hiện tại",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    new_password1 = forms.CharField(
        label="Mật khẩu mới",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    new_password2 = forms.CharField(
        label="Xác nhận mật khẩu mới",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
