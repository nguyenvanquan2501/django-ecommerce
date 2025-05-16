from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),

    # Home app (namespace 'home')
    path('', include(('home.urls', 'home'), namespace='home')),

    # Products app (namespace 'products')
    path('product/', include(('products.urls', 'products'), namespace='products')),

    # Accounts app (namespace 'accounts')
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),

    # Analytics app (namespace 'analytics')
    path('analytics/', include(('analytics.urls', 'analytics'), namespace='analytics')),

    # Social Auth URLs
    path('social-auth/', include('social_django.urls', namespace='social')),
    path('accounts/', include('allauth.urls')),
]

# Serve media files in DEBUG mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve static files
urlpatterns += staticfiles_urlpatterns()
