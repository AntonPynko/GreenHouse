#! COM Communications: Get & Send data to COM Port & DB
import cv2
import os
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
import csv
import ast


ioloop = IOLoop.instance()
conn = momoko.Pool(dsn=Config.pdb, size=1, ioloop=ioloop)
fut = conn.connect()
ioloop.add_future(fut, lambda f: ioloop.stop())
ioloop.start()
try:
    fut.result()  # raises exception on connection error
except Exception as error:
    with open("logs.txt", "a") as logfile:
        logfile.write(time.strftime('%Y-%m-%d %H:%M:%S | ', time.localtime()) +
                      "Exception in connection to db: " + str(error))
        logfile.write("\n")


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
        elif self.name == "to_client":
            application = tornado.web.Application([
                (r'/', Handler)
            ])

            application.db = conn
            print("I am at client side")

            http_server = HTTPServer(application)
            http_server.listen(7777, 'localhost')
            ioloop.start()
        else:
            s = CaptureImg()
            yield s.save_img()


class CaptureImg:
    @gen.coroutine
    def save_img(self):
        cap = cv2.VideoCapture(0)
        while cap.isOpened():
            ret, frame = cap.read()
            if ret:
                yield gen.sleep(28800)
                if not os.path.exists(time.strftime('%Y%m%d', time.localtime())):
                    os.makedirs(time.strftime('%Y%m%d', time.localtime()))
                cv2.imwrite('{}/{}.jpg'.format(time.strftime('%Y%m%d', time.localtime()),
                                               time.strftime('%Y%m%d%H%M', time.localtime())), frame)
            else:
                break
        # Release everything if job is finished
        cap.release()
        cv2.destroyAllWindows()


class InsertHandler:
    @gen.coroutine
    def send_to_db(self):
        flag = 0
        current_light_state = 2
        readjson = 1
        while flag == 0:
            yield gen.sleep(1)
            yield communication_test.send_data(readjson, current_light_state)
            yield gen.sleep(2)
            received_data = yield communication_test.get_data()
            if not isinstance(received_data, dict):
                continue
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
            try:
                yield conn.execute(data_to_db)
                print("I've sent some data to db")
            except Exception as error:
                with open("logs.txt", "a") as logfile:
                    logfile.write(time.strftime('%Y-%m-%d %H:%M:%S | ', time.localtime()) +
                                  "Exception in send_to_db: " + str(error))
                    logfile.write("\n")

            if received_data[Config.light]:
                current_light_state = 1
            else:
                current_light_state = 0

            if not received_data["ReadJson"]:
                print("json wasn't read")
                readjson = 1
            else:
                print("success")
                readjson = 0


class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db


class Handler(BaseHandler):
    @gen.coroutine
    def get(self):
        try:
            cursor = yield self.db.execute(Config.select.format(time.strftime('%Y-%m-%d %H:%M', time.localtime())))
            newjson, fulljson = dict(), dict()
            for line in cursor:
                newjson["AirTemperature"] = line[1]
                newjson["AirHumidity"] = line[2]
                newjson["AirPress"] = line[3]
                newjson["GroundTemp"] = line[4]
                newjson["GroundGygro"] = line[5]
                newjson["Heating"] = line[6]
                newjson["Watering"] = line[7]
                newjson["Blowing"] = line[8]
                newjson["Light"] = line[9]
                fulljson[line[10].strftime('%A, %d. %B %Y %I:%M:%S %p')] = newjson
            self.write(fulljson)
            self.write("\n")
        except Exception as error:
            with open("logs.txt", "a") as logfile:
                logfile.write(time.strftime('%Y-%m-%d %H:%M:%S | ', time.localtime()) +
                              "Exception in send_to_user: " + str(error))
                logfile.write("\n")
            self.write(str(error))
        self.finish()


