#!/usr/bin/env python3
"""Генератор визуализаций для каталога МЕТР² ПОД КЛЮЧ.

Поддерживает два провайдера:
  * Прямой OpenAI (OPENAI_API_KEY) — api.openai.com
  * ProxyAPI (PROXYAPI_KEY)        — api.proxyapi.ru/openai/v1  (используется в Дзен-проекте)

Авто-поиск ключа в env, .env-файлах /opt/projects/*/, /opt/projects/*/code/, systemd units.
"""
import base64
import json
import os
import re
import sys
from glob import glob
from pathlib import Path

# Имя переменной → base_url
KEY_PROVIDERS = [
    ("PROXYAPI_KEY", "https://api.proxyapi.ru/openai/v1"),
    ("OPENAI_API_KEY", None),  # None = default api.openai.com
]


def _extract_kv_from_text(text: str, var_name: str) -> str | None:
    m = re.search(
        rf'^\s*(?:export\s+)?{re.escape(var_name)}\s*=\s*["\']?([A-Za-z0-9_\-\.]+)["\']?',
        text, re.MULTILINE,
    )
    return m.group(1) if m else None


def find_api_key():
    """Возвращает (key, base_url, source). base_url=None → дефолтный OpenAI."""
    # 1. ENV
    for var, base in KEY_PROVIDERS:
        if k := os.getenv(var):
            return k, base, f"env:{var}"

    # 2. .env-файлы во всех проектах
    candidates = []
    candidates.extend(glob("/opt/projects/*/.env"))
    candidates.extend(glob("/opt/projects/*/code/.env"))
    candidates.extend(glob("/opt/projects/*/*/.env"))
    candidates.extend(glob("/root/.env"))
    for path in candidates:
        try:
            text = Path(path).read_text(errors="ignore")
        except Exception:
            continue
        for var, base in KEY_PROVIDERS:
            if key := _extract_kv_from_text(text, var):
                return key, base, f"{path}:{var}"

    # 3. systemd unit-файлы
    for unit in glob("/etc/systemd/system/*.service"):
        try:
            text = Path(unit).read_text(errors="ignore")
        except Exception:
            continue
        for var, base in KEY_PROVIDERS:
            if key := _extract_kv_from_text(text, var):
                return key, base, f"{unit}:{var}"
        for m in re.finditer(r"EnvironmentFile=-?(\S+)", text):
            try:
                ef_text = Path(m.group(1)).read_text(errors="ignore")
            except Exception:
                continue
            for var, base in KEY_PROVIDERS:
                if key := _extract_kv_from_text(ef_text, var):
                    return key, base, f"{m.group(1)}:{var}"

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
        print("ERROR: API key not found. Searched: env, /opt/projects/**/.env, systemd units.", file=sys.stderr)
        print(f"Looked for vars: {[v for v, _ in KEY_PROVIDERS]}", file=sys.stderr)
        sys.exit(1)
    print(f"Found API key in: {source}")
    if base_url:
        print(f"Using base URL: {base_url}")
    else:
        print("Using default OpenAI base URL")

    client = OpenAI(api_key=api_key, base_url=base_url)
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
