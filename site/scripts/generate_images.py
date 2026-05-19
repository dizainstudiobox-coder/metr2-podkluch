#!/usr/bin/env python3
"""Генератор визуализаций для каталога МЕТР² ПОД КЛЮЧ через OpenAI gpt-image-1."""
import base64
import json
import os
import sys
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    os.system("pip install -q openai")
    from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
PROJECTS_JSON = ROOT / "data" / "projects.json"
IMAGES_DIR = ROOT / "assets" / "projects"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY env var required", file=sys.stderr)
    sys.exit(1)

client = OpenAI(api_key=api_key)
projects = json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
print(f"Loaded {len(projects)} projects")

for p in projects:
    out = IMAGES_DIR / p["image"]
    if out.exists() and out.stat().st_size > 10000:
        print(f"  SKIP {p['id']}")
        continue
    prompt = p.get("prompt") or f"Modern {p['style']} interior, photorealistic"
    print(f"  GEN  {p['id']}: {prompt[:80]}...")
    try:
        resp = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1536x1024",
            quality="medium",
            n=1,
        )
        out.write_bytes(base64.b64decode(resp.data[0].b64_json))
        print(f"        saved ({out.stat().st_size//1024} KB)")
    except Exception as e:
        print(f"        FAIL: {e}", file=sys.stderr)

print(f"Done. {IMAGES_DIR}")
