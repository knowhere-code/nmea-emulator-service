# NMEA Emulator Service

[![Python 3.8.5](https://img.shields.io/badge/python-3.8.5-blue.svg)](https://www.python.org/downloads/release/python-385/)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)

Сервис **NMEA Emulator Service** для нужд тестирования генерирует пакеты RMC и GSA NMEA протокола, подключенным по TCP/IP клиентам.

## Установка

Установка зависимостей deb linux.

```sh
sudo apt update
sudo apt install pip3
```
```bash
sudo pip3 intall pynmea2
sudo pip3 intall keyboard
или
sudo pip3 install -r requirements.txt
```

Пример запуска сервиса в консольном режиме:

```sh
sudo python3 NmeaServer.py --rmc --gsa --port 5007
```

По пробелу можно переключать статус RMC пакета с A на V

Установка сервиса как демона systemd.unit

```sh
sudo ./install_nmea_srv.sh
```

Сервис будет доступен на сокете 127.0.0.1:5007

```sh
telnet 127.0.0.1 5007
```

options:
``` 
  -h, --help  
  -p PORT, --port PORT                           Серверный порт для подключения клиентов (по умолчанию 5007)  
  -r, --rmc                                      Ключ генерации RMC пакетов  
  -g, --gsa                                      Ключ генерации GSA пакетов  
  -s {A,V}, --status {A,V}                       Генерация пакетов RMC c A - валидным статусом, V - невалидный статус (по умолчанию А) 
  -i {GP,GN,GL,BD,GA}, --id {GP,GN,GL,BD,GA}     Индификатор GPS системы (по умолчанию GP)  
```
