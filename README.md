# NMEA EMULATOR SERVICE

Сервис генерирует пакеты RMC и GSA NMEA протокола, подключенным по TCP/IP клиентам.

## Installation

Установка зависимостей deb linux.

```sh
sudo apt update
sudo apt install pip3
sudo pip3 intall pynmea2
```

Запуск сервиса в консольном режиме:

```sh
sudo python3 NmeaServer.py --rmc --gsa --port 50005
```

Установка сервиса как демона systemd.unit

```sh
sudo ./install_nmea_srv.sh
```

Сервис будет доступен на сокете 127.0.0.1:50005

```sh
telnet 127.0.0.1 50005
```

options:  

  -h, --help  

  -p PORT, --port PORT                           Серверный порт для подкючения клиентов (по умолчанию 5007)  

  -t TIMEOUT, --timeout TIMEOUT                  Таймаут  

  -r, --rmc                                      Ключ генерации RMC пакетов  

  -g, --gsa                                      Ключ генерации GSA пакетов  

  -s {A,V}, --status {A,V}                       Генерация пакетов RMC c A - валидным статусом, V - невалидный статус  

  -i {GP,GN,GL,BD,GA}, --id {GP,GN,GL,BD,GA}     Индификатор GPS системы по умолчанию (GP)  
