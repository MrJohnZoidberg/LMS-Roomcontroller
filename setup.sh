#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
DEFAULT_CONFIG_FILE="./config.toml.default"
CONFIG_FILE="./config.toml"
SQUEEZELITE_ENV_FILE=".squeezelite_env"
CONTROLLER_LOG_FILE=".controller.log"
PLAYER_MACS_FILE=".player_macs"

red=$(tput setaf 1)
green=$(tput setaf 2)
yellow=$(tput setaf 3)
reset=$(tput sgr0)

# user config version checking
if [ ! -e $CONFIG_FILE ]; then
    cp $DEFAULT_CONFIG_FILE $CONFIG_FILE
    echo "${yellow}A new config file was created from default config file: $CONFIG_FILE"
    echo "Please open this file now and set the values according to your needs."
    echo "After that, execute this setup file (./setup.sh) again.${reset}"
    exit
else
    user_ver=$(grep "config_ver" $CONFIG_FILE | sed 's/^config_ver=\([0-9]\.[0-9]\)/\1/g')
    def_ver=$(grep "config_ver" $DEFAULT_CONFIG_FILE | sed 's/^config_ver=\([0-9]\.[0-9]\)/\1/g')
    if [ "$def_ver" != "$user_ver" ]; then
        echo "${yellow}Current config options are overwrote by the new default value since they are out of date."
        echo "Please open this file now and change it manually to adapt to your old setup after installation."
        echo "For your previous values, look in config.toml.old${reset}"
        cp $CONFIG_FILE "$CONFIG_FILE.old"
        cp $DEFAULT_CONFIG_FILE $CONFIG_FILE
        exit
    fi
fi

# install packages
echo "${green}Installing required packages... (libev4 libfaad2 liblirc-client0 libmad0 libuv1 libwebsockets8)${reset}"
sudo apt install -y libev4 libfaad2 liblirc-client0 libmad0 libuv1 libwebsockets8
echo "${green}Removing old squeezelite package...${reset}"
sudo apt autoremove -y squeezelite
echo "${green}Downloading squeezelite source from github.com/MrJohnZoidberg...${reset}"
git clone https://github.com/MrJohnZoidberg/squeezelite.git
cd squeezelite || { echo "${red}Failed to download squeezelite source. Exit.${reset}"; exit; }
echo "${green}Installing build dependencies...${reset}"
sudo apt install -y libasound2-dev libflac-dev libmad0-dev libvorbis-dev libmpg123-dev libfaad-dev
echo "${green}Compiling binary file...${reset}"
make
echo "${green}Stopping running services that have /usr/bin/squeezelite open...${reset}"
sudo systemctl stop squeezelite
sudo systemctl stop squeezelite-custom
echo "${green}Copying squeezelite binary to /usr/bin/squeezelite in system...${reset}"
sudo cp ./squeezelite /usr/bin/squeezelite
cd ..
rm -rf squeezelite

PYTHON=$(command -v python3)
VENV=venv

if [ ! -f "$PYTHON" ]; then
    echo "${red}Cannot find Python 3. Please install it. Exit.${reset}"
    exit
fi

if [ "" == "$(dpkg -s python3-venv | grep installed)" ]; then
    echo "${green}Installing python3-venv for virtual environment...${reset}"
    sudo apt-get install -y python3-venv python3.7-venv
fi

echo "${green}Installing requirements with pip...${reset}"
if [ ! -d $VENV ]; then
    # Create a virtual environment if it doesn't exist.
    $PYTHON -m venv $VENV
fi
# Activate the virtual environment and install requirements.
# shellcheck source=/dev/null
. $VENV/bin/activate
pip3 install -r requirements.txt

LMS_SERVICE="
[Unit]
Description=LMS-Roomcontroller
After=network.target multi-user.target

[Service]
Type=idle
WorkingDirectory=$DIR
ExecStart=$DIR/venv/bin/python3 lms-roomcontroller.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
"

SQUEEZELITE_SERVICE="
[Unit]
Description=Squeezelite Player
After=network.target sound.target

[Service]
Nice=-15
LimitRTPRIO=infinity
LimitMEMLOCK=infinity
PIDFile=/run/squeezelite.pid
EnvironmentFile=-$DIR/$SQUEEZELITE_ENV_FILE
ExecStart=/usr/bin/squeezelite \$SB_EXTRA_ARGS

UMask=0002
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
"

touch $SQUEEZELITE_ENV_FILE
touch $CONTROLLER_LOG_FILE
touch $PLAYER_MACS_FILE

# create services
echo "${green}Creating systemd services (lms-roomcontroller.service and squeezelite-custom.service)...${reset}"
echo "$LMS_SERVICE" | sudo tee /lib/systemd/system/lms-roomcontroller.service >/dev/null
echo "$SQUEEZELITE_SERVICE" | sudo tee /lib/systemd/system/squeezelite-custom.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl disable squeezelite
echo "${green}Enabling lms-roomcontroller service...${reset}"
sudo systemctl enable -f lms-roomcontroller
echo "${green}Starting lms-roomcontroller service...${reset}"
sudo systemctl restart lms-roomcontroller
echo "${green}Finished successfully.${reset}"
