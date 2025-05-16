from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.db.models.functions import ExtractMonth, ExtractYear, ExtractQuarter
from accounts.models import OrderItem, Order
from datetime import datetime
import calendar

@staff_member_required
def sales_dashboard(request):
    # Lấy năm và tháng hiện tại
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Thống kê theo sản phẩm bán chạy
    best_selling_products = OrderItem.objects.values(
        'product__product_name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('product_price')
    ).order_by('-total_quantity')[:10]

    # Thống kê theo tháng trong năm hiện tại
    monthly_sales = Order.objects.filter(
        created_at__year=current_year
    ).annotate(
        month=ExtractMonth('created_at')
    ).values('month').annotate(
        total_sales=Sum('grand_total'),
        order_count=Count('uid')
    ).order_by('month')

    # Thống kê theo quý
    quarterly_sales = Order.objects.filter(
        created_at__year=current_year
    ).annotate(
        quarter=ExtractQuarter('created_at')
    ).values('quarter').annotate(
        total_sales=Sum('grand_total'),
        order_count=Count('uid')
    ).order_by('quarter')

    # Thống kê theo năm
    yearly_sales = Order.objects.annotate(
        year=ExtractYear('created_at')
    ).values('year').annotate(
        total_sales=Sum('grand_total'),
        order_count=Count('uid')
    ).order_by('-year')[:5]  # 5 năm gần nhất

    context = {
        'best_selling_products': best_selling_products,
        'monthly_sales': monthly_sales,
        'quarterly_sales': quarterly_sales,
        'yearly_sales': yearly_sales,
        'current_year': current_year,
        'months': [calendar.month_name[i] for i in range(1, 13)],
    }
    
    return render(request, 'analytics/dashboard.html', context)
