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
Можно проверить командой:

```sh
telnet 127.0.0.1 50005
```

License
MIT

Free Software, Hell Yeah!
