from functools import wraps
from gc import disable
import json
import os
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.models import Group
from django.db.models import Q
from django.db import transaction
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from dbapp.models import *
from webapp.forms import *

# Create your views here.
def log_action(user, instance, action_flag: int, old_instance = None, change_message: str | None = None):
    changed_fields = None
    if action_flag == CHANGE and old_instance:
        changed_fields = []
        for f in instance._meta.fields:
            old_val = getattr(old_instance, f.name)
            new_val = getattr(instance, f.name)
            if old_val != new_val:
                changed_fields.append(str(f.verbose_name))
    
    if change_message:
        pass
    elif action_flag == ADDITION:
        change_message = "Добавлено."
    elif action_flag == DELETION:
        change_message = "Удалено."
    elif action_flag == CHANGE:
        if not changed_fields:
            change_message = 'Ни одно поле не изменено.'
        else:
            if len(changed_fields) == 1:
                change_message = f'Изменено {changed_fields[0]}.'
            elif len(changed_fields) == 2:
                change_message = f'Изменено {changed_fields[0]} и {changed_fields[1]}.'
            else:
                change_message = f'Изменено {", ".join(changed_fields[:-1])} и {changed_fields[-1]}.'
    else:
        change_message = '[]'

    LogEntry.objects.log_action(
        user_id=user.pk,
        content_type_id=ContentType.objects.get_for_model(instance).pk,
        object_id=instance.pk,
        object_repr=str(instance),
        action_flag=action_flag,
        change_message=change_message
    )

def check_permission(request: HttpRequest, perms: str | list[str] | None = None):
    if not request.user.is_authenticated:
        status = 401
        title = "Неавторизован"
        message = "Вы должны войти в систему, чтобы получить доступ к этой странице."
    else:
        if isinstance(perms, str):
            perms = [perms]

        if perms and not any(request.user.has_perm(p) for p in perms):  # type: ignore
            status = 403
            title = "Доступ запрещён"
            message = "У вас нет прав для просмотра этой страницы."
        else:
            return None

    context = {
        "status_code": status,
        "title": title,
        "message": message
    }
    return render(request, "error.html", context, status=status)

def permission_required(perm: str | list[str] | None = None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request: HttpRequest, *args, **kwargs):
            response = check_permission(request, perm)
            if response:
                return response
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def index(request: HttpRequest):
    return render(request, 'index.html', 
        {
            'flights': Flight.objects.all(),
            'airports': Airport.objects.all(),
            'statuses': FlightStatus.objects.all(),
        }
    )

@permission_required()
def profile(request: HttpRequest):
    worker = Worker.objects.get(pk=request.user.pk)

    all_groups = Group.objects.all()

    group_dict = {g.pk: g.name for g in all_groups}

    user_group_ids = worker.groups.values_list('id', flat=True) if worker else []
    group_names = [group_dict.get(gid, "Неизвестная роль") for gid in user_group_ids]

    return render(request, 'profile.html', {
        'data': worker,
        'group_names': group_names
    })

@permission_required('dbapp.view_worker')
def workers(request: HttpRequest):
    workers = Worker.objects.all().prefetch_related('groups')
    for w in workers:
        w.group_names = ", ".join(w.groups.values_list("name", flat=True)) # type: ignore
    return render(request, 'workers.html', {'workers': workers})

@transaction.atomic
@permission_required('dbapp.add_worker')
def worker_add(request: HttpRequest):
    if request.method == 'POST':
        form = WorkerCreateForm(request.POST)
        if form.is_valid():
            instance = form.save()
            log_action(request.user, instance, ADDITION)

            messages.success(request, 'Сотрудник успешно добавлен!')
            return redirect('workers')
    else:
        form = WorkerCreateForm()

        form.fields.pop('is_active')

    return render(request, 'worker_form.html', {
        'form': form,
        'title': 'Добавить сотрудника'
    })

@transaction.atomic
@permission_required('dbapp.view_worker')
def worker_edit(request: HttpRequest, worker_id: int):
    worker = get_object_or_404(Worker, pk=worker_id)
    can_change = request.user.has_perm('dbapp.change_worker') # type: ignore

    if request.method == 'POST':
        if not can_change:
            messages.error(request, "У вас нет прав на редактирование.")
            return redirect('workers')

        form = WorkerEditForm(request.POST, instance=worker)
        if form.is_valid():
            old_worker = Worker.objects.get(pk=worker_id)
            instance = form.save()
            log_action(request.user, instance, CHANGE, old_instance=old_worker)

            messages.success(request, "Сотрудник успешно обновлён!")
            return redirect('workers')
    else:
        form = WorkerEditForm(instance=worker)
        if not can_change:
            for field in form.fields.values():
                field.disabled = True

    return render(request, 'worker_form.html', {
        'form': form,
        'title': f'Редактировать сотрудника: {worker}'
    })

