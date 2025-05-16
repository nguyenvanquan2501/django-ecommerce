// Hàm lấy CSRF token
function getCSRFToken() {
    let csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    return csrftoken;
}

// Hàm hiển thị thông báo toast
function showToast(type, message) {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : 'danger'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Xóa toast sau khi ẩn
    toast.addEventListener('hidden.bs.toast', function () {
        document.body.removeChild(toast);
    });
}

// Hàm cập nhật trạng thái wishlist cho tất cả các nút có cùng product_id
function updateWishlistButtons(product_id, in_wishlist) {
    document.querySelectorAll(`.toggle-wishlist-btn[data-product-id="${product_id}"]`).forEach(btn => {
        const icon = btn.querySelector('i');
        
        if (in_wishlist) {
            icon.classList.add('text-danger');
            btn.setAttribute('title', 'Bỏ khỏi yêu thích');
            btn.setAttribute('data-bs-original-title', 'Bỏ khỏi yêu thích');
        } else {
            icon.classList.remove('text-danger');
            btn.setAttribute('title', 'Thêm vào yêu thích');
            btn.setAttribute('data-bs-original-title', 'Thêm vào yêu thích');
        }
        
        // Cập nhật tooltip nếu đang hiển thị
        const tooltip = bootstrap.Tooltip.getInstance(btn);
        if (tooltip) {
            tooltip.dispose();
            new bootstrap.Tooltip(btn);
        }
    });
}

// Hàm cập nhật số lượng wishlist trong header
function updateWishlistCount(count) {
    const wishlistCountElements = document.querySelectorAll('.wishlist-count');
    wishlistCountElements.forEach(element => {
        element.textContent = count;
        // Ẩn/hiện badge số lượng
        if (count > 0) {
            element.classList.remove('d-none');
        } else {
            element.classList.add('d-none');
        }
    });
}

// Hàm xử lý toggle wishlist
function toggleWishlist(button) {
    const url = button.getAttribute('href');
    const productId = button.getAttribute('data-product-id');
    const icon = button.querySelector('i');
    const isInWishlist = icon.classList.contains('text-danger');
    const loadingSpinner = document.createElement('span');
    loadingSpinner.className = 'spinner-border spinner-border-sm ms-1';
    
    // Disable nút trong khi đang xử lý
    button.disabled = true;
    if (icon) {
        icon.style.display = 'none';
    }
    button.appendChild(loadingSpinner);
    
    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            // Cập nhật trạng thái cho tất cả các nút của sản phẩm này
            updateWishlistButtons(productId, data.in_wishlist);
            
            // Cập nhật số lượng wishlist trong header
            updateWishlistCount(data.wishlist_count);
            
            // Hiển thị thông báo thành công
            showToast('success', data.message);
            
            // Nếu đang ở trang wishlist và xóa item, refresh để cập nhật UI
            if (window.location.pathname.includes('/wishlist/') && !data.in_wishlist) {
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            }
        } else {
            // Hiển thị thông báo lỗi
            showToast('error', data.message || 'Có lỗi xảy ra khi thực hiện thao tác');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('error', 'Có lỗi xảy ra, vui lòng thử lại sau');
    })
    .finally(() => {
        // Restore nút về trạng thái ban đầu
        button.disabled = false;
        if (icon) {
            icon.style.display = '';
        }
        loadingSpinner.remove();
    });
}

// Khởi tạo xử lý cho tất cả nút wishlist
document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Xử lý nút toggle wishlist
    document.addEventListener('click', function(e) {
        const wishlistBtn = e.target.closest('.toggle-wishlist-btn');
        if (wishlistBtn) {
            e.preventDefault();
            toggleWishlist(wishlistBtn);
        }
    });
}); 