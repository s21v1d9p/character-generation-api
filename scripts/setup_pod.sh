#!/bin/bash
# RunPod ComfyUI Setup Script
# Run this script after SSH/terminal access to your RunPod pod

set -e

echo "============================================"
echo "Character Generation API - ComfyUI Setup"
echo "============================================"

# Detect ComfyUI location
if [ -d "/workspace/ComfyUI" ]; then
    COMFYUI_DIR="/workspace/ComfyUI"
elif [ -d "/opt/ComfyUI" ]; then
    COMFYUI_DIR="/opt/ComfyUI"
elif [ -d "$HOME/ComfyUI" ]; then
    COMFYUI_DIR="$HOME/ComfyUI"
else
    echo "ERROR: ComfyUI not found. Please install ComfyUI first."
    exit 1
fi

echo "Found ComfyUI at: $COMFYUI_DIR"

# Create directories
echo ""
echo "[1/4] Creating directories..."
mkdir -p "$COMFYUI_DIR/models/checkpoints"
mkdir -p "$COMFYUI_DIR/models/loras"
mkdir -p "$COMFYUI_DIR/models/clip"
mkdir -p "$COMFYUI_DIR/models/vae"
mkdir -p "$COMFYUI_DIR/input"
mkdir -p "$COMFYUI_DIR/output"

# Download SDXL Base Model
echo ""
echo "[2/4] Downloading SDXL Base Model (~6.5GB)..."
cd "$COMFYUI_DIR/models/checkpoints"

if [ -f "sd_xl_base_1.0.safetensors" ]; then
    echo "SDXL Base already exists, skipping..."
else
    echo "Downloading sd_xl_base_1.0.safetensors..."
    wget -c --show-progress \
        "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors"
fi

# Download SVD XT 1.1
echo ""
echo "[3/4] Downloading Stable Video Diffusion XT 1.1 (~9.5GB)..."

if [ -f "svd_xt_1_1.safetensors" ]; then
    echo "SVD XT 1.1 already exists, skipping..."
else
    echo "Downloading svd_xt_1_1.safetensors..."
    wget -c --show-progress \
        "https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt-1-1/resolve/main/svd_xt_1_1.safetensors"
fi

# Install Custom Nodes
echo ""
echo "[4/4] Installing custom nodes..."
cd "$COMFYUI_DIR/custom_nodes"

if [ -d "ComfyUI-VideoHelperSuite" ]; then
    echo "VideoHelperSuite already installed, updating..."
    cd ComfyUI-VideoHelperSuite
    git pull
else
    echo "Installing ComfyUI-VideoHelperSuite..."
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
    cd ComfyUI-VideoHelperSuite
fi

# Install Python dependencies
pip install -r requirements.txt -q

# Verify installation
echo ""
echo "============================================"
echo "Setup Complete! Verifying installation..."
echo "============================================"
echo ""

echo "Checking models:"
if [ -f "$COMFYUI_DIR/models/checkpoints/sd_xl_base_1.0.safetensors" ]; then
    echo "  ✓ SDXL Base Model"
else
    echo "  ✗ SDXL Base Model - MISSING"
fi

if [ -f "$COMFYUI_DIR/models/checkpoints/svd_xt_1_1.safetensors" ]; then
    echo "  ✓ SVD XT 1.1"
else
    echo "  ✗ SVD XT 1.1 - MISSING"
fi

echo ""
echo "Checking custom nodes:"
if [ -d "$COMFYUI_DIR/custom_nodes/ComfyUI-VideoHelperSuite" ]; then
    echo "  ✓ VideoHelperSuite"
else
    echo "  ✗ VideoHelperSuite - MISSING"
fi

echo ""
echo "Checking directories:"
echo "  LoRAs directory: $COMFYUI_DIR/models/loras"
echo "  Input directory: $COMFYUI_DIR/input"
echo "  Output directory: $COMFYUI_DIR/output"

echo ""
echo "============================================"
echo "Next Steps:"
echo "1. Restart ComfyUI to load new models/nodes"
echo "2. Test the API connection from your local machine"
echo "3. Get your pod's URL from RunPod console"
echo "============================================"
