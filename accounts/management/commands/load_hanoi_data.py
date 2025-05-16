from django.core.management.base import BaseCommand
from accounts.models import City, District, Ward
import requests

class Command(BaseCommand):
    help = 'Load Hanoi locations data from API'

    def handle(self, *args, **kwargs):
        # API endpoints
        PROVINCE_API = "https://provinces.open-api.vn/api/p/01?depth=3"  # Mã Hà Nội là 01

        try:
            # Xóa dữ liệu cũ của Hà Nội
            self.stdout.write('Deleting old Hanoi data...')
            hanoi = City.objects.filter(name__icontains='Hà Nội').first()
            if hanoi:
                hanoi.delete()

            # Lấy dữ liệu Hà Nội
            self.stdout.write('Fetching Hanoi data...')
            response = requests.get(PROVINCE_API)
            hanoi_data = response.json()

            # Tạo City Hà Nội
            hanoi = City.objects.create(name=hanoi_data['name'])
            self.stdout.write(f'Created city: {hanoi.name}')

            # Tạo các quận/huyện
            for district_data in hanoi_data['districts']:
                district = District.objects.create(
                    name=district_data['name'],
                    city=hanoi
                )
                self.stdout.write(f'Created district: {district.name}')

                # Tạo các phường/xã
                for ward_data in district_data['wards']:
                    ward = Ward.objects.create(
                        name=ward_data['name'],
                        district=district
                    )
                    self.stdout.write(f'Created ward: {ward.name}')

            self.stdout.write(self.style.SUCCESS('Successfully loaded Hanoi locations data'))

        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Error fetching data from API: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}')) 