@transaction.atomic
@permission_required('dbapp.delete_worker')
def worker_delete(request: HttpRequest, worker_id: int):
    worker = get_object_or_404(Worker, pk=worker_id)

    if worker == request.user:
        messages.error(request, "Вы не можете удалить самого себя.")
        return redirect('workers')

    if CheckInDesk.objects.filter(worker=worker).exists() or Gate.objects.filter(worker=worker).exists():
        messages.error(request, 
            'Невозможно удалить сотрудника, пока он назначен на стойку регистрации или посадочный выход'
        )
        return redirect('workers')

    worker.delete()
    log_action(request.user, worker, DELETION)

    messages.success(request, "Сотрудник успешно удалён!")
    return redirect('workers')

@permission_required(['dbapp.view_checkindesk', 'dbapp.view_own_checkindesk'])
def check_in_desks(request: HttpRequest):
    if request.user.has_perm('dbapp.view_checkindesk'): #type: ignore
        check_in_desks_data = CheckInDesk.objects.all()
        only_own_desks = False
    else:
        check_in_desks_data = CheckInDesk.objects.filter(worker=request.user)
        only_own_desks = True

    return render(request, 'check_in_desks.html', 
{
            'check_in_desks': check_in_desks_data,
            'only_own_desks': only_own_desks    
        }
    )

@transaction.atomic
@permission_required('dbapp.add_checkindesk')
def check_in_desk_add(request: HttpRequest):
    if request.method == 'POST':
        form = CheckInDeskForm(request.POST)
        if form.is_valid():
            instance = form.save()
            log_action(request.user, instance, ADDITION)

            messages.success(request, 'Стойка регистрации успешно добавлена!')
            return redirect('check_in_desks')
    else:
        form = CheckInDeskForm()

    return render(request, 'check_in_desk_form.html', {
        'form': form,
        'title': 'Добавить стойку регистрации'
    })

@transaction.atomic
@permission_required(['dbapp.view_checkindesk', 'dbapp.view_own_checkindesk'])
def check_in_desk_edit(request: HttpRequest, check_in_desk_id: int):
    check_in_desk = get_object_or_404(CheckInDesk, pk=check_in_desk_id)

    if check_in_desk.worker != request.user and not request.user.has_perm('dbapp.view_checkindesk'): # type: ignore
        context = {
            "status_code": 403,
            "title": "Доступ запрещен",
            "message": "У вас нет прав для просмотра этой страницы."
        }
        return render(request, "error.html", context, status=403)
    
    can_change_all = request.user.has_perm('dbapp.change_checkindesk')  # type: ignore
    can_change_worker = request.user.has_perm('dbapp.change_worker_checkindesk')  # type: ignore
    can_change_is_active = request.user.has_perm('dbapp.change_is_active_checkindesk')  # type: ignore

    if request.method == 'POST':
        form = CheckInDeskForm(request.POST, instance=check_in_desk)

        if not (can_change_all or can_change_worker or can_change_is_active):
            messages.error(request, "У вас нет прав на редактирование.")
            return redirect('check_in_desks')

        if form.is_valid():
            updated_instance: CheckInDesk = form.save(commit=False)

            if not can_change_all:
                if not can_change_worker:
                    updated_instance.worker = check_in_desk.worker
                if not can_change_is_active:
                    updated_instance.is_active = check_in_desk.is_active

            updated_instance.save()
            log_action(request.user, updated_instance, CHANGE, old_instance=check_in_desk)

            messages.success(request, "Стойка регистрации успешно обновлена!")
            return redirect('check_in_desks')
    else:
        form = CheckInDeskForm(instance=check_in_desk)

        if not can_change_all:
            if not can_change_worker:
                form.fields['worker'].disabled = True
            if not can_change_is_active:
                form.fields['is_active'].disabled = True

    return render(request, 'check_in_desk_form.html', {
        'form': form,
        'title': f'Редактировать стойку регистрации: {check_in_desk}'
    })

@transaction.atomic
@permission_required('dbapp.delete_checkindesk')
def check_in_desk_delete(request: HttpRequest, check_in_desk_id: int):
    check_in_desk = get_object_or_404(CheckInDesk, pk=check_in_desk_id)

    if CheckInDeskFlight.objects.filter(desk=check_in_desk).exists():
        messages.error(request, 
            'Невозможно удалить стойку регистрации, пока на неё назначены рейсы'
        )
        return redirect('check_in_desks')

    check_in_desk.delete()
    log_action(request.user, check_in_desk, DELETION)

    messages.success(request, "Стойка регистрации успешно удалена!")
    return redirect('check_in_desks')

@permission_required(['dbapp.view_gate', 'dbapp.view_own_gate'])
def gates(request: HttpRequest):
    if request.user.has_perm('dbapp.view_gate'): #type: ignore
        gates_data = Gate.objects.all()
        only_own_gates = False
    else:
        gates_data = Gate.objects.filter(worker=request.user)
        only_own_gates = True

    return render(request, 'gates.html', 
{
            'gates': gates_data,
            'only_own_gates': only_own_gates    
        }
    )

