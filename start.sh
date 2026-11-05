#!/usr/bin/env bash

# --------------------------------------------------------------------------- #
#  Mantis Bots™ - Startup Shell Script                                        #
#  Installs/Updates Dependencies and Boots Up the Telegram Bot                  #
# --------------------------------------------------------------------------- #

# Upgrade and install requirements securely
pip3 install -U -r requirements.txt

# Log startup message
echo "Starting Bot....✅"

# Execute the main bot application
python3 bot.py
