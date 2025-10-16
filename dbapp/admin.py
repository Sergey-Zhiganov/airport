from django.contrib import admin
from .models import *

# Register your models here.

admin.site.site_header = "Администрирование FlyPodolsk"
admin.site.site_title = "Администрирование аэропорта"
admin.site.index_title = "Управление системой"

@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    fields = ('password', 'last_login', 'is_superuser', 'username', 
        'first_name', 'last_name', 'middle_name', 'phone', 'is_staff', 'is_active', 'date_joined')

admin.site.register(CheckInDesk)
admin.site.register(Gate)
admin.site.register(Airline)
admin.site.register(Airplane)
admin.site.register(Airport)
admin.site.register(FlightStatus)
admin.site.register(Flight)
admin.site.register(CheckInDeskFlight)
admin.site.register(GateFlight)
admin.site.register(FlightTime)
admin.site.register(Passenger)
admin.site.register(BoardingPass)