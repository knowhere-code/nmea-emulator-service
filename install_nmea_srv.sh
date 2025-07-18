#!/bin/bash
# Скрипт установки службы эмуляции NMEA на базе скрипта nmeaServer.py
# Порт сервера NMEA определяется переменной PORT, SERVER_SCRIPT - путь до скрипта nmeaServer.py

# Проверка на запуск скрипта от имени root
if [ "$(id -u)" != 0 ]; then
  echo "This script must be run as root. Use 'sudo $0'"
  exit 1
fi

# Проверка наличия скрипта nmeaServer.py
if [ ! -f ./nmeaServer.py ]; then
  echo "nmeaServer.py script not found!"
  exit 1
fi

# Проверка установки Python3
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed!"
    exit 1
fi

# Проверка установки pip3
if ! command -v pip3 &> /dev/null; then
    echo "pip3 is not installed!"
    exit 1
fi

# Проверка установки pynmea2
if ! pip3 list | grep pynmea2 &> /dev/null; then
   echo "pynmea2 is not installed!"
   exit 1
fi

# Проверка установки keyboard
if ! pip3 list | grep keyboard &> /dev/null; then
   echo "keyboard is not installed!"
   exit 1
fi

PORT=50005

PYTHON_EXEC=$(command -v python3)
SERVER_SCRIPT=$(realpath ./nmeaServer.py)
SERVICE_CAPTION=nmea-emulator.service
SERVICE_PATH=/etc/systemd/system/$SERVICE_CAPTION
WORKDIR=$(pwd)

# Проверка, установлен ли уже сервис
if [ -f $SERVICE_PATH ]; then
    echo "$SERVICE_CAPTION is already installed!"
    systemctl status $SERVICE_CAPTION
    exit 1
fi

# Создание файла службы
cat << EOF > $SERVICE_PATH
[Unit]
Description=NMEA emulator script service
After=network.target

[Service]
ExecStart=${PYTHON_EXEC} ${SERVER_SCRIPT} --rmc --gsa --port $PORT
Restart=always
RestartSec=30s
WorkingDirectory=${WORKDIR}
#StandardOutput=append:/var/log/nmeasrv.log

[Install]
WantedBy=multi-user.target
EOF

# Активация и запуск службы
systemctl enable $SERVICE_CAPTION
systemctl start $SERVICE_CAPTION
systemctl status $SERVICE_CAPTION --no-pager

echo "Для остановки: sudo systemctl stop $SERVICE_NAME"
echo "Для просмотра логов: journalctl -u $SERVICE_NAME -f"