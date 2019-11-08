#!/bin/bash

DEFAULT_CONFIG_FILE="./config.toml.default"
CONFIG_FILE="./config.toml"

if [ "$EUID" -ne 0 ]
    then echo "Please run as root - Exiting..."
    exit 1
fi

# user config version checking
if [ ! -e $CONFIG_FILE ]; then
    cp $DEFAULT_CONFIG_FILE $CONFIG_FILE
else
    user_ver=$(grep "config_ver" $CONFIG_FILE | sed 's/^config_ver=\([0-9]\.[0-9]\)/\1/g')
    def_ver=$(grep "config_ver" $DEFAULT_CONFIG_FILE | sed 's/^config_ver=\([0-9]\.[0-9]\)/\1/g')

    if [ "$def_ver" != "$user_ver" ]
    then
        echo "Current config options are overwrote by the new default value since they are out of date"
        echo "The lastest config.ini version is $def_ver"
        echo "Please change it manually to adapt to your old setup after installation"
        echo "For your previous values, look in config.toml.old"
        cp $CONFIG_FILE "$CONFIG_FILE.old"
        cp $DEFAULT_CONFIG_FILE $CONFIG_FILE
    else
        echo "Good config.ini version: $user_ver"
    fi
fi

PYTHON=$(command -v python3)
VENV=venv

if [ -f "$PYTHON" ]
then
    if [ ! -d $VENV ]
    then
        # Create a virtual environment if it doesn't exist.
        $PYTHON -m venv $VENV
    fi
    # Activate the virtual environment and install requirements.
    # shellcheck source=/dev/null
    . $VENV/bin/activate
    pip3 install -r requirements.txt
else
    echo "Cannot find Python 3. Please install it."
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

LMS_SERVICE="
[Unit]
Description=LMS-Roomcontroller
After=network.target multi-user.target

[Service]
Type=idle
WorkingDirectory=$DIR
ExecStart=$DIR/venv/bin/python3 main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"

SQUEEZELITE_SERVICE="
[Unit]
Description=Squeezelite Player
After=network.target sound.target

[Service]
Nice=-10
LimitRTPRIO=98
PIDFile=/run/squeezelite.pid
EnvironmentFile=-/etc/default/squeezelite
ExecStart=/usr/bin/squeezelite $SB_EXTRA_ARGS

[Install]
WantedBy=multi-user.target
"

echo "$LMS_SERVICE" | tee /lib/systemd/system/lms-roomcontroller.service
echo "$SQUEEZELITE_SERVICE" | tee /lib/systemd/system/squeezelite-custom.service
