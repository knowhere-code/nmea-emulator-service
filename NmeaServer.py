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
import keyboard

IS_WIN = sys.platform.startswith("win") or (sys.platform == "cli" and os.name == "nt")
DEFAULT_PORT = 5007
INTERVAL_TX_PACKET = 1  # sec

if IS_WIN:
    from msvcrt import getch

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = f"{BASE_DIR}/nmea.log" if IS_WIN else "/var/log/nmea.log"

try:
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG, filename=LOG_PATH, format='%(asctime)s %(levelname)s:%(message)s')
except PermissionError as e:
    print(f"PermissionError: {e}")

def print2(value, debug=True, error=False):
    print(value)
    if debug:
        logger.debug(value)
    if error:
        logger.error(value)


class ClientSet(set):
    def __str__(self):
        return " ".join(f"[{v[0]}:{v[1]}]" for v in self)


class NMEAServer:
    def __init__(self, host='', port=DEFAULT_PORT, clients=20, rmc=True, gsa=False, status="A", id="GP"):
        self._host = host
        self._port = port
        self._clients = clients
        self._rmc = rmc
        self._gsa = gsa
        self._status = status
        self._id = id

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                print2(f"Starting NMEA server on port {self._port}...")
                sock.bind((self._host, self._port))
                sock.listen(self._clients)
                sock.setblocking(False)
            except socket.error as e:
                print2(e.strerror, debug=False, error=True)
                return
            print2(f"NMEA server started on port {self._port}")
            while True:
                ready = select.select([sock], [], [], 1)
                if ready[0]:
                    conn, addr = sock.accept()
                    print2(f"Connection detected from {addr[0]}:{addr[1]}")
                    client = NMEAClient(name=f"NMEAClient {addr}",
                                        conn=conn, 
                                        addr=addr,
                                        rmc=self._rmc, 
                                        gsa=self._gsa, 
                                        status=self._status, 
                                        id=self._id
                                        )
                    client.start()


class NMEAClient(threading.Thread):
    _clients = ClientSet()

    def __init__(self, conn=None, addr=None, rmc=True, gsa=False, status="A", id="GP", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conn = conn
        self._addr = addr
        self._ip, self._port = addr
        self.rmc = rmc
        self.gsa = gsa
        self.status = status
        self.id = id
        self._lock = threading.RLock()
        NMEAClient._add_client(addr)
        print2(NMEAClient._get_total_clients())

    @classmethod
    def _add_client(cls, addr):
        cls._clients.add(addr)

    @classmethod
    def _del_client(cls, addr):
        cls._clients.discard(addr)

    @classmethod
    def _get_total_clients(cls):
        return f"Total clients: {len(cls._clients)} {cls._clients}"

            
    def toggle_rmc_status(self):
        with self._lock:
            self.status = "V" if self.status == "A" else "A"
            print(f"New status \"{self.status}\" for RMC packet ({self._addr})")

        
    def _make_nmea_sentence(self):
        time_t = time.gmtime()
        hhmmssss = f'{time_t.tm_hour:02d}{time_t.tm_min:02d}{time_t.tm_sec:02d}.000'
        ddmmyy = time.strftime("%d%m%y", time_t)

        sentences = []
        if self.rmc:
            rmc = pynmea2.RMC(self.id, 'RMC', (
                hhmmssss, self.status, '4916.45', 'N', '12311.12', 'W', '173.8', '231.8', ddmmyy, '005.2', 'W'))
            sentences.append(str(rmc).strip())

        if self.gsa:
            gsa = pynmea2.GSA(self.id, 'GSA', ('A', '3', '10', '16', '18', '20', '26', '27', '', '', '', '', '', '', '4.8', '2.0', '4.3'))
            sentences.append(str(gsa).strip())

        return "\r\n".join(sentences).encode('ascii') + b'\r\n'

    def _send_nmea_sentences(self):
        nmea_sentences = self._make_nmea_sentence()
        self._conn.sendall(nmea_sentences)
        print(f"{datetime.datetime.now()}\t {self._ip}:{self._port} <-- TX: {nmea_sentences}")

    def run(self):
        try:
            while True:
                threading.Timer(INTERVAL_TX_PACKET, self._send_nmea_sentences).run()
        except Exception as e:
            self._err = e
        finally:
            self._close()

    def _close(self):
        msg = f"Client [{self._ip}:{self._port}] connection closed ({self._err})"
        print2(msg)
        self._conn.close()
        NMEAClient._del_client(self._addr)
        print2(NMEAClient._get_total_clients())
        # Close thread
        sys.exit()


def create_parser():
    parser = argparse.ArgumentParser(description="NMEA protocol emulation of RMC and GSA packages")
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT, help='Port to run the server on')
    parser.add_argument('-r', '--rmc', action='store_true', help='Include RMC sentences')
    parser.add_argument('-g', '--gsa', action='store_true', help='Include GSA sentences')
    parser.add_argument('-s', '--status', choices=["A", "V"], default="A", help='Status character for RMC sentence')
    parser.add_argument('-i', '--id', choices=["GP", "GN", "GL", "BD", "GA"], default="GP", help='Talker ID')
    return parser


def exit_gracefully(signal, frame):
    sys.exit(0)


signal.signal(signal.SIGINT, exit_gracefully)


if __name__ == '__main__':
    print('Press ESC to exit' if IS_WIN else 'Press CTRL+C to exit')
    print('Press hotkey Space to change status RMC packet')
    parser = create_parser()
    args = parser.parse_args()
    try:
        ns = NMEAServer(port=args.port, rmc=args.rmc, gsa=args.gsa, status=args.status, id=args.id)
        thread_ns = threading.Thread(name="NMEAServer", target=ns.run, daemon=True)
        thread_ns.start()
        while thread_ns.is_alive():
            if keyboard.read_key() == "esc": 
                sys.exit()
            if keyboard.read_key() == "space":
                thread_list = [thread for thread in threading.enumerate() if thread.name.startswith('NMEAClient')]
                if thread_list:
                    for thr in thread_list:
                        thr.toggle_rmc_status()
            time.sleep(0.1)
    except Exception as e:
        print2(e, debug=False, error=True)
    finally:
        print2("NMEA server stopped!")