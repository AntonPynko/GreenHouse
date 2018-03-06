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

    # Файл с параметрами растения
    file = "cucumis.txt"

    # Начальное состояние лампочки (2 - начало работы | 1 - включена | 0 - отключена)
    light_state = 2

    # Параметры COM порта
    COM = 'COM4'
    Speed = 9600

    # Убираем возможность изменения констант
    def __setattr__(self, *_):
        pass
