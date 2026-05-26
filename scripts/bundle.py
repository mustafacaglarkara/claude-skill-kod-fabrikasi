"""
Kod Fabrikası — bundle.py (config-driven, project-agnostic).

Proje root'unda çalışır. Tüm ayarları `.claude/kod-fabrikasi.config.json`'dan okur.
Hardcoded path / projeye özel değer içermez.

Çalıştırma:
    cd <proje-root>
    <config.python_bin> bundle.py
"""
import json
import os
import sys
import shutil
import asyncio
import tempfile
import fnmatch
from pathlib import Path

# ---- KONFIG OKUMA ----
CONFIG_PATH = Path(".claude/kod-fabrikasi.config.json")

if not CONFIG_PATH.exists():
    print(f"❌ Config bulunamadı: {CONFIG_PATH}", file=sys.stderr)
    print("   ipucu: bash ~/.claude/skills/kod-fabrikasi/scripts/init.sh", file=sys.stderr)
    sys.exit(1)

with CONFIG_PATH.open("r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# Zorunlu alanlar
REQUIRED = ["drive_folder_path", "notebook_id"]
missing = [k for k in REQUIRED if not CONFIG.get(k)]
if missing:
    print(f"❌ Config eksik alan(lar): {missing}", file=sys.stderr)
    sys.exit(1)

DRIVE_FOLDER_PATH = CONFIG["drive_folder_path"]
NOTEBOOK_ID = CONFIG["notebook_id"]
SYNC_TO_NOTEBOOKLM = CONFIG.get("sync_to_notebooklm", True)

# Varsayılanlar (config override edebilir)
ALLOWED_EXTENSIONS = set(CONFIG.get("allowed_extensions", [
    ".go", ".proto", ".sql", ".js", ".ts", ".tsx", ".jsx",
    ".py", ".json", ".md", ".yml", ".yaml", ".html", ".css",
    ".php", ".dart", ".swift", ".kt", ".java", ".rb", ".rs",
]))

IGNORE_DIRS = set(CONFIG.get("ignore_dirs", [
    "node_modules", ".git", ".idea", ".vscode", "vendor",
    ".venv", "venv", "dist", "build", "graphify-out",
    "__pycache__", "storage", "public", "cache", "views",
    "snapshots", ".dart_tool", ".gradle", ".next", "target",
]))

CRITICAL_DOCS = CONFIG.get("critical_docs", [
    "ROADMAP.md", "MEMORY.md", "QA_REPORTS.md",
    "NOTEBOOKLM_SUMMARY.md", "GRAPHIFY_NOTES.md", "FAZ_PROMPT.md",
    ".claude/ROADMAP.md", ".claude/MEMORY.md",
])

SYNC_DIRS = CONFIG.get("sync_dirs", ["reports", "graphify-out"])

# NotebookLM kaynak senkronu — NotebookLM dostu, metin tabanlı
NOTEBOOKLM_ALLOWED_EXTENSIONS = set(CONFIG.get(
    "notebooklm_allowed_extensions", [".md", ".txt", ".pdf"]
))
NOTEBOOKLM_IGNORE_DIRS = set(CONFIG.get(
    "notebooklm_ignore_dirs", ["cache", "__pycache__"]
))
STALE_DRIVE_PATTERNS = CONFIG.get("stale_drive_patterns", [])
NOTEBOOKLM_MAX_FILE_SIZE = CONFIG.get(
    "notebooklm_max_file_size_mb", 50
) * 1024 * 1024


# notebooklm SDK'yı geç yükle (sync_to_notebooklm=False ise import gerekmez)
def _import_notebooklm():
    try:
        from notebooklm import NotebookLMClient  # type: ignore
        return NotebookLMClient
    except ImportError as e:
        print(f"❌ notebooklm-py kurulu değil: {e}", file=sys.stderr)
        print("   ipucu: python3 -m pip install 'notebooklm-py[browser]'", file=sys.stderr)
        sys.exit(1)


def bundle_everything():
    os.makedirs(DRIVE_FOLDER_PATH, exist_ok=True)

    output_file = os.path.join(DRIVE_FOLDER_PATH, "tum_kodlar.txt")

    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.write("# PROJE BEYNI VE KAYNAK KOD DOKUMU\n\n")

        # 1. KISIM: Kritik dökümanlar (NotebookLM bağlamı)
        outfile.write("## Proje Yonetim ve Hafiza Belgeleri\n\n")
        for doc in CRITICAL_DOCS:
            if os.path.exists(doc):
                outfile.write(f"### {doc}\n```markdown\n")
                with open(doc, "r", encoding="utf-8") as f:
                    outfile.write(f.read())
                outfile.write("\n```\n\n---\n\n")

        # 2. KISIM: Klasör yapısı
        outfile.write("## Proje Klasor Yapisi\n```text\n")
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            level = root.replace(".", "").count(os.sep)
            indent = " " * 4 * level
            outfile.write(f"{indent}{os.path.basename(root)}/\n")
            for f in files:
                ext = os.path.splitext(f)[1]
                if (
                    ext in ALLOWED_EXTENSIONS
                    and f not in [os.path.basename(d) for d in CRITICAL_DOCS]
                    and f not in {"package-lock.json", "composer.lock", "pubspec.lock"}
                ):
                    outfile.write(f"{' ' * 4 * (level + 1)}{f}\n")
        outfile.write("```\n\n---\n\n")

        # 3. KISIM: Kaynak kodlar
        outfile.write("## Kaynak Kodlar\n\n")
        critical_basenames = {os.path.basename(d) for d in CRITICAL_DOCS}
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for file in files:
                ext = os.path.splitext(file)[1]
                if (
                    ext in ALLOWED_EXTENSIONS
                    and file not in critical_basenames
                    and file not in {"package-lock.json", "composer.lock", "pubspec.lock"}
                ):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, ".")
                    outfile.write(f"### Dosya: {rel_path}\n")
                    lang = ext.lstrip(".")
                    if lang in ("yml", "yaml"):
                        lang = "yaml"
                    outfile.write(f"```{lang}\n")
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            outfile.write(f.read())
                    except Exception as e:
                        outfile.write(f"// Dosya okunurken hata: {e}")
                    outfile.write("\n```\n\n---\n\n")

    print(f"✅ Kod paketi olusturuldu: {output_file}")

    # Drive'a SYNC_DIRS klasörlerini BİREBİR aynala (rmtree + copytree)
    for sync_dir in SYNC_DIRS:
        if os.path.isdir(sync_dir):
            dest_dir = os.path.join(DRIVE_FOLDER_PATH, sync_dir)
            shutil.rmtree(dest_dir, ignore_errors=True)
            shutil.copytree(sync_dir, dest_dir)
            print(f"✅ '{sync_dir}/' klasoru Drive'a aynalandi.")

    # Kritik dökümanları Drive köküne kopyala
    for doc in CRITICAL_DOCS:
        if os.path.exists(doc):
            dest_name = os.path.basename(doc)
            if doc.startswith(".claude/"):
                dest_name = "CLAUDE_" + dest_name
            shutil.copy(doc, os.path.join(DRIVE_FOLDER_PATH, dest_name))
            print(f"📄 {dest_name} Drive'a kopyalandi.")

    # NotebookLM senkronu
    if SYNC_TO_NOTEBOOKLM:
        cleanup_stale_drive_files()
        asyncio.run(sync_to_notebooklm_async())


