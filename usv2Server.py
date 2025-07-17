#!/usr/bin/python3
import argparse
import datetime
import socket
import sys
import os
import time
import threading
import select
import signal
import keyboard
from config_log import setup_logger

logger = setup_logger("usv2srv.log")

IS_WIN = sys.platform.startswith("win") or (sys.platform == "cli" and os.name == "nt")
DEFAULT_PORT = 5008


class ClientSet(set):
    def __str__(self):
        return " ".join(f"[{v[0]}:{v[1]}]" for v in self)


class USV2Server:
    def __init__(self, host='', port=DEFAULT_PORT, clients=20):
        self._host = host
        self._port = port
        self._clients = clients



    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                # Флаг SO_REUSEADDR сообщает ядру о необходимости повторно использовать локальный сокет в состоянии TIME_WAIT, 
                # не дожидаясь истечения его естественного тайм-аута.
                logger.info(f"Starting USV2 Server on port {self._port}...")
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self._host, self._port))
                sock.listen(self._clients)
                sock.setblocking(True)
            except socket.error as e:
                logger.error(e.strerror, exc_info=True)
                return
            logger.info(f"USV2 Server started on port {self._port}")
            while True:
                ready = select.select([sock], [], [], 1)
                if ready[0]:
                    conn, addr = sock.accept()
                    logger.info(f"Connection detected from {addr[0]}:{addr[1]}")
                    client = USV2Client(name=f"USV2Client {addr}", 
                                        daemon=True,
                                        conn=conn, 
                                        addr=addr,
                                        )
                    client.start()


class USV2Client(threading.Thread):
    _clients = ClientSet()

    def __init__(self, conn=None, addr=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conn = conn
        self._addr = addr
        self._ip, self._port = addr
        self._err = ""
        self._status_clock = b'\x00'
        self._lock = threading.RLock()
        
        USV2Client._add_client(addr)
        logger.info(USV2Client._get_total_clients())

    @classmethod
    def _add_client(cls, addr):
        cls._clients.add(addr)

    @classmethod
    def _del_client(cls, addr):
        cls._clients.discard(addr)

    @classmethod
    def _get_total_clients(cls):
        return f"Total clients: {len(cls._clients)} {cls._clients}"


    def bytes2str(self, input_data, ascii=False):
        try:
            is_bytes = isinstance(input_data, bytes)
            is_byte_list = isinstance(input_data, bytearray)

            if not is_bytes and not is_byte_list:
                raise Exception("Входные данные не являются байт строкой/массив")
            s = ""
            if ascii:
                input_data = input_data.decode("ascii")
            for byte in input_data:
                if ascii:
                    s += f"{byte}"
                else:
                    s += f"_{byte:02X}"
            return s.lstrip('_')
        except Exception as e:
            logger.error(e, exc_info=True)
            
            
    def toggle_clock_status(self):
        with self._lock: # Исключаем гонку потоков. 
            self._status_clock = b'\x80' if self._status_clock == b'\x00' else b'\x00'
            print(f"New status clock \"{self._status_clock}\" for ({self._addr})")


    def to_bcd(self, num: int) -> int:
    # """Конвертирует число в BCD-формат (например, 23 → 0x23)."""
        return ((num // 10) << 4) | (num % 10)
    
    
    def _get_date_time_now(self):
        dt = datetime.datetime.now()
        YY = dt.strftime("%y")  # Год (23)
        MM = dt.strftime("%m")  # Месяц (10)
        DD = dt.strftime("%d")  # День (15)
        hh = dt.strftime("%H")  # Часы (12)
        mm = dt.strftime("%M")  # Минуты (30)
        ss = dt.strftime("%S")  # Секунды (45)
        dt_bcd_bytes = bytes([
            self.to_bcd(int(YY)),  # 23 → 0x23
            self.to_bcd(int(MM)),  # 10 → 0x10
            self.to_bcd(int(DD)),  # 15 → 0x15
            self.to_bcd(int(hh)),  # 12 → 0x12
            self.to_bcd(int(mm)),  # 30 → 0x30
            self.to_bcd(int(ss))   # 45 → 0x45
        ])
        return dt_bcd_bytes 
       
    def _calc_crc(self, data):
        crc = sum(data[2:]) & 0xFF
        return bytes([crc])
         
    def _send_dt_packet(self):
        try:
            tx = self.make_dt_packet()
            self._conn.send(tx)
            logger.info(f"{datetime.datetime.now()}\t{self._ip}:{self._port} <- TX: {self.bytes2str(tx)}")
        except Exception as e:
            logger.error(e, exc_info=True)

    def make_dt_packet(self):
        # self._conn.send(b'\x73\x0A\x14\x03\x31\x13\x41\x05\x00\x00\x00\x21')
        dtb = self._get_date_time_now()
        data = b'\x73\x0A' + dtb + b'\x00\x00' + self._status_clock
        crc = self._calc_crc(data)
        tx = data + crc
        return tx
      
            
    def run(self):
        try:
            while True:
                # метод блокирующий, а это значит что к if not tmp перейдет только после того, как клиент отвалится и вернется 0 байт
                rx = self._conn.recv(1024)
                logger.info(f"{datetime.datetime.now()}\t{self._ip}:{self._port} -> RX: {self.bytes2str(rx)}")
                if not rx:
                    break
                if b's' in rx:
                    self._send_dt_packet()    
        except Exception as e:
            self._err = e
        finally:
            self._close()


    def _close(self):
        msg = f"Client [{self._ip}:{self._port}] connection closed ({self._err})"
        logger.info(msg)
        self._conn.close()
        USV2Client._del_client(self._addr)
        logger.info(USV2Client._get_total_clients())
        # Close thread
        sys.exit()


def create_parser():
    parser = argparse.ArgumentParser(description="USV2 protocol emulation")
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT, help='Port to run the server on')
    return parser


def exit_gracefully(signal, frame):
    sys.exit(0)


signal.signal(signal.SIGINT, exit_gracefully)


def toggle_clock_status():
    thread_list = [thread for thread in threading.enumerate() if thread.name.startswith('USV2Client')]
    if thread_list:
        for thr in thread_list:
            thr.toggle_clock_status()


if __name__ == '__main__':
    print('Press ESC to exit' if IS_WIN else 'Press CTRL+C to exit')
    print('Press hotkey Space to change status time USV2')
    keyboard.add_hotkey('space', toggle_clock_status)
    args = create_parser().parse_args()
    try:
        ns = USV2Server(port=args.port)
        thread_ns = threading.Thread(name="USV2Server", target=ns.run, daemon=True)
        thread_ns.start()
        while thread_ns.is_alive():
            if keyboard.read_key() == "esc": 
                sys.exit(0)
            time.sleep(0.1)
    except Exception as e:
        logger.error(e, exc_info=True)
    finally:
        logger.info("USV2 Server stopped!")