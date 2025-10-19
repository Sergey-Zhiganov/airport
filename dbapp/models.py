import re
from typing import cast
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_delete
from fernet_fields import EncryptedTextField

def validate_phone(value: str):
    digits = re.sub(r'\D', "", value)
    if len(digits) != 11:
        raise ValidationError(
            "Телефон должен содержать 11 цифр. Пример: 79254717170"
        )

class BackupLog(models.Model):
    BACKUP_TYPES = [
        ('daily', 'Ежедневный'),
        ('manual', 'Ручной'),
    ]
    
    STATUS_CHOICES = [
        ('success', 'Успешно'),
        ('error', 'Ошибка'),
        ('running', 'Выполняется'),
    ]
    
    backup_type = models.CharField('Тип бэкапа', max_length=10, choices=BACKUP_TYPES)
    filename = models.CharField('Имя файла', max_length=255)
    file_path = models.CharField('Путь к файлу', max_length=500)
    file_size = models.BigIntegerField('Размер файла', null=True, blank=True)
    status = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES)
    error_message = models.TextField('Сообщение об ошибке', blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Лог резервного копирования'
        verbose_name_plural = 'Логи резервного копирования'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_backup_type_display()} - {self.created_at.strftime('%d.%m.%Y %H:%M')}" # type: ignore

class Worker(AbstractUser):
    middle_name = models.CharField(
        "Отчество",
        max_length=100,
        null=True,
        help_text='Введите отчество (если имеется)'
    )
    phone = EncryptedTextField(
        "Телефон",
        max_length=1024,
        validators=[validate_phone],
        help_text="Введите номер телефона в формате +7 (XXX) XXX-XX-XX"
    )

    def save(self, *args, **kwargs):
        if self.phone:
            self.phone = re.sub(r"\D", "", self.phone)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"

    def __str__(self):
        return f'{self.last_name} {self.first_name} {self.middle_name}'

class CheckInDesk(models.Model):
    number = models.CharField(
        "Номер стойки регистрации",
        max_length=20,
        help_text='Введите номер стойки регистрации'
    )
    worker = models.OneToOneField(
        Worker,
        models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Сотрудник',
        help_text='Выберите сотрудника, который будет назначен на эту стойку'
    )
    is_active = models.BooleanField(
        'Стойка активна',
        default=False,
        help_text='Отметьте, активна ли стойка регистрации'
    )

    def clean(self):
        worker = cast(Worker, self.worker)
        if self.worker:
            if not worker.groups.filter(id__in=[1, 3]).exists():
                raise ValidationError({
                    'worker': 'Можно выбрать только сотрудника с должностью «Регистратор» или «Старший смены»'
                })
        
            if not worker.is_active:
                raise ValidationError({
                    'worker': 'Назначать можно только активного сотрудника'
                })

    class Meta:
        verbose_name = 'Стойка регистрации'
        verbose_name_plural = 'Стойки регистрации'
        permissions = [
            ("view_own_checkindesk", "Можно видеть только свою стойку"),
            ("change_worker_checkindesk", "Можно изменить Сотрудник"),
            ("change_is_active_checkindesk", "Можно изменить Стойка активна")
        ]

    def __str__(self) -> str:
        return f'Стойка {self.number}'

class Gate(models.Model):
    number = models.CharField(
        'Номер посадочного выхода',
        max_length=20,
        help_text='Введите номер посадочного выхода'
    )
    worker = models.ForeignKey(
        Worker,
        models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Сотрудник',
        help_text='Выберите сотрудника, который будет назначен на этот посадочный выход'
    )
    is_active = models.BooleanField(
        'Посадочный выход активен',
        default=False,
        help_text='Отметьте, активен ли посадочный выход'
    )

    def clean(self):
        worker = cast(Worker, self.worker)
        if self.worker and not worker.groups.filter(id__in=[2, 3]).exists():
            raise ValidationError({
                'worker': 'Можно выбрать только сотрудника с должностью «Агент посадки» или «Старший смены»'
            })

    class Meta:
        verbose_name = 'Посадочный выход'
        verbose_name_plural = 'Посадочные выходы'
        permissions = [
            ("view_own_gate", "Можно видеть только свой выход"),
            ("change_worker_gate", "Можно изменить Сотрудник"),
            ('change_is_active_gate', 'Можно изменить Стойка активна')
        ]
    
    def __str__(self) -> str:
        return f'Выход {self.number}'