class ComCommunication:
    def __init__(self, name, speed):
        self.name = name    # параметры порта
        self.speed = speed

        # self.current_light_state = 2  # показания света ( 1 - вкл, 0 - выкл, 2 - начальное)
        self.starting_hour = time.localtime().tm_hour  # время, когда был запущен процесс роста
        self.starting_min = time.localtime().tm_min
        self.current_day = Config.Day  # счетчик текущего дня
        self.light_period = list()  # период освещения растения ( получаем из csv, изначально 0 )
        self.counter = 0  # счетчик изменения недели ( 1 - обновлено, 0 - не обновлено)
        self.ard_data = dict()  # данные для Arduino

        try:
            self.data = serial.Serial(self.name, self.speed)

        except serial.serialutil.SerialException:
            with open("logs.txt", "a") as logfile:
                logfile.write(time.strftime('%Y-%m-%d %H:%M:%S | ', time.localtime()) +
                              "Exception in open serial.")
                logfile.write("\n")

    @gen.coroutine
    def get_data(self):
            # self.data.close()
            # self.data.open()
            try:
                data_sensor = str(self.data.readline())
                data_sensor = data_sensor[2:len(data_sensor)-5]
                # print(data_sensor)
            except Exception as exc:
                with open("logs.txt", "a") as logfile:
                    logfile.write(time.strftime('%Y-%m-%d %H:%M:%S | ', time.localtime()) +
                                  "Exception in reading from serial port: " + str(exc))
                    logfile.write("\n")
                try:
                    self.data = serial.Serial(self.name, self.speed)
                except serial.serialutil.SerialException:
                    with open("logs.txt", "a") as logfile:
                        logfile.write(time.strftime('%Y-%m-%d %H:%M:%S | ', time.localtime()) +
                                      "Failed to reopen serial port.")
                        logfile.write("\n")
                return 1

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

                data_to_send["ReadJson"] = parsed_string["ReadJson"]

                # print(data_to_send)

                return data_to_send
            except json.decoder.JSONDecodeError:
                with open("logs.txt", "a") as logfile:
                    logfile.write(time.strftime('%Y-%m-%d %H:%M:%S | ', time.localtime()) +
                                  "Exception in parsing..")
                    logfile.write("\n")
                print(json.decoder.JSONDecodeError)
                return 1

    @gen.coroutine
    def send_data(self, readjson, light_state):
        e = time.localtime()
        isnotread = readjson
        current_light_state = light_state

        if (e.tm_hour == self.starting_hour) & \
                (e.tm_min == 1 + self.starting_min):
            self.counter = 0

        if (e.tm_hour == self.starting_hour) & \
                (e.tm_min == self.starting_min) & (self.counter != 1):
            self.counter = 1
            with open(Config.file, "r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if self.current_day in list(
                            range(ast.literal_eval(row["day"])[0], ast.literal_eval(row["day"])[1] + 1)):
                        self.ard_data[Config.temp_limits] = ast.literal_eval(row["temp"])
                        # self.ard_data["AirHumidityLimits"] = ast.literal_eval(row["hum"])
                        self.ard_data[Config.soilt_limits] = ast.literal_eval(row["ground_temp"])
                        self.ard_data[Config.soilm_limits] = ast.literal_eval(row["hum_seed"])
                        self.ard_data["Watering"] = ast.literal_eval(row["watering"])
                        self.ard_data[Config.light] = ast.literal_eval(row["light"])
                self.current_day += 1
            if (self.ard_data[Config.light] != 0) & (e.tm_hour + self.ard_data[Config.light] <= 24):
                if e.tm_hour + self.ard_data[Config.light] < 24:
                    self.light_period = list(range(e.tm_hour, e.tm_hour + self.ard_data[Config.light] + 1))
                else:
                    self.light_period = list(range(e.tm_hour, e.tm_hour + self.ard_data[Config.light]))
                    self.light_period.append(0)
            elif (self.ard_data[Config.light] != 0) & (e.tm_hour + self.ard_data[Config.light] > 24):
                light_period_1 = list(range(e.tm_hour, 24))
                light_period_2 = list(range(0, e.tm_hour + self.ard_data[Config.light] - 24 + 1))
                self.light_period = light_period_1 + light_period_2

        if (e.tm_hour in self.light_period) & (current_light_state != 1) & isnotread:
            self.ard_data[Config.light] = 1
            self.current_light_state = 1
            data_to_send = json.dumps(self.ard_data)
            try:
                self.data.write(data_to_send.encode('ascii'))
                print("I've sent data to Arduino")
            except Exception:
                with open("logs.txt", "a") as logfile:
                    logfile.write(time.strftime('%Y-%m-%d %H:%M:%S | ', time.localtime()) +
                                  "Exception in sending to serial port.")
                    logfile.write("\n")

        elif (e.tm_hour not in self.light_period) & (current_light_state != 0) & isnotread:
            self.ard_data[Config.light] = 0
            self.current_light_state = 0
            data_to_send = json.dumps(self.ard_data)
            # print(data_to_send.encode('ascii'))
            try:
                self.data.write(data_to_send.encode('ascii'))
                print("I've sent some data to turn off lights")
            except Exception:
                with open("logs.txt", "a") as logfile:
                    logfile.write(time.strftime('%Y-%m-%d %H:%M:%S | ', time.localtime()) +
                                  "Exception in sending to serial port.")
                    logfile.write("\n")


communication_test = ComCommunication(Config.COM, Config.Speed)

if __name__ == '__main__':

    thread1 = MyThread(1, "to_db")
    thread2 = MyThread(2, "to_client")
    thread3 = MyThread(3, "to_img")

    # Start new Threads
    thread1.start()
    thread2.start()
    thread3.start()
    thread1.join()
    thread2.join()
    thread3.join()
