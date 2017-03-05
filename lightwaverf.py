#!/usr/bin/python3

import plistlib
import urllib.request
import logging
import os.path
from queue import Queue
import threading
import time
import ast
import sqlite3 as lite
from enum import Enum
import socket
import json
import calendar
import time

class LWRFServer:

    """Class for interacting with the LightwaveRF Wifi Box"""

    _version = "0.7.B"

    received_commands = Queue()
    command_queue = []
    sent_commands = Queue()
    schedule = []

    _discovery_obeservers = []
    _observers = []

    config = {}

    remote_address ="https://control-api.lightwaverf.com/v1/"

    command_id = 588
    settings = {}
    _settings_interval_hours = 2

    rooms = []
    lights = []
    sockets = []
    heating = []
    timers = []
    events = []

    hub = None
    energy = None

    def bind_to(self, fn_value, bind_key, bind_value, callback):
        self._observers.append([fn_value, bind_key, bind_value, callback])

    def __init__ (self,log="debug",username="", pin=""):
        self._observers = []
        # 1. Sort out logging.
        numeric_level = getattr(logging, log.upper(), 0)

        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % log)

        logging.basicConfig(filename="LightwaveRF.log",level=numeric_level)
        console = logging.StreamHandler()
        console.setLevel(numeric_level)
        # tell the handler to use this format
        console.setFormatter(logging.Formatter('%(asctime)s: %(levelname)-8s %(message)s'))
        # add the handler to the root logger
        logging.getLogger('').addHandler(console)

        # 2. Check and load/create config
                #9761
        self.config = {
            'server':{'ip':'255.255.255.255','port':9760},
            'client':{'ip':'0.0.0.0','port':9761},
            'username': username,
            'pin':pin
        }
        self.config['cookie'] = None

    def start_server (self, auto_update_settings=False):
        t = threading.Thread(target=self.server, args=(self.received_commands,))
        # classifying as a daemon, so they will die when the main dies
        t.daemon = True
        # begins, must come after daemon definition
        t.start()

        commands_thread = threading.Thread(target=self.send_commands, args=(self.command_queue,))
        commands_thread.daemon = True
        commands_thread.start()

        if auto_update_settings:
            settings_thread = threading.Thread(target=self.continuously_update_settings )
            settings_thread.daemon = True
            settings_thread.start()

    def continuously_update_settings(self):
        while True:
            logging.debug ('Downloading settings from server...')
            settings_downloaded = self.download_settings()
            if settings_downloaded:
                self.implement_settings()
                logging.info ('Settings successfully downloaded from server.')
            else:
                logging.info("Settings download from server failed")
                return False
            time.sleep(60 * 60 * self._settings_interval_hours)

    def _send_message (self, message, id=0):
        if (id == 0):
            id = self.command_id
            self.command_id += 1

        message = str(id) +","+message+"\n"
        self.command_id += 1
        logging.debug("Sending: %s" % repr(message))
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind((self.config['client']['ip'],self.config['server']['port']))
        sock.sendto(bytes(message,'UTF-8'), (self.config['server']['ip'], self.config['server']['port']))

    def download_settings (self):
        logging.debug(self.config)

        request_user = "user?password={0}&username={1}"
        request_auth = "auth?application_key={0}"
        request_types = "device_type?is_nested=1"
        request_profile = "user_profile?nested=1"

        profile_response = None
        connection_attempts = 0
        success = False
        max_attempts = 8
        sleep_between_attempts = 2
        sleep_between_requests = 0
        lwrf_cookie = ""
        while connection_attempts < max_attempts and success == False:
            logging.debug("First Request...")
            user_http = self.remote_address + request_user.format(self.config['pin'], self.config['username'])
            user_request = urllib.request.Request(user_http,method='GET')
            user_request.add_header('X-LWRF-platform', 'ios')
            user_request.add_header('X-LWRF-skin', 'lightwaverf')
            user_request.add_header('User-Agent', 'LightwaveRF/0.0.47 (iPhone; iOS 10.0.1; Scale/2.00)')
            if self.config['cookie'] is not None:
                user_request.add_header('Cookie', self.config['cookie'])
            user_response = urllib.request.urlopen(user_request)
            user_response_json =  ast.literal_eval(user_response.read().decode(encoding='UTF-8'))
            self.config['application_key'] = user_response_json['application_key']
            if user_response.getheader('Set-Cookie') is not None:
                lwrf_cookie = user_response.getheader('Set-Cookie').split(';')[0].strip()
            if lwrf_cookie != self.config['cookie']:
                self.config['cookie'] = lwrf_cookie

            logging.debug("Second Request...")
            time.sleep(sleep_between_requests)
            auth_http = self.remote_address + request_auth.format(self.config['application_key'])
            auth_request = urllib.request.Request(auth_http,method='GET')
            auth_request.add_header('Cookie', self.config['cookie'])
            auth_response = urllib.request.urlopen(auth_request)
            auth_response_json = ast.literal_eval(auth_response.read().decode(encoding='UTF-8'))

            self.config['token'] = auth_response_json['token']

            logging.debug("Third Request...")
            time.sleep(sleep_between_requests)
            types_http = self.remote_address + request_types
            types_request = urllib.request.Request(types_http,method='GET')
            types_request.add_header('X-LWRF-platform', 'ios')
            types_request.add_header('X-LWRF-token', self.config['token'])
            types_request.add_header('Cookie', self.config['cookie'])
            types_response = urllib.request.urlopen(types_request)

            logging.debug("Fourth Request...")
            time.sleep(sleep_between_requests)
            profile_http = self.remote_address + request_profile
            profile_request = urllib.request.Request(profile_http,method='GET')
            profile_request.add_header('Cookie', self.config['cookie'])
            profile_request.add_header('X-LWRF-platform', 'ios')
            profile_request.add_header('X-LWRF-token', self.config['token'])
            profile_request.add_header('Accept', '*/*')
            profile_request.add_header('User-Agent', 'LightwaveRF/0.0.47 (iPhone; iOS 10.0.1; Scale/2.00)')
            profile_request.add_header('X-LWRF-skin', 'lightwaverf')

            try:
                profile_response = urllib.request.urlopen(profile_request)
                success = True
            except:
                logging.info("Connection Failed.  Attempt: " + str(connection_attempts + 1) + " of "+str(max_attempts)+". Waiting " + str(sleep_between_attempts) + " seconds.")
                time.sleep(sleep_between_attempts)

            connection_attempts += 1

        if connection_attempts >= max_attempts and success == False:
            logging.error("Settings Update FAILED after " + max_attempts + " attempts.")
            return False

        profile_body = profile_response.read().decode(encoding='UTF-8')
        profile_response_json = json.loads(profile_body)
        logging.debug(profile_response_json)
        self.settings = profile_response_json
        return True

    def implement_settings (self):
        #Process Settings
        logging.debug(self.settings['content']['estates'][0]['locations'][0]['zones'][0]['rooms'])

        # Make sure we have a clean slate
        self.rooms = []
        self.lights = []
        self.sockets = []
        self.heating = []
        self.timers = []
        self.events = []
        self.hub = None
        self.energy = None

        # Set the hub
        hub = self.settings['content']['wfls'][0]
        self.hub = LightwaveRFHub(self,hub['mac'])

        # Get Rooms and Room-based devices (Dimmers and lights)
        for room in self.settings['content']['estates'][0]['locations'][0]['zones'][0]['rooms']:
            lwrf_room = LightwaveRFRoom(room['name'], room['room_number'],room['active'],room['room_id'],room['image_hash']+"."+room['image_ext'])

            if 'devices' in room:
                for device in room['devices']:
                    lwrf_device = None
                    if device['device_type_prod'] == "dimmer":
                        lwrf_device = LightwaveRFLight(self,device['name'], room['name'],room['room_number'],device['device_number'])
                        self.lights.append(lwrf_device)
                    elif device['device_type_prod'] == "on_off":
                        lwrf_device = LightwaveRFSocket(self,device['name'], room['name'], room['room_number'],device['device_number'])
                        self.sockets.append(lwrf_device)

                lwrf_room.devices.append(lwrf_device)

            self.rooms.append(lwrf_room)

        # Get Heating Devices (includes Energy Monitor)
        for d in self.settings['content']['wfls'][0]['heating_devices']:
            device_name = d['name']
            serial = d['serial']
            device_number = d['device_number']
            room_id = d['room_id']

            lwrf_device = None
            room_name = "Main"
            for room in self.rooms:
                if room_id == room.room_id:
                    room_name = room.name

            if d['wfl_code'] == "EM":
                logging.info("Adding Energy Monitor: %s ..." % (device_name))
                lwrf_device = LightwaveRFEnergy(self, serial, device_name)
                self.energy = lwrf_device
            elif d['wfl_code'] == "V":
                logging.info("Adding TRV %s %d %s..."%(device_name,device_number, room_name))
                lwrf_device = LightwaveRFValve(self, serial, device_name,device_number, room_name)
                self.heating.append(lwrf_device)
            elif d['wfl_code'] == "T":
                logging.info("Adding Thermostat %s %d %s..."%(device_name,device_number, room_name))
                lwrf_device = LightwaveRFThermostat(self, serial, device_name,device_number, room_name)
                self.heating.append(lwrf_device)

        # Get Timers
        for t in self.settings['content']['wfls'][0]['timers']:
            timer_name = t['name']
            timer_id = t['timer_id']
            timer_command = t['command']
            timer_active = t['active']
            lwrf_timer = LightwaveRFTimer(self, timer_name, timer_id, timer_command, timer_active)
            self.timers.append(lwrf_timer)

        # Get Events
        for e in self.settings['content']['wfls'][0]['events']:
            event_name = e['name']
            event_id = e['event_id']
            event_command = e['command']
            lwrf_event = LightwaveRFEvent(self, event_name, event_id, event_command)
            self.events.append(lwrf_event)

        for discovery_callback in self._discovery_obeservers:
            discovery_callback();

    def switch (self, device_number, status, schedule = False, delay = False, once = False):
        code = "F0"
        state = "Off"
        status = float(status)
        if ((status > 0) and (status < 1)):
            if (self.settings['deviceStatus'][device_number] == 'D'):
                percentage = str(int(32 * status))
                code = "FdP" + percentage
                state = "On at " + str(int(status * 100)) + "%"
            else:
                status = 1
                logging.debug("Trying to dim a non-dimming device.  Treating as ON instead.")
        elif (status == 1):
            code = "F1"
            state = "On"

        if (self.settings['deviceStatus'][device_number].lower() == 'm' or self.settings['deviceStatus'][device_number] == 'o' ):
            code = ""

        logging.debug ("Enqueue: Switch " + self.get_device_name(device_number) + " in " + self.get_room_name(device_number) + " to " + code)
        command = "!" + self.get_device_code(device_number) + code + "|" + self.get_device_name(device_number) + "|" +state
        logging.debug(command)
        logging.debug(status)
        if (schedule == False):
            self.sent_commands.put(command)
        else:
            self.schedule.append( {'command':command,"interval":schedule, "started":time.time(), 'delay':delay, 'once':once} )

    def server(self, received_commands):
        sock2 = socket.socket(type=socket.SOCK_DGRAM)
        sock2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock2.bind((self.config['client']['ip'], self.config['client']['port']))

        last_called = {'pwrMtr': 0, 'tmr1ch': 0}

        while True:
            data, addr = sock2.recvfrom(1024) # buffer size is 1024 bytes
            self.process_command(data, last_called)

    def process_command(self, data, last_called):
        data = str(data,'UTF-8')
        if (data[0:3].isdigit()):
            if data[4:7] == "ERR":
                logging.error("Command %s failed: %s" % (data[0:3],repr(data[4:])))
            else:
                logging.debug ("Command %s returned %s" % (data[0:3],repr(data[4:])))
            return "REPLY", False
        elif (data[0:3] == "*!{"):
            d = ast.literal_eval(data[2:])
            for callback in self._observers:
                if 'fn' in d:
                    if d['fn'] == callback[0] and callback[1] in d:
                        logging.debug('Monitored Dictionary Received: %s',data);
                        if callback[2] == d[callback[1]]:
                            callback[3](d)
                else:
                    logging.debug('Dictionary Received: %s',data);
        else:
            logging.debug('Surprising Command Received: %s',data);

    def send_commands ( self, command_queue):
        time.sleep(3)
        while True:
            if len(command_queue) > 0:
                message = command_queue.pop(0)
                logging.info ('Sending Enqueued Command: %s' % message)
                self._send_message(message)
                time.sleep(3)

