#!/bin/bash

echo "🔧 Rebuilding venv with Python 3.11..."

# Remove any old venv created with Python 3.13
rm -rf .venv

# Create new venv with correct version
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements1.txt

echo "✅ Build completed with Python $(python --version)"
