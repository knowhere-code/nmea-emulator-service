#!/usr/bin/python3

import argparse
import datetime
import socket
import sys
import time
import threading
import pynmea2
import logging
import select
import signal
from sys import platform

if "win" in platform:
    from msvcrt import getch

def is_win_os():
    if "win" in platform:
        return True
    return False

if is_win_os():
    LOG_PATH = "nmea.log"
else:
    LOG_PATH = "/var/log/nmea.log"
    
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, filename=LOG_PATH, format='%(asctime)s %(levelname)s:%(message)s')
DEFAULT_PORT = 5007
INTERVAL_TX_PACKET = 1 #sec


def bytes_to_str(input_data):
    try:
        is_bytes = isinstance(input_data, bytes)
        is_byte_list = isinstance(input_data, bytearray)

        if not is_bytes and not is_byte_list:
            raise Exception("Входные данные не являются байт строкой/массив")
        s = ""
        for b in input_data:
            s += "_{0:02X}".format(b)
        return s.lstrip('_')
    except Exception as e:
        print(e)
        logger.error(e)


def print2(value, debug=True, error=False):
    print(value)
    if debug:
        logger.debug(value)
    if error:
        logger.error(value)
    

class NMEAServer():

    def __init__(self, host='', port=DEFAULT_PORT, clients=1000, timeout=1, rmc=True, gsa=False, status="A", id="GP"):
        self._port = port
        self._host = host
        self._clients = clients
        self._timeout = timeout
        self._status = status
        self._rmc = rmc
        self._gsa = gsa
        self._id = id

    def run(self):
        with socket.socket() as sock:
            try:
                print2("Try start NMEA server on port {}...".format(self._port))
                sock.bind((self._host, self._port))
                sock.listen(self._clients)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setblocking(0)
            except socket.error as msg:
                print2(msg, debug=False, error=True)
                return 1
            print2("NMEA server started on port {}".format(self._port))
            while True:
                ready = select.select([sock], [], [], 1)
                if ready[0]:
                    conn, addr = sock.accept()
                    conn.settimeout(self._timeout)
                    conn_msg = "Connection detected {}".format(addr)
                    print2(conn_msg)
                    client = ClientClass(conn, addr, self._timeout, rmc=self._rmc, gsa=self._gsa, status=self._status, id=self._id)
                    try:
                        threading.Thread(target=client.process).start()
                    except Exception as msg:
                        print2(msg, debug=False, error=True)

class ClientClass():
    _clients = set()

    def __init__(self, conn, addr, timeout=30, rmc=True, gsa=False, status="A", id="GP"):
        self._conn = conn
        self._addr = addr
        self._port = addr[1]
        self._ip = addr[0]
        self._msg = ''
        self._timeout = timeout
        self.rmc = rmc
        self.gsa = gsa
        self.status = status
        self.id = id
        ClientClass._add_client(self._addr) 
        msg_diag = ClientClass._get_diagnostic()
        print2(msg_diag)

    @classmethod
    def _get_count_clients(cls):
        return len(cls._clients)
    
    @classmethod
    def _add_client(cls, addr):
        cls._clients.add(addr) 
        
    @classmethod
    def _del_client(cls, addr):
        cls._clients.remove(addr)
    
    @classmethod
    def _get_diagnostic(cls):
        return "Total clients: {} {}".format(cls._get_count_clients(), cls._clients)

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
        print("{}\t{}:{} <- RX: {}".format(datetime.datetime.now(), self._ip, self._port, nmea_packs))

    def process(self):
        try:
            while True:
                threading.Timer(INTERVAL_TX_PACKET, self._send_packs).run()               
        except socket.error as msg:
            self._msg = msg
        finally:
            self._close()

    def _close(self):
        # if not self.conn._closed:
        msg = "{}:{} Client connection closed ({})".format(self._ip, self._port,
                                                             self._msg)
        print2(msg)                                                   
        self._conn.close()
        ClientClass._del_client(self._addr)
        print2(ClientClass._get_diagnostic())

def create_parser():
    parser = argparse.ArgumentParser(description="NMEA protocol emulation of RMC и GSA packages")
    parser.add_argument('-p', '--port', required=False, type=int, default=DEFAULT_PORT)
    parser.add_argument('-t', '--timeout', required=False, type=int, default=5)
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
    
    
if __name__ == '__main__':
    if is_win_os():
        print('Press ESC to exit')
    else:
        print('Press CTRL+C to exit')
    parser = create_parser()
    arg = parser.parse_args(sys.argv[1:])
    try:
        ns = NMEAServer(port=arg.port, timeout=arg.timeout, rmc=arg.rmc, gsa=arg.gsa, status=arg.status, id=arg.id)
        thread_ns = threading.Thread(target=ns.run, daemon=True)
        thread_ns.start()
        while True:
            if not thread_ns.is_alive():
                break
            if is_win_os():
                if ord(getch()) == 27:  #ESC
                    break
            signal.signal(signal.SIGINT, exit_gracefully)
            time.sleep(0.1)
    except Exception as msg:
        print2(msg, debug=False, error=True)
    finally:
        print2("NMEA server stopped!")
    