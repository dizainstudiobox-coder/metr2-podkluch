#!/usr/bin/env python3
"""Генератор визуализаций для каталога МЕТР² ПОД КЛЮЧ через OpenAI gpt-image-1.

Авто-поиск OPENAI_API_KEY в:
  1. $OPENAI_API_KEY env
  2. .env-файлах любых проектов под /opt/projects/  (включая /code/.env)
  3. /etc/systemd/system/*.service (Environment= и EnvironmentFile=)
"""
import base64
import json
import os
import re
import sys
from glob import glob
from pathlib import Path


def _extract_key_from_text(text: str) -> str | None:
    # OPENAI_API_KEY=xxx, OPENAI_API_KEY = "xxx", export OPENAI_API_KEY=xxx
    m = re.search(r'OPENAI_API_KEY\s*=\s*["\']?([A-Za-z0-9_\-]+)["\']?', text)
    return m.group(1) if m else None


def find_api_key():
    # 1. ENV
    if k := os.getenv("OPENAI_API_KEY"):
        return k, "env"
    # 2. .env-файлы во всех проектах
    candidates = []
    candidates.extend(glob("/opt/projects/*/.env"))
    candidates.extend(glob("/opt/projects/*/code/.env"))
    candidates.extend(glob("/opt/projects/*/*/.env"))
    candidates.extend(glob("/root/.env"))
    for path in candidates:
        try:
            text = Path(path).read_text(errors="ignore")
            if key := _extract_key_from_text(text):
                return key, path
        except Exception:
            continue
    # 3. systemd unit-файлы
    for unit in glob("/etc/systemd/system/*.service"):
        try:
            text = Path(unit).read_text(errors="ignore")
        except Exception:
            continue
        # Environment="OPENAI_API_KEY=..."
        if key := _extract_key_from_text(text):
            return key, unit
        # EnvironmentFile=/path/to/file — рекурсивно
        for m in re.finditer(r"EnvironmentFile=-?(\S+)", text):
            ef = m.group(1)
            try:
                if key := _extract_key_from_text(Path(ef).read_text(errors="ignore")):
                    return key, ef
            except Exception:
                continue
    return None, None


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

    api_key, source = find_api_key()
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found. Searched:", file=sys.stderr)
        print("  - $OPENAI_API_KEY env", file=sys.stderr)
        print("  - /opt/projects/*/.env", file=sys.stderr)
        print("  - /opt/projects/*/code/.env", file=sys.stderr)
        print("  - /etc/systemd/system/*.service (Environment= and EnvironmentFile=)", file=sys.stderr)
        sys.exit(1)
    print(f"Found OPENAI_API_KEY in: {source}")

    client = OpenAI(api_key=api_key)
    projects = json.loads(projects_json.read_text(encoding="utf-8"))
    print(f"Loaded {len(projects)} projects")
    print(f"Output: {images_dir}")

    for p in projects:
        out = images_dir / p["image"]
        if out.exists() and out.stat().st_size > 10000:
            print(f"  SKIP {p['id']} (exists, {out.stat().st_size//1024} KB)")
            continue
        prompt = p.get("prompt") or f"Modern {p['style']} interior, photorealistic premium quality"
        print(f"  GEN  {p['id']}")
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