def cleanup_stale_drive_files():
    """Config'teki stale_drive_patterns'a uyan eski/artık dosyaları Drive'dan siler."""
    if not STALE_DRIVE_PATTERNS or not os.path.isdir(DRIVE_FOLDER_PATH):
        return
    for name in os.listdir(DRIVE_FOLDER_PATH):
        full = os.path.join(DRIVE_FOLDER_PATH, name)
        if not os.path.isfile(full):
            continue
        if any(fnmatch.fnmatch(name, pat) for pat in STALE_DRIVE_PATTERNS):
            try:
                os.remove(full)
                print(f"🗑️ Eski artik dosya silindi: {name}")
            except OSError as e:
                print(f"⚠️ {name} silinemedi: {e}")


def collect_drive_sources():
    """Drive klasöründeki NotebookLM'e yüklenecek dosyaları toplar.

    Dönen: [(kaynak_basligi, dosya_yolu), ...]
    Kaynak başlığı = klasör köküne göreli yol; alt klasörler '__' ile düzleştirilir
    (NotebookLM kaynakları başlığa göre eşleştirildiği için başlıklar BENZERSİZ olmalı).
    """
    collected = []
    seen_titles = set()
    for root, dirs, files in os.walk(DRIVE_FOLDER_PATH):
        dirs[:] = [
            d for d in dirs
            if d not in NOTEBOOKLM_IGNORE_DIRS and not d.startswith(".")
        ]
        for fname in sorted(files):
            if fname.startswith("."):
                continue
            if any(fnmatch.fnmatch(fname, pat) for pat in STALE_DRIVE_PATTERNS):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in NOTEBOOKLM_ALLOWED_EXTENSIONS:
                continue
            full_path = os.path.join(root, fname)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                continue
            if size == 0:
                continue
            if size > NOTEBOOKLM_MAX_FILE_SIZE:
                print(f"⚠️ {fname} cok buyuk ({size // 1024 // 1024} MB) — atlaniyor.")
                continue
            rel = os.path.relpath(full_path, DRIVE_FOLDER_PATH)
            title = rel.replace(os.sep, "__")
            if title in seen_titles:
                print(f"⚠️ Baslik cakismasi '{title}' — {rel} atlaniyor.")
                continue
            seen_titles.add(title)
            collected.append((title, full_path))
    return collected