@transaction.atomic
@permission_required('dbapp.add_gate')
def gate_add(request: HttpRequest):
    if request.method == 'POST':
        form = GateForm(request.POST)
        if form.is_valid():
            instance = form.save()
            log_action(request.user, instance, ADDITION)

            messages.success(request, 'Посадочный выход успешно добавлена!')
            return redirect('gates')
    else:
        form = GateForm()

    return render(request, 'gate_form.html', {
        'form': form,
        'title': 'Добавить посадочный выход'
    })

@transaction.atomic
@permission_required(['dbapp.view_gate', 'dbapp.view_own_gate'])
def gate_edit(request: HttpRequest, gate_id: int):
    gate = get_object_or_404(Gate, pk=gate_id)

    if gate.worker != request.user and not request.user.has_perm('dbapp.view_gate'): # type: ignore
        context = {
            "status_code": 403,
            "title": "Доступ запрещен",
            "message": "У вас нет прав для просмотра этой страницы."
        }
        return render(request, "error.html", context, status=403)
    
    can_change_all = request.user.has_perm('dbapp.change_gate')  # type: ignore
    can_change_worker = request.user.has_perm('dbapp.change_worker_gate')  # type: ignore
    can_change_is_active = request.user.has_perm('dbapp.change_is_active_gate')  # type: ignore

    if request.method == 'POST':
        form = GateForm(request.POST, instance=gate)

        if not (can_change_all or can_change_worker or can_change_is_active):
            messages.error(request, "У вас нет прав на редактирование.")
            return redirect('gates')

        if form.is_valid():
            updated_instance: Gate = form.save(commit=False)

            if not can_change_all:
                if not can_change_worker:
                    updated_instance.worker = gate.worker
                if not can_change_is_active:
                    updated_instance.is_active = gate.is_active

            updated_instance.save()
            log_action(request.user, updated_instance, CHANGE, old_instance=gate)

            messages.success(request, "Посадочный выход успешно обновлён!")
            return redirect('gates')
    else:
        form = GateForm(instance=gate)

        if not can_change_all:
            if not can_change_worker:
                form.fields['worker'].disabled = True
            if not can_change_is_active:
                form.fields['is_active'].disabled = True

    return render(request, 'gate_form.html', {
        'form': form,
        'title': f'Редактировать посадочный выход: {gate}'
    })

@transaction.atomic
@permission_required('dbapp.delete_gate')
def gate_delete(request: HttpRequest, gate_id: int):
    gate = get_object_or_404(Gate, pk=gate_id)

    if GateFlight.objects.filter(gate=gate).exists():
        messages.error(request, 
            'Невозможно удалить посадочный выход, пока на него назначены рейсы'
            )
        return redirect('gates')

    gate.delete()
    log_action(request.user, gate, DELETION)

    messages.success(request, "Посадочный выход успешно удалён!")
    return redirect('gates')

@permission_required('dbapp.view_airline')
def airlines(request: HttpRequest):
    return render(request, 'airlines.html', {'airlines': Airline.objects.all()})

@transaction.atomic
@permission_required('dbapp.add_airline')
def airline_add(request: HttpRequest):
    if request.method == 'POST':
        form = AirlineForm(request.POST)
        if form.is_valid():
            instance = form.save()
            log_action(request.user, instance, ADDITION)

            messages.success(request, 'Авиакомпания успешно добавлена!')
            return redirect('airlines')
    else:
        form = AirlineForm()

    return render(request, 'airline_form.html', {
        'form': form,
        'title': 'Добавить авиакомпанию'
    })

@transaction.atomic
@permission_required('dbapp.change_airline')
def airline_edit(request: HttpRequest, airline_id: int):
    airline = get_object_or_404(Airline, pk=airline_id)
    can_change = request.user.has_perm('dbapp.change_airline') # type: ignore

    if request.method == 'POST':
        if not can_change:
            messages.error(request, "У вас нет прав на редактирование.")
            return redirect('airlines')

        form = AirlineForm(request.POST, instance=airline)
        if form.is_valid():
            old_airline = Airline.objects.get(pk=airline_id)
            instance = form.save()
            log_action(request.user, instance, CHANGE, old_instance=old_airline)
            
            messages.success(request, "Авиакомпания успешно обновлена!")
            return redirect('airlines')
    else:
        form = AirlineForm(instance=airline)
        if not can_change:
            for field in form.fields.values():
                field.disabled = True

    return render(request, 'airline_form.html', {
        'form': form,
        'title': f'Редактировать авиакомпанию: {airline}'
    })

@transaction.atomic
@permission_required('dbapp.delete_airline')
def airline_delete(request: HttpRequest, airline_id: int):
    airline = get_object_or_404(Airline, pk=airline_id)

    if Airplane.objects.filter(airline=airline).exists():
        messages.error(request,
            'Невозможно удалить авиакомпанию, пока у неё есть самолёты'
        )
        return redirect('airlines')

    airline.delete()
    log_action(request.user, airline, DELETION)

    messages.success(request, "Авиакомпания успешно удалена!")
    return redirect('airlines')

@permission_required('dbapp.view_airplane')
def airplanes(request: HttpRequest):
    return render(request, 'airplanes.html', {'airplanes': Airplane.objects.all()})

