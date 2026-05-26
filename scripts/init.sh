#!/bin/bash
# Kod Fabrikasi — init.sh (interaktif kurulum)
#
# Proje root'unda çalışır. 4 soru sorar, .claude/kod-fabrikasi.config.json üretir,
# bundle.py + Makefile + setup-hooks.sh template'lerini proje root'a kopyalar,
# .gitignore'a gerekli satırları ekler.
#
# Kullanım:
#   bash ~/.claude/skills/kod-fabrikasi/scripts/init.sh           # tam kurulum
#   bash ~/.claude/skills/kod-fabrikasi/scripts/init.sh --repair  # sadece eksikleri tamamla
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$SKILL_DIR/scripts"
CONFIG_PATH=".claude/kod-fabrikasi.config.json"
REPAIR_MODE=false

if [ "${1:-}" = "--repair" ]; then
    REPAIR_MODE=true
fi

echo "🏭 Kod Fabrikasi — Proje Kurulumu"
echo "────────────────────────────────"
echo "Proje: $(pwd)"
echo "Skill: $SKILL_DIR"
echo ""

# ───────────────────────────────────────────────────────
# CONFIG: yoksa yaz, varsa --repair ise koru
# ───────────────────────────────────────────────────────
mkdir -p .claude

if [ -f "$CONFIG_PATH" ] && [ "$REPAIR_MODE" = "true" ]; then
    echo "ℹ️  Mevcut config korunuyor: $CONFIG_PATH"
elif [ -f "$CONFIG_PATH" ] && [ "$REPAIR_MODE" = "false" ]; then
    echo "⚠️  Config zaten var: $CONFIG_PATH"
    read -rp "    Üzerine yaz? (y/N): " overwrite
    if [ "${overwrite:-N}" != "y" ] && [ "${overwrite:-N}" != "Y" ]; then
        echo "   → Mevcut config korunuyor. (--repair ile sadece dosya kopyalamak istersen kullan)"
    else
        rm -f "$CONFIG_PATH"
    fi
fi

if [ ! -f "$CONFIG_PATH" ]; then
    echo ""
    echo "📝 4 soruya cevap ver:"
    echo ""

    # 1) Drive klasörü
    DEFAULT_DRIVE="$HOME/Library/CloudStorage/GoogleDrive-/Drive'ım/DEV_PROJELERI/$(basename "$(pwd)")"
    echo "1️⃣  Google Drive senkron klasör yolu (bundle.py buraya yazacak):"
    echo "   Örnek: $DEFAULT_DRIVE"
    read -rp "   Yol: " drive_path
    if [ -z "$drive_path" ]; then
        echo "❌ Drive yolu zorunlu. Çıkılıyor."
        exit 1
    fi

    # 2) Notebook ID
    echo ""
    echo "2️⃣  NotebookLM notebook ID'si (UUID format):"
    echo "   Yoksa: notebooklm create \"$(basename "$(pwd)")\" ile oluştur ve dönen ID'yi yapıştır."
    read -rp "   ID: " notebook_id
    if [ -z "$notebook_id" ]; then
        echo "❌ Notebook ID zorunlu. Çıkılıyor."
        exit 1
    fi

    # 3) Python bin
    echo ""
    DEFAULT_PYTHON=$(which python3 2>/dev/null || echo "/usr/bin/python3")
    echo "3️⃣  notebooklm-py paketinin kurulu olduğu Python tam yolu:"
    echo "   ipucu: python3 -c \"import notebooklm; print(__import__('sys').executable)\""
    echo "   Önerilen: $DEFAULT_PYTHON"
    read -rp "   Python: " python_bin
    python_bin="${python_bin:-$DEFAULT_PYTHON}"
    if [ ! -x "$python_bin" ]; then
        echo "⚠️  $python_bin executable değil veya bulunamadı — yine de kayd ediliyor (doğrulamayı kullanıcıya bırakıyoruz)."
    fi

    # 4) Graphify bin
    echo ""
    DEFAULT_GRAPHIFY=$(which graphify 2>/dev/null || echo "$(dirname "$python_bin")/graphify")
    echo "4️⃣  Graphify binary tam yolu:"
    echo "   Önerilen: $DEFAULT_GRAPHIFY"
    read -rp "   Graphify: " graphify_bin
    graphify_bin="${graphify_bin:-$DEFAULT_GRAPHIFY}"

    # 5) Framework
    echo ""
    echo "5️⃣  Projenin framework'ü (pre-commit test komutu seçimi):"
    echo "   1) flutter      → flutter analyze + flutter test"
    echo "   2) go           → go test ./..."
    echo "   3) php-laravel  → php artisan test"
    echo "   4) python       → pytest"
    echo "   5) node         → npm test"
    echo "   6) none         → test komutu yok"
    read -rp "   Seçim (1-6): " fw_choice
    case "${fw_choice:-6}" in
        1) framework="flutter" ;;
        2) framework="go" ;;
        3) framework="php-laravel" ;;
        4) framework="python" ;;
        5) framework="node" ;;
        *) framework="none" ;;
    esac

    # Config dosyasını yaz (assets/kod-fabrikasi.config.example.json'dan türetilmiş)
    cat > "$CONFIG_PATH" <<EOF
{
  "drive_folder_path": "$drive_path",
  "notebook_id": "$notebook_id",
  "python_bin": "$python_bin",
  "graphify_bin": "$graphify_bin",
  "framework": "$framework",
  "sync_to_notebooklm": true,
  "critical_docs": [
    "ROADMAP.md",
    "MEMORY.md",
    "QA_REPORTS.md",
    "NOTEBOOKLM_SUMMARY.md",
    "GRAPHIFY_NOTES.md",
    "FAZ_PROMPT.md",
    ".claude/ROADMAP.md",
    ".claude/MEMORY.md"
  ],
  "sync_dirs": ["reports", "graphify-out"],
  "phase_files": {
    "roadmap": "ROADMAP.md",
    "memory": "MEMORY.md",
    "qa": "QA_REPORTS.md",
    "known_bugs": "KNOWN_BUGS.md"
  },
  "notebooklm_allowed_extensions": [".md", ".txt", ".pdf"],
  "notebooklm_ignore_dirs": ["cache", "__pycache__"],
  "notebooklm_max_file_size_mb": 50,
  "stale_drive_patterns": []
}
EOF
    echo ""
    echo "✅ Config yazıldı: $CONFIG_PATH"
