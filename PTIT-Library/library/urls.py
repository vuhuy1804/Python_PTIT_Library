from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from django.contrib import messages
from . import views

urlpatterns = [
    # Trang chủ
    path("", views.home, name="home"),

    path("collections/<int:sub_id>/", views.subcollection_books, name="subcollection_books"),
    
    # Sách
    path("books/", views.book_list, name="book_list"),

    #Chi tiết sách
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),

    # Mượn sách
    path("register/<int:book_id>/", views.register_borrow, name="register_borrow"),

    path("cancel/<int:borrow_id>/", views.cancel_borrow, name="cancel_borrow"),

    path("myborrows/", views.my_borrows, name="my_borrows"),

    # Đăng nhập
    path("login/", auth_views.LoginView.as_view(template_name="library/login.html"), name="login"),

    # Đăng xuất
    path("logout/", auth_views.LogoutView.as_view(next_page="/"), name="logout"),

    # Đổi mật khẩu
    path("password/change/", auth_views.PasswordChangeView.as_view(
        template_name="library/change_password.html",
        success_url="/",
        extra_context={'title': 'Đổi mật khẩu'}
    ), name="change_password"),

    # Notifications (AJAX)
    path('notifications/mark_all_read/', views.mark_all_read, name='mark_all_read'),
    
    path('notifications/<int:notif_id>/read/', views.read_notification, name='read_notification'),

    path('notifications/load_more/', views.load_more_notifications, name='load_more_notifications'),

    # Điểm danh
    path("attendance/qr/", views.attendance_qr_page, name="attendance_qr"),
    path("attendance/qr/generate/", views.generate_qr_code, name="generate_qr_code"),
    path("attendance/check/", views.attendance_check_code, name="attendance_check_code"),  # nhập mã điểm danh
    path("attendance/history/", views.attendance_history, name="attendance_history"),
    path("attendance/statistics/", views.attendance_statistics, name="attendance_statistics"),
    path("attendance/top/", views.attendance_top, name="attendance_top"),

]
