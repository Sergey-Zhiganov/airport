from datetime import datetime
from dbapp.models import *

def run():
    Worker.objects.bulk_create([
        Worker(
            firstname="Афанасия",
            lastname="Горчакова",
            middle_name="Никандровна",
            phone="79856007366",
            email="afanasiya1966@rambler.ru",
            position_id=1,
            password="6c126D595*"
        ),
        Worker(
            firstname="Любовь",
            lastname="Квитко",
            middle_name="Степановна",
            phone="79722849424",
            email="lyubov.kvitko@mail.ru",
            position_id=1,
            password="53065B991#"
        ),
        Worker(
            firstname="Ульяна",
            lastname="Азаренкова",
            middle_name="Тарасовна",
            phone="79759244894",
            email="ulyana14121976@yandex.ru",
            position_id=2,
            password="A1a086100@"
        ),
        Worker(
            firstname="Дмитрий",
            lastname="Жилов",
            middle_name="Егорович",
            phone="79145455669",
            email="dmitriy45@outlook.com",
            position_id=2,
            password="9d50B1032$"
        ),
        Worker(
            firstname="Антон",
            lastname="Рытин",
            middle_name="Юрьевич",
            phone="79098295865",
            email="anton09061968@gmail.com",
            position_id=3,
            password="c1bE7c243^"
        ),
        Worker(
            firstname="Анна",
            lastname="Мажулина",
            middle_name="Константиновна",
            phone="79855689276",
            email="anna2522@outlook.com",
            position_id=4,
            password="30d67Ff40%"
        ),
        Worker(
            firstname="Сергей",
            lastname="Жиганов",
            middle_name="Алексеевич",
            phone="79254717170",
            email="isip_s.a.zhiganov@mpt.ru",
            position_id=5,
            password="SergeyZhiganov5+"
        ),
    ])

    CheckInDesk.objects.bulk_create([
        CheckInDesk(desk_number="01", worker_id=1),
        CheckInDesk(desk_number="02"),
        CheckInDesk(desk_number="03", worker_id=2, is_active=True),
        CheckInDesk(desk_number="04")
    ])

    Gate.objects.bulk_create([
        Gate(gate_number="01"),
        Gate(gate_number="02", worker_id=3),
        Gate(gate_number="03"),
        Gate(gate_number="04", worker_id=4, is_active=True),
    ])

    Airline.objects.bulk_create([
        Airline(
            name="Pirozhok Airlines",
            IATA_code="PI",
            ICAO_code="PRZ",
            contact_person="Владимир Пирожков",
            contact_phone="79876543210",
            contact_email="contact@pirozhok.aero"
        ),
        Airline(
            name="Gopnik Air",
            IATA_code="GP",
            ICAO_code="GPK",
            contact_person="Серёга на районе",
            contact_phone="79998887766",
            contact_email="info@gopair.ru"
        ),
        Airline(
            name="Cheburek Avia",
            IATA_code="CH",
            ICAO_code="CHB",
            contact_person="Арсен Магомедов",
            contact_phone="79261112233",
            contact_email="support@cheburekavia.com"
        ),
        Airline(
            name="FlyPodolsk",
            IATA_code="FP",
            ICAO_code="FPD",
            contact_person="Сергей Жиганов",
            contact_phone="79254717170",
            contact_email="info@flypodolsk.ru"
        ),
    ])

    Airplane.objects.bulk_create([
        Airplane(tail_number="RA-PI001", name="Sukhoi Superjet 100", airline_id=1),
        Airplane(tail_number="VP-GP01", name="Airbus A320", airline_id=2),
        Airplane(tail_number="CH-CB01", name="Boeing 737 Cheburek Edition", airline_id=3),
        Airplane(tail_number="RA-PDL01", name="Ту-214 Podolsk Edition", airline_id=4),
    ])

    Airport.objects.bulk_create([
        Airport(IATA_code="SVO", ICAO_code="UUEE", name="Москва Шереметьево"),
        Airport(IATA_code="DME", ICAO_code="UUDD", name="Москва Домодедово"),
        Airport(IATA_code="VKO", ICAO_code="UUWW", name="Москва Внуково"),
        Airport(IATA_code="PDK", ICAO_code="UUPD", name="Подольск International"),
        Airport(IATA_code="BAL", ICAO_code="UUBA", name="Балашиха Grand Airhub"),
        Airport(IATA_code="RYA", ICAO_code="UURY", name="Рязань Skyport"),
        Airport(IATA_code="KOL", ICAO_code="UUKL", name="Коломна Intergalactic"),
        Airport(IATA_code="MYT", ICAO_code="UUMY", name="Мытищи Air Village"),
        Airport(IATA_code="CHE", ICAO_code="UUCH", name="Челябинск Luxury Air Terminal"),
        Airport(IATA_code="TUL", ICAO_code="UUTL", name="Тула Galaxy Airport"),
    ])

    FlightStatus.objects.bulk_create([
        FlightStatus(name="Запланирован"),
        FlightStatus(name="Регистрация открыта"),
        FlightStatus(name="Регистрация завершена"),
        FlightStatus(name="Посадка началась"),
        FlightStatus(name="Посадка завершена"),
        FlightStatus(name="Вылетел"),
        FlightStatus(name="Прибыл"),
        FlightStatus(name="Задержан"),
        FlightStatus(name="Отменён"),
    ])

    Flight.objects.bulk_create([
        Flight(
            airplane_id=1,
            planned_departure=datetime(2025, 10, 1, 9, 0),
            planned_arrival=datetime(2025, 10, 1, 10, 15),
            departure_airport_id=4,
            arrival_airport_id=5,
            flight_status_id=1
        ),
        Flight(
            airplane_id=2,
            planned_departure=datetime(2025, 10, 2, 11, 0),
            planned_arrival=datetime(2025, 10, 2, 12, 20),
            departure_airport_id=6,
            arrival_airport_id=4,
            flight_status_id=1
        ),
        Flight(
            airplane_id=3,
            planned_departure=datetime(2025, 10, 3, 14, 0),
            planned_arrival=datetime(2025, 10, 3, 15, 30),
            departure_airport_id=4,
            arrival_airport_id=7,
            flight_status_id=1
        ),
        Flight(
            airplane_id=4,
            planned_departure=datetime(2025, 10, 4, 16, 0),
            planned_arrival=datetime(2025, 10, 4, 17, 30),
            departure_airport_id=8,
            arrival_airport_id=4,
            flight_status_id=1
        ),
        Flight(
            airplane_id=4,
            planned_departure=datetime(2025, 10, 5, 8, 0),
            planned_arrival=datetime(2025, 10, 5, 9, 30),
            departure_airport_id=4,
            arrival_airport_id=9,
            flight_status_id=1
        ),
        Flight(
            airplane_id=1,
            planned_departure=datetime(2025, 10, 6, 10, 0),
            planned_arrival=datetime(2025, 10, 6, 11, 15),
            departure_airport_id=10,
            arrival_airport_id=4,
            flight_status_id=1
        ),
    ])

    CheckInDeskFlight.objects.bulk_create([
        CheckInDeskFlight(desk_id=1, flight_id=1),
        CheckInDeskFlight(desk_id=2, flight_id=4)
    ])

    GateFlight.objects.bulk_create([
        GateFlight(gate_id=1, flight_id=1),
        GateFlight(gate_id=3, flight_id=4)
    ])

    Passenger.objects.bulk_create([
        Passenger(firstname="Иван", lastname="Петров", middle_name="Сергеевич",
            passport="4510123456", flight_id=1),
        Passenger(firstname="Мария", lastname="Иванова", middle_name="Андреевна",
            passport="4510987654", flight_id=1),
        Passenger(firstname="Олег", lastname="Кузнецов", middle_name="Игоревич",
            passport="4510765432", flight_id=4),
        Passenger(firstname="Анна", lastname="Соколова", middle_name="Владимировна",
            passport="4510654321", flight_id=4),
    ])