"""SessionStart hook: proje hafizasini oturum baglamina enjekte eder (Kod Fabrikasi v3).

stdout'a yazilan metin Claude'un baglamina eklenir. Yeni oturum, /resume, /clear ve
baglam sikistirmasi (compact) sonrasinda calisir. Kaynaklar config'teki `phase_files`
yollarindan okunur: PROGRESS (Durum + Siradaki adim + son gunluk), OPEN_QUESTIONS
(acik soru basliklari), DECISIONS (son ADR), ROADMAP (aktif faz) ve git durumu.

Hata olsa bile oturumu bozmamak icin HER ZAMAN 0 ile cikar. Gizli bilgi okumaz.
Kurulum: .claude/hooks/faz_hafiza.py  (kf.py init kopyalar)
"""
import json
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
CONFIG_PATH = os.path.join(ROOT, ".claude", "kod-fabrikasi.config.json")

DEFAULT_FILES = {
    "roadmap": ".claude/archives/ROADMAP.md",
    "progress": ".claude/archives/PROGRESS.md",
    "decisions": ".claude/decisions/DECISIONS.md",
    "open_questions": ".claude/decisions/OPEN_QUESTIONS.md",
}


def load_phase_files():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        files = dict(DEFAULT_FILES)
        files.update(cfg.get("phase_files", {}))
        return files
    except Exception:
        return DEFAULT_FILES


def oku(rel):
    if not rel:
        return ""
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def bolum(metin, baslik, max_satir):
    """'## <baslik>' ile baslayan bolumu bir sonraki '## ' basligina kadar dondurur."""
    m = re.search(rf"^## {re.escape(baslik)}\s*$(.*?)(?=^## |\Z)", metin, re.M | re.S)
    if not m:
        return ""
    satirlar = [s for s in m.group(1).strip().splitlines() if s.strip()]
    kesik = len(satirlar) > max_satir
    return "\n".join(satirlar[:max_satir]) + ("\n...(devami dosyada)" if kesik else "")


def git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=5)
        return r.stdout.strip()
    except Exception:
        return ""


def main():
    files = load_phase_files()
    out = ["# Proje hafizasi (otomatik yuklendi: .claude/hooks/faz_hafiza.py)"]

    progress = oku(files.get("progress"))
    if progress:
        durum = bolum(progress, "Durum", 20)
        if durum:
            out.append(f"## Faz durumu ({os.path.basename(files['progress'])})\n{durum}")
        gunluk = bolum(progress, "Günlük", 10_000) or bolum(progress, "Gunluk", 10_000)
        gunler = sorted(set(re.findall(r"^(?:###|-)\s*(\d{4}-\d{2}-\d{2})", gunluk, re.M)))
        if gunler:
            son = [s for s in gunluk.splitlines() if s.startswith(f"- {gunler[-1]}")][-3:]
            out.append(f"Son gunluk kaydi: {gunler[-1]}" + ("\n" + "\n".join(s[:400] for s in son) if son else ""))
        sirada = bolum(progress, "Sıradaki adım", 15) or bolum(progress, "Siradaki adim", 15)
        if sirada:
            out.append("## Siradaki adim\n" + sirada)
    else:
        roadmap = oku(files.get("roadmap"))
        aktif = re.findall(r"^.*(?:🟡|Aktif|\[ \]).*$", roadmap, re.M)[:3]
        if aktif:
            out.append("## Roadmap (PROGRESS.md yok; aktif/acik ilk maddeler)\n" + "\n".join(a[:200] for a in aktif))

    acik = re.findall(r"^## (OPEN-\d+: .+)$", oku(files.get("open_questions")), re.M)
    if acik:
        out.append("## Acik sorular\n" + "\n".join("- " + a for a in acik[:10]))

    adr = re.findall(r"^## (ADR-\d+: .+)$", oku(files.get("decisions")), re.M)
    if adr:
        out.append(f"Son karar: {adr[-1]} (toplam {len(adr)} ADR)")

    log = git("log", "--oneline", "-5")
    if log:
        degisen = git("status", "--short")
        n = len(degisen.splitlines()) if degisen else 0
        out.append("## Git\n" + log + f"\nCommit edilmemis degisiklik: {n} dosya")

    out.append(
        "Kural: Yarim kalmis bir adim varsa kullaniciya nerede kalindigini kisaca hatirlat. "
        "Faz akisi: baglam -> plan -> ONAY -> gelistirici -> tester -> reviewer -> faz-arsivcisi -> commit (kullanici isterse). "
        "Planlama belgelerini yalnizca faz-arsivcisi gunceller."
    )
    print("\n\n".join(out))


try:
    main()
except Exception as e:  # hook asla oturumu bozmasin
    print(f"(faz_hafiza hook hatasi: {e})")
sys.exit(0)
