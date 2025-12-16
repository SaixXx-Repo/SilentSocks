#!/bin/bash

# Determine where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================"
echo "   Sales Analysis App - Setup & Run"
echo "========================================"
echo ""

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 could not be found."
    echo "Please install Python 3 from https://www.python.org/downloads/"
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "First time setup: Creating virtual environment..."
    echo "This may take a few minutes."
    
    python3 -m venv venv
    
    if [ ! -d "venv" ]; then
        echo "❌ Failed to create virtual environment."
        read -n 1
        exit 1
    fi
    
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies."
        echo "Check your internet connection."
        read -n 1
        exit 1
    fi
    
    echo "✅ Setup complete!"
else
    echo "Environment found. Activating..."
    source venv/bin/activate
fi

echo ""
echo "🚀 Starting the application..."
echo "Your browser should open automatically."
echo "To stop the app, close this terminal window."
echo ""

# Run the app
streamlit run app.py

# Keep window open if it crashes immediately
echo ""
echo "App stopped."
read -p "Press Enter to close..."

