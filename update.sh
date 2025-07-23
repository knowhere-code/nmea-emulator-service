#!/bin/bash

GIT_EXEC=$(which git)
${GIT_EXEC} pull

sudo systemctl restart nmea-emulator.service
sudo systemctl restart usv2-emulator.service
sudo systemctl status nmea-emulator.service --no-pager
sudo systemctl status usv2-emulator.service --no-pager