async def upload_as_source(client, title, src_path, staging_dir):
    """Dosyayı NotebookLM'e yükler. Başlık dosya adından türediği için,
    hedef başlık dosya adından farklıysa geçici kopya üzerinden yüklenir."""
    if os.path.basename(src_path) == title:
        await client.sources.add_file(NOTEBOOK_ID, src_path, wait=True, wait_timeout=300)
        return
    staged = os.path.join(staging_dir, title)
    shutil.copy(src_path, staged)
    await client.sources.add_file(NOTEBOOK_ID, staged, wait=True, wait_timeout=300)


async def sync_to_notebooklm_async():
    """NotebookLM kaynaklarını DRIVE_FOLDER_PATH ile BİREBİR eşitler."""
    print("🔄 NotebookLM guncelleniyor (Drive klasoru birebir aynalaniyor)...")

    drive_sources = collect_drive_sources()
    if not drive_sources:
        # GÜVENLİK FRENİ — boş klasörde TÜM kaynakları silmeyi önler.
        print("⚠️ Drive klasorunde dosya yok — guvenlik icin NotebookLM'e dokunulmuyor.")
        return
    print(f"📁 {len(drive_sources)} dosya esitlenecek.")

    NotebookLMClient = _import_notebooklm()

    staging_dir = tempfile.mkdtemp(prefix="nblm_stage_")
    try:
        async with await NotebookLMClient.from_storage() as client:
            # Eşitleme öncesi mevcut kaynakların TAM listesi
            # (aynı başlıktan birden fazla olabilir — başlığa göre dict YAPMA).
            old_sources = await client.sources.list(NOTEBOOK_ID)
            desired_titles = {title for title, _ in drive_sources}

            # 1. Klasördeki her dosyayı taze yükle
            #    (yükleme başarısız olursa eski nüsha korunsun diye önce yükle, sonra sil)
            uploaded_ok = set()
            for title, path in drive_sources:
                print(f"📤 '{title}' yukleniyor...")
                try:
                    await upload_as_source(client, title, path, staging_dir)
                    uploaded_ok.add(title)
                    print(f"✅ '{title}' yuklendi.")
                except Exception as e:
                    print(f"❌ '{title}' yuklenemedi: {e}")

            # 2. Birebir ayna: eski kaynakları id bazında temizle
            for s in old_sources:
                if s.title not in desired_titles:
                    reason = "klasorde yok"
                elif s.title in uploaded_ok:
                    reason = "eski nusha"
                else:
                    print(f"⏭️ '{s.title}' eski nushasi korunuyor (yeni yukleme basarisiz).")
                    continue
                print(f"🗑️ '{s.title}' siliniyor ({reason})...")
                try:
                    await client.sources.delete(NOTEBOOK_ID, s.id)
                except Exception as e:
                    print(f"⚠️ '{s.title}' silinemedi: {e}")
    except Exception as e:
        print(f"❌ NotebookLM senkronu genel hata: {e}")
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


if __name__ == "__main__":
    bundle_everything()
