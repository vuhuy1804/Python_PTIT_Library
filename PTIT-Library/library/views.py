from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date, timedelta
from .models import Book, Borrow, Notification, Collection, SubCollection
from django.db.models import Q, Count
from django.core.paginator import Paginator
from unidecode import unidecode
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.utils.timezone import localtime
import random, io, qrcode, base64
from .models import EntryLog
from django.views.decorators.http import require_POST


def home(request):
    return render(request, 'library/home.html')

@login_required
def book_list(request):
    query = request.GET.get('q', '').strip()
    collections = Collection.objects.prefetch_related('subcollections').all().order_by('id')

    # ✅ Kiểm tra cảnh báo quá hạn (chỉ hiện 1 lần trong phiên)
    if request.user.is_authenticated:
        has_overdue = Borrow.objects.filter(
            user=request.user,
            status='Đang mượn',
            due_date__lt=timezone.now().date()
        ).exists()

        if has_overdue and not request.session.get('overdue_alert_shown', False):
            count = Borrow.objects.filter(
                user=request.user,
                status='Đang mượn',
                due_date__lt=timezone.now().date()
            ).count()
            messages.error(request, f"Bạn đang có {count} sách quá hạn! Hãy nhanh chóng đến thư viện trả sách!")
            request.session['overdue_alert_shown'] = True  # ✅ Đánh dấu đã hiển thị

    # Nếu người dùng tìm kiếm, hiển thị danh sách sách
    if query:
        normalized_query = unidecode(query).lower()
        books = [
            b for b in Book.objects.all()
            if normalized_query in unidecode(b.title).lower()
            or normalized_query in unidecode(b.author).lower()
        ]
        paginator = Paginator(books, 12)
        page_obj = paginator.get_page(request.GET.get('page'))
        return render(request, 'library/book_list.html', {
            'query': query,
            'page_obj': page_obj,
            'collections': None,
            'grid_view': True
        })

    # Nếu không có tìm kiếm → hiển thị bộ sưu tập
    return render(request, 'library/book_list.html', {
        'collections': collections,
        'query': query,
        'grid_view': True
    })


@login_required
def subcollection_books(request, sub_id):
    sub = get_object_or_404(SubCollection, id=sub_id)
    books = Book.objects.filter(subcollection=sub).order_by('title')

    paginator = Paginator(books, 6)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'library/collection_list.html', {
        'sub': sub,
        'page_obj': page_obj
    })

@login_required
def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    return render(request, 'library/book_detail.html', {'book': book})

@login_required
def register_borrow(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    # Kiểm tra số lượng sách còn hay không
    if book.quantity <= 0:
        messages.warning(request, f"Sách '{book.title}' hiện đang hết, vui lòng chọn sách khác.")
        return redirect('book_list')

    # Kiểm tra xem user đã có mượn hoặc đang chờ cuốn này chưa
    existing = Borrow.objects.filter(
        user=request.user,
        book=book,
        status__in=["Đang chờ", "Đang mượn"]
    ).exists()

    if existing:
        messages.warning(request, f"Bạn đang mượn hoặc đã đăng ký mượn sách '{book.title}' rồi!")
        return redirect('book_list')
    
    # Giới hạn 7 cuốn đang chờ hoặc đang mượn
    total_active = Borrow.objects.filter(
        user=request.user,
        status__in=["Đang chờ", "Đang mượn"]
    ).count()

    if total_active >= 7:
        messages.warning(request, "Bạn chỉ được mượn cùng lúc tối đa 7 cuốn.")
        return redirect('book_list')

    # Tạo yêu cầu mượn mới
    Borrow.objects.create(
        user=request.user,
        book=book,
        status="Đang chờ",
        due_date=None
    )

    messages.success(request, f"Đăng ký mượn sách '{book.title}' thành công! Hãy đến thư viện để hoàn tất thủ tục và nhận sách.")
    return redirect('book_list')

@login_required
def cancel_borrow(request, borrow_id):
    borrow = get_object_or_404(Borrow, id=borrow_id, user=request.user, status="Đang chờ")
    borrow.delete()
    messages.info(request, f"Đã huỷ yêu cầu mượn sách '{borrow.book.title}'.")
    return redirect('my_borrows')

@login_required
def my_borrows(request):
    pending = Borrow.objects.filter(user=request.user, status="Đang chờ")
    active = Borrow.objects.filter(user=request.user, status="Đang mượn")
    returned = Borrow.objects.filter(user=request.user, status="Đã trả")

    # Kiểm tra sách sắp hết hạn trong 7 ngày
    now = timezone.now().date()
    for borrow in active:
        if borrow.due_date and 0 <= (borrow.due_date - now).days <= 7:
            exists = Notification.objects.filter(
                user=request.user,
                title="Lưu ý!",
                message__icontains=borrow.book.title,
                is_read=False
            ).exists()
            if not exists:
                Notification.objects.create(
                    user=request.user,
                    title="Lưu ý!",
                    message=f"Sách '{borrow.book.title}' bạn đang mượn sẽ hết hạn vào ngày {borrow.due_date.strftime('%d/%m/%Y')}. "
                            "Hãy trả sách đúng hạn để tránh phí phạt."
                )

    overdue = [b for b in active if b.is_overdue()]

    for b in active:
        b.is_late = b.is_overdue()

    return render(request, 'library/my_borrows.html', {
        'pending': pending,
        'active': active,
        'returned': returned,
        'overdue': overdue,
        'count_pending': pending.count(),
        'count_active': active.count(),
        'count_returned': returned.count(),
        'count_overdue': len(overdue),
    })

# === THÔNG BÁO ===
@login_required
def mark_all_read(request):
    if request.method == 'POST':
        request.user.notifications.filter(is_read=False).update(is_read=True)
        return JsonResponse({'status': 'ok'})
    return redirect('home')

@login_required
def read_notification(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, user=request.user)
    notif.is_read = True
    notif.save()

    local_time = timezone.localtime(notif.created_at)
    
    return JsonResponse({
        'title': notif.title,
        'message': notif.message,
        'time': local_time.strftime("%d/%m/%Y %H:%M"),
    })

def notification_context(request):
    if request.user.is_authenticated:
        unread = Notification.objects.filter(user=request.user, is_read=False).count()
        recent = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
        return {'unread_notifications': unread, 'recent_notifications': recent}
    return {}

@login_required
def load_more_notifications(request):
    if not request.user.is_authenticated:
        return JsonResponse({'notifications': []})

    offset = int(request.GET.get('offset', 0))
    limit = 10

    notifications = (
        Notification.objects.filter(user=request.user)
        .order_by('-created_at')[offset:offset + limit]
    )

    data = []
    for n in notifications:
        data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message[:80],
            'is_read': n.is_read,
            'time': timezone.localtime(n.created_at).strftime("%d/%m/%Y %H:%M"),
        })

    return JsonResponse({'notifications': data})