class Airline(models.Model):
    name = models.CharField(
        'Название',
        max_length=255,
        help_text='Введите название авиакомпании'
    )
    IATA_code = models.CharField(
        'IATA-код',
        max_length=2,
        unique=True,
        help_text='Введите IATA-код авиакомпании'
    )
    ICAO_code = models.CharField(
        'ICAO-код',
        max_length=3,
        unique=True,
        help_text='Введите ICAO-код авиакомпании'
    )
    contact_person = models.CharField(
        'Контактное лицо',
        max_length=255,
        help_text='Введите ФИО контактного лица'
    )
    contact_phone = models.CharField(
        'Телефон контактного лица',
        max_length=30,
        help_text='Введите телефон контактного лица в формате +7 (XXX) XXX-XX-XX',
        validators=[validate_phone]
    )
    contact_email = models.EmailField(
        'Почта контактного лица',
        max_length=255,
        help_text='Введите почту контактного лица'
    )

    class Meta:
        verbose_name = 'Авикомпания'
        verbose_name_plural = 'Авиакомпании'

    def __str__(self):
        return self.name

class Airplane(models.Model):
    tail_number = models.CharField(
        'Бортовой номер',
        max_length=20,
        unique=True,
        help_text='Введите бортовой номер самолета'
    )
    name = models.CharField(
        'Модель',
        max_length=100,
        help_text='Введите модель самолета'
    )
    airline = models.ForeignKey(
        Airline,
        models.PROTECT,
        verbose_name='Авиакомпания-владелец',
        help_text='Выберите авиакомпанию-владельца самолета'
    )
    layout = models.CharField(
        'Компоновка',
        max_length=20,
        help_text='Введите схему, например: 3-3 или 2-2-2'
    )
    rows = models.PositiveIntegerField(
        'Количество рядов',
        help_text='Введите количество рядов (например: 15)'
    )

    class Meta:
        verbose_name = 'Самолет'
        verbose_name_plural = 'Самолеты'

    def __str__(self):
        return f'{self.name} ({self.tail_number})'

class Airport(models.Model):
    name = models.CharField(
        'Название',
        max_length=255,
        help_text='Введите название аэропорта'
    )
    IATA_code = models.CharField(
        'IATA-код',
        max_length=3,
        unique=True,
        help_text='Введите IATA-код аэропорта'
    )
    ICAO_code = models.CharField(
        'ICAO-код',
        max_length=4,
        unique=True,
        help_text='Введите ICAO-код аэропорта'
    )

    class Meta:
        verbose_name = 'Аэропорт'
        verbose_name_plural = 'Аэропорты'

    def __str__(self) -> str:
        return self.name

class FlightStatus(models.Model):
    name = models.CharField(
        'Название',
        max_length=50,
        help_text='Введите название статуса'
    )

    class Meta:
        verbose_name = 'Статус рейса'
        verbose_name_plural = 'Статусы рейсов'

    def __str__(self) -> str:
        return self.name