@transaction.atomic
@permission_required('dbapp.add_airplane')
def airplane_add(request: HttpRequest):
    if request.method == 'POST':
        form = AirplaneForm(request.POST)
        if form.is_valid():
            instance = form.save()
            log_action(request.user, instance, ADDITION)

            messages.success(request, 'Самолёт успешно добавлен!')
            return redirect('airplanes')
    else:
        form = AirplaneForm()

    return render(request, 'airplane_form.html', {
        'form': form,
        'title': 'Добавить самолёт'
    })

@transaction.atomic
@permission_required('dbapp.change_airplane')
def airplane_edit(request: HttpRequest, airplane_id: int):
    airplane = get_object_or_404(Airplane, pk=airplane_id)
    can_change = request.user.has_perm('dbapp.change_airplane') # type: ignore

    if request.method == 'POST':
        if not can_change:
            messages.error(request, "У вас нет прав на редактирование.")
            return redirect('airplanes')

        form = AirplaneForm(request.POST, instance=airplane)
        if form.is_valid():
            old_airplane = Airplane.objects.get(pk=airplane_id)
            instance = form.save()
            log_action(request.user, instance, CHANGE, old_instance=old_airplane)

            messages.success(request, "Самолёт успешно обновлён!")
            return redirect('airplanes')
    else:
        form = AirplaneForm(instance=airplane)
        if not can_change:
            for field in form.fields.values():
                field.disabled = True

    return render(request, 'airplane_form.html', {
        'form': form,
        'title': f'Редактировать самолёт: {airplane}'
    })

@transaction.atomic
@permission_required('dbapp.delete_airplane')
def airplane_delete(request: HttpRequest, airplane_id: int):
    airplane = get_object_or_404(Airplane, pk=airplane_id)

    if Flight.objects.filter(airplane=airplane).exists():
        messages.error(request,
            'Невозможно удалить самолёт, пока на него назначены рейсы'
        )
        return redirect('airplanes')

    airplane.delete()
    log_action(request.user, airplane, DELETION)

    messages.success(request, "Самолёт успешно удалён!")
    return redirect('airplanes')

@permission_required('dbapp.view_airport')
def airports(request: HttpRequest):
    return render(request, 'airports.html', {'airports': Airport.objects.all()})

@transaction.atomic
@permission_required('dbapp.add_airport')
def airport_add(request: HttpRequest):
    if request.method == 'POST':
        form = AirportForm(request.POST)
        if form.is_valid():
            instance = form.save()
            log_action(request.user, instance, ADDITION)

            messages.success(request, 'Аэропорт успешно добавлен!')
            return redirect('airports')
    else:
        form = AirportForm()

    return render(request, 'airport_form.html', {
        'form': form,
        'title': 'Добавить аэропорт'
    })

@transaction.atomic
@permission_required('dbapp.change_airport')
def airport_edit(request: HttpRequest, airport_id: int):
    airport = get_object_or_404(Airport, pk=airport_id)
    can_change = request.user.has_perm('dbapp.change_airport') # type: ignore

    if request.method == 'POST':
        if not can_change:
            messages.error(request, "У вас нет прав на редактирование.")
            return redirect('airports')

        form = AirportForm(request.POST, instance=airport)
        if form.is_valid():
            old_airport = Airport.objects.get(pk=airport_id)
            instance = form.save()
            log_action(request.user, instance, CHANGE, old_instance=old_airport)

            messages.success(request, "Аэропорт успешно обновлён!")
            return redirect('airports')
    else:
        form = AirportForm(instance=airport)
        if not can_change:
            for field in form.fields.values():
                field.disabled = True

    return render(request, 'airport_form.html', {
        'form': form,
        'title': f'Редактировать аэропорт: {airport}'
    })

@transaction.atomic
@permission_required('dbapp.delete_airport')
def airport_delete(request: HttpRequest, airport_id: int):
    airport = get_object_or_404(Airport, pk=airport_id)

    if Flight.objects.filter(Q(departure_airport=airport) | Q(arrival_airport=airport)).exists():
        messages.error(request,
            'Невозможно удалить аэропорт, пока он указан в расписании рейсов'
        )
        return redirect('airports')

    airport.delete()
    log_action(request.user, airport, DELETION)

    messages.success(request, "Аэропорт успешно удалён!")
    return redirect('airports')

@permission_required('dbapp.view_flight')
def flights(request: HttpRequest):
    return render(request, 'flights.html', {'flights': Flight.objects.all()})

@transaction.atomic
@permission_required('dbapp.add_flight')
def flight_add(request: HttpRequest):
    if request.method == 'POST':
        form = FlightForm(request.POST)
        if form.is_valid():
            instance: Flight = form.save(commit=False)
            instance.flight_status_id = 1 # type: ignore
            instance.save()
            log_action(request.user, instance, ADDITION)

            messages.success(request, 'Рейс успешно добавлен!')
            return redirect('flights')
    else:
        form = FlightForm()

    iata_codes = {
        airplane.pk: airplane.airline.IATA_code
        for airplane in Airplane.objects.select_related('airline').all()
    }

    return render(request, 'flight_form.html', {
        'form': form,
        'title': 'Добавить рейс',
        'iata_codes': iata_codes,
        'hide_status': True
    })