class LWRFType(Enum):
    empty = 0
    hub = 1
    light = 2
    socket = 3
    energy = 4
    thermostat = 5
    trv = 6

class LightwaveRFDevice:
    def __init__(self, device_server, device_type):
        self.type = device_type
        self.server = device_server
    @property
    def room_id(self):
        return self.__room_id

    @room_id.setter
    def room_id(self,room_id):
        self.__room_id = room_id

    @property
    def server(self):
        return self.__server

    @server.setter
    def server(self, device_server):
        if type(device_server) is LWRFServer:
            self.__server = device_server
        else:
            raise ValueError('Server is not LWRFServer.')

    @property
    def active(self):
        return self.__active

    @active.setter
    def active(self, device_active):
        if type(device_active) is bool:
            self.__active = device_active
        else:
            raise ValueError('Active is not boolean.')

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, device_name):
        self.__name = device_name

    @property
    def type(self):
        return self.__type

    @type.setter
    def type(self, device_type):
        try:
            if type(device_type) is LWRFType:
                self.__type = device_type
            elif type(device_type) is int:
                self.__type = LWRFType(device_type)
            else:
                raise ValueError('Device type is not LWRFType or int.')
        except ValueError as error:
            logging.error('Error Setting Type: ' + repr(error))
            return False;