# ✅ Trang hiển thị QR code và mã
@login_required
def attendance_qr_page(request):
    return render(request, "library/attendance_qr.html")

@login_required
def generate_qr_code(request):
    #chỉ admin mới dc xem link QR, cmt phần này để demo cho nhanh
    '''
    if not request.user.is_staff:
        messages.error(request, "Bạn không có quyền truy cập trang này.")
        return redirect("home")
    '''
    # Sinh mã ngẫu nhiên gồm 6 chữ số
    code = str(random.randint(100000, 999999))
    request.session['attendance_code'] = code  # lưu vào session (demo)
    request.session.modified = True

    # Sinh ảnh QR (nội dung là mã 6 số)
    qr = qrcode.make(code)
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    qr_data = base64.b64encode(buffer.getvalue()).decode()

    return JsonResponse({
        "code": code,
        "qr_image": f"data:image/png;base64,{qr_data}",
        "generated_at": timezone.localtime(timezone.now()).strftime("%H:%M:%S"),
    })

@login_required
def attendance_check_code(request):
    if request.method == "POST":
        input_code = request.POST.get("code")
        saved_code = request.session.get("attendance_code")

        if input_code != saved_code:
            messages.error(request, "Mã điểm danh không hợp lệ hoặc đã hết hạn.")
            return redirect("attendance_history")

        user = request.user
        now = timezone.localtime(timezone.now())
        shift = "Sáng" if now.hour < 12 else "Chiều"
        today = now.date()

        log, created = EntryLog.objects.get_or_create(user=user, shift=shift, check_in__date=today)

        if not log.check_in:
            log.check_in = now
            log.save()
            messages.success(request, f"Điểm danh vào {shift.lower()} thành công lúc {now.strftime('%H:%M:%S')}")
        elif not log.check_out:
            log.check_out = now
            log.save()
            messages.success(request, f"Điểm danh ra {shift.lower()} thành công lúc {now.strftime('%H:%M:%S')}")
        else:
            messages.info(request, "Bạn đã hoàn thành điểm danh buổi này.")

        return redirect("attendance_history")

    return render(request, 'library/attendance_check.html')


@login_required
def attendance_history(request):
    logs = EntryLog.objects.filter(user=request.user)

    # Lọc theo ngày
    start_date = request.GET.get("start")
    end_date = request.GET.get("end")
    if start_date:
        logs = logs.filter(check_in__date__gte=start_date)
    if end_date:
        logs = logs.filter(check_in__date__lte=end_date)

    paginator = Paginator(logs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "library/attendance_history.html", {
        "page_obj": page_obj,
        "start_date": start_date,
        "end_date": end_date,
        "total_count": logs.count()
    })

@login_required
def attendance_statistics(request):
    from django.db.models.functions import TruncMonth
    now = timezone.now()

    data = (
        EntryLog.objects.filter(user=request.user)
        .annotate(month=TruncMonth('check_in'))
        .values('month')
        .annotate(total=Count('id'))
        .order_by('-month')[:10]
    )

    # Chuẩn hóa dữ liệu cho biểu đồ
    labels = [d['month'].strftime("%m/%Y") for d in reversed(data)]
    values = [d['total'] for d in reversed(data)]

    return render(request, "library/attendance_statistics.html", {
        "labels": labels,
        "values": values
    })

@login_required
def attendance_top(request):
    data = (
        EntryLog.objects.values('user__username')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )
    labels = [d['user__username'] for d in data]
    values = [d['total'] for d in data]

    return render(request, "library/attendance_top.html", {
        "labels": labels,
        "values": values
    })
