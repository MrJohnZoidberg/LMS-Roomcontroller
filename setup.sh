#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
DEFAULT_CONFIG_FILE="./config.toml.default"
CONFIG_FILE="./config.toml"
SQUEEZELITE_ENV_FILE=".squeezelite_env"

# user config version checking
if [ ! -e $CONFIG_FILE ]; then
    cp $DEFAULT_CONFIG_FILE $CONFIG_FILE
    echo "A new config file was created from default config file: $CONFIG_FILE"
    echo "Please open this file now and set the values according to your needs."
    echo "After that, execute this setup file (./setup.sh) again."
    exit 1
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
    echo "Installing requirements with pip..."
    # Activate the virtual environment and install requirements.
    # shellcheck source=/dev/null
    . $VENV/bin/activate
    pip3 install -r requirements.txt
else
    echo "Cannot find Python 3. Please install it."
fi

LMS_SERVICE="
[Unit]
Description=LMS-Roomcontroller
After=network.target multi-user.target

[Service]
Type=idle
WorkingDirectory=$DIR
ExecStart=$DIR/venv/bin/python3 lms-roomcontroller.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"

touch $SQUEEZELITE_ENV_FILE

SQUEEZELITE_SERVICE="
[Unit]
Description=Squeezelite Player
After=network.target sound.target

[Service]
Nice=-10
LimitRTPRIO=98
PIDFile=/run/squeezelite.pid
EnvironmentFile=-$DIR/$SQUEEZELITE_ENV_FILE
ExecStart=/usr/bin/squeezelite $SB_EXTRA_ARGS

[Install]
WantedBy=multi-user.target
"

echo "$LMS_SERVICE" | sudo tee /lib/systemd/system/lms-roomcontroller.service >/dev/null
echo "$SQUEEZELITE_SERVICE" | sudo tee /lib/systemd/system/squeezelite-custom.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl kill -f squeezelite
sudo systemctl disable squeezelite
sudo systemctl enable -f lms-roomcontroller
sudo systemctl start lms-roomcontroller
