#!/usr/bin/python3
import argparse
import socket
import sys
import os
import time
import threading
import pynmea2
import select
import signal
from config_log import setup_logger

logger = setup_logger()

try:
    import keyboard
except ImportError as e:
    logger.error(e)
    
IS_WIN = sys.platform.startswith("win") or (sys.platform == "cli" and os.name == "nt")
DEFAULT_PORT = 5007
INTERVAL_TX_PACKET = 1  # sec

class ClientSet(set):
    def __str__(self):
        return " ".join(f"[{v[0]}:{v[1]}]" for v in self)


class NMEAServer(threading.Thread):
    def __init__(self, host='', port=DEFAULT_PORT, clients=20, 
                 rmc=True, gsa=False, status="A", id="GP", *args, **kwargs):
        super().__init__(*args, **kwargs)
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
                # Флаг SO_REUSEADDR сообщает ядру о необходимости повторно использовать локальный сокет в состоянии TIME_WAIT, 
                # не дожидаясь истечения его естественного тайм-аута.
                logger.info(f"Starting NMEA Server on port {self._port}...")
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self._host, self._port))
                sock.listen(self._clients)
                sock.setblocking(False)
            except socket.error as e:
                logger.error(e.strerror, exc_info=True)
                return
            logger.info(f"NMEA Server started on port {self._port}")
            while True:
                ready = select.select([sock], [], [], 1)
                if ready[0]:
                    conn, addr = sock.accept()
                    logger.info(f"Connection detected from {addr[0]}:{addr[1]}")
                    client = NMEAClient(name=f"NMEAClient {addr}", 
                                        daemon=True,
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
        self._err = ""
        self._lock = threading.RLock()
        NMEAClient._add_client(addr)
        logger.info(NMEAClient._get_total_clients())

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
        with self._lock: # Исключаем гонку потоков. 
            self.status = "V" if self.status == "A" else "A"
            logger.debug(f"New status \"{self.status}\" for RMC packet ({self._addr})")

        
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
        logger.debug(f"{self._ip}:{self._port} <-- TX: {nmea_sentences}")

    def run(self):
        try:
            while True:
                timer_start = time.perf_counter()
                self._send_nmea_sentences()
                time.sleep(max(INTERVAL_TX_PACKET - (time.perf_counter() - timer_start), 0))
        except Exception as e:
            self._err = e
        finally:
            self._close()

    def _close(self):
        msg = f"Client [{self._ip}:{self._port}] connection closed ({self._err})"
        logger.info(msg)
        self._conn.close()
        NMEAClient._del_client(self._addr)
        logger.info(NMEAClient._get_total_clients())
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


def toggle_rmc_status():
    thread_list = [thread for thread in threading.enumerate() if thread.name.startswith('NMEAClient')]
    if thread_list:
        for thr in thread_list:
            thr.toggle_rmc_status()

def keyhandler():
    try:
        keyboard.add_hotkey('space', toggle_rmc_status)
    except ImportError:
        logger.info("Module keyboard work only for root user!")
        

if __name__ == '__main__':
    if os.getppid() != 1:  # если родительский процесс - не  init/systemd
        print('Press ESC to exit' if IS_WIN else 'Press CTRL+C to exit')
        print('Press hotkey Space to change status RMC packet')
        keyhandler()
    args = create_parser().parse_args()
    try:
        server = NMEAServer(name="NMEAServer", daemon=True, port=args.port, 
                            rmc=args.rmc, gsa=args.gsa, status=args.status, id=args.id)
        server.start()
        while server.is_alive():
            if IS_WIN and keyboard.read_key() == "esc": 
                sys.exit(0)
            time.sleep(0.1)
    except Exception as e:
        logger.error(e, exc_info=True)
    finally:
        logger.info("NMEA Server stopped!")