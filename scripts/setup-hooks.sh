#!/bin/bash
# Kod Fabrikasi — setup-hooks.sh (config-driven, framework-aware)
#
# Proje root'unda çalışır. Config'ten python_bin, graphify_bin ve framework okur,
# uygun pre-commit (test) ve post-commit (graphify + bundle) hook'larını üretir.
set -euo pipefail

CONFIG=".claude/kod-fabrikasi.config.json"

if [ ! -d ".git" ]; then
    echo "❌ Git reposu yok. Once: git init"
    exit 1
fi

if [ ! -f "$CONFIG" ]; then
    echo "❌ $CONFIG bulunamadi. Once: bash ~/.claude/skills/kod-fabrikasi/scripts/init.sh"
    exit 1
fi

# Config'ten değerleri çek (PATH'teki python3'le, hook üretiminde gerekli)
PYTHON_BIN=$(python3 -c "import json; print(json.load(open('$CONFIG'))['python_bin'])")
GRAPHIFY_BIN=$(python3 -c "import json; print(json.load(open('$CONFIG'))['graphify_bin'])")
FRAMEWORK=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('framework', 'none'))")

if [ -z "$PYTHON_BIN" ] || [ -z "$GRAPHIFY_BIN" ]; then
    echo "❌ Config'te python_bin veya graphify_bin eksik."
    exit 1
fi

HOOK_DIR=".git/hooks"

# --- Framework'e göre pre-commit komutu seç ---
case "$FRAMEWORK" in
    flutter)
        PRE_COMMIT_BODY='echo "🔄 [PRE-COMMIT] Flutter analyze + test suite..."
ANALYZE_OUT=$(flutter analyze lib/ test/ 2>&1)
ERROR_LINES=$(echo "$ANALYZE_OUT" | grep "error •" || true)
if [ -n "$ERROR_LINES" ]; then
    echo "$ERROR_LINES"
    ERROR_COUNT=$(echo "$ERROR_LINES" | wc -l | tr -d " ")
    echo "❌ flutter analyze: $ERROR_COUNT error. Commit iptal."
    exit 1
fi
echo "$ANALYZE_OUT" | tail -1

TEST_OUT=$(flutter test 2>&1)
TEST_RC=$?
echo "$TEST_OUT" | tail -3
if [ $TEST_RC -ne 0 ]; then
    echo "❌ flutter test basarisiz. Commit iptal."
    exit 1
fi'
        ;;
    go)
        PRE_COMMIT_BODY='echo "🔄 [PRE-COMMIT] go test..."
go test ./... -v || { echo "❌ go test basarisiz. Commit iptal."; exit 1; }'
        ;;
    php-laravel)
        PRE_COMMIT_BODY='echo "🔄 [PRE-COMMIT] php artisan test..."
php artisan test || { echo "❌ Testler basarisiz. Commit iptal."; exit 1; }'
        ;;
    python)
        PRE_COMMIT_BODY='echo "🔄 [PRE-COMMIT] pytest..."
pytest || { echo "❌ pytest basarisiz. Commit iptal."; exit 1; }'
        ;;
    node)
        PRE_COMMIT_BODY='echo "🔄 [PRE-COMMIT] npm test..."
npm test || { echo "❌ npm test basarisiz. Commit iptal."; exit 1; }'
        ;;
    none|*)
        PRE_COMMIT_BODY='echo "ℹ️  [PRE-COMMIT] Test komutu tanimli degil (framework=none). Atlanir."'
        ;;
esac

# --- PRE-COMMIT yaz ---
cat > "$HOOK_DIR/pre-commit" <<EOF
#!/bin/bash
$PRE_COMMIT_BODY

echo "✅ [PRE-COMMIT] Tamam."
exit 0
EOF

# --- POST-COMMIT yaz (graphify + bundle) ---
cat > "$HOOK_DIR/post-commit" <<EOF
#!/bin/bash
echo "🚀 [POST-COMMIT] Otomasyon basliyor..."

echo "🗺️ [1/2] Graphify haritasi guncelleniyor..."
GRAPHIFY_VIZ_NODE_LIMIT=15000 $GRAPHIFY_BIN update . 2>&1 | tail -5

echo "📦 [2/2] Paketleniyor + NotebookLM aynalaniyor..."
$PYTHON_BIN bundle.py 2>&1 | tail -10

echo "✅ Senkronizasyon tamamlandi."
exit 0
EOF

chmod +x "$HOOK_DIR/pre-commit" "$HOOK_DIR/post-commit"

echo "✅ Git hook'lari kuruldu:"
echo "   pre-commit  → framework: $FRAMEWORK"
echo "   post-commit → graphify ($GRAPHIFY_BIN) + bundle.py ($PYTHON_BIN)"
