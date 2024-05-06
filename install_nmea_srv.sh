#!/bin/bash
# Скипт создание службы эмуляции NMEA на базе скрипта NmeaServer.py
# Порт сервера NMEA определяется переменной PORT, SERVER_SCRIPT - путь до скрипта NmeaServer.py

if [ "$(id -u)" != 0 ]; then
  echo "This script must be run as root. 'sudo $0'"
  exit 1
fi

if [ ! -f ./NmeaServer.sh ]
then
  echo "Not found NmeaServer.sh script!"
  exit 1
fi

if ! which python3 &> /dev/null
then
    echo "Python3 is not installed!"
    exit 1
fi

if ! which pip3 &> /dev/null
then
    echo "pip3 is not installed!"
    exit 1
fi

if ! pip3 list | grep pynmea2 &> /dev/null
then
   echo "pynmea2 is not installed!"
   exit 1
fi

PORT=50005

PYTHON_EXEC=$(which python3)
SERVER_SCRIPT=$(pwd)/NmeaServer.py
SERVICE_CAPTION=nmea-emulator.service

if [ -f /etc/systemd/system/$SERVICE_CAPTION ] 
then
    echo "$SERVICE_CAPTION is already installed!"
    systemctl status $SERVICE_CAPTION
    exit 1
fi

cat << EOF > /etc/systemd/system/$SERVICE_CAPTION
[Unit]
Description=NMEA emulator script service
After=network.target

[Service]
ExecStart=${PYTHON_EXEC} ${SERVER_SCRIPT} --rmc --gsa --port $PORT
Restart=always
RestartSec=30s

[Install]
WantedBy=multi-user.target
EOF

systemctl enable $SERVICE_CAPTION
systemctl start $SERVICE_CAPTION
systemctl status $SERVICE_CAPTION