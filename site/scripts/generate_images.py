#!/usr/bin/env python3
"""Генератор визуализаций для каталога МЕТР² ПОД КЛЮЧ через OpenAI gpt-image-1.

Автоматически находит OPENAI_API_KEY в:
  1. $OPENAI_API_KEY (env)
  2. /opt/projects/blog_dzen/.env  (от Дзен-проекта)
  3. /etc/systemd/system/blog-dzen-draft.service (Environment=)
"""
import base64
import json
import os
import re
import sys
from pathlib import Path


def find_api_key():
    if k := os.getenv("OPENAI_API_KEY"):
        return k
    env_file = Path("/opt/projects/blog_dzen/.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY"):
                return line.split("=", 1)[1].strip().strip("'\"")
    unit = Path("/etc/systemd/system/blog-dzen-draft.service")
    if unit.exists():
        m = re.search(r'Environment=.*OPENAI_API_KEY=([^\s"\']+)', unit.read_text())
        if m:
            return m.group(1)
    return None


def main():
    try:
        from openai import OpenAI
    except ImportError:
        os.system("pip install -q --break-system-packages openai")
        from openai import OpenAI

    root = Path(__file__).resolve().parents[1]
    projects_json = root / "data" / "projects.json"
    images_dir = root / "assets" / "projects"
    images_dir.mkdir(parents=True, exist_ok=True)

    api_key = find_api_key()
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found (checked env, blog_dzen/.env, systemd unit)", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    projects = json.loads(projects_json.read_text(encoding="utf-8"))
    print(f"Loaded {len(projects)} projects from {projects_json}")
    print(f"Output: {images_dir}")

    for p in projects:
        out = images_dir / p["image"]
        if out.exists() and out.stat().st_size > 10000:
            print(f"  SKIP {p['id']} (exists)")
            continue
        prompt = p.get("prompt") or f"Modern {p['style']} interior, photorealistic premium quality"
        print(f"  GEN  {p['id']}")
        print(f"        prompt: {prompt[:100]}...")
        try:
            resp = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="1536x1024",
                quality="medium",
                n=1,
            )
            out.write_bytes(base64.b64decode(resp.data[0].b64_json))
            print(f"        saved {out.name} ({out.stat().st_size//1024} KB)")
        except Exception as e:
            print(f"        FAIL: {e}", file=sys.stderr)

    print(f"\nDone. Images at {images_dir}")


if __name__ == "__main__":
    main()
