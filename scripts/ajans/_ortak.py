"""Ajans betikleri icin ortak yardimcilar (yalnizca stdlib).

Kurallar:
  * Kimlik bilgileri .credentials/.env (KEY=VALUE) ya da ortam degiskeninden okunur; ASLA yazdirilmaz.
  * HTTP: urllib + kisa yeniden deneme; hata mesajlarinda token maskelenir.
  * Cikti: --json ile ham JSON, --out ile dosyaya (md/json) yazim; varsayilan kisa Markdown.
  * Betikler proje kopyasinda <root>/.claude/scripts/ajans/ altinda durur; config'i oradan bulur.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
UA = "kod-fabrikasi-ajans/3.1 (+site denetimi; kullanici tarafindan calistirilir)"
_SECRET_RE = re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}|([A-Za-z0-9_\-]{32,})")


def die(msg, code=1):
    print(f"[ajans] HATA: {mask(str(msg))}", file=sys.stderr)
    sys.exit(code)


def log(msg):
    print(f"[ajans] {mask(str(msg))}", file=sys.stderr)


def mask(s):
    """Token benzeri degerleri gizler (hata ciktisinda sir sizmasin)."""
    s = re.sub(r"(Bearer\s+)\S+", r"\1***", s)
    s = re.sub(r"([?&](?:key|token|api_key|access_token)=)[^&\s\"']+", r"\1***", s, flags=re.I)
    return s


_SSL_CTX = None


def ssl_context():
    """Windows'ta OpenSSL sistem deposundan eksik kok yukleyebilir; certifi kuruluysa onun paketini de ekler.
    Dogrulama hicbir zaman kapatilmaz."""
    global _SSL_CTX
    if _SSL_CTX is None:
        import ssl
        ctx = ssl.create_default_context()
        try:
            import certifi  # type: ignore
            ctx.load_verify_locations(certifi.where())
        except Exception:
            pass
        _SSL_CTX = ctx
    return _SSL_CTX


def project_root():
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).is_dir():
        return Path(env).resolve()
    # <root>/.claude/scripts/ajans/_ortak.py
    if HERE.parent.name == "scripts" and HERE.parent.parent.name == ".claude":
        return HERE.parent.parent.parent
    return Path.cwd().resolve()


def load_kf_config():
    p = project_root() / ".claude" / "kod-fabrikasi.config.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def agency_cfg(cfg=None):
    cfg = cfg if cfg is not None else load_kf_config()
    return cfg.get("agency") or {}


def credentials_dir(cfg=None):
    a = agency_cfg(cfg)
    return project_root() / (a.get("credentials_dir") or ".credentials")


def load_env():
    """.credentials/.env dosyasini ortam degiskenlerine yukler (mevcut olanlari ezmez)."""
    p = credentials_dir() / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def need(key, hint=""):
    load_env()
    v = os.environ.get(key, "").strip()
    if not v:
        die(f"{key} tanimli degil. {hint or ''} (.credentials/.env icine yaz: {key}=...)".strip())
    return v


def optional(key, default=""):
    load_env()
    return os.environ.get(key, default).strip()


def client_cfg(slug, cfg=None):
    """config agency.clients icinden musteri kaydi."""
    if not slug:
        return {}
    for c in agency_cfg(cfg).get("clients", []):
        if c.get("slug") == slug:
            return c
    die(f"musteri bulunamadi: {slug} (kf.py client list)")


def client_dir(slug, cfg=None):
    a = agency_cfg(cfg)
    return project_root() / (a.get("clients_dir") or "clients") / slug


# ---------------------------------------------------------------- HTTP
def http(method, url, headers=None, data=None, timeout=30, retries=2, json_body=True, raw=False):
    """Basit HTTP; (status, body) dondurur. body JSON ise dict/list, degilse str (raw=True: bytes)."""
    hdrs = {"User-Agent": UA, "Accept": "application/json, text/html;q=0.9, */*;q=0.8"}
    hdrs.update(headers or {})
    body = None
    if data is not None:
        if json_body:
            body = json.dumps(data).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        else:
            body = data if isinstance(data, bytes) else str(data).encode("utf-8")
    last = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as r:
                content = r.read()
                status = r.status
                ctype = r.headers.get("Content-Type", "")
                final = r.geturl()
                hd = dict(r.headers)
        except urllib.error.HTTPError as e:
            content = e.read()
            status = e.code
            ctype = e.headers.get("Content-Type", "") if e.headers else ""
            final = url
            hd = dict(e.headers) if e.headers else {}
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            msg = mask(str(e))
            if "CERTIFICATE_VERIFY_FAILED" in msg:
                msg += " | kok sertifika eksik: `pip install certifi` (betikler certifi'yi otomatik kullanir)"
            return 0, {"error": msg, "url": url}
        if status in (429, 502, 503, 504) and attempt < retries:
            time.sleep(2.0 * (attempt + 1))
            continue
        if raw:
            return status, {"bytes": content, "headers": hd, "final_url": final, "content_type": ctype}
        text = content.decode("utf-8", errors="replace")
        if "json" in ctype or text[:1] in "{[":
            try:
                return status, json.loads(text)
            except json.JSONDecodeError:
                pass
        return status, text
    return 0, {"error": mask(str(last)), "url": url}


# ---------------------------------------------------------------- cikti
def add_common_args(ap: argparse.ArgumentParser):
    ap.add_argument("--client", help="config agency.clients slug'i (domain/zone/site degerlerini oradan alir)")
    ap.add_argument("--json", action="store_true", help="ham JSON cikti")
    ap.add_argument("--out", help="ciktiyi dosyaya yaz (.md ya da .json); stdout'a kisa ozet basilir")
    return ap


def md_table(rows, headers):
    if not rows:
        return "_(kayit yok)_"
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        lines.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in r) + " |")
    return "\n".join(lines)


def emit(result, args, markdown):
    """result: dict (JSON icin) · markdown: str (insan icin). --out uzantisina gore yazar."""
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix.lower() == ".json":
            p.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        else:
            p.write_text(markdown.rstrip() + "\n", encoding="utf-8", newline="\n")
        log(f"yazildi: {p}")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(markdown.rstrip())


def flag(ok, warn=False):
    return "✅" if ok else ("⚠️" if warn else "❌")


def pct(a, b):
    return f"{(a / b * 100):.1f}%" if b else "-"


def delta(cur, prev, digits=1):
    if prev in (None, 0) or cur is None:
        return "-"
    d = (cur - prev) / prev * 100
    return f"{d:+.{digits}f}%"


def fmt_num(n):
    if n is None:
        return "-"
    if isinstance(n, float):
        return f"{n:,.2f}"
    return f"{n:,}"


def fmt_bytes(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def days_range(days, end_offset=0):
    """(baslangic, bitis) ISO tarih; Google API'leri 2-3 gun gecikmeli, end_offset ile kaydir."""
    import datetime as dt
    end = dt.date.today() - dt.timedelta(days=end_offset)
    start = end - dt.timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def append_log(path: Path, line):
    path.parent.mkdir(parents=True, exist_ok=True)
    import datetime as dt
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    with path.open("a", encoding="utf-8") as f:
        f.write(f"- {stamp} {line}\n")
