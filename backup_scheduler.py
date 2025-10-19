import schedule
import time
from django.core.management import call_command

def schedule_backups():
    schedule.every().day.at("02:00").do(
        lambda: call_command('backup_database', '--type', 'daily')
    )
    
    while True:
        schedule.run_pending()
        time.sleep(60)