class Flight(models.Model):
    number = models.IntegerField(
        'Номер рейса',
        help_text='Введите номер рейса'
    )
    airplane = models.ForeignKey(
        Airplane,
        models.PROTECT,
        verbose_name='Самолет',
        help_text='Выберите самолет, который будет выполнять данный рейс'
    )
    planned_departure = models.DateTimeField(
        'Запланированное время вылета',
        null=True,
        blank=True,
        help_text='Введите планируемое время вылета (если рейс вылетает из данного аэропорта)'
    )
    planned_arrival = models.DateTimeField(
        'Запланированное время прибытия',
        null=True,
        blank=True,
        help_text='Введите планируемое время прибытия (если рейс прибывает в данный аэропорт)'
    )
    departure_airport = models.ForeignKey(
        Airport,
        models.PROTECT,
        'departures',
        verbose_name='Аэропорт вылета',
        help_text='Выберите аэропорт вылета рейса'
    )
    arrival_airport = models.ForeignKey(
        Airport,
        models.PROTECT,
        'arrivals',
        verbose_name='Аэропорт прибытия',
        help_text='Выберите аэропорт прибытия рейса'
    )
    flight_status = models.ForeignKey(
        FlightStatus,
        models.PROTECT,
        verbose_name='Статус рейса',
        help_text='Выберите статус рейса'
    )

    class Meta:
        verbose_name = 'Рейс'
        verbose_name_plural = 'Рейсы'
        permissions = [
            ('change_flight_status', 'Можно изменить Статус рейса')
        ]

    def __str__(self) -> str:
        return f'{self.airplane.airline.IATA_code} {self.number}'
    
    def clean(self):
        errors = {}

        if self.departure_airport.pk == 1 and not self.planned_departure:
            errors['planned_departure'] = 'Для рейсов, вылетающих из данного аэропорта, необходимо указать время вылета'
        
        if self.arrival_airport.pk == 1 and not self.planned_arrival:
            errors['planned_arrival'] = 'Для рейсов, прибывающие в данный аэропорт, неоходимо указать время прибытия'

class CheckInDeskFlight(models.Model):
    desk = models.ForeignKey(
        CheckInDesk,
        models.PROTECT,
        verbose_name='Стойка регистрации',
        help_text='Выберите стойку регистрации, которая будет обслуживать указанный рейс'
    )
    flight = models.ForeignKey(
        Flight,
        models.PROTECT,
        verbose_name='Рейс',
        help_text='Выберите рейс, который будет обслуживаться указанной стойкой регистрации'
    )
    is_active = models.BooleanField(
        'Открыта регистрация на рейс',
        default=False,
        help_text='Отметьте, открыта ли регистрация на рейс'
    )

    class Meta:
        verbose_name = 'Стойка регистрации, обслуживающая рейс'
        verbose_name_plural = 'Стойки регистрации, обслуживающие рейсы'
        permissions = [
            ('change_is_active_checkindeskflight', 'Можно изменить Открыта регистрация на рейс')
        ]
        unique_together = ('desk', 'flight')

class GateFlight(models.Model):
    gate = models.ForeignKey(
        Gate,
        models.PROTECT,
        verbose_name='Посадочный выход',
        help_text='Выберите посадочный выход, который будет обслуживать указанный рейс'
    )
    flight = models.ForeignKey(
        Flight,
        models.PROTECT,
        verbose_name='Рейс',
        help_text='Выберите рейс, который будет обслуживаться указанным посадочным выходом'
    )
    is_active = models.BooleanField(
        'Выход открыт для посадки',
        default=False,
        help_text='Отметьте, открыт ли выход для посадки пассажиров в самолет'
    )

    class Meta:
        verbose_name = 'Посадочный выход, обслуживающий рейс'
        verbose_name_plural = 'Посадочные выходы, обслуживающие рейсы'
        permissions = [
            ('change_is_acitve_gateflight', 'Можно изменить Выход открыт для посадки')
        ]

class FlightTime(models.Model):
    id = models.OneToOneField(
        Flight,
        models.CASCADE,
        primary_key=True,
        editable=True,
        verbose_name='Рейс',
        help_text='Выберите рейс, для которого будут назначены указанные временные метки'
    )
    actual_departure = models.DateTimeField(
        'Фактическое время вылета',
        null=True,
        help_text='Введите фактическое время вылета рейса (если вылет из данного аэропорта)'
    )
    actual_arrival = models.DateTimeField(
        'Фактическое время прибытия',
        null=True,
        help_text='Введите фактическое время прибытия рейса (если вылет из другого аэропорта)'
    )
    check_in_open_time = models.DateTimeField(
        'Время начала регистрации',
        null=True
    ) # readonly
    check_in_close_time = models.DateTimeField(
        'Время окончания регистрации',
        null=True
    ) # readonly
    boarding_open_time = models.DateTimeField(
        'Время начала посадки',
        null=True
    ) # readonly
    boarding_close_time = models.DateTimeField(
        'Время окончания посадки',
        null=True
    ) # readonly

    class Meta:
        verbose_name = 'Временные отметки рейса'
        verbose_name_plural = 'Временные отметки рейсов'