class LightwaveRFSwitch(LightwaveRFDevice):

    def __init__(self, device_server, device_type, name, room_name, room, code, device_state):
        self.state = device_state
        self.name = name
        self.room_name = room_name
        self.room = room
        self.code = code
        super(LightwaveRFSwitch, self).__init__(device_server, device_type)

    @property
    def room_name(self):
        return self.__room_name

    @room_name.setter
    def room_name(self, device_room_name):
        self.__room_name = device_room_name

    @property
    def room(self):
        return self.__room

    @room.setter
    def room(self, device_room):
        if type(device_room) is int:
            self.__room = device_room
        elif type(device_room) is string:
            self.__room = int(device_room[2])
        else:
            raise ValueError('Room is not integer or appropriate string.')

    @property
    def code(self):
        return self.__code

    @code.setter
    def code(self, device_code):
        if type(device_code) is int:
            self.__code = device_code
        elif type(device_code) is str:
            self.__room = int(device_code[2])
        else:
            raise ValueError('Code is not integer or appropriate string.')
    @property
    def state(self):
        return self.__state

    @state.setter
    def state(self, device_state):
        if type(device_state) is bool:
            self.__state = device_state
        else:
            raise ValueError('State is not boolean.')

    def turn_on(self):
        self.server.command_queue.append("!R"+str(self.room) + "D" + str(self.code) + "F1|" + self.name + "|Switch On")
        self.state = True

    def turn_off(self):
        self.server.command_queue.append("!R"+str(self.room) + "D" + str(self.code) + "F0|" + self.name + "|Switch Off")
        self.state = False

