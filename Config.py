#! Файл конфигурации
class Config:
    # Сенсоры
    sensors = "sensors"
    temperature, groundTemp, humidity, pressure, groundGygro = "DataBME280Temp", "DataGroundTemperatureSensor", \
                                                               "DataBME280Humidity", "DataBME280Pressure", \
                                                               "DataGroundGygrometers"
    # Устройства
    devices = "devices"
    heating, watering, blowing, light = "Heating", "Watering", "Blowing", "Light"

    # Параметры для Arduino
    temp_limits, soilt_limits, soilm_limits = "AirTemperatureLimits", "SoilTemperatureLimits", "SoilMoistureLimits"

    # Параметры БД
    pdb = 'dbname=mydb user=postgres host=localhost port=5432'

    # Запросы в БД
    insert = "INSERT INTO greenhouse (tempe, hum, press, ground_tempe, " \
             "ground_gygro, heating, watering, blowing, light) VALUES ({}," \
             " {}, {}, ARRAY{}, ARRAY{}, {}, {}, {}, {})"
    select = """ 
             SELECT *
             FROM greenhouse 
             WHERE post_time >= '{}'
             """

    # Файл с параметрами растения
    file = "plant2.csv"

    # Начальное состояние лампочки (2 - начало работы | 1 - включена | 0 - отключена)
    light_state = 2

    # Параметры COM порта
    COM = 'COM3'
    Speed = 9600

    # Параметры HTTP порта
    Port = 7777
    Host = 'localhost'

    # Время начала цикла (c 0-го дня)
    Day = 0

    # Убираем возможность изменения констант
    def __setattr__(self, *_):
        pass
