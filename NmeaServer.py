#!/usr/bin/python3
import argparse
import datetime
import socket
import sys
import os
import time
import threading
import pynmea2
import logging
import select
import signal
from sys import platform

IS_WIN = False
DEFAULT_PORT = 5007
INTERVAL_TX_PACKET = 1 #sec

if "win" in platform:
    from msvcrt import getch
    IS_WIN = True
    
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if IS_WIN:
    LOG_PATH = f"{BASE_DIR}/nmea.log"
else:
    LOG_PATH = "/var/log/nmea.log"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, filename=LOG_PATH, format='%(asctime)s %(levelname)s:%(message)s')

def print2(value, debug=True, error=False):
    print(value)
    if debug:
        logger.debug(value)
    if error:
        logger.error(value)
 
class ClientSet(set):
    
    def  __str__ (self):
        value = ""
        if len(self) == 0:
            return value
        for v in self:
            value += f" [{v[0]}:{v[1]}]"
        return value.lstrip(" ")
            
class NMEAServer():

    def __init__(self, host='', port=DEFAULT_PORT, clients=100, rmc=True, gsa=False, status="A", id="GP"):
        self._port = port
        self._host = host
        self._clients = clients
        self._status = status
        self._rmc = rmc
        self._gsa = gsa
        self._id = id

    def run(self):
        with socket.socket() as sock:
            try:
                print2(f"Try start NMEA server on port {self._port}...")
                sock.bind((self._host, self._port))
                sock.listen(self._clients)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setblocking(0)
            except socket.error as e:
                print2(e, debug=False, error=True)
                return 1
            print2(f"NMEA server started on port {self._port}")
            while True:
                ready = select.select([sock], [], [], 1)
                if ready[0]:
                    conn, addr = sock.accept()
                    print2(f"Connection detected {addr[0]}:{addr[1]}")
                    client = NMEAClient(conn, addr, rmc=self._rmc, gsa=self._gsa, status=self._status, id=self._id)
                    try:
                        threading.Thread(target=client.process).start()
                    except Exception as e:
                        print2(e, debug=False, error=True)

class NMEAClient():
    _clients = ClientSet()

    def __init__(self, conn, addr, rmc=True, gsa=False, status="A", id="GP"):
        self._conn = conn
        self._addr = addr
        self._port = addr[1]
        self._ip = addr[0]
        self._err = None
        self.rmc = rmc
        self.gsa = gsa
        self.status = status
        self.id = id
        NMEAClient._add_client(self._addr)
        print2(NMEAClient._get_total())

    @classmethod
    def _get_cnt_clients(cls):
        return len(cls._clients)
    
    @classmethod
    def _add_client(cls, addr):
        cls._clients.add(addr) 
        return cls._get_cnt_clients()
        
    @classmethod
    def _del_client(cls, addr):
        try:
            cls._clients.remove(addr)
        except KeyError as e:
            print2(e, debug=False, error=True)
        return cls._get_cnt_clients() 
    
    @classmethod
    def _get_total(cls):
        return f"Total clients: {cls._get_cnt_clients()} {cls._clients}"

    def _gen_rmc(self):
        time_t = time.gmtime()
        hhmmssss = '%02d%02d%02d.000' % (time_t.tm_hour, time_t.tm_min, time_t.tm_sec)
        ddmmyy = time.strftime("%d%m%y", time_t)
        status = self.status
        # $GPRMC,083806.000,A,4916.37598,N,04305.35724,E,0.1,0.0,130519,0.0,W*70/r/n
        #        [время]                                         [дата]
        tmp = pynmea2.RMC(self.id, 'RMC', (
        hhmmssss, status, '4916.45', 'N', '12311.12', 'W', '173.8', '231.8', ddmmyy, '005.2', 'W'))
        rmc_pack = bytes(str(tmp).strip() + "\r\n", 'ascii')
        return rmc_pack

    def _gen_gsa(self):
        # $GNGSA,A,3,10,16,18,20,26,27,,,,,,,4.8,2.0,4.3,1*FF/r/n 
        tmp = pynmea2.GSA(self.id, 'GSA', ('A','3','10','16','18','20','26','27','','','','','','','4.8','2.0','4.3'))
        gsa_pack = bytes(str(tmp).strip() + "\r\n", 'ascii')
        return gsa_pack

    def _gen_packs(self, rmc=True, gsa=False):
        rmc_pack = b''
        gsa_pack = b''
        if rmc:
            rmc_pack = self._gen_rmc()
        if gsa:
            gsa_pack = self._gen_gsa()
        return rmc_pack + gsa_pack

    def _send_packs(self):
        nmea_packs = self._gen_packs(rmc=self.rmc, gsa=self.gsa)
        self._conn.sendall(nmea_packs)
        print(f"{datetime.datetime.now()}\t {self._ip}:{self._port} <-- RX: {nmea_packs}")

    def process(self):
        try:
            while True:
                threading.Timer(INTERVAL_TX_PACKET, self._send_packs).run()               
        except socket.error as e:
            self._err = e
        finally:
            self._close()

    def _close(self):
        msg = f"Client [{self._ip}:{self._port}] connection closed ({self._err})"
        print2(msg)                                                   
        self._conn.close()
        NMEAClient._del_client(self._addr)
        print2(NMEAClient._get_total())

def create_parser():
    parser = argparse.ArgumentParser(description="NMEA protocol emulation of RMC и GSA packages")
    parser.add_argument('-p', '--port', required=False, type=int, default=DEFAULT_PORT)
    parser.add_argument('-r', '--rmc', action='store_true', required=False)
    parser.add_argument('-g', '--gsa', action='store_true', required=False)
    parser.add_argument('-s', '--status', choices=["A", "V"], required=False, type=str, default="A")
    # GP – только GPS - GPGGA
    # GL – только ГЛОНАСС - GLGGA
    # BD – только BeiDou - BDGGA
    # GA – только GALILEO GAGGA
    # GN – мультисистемное решение – GNGGA
    parser.add_argument('-i', '--id', choices=["GP", "GN", "GL", "BD", "GA"], required=False, type=str, default="GP")
    return parser

def exit_gracefully(signal, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, exit_gracefully) 
    
if __name__ == '__main__':
    if IS_WIN:
        print('Press ESC to exit')
    else:
        print('Press CTRL+C to exit')
    parser = create_parser()
    arg = parser.parse_args(sys.argv[1:])
    try:
        ns = NMEAServer(port=arg.port, rmc=arg.rmc, gsa=arg.gsa, status=arg.status, id=arg.id)
        thread_ns = threading.Thread(target=ns.run, daemon=True)
        thread_ns.start()
        while True:
            if not thread_ns.is_alive():
                break
            if IS_WIN and ord(getch()) == 27:  #ESC:
                break
            time.sleep(0.1)
    except Exception as e:
        print2(e, debug=False, error=True)
    finally:
        print2("NMEA server stopped!")
    