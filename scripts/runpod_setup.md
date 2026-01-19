# RunPod ComfyUI Deployment Guide

This guide walks through deploying a ComfyUI GPU pod on RunPod for the Character Generation API.

## Step 1: Create a RunPod Pod

### Option A: Use Pre-built ComfyUI Template (Recommended)

1. Go to [RunPod Console](https://www.runpod.io/console/pods)
2. Click **"+ Deploy"**
3. Search for template: **"ComfyUI"** or **"TheLastBen ComfyUI"**
4. Select a GPU:
   - **Budget**: RTX 4090 (24GB VRAM) - ~$0.44/hr
   - **Recommended**: RTX A5000 (24GB) - ~$0.39/hr
   - **Premium**: A100 (40/80GB) - for larger batches
5. Set **Volume Size**: 50GB minimum (for models)
6. Enable **Expose HTTP Ports**: `8188` (ComfyUI) and `3000` (optional web UI)
7. Click **Deploy**

### Option B: Custom Docker Template

If you need more control, use this template:

```
Template Name: comfyui-character-gen
Container Image: ghcr.io/ai-dock/comfyui:pytorch-2.1.1-py3.10-cuda-12.1.0-runtime
Container Disk: 20GB
Volume Disk: 50GB
Volume Mount Path: /workspace
Expose HTTP Ports: 8188,3000
Expose TCP Ports: 22
```

## Step 2: Download Required Models

Once the pod is running, connect via **Web Terminal** and run:

```bash
# Navigate to ComfyUI models directory
cd /workspace/ComfyUI/models

# 1. Download SDXL Base Model (Required for image generation)
cd checkpoints
wget -c "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors"

# 2. Download SVD XT 1.1 (Required for video generation)
wget -c "https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt-1-1/resolve/main/svd_xt_1_1.safetensors"

# 3. Create loras directory if it doesn't exist
mkdir -p ../loras
```

**Model Sizes:**
- `sd_xl_base_1.0.safetensors`: ~6.5GB
- `svd_xt_1_1.safetensors`: ~9.5GB

Total download: ~16GB (allow 10-15 minutes on fast connection)

## Step 3: Install Required Custom Nodes

Connect via Web Terminal:

```bash
cd /workspace/ComfyUI/custom_nodes

# VideoHelperSuite - Required for video export (VHS_VideoCombine node)
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git

# Install dependencies
cd ComfyUI-VideoHelperSuite
pip install -r requirements.txt

# Restart ComfyUI (or restart the pod)
```

**Alternative**: Some ComfyUI templates include Manager. Use ComfyUI Manager to install:
- `ComfyUI-VideoHelperSuite`

## Step 4: Verify Setup

1. Open ComfyUI web interface (click "Connect" → HTTP Port 8188)
2. Load a simple workflow to test SDXL is working
3. Verify these model files exist:
   - `/workspace/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors`
   - `/workspace/ComfyUI/models/checkpoints/svd_xt_1_1.safetensors`
   - `/workspace/ComfyUI/models/loras/` (empty, will be populated by training)

## Step 5: Get Connection Details

From RunPod Console, get your pod's connection info:

### For Direct Connection
- **ComfyUI URL**: `https://{POD_ID}-8188.proxy.runpod.net`

### For API Access
- **RunPod API Key**: Get from [RunPod Settings → API Keys](https://www.runpod.io/console/user/settings)
- **Pod ID**: Visible in the console (e.g., `abc123xyz`)

## Step 6: Configure Your API

Update your `.env` file:

```bash
# RunPod Configuration
RUNPOD_API_KEY=your_runpod_api_key_here
RUNPOD_POD_IDS=pod_id_1,pod_id_2  # Comma-separated for multiple pods

# ComfyUI (fallback if RunPod discovery fails)
COMFYUI_URL=https://{POD_ID}-8188.proxy.runpod.net

# LoRA Configuration
LORA_OUTPUT_DIR=/workspace/ComfyUI/models/loras
```

## Cost Estimation

With $25 RunPod credit:

| GPU | Cost/hr | Runtime |
|-----|---------|---------|
| RTX 4090 | $0.44 | ~56 hours |
| RTX A5000 | $0.39 | ~64 hours |
| RTX 3090 | $0.31 | ~80 hours |

**Tips to save credits:**
- Stop pod when not in use
- Use **Spot** instances for non-critical work (cheaper but can be interrupted)
- Start with smaller GPU, scale up if needed

## Directory Structure on Pod

```
/workspace/
└── ComfyUI/
    ├── models/
    │   ├── checkpoints/
    │   │   ├── sd_xl_base_1.0.safetensors
    │   │   └── svd_xt_1_1.safetensors
    │   ├── loras/
    │   │   └── {character_loras_will_be_here}.safetensors
    │   ├── clip/
    │   └── vae/
    ├── input/           # Uploaded images for processing
    ├── output/          # Generated images/videos
    └── custom_nodes/
        └── ComfyUI-VideoHelperSuite/
```

## Troubleshooting

### "Model not found" errors
- Verify model files are in correct directories
- Check file names match exactly (case-sensitive)
- Restart ComfyUI after adding models

### ComfyUI not responding
- Check pod status in RunPod console
- Verify port 8188 is exposed
- Check pod logs for errors

### Out of VRAM
- Reduce batch size to 1
- Use smaller resolution (768x768 instead of 1024x1024)
- Close other workflows before running

### LoRA not loading
- Verify `.safetensors` file is in `/workspace/ComfyUI/models/loras/`
- Check LoRA file isn't corrupted (should be several MB)
- Restart ComfyUI after adding new LoRAs

## Next Steps

After setup is complete:

1. Test the API connection:
   ```bash
   curl https://{POD_ID}-8188.proxy.runpod.net/system_stats
   ```

2. Create your first character by uploading training images via the API

3. Generate images with your trained LoRA

4. Generate videos from your character images
