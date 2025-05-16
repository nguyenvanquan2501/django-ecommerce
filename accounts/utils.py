import hashlib
import hmac
import urllib.parse
from django.conf import settings
from datetime import datetime
import pytz

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def hmacsha512(key, data):
    byteKey = key.encode('utf-8')
    byteData = data.encode('utf-8')
    return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()

def create_vnpay_url(order_id, total_amount, order_info, client_ip):
    # Cấu hình thông tin merchant
    vnp = {
        'vnp_Version': '2.1.0',
        'vnp_Command': 'pay',
        'vnp_TmnCode': settings.VNPAY_TMN_CODE,
        'vnp_Amount': int(total_amount * 100),  # Số tiền * 100 (VNĐ)
        'vnp_CurrCode': 'VND',
        'vnp_TxnRef': str(order_id),
        'vnp_OrderInfo': order_info,
        'vnp_OrderType': 'billpayment',
        'vnp_Locale': 'vn',
        'vnp_ReturnUrl': settings.VNPAY_RETURN_URL,
        'vnp_IpAddr': client_ip,
        'vnp_CreateDate': datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%Y%m%d%H%M%S')
    }

    # Sắp xếp các tham số theo thứ tự a-z
    sorted_params = sorted(vnp.items())
    
    # Tạo chuỗi ký tự cần mã hóa
    query_string = ''
    for key, value in sorted_params:
        if value:
            if query_string:
                query_string += '&'
            query_string += f"{key}={urllib.parse.quote_plus(str(value))}"

    # Tạo chuỗi mã hóa
    hmac_obj = hmac.new(
        settings.VNPAY_HASH_SECRET_KEY.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha512
    )
    vnp['vnp_SecureHash'] = hmac_obj.hexdigest()

    # Tạo URL thanh toán
    payment_url = f"{settings.VNPAY_PAYMENT_URL}?{query_string}&vnp_SecureHash={vnp['vnp_SecureHash']}"
    return payment_url

def verify_vnpay_response(response_data):
    # Tách secure hash từ response data
    secure_hash = response_data.pop('vnp_SecureHash', '')
    
    # Sắp xếp các tham số theo thứ tự a-z
    sorted_params = sorted(response_data.items())
    
    # Tạo chuỗi ký tự cần mã hóa
    query_string = ''
    for key, value in sorted_params:
        if value:
            if query_string:
                query_string += '&'
            query_string += f"{key}={urllib.parse.quote_plus(str(value))}"

    # Tạo chuỗi mã hóa để so sánh
    hmac_obj = hmac.new(
        settings.VNPAY_HASH_SECRET_KEY.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha512
    )
    calculated_hash = hmac_obj.hexdigest()

    # So sánh secure hash
    return secure_hash == calculated_hash 