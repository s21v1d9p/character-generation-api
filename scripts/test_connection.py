#!/usr/bin/env python3
"""
Test script to verify RunPod/ComfyUI connection.
Run this locally after setting up your RunPod pod.

Usage:
    python scripts/test_connection.py
    python scripts/test_connection.py --url https://your-pod-url:8188
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx
from dotenv import load_dotenv


async def test_comfyui_direct(url: str) -> bool:
    """Test direct connection to ComfyUI."""
    print(f"\n[1] Testing direct ComfyUI connection: {url}")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Test system stats endpoint
            response = await client.get(f"{url}/system_stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"    ✓ ComfyUI is running")
                print(f"    ✓ GPU: {stats.get('devices', [{}])[0].get('name', 'Unknown')}")
                print(f"    ✓ VRAM: {stats.get('devices', [{}])[0].get('vram_total', 0) / 1e9:.1f} GB")
                return True
            else:
                print(f"    ✗ Unexpected status: {response.status_code}")
                return False
    except httpx.ConnectError:
        print(f"    ✗ Connection refused - is the pod running?")
        return False
    except httpx.TimeoutException:
        print(f"    ✗ Connection timeout - check URL and network")
        return False
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False


async def test_models(url: str) -> bool:
    """Check if required models are installed."""
    print(f"\n[2] Checking installed models...")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{url}/object_info")
            if response.status_code != 200:
                print(f"    ✗ Could not fetch object info")
                return False

            # Check for required node types
            info = response.json()
            required_nodes = [
                "CheckpointLoaderSimple",
                "KSampler",
                "CLIPTextEncode",
                "LoraLoader",
                "VAEDecode",
                "SaveImage",
            ]

            missing = []
            for node in required_nodes:
                if node in info:
                    print(f"    ✓ {node}")
                else:
                    print(f"    ✗ {node} - MISSING")
                    missing.append(node)

            # Check for video nodes
            if "VHS_VideoCombine" in info:
                print(f"    ✓ VHS_VideoCombine (VideoHelperSuite)")
            else:
                print(f"    ⚠ VHS_VideoCombine - not installed (video gen won't work)")

            return len(missing) == 0

    except Exception as e:
        print(f"    ✗ Error checking models: {e}")
        return False


async def test_runpod_api(api_key: str) -> bool:
    """Test RunPod API connection."""
    print(f"\n[3] Testing RunPod API...")

    if not api_key:
        print(f"    ⚠ RUNPOD_API_KEY not set - skipping")
        return True

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.runpod.io/graphql",
                json={
                    "query": "query { myself { id email pods { id name } } }"
                },
                headers={"Authorization": f"Bearer {api_key}"}
            )

            if response.status_code == 200:
                data = response.json()
                if "data" in data and "myself" in data["data"]:
                    pods = data["data"]["myself"].get("pods", [])
                    print(f"    ✓ RunPod API connected")
                    print(f"    ✓ Found {len(pods)} pod(s)")
                    for pod in pods:
                        print(f"       - {pod['name']} ({pod['id']})")
                    return True
                else:
                    print(f"    ✗ Invalid API response")
                    return False
            else:
                print(f"    ✗ API returned status {response.status_code}")
                return False

    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Test RunPod/ComfyUI connection")
    parser.add_argument("--url", help="ComfyUI URL (overrides .env)")
    args = parser.parse_args()

    # Load environment
    load_dotenv()

    url = args.url or os.getenv("COMFYUI_URL", "http://localhost:8188")
    api_key = os.getenv("RUNPOD_API_KEY", "")

    print("=" * 50)
    print("Character Generation API - Connection Test")
    print("=" * 50)

    # Run tests
    results = []

    results.append(await test_comfyui_direct(url))

    if results[0]:  # Only test models if connection works
        results.append(await test_models(url))

    results.append(await test_runpod_api(api_key))

    # Summary
    print("\n" + "=" * 50)
    if all(results):
        print("✓ All tests passed! Your setup is ready.")
        print("=" * 50)
        print("\nNext steps:")
        print("1. Start your API: uvicorn src.main:app --reload")
        print("2. Create a character: POST /characters")
        print("3. Generate images: POST /generate-image")
        return 0
    else:
        print("✗ Some tests failed. Check the issues above.")
        print("=" * 50)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
