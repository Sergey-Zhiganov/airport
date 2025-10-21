from django.core.management.base import BaseCommand
from django.conf import settings
import subprocess
import os
from datetime import datetime

from dbapp.models import BackupLog

class Command(BaseCommand):
    help = 'Создание резервной копии базы данных'

    def add_arguments(self, parser):
        parser.add_argument('--type', type=str, default='daily', 
            help='Тип бэкапа: daily, weekly, monthly')
        
    def handle(self, *args, **options):
        backup_type = options['type']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        backup_filename = f'backup_{backup_type}_{timestamp}.bak'
        backup_path = os.path.join(settings.DB_BACKUP_DIR, backup_filename)

        try:
            cmd = [
                'sqlcmd',
                '-S', settings.DATABASES['default']['HOST'],
                '-E',
                '-Q', f"BACKUP DATABASE [{settings.DATABASES['default']['NAME']}] TO DISK = N'{backup_path}' WITH FORMAT, INIT",
                '-b'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.stdout.write(self.style.SUCCESS(f'Бэкап успешно создан: {backup_path}'))

                BackupLog.objects.create(
                    backup_type=backup_type,
                    filename=backup_filename,
                    file_path=backup_path,
                    status='success',
                    file_size=os.path.getsize(backup_path)
                )
            else:
                raise Exception(f'Ошибка бэкапа: {result.stderr}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка создания бэкапа: {str(e)}'))

            BackupLog.objects.create(
                backup_type=backup_type,
                filename=backup_filename,
                file_path=backup_path,
                status='error',
                error_message=str(e)
            )