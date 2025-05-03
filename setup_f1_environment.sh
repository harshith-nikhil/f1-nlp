#!/bin/bash

echo "Setting up F1 Chatbot Project Environment..."

# Step 1: Install System-Level Non-Python dependencies
echo "Checking if Rust (cargo) is installed..."
if ! command -v cargo &> /dev/null
then
    echo "Rust is not installed. Installing Rust using rustup..."
    curl https://sh.rustup.rs -sSf | sh -s -- -y
    source $HOME/.cargo/env
else
    echo "Rust is already installed."
fi

echo "Checking if gcc is installed..."
if ! command -v gcc &> /dev/null
then
    echo "gcc is not installed. Please install gcc manually (e.g., sudo apt install build-essential OR via Xcode on Mac)."
    exit 1
else
    echo "gcc is installed."
fi

# Step 2: Setup Python Virtual Environment
echo "Creating Python virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

# Step 3: Upgrade pip and build tools
echo "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Step 4: Install Python packages
echo "Installing required Python packages..."
pip install numpy==1.24.4 pandas fastf1 pandasai openai matplotlib scipy notebook ipykernel

# Step 5: Register venv as a Jupyter kernel
echo "Setting up Jupyter Kernel..."
python -m ipykernel install --user --name=f1-env --display-name "Python (f1-env)"

echo "Setup complete!"
echo ""
echo "To start working:"
echo "1. source venv/bin/activate"
echo "2. jupyter notebook"
echo "3. Select kernel 'Python (f1-env)' in Jupyter"
echo ""
echo "🏎️ Good luck with your F1 Project!"