from django.core.management.base import BaseCommand
from accounts.models import City, District, Ward
import requests

class Command(BaseCommand):
    help = 'Load Vietnamese locations data from API'

    def handle(self, *args, **kwargs):
        # API endpoints
        PROVINCE_API = "https://provinces.open-api.vn/api/p/"
        DISTRICT_API = "https://provinces.open-api.vn/api/p/{code}?depth=2"
        WARD_API = "https://provinces.open-api.vn/api/d/{code}?depth=2"

        try:
            # Xóa dữ liệu cũ
            self.stdout.write('Deleting old data...')
            City.objects.all().delete()
            District.objects.all().delete()
            Ward.objects.all().delete()

            # Lấy danh sách tỉnh/thành phố
            self.stdout.write('Fetching provinces...')
            response = requests.get(PROVINCE_API)
            provinces = response.json()

            for province in provinces:
                # Tạo tỉnh/thành phố
                city = City.objects.create(name=province['name'])
                self.stdout.write(f'Created province: {city.name}')

                # Lấy danh sách quận/huyện của tỉnh/thành phố
                response = requests.get(DISTRICT_API.format(code=province['code']))
                province_data = response.json()
                
                for district_data in province_data['districts']:
                    # Tạo quận/huyện
                    district = District.objects.create(
                        name=district_data['name'],
                        city=city
                    )
                    self.stdout.write(f'Created district: {district.name}')

                    # Lấy danh sách phường/xã của quận/huyện
                    response = requests.get(WARD_API.format(code=district_data['code']))
                    district_detail = response.json()

                    for ward_data in district_detail['wards']:
                        # Tạo phường/xã
                        ward = Ward.objects.create(
                            name=ward_data['name'],
                            district=district
                        )
                        self.stdout.write(f'Created ward: {ward.name}')

            self.stdout.write(self.style.SUCCESS('Successfully loaded Vietnamese locations data'))

        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Error fetching data from API: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}')) 