@transaction.atomic
@permission_required(['dbapp.view_flight'])
def flight_edit(request: HttpRequest, flight_id: int):
    flight = get_object_or_404(Flight, pk=flight_id)
    
    can_change_all = request.user.has_perm('dbapp.change_gate')  # type: ignore
    can_change_flight_status = request.user.has_perm('dbapp.change_flight_status')  # type: ignore

    if request.method == 'POST':
        form = FlightForm(request.POST, instance=flight, is_edit=True)

        if not (can_change_all or can_change_flight_status):
            messages.error(request, "У вас нет прав на редактирование.")
            return redirect('flights')

        if form.is_valid():
            updated_instance: Flight = form.save(commit=False)

            if not can_change_all:
                if not can_change_flight_status:
                    updated_instance.flight_status = flight.flight_status

            updated_instance.save()
            log_action(request.user, updated_instance, CHANGE, old_instance=flight)

            messages.success(request, "Рейс успешно обновлён!")
            return redirect('gates')
    else:
        form = FlightForm(instance=flight, is_edit=True)

        if not can_change_all:
            if not can_change_flight_status:
                form.fields['flight_status'].disabled = True
    
    iata_codes = {
        airplane.pk: airplane.airline.IATA_code
        for airplane in Airplane.objects.select_related('airline').all()
    }

    return render(request, 'flight_form.html', {
        'form': form,
        'title': f'Редактировать рейс: {flight}',
        'iata_codes': iata_codes,
        'hide_status': False
    })

@transaction.atomic
@permission_required('dbapp.delete_flight')
def flight_delete(request: HttpRequest, flight_id: int):
    flight = get_object_or_404(Flight, pk=flight_id)

    if Passenger.objects.filter(flight=flight).exists():
        messages.error(request,
            'Невозможно удалить рейс, пока на него назначены пассажиры'
        )

    flight.delete()
    log_action(request.user, flight, DELETION)

    messages.success(request, "Рейс успешно удалён!")
    return redirect('flights')

@permission_required(['dbapp.change_checkindeskflight', 'dbapp.change_is_active_checkindeskflight'])
def check_in_desk_flights(request: HttpRequest, check_in_desk_id: int):
    desk = get_object_or_404(CheckInDesk, pk=check_in_desk_id)

    if not desk.worker:
        messages.error(request, 'На данную стойку не назначен сотрудник')
        return redirect('check_in_desks')
    
    if (not request.user.has_perm('dbapp.change_checkindeskflight')  # type: ignore
        and desk.worker.pk != request.user.pk):
        context = {
            "status_code": 403,
            "title": "Доступ запрещен",
            "message": "У вас нет прав для просмотра этой страницы."
        }
        return render(request, "error.html", context, status=403)

    available_flights = Flight.objects.exclude(
        checkindeskflight__desk=desk
    ).filter(flight_status__lt=9)

    if request.method == 'POST':
        form = CheckInDeskFlightForm(request.POST)
        if form.is_valid():
            instance: CheckInDeskFlight = form.save(commit=False)
            instance.desk = desk
            instance.save()
            messages.success(request, 'Рейс успешно назначен на стойку')
            return redirect('check_in_desk_flights', check_in_desk_id=desk.pk)
    else:
        form = CheckInDeskFlightForm()

    assigned_flights = CheckInDeskFlight.objects.filter(desk=desk)

    form.fields['flight'].queryset = available_flights # type: ignore

    return render(request, 'check_in_desk_flights.html', {
        'desk': desk,
        'form': form,
        'available_flights': available_flights,
        'assigned_flights': assigned_flights
    })

@transaction.atomic
@permission_required(['dbapp.change_checkindeskflight', 'dbapp.change_is_active_checkindeskflight'])
def check_in_desk_flight_toggle(request: HttpRequest, cf_id: int):
    cf = get_object_or_404(CheckInDeskFlight, pk=cf_id)
    if request.method == 'POST':
        data: dict = json.loads(request.body)
        cf.is_active = data.get('is_active', False)
        cf.save()

        flight_time, _ = FlightTime.objects.get_or_create(id=cf.flight)

        if cf.is_active:
            if cf.flight.flight_status.pk != 2:
                flight_time.check_in_open_time = timezone.now()
                flight_time.check_in_close_time = None
                flight_time.save()

                cf.flight.flight_status = FlightStatus.objects.get(pk=2)
                cf.flight.save()
        else:
            if not CheckInDeskFlight.objects.filter(flight=cf.flight, is_active=True).exists():
                flight_time.check_in_close_time = timezone.now()
                flight_time.save()

                cf.flight.flight_status = FlightStatus.objects.get(pk=3)
                cf.flight.save()

        return JsonResponse({'success': True})
    return JsonResponse({'error': 'invalid method'}, status=400)