fi

# ───────────────────────────────────────────────────────
# DOSYA KOPYALAMA — bundle.py, Makefile, setup-hooks.sh
# ───────────────────────────────────────────────────────
echo ""
echo "📋 Proje root'una dosyalar kopyalanıyor..."

copy_if_missing() {
    local src="$1"
    local dest="$2"
    if [ -f "$dest" ]; then
        if [ "$REPAIR_MODE" = "true" ]; then
            echo "   ⏭️  $dest zaten var (--repair: korunuyor)"
        else
            read -rp "   ⚠️  $dest zaten var. Üzerine yaz? (y/N): " ow
            if [ "${ow:-N}" = "y" ] || [ "${ow:-N}" = "Y" ]; then
                cp "$src" "$dest"
                echo "      → üzerine yazıldı"
            else
                echo "      → korundu"
            fi
        fi
    else
        cp "$src" "$dest"
        echo "   ✅ $dest"
    fi
}

copy_if_missing "$SCRIPTS_DIR/bundle.py" "bundle.py"
copy_if_missing "$SCRIPTS_DIR/Makefile" "Makefile"
copy_if_missing "$SCRIPTS_DIR/setup-hooks.sh" "setup-hooks.sh"
chmod +x setup-hooks.sh

# ───────────────────────────────────────────────────────
# .gitignore — idempotent
# ───────────────────────────────────────────────────────
echo ""
echo "🚫 .gitignore güncelleniyor..."
touch .gitignore
ensure_gitignore() {
    local pattern="$1"
    if ! grep -qxF "$pattern" .gitignore; then
        echo "$pattern" >> .gitignore
        echo "   ➕ $pattern"
    else
        echo "   ✓  $pattern (mevcut)"
    fi
}
ensure_gitignore "graphify-out/"
ensure_gitignore "__pycache__/"
ensure_gitignore ".claude/settings.local.json"
ensure_gitignore "tum_kodlar.txt"

# ───────────────────────────────────────────────────────
# Klasörler — reports/ olmalı
# ───────────────────────────────────────────────────────
mkdir -p reports
echo "   ✅ reports/ klasörü hazır"

# ───────────────────────────────────────────────────────
# Özet ve sonraki adımlar
# ───────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────"
echo "✅ Kod Fabrikasi kurulumu tamamlandı."
echo "────────────────────────────────"
echo ""
echo "📌 Sonraki adımlar:"
echo ""
if [ ! -d ".git" ]; then
    echo "  1. git init                                    # repo başlat"
    echo "  2. make setup-hooks                             # pre-commit + post-commit kur"
    echo "  3. make bundle                                  # ilk eşitleme"
else
    echo "  1. make setup-hooks                             # pre-commit + post-commit kur"
    echo "  2. make bundle                                  # ilk eşitleme"
fi
echo ""
echo "💡 Faz başlatmak için Claude'a yaz:"
echo "   \"FAZ_PROMPT'u oku ve sıradaki fazı başlat.\""
echo ""
