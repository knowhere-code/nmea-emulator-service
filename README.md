# NMEA EMULATOR SERVICE

Сервис эмулирует работу NMEA протокола. Генерируются RMC и GSA пакеты. Сервис поддерживает работу одновременно с множеством TCP клиентов.

## Installation

Установка зависимостей.

```sh
sudo apt update
sudo apt install pip3
sudo pip3 intall pynmea2
```

Установка службы systemd.unit.

Копируем файлы install_nmea_srv.sh, NmeaServer.py в папку от куда служба NMEA EMULATOR SERVICE будет запускаться и запускаем скрипт с правами sudo

```sh
install_nmea_srv.sh
```

Сервис будет доступен на сокете 127.0.0.1:50005

```sh
telnet 127.0.0.1 50005
```

Ключи:

options:  

  -h, --help  

  -p PORT, --port PORT                           Серверный порт для подкючения клиентов (по умолчанию 50005)  

  -t TIMEOUT, --timeout TIMEOUT                  Таймаут  

  -r, --rmc                                      Ключ генерации RMC пакетов  

  -g, --gsa                                      Ключ генерации GSA пакетов  

  -s {A,V}, --status {A,V}                       Генерация пакетов RMC c A - валидным статусом, V - невалидный статус  

  -i {GP,GN,GL,BD,GA}, --id {GP,GN,GL,BD,GA}     Индификатор GPS системы по умолчанию (GP)  

License
MIT

Free Software, Hell Yeah!
