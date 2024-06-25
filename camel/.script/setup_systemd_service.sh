#!/bin/bash

WORK_SPACE_DIR=~/.local/camel
SYSTEMD_FILE_DIR=~/.config/systemd/user
SCRIPT_FOLDER_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
LIB_HOME_DIR=$( cd -- "$( dirname -- "$SCRIPT_FOLDER_DIR" )" &> /dev/null && pwd )
VENV_BIN_DIR="$( dirname -- "$(which python3)" )"
LOG_DIR=$WORK_SPACE_DIR/logs

mkdir -p $SYSTEMD_FILE_DIR

if [ ! -d $LOG_DIR ]; then
    echo "Creating camel working directory..."
    mkdir -p $LOG_DIR
    echo "camel working directory: $WORK_SPACE_DIR"
fi

# Initialize camel config file
echo "Initializing camel config file..."
echo "[Service]
host = "127.0.0.1"
port = "8000"" > $SYSTEMD_FILE_DIR/camel.conf

# Initialize camel systemd unit file
echo "Initializing camel systemd unit file..."
echo "[Unit]
Description=CAMEL Project app
After=network.target

[Service]
WorkingDirectory=$WORK_SPACE_DIR
Environment=PATH=$VENV_BIN_DIR:\$PATH
EnvironmentFile=-$SYSTEMD_FILE_DIR/camel.conf
ExecStart=$VENV_BIN_DIR/python $LIB_HOME_DIR/serve/openai_api_server.py --host \$host --port \$port
StandardOutput=append:$LOG_DIR/camel.log
StandardError=append:$LOG_DIR/camel_err.log

[Install]
WantedBy=default.target" > $SYSTEMD_FILE_DIR/camel.service

# reload systemd user daemon
systemctl --user daemon-reload

exit 0