class LightwaveRFSocket(LightwaveRFSwitch):
    def __init__(self, device_server, room_name, name, room, code):
        super(LightwaveRFSocket, self).__init__(device_server, LWRFType.socket, room_name, name, room, code, False)

class LightwaveRFLight(LightwaveRFSwitch):
    def __init__(self, device_server, room_name, name, room, code):
        super(LightwaveRFLight, self).__init__(device_server, LWRFType.light, room_name, name, room, code, False)

    @property
    def brightness(self):
        return self.__brightness

    @brightness.setter
    def brightness(self, percentage):
        if percentage > 100:
            percentage = 100
        elif percentage < 0:
            percentage = 0

        self.__brightness = percentage

        brightness_32 = int((self.brightness / 100) * 32)
        if brightness_32 > 0:
            self.server.command_queue.append("!R"+str(self.room) + "D" + str(self.code) + "FdP" + str(brightness_32) +"|" + self.name + "|Bright " + str(self.brightness) + "%")
            self.state = True
        else:
            self.server.command_queue.append("!R"+str(self.room) + "D" + str(self.code) + "F0|" + self.name + "|Switch Off")
            self.state = False

class LightwaveRFSensor(LightwaveRFDevice):
    def __init__(self,device_server, device_type, fn_value, bind_key, bind_value):
        super(LightwaveRFSensor, self).__init__(device_server, device_type)
        self.server.bind_to(fn_value, bind_key, bind_value, self.update_data)

    @property
    def serial(self):
        return self.__serial

    @serial.setter
    def serial(self, serial):
        self.__serial = serial
    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, data):
        self.__data = data

    def update_data(self, data):
        self.data = data

    @property
    def timestamp(self):
        return self.__timestamp

    @timestamp.setter
    def timestamp(self, value):
        self.__timestamp = value

