#!/bin/bash

GIT_EXEC=$(which git)
${GIT_EXEC} pull

sudo systemctl restart nmea-emulator.service
