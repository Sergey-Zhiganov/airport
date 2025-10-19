from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from matplotlib import widgets

from dbapp.models import Airline, Airplane, Airport, Baggage, BoardingPass, CheckInDesk, CheckInDeskFlight, Flight, FlightTime, Gate, GateFlight, Passenger, Worker

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Логин",
        max_length=150,
        widget=forms.TextInput({'class': 'form-control'})
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput({'class': 'form-control'})
    )

    class Meta:
        model = Worker
        fields = ['username', 'password']

class WorkerCreateForm(UserCreationForm):
    class Meta:
        model = Worker
        fields = [
            'username', 'first_name', 'last_name', 'middle_name',
            'phone', 'email', 'is_active', 'is_staff', 'is_superuser', 'groups'
        ]
        widgets = {
            'username': forms.TextInput({'class': 'form-control'}),
            'first_name': forms.TextInput({'class': 'form-control'}),
            'last_name': forms.TextInput({'class': 'form-control'}),
            'middle_name': forms.TextInput({'class': 'form-control'}),
            'phone': forms.TextInput({'class': 'form-control', 'phone': 'true'}),
            'email': forms.EmailInput({'class': 'form-control'}),
            'is_active': forms.CheckboxInput(),
            'is_staff': forms.CheckboxInput(),
            'is_superuser': forms.CheckboxInput(),
            'groups': forms.CheckboxSelectMultiple(),
            'password1': forms.PasswordInput({'class': 'form-control'}),
            'password2': forms.PasswordInput({'class': 'form-control'}),
        }
        help_texts = {
            'groups': 'Выберите должности для сотрудника',
        }

class WorkerEditForm(forms.ModelForm):
    password = forms.CharField(
        label='Пароль',
        required=False,
        widget=forms.PasswordInput({'class': 'form-control'}),
        help_text='Введите новый пароль, если хотите изменить'
    )

    class Meta:
        model = Worker
        fields = [
            'username', 'first_name', 'last_name', 'middle_name',
            'phone', 'email', 'is_active', 'is_staff', 'is_superuser', 'groups', 'password'
        ]
        widgets = {
            'username': forms.TextInput({'class': 'form-control'}),
            'first_name': forms.TextInput({'class': 'form-control'}),
            'last_name': forms.TextInput({'class': 'form-control'}),
            'middle_name': forms.TextInput({'class': 'form-control'}),
            'phone': forms.TextInput({'class': 'form-control', 'phone': 'true'}),
            'email': forms.EmailInput({'class': 'form-control'}),
            'is_active': forms.CheckboxInput(),
            'is_staff': forms.CheckboxInput(),
            'is_superuser': forms.CheckboxInput(),
            'groups': forms.CheckboxSelectMultiple(),
        }

    def save(self, commit=True):
        user: Worker = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        else:
            old_user = Worker.objects.get(pk=user.pk)
            user.password = old_user.password
        
        if commit:
            user.save()
            self.save_m2m()
        return user

class CheckInDeskForm(forms.ModelForm):
    worker = forms.ModelChoiceField(
        queryset=Worker.objects.filter(groups__id__in=[1, 3]),
        required=False,
        label='Сотрудник',
        help_text='Выберите сотрудника, который будет назначен на эту стойку'
    )
    class Meta:
        model = CheckInDesk
        fields = ['number', 'worker', 'is_active']
        widgets = {
            'number': forms.TextInput({'class': 'form-control'}),
            'worker': forms.Select({'class': 'form-control'}),
            'is_active': forms.CheckboxInput()
        }

class GateForm(forms.ModelForm):
    worker = forms.ModelChoiceField(
        queryset=Worker.objects.filter(groups__id__in=[2, 3]),
        required=False,
        label='Сотрудник',
        help_text='Выберите сотрудника, который будет назначен на этот выход'
    )
    class Meta:
        model = Gate
        fields = ['number', 'worker', 'is_active']
        widgets = {
            'number': forms.TextInput({'class': 'form-control'}),
            'worker': forms.Select({'class': 'form-control'}),
            'is_active': forms.CheckboxInput()
        }

class AirlineForm(forms.ModelForm):
    class Meta:
        model = Airline
        fields = [
            'name', 'IATA_code', 'ICAO_code',
            'contact_person', 'contact_phone', 'contact_email'
        ]
        widgets = {
            'name': forms.TextInput({'class': 'form-control'}),
            'IATA_code': forms.TextInput({'class': 'form-control'}),
            'ICAO_code': forms.TextInput({'class': 'form-control'}),
            'contact_person': forms.TextInput({'class': 'form-control'}),
            'contact_phone': forms.TextInput({'class': 'form-control', 'phone': 'true'}),
            'contact_email': forms.TextInput({'class': 'form-control'})
        }