@permission_required('dbapp.change_checkindeskflight')
def check_in_desk_flight_delete(request: HttpRequest, cf_id: int):
    cf = get_object_or_404(CheckInDeskFlight, pk=cf_id)
    desk_id: int = cf.desk.pk
    cf.delete()
    messages.success(request, "Рейс удалён со стойки")
    return redirect('check_in_desk_flights', check_in_desk_id=desk_id)

@permission_required(['dbapp.change_gateflight', 'dbapp.change_is_active_gateflight'])
def gate_flights(request: HttpRequest, gate_id: int):
    gate = get_object_or_404(Gate, pk=gate_id)

    if not gate.worker:
        messages.error(request, 'На данный посадочный выход не назначен сотрудник')
        return redirect('gates')
    
    if (not request.user.has_perm('dbapp.change_gateflight')  # type: ignore
        and gate.worker.pk != request.user.pk):
        context = {
            "status_code": 403,
            "title": "Доступ запрещен",
            "message": "У вас нет прав для просмотра этой страницы."
        }
        return render(request, "error.html", context, status=403)

    available_flights = Flight.objects.exclude(
        gateflight__gate=gate
    ).exclude(flight_status__in=[1, 2, 9])

    if request.method == 'POST':
        form = GateFlightForm(request.POST)
        if form.is_valid():
            instance: GateFlight = form.save(commit=False)
            instance.gate = gate
            instance.save()
            messages.success(request, 'Рейс успешно назначен на посадочный выход')
            return redirect('gate_flights', gate_id=gate.pk)
    else:
        form = GateFlightForm()

    assigned_flights = GateFlight.objects.filter(gate=gate)

    form.fields['flight'].queryset = available_flights # type: ignore

    return render(request, 'gate_flights.html', {
        'gate': gate,
        'form': form,
        'available_flights': available_flights,
        'assigned_flights': assigned_flights
    })

@transaction.atomic
@permission_required(['dbapp.change_gateflight', 'dbapp.change_is_active_gateflight'])
def gate_flight_toggle(request: HttpRequest, gf_id: int):
    gf = get_object_or_404(GateFlight, pk=gf_id)
    if request.method == 'POST':
        flight_status = gf.flight.flight_status.pk

        if flight_status in [1, 2, 9]:
            reason = {
                1: "регистрация не началась",
                2: "регистрация не закончилась",
                9: "рейс отменён"
            }[flight_status]
            messages.error(request, f"Невозможно назначить данному рейсу выход ({reason})")
            return JsonResponse({'success': False})
        
        data: dict = json.loads(request.body)
        gf.is_active = data.get('is_active', False)
        gf.save()

        flight_time, _ = FlightTime.objects.get_or_create(id=gf.flight)

        if gf.is_active:
            if flight_status != 4:
                flight_time.boarding_open_time = timezone.now()
                flight_time.boarding_close_time = None
                flight_time.save()

                gf.flight.flight_status = FlightStatus.objects.get(pk=3)
                gf.flight.save()
        else:
            if not GateFlight.objects.filter(flight=gf.flight, is_active=True).exists():
                flight_time.boarding_close_time = timezone.now()
                flight_time.save()

                gf.flight.flight_status = FlightStatus.objects.get(pk=4)
                gf.flight.save()

        return JsonResponse({'success': True})
    return JsonResponse({'error': 'invalid method'}, status=400)

@permission_required('dbapp.change_gateflight')
def gate_flight_delete(request: HttpRequest, gf_id: int):
    gf = get_object_or_404(GateFlight, pk=gf_id)
    gate_id: int = gf.gate.pk
    gf.delete()
    messages.success(request, "Рейс удалён с посадочного выхода")
    return redirect('gate_flights', gate_id=gate_id)

@transaction.atomic
@permission_required('dbapp.view_flighttime')
def flight_time_edit(request: HttpRequest, flight_id: int):
    flight = get_object_or_404(Flight, pk=flight_id)
    flight_time, _ = FlightTime.objects.get_or_create(id=flight)

    can_change = request.user.has_perm('dbapp.change_flighttime') # type: ignore

    if request.method == 'POST':
        if not can_change:
            messages.error(request, "У вас нет прав на редактирование.")
            return redirect('airports')
        
        form = FlightTimeForm(request.POST, instance=flight_time)
        if form.is_valid():
            if flight.departure_airport.pk != 1:
                form.fields.pop('departure_airport')
            if flight.arrival_airport.pk != 1:
                form.fields.pop('arrival_airport')

            form.save()
            log_action(request.user, flight_time, CHANGE, change_message=f"Изменены временные отметки рейса {flight}")
            messages.success(request, "Временные отметки успешно обновлены!")
            return redirect('flights')
    else:
        form = FlightTimeForm(instance=flight_time)
        if not can_change:
            for field in form.fields.values():
                field.disabled = True
        else:
            if flight.departure_airport.pk != 1:
                form.fields.pop('actual_departure', None)
            if flight.arrival_airport.pk != 1:
                form.fields.pop('actual_arrival', None)

    return render(request, 'flight_time_form.html', {
        'form': form,
        'flight': flight,
        'title': f'Редактировать временные метки рейса {flight}'
    })

