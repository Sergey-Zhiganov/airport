from django.urls import path
from django.contrib.auth import views as auth_views
from .views import *

urlpatterns = [
    path('', index, name='index'),
    path('logout/', auth_views.LogoutView.as_view(template_name='registration/logout.html'), name='logout'),
    path('profile', profile, name='profile'),

    path('workers', workers, name='workers'),
    path('workers/add', worker_add, name='worker_add'),
    path('workers/<int:worker_id>', worker_edit, name='worker_edit'),
    path('workers/<int:worker_id>/delete', worker_delete, name='worker_delete'),
    path('workers/import/', worker_import, name='worker_import'),
    path('workers/export/', worker_export, name='worker_export'),

    path('check-in-desks', check_in_desks, name='check_in_desks'),
    path('check-in-desks/add', check_in_desk_add, name='check_in_desk_add'),
    path('check-in-desks/<int:check_in_desk_id>', check_in_desk_edit, name='check_in_desk_edit'),
    path('check-in_desks/<int:check_in_desk_id>/delete', check_in_desk_delete, name='check_in_desk_delete'),

    path('gates', gates, name='gates'),
    path('gates/add', gate_add, name='gate_add'),
    path('gates/<int:gate_id>', gate_edit, name='gate_edit'),
    path('gates/<int:gate_id>/delete', gate_delete, name='gate_delete'),

    path('airlines', airlines, name='airlines'),
    path('airlines/add', airline_add, name='airline_add'),
    path('airlines/<int:airline_id>', airline_edit, name='airline_edit'),
    path('airlines/<int:airline_id>/delete', airline_delete, name='airline_delete'),
    path('airlines/import/', airline_import, name='airline_import'),
    path('airlines/export/', airline_export, name='airline_export'),

    path('airplanes', airplanes, name='airplanes'),
    path('airplanes/add', airplane_add, name='airplane_add'),
    path('airplanes/<int:airplane_id>', airplane_edit, name='airplane_edit'),
    path('airplanes/<int:airplane_id>/delete', airplane_delete, name='airplane_delete'),
    path('airplanes/import/', airplane_import, name='airplane_import'),
    path('airplanes/export/', airplane_export, name='airplane_export'),

    path('airports', airports, name='airports'),
    path('airports/add', airport_add, name='airport_add'),
    path('airports/<int:airport_id>', airport_edit, name='airport_edit'),
    path('airports/<int:airport_id>/delete', airport_delete, name='airport_delete'),
    path('airports/import/', airport_import, name='airport_import'),
    path('airports/export/', airport_export, name='airport_export'),

    path('flights', flights, name='flights'),
    path('flights/add', flight_add, name='flight_add'),
    path('flights/<int:flight_id>', flight_edit, name='flight_edit'),
    path('flights/<int:flight_id>/delete', flight_delete, name='flight_delete'),
    path('flights/import/', flight_import, name='flight_import'),
    path('flights/export/', flight_export, name='flight_export'),

    path('check-in-desks/<int:check_in_desk_id>/flights/', check_in_desk_flights, name='check_in_desk_flights'),
    path('check-in-desks/flight/<int:cf_id>/toggle/', check_in_desk_flight_toggle, name='check_in_desk_flight_toggle'),
    path('check-in-desks/flight/<int:cf_id>/delete/', check_in_desk_flight_delete, name='check_in_desk_flight_delete'),

    path('gates/<int:gate_id>/flights/', gate_flights, name='gate_flights'),
    path('gates/flight/<int:cf_id>/toggle/', gate_flight_toggle, name='gate_flight_toggle'),
    path('gates/flight/<int:cf_id>/delete/', gate_flight_delete, name='gate_flight_delete'),

    path('flights/<int:flight_id>/time/', flight_time_edit, name='flight_time_edit'),

    path('passengers', passengers, name='passengers'),
    path('passengers/add', passenger_add, name='passenger_add'),
    path('passengers/<int:passenger_id>', passenger_edit, name='passenger_edit'),
    path('passengers/<int:passenger_id>/delete', passenger_delete, name='passenger_delete'),
    path('passengers/import/', passenger_import, name='passenger_import'),
    path('passengers/export/', passenger_export, name='passenger_export'),

    path('passengers/<int:passenger_id>/baggage', baggage, name='baggage'),
    path('passengers/<int:passenger_id>/baggage/add', baggage_add, name='baggage_add'),
    path('passengers/<int:passenger_id>/baggage/<int:baggage_id>', baggage_edit, name='baggage_edit'),
    path('passengers/<int:passenger_id>/baggage/<int:baggage_id>/delete', baggage_delete, name='baggage_delete'),

    path('passengers/<int:passenger_id>/boarding-pass', boarding_pass_edit, name='boarding_pass_edit'),

    path('backups/', backup_list, name='backup_list'),
    path('backups/create/', create_backup, name='create_backup'),
    path('backups/<int:backup_id>/delete/', backup_delete, name='backup_delete'),
    path('backups/<int:backup_id>/download/', backup_download, name='backup_download'),
    path('backups/<int:backup_id>/restore/', backup_restore, name='backup_restore'),
    path('backups/restore-upload/', backup_restore_upload, name='backup_restore_upload'),

    path('analytics/', analytics_dashboard, name='analytics_dashboard'),
]