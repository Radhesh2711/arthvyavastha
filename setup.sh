#!/bin/bash
# Artha Vyavastha — one-time setup and launch (macOS / Linux)

set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "Starting Artha Vyavastha..."
echo "The app will open in your browser shortly."
echo ""
streamlit run app.py
