.PHONY: bundle graphify-update end-phase setup-hooks check-config

# Config'ten python_bin'i oku; yoksa PATH'teki python3'e düş
CONFIG := .claude/kod-fabrikasi.config.json
PYTHON_BIN := $(shell test -f $(CONFIG) && python3 -c "import json; print(json.load(open('$(CONFIG)')).get('python_bin', 'python3'))" 2>/dev/null || echo python3)
GRAPHIFY_BIN := $(shell test -f $(CONFIG) && python3 -c "import json; print(json.load(open('$(CONFIG)')).get('graphify_bin', 'graphify'))" 2>/dev/null || echo graphify)

check-config:
	@test -f $(CONFIG) || (echo "❌ $(CONFIG) yok. Once: bash ~/.claude/skills/kod-fabrikasi/scripts/init.sh" && exit 1)
	@echo "✅ Config: $(CONFIG)"
	@echo "   PYTHON_BIN  = $(PYTHON_BIN)"
	@echo "   GRAPHIFY_BIN = $(GRAPHIFY_BIN)"

# Kodu paketler, Drive'a kopyalar, NotebookLM'i birebir aynalar
bundle: check-config
	@echo "📦 Paketleniyor + Drive ve NotebookLM aynalaniyor..."
	$(PYTHON_BIN) bundle.py

# Graphify mimari haritasini gunceller (AST tabanli, LLM yok)
graphify-update: check-config
	@echo "🗺️ Graphify haritasi guncelleniyor..."
	GRAPHIFY_VIZ_NODE_LIMIT=15000 $(GRAPHIFY_BIN) update .
	@echo "📊 Callflow diyagramlari olusturuluyor..."
	-$(GRAPHIFY_BIN) export callflow-html

# Faz bittiginde: harita + paket birlikte
end-phase: check-config
	@echo "🚀 Faz kapatiliyor..."
	$(MAKE) graphify-update
	@echo "-----------------------------------"
	$(MAKE) bundle
	@echo "✅ Faz kapatma islemleri tamamlandi."

# Git hook'larini kur (config'teki framework'e gore)
setup-hooks: check-config
	@echo "⚙️ Git pre-commit + post-commit hook'lari kuruluyor..."
	@chmod +x setup-hooks.sh
	@./setup-hooks.sh
