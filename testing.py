import lightwaverf
import logging
import sys
from colorama import Fore, Back, Style, init
from pygments import highlight, lexers, formatters
import json
import configparser

import urllib.request
import os

init()


#    def __init__(self, fmt='[%(asctime)s] %(levelname)-8s %(message)s'):
class MyFormatter(logging.Formatter):
    FORMATS = {logging.DEBUG : logging._STYLES['%'][0]("[%(asctime)s] %(levelname)s %(message)s"),
       logging.ERROR : logging._STYLES['%'][0](Fore.RED + "[%(asctime)s] %(levelname)s %(message)s" + Fore.WHITE),
       logging.INFO : logging._STYLES['%'][0](Fore.CYAN + "[%(asctime)s] %(levelname)s %(message)s"+ Fore.WHITE),
       logging.WARNING : logging._STYLES['%'][0](Fore.YELLOW + "[%(asctime)s] %(levelname)s %(message)s"+ Fore.WHITE),
       logging.CRITICAL : logging._STYLES['%'][0](Back.RED + "[%(asctime)s] %(levelname)s %(message)s"+ Back.WHITE),
       'DEFAULT' : logging._STYLES['%'][0]( Fore.GREEN + "[%(asctime)s] %(levelname)s %(message)s" + Fore.WHITE)}

    def format(self, record):
        # Ugly. Should be better
        self._style = self.FORMATS.get(record.levelno, self.FORMATS['DEFAULT'])
        return logging.Formatter.format(self, record)

def test():
    print(Back.RED+"Settings updated."+Back.BLACK)

config = configparser.RawConfigParser()
config.read('prefs.ini')

username = config.get('Login','user')
password = str(config.get('Login','password'))

levels = ['debug','info','warning','error','critical']

log_level = 'critical'

if len(sys.argv) == 2:
    log_level = sys.argv[1] if sys.argv[1] in levels else 'critical'

print("Logging level: "+Fore.RED+log_level.upper()+ "."+Fore.WHITE)

numeric_level = getattr(logging, log_level.upper(), 0)

if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % log_level)

l = lightwaverf.LWRFServer(username=username, pin=password,log=log_level)

logging.basicConfig(level=numeric_level)
console = logging.getLogger('').handlers[1]
console.setFormatter(MyFormatter())

l._discovery_obeservers.append(test)

x = True

while x:
    p = input('>> ')
    if p == ".exit":
        x= False
    elif p == ".connect":
        print(Fore.GREEN + "Connecting..." + Fore.WHITE)
        l.start_server(auto_update_settings=True)
    elif p == ".heating":
        l.heating[0].set_target_temperature(10)
    elif p[:5] == ".save":
        c = p[6:]
        if c == "settings":
            formatted_json = json.dumps(l.settings, sort_keys=True, indent=4)
            colorful_json = highlight(formatted_json, lexers.JsonLexer(), formatters.TerminalFormatter())
            print(colorful_json)
            filename = "settings.json.txt"
            of = open(filename,"w")
            of.write(formatted_json)
            of.close()
            print(Fore.GREEN + "Settings file saved: " + Fore.RED + filename + Fore.WHITE)
    elif p[:5] == ".list":
        c = p[6:]
        if c[0] == "h":
            print("┌───────────────┬──────────────┬─────┬────────┬────────┐")
            print("│ %s │ %s │ %s │ %s │ %s │" % ("Device Name".ljust(13), "Room Name".ljust(12), "Num".ljust(3), "Temp.".ljust(6), "Target".ljust(6)))
            print("├───────────────┼──────────────┼─────┼────────┼────────┤")
            for h in l.heating:
                curr = "----"
                if hasattr(h,'current'):
                    curr = str(h.current).ljust(4)
                targ =  "----"
                if hasattr(h,'target'):
                    targ = Fore.BLUE + str(h.target).ljust(4) + Fore.WHITE

                if hasattr(h,'current') and hasattr(h,'target'):
                    if h.current < (h.target - 0.5):
                        curr = Fore.RED + curr + Fore.WHITE
                    else:
                        curr = Fore.GREEN + curr + Fore.WHITE

                print("│ %s │ %s │ %s │ %s°C │ %s°C │" % (h.name.ljust(13), h.room_name.ljust(12), str(h.device_number).ljust(3), curr, targ))
            print("└───────────────┴──────────────┴─────┴────────┴────────┘")
        elif c[0] == "l":
            print("┌───────────────┬──────────────┬─────┐")
            print("│ %s │ %s │ %s │" % ("Device Name".ljust(13), "Room Name".ljust(12), "Num".ljust(3)))
            print("├───────────────┼──────────────┼─────┤")
            for d in l.lights:
                print("│ %s │ %s │ %s │" % (d.name.ljust(13), str(d.room).ljust(12), str(d.code).ljust(3)))
            print("└───────────────┴──────────────┴─────┘")
        elif c[0] == "s":
            print("┌───────────────┬──────────────┬─────┐")
            print("│ %s │ %s │ %s │" % ("Device Name".ljust(13), "Room Name".ljust(12), "Num".ljust(3)))
            print("├───────────────┼──────────────┼─────┤")
            for d in l.sockets:
                print("│ %s │ %s │ %s │" % (d.name.ljust(13), str(d.room).ljust(12), str(d.code).ljust(3)))
            print("└───────────────┴──────────────┴─────┘")
        elif c[0] == "e":
            print("┌───────────────┬─────────┬─────────┐")
            print("│ %s │ %s │ %s │" % ("Device Name".ljust(13), "Current".ljust(7), "Today".ljust(7)))
            print("├───────────────┼─────────┼─────────┤")
            d = l.energy
            if d is not None:
                curr = str(d.current) if hasattr(d,'current') else "----"
                tod = str(d.today) if hasattr(d,'today') else "----"
                print("│ %s │ %skWh │ %skWh │" % (d.name.ljust(13), curr.ljust(4), tod.ljust(4)))
            print("└───────────────┴─────────┴─────────┘")
    elif p == ".image":
        c = p[6]
        for r in l.rooms:
            filename, file_extension = os.path.splitext(r.get_image_url())
            urllib.reque.urlretrieve(filename,r.name + " " + str(r.room_number) + file_extension)

    else:
        l.command_queue.append(p)
