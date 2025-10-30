from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# --- Tùy chỉnh giao diện trang quản trị ---
admin.site.site_header = "QUẢN TRỊ THƯ VIỆN PTIT"
admin.site.site_title = "Quản trị Thư viện PTIT"
admin.site.index_title = "Trang quản trị hệ thống"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("library.urls")),  # gom route của app library vào
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

