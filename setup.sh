#!/bin/bash

# Copy config.ini.default if config.ini doesn't exist.
if [ ! -e config.ini ]; then
    cp config.toml.setup config.toml
    echo "Hello2"
else
    user_line=$(sed '3q;d' config.ini)
    user_version=${user_line//[!0-9]/}
    setup_line=$(sed '3q;d' config.ini)
    setup_version=${setup_line//[!0-9]/}
    if [ "$user_version" -lt "$setup_version" ]; then
        echo "hello"
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
