# Character Generation API

Backend API for AI character image and video generation with LoRA-based character system.

## Features

- **Character Management**: Create, list, and manage AI characters
- **Automated LoRA Training**: Upload ~20 images, get a trained character LoRA
- **Image Generation**: Generate character images with SDXL + LoRA
- **Video Generation**: Generate character videos with Stable Video Diffusion
- **Cloud Storage**: Automatic upload to S3 or Supabase

## Quick Start

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/characters` | GET | List all characters |
| `/characters` | POST | Create character (upload images, triggers training) |
| `/characters/{id}` | GET | Get character details |
| `/characters/{id}` | DELETE | Delete a character |
| `/generate-image` | POST | Generate image with character |
| `/generate-image/{id}` | GET | Get image generation status |
| `/generate-video` | POST | Generate video with character |
| `/generate-video/{id}` | GET | Get video generation status |

## Creating a Character

```bash
curl -X POST http://localhost:8000/characters \
  -F "name=My Character" \
  -F "description=A test character" \
  -F "images=@image1.jpg" \
  -F "images=@image2.jpg" \
  # ... upload 10-20 images
```

## Generating Images

```bash
curl -X POST http://localhost:8000/generate-image \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "uuid-here",
    "prompt": "portrait photo, studio lighting"
  }'
```

## Architecture

See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation.

## Requirements

- Python 3.10+
- PostgreSQL
- Redis (for background tasks)
- ComfyUI with SDXL and SVD models
- RunPod GPU (or equivalent)