@permission_required('dbapp.view_passenger')
def passengers(request: HttpRequest):
    return render(request, 'passengers.html', {'passengers': Passenger.objects.all()})

@transaction.atomic
@permission_required('dbapp.add_passenger')
def passenger_add(request: HttpRequest):
    if request.method == 'POST':
        form = PassengerForm(request.POST)
        if form.is_valid():
            instance = form.save()
            log_action(request.user, instance, ADDITION)

            messages.success(request, 'Пассажир успешно добавлен!')
            return redirect('passengers')
    else:
        form = PassengerForm()
        form.fields.pop('check_in_passed')
        form.fields.pop('boarding_passed')
        form.fields.pop('is_removed')

    return render(request, 'passenger_form.html', {
        'form': form,
        'title': 'Добавить пассажира'
    })

@transaction.atomic
@permission_required('dbapp.change_passenger')
def passenger_edit(request: HttpRequest, passenger_id: int):
    passenger = get_object_or_404(Passenger, pk=passenger_id)
    
    can_change_all = request.user.has_perm('dbapp.change_passenger') # type: ignore
    can_change_check_in_passed  = request.user.has_perm('dbapp.change_check_in_passed_passenger') # type: ignore
    can_change_boarding_passed = request.user.has_perm('change_boarding_passed_passenger') # type: ignore

    if request.method == 'POST':
        if not can_change_all:
            messages.error(request, "У вас нет прав на редактирование.")
            return redirect('passengers')

        form = PassengerForm(request.POST, instance=passenger)
        if form.is_valid():
            instance: Passenger = form.save(commit=False)
            old_passenger = Passenger.objects.get(pk=passenger_id)

            if not can_change_all:
                if not can_change_check_in_passed:
                    instance.check_in_passed = old_passenger.check_in_passed
                if not can_change_boarding_passed:
                    instance.boarding_passed = old_passenger.boarding_passed

                editable_fields = []
                if can_change_check_in_passed:
                    editable_fields.append('check_in_passed')
                if can_change_boarding_passed:
                    editable_fields.append('boarding_passed')

                for field in form.fields.keys():
                    if field not in editable_fields:
                        setattr(instance, field, getattr(old_passenger, field))

            instance = form.save()
            log_action(request.user, instance, CHANGE, old_instance=old_passenger)

            messages.success(request, "Пассажир успешно обновлён!")
            return redirect('passengers')
    else:
        form = PassengerForm(instance=passenger)
        if not can_change_all:
            for field in form.fields.values():
                field.disabled = True

    return render(request, 'passenger_form.html', {
        'form': form,
        'title': f'Редактировать пассажира: {passenger}'
    })

@transaction.atomic
@permission_required('dbapp.delete_passenger')
def passenger_delete(request: HttpRequest, passenger_id: int):
    passenger = get_object_or_404(Passenger, pk=passenger_id)

    if (Baggage.objects.filter(passenger=passenger).exists() or
        BoardingPass.objects.filter(passenger=passenger)):
        messages.error(request,
            'Невозможно удалить пассажира, пока у него зарегистрирован багаж и имеется посадочный талон'
        )
        return redirect('passengers')

    passenger.delete()
    log_action(request.user, passenger, DELETION)

    messages.success(request, "Пассажир успешно удалён!")
    return redirect('passengers')

@permission_required('dbapp.view_baggage')
def baggage(request: HttpRequest, passenger_id: int):
    passenger = get_object_or_404(Passenger, pk=passenger_id)

    return render(request, 'baggage.html', {
        'passenger': passenger,
        'baggage': Baggage.objects.filter(passenger=passenger)
    })

@transaction.atomic
@permission_required('dbapp.add_baggage')
def baggage_add(request: HttpRequest, passenger_id: int):
    passenger = get_object_or_404(Passenger, pk=passenger_id)

    if request.method == 'POST':
        form = BaggageForm(request.POST)
        if form.is_valid():
            instance: Baggage = form.save(commit=False)
            instance.passenger = passenger
            instance.save()
            log_action(request.user, instance, ADDITION)

            messages.success(request, 'Багаж успешно добавлен!')
            return redirect('baggage', passenger_id=passenger_id)
    else:
        form = BaggageForm()

    return render(request, 'baggage_form.html', {
        'form': form,
        'title': 'Добавить багаж',
        'passenger': passenger
    })

