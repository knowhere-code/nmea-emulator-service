import asyncio
from datetime import datetime
import sys

# Глобальные переменные
clients = set()
current_status = "A"
position = (4807.38, "N", 1131.00, "E")

def generate_rmc():
    """Генерация NMEA RMC пакета"""
    time = datetime.utcnow().strftime("%H%M%S.%f")[:10]
    date = datetime.utcnow().strftime("%d%m%y")
    lat, lat_dir, lon, lon_dir = position
    #$GPRMC, 064016.000, A, 4916.45, N, 12311.12, W ,173.8,231.8,130525, 005.2, W*67 
    
    #$GPRMC, 064032.648, A, 4807.038, N, 1131.000, E, 0.0, 0.0, 130525, , *0012 
    nmea = f"GPRMC,{time},{current_status},{lat:.3f},{lat_dir},{lon:.3f},{lon_dir},0.0,0.0,{date},,W"
    checksum = calculate_checksum(nmea)
    return f"${nmea}*{checksum}\r\n".encode()

def calculate_checksum(s):
    """Вычисление контрольной суммы NMEA"""
    checksum = 0
    for c in s:
        checksum ^= ord(c)
    return f"{checksum:02X}"

async def handle_client(reader, writer):
    """Обработка клиентского подключения"""
    addr = writer.get_extra_info('peername')
    print(f"Подключен новый клиент: {addr}")
    clients.add(writer)
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(reader.read(100), timeout=1.0)
                if not data:
                    break
                print(f"Получено от {addr}: {data.decode().strip()}")
            except asyncio.TimeoutError:
                continue
    except Exception as e:
        print(f"Ошибка с клиентом {addr}: {e}")
    finally:
        clients.discard(writer)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        print(f"Клиент {addr} отключен")

async def broadcast_nmea():
    """Регулярная рассылка данных клиентам"""
    while True:
        if clients:
            packet = generate_rmc()
            for writer in list(clients):
                try:
                    writer.write(packet)
                    await writer.drain()
                except Exception as e:
                    print(f"Ошибка отправки: {e}")
                    clients.discard(writer)
        await asyncio.sleep(1)

def toggle_status():
    """Смена статуса A/V"""
    global current_status
    current_status = "V" if current_status == "A" else "A"
    print(f"\nСтатус изменен на {current_status}")

async def keyboard_monitor():
    """Мониторинг клавиатуры для смены статуса"""
    if sys.platform == "win32":
        import msvcrt
        while True:
            if msvcrt.kbhit() and msvcrt.getch() == b' ':
                toggle_status()
            await asyncio.sleep(0.1)
    else:
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        while True:
            char = await reader.read(1)
            if char == b' ':
                toggle_status()


async def cleanup():
    """Очистка подключений"""
    for writer in list(clients):
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

async def main():
    """Основная функция"""
    server = await asyncio.start_server(
        handle_client,
        '0.0.0.0',
        8888
    )
    
    print(f"Сервер NMEA запущен на tcp://0.0.0.0:8888")
    print("Нажмите пробел для смены статуса (A/V)")
    
    asyncio.create_task(broadcast_nmea())
    asyncio.create_task(keyboard_monitor())
    
    try:
        async with server:
            await server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен")
    finally:
        print("Очистка подключений...")
        await cleanup()

if __name__ == "__main__":
    asyncio.run(main())