#!/bin/bash

# SmartPlant Deployment Script for Raspberry Pi
echo "Starting SmartPlant installation..."

# 1. Update system
echo "Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install Python dependencies
echo "Installing Python and virtualenv..."
sudo apt-get install -y python3 python3-pip python3-venv

# 3. Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 4. Install project requirements
echo "Installing Python requirements..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Setup Serial Permissions
echo "Adding user to dialout group for serial access..."
sudo usermod -a -G dialout $USER

echo "-------------------------------------------------------"
echo "Setup complete! Please REBOOT or LOG OUT and LOG IN"
echo "to apply group changes (serial access)."
echo ""
echo "To run the system manually: source venv/bin/activate && python main.py"
echo "-------------------------------------------------------"