@transaction.atomic
@permission_required('dbapp.change_baggage')
def baggage_edit(request: HttpRequest, passenger_id: int, baggage_id: int):
    passenger = get_object_or_404(Passenger, pk=passenger_id)
    baggage = get_object_or_404(Baggage, pk=baggage_id)
    can_change = request.user.has_perm('dbapp.change_baggage') # type: ignore

    if request.method == 'POST':
        if not can_change:
            messages.error(request, "У вас нет прав на редактирование.")
            return redirect('baggage', passenger_id=passenger_id)

        form = BaggageForm(request.POST, instance=baggage)
        if form.is_valid():
            old_baggage = Baggage.objects.get(pk=baggage_id)
            instance = form.save()
            log_action(request.user, instance, CHANGE, old_instance=old_baggage)

            messages.success(request, "Багаж успешно обновлён!")
            return redirect('baggage', passenger_id=passenger_id)
    else:
        form = BaggageForm(instance=baggage)
        if not can_change:
            for field in form.fields.values():
                field.disabled = True

    return render(request, 'baggage_form.html', {
        'form': form,
        'title': f'Редактировать багаж: {baggage}',
        'passenger': passenger
    })

@transaction.atomic
@permission_required('dbapp.delete_baggage')
def baggage_delete(request: HttpRequest, baggage_id: int):
    baggage = get_object_or_404(Baggage, pk=baggage_id)

    baggage.delete()
    log_action(request.user, baggage, DELETION)

    messages.success(request, "Багаж успешно удалён!")
    return redirect('baggage', passenger_id=baggage.passenger.pk)

@transaction.atomic
@permission_required('dbapp.view_boardingpass')
def boarding_pass_edit(request: HttpRequest, passenger_id: int):
    passenger = get_object_or_404(Passenger, pk=passenger_id)
    
    try:
        boarding_pass = BoardingPass.objects.get(id=passenger)
        is_edit = True
    except BoardingPass.DoesNotExist:
        boarding_pass = BoardingPass(id=passenger)
        is_edit = False

    flight: Flight = passenger.flight
    airplane: Airplane = flight.airplane
    layout = airplane.layout
    rows = airplane.rows
    
    occupied_seats = BoardingPass.objects.filter(
        id__flight=flight
    ).exclude(id=passenger).values_list('seat', flat=True)

    can_add = request.user.has_perm('dbapp.add_boardingpass') # type: ignore
    can_change = request.user.has_perm('dbapp.change_boardingpass') # type: ignore
    can_delete = request.user.has_perm('dbapp.delete_boardingpass') # type: ignore
    
    if is_edit:
        can_modify = can_change or can_delete
        mode = 'edit'
    else:
        can_modify = can_add
        mode = 'add'

    form = BoardingPassForm(instance=boarding_pass)

    if request.method == 'POST' and can_modify:
        action = request.POST.get('action')
        
        if action == 'save' and (can_add or can_change):
            form = BoardingPassForm(request.POST, instance=boarding_pass)
            if form.is_valid():
                instance = form.save()
                
                if is_edit:
                    log_action(request.user, instance, CHANGE)
                    messages.success(request, "Посадочный талон успешно обновлён!")
                else:
                    log_action(request.user, instance, ADDITION)
                    messages.success(request, "Посадочный талон успешно создан!")
                
                return redirect('boarding_pass_edit', passenger_id=passenger_id)
        
        elif action == 'clear' and can_delete and is_edit and boarding_pass.seat:
            old_seat = boarding_pass.seat
            boarding_pass.seat = ''
            boarding_pass.save()
            log_action(request.user, boarding_pass, DELETION)
            messages.success(request, f"Место {old_seat} успешно освобождено!")
            return redirect('boarding_pass_edit', passenger_id=passenger_id)

    return render(request, 'boarding_pass_form.html', {
        'form': form,
        'passenger': passenger,
        'boarding_pass': boarding_pass,
        'layout': layout,
        'rows': rows,
        'occupied_seats': list(occupied_seats),
        'title': 'Посадочный талон',
        'mode': mode,
        'can_add': can_add,
        'can_change': can_change,
        'can_delete': can_delete,
        'can_modify': can_modify,
        'is_edit': is_edit,
    })

@permission_required('dbapp.view_backuplog') 
def backup_list(request: HttpRequest):
    backups = BackupLog.objects.all()
    return render(request, 'backup_list.html', {'backups': backups})

@permission_required('dbapp.add_backuplog')
def create_backup(request: HttpRequest):
    try:
        from django.core.management import call_command
        call_command('backup_database', '--type', 'manual')
        messages.success(request, "Резервная копия успешно создана")
    except Exception as e:
        messages.error(request, f"Ошибка создания бэкапа: {str(e)}")
    
    return redirect('backup_list')

@permission_required('dbapp.delete_backuplog')
def backup_delete(request: HttpRequest, backup_id: int):
    backup = get_object_or_404(BackupLog, pk=backup_id)
    
    try:
        if os.path.exists(backup.file_path):
            os.remove(backup.file_path)
        
        backup.delete()
        messages.success(request, "Резервная копия удалена")
    except Exception as e:
        messages.error(request, f"Ошибка удаления: {str(e)}")
    
    return redirect('backup_list')

@permission_required('dbapp.view_backuplog')
def backup_download(request: HttpRequest, backup_id: int):
    backup = get_object_or_404(BackupLog, pk=backup_id)
    
    if os.path.exists(backup.file_path):
        with open(backup.file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{backup.filename}"'
            return response
    else:
        messages.error(request, "Файл бэкапа не найден")
        return redirect('backup_list')