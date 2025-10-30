from django.db import models
from django.contrib.auth.models import User
from django.db.models import F
from datetime import date
from dateutil.relativedelta import relativedelta
from django.utils import timezone
import uuid

class Collection(models.Model):
    """Bộ sưu tập chính (ví dụ: Bài giảng, Giáo trình, E-book...)"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Tên bộ sưu tập")
    image = models.ImageField(upload_to='collections/', blank=True, null=True, verbose_name="Ảnh đại diện")
    description = models.TextField(blank=True, verbose_name="Mô tả")

    class Meta:
        verbose_name = "Bộ sưu tập"
        verbose_name_plural = "Các bộ sưu tập"

    def __str__(self):
        return self.name


class SubCollection(models.Model):
    """Danh mục con bên trong mỗi bộ sưu tập (ví dụ: Khoa CNTT, Kế toán, v.v.)"""
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='subcollections', verbose_name="Bộ sưu tập")
    name = models.CharField(max_length=100, verbose_name="Tên danh mục con")

    class Meta:
        verbose_name = "Danh mục con"
        verbose_name_plural = "Các danh mục con"
        unique_together = ('collection', 'name')

    def __str__(self):
        return f"{self.collection.name} - {self.name}"

class Book(models.Model):
    title = models.CharField("Tên sách", max_length=200)
    author = models.CharField("Tác giả", max_length=100)
    quantity = models.IntegerField("Số lượng", default=1)
    cover = models.ImageField(upload_to='books/covers/', blank=True, null=True, verbose_name="Ảnh bìa")
    subcollection = models.ForeignKey(SubCollection, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Phân loại")
    publish_year = models.CharField("Năm xuất bản", max_length=200, default="2023")
    publisher = models.CharField("Nhà xuất bản", max_length=255, default="Học viện Công nghệ Bưu Chính Viễn Thông")
    pdf = models.FileField(upload_to='books/pdfs/', null=True, blank=True)

    class Meta:
        verbose_name = "Sách"
        verbose_name_plural = "Sách"

    def __str__(self):
        return f"{self.title} - {self.author}"
    
    @property
    def collection(self):
        """Truy cập nhanh đến bộ sưu tập cha"""
        return self.subcollection.collection if self.subcollection else None


class Borrow(models.Model):
    STATUS_CHOICES = [
        ("Đang chờ", "Đang chờ"),
        ("Đang mượn", "Đang mượn"),
        ("Đã trả", "Đã trả"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Người mượn")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="Sách")
    borrow_code = models.CharField(max_length=20, unique=True, verbose_name="Mã mượn")
    borrow_date = models.DateField(auto_now_add=True, verbose_name="Ngày mượn")
    due_date = models.DateField(null=True, blank=True, verbose_name="Hạn trả")
    return_date = models.DateField(null=True, blank=True, verbose_name="Ngày trả")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Đang chờ", verbose_name="Trạng thái")

    def __str__(self):
        return f"{self.borrow_code} - {self.book.title} ({self.status})"

    def is_overdue(self):
        return self.due_date and timezone.now().date() > self.due_date

    class Meta:
        verbose_name = "Lượt mượn sách"
        verbose_name_plural = "Danh sách lượt mượn"

    def save(self, *args, **kwargs):
        from .models import Notification  # tránh circular import

        creating = self._state.adding  # True nếu là bản ghi mới

        # Tạo mã mượn tự động
        if creating and not self.borrow_code:
            last = Borrow.objects.order_by('id').last()
            next_id = (last.id + 1) if last else 1
            self.borrow_code = f"BRC{next_id:04d}"

        # Kiểm tra thay đổi trạng thái
        if not creating:
            old = Borrow.objects.get(pk=self.pk)
            old_status = old.status
            new_status = self.status

            # Nếu từ "Đang chờ" → "Đang mượn": giảm số lượng
            if old_status == "Đang chờ" and new_status == "Đang mượn":
                if self.book.quantity > 0:
                    self.book.quantity -= 1
                    self.book.save()

                # Tự động tính hạn trả = 5 tháng kể từ ngày mượn
                if not self.due_date:
                    self.due_date = (self.borrow_date or date.today()) + relativedelta(months=5)

                Notification.objects.create(
                    user=self.user,
                    title="Mượn sách thành công",
                    message=f"Bạn đã mượn thành công sách '{self.book.title}'. "
                            f"Sách được mượn đến hết ngày {self.due_date.strftime('%d/%m/%Y')}."
                )

            # Nếu từ "Đang mượn" → "Đã trả": tăng số lượng
            elif old_status == "Đang mượn" and new_status == "Đã trả":
                self.book.quantity += 1
                self.book.save()
                # Ghi nhận ngày trả
                self.return_date = date.today()

                if self.return_date > (self.due_date or date.today()):
                    msg = f"Cảm ơn bạn đã trả sách '{self.book.title}'. " \
                          "Hãy lưu ý trả sách đúng hạn các lần mượn sau để tránh phí phạt."
                else:
                    msg = f"Cảm ơn bạn đã trả sách '{self.book.title}' đúng hạn."
                Notification.objects.create(user=self.user, title="Trả sách thành công", message=msg)

        super().save(*args, **kwargs)

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Thông báo"
        verbose_name_plural = "Thông báo"

    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
class EntryLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="MSV")
    shift = models.CharField(max_length=10, choices=[('Sáng', 'Sáng'), ('Chiều', 'Chiều')], verbose_name="Buổi")
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Lượt vào ra"
        verbose_name_plural = "Các lượt vào ra"
        ordering = ['-check_in']

    def __str__(self):
        return f"{self.user.username} - {self.shift} ({self.check_in or 'Chưa vào'})"

