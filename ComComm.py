#! COM Communications: Get & Send data to COM Port & DB

import serial
import json
import time
from Config import Config
import tornado.web
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado import gen
import momoko
import serial.tools.list_ports
import threading

current_light_state = Config.light_state

ioloop = IOLoop.instance()
conn = momoko.Pool(dsn=Config.pdb, size=1, ioloop=ioloop)
fut = conn.connect()
ioloop.add_future(fut, lambda f: ioloop.stop())
ioloop.start()
fut.result()  # raises exception on connection error


class MyThread (threading.Thread):

    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

    @gen.coroutine
    def run(self):
        if self.name == "to_db":
            ins = InsertHandler()
            yield ins.send_to_db()
        else:
            application = tornado.web.Application([
                (r'/', Handler)
            ])

            application.db = conn
            print("I am at client side")

            http_server = HTTPServer(application)
            http_server.listen(7777, 'localhost')
            ioloop.start()


class InsertHandler:
    @gen.coroutine
    def send_to_db(self):
        flag = 0
        i = 0
        while flag == 0:
            yield gen.sleep(1)
            yield communication_test.send_data()
            yield gen.sleep(2)
            received_data = yield communication_test.get_data()
            # yield gen.sleep(1)
            #print(received_data)
            data_to_db = Config.insert.format(received_data[Config.temperature],
                                              received_data[Config.humidity],
                                              received_data[Config.pressure],
                                              received_data[Config.groundTemp],
                                              received_data[Config.groundGygro],
                                              received_data[Config.heating],
                                              received_data[Config.watering],
                                              received_data[Config.blowing],
                                              received_data[Config.light]
                                              )
            # print(data_to_db)
            yield conn.execute(data_to_db)
            print("I've sent some data to db")
            i += 1
            if i == 50:
                flag = 1


class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db


class Handler(BaseHandler):
    @gen.coroutine
    def get(self):
        cursor = yield self.db.execute(Config.select)
        for record in cursor:
            self.write("Line: {}".format(record)) # Асинхронно пишем в сокет
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
            # print(data_sensor)
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

                # print(data_to_send)

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
            print(data_to_send.encode('ascii'))
            self.data.write(data_to_send.encode('ascii'))
            print("I've sent data to Arduino")

        elif (e.tm_hour not in lightRange) & (current_light_state != 0):
            data[Config.light] = 0
            current_light_state = 0
            data_to_send = json.dumps(data)
            self.data.write(data_to_send.encode('ascii'))
            print("I've sent some data to turn off lights")


communication_test = ComCommunication(Config.COM, Config.Speed)

if __name__ == '__main__':

    thread1 = MyThread(1, "to_db")
    thread2 = MyThread(2, "to_client")

    # Start new Threads
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
