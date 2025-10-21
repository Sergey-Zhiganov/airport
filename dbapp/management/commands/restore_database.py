from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from dbapp.models import BackupLog
import subprocess
import os
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Восстановление базы данных из резервной копии'

    def add_arguments(self, parser):
        parser.add_argument('backup_path', type=str, help='Путь к файлу бэкапа')
        parser.add_argument('--backup-id', type=int, help='ID записи BackupLog для обновления статуса')

    def handle(self, *args, **options):
        backup_path = options['backup_path']
        
        if not os.path.exists(backup_path):
            self.stdout.write(self.style.ERROR('Файл бэкапа не найден'))
            return None

        try:
            self.stdout.write('Начинаем восстановление базы данных...')
            
            db_settings = settings.DATABASES['default']
            db_host = db_settings.get('HOST', 'localhost')
            db_name = db_settings.get('NAME')
            
            cmd_single = [
                'sqlcmd',
                '-S', db_host,
                '-Q', f"ALTER DATABASE [{db_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE",
                '-E'
            ]

            cmd_restore = [
                'sqlcmd',
                '-S', db_host,
                '-Q', f"RESTORE DATABASE [{db_name}] FROM DISK = N'{backup_path}' WITH REPLACE, RECOVERY",
                '-E'
            ]

            cmd_multi = [
                'sqlcmd',
                '-S', db_host,
                '-Q', f"ALTER DATABASE [{db_name}] SET MULTI_USER",
                '-E'
            ]
            
            self.stdout.write('Перевод БД в однопользовательский режим...')
            result_single = subprocess.run(cmd_single, capture_output=True, text=True, timeout=300)
            if result_single.returncode != 0:
                self.stdout.write(self.style.ERROR(f'Ошибка перевода в однопользовательский режим: {result_single.stderr}'))
                raise subprocess.CalledProcessError(result_single.returncode, cmd_single, output=result_single.stdout, stderr=result_single.stderr)
            
            self.stdout.write('Выполнение восстановления...')
            result_restore = subprocess.run(cmd_restore, capture_output=True, text=True, timeout=600)
            if result_restore.returncode != 0:
                self.stdout.write(self.style.ERROR(f'Ошибка восстановления: {result_restore.stderr}'))
                try:
                    subprocess.run(cmd_multi, timeout=60)
                except:
                    pass
                raise subprocess.CalledProcessError(result_restore.returncode, cmd_restore, output=result_restore.stdout, stderr=result_restore.stderr)
            
            self.stdout.write('Возврат БД в многопользовательский режим...')
            result_multi = subprocess.run(cmd_multi, capture_output=True, text=True, timeout=300)
            if result_multi.returncode != 0:
                self.stdout.write(self.style.WARNING(f'Предупреждение при возврате в многопользовательский режим: {result_multi.stderr}'))
            
            self.stdout.write(self.style.SUCCESS('База данных успешно восстановлена'))
            
        except subprocess.CalledProcessError as e:
            error_msg = f'Ошибка восстановления: {str(e)}'
            if hasattr(e, 'stderr') and e.stderr:
                error_msg += f'\nДетали: {e.stderr}'
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            raise e
        except subprocess.TimeoutExpired:
            error_msg = 'Таймаут выполнения операции восстановления'
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            raise
        except Exception as e:
            error_msg = f'Неожиданная ошибка: {str(e)}'
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            raise