class AirplaneForm(forms.ModelForm):
    class Meta:
        model = Airplane
        fields = ['tail_number', 'name', 'airline', 'layout', 'rows']
        widgets = {
            'tail_number': forms.TextInput({'class': 'form-control'}),
            'name': forms.TextInput({'class': 'form-control'}),
            'airline': forms.Select({'class': 'form-control'}),
            'layout': forms.TextInput({'class': 'form-control'}),
            'rows': forms.TextInput({'class': 'form-control'}),
        }

class AirportForm(forms.ModelForm):
    class Meta:
        model = Airport
        fields = ['name', 'IATA_code', 'ICAO_code']
        widgets = {
            'name': forms.TextInput({'class': 'form-control'}),
            'IATA_code': forms.TextInput({'class': 'form-control'}),
            'ICAO_code': forms.TextInput({'class': 'form-control'})
        }

class FlightForm(forms.ModelForm):
    class Meta:
        model = Flight
        fields = [
            'number', 'airplane', 'departure_airport',
            'planned_departure', 'arrival_airport',
            'planned_arrival', 'flight_status'
        ]
        widgets = {
            'number': forms.NumberInput(attrs={'class': 'form-control'}),
            'airplane': forms.Select(attrs={'class': 'form-control'}),
            'planned_departure': forms.DateTimeInput(attrs={'class': 'form-control','type': 'datetime-local'}),
            'planned_arrival': forms.DateTimeInput(attrs={'class': 'form-control','type': 'datetime-local'}),
            'departure_airport': forms.Select(attrs={'class': 'form-control'}),
            'arrival_airport': forms.Select(attrs={'class': 'form-control'}),
            'flight_status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        is_edit = kwargs.pop('is_edit', False)
        super().__init__(*args, **kwargs)

        allowed_statuses = [1, 6, 7, 8, 9]

        instance = kwargs.get('instance')
        if instance and instance.flight_status_id not in allowed_statuses:
            allowed_statuses.append(instance.flight_status_id)

        self.fields['flight_status'].queryset = (  # type: ignore
            self.fields['flight_status'].queryset.filter(pk__in=allowed_statuses) # type: ignore
        )

        if not is_edit:
            self.fields['flight_status'].initial = 1

class CheckInDeskFlightForm(forms.ModelForm):
    flight = forms.ModelChoiceField(
        queryset=Flight.objects.filter(flight_status__lt=9),
        label='Рейс',
        help_text='Выберите рейс, который будет обслуживаться этой стойкой'
    )

    class Meta:
        model = CheckInDeskFlight
        fields = ['flight', 'is_active']
        widgets = {
            'is_active': forms.CheckboxInput()
        }

class GateFlightForm(forms.ModelForm):
    flight = forms.ModelChoiceField(
        queryset=Flight.objects.exclude(flight_status__in=[1, 2, 9]),
        label='Рейс',
        help_text='Выберите рейс, который будет обслуживаться этим посадочным выходом'
    )

    class Meta:
        model = GateFlight
        fields = ['flight', 'is_active']
        widgets = {
            'is_active': forms.CheckboxInput()
        }

class FlightTimeForm(forms.ModelForm):
    class Meta:
        model = FlightTime
        fields = [
            'actual_departure',
            'actual_arrival',
            'check_in_open_time',
            'check_in_close_time',
            'boarding_open_time',
            'boarding_close_time'
        ]
        widgets = {
            'actual_departure': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                }
            ),
            'actual_arrival': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                }
            ),
            'check_in_open_time': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                    'readonly': 'readonly'
                }
            ),
            'check_in_close_time': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                    'readonly': 'readonly'
                }
            ),
            'boarding_open_time': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                    'readonly': 'readonly'
                }
            ),
            'boarding_close_time': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                    'readonly': 'readonly'
                }
            )
        }

class PassengerForm(forms.ModelForm):
    class Meta:
        model = Passenger
        fields = [
            'first_name',
            'last_name',
            'middle_name',
            'passport',
            'flight',
            'check_in_passed',
            'boarding_passed',
            'is_removed'
        ]
        widgets = {
            'first_name': forms.TextInput({'class': 'form-control'}),
            'last_name': forms.TextInput({'class': 'form-control'}),
            'middle_name': forms.TextInput({'class': 'form-control'}),
            'passport': forms.TextInput({'class': 'form-control'}),
            'flight': forms.Select({'class': 'form-control'}),
            'check_in_passed': forms.CheckboxInput(),
            'boarding_passed': forms.CheckboxInput(),
            'is_removed': forms.CheckboxInput()
        }

class BaggageForm(forms.ModelForm):
    class Meta:
        model = Baggage
        fields = ['weight', 'is_removed']
        widgets = {
            'weight': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'is_removed': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class BoardingPassForm(forms.ModelForm):
    class Meta:
        model = BoardingPass
        fields = ['seat']
        widgets = {
            'seat': forms.HiddenInput()
        }