class Passenger(models.Model):
    first_name = models.CharField(
        'Имя',
        max_length=100,
        help_text='Введите имя пассажира'
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=100,
        help_text='Введите фамилию пассажира'
    )
    middle_name = models.CharField(
        'Отчество',
        max_length=100,
        null=True,
        blank=True,
        help_text='Введите отчество пассажира (если имеется)'
    )
    passport = EncryptedTextField(
        'Паспорт',
        max_length=1024,
        help_text='Введите паспорт пассажира'
    )
    flight = models.ForeignKey(
        Flight,
        models.PROTECT,
        verbose_name='Рейс',
        help_text='Выберите рейс, на который будет назначен пассажир'
    )
    check_in_passed = models.BooleanField(
        'Пройдена регистрация',
        default=False,
        help_text='Отметьте, пройдена ли регистрация пассажиром'
    )
    boarding_passed = models.BooleanField(
        'Посадка выполнена',
        default=False,
        help_text='Отметьте, прошел ли пассажир посадку в самолет'
    )
    is_removed = models.BooleanField(
        'Пассажир снят с рейса',
        default=False,
        help_text='Отметьте, снят ли пассажир с рейса'
    )

    class Meta:
        verbose_name = 'Пассажир'
        verbose_name_plural = 'Пассажиры'
        permissions = [
            ('change_check_in_passed_passenger', 'Можно изменить Пройдена регистрация'),
            ('change_boarding_passed_passenger', 'Можно изменить Посадка выполнена')
        ]

    def __str__(self):
        return f'{self.last_name} {self.first_name} {self.middle_name}'

class Baggage(models.Model):
    passenger = models.ForeignKey(
        Passenger,
        models.PROTECT,
        verbose_name='Пассажир-владелец',
        help_text='Выберите пассажира-владельца багажа'
    )
    weight = models.DecimalField(
        'Вес',
        max_digits=5,
        decimal_places=2,
        help_text='Введите вес багажа (кг)'
    )
    is_removed = models.BooleanField(
        'Багаж снят с рейса',
        default=False,
        help_text='Отметьте, снят ли багаж с рейса'
    )

    class Meta:
        verbose_name = 'Багаж'
        constraints = [
            models.CheckConstraint(
                name='weight_more_0',
                check=models.Q(weight__gte=0.1)
            )
        ]
        permissions = [
            ('change_passenger', 'Можно изменить Пассажир-владелец'),
            ('change_weight', 'Можно изменить Вес')
        ]

    def __str__(self):
        return f'Багаж #{self.pk}'

class BoardingPass(models.Model):
    id = models.OneToOneField(
        Passenger,
        models.PROTECT,
        primary_key=True,
        editable=True,
        verbose_name='Пассажир',
        help_text='Выберите пассажира, который будет указан в посадочном талоне'
    )
    seat = models.CharField(
        'Место',
        max_length=5,
        help_text='Выберите место, на которое будет назначен пассажир'
    )

    class Meta:
        verbose_name = 'Посадочный талон'
        verbose_name_plural = 'Посадочные талоны'

@receiver(pre_save, sender='dbapp.Worker')
def deactivate_worker(sender, instance, **kwargs):
    if instance.pk:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.is_active and not instance.is_active:
            CheckInDesk.objects.filter(worker=instance).update(worker=None, is_active=False)


@receiver(post_delete, sender='dbapp.Worker')
def delete_worker(sender, instance, **kwargs):
    CheckInDesk.objects.filter(worker=instance).update(worker=None, is_active=False)