class LightwaveRFHub(LightwaveRFSensor):
    def __init__(self, server, mac):
        self.name = mac
        self.mac = mac[-8:]
        logging.debug("Last 8 Characters of MAC: " + self.mac)
        super(LightwaveRFHub, self).__init__(server, LWRFType.hub, "hubCall", "prod", "wfl")

    def update(self):
        self.message_send("@H")

    def update_data(self, data):
        if self.mac == data['mac']:
            self.uptime = data['uptime']
            self.version = data['fw']
            self.time = data['time']
            if 'timeZ' in data:
                self.timezone = data['timeZ']
            self.latitude = data['lat']
            self.longitude = data['long']
            if 'dawnT' in data:
                self.dawn = data['dawnT']
                self.dusk = data['duskT']
            self.timers = data['tmrs']
            self.events = data['evns']
            self.devices = data['macs']
            self.heating = data['devs']
            self.ip = data['ip']
            logging.info("Hub Updated")
        else:
            print ("This is: " + data['mac'] + ".  Looking for: " + self.mac)

    @property
    def version(self):
        return self.__version

    @version.setter
    def version(self, value):
        self.__version = value

    @property
    def name(self):
        return self.__name

    @version.setter
    def name(self, value):
        self.__name = value

    @property
    def mac(self):
        return self.__mac

    @mac.setter
    def mac(self, value):
        self.__mac = value

    @property
    def uptime(self):
        return self.__uptime

    @uptime.setter
    def uptime(self, value):
        self.__uptime = value

    @property
    def timezone(self):
        return self.__timezone

    @timezone.setter
    def timezone(self, value):
        self.__timezone = value

    @property
    def latitude(self):
        return self.__latitude

    @latitude.setter
    def latitude(self, value):
        self.__latitude = value

    @property
    def longitude(self):
        return self.__longitude

    @longitude.setter
    def longitude(self, value):
        self.__longitude = value

    @property
    def dawn(self):
        return self.__dawn

    @dawn.setter
    def dawn(self, value):
        self.__dawn = value

    @property
    def dusk(self):
        return self.__dusk

    @dusk.setter
    def dusk(self, value):
        self.__dusk = value

    @property
    def phones(self):
        return self.__phones

    @phones.setter
    def phones(self, value):
        self.__phones = value

    @property
    def timers(self):
        return self.__timers

    @timers.setter
    def timers(self, value):
        self.__timers = value

    @property
    def events(self):
        return self.__events

    @events.setter
    def events(self, value):
        self.__events = value

    @property
    def heating(self):
        return self.__heating

    @heating.setter
    def heating(self, value):
        self.__heating = value

    @property
    def ip(self):
        return self.__ip

    @ip.setter
    def ip(self, value):
        self.__ip = value

class LightwaveRFEnergy(LightwaveRFSensor):
    def __init__(self, server, serial, name):
        self.name = name
        super(LightwaveRFEnergy, self).__init__(server, LWRFType.energy, "meterData","serial", serial)

    def update_data(self, data):
        self.current = data['cUse']
        self.today = data['todUse']
        logging.debug("Updated " + self.name + "; Today: " + str(self.today))

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value):
        self.__name = value

    @property
    def current(self):
        return self.__current

    @current.setter
    def current(self, value):
        self.__current = value

    @property
    def today(self):
        return self.__today

    @today.setter
    def today(self, value):
        self.__today = value

    @property
    def yesterday(self):
        return self.__yesterday

    @yesterday.setter
    def yesterday(self, value):
        self.__yesterday = value

