#!/usr/bin/env python3
"""
Image Creator - OpenRouter API Image Generation Script

Supports two modes:
  - text2img: Generate image from text prompt via /images/generations
  - img2img:  Generate image from text prompt + reference image via /chat/completions

Usage:
  python3 generate.py --mode text2img --prompt "..." --size "1024x1792" --output out.png
  python3 generate.py --mode img2img  --prompt "..." --input-image ref.jpg --size "1024x1792" --output out.png
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error
import ssl

# --- Configuration ---
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "openai/gpt-5.4-image-2"
TIMEOUT = 180


def get_api_key():
    """Get API key from env var or stored file."""
    # 1. Environment variable
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key

    # 2. Stored file
    key_file = os.path.expanduser("~/.workbuddy/skills/image-creator/.api_key")
    if os.path.exists(key_file):
        with open(key_file, "r") as f:
            key = f.read().strip()
        if key:
            return key

    print("ERROR: No API key found. Set OPENROUTER_API_KEY env var or store in ~/.workbuddy/skills/image-creator/.api_key", file=sys.stderr)
    sys.exit(1)


def save_api_key(key):
    """Save API key to file for future use."""
    key_file = os.path.expanduser("~/.workbuddy/skills/image-creator/.api_key")
    os.makedirs(os.path.dirname(key_file), exist_ok=True)
    with open(key_file, "w") as f:
        f.write(key.strip())


def image_to_base64(image_path):
    """Convert a local image file to base64 data URI."""
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    mime = mime_map.get(ext, "image/jpeg")
    return f"data:{mime};base64,{data}"


def ensure_output_dir(output_path):
    """Ensure the output directory exists."""
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)


def download_and_save_image(url_or_b64, output_path):
    """Download image from URL or decode base64 and save to file."""
    ensure_output_dir(output_path)

    if url_or_b64.startswith("data:"):
        # Base64 data URI
        b64_data = url_or_b64.split(",", 1)[1]
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(b64_data))
        return output_path
    else:
        # HTTP URL
        ctx = ssl.create_default_context()
        urllib.request.urlretrieve(url_or_b64, output_path)
        return output_path


def _extract_image_from_chat_response(message, output_path):
    """Extract image from chat/completions response message.
    Image may be in: message.images (OpenRouter native), message.content (list or string).
    Returns True if saved successfully.
    """
    ensure_output_dir(output_path)

    # Case 1: OpenRouter returns images in dedicated 'images' field
    images = message.get("images", [])
    if images:
        for img in images:
            img_url = img.get("image_url", {}).get("url", "")
            if img_url.startswith("data:"):
                b64_data = img_url.split(",", 1)[1]
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(b64_data))
                return True
            elif img_url:
                download_and_save_image(img_url, output_path)
                return True

    content = message.get("content", "")

    # Case 2: content is a list of parts (structured multimodal)
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                img_url = part["image_url"]["url"]
                download_and_save_image(img_url, output_path)
                return True

    # Case 3: content is a string with markdown image link or data URI
    if isinstance(content, str):
        import re
        md_urls = re.findall(r'!\[.*?\]\((https?://\S+)\)', content)
        bare_urls = re.findall(r'(https?://\S+\.(?:png|jpg|jpeg|webp|gif))', content)
        all_urls = md_urls + bare_urls

        if all_urls:
            download_and_save_image(all_urls[0], output_path)
            return True

        b64_matches = re.findall(r'data:image/[^;]+;base64,[A-Za-z0-9+/=]{100,}', content)
        if b64_matches:
            download_and_save_image(b64_matches[0], output_path)
            return True

    return False


def text2img(api_key, prompt, size, output_path):
    """Generate image from text prompt.
    Tries /images/generations first, falls back to /chat/completions.
    """
    # Try /images/generations endpoint first
    try:
        url = f"{BASE_URL}/images/generations"
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "n": 1,
            "size": size,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        # Parse standard images/generations response
        if "data" in result and result["data"]:
            image_data = result["data"][0]
            image_url = image_data.get("url", "")
            b64_json = image_data.get("b64_json", "")
            if image_url:
                download_and_save_image(image_url, output_path)
                print(f"Image saved to: {output_path}")
                return output_path
            elif b64_json:
                data_uri = f"data:image/png;base64,{b64_json}"
                download_and_save_image(data_uri, output_path)
                print(f"Image saved to: {output_path}")
                return output_path
        elif "error" in result:
            print(f"/images/generations error: {result['error']}", file=sys.stderr)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"/images/generations returned {e.code}, falling back to /chat/completions...", file=sys.stderr)
    except Exception as e:
        print(f"/images/generations failed: {e}, falling back to /chat/completions...", file=sys.stderr)

    # Fallback: use /chat/completions endpoint (works for both text2img and img2img models)
    print("Using /chat/completions fallback for text2img generation...")
    url = f"{BASE_URL}/chat/completions"
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"Generate an image: {prompt}",
            }
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"API Error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network Error: {e.reason}", file=sys.stderr)
        sys.exit(1)

    if "choices" not in result or not result["choices"]:
        print(f"Unexpected response: {json.dumps(result, indent=2)[:500]}", file=sys.stderr)
        sys.exit(1)

    message = result["choices"][0].get("message", {})

    if _extract_image_from_chat_response(message, output_path):
        print(f"Image saved to: {output_path}")
        return output_path
    else:
        print("No image found in response.", file=sys.stderr)
        content = message.get("content") or "(empty)"
        print(f"Response content preview: {str(content)[:500]}", file=sys.stderr)
        sys.exit(1)


def img2img(api_key, prompt, input_image_path, size, output_path):
    """Generate image from text prompt + reference image using /chat/completions endpoint."""
    url = f"{BASE_URL}/chat/completions"

    # Convert input image to base64
    image_data_uri = image_to_base64(input_image_path)

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_uri},
                    },
                ],
            }
        ],
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"API Error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network Error: {e.reason}", file=sys.stderr)
        sys.exit(1)

    # Parse response - image may be in different formats
    if "choices" not in result or not result["choices"]:
        print(f"Unexpected response: {json.dumps(result, indent=2)[:500]}", file=sys.stderr)
        sys.exit(1)

    message = result["choices"][0].get("message", {})

    if _extract_image_from_chat_response(message, output_path):
        print(f"Image saved to: {output_path}")
        return output_path
    else:
        print("No image found in response.", file=sys.stderr)
        content = message.get("content") or "(empty)"
        print(f"Response content preview: {str(content)[:500]}", file=sys.stderr)
        sys.exit(1)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Image Creator - OpenRouter API Image Generation")
    parser.add_argument("--mode", choices=["text2img", "img2img"], required=True, help="Generation mode")
    parser.add_argument("--prompt", required=True, help="Text prompt for image generation")
    parser.add_argument("--input-image", help="Path to reference image (required for img2img mode)")
    parser.add_argument("--size", default="1024x1792", help="Image size, e.g. 1024x1792 (default: 1024x1792)")
    parser.add_argument("--output", default="/tmp/poster-output.png", help="Output file path (default: /tmp/poster-output.png)")
    parser.add_argument("--api-key", help="OpenRouter API key (overrides env var and stored key)")
    parser.add_argument("--save-key", help="Save the provided API key for future use", action="store_true")

    args = parser.parse_args()

    # Validate img2img mode
    if args.mode == "img2img" and not args.input_image:
        parser.error("--input-image is required for img2img mode")

    if args.mode == "img2img" and not os.path.exists(args.input_image):
        print(f"ERROR: Input image not found: {args.input_image}", file=sys.stderr)
        sys.exit(1)

    # Get API key
    if args.api_key:
        api_key = args.api_key
        if args.save_key:
            save_api_key(api_key)
            print(f"API key saved to ~/.workbuddy/skills/image-creator/.api_key")
    else:
        api_key = get_api_key()

    # Generate
    if args.mode == "text2img":
        text2img(api_key, args.prompt, args.size, args.output)
    else:
        img2img(api_key, args.prompt, args.input_image, args.size, args.output)


if __name__ == "__main__":
    main()
