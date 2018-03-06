#! COM Communications: Get & Send data to COM Port & localhost

import serial
import json
import time
from Config import Config
import tornado.web
from tornado.ioloop import IOLoop
from tornado import gen
import serial.tools.list_ports

current_light_state = Config.light_state


class Handler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):

        yield communication_test.send_data()
        yield gen.sleep(6)
        received_data = yield communication_test.get_data()
        yield gen.sleep(1)
        self.write(received_data) # Асинхронно пишем в сокет
        self.finish()       # Завершаем составление ответа


class ComCommunication:
    def __init__(self, name, speed):
        self.name = name
        self.speed = speed
        try:
            self.data = serial.Serial(self.name, self.speed)

        except serial.serialutil.SerialException:
            pass

    @gen.coroutine
    def get_data(self):
            #self.data.close()
            #self.data.open()
            data_sensor = str(self.data.readline())
            data_sensor = data_sensor[2:len(data_sensor)-5]
            print(data_sensor)
            try:
                parsed_string = json.loads(data_sensor)
                data_to_send = dict()
                data_to_send[Config.temperature] = parsed_string[Config.temperature]

                data_to_send[Config.groundTemp] = parsed_string[Config.groundTemp]

                data_to_send[Config.humidity] = parsed_string[Config.humidity]

                data_to_send[Config.pressure] = parsed_string[Config.pressure]

                data_to_send[Config.groundGygro] = parsed_string[Config.groundGygro]

                data_to_send[Config.heating] = parsed_string[Config.heating]

                data_to_send[Config.watering] = parsed_string[Config.watering]

                data_to_send[Config.blowing] = parsed_string[Config.blowing]

                data_to_send[Config.light] = parsed_string[Config.light]
                return data_to_send
            except json.decoder.JSONDecodeError:
                print(json.decoder.JSONDecodeError)

    @gen.coroutine
    def send_data(self):
        global current_light_state
        e = time.localtime()
        data = dict()
        with open(Config.file, "r") as file:
            for line in file:
                splitted_text = line.split()
                data[splitted_text[0]] = [int(splitted_text[1]), int(splitted_text[2])]
        lightRange = list(range(data[Config.light][0], data[Config.light][1] + 1))

        if (e.tm_hour in lightRange) & (current_light_state != 1):
            data[Config.light] = 1
            data_to_send = json.dumps(data)
            current_light_state = 1
            self.data.write(data_to_send.encode('ascii'))

        elif (e.tm_hour not in lightRange) & (current_light_state != 0):
            data[Config.light] = 0
            current_light_state = 0
            data_to_send = json.dumps(data)
            self.data.write(data_to_send.encode('ascii'))


communication_test = ComCommunication(Config.COM, Config.Speed)

if __name__ == '__main__':

    application = tornado.web.Application([(r"/test", Handler)])

    application.listen(8080)
    IOLoop.instance().start()
