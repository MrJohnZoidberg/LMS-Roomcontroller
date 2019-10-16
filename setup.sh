#!/bin/bash

# Copy config.ini.default if config.ini doesn't exist.
if [ ! -e config.toml ]; then
    cp config.toml.setup config.toml
else
    user_line=$(sed '3q;d' config.toml)
    user_version=${user_line//[!0-9]/}
    setup_line=$(sed '3q;d' config.toml.setup)
    setup_version=${setup_line//[!0-9]/}
    if [ "$user_version" -lt "$setup_version" ]; then
        cp config.toml config.toml.old
        cp config.toml.setup config.toml
        echo "The config.toml file has been updated and all values are reset to default."
        echo "For your previous values, look in config.toml.old"
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