class LightwaveRFHeating(LightwaveRFSensor):
    def __init__(self, server, type, serial, name, device_number, room_name):
        self.name = name
        self.room_name = room_name
        self.device_number = device_number
        super(LightwaveRFHeating, self).__init__(server, type, "statusPush", "serial", serial)
        server.command_queue.append("!R" + str(device_number) + "DhF*r|Requesting|Temperature")

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value):
        self.__name = value

    @property
    def room_name(self):
        return self.__room_name

    @room_name.setter
    def room_name(self, value):
        self.__room_name = value

    @property
    def device_number(self):
        return self.__device_number

    @device_number.setter
    def device_number(self, value):
        self.__device_number = value

    def refresh(self):
        self.server.command_queue.append("!R" + str(self.device_number) + "DhF*r|Requesting|Temperature")

    def set_target_temperature(self, temperature):
        cmd = "!R" + str(self.device_number) + "DhF*tP{0:.1f}".format(temperature)
        self.server.command_queue.append(cmd)

    def set_mode (self, mode):
        # 1. Running
        # 2. Away
        cmd = "!R" + str(self.device_number) + "DhF*mP" + str(mode)
        self.server.command_queue.append(cmd)

class LightwaveRFValve(LightwaveRFHeating):
    def __init__(self, server, serial, name, device_number, room_name):
        super(LightwaveRFValve, self).__init__(server, LWRFType.trv, serial, name, device_number, room_name)

    def update_data(self, data):
        self.current = data['cTemp']
        self.target = data['cTarg']
        self.state = data['state']
        self.battery = data['batt']

        logging.debug("Updated " + self.name + "; Temp: " + str(self.current))

class LightwaveRFThermostat(LightwaveRFHeating):
    def __init__(self, server, serial, name, device_number, room_name):
        super(LightwaveRFThermostat, self).__init__(server, LWRFType.thermostat, serial, name, device_number, room_name)

    def update_data(self, data):
        self.current = data['cTemp']
        self.target = data['cTarg']
        self.state = data['state']
        self.battery = data['batt']

        logging.debug("Updated " + self.name + "; Temp: " + str(self.current))

class LightwaveRFRoom:
    image_root = "https://control-api.lightwaverf.com/assets/public/room/"

    def __init__(self, name, room_number, active, room_id, filename):
        self.name = name
        self.room_number = room_number
        self.active = active
        self.devices = []
        self.room_id = room_id
        self.filename = filename

    def get_image_url(self):
        return self.image_root + self.filename

class LightwaveRFTimer:
    def __init__(self, server, name, timer_id, command, active):
        self.__timer_api = "https://control-api.lightwaverf.com/v1/timer"
        self.__server = server
        self.name = name
        self.__timer_id = timer_id
        self.__command = command
        self.active = active

    def pause(self):
        self.__server.command_queue.append("!FxP\"T" + str(self.__timer_id) + "\"|Pausing Timer")
        self.__send_web_api_command(0)
        self.active = 0

    def start(self):
        self.__server.command_queue.append(self.__command)
        self.__send_web_api_command(1)
        self.active = 1

    def __send_web_api_command(self,active):
        json_data = "{\"active\":"+str(active)+",\"timer_id\":"+str(self.__timer_id)+"}"
        profile_request = urllib.request.Request(self.__timer_api,json_data.encode())
        profile_request.get_method = lambda: 'PATCH'
        profile_request.add_header('X-LWRF-platform', 'ios')
        profile_request.add_header('Content-Type', 'application/json')
        profile_request.add_header('X-LWRF-token', self.__server.config['token'])
        profile_response = urllib.request.urlopen(profile_request)

class LightwaveRFEvent:
    def __init__(self, server, name, event_id, command):
        self.__server = server
        self.name = name
        self.__event_id = event_id
        self.__command = command

    def pause(self):
        self.__server.command_queue.append("!FxP\"E" + str(self.__event_id) + "\"|Pausing Event")

    def start(self):
        self.__server.command_queue.append("!FqP\"E" + str(self.__event_id) + "\"|Starting Event")
