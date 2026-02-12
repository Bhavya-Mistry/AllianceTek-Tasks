#!/bin/bash

# Navigate to the project directory
cd /home/ubuntu/chess-automation/chess-automation/

# Activate the virtual environment
source venv/bin/activate

# Run the main script
nohup python3 main.py &