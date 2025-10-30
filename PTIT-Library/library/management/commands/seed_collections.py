from django.core.management.base import BaseCommand
from library.models import Collection, SubCollection

class Command(BaseCommand):
    help = "Tạo sẵn 9 bộ sưu tập và các phân loại con mặc định"

    def handle(self, *args, **options):
        collections = {
            "Bài giảng": [
                "Công nghệ thông tin", "An toàn thông tin", "Viễn thông", "Điện tử",
                "Cơ bản", "Đa phương tiện", "Kế toán", "Quản trị kinh doanh"
            ],
            "Giáo trình": [
                "Công nghệ thông tin", "An toàn thông tin", "Viễn thông", "Điện tử",
                "Cơ bản", "Đa phương tiện", "Kế toán", "Quản trị kinh doanh"
            ],
            "E-book chuyên ngành": [
                "Công nghệ thông tin", "An toàn thông tin", "Viễn thông", "Điện tử"
            ],
            "Khoá luận tốt nghiệp": [
                "Công nghệ thông tin", "An toàn thông tin", "Viễn thông", "Điện tử",
                "Cơ bản", "Đa phương tiện", "Kế toán", "Quản trị kinh doanh"
            ],
            "Luận văn thạc sĩ": [
                "Hệ thống thông tin", "Khoa học máy tính", "Kỹ thuật viễn thông",
                "Kỹ thuật điện tử", "Quản trị kinh doanh"
            ],
            "Luận án tiến sĩ": [
                "Hệ thống thông tin", "Khoa học máy tính", "Kỹ thuật viễn thông",
                "Kỹ thuật điện tử", "Quản trị kinh doanh"
            ],
            "Sách danh nhân": ["Danh nhân Việt Nam", "Danh nhân thế giới"],
            "Sách tâm lý - kỹ năng": [
                "Kỹ năng quản lý thời gian", "Kỹ năng lãnh đạo", "Cẩm nang kinh doanh - làm giàu"
            ],
            "Sách giải trí - giáo dục": ["Truyện ngắn", "Tiểu thuyết"],
        }

        for c_name, subs in collections.items():
            collection, created = Collection.objects.get_or_create(name=c_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Tạo bộ sưu tập: {c_name}"))
            for s in subs:
                sub, sub_created = SubCollection.objects.get_or_create(collection=collection, name=s)
                if sub_created:
                    self.stdout.write(f"   └── {s}")

        self.stdout.write(self.style.SUCCESS("\n🎉 Hoàn tất tạo bộ sưu tập và phân loại mặc định!"))
