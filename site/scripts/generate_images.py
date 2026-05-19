#!/usr/bin/env python3
"""Генератор визуализаций для карусели МЕТР² ПОД КЛЮЧ.

Поддерживает массив visualizations внутри проекта (новая структура).
Использует PROXYAPI_KEY или OPENAI_API_KEY.
"""
import base64
import json
import os
import re
import sys
from glob import glob
from pathlib import Path

KEY_PROVIDERS = [
    ("PROXYAPI_KEY", "https://api.proxyapi.ru/openai/v1"),
    ("OPENAI_API_KEY", None),
]


def _extract(text, var):
    m = re.search(
        rf'^\s*(?:export\s+)?{re.escape(var)}\s*=\s*["\']?([A-Za-z0-9_\-\.]+)["\']?',
        text, re.MULTILINE,
    )
    return m.group(1) if m else None


def find_api_key():
    for var, base in KEY_PROVIDERS:
        if k := os.getenv(var):
            return k, base, f"env:{var}"
    paths = (glob("/opt/projects/*/.env") + glob("/opt/projects/*/code/.env")
             + glob("/opt/projects/*/*/.env") + glob("/root/.env"))
    for p in paths:
        try:
            text = Path(p).read_text(errors="ignore")
        except Exception:
            continue
        for var, base in KEY_PROVIDERS:
            if k := _extract(text, var):
                return k, base, f"{p}:{var}"
    for unit in glob("/etc/systemd/system/*.service"):
        try:
            text = Path(unit).read_text(errors="ignore")
        except Exception:
            continue
        for var, base in KEY_PROVIDERS:
            if k := _extract(text, var):
                return k, base, f"{unit}:{var}"
        for m in re.finditer(r"EnvironmentFile=-?(\S+)", text):
            try:
                ef_text = Path(m.group(1)).read_text(errors="ignore")
            except Exception:
                continue
            for var, base in KEY_PROVIDERS:
                if k := _extract(ef_text, var):
                    return k, base, f"{m.group(1)}:{var}"
    return None, None, None


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

    api_key, base_url, source = find_api_key()
    if not api_key:
        print("ERROR: API key not found.", file=sys.stderr)
        sys.exit(1)
    print(f"API key from: {source}")
    print(f"Base URL: {base_url or 'default OpenAI'}")

    client = OpenAI(api_key=api_key, base_url=base_url)
    projects = json.loads(projects_json.read_text(encoding="utf-8"))
    print(f"Loaded {len(projects)} projects")

    total_imgs = 0
    for p in projects:
        if "images" not in p:
            continue
        for img in p["images"]:
            total_imgs += 1
            out = images_dir / img["file"]
            if out.exists() and out.stat().st_size > 10000:
                print(f"  SKIP {img['file']} (exists)")
                continue
            prompt = img["prompt"]
            print(f"  GEN  {img['file']}")
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

    print(f"\nDone. Generated/skipped {total_imgs} images in {images_dir}")


if __name__ == "__main__":
    main()
