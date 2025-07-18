#!/bin/bash

GIT_EXEC=$(which git)
${GIT_EXEC} pull

sudo systemctl restart nmea-emulator.service
sudo systemctl restart usv2-emulator.service
