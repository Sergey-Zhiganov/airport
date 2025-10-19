from django.core.management.base import BaseCommand
from django.conf import settings
import subprocess
import os

class Command(BaseCommand):
    help = 'Восстановление базы данных из резервной копии'

    def add_arguments(self, parser):
        parser.add_argument('backup_path', type=str, help='Путь к файлу бэкапа')

    def handle(self, *args, **options):
        backup_path = options['backup_path']
        
        if not os.path.exists(backup_path):
            self.stdout.write(self.style.ERROR('Файл бэкапа не найден'))
            return

        try:
            cmd_single = [
                'sqlcmd',
                '-S', settings.DATABASES['default']['HOST'],
                '-Q', f"ALTER DATABASE [{settings.DATABASES['default']['NAME']}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE",
                '-U', settings.DATABASES['default']['USER'],
                '-P', settings.DATABASES['default']['PASSWORD']
            ]

            cmd_restore = [
                'sqlcmd',
                '-S', settings.DATABASES['default']['HOST'],
                '-Q', f"RESTORE DATABASE [{settings.DATABASES['default']['NAME']}] FROM DISK = N'{backup_path}' WITH REPLACE",
                '-U', settings.DATABASES['default']['USER'],
                '-P', settings.DATABASES['default']['PASSWORD']
            ]
            
            subprocess.run(cmd_single, check=True)
            subprocess.run(cmd_restore, check=True)
            
            self.stdout.write(self.style.SUCCESS('База данных успешно восстановлена'))
            
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка восстановления: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Неожиданная ошибка: {str(e)}'))