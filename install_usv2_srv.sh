#!/bin/bash
# Скрипт установки службы эмуляции USV2 на базе скрипта usv2Server
# Порт сервера NMEA определяется переменной PORT, SERVER_SCRIPT - путь до скрипта usv2Server

# Проверка на запуск скрипта от имени root
if [ "$(id -u)" != 0 ]; then
  echo "This script must be run as root. Use 'sudo $0'"
  exit 1
fi

# Проверка наличия скрипта usv2Server.py
if [ ! -f ./usv2Server.py ]; then
  echo "usv2Server.py script not found!"
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


# Проверка установки keyboard
if ! pip3 list | grep keyboard &> /dev/null; then
   echo "keyboard is not installed!"
   exit 1
fi

PORT=50006

PYTHON_EXEC=$(command -v python3)
SERVER_SCRIPT=$(realpath ./usv2Server.py)
SERVICE_CAPTION=usv2-emulator.service
SERVICE_PATH=/etc/systemd/system/$SERVICE_CAPTION

# Проверка, установлен ли уже сервис
if [ -f $SERVICE_PATH ]; then
    echo "$SERVICE_CAPTION is already installed!"
    systemctl status $SERVICE_CAPTION
    exit 1
fi

# Создание файла службы
cat << EOF > $SERVICE_PATH
[Unit]
Description=USV2 emulator script service
After=network.target

[Service]
ExecStart=${PYTHON_EXEC} ${SERVER_SCRIPT} --port $PORT
Restart=always
RestartSec=30s
WorkingDirectory=${SERVER_SCRIPT}
#StandardOutput=append:/var/log/usv2srv.log

[Install]
WantedBy=multi-user.target
EOF

# Активация и запуск службы
systemctl enable $SERVICE_CAPTION
systemctl start $SERVICE_CAPTION
systemctl status $SERVICE_CAPTION