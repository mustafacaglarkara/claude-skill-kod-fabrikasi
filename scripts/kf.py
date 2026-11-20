#!/usr/bin/env python3
"""Kod Fabrikasi v3 — tek giris noktasi (Windows / macOS / Linux).

Iki kopyasi olur:
  * Skill kopyasi : ~/.claude/skills/kod-fabrikasi/scripts/kf.py  -> init / migrate / repair (assets gerekir)
  * Proje kopyasi : <proje>/.claude/scripts/kf.py                  -> bundle / graphify / sync / hooks / selftest / status

Komutlar:
  check        Kurulum durumu (SKILL.md "ilk kontrol" bunu calistirir)
  init         Etkilesimsiz kurulum; tum bilgiler parametreyle gelir (Claude AskUserQuestion ile toplar)
  repair       Eksik dosyalari tamamlar, mevcutlara dokunmaz
  migrate      v1 / v2 projeyi v3 yapisina tasir (git mv)
  hooks        .git/hooks/pre-commit (gizli bilgi taramasi) + post-commit (end-phase) kurar
  secret-scan  Staged dosyalarda gizli bilgi arar (pre-commit bunu cagirir)
  graphify     Kod haritasini gunceller
  bundle       git'in izledigi dosyalardan paket uretir; Drive + NotebookLM aynalar (etkinse)
  sync         Obsidian kasasina aktarir (etkinse)
  end-phase    graphify + bundle + sync (post-commit bunu cagirir)
  selftest     Kurulumu dogrular; PASS/FAIL/WARN satirlari, FAIL varsa exit 1
  status       Faz hafizasini yazdirir (SessionStart hook'u ile ayni cikti)

Tum ayarlar .claude/kod-fabrikasi.config.json dosyasindan okunur. Hardcoded yol yok.
Guvenlik: paket ve senkron SADECE `git ls-files` ciktisindaki dosyalari kullanir.
"""
import argparse
import asyncio
import datetime as _dt
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

VERSION = 3
MARK = "# >>> kod-fabrikasi >>>"
MARK_END = "# <<< kod-fabrikasi <<<"
CLAUDE_MD_MARK = "<!-- kod-fabrikasi:start -->"
CLAUDE_MD_MARK_END = "<!-- kod-fabrikasi:end -->"
HERE = Path(__file__).resolve().parent

CORE_AGENTS = ["kesifci", "gelistirici", "tester", "reviewer", "faz-arsivcisi"]
OPTIONAL_AGENTS = ["mimar", "guvenlik-inceleyici"]
READ_ONLY_AGENTS = {"kesifci", "tester", "reviewer", "guvenlik-inceleyici"}
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

DEFAULT_PHASE_FILES = {
    "roadmap": ".claude/archives/ROADMAP.md",
    "progress": ".claude/archives/PROGRESS.md",
    "decisions": ".claude/decisions/DECISIONS.md",
    "open_questions": ".claude/decisions/OPEN_QUESTIONS.md",
    "faz_prompt": ".claude/decisions/FAZ_PROMPT.md",
    "memory": ".claude/context/MEMORY.md",
    "graphify_notes": ".claude/context/GRAPHIFY_NOTES.md",
    "qa": ".claude/references/QA_REPORTS.md",
    "known_bugs": ".claude/references/KNOWN_BUGS.md",
    "notebooklm_summary": ".claude/archives/NOTEBOOKLM_SUMMARY.md",
    "phase_template": ".claude/archives/PHASE_TEMPLATE.md",
    "phase_reports_glob": ".claude/archives/PHASE_*.md",
}
# phase_files anahtari -> assets/templates dosya adi
TEMPLATE_FOR = {
    "roadmap": "ROADMAP.md", "progress": "PROGRESS.md", "decisions": "DECISIONS.md",
    "open_questions": "OPEN_QUESTIONS.md", "faz_prompt": "FAZ_PROMPT.md", "memory": "MEMORY.md",
    "graphify_notes": "GRAPHIFY_NOTES.md", "qa": "QA_REPORTS.md", "known_bugs": "KNOWN_BUGS.md",
    "notebooklm_summary": "NOTEBOOKLM_SUMMARY.md", "phase_template": "PHASE_TEMPLATE.md",
}
# v1 (kok) ve v2 (.claude alt klasor) konumlari -> phase_files anahtari
LEGACY_LOCATIONS = {
    "ROADMAP.md": "roadmap", ".claude/ROADMAP.md": "roadmap", ".claude/archives/ROADMAP.md": "roadmap",
    "MEMORY.md": "memory", ".claude/MEMORY.md": "memory", ".claude/context/MEMORY.md": "memory",
    "QA_REPORTS.md": "qa", ".claude/references/QA_REPORTS.md": "qa",
    "KNOWN_BUGS.md": "known_bugs", ".claude/references/KNOWN_BUGS.md": "known_bugs",
    "NOTEBOOKLM_SUMMARY.md": "notebooklm_summary", ".claude/archives/NOTEBOOKLM_SUMMARY.md": "notebooklm_summary",
    "GRAPHIFY_NOTES.md": "graphify_notes", ".claude/context/GRAPHIFY_NOTES.md": "graphify_notes",
    "FAZ_PROMPT.md": "faz_prompt", ".claude/decisions/FAZ_PROMPT.md": "faz_prompt",
    ".claude/PROGRESS.md": "progress", ".claude/DECISIONS.md": "decisions",
    ".claude/OPEN_QUESTIONS.md": "open_questions",
}
GITIGNORE_LINES = [
    "graphify-out/", "__pycache__/", ".claude/settings.local.json", ".claude/bundle-out/",
    "tum_kodlar.txt", ".obsidian/", ".env", ".env.*", "!.env.example",
]
DEFAULT_SECRET_NAME_PATTERNS = [
    r"\.env$", r"\.env\.", r"\.pem$", r"\.key$", r"\.p12$", r"secret", r"password", r"sifre",
    r"\.db$", r"\.sqlite", r"dump\.sql",
]


# ---------------------------------------------------------------- yardimcilar
def log(msg):
    print(f"[kf] {msg}")


def die(msg, code=1):
    print(f"[kf] HATA: {msg}", file=sys.stderr)
    sys.exit(code)


def run(cmd, cwd=None, check=False, env=None, timeout=600):
    r = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, cmd))} -> {r.returncode}\n{r.stderr.strip()}")
    return r


def project_root():
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).is_dir():
        return Path(env).resolve()
    # proje kopyasi: <root>/.claude/scripts/kf.py
    if HERE.name == "scripts" and HERE.parent.name == ".claude":
        return HERE.parent.parent
    r = run(["git", "rev-parse", "--show-toplevel"])
    if r.returncode == 0 and r.stdout.strip():
        return Path(r.stdout.strip()).resolve()
    return Path.cwd().resolve()


def skill_dir():
    """assets/ klasorunu tasiyan skill kopyasini bul (init/migrate/repair icin)."""
    for cand in (HERE.parent, Path.home() / ".claude" / "skills" / "kod-fabrikasi"):
        if (cand / "assets" / "agents").is_dir() and (cand / "assets" / "templates").is_dir():
            return cand
    return None


def config_path(root):
    return root / ".claude" / "kod-fabrikasi.config.json"


def load_config(root, required=True):
    p = config_path(root)
    if not p.exists():
        if required:
            die(f"config yok: {p}\n       once: python <skill>/scripts/kf.py init ...")
        return None
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def save_config(root, cfg):
    p = config_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def phase_files(cfg):
    files = dict(DEFAULT_PHASE_FILES)
    files.update((cfg or {}).get("phase_files", {}))
    return files


def integ(cfg, name):
    i = (cfg.get("integrations") or {}).get(name) or {}
    return i if i.get("enabled") else None


def python_bin(cfg):
    return (cfg or {}).get("python_bin") or sys.executable


def tracked_files(root):
    r = run(["git", "ls-files", "-z"], cwd=root)
    if r.returncode != 0:
        return []
    return [p for p in r.stdout.split("\0") if p]


def is_tracked(root, rel):
    return run(["git", "ls-files", "--error-unmatch", rel], cwd=root).returncode == 0


def today():
    return _dt.date.today().isoformat()


def flat(rel):
    """Goreli yolu tek dosya adina duzlestir; bastaki nokta kalkar (gizli dosya sanilmasin)."""
    return rel.replace("\\", "/").replace("/", "__").lstrip(".")


def render(text, ctx):
    for k, v in ctx.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def ensure_lines(path: Path, lines, label):
    path.touch(exist_ok=True)
    existing = set(path.read_text(encoding="utf-8", errors="replace").splitlines())
    added = [l for l in lines if l not in existing]
    if added:
        with path.open("a", encoding="utf-8") as f:
            if existing and not path.read_text(encoding="utf-8", errors="replace").endswith("\n"):
                f.write("\n")
            f.write("\n".join(added) + "\n")
        log(f"{label}: eklendi -> {', '.join(added)}")
    else:
        log(f"{label}: guncel")


def read_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm, m.group(2)


# ---------------------------------------------------------------- check
def detect_structure(root):
    cfg = load_config(root, required=False)
    if cfg and cfg.get("version") == VERSION:
        return "v3", cfg
    if cfg and (root / ".claude" / "archives").is_dir():
        return "v2", cfg
    if cfg:
        return "v1", cfg
    if any((root / n).exists() for n in ("ROADMAP.md", "MEMORY.md", "QA_REPORTS.md")) or (root / "bundle.py").exists():
        return "v1-config-yok", None
    return "yok", None


def cmd_check(args):
    root = project_root()
    kind, cfg = detect_structure(root)
    print(f"PROJE      : {root}")
    print(f"YAPI       : {kind}")
    print(f"GIT        : {'var' if (root / '.git').exists() else 'YOK'}")
    agents = sorted(p.stem for p in (root / ".claude" / "agents").glob("*.md"))
    print(f"AJANLAR    : {', '.join(agents) if agents else 'yok'}")
    hooks_dir = root / ".git" / "hooks"
    pc = hooks_dir / "post-commit"
    print(f"GIT HOOK   : post-commit {'kod-fabrikasi' if pc.exists() and MARK in pc.read_text(encoding='utf-8', errors='replace') else ('baska' if pc.exists() else 'yok')}")
    s = root / ".claude" / "settings.json"
    has_hook = s.exists() and "faz_hafiza.py" in s.read_text(encoding="utf-8", errors="replace")
    print(f"SESSION HK : {'var' if has_hook else 'yok'}")
    print(f"GRAPHIFY   : {'var' if shutil.which((cfg or {}).get('graphify_bin') or 'graphify') else 'bulunamadi'}")
    if cfg:
        for name in ("drive", "notebooklm", "obsidian"):
            print(f"{name.upper():<11}: {'etkin' if integ(cfg, name) else 'kapali'}")
    print(f"SKILL DIR  : {skill_dir() or 'bulunamadi (init/migrate icin gerekli)'}")


# ---------------------------------------------------------------- init / repair
def build_config(args, root):
    experts = []
    for e in args.expert or []:
        parts = e.split(":")
        name = parts[0].strip()
        domain = parts[1].strip() if len(parts) > 1 else name
        paths = [p for p in parts[2].split(",") if p] if len(parts) > 2 else []
        url = parts[3].strip() if len(parts) > 3 else ""
        experts.append({"name": name, "domain": domain, "paths": paths, "docs_url": url})
    optional = [a for a in (args.agents.split(",") if args.agents else []) if a in OPTIONAL_AGENTS]
    return {
        "_comment": "Kod Fabrikasi v3. Bos/kapali entegrasyon atlanir. Paket yalnizca git'in izledigi dosyalardan olusur.",
        "version": VERSION,
        "project_name": args.name or root.name,
        "language": args.language,
        "python_bin": args.python or sys.executable,
        "graphify_bin": args.graphify or "graphify",
        "framework": args.framework,
        "test_commands": args.test_cmd or [],
        "build_commands": args.build_cmd or [],
        "live_write_commands": args.live_cmd or [],
        "high_risk_areas": args.risk or [],
        "agents": {
            "core": list(CORE_AGENTS),
            "optional": optional,
            "domain_experts": experts,
            "max_parallel_editors": args.max_parallel,
        },
        "phase_files": dict(DEFAULT_PHASE_FILES),
        "integrations": {
            "graphify": {"enabled": not args.no_graphify, "viz_node_limit": 15000},
            "drive": {"enabled": bool(args.drive), "folder_path": args.drive or ""},
            "notebooklm": {
                "enabled": bool(args.notebook), "notebook_id": args.notebook or "",
                "allowed_extensions": [".md", ".txt", ".pdf"],
                "ignore_dirs": ["cache", "__pycache__"], "max_file_size_mb": 50,
            },
            "obsidian": {"enabled": bool(args.obsidian), "vault_path": args.obsidian or ""},
        },
        "bundle": {
            "allowed_extensions": [
                ".go", ".proto", ".sql", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".vue", ".svelte", ".astro",
                ".py", ".json", ".md", ".yml", ".yaml", ".toml", ".html", ".css", ".scss",
                ".php", ".dart", ".swift", ".kt", ".java", ".rb", ".rs", ".cs", ".sh",
            ],
            "skip_files": ["package-lock.json", "pnpm-lock.yaml", "yarn.lock", "composer.lock",
                           "pubspec.lock", "Cargo.lock", "poetry.lock"],
            "skip_prefixes": [".claude/skills/", "graphify-out/"],
            "sync_dirs": [".claude/archives", "graphify-out"],
            "stale_patterns": [],
        },
        "hooks": {
            "pre_commit_secret_scan": True,
            "post_commit_end_phase": True,
            "secret_name_patterns": list(DEFAULT_SECRET_NAME_PATTERNS),
        },
    }


def template_ctx(cfg):
    def bullets(items, empty="- (yok)"):
        return "\n".join(f"- `{i}`" for i in items) if items else empty
    ag = cfg.get("agents", {})
    return {
        "PROJECT_NAME": cfg.get("project_name", ""),
        "DATE": today(),
        "FRAMEWORK": cfg.get("framework", "none"),
        "TEST_COMMANDS": bullets(cfg.get("test_commands"), "- (test komutu tanimli degil; `.claude/kod-fabrikasi.config.json` -> test_commands)"),
        "BUILD_COMMANDS": bullets(cfg.get("build_commands")),
        "LIVE_WRITE_COMMANDS": bullets(cfg.get("live_write_commands"), "- (tanimli degil)"),
        "HIGH_RISK_AREAS": ", ".join(cfg.get("high_risk_areas") or []) or "(tanimli degil)",
        "MAX_PARALLEL": ag.get("max_parallel_editors", 3),
        "EXPERT_ROWS": "\n".join(
            f"| {e['domain']} ile ilgili cagri / alan / sinir / hata kodu ne? | `{e['name']}` (salt okunur) |"
            for e in ag.get("domain_experts", [])
        ),
        "OPTIONAL_ROWS": "\n".join(filter(None, [
            "| Yuksek riskli alan, sistem tasarimi, nedeni bilinmeyen hata, performans | `mimar` (yazar; once yeniden uretir, sonra kok neden) |" if "mimar" in ag.get("optional", []) else "",
            "| Auth, oturum, token, yukleme, gizli bilgi, kisisel veri dokunan degisiklik | `guvenlik-inceleyici` (salt okunur) |" if "guvenlik-inceleyici" in ag.get("optional", []) else "",
        ])),
    }


def install_agents(root, cfg, sdir, force=False):
    src = sdir / "assets" / "agents"
    dst = root / ".claude" / "agents"
    dst.mkdir(parents=True, exist_ok=True)
    ctx = template_ctx(cfg)
    ag = cfg.get("agents", {})
    wanted = list(ag.get("core", CORE_AGENTS)) + list(ag.get("optional", []))
    for name in wanted:
        s = src / f"{name}.md"
        d = dst / f"{name}.md"
        if not s.exists():
            log(f"ajan sablonu yok: {s.name} (atlandi)")
            continue
        if d.exists() and not force:
            log(f"ajan korunuyor: {d.relative_to(root).as_posix()}")
            continue
        d.write_text(render(s.read_text(encoding="utf-8"), ctx), encoding="utf-8", newline="\n")
        log(f"ajan yazildi: {d.relative_to(root).as_posix()}")
    tpl = src / "alan-uzmani.md"
    for e in ag.get("domain_experts", []):
        d = dst / f"{e['name']}.md"
        if d.exists() and not force:
            log(f"ajan korunuyor: {d.relative_to(root).as_posix()}")
            continue
        ectx = dict(ctx, AGENT_NAME=e["name"], DOMAIN=e.get("domain", e["name"]),
                    DOMAIN_PATHS=", ".join(f"`{p}`" for p in e.get("paths", [])) or "(belirtilmedi)",
                    DOMAIN_DOCS_URL=e.get("docs_url") or "(belirtilmedi)")
        d.write_text(render(tpl.read_text(encoding="utf-8"), ectx), encoding="utf-8", newline="\n")
        log(f"alan uzmani yazildi: {d.relative_to(root).as_posix()}")


def install_templates(root, cfg, sdir):
    tdir = sdir / "assets" / "templates"
    ctx = template_ctx(cfg)
    for key, rel in phase_files(cfg).items():
        tname = TEMPLATE_FOR.get(key)
        if not tname or "*" in rel:
            continue
        d = root / rel
        if d.exists():
            continue
        s = tdir / tname
        if not s.exists():
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(render(s.read_text(encoding="utf-8"), ctx), encoding="utf-8", newline="\n")
        log(f"belge olusturuldu: {rel}")


def install_scripts(root, sdir):
    pairs = [
        (sdir / "scripts" / "kf.py", root / ".claude" / "scripts" / "kf.py"),
        (sdir / "scripts" / "faz_hafiza.py", root / ".claude" / "hooks" / "faz_hafiza.py"),
    ]
    for s, d in pairs:
        d.parent.mkdir(parents=True, exist_ok=True)
        if d.exists() and d.read_bytes() == s.read_bytes():
            continue
        shutil.copy2(s, d)
        log(f"betik kopyalandi: {d.relative_to(root).as_posix()}")


def merge_settings(root, cfg):
    """`.claude/settings.json` birlestirir: mevcut kurallar korunur, eksikler eklenir."""
    p = root / ".claude" / "settings.json"
    data = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            log(f"settings.json bozuk JSON ({e}); dokunulmadi. Elle duzelt.")
            return
    perms = data.setdefault("permissions", {})
    deny = perms.setdefault("deny", [])
    ask = perms.setdefault("ask", [])
    for rule in ["Read(.env)", "Read(.env.*)", "Read(**/*.pem)", "Read(**/*.key)", "Bash(cat *.env*)"]:
        if rule not in deny:
            deny.append(rule)
    for rule in ["Bash(git push *)", "Bash(git push)", "Bash(git reset --hard *)", "Bash(git checkout -- *)",
                 "Bash(git stash *)", "Bash(git clean *)", "Bash(rm -rf *)"]:
        if rule not in ask:
            ask.append(rule)
    for cmd in cfg.get("live_write_commands") or []:
        rule = f"Bash({cmd} *)"
        if rule not in ask and f"Bash({cmd})" not in ask:
            ask.append(rule)
            ask.append(f"Bash({cmd})")
    hooks = data.setdefault("hooks", {})
    ss = hooks.setdefault("SessionStart", [])
    hook_cmd = f'"{python_bin(cfg)}" "$CLAUDE_PROJECT_DIR/.claude/hooks/faz_hafiza.py"'
    if not any("faz_hafiza.py" in json.dumps(g) for g in ss):
        ss.append({"matcher": "startup|resume|clear|compact",
                   "hooks": [{"type": "command", "command": hook_cmd, "timeout": 15}]})
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    log("settings.json birlestirildi (deny: .env/pem/key, ask: push/reset/canli komutlar, SessionStart hook)")


def install_claude_md(root, cfg, sdir):
    tpl = sdir / "assets" / "templates" / "CLAUDE_SECTION.md"
    if not tpl.exists():
        return
    section = render(tpl.read_text(encoding="utf-8"), template_ctx(cfg))
    target = root / "CLAUDE.md"
    if not target.exists() and (root / ".claude" / "CLAUDE.md").exists():
        target = root / ".claude" / "CLAUDE.md"
    text = target.read_text(encoding="utf-8") if target.exists() else f"# {cfg.get('project_name', root.name)}\n\n"
    block = f"{CLAUDE_MD_MARK}\n{section.strip()}\n{CLAUDE_MD_MARK_END}\n"
    if CLAUDE_MD_MARK in text:
        text = re.sub(re.escape(CLAUDE_MD_MARK) + r".*?" + re.escape(CLAUDE_MD_MARK_END) + r"\n?", block, text, flags=re.S)
        log(f"{target.relative_to(root).as_posix()}: kod-fabrikasi bolumu guncellendi")
    else:
        text = text.rstrip("\n") + "\n\n" + block
        log(f"{target.relative_to(root).as_posix()}: kod-fabrikasi bolumu eklendi")
    target.write_text(text, encoding="utf-8", newline="\n")
    n = len(text.splitlines())
    if n > 200:
        log(f"UYARI: {target.name} {n} satir (hedef < 200). Bolumleri kisalt ya da .claude/rules/ kullan.")


def install_graphify_files(root, sdir):
    tdir = sdir / "assets" / "templates"
    for name, dest in (("graphifyignore", ".graphifyignore"), ("graphifyrc", ".graphifyrc")):
        d = root / dest
        s = tdir / name
        if s.exists() and not d.exists():
            shutil.copy2(s, d)
            log(f"{dest} olusturuldu")


def run_install(root, cfg, sdir, force_agents=False):
    for sub in ("context", "decisions", "archives", "references", "agents", "hooks", "scripts"):
        (root / ".claude" / sub).mkdir(parents=True, exist_ok=True)
    install_templates(root, cfg, sdir)
    install_agents(root, cfg, sdir, force=force_agents)
    install_scripts(root, sdir)
    merge_settings(root, cfg)
    ensure_lines(root / ".gitignore", GITIGNORE_LINES, ".gitignore")
    ga = root / ".gitattributes"
    if not ga.exists():
        ga.write_text("* text=auto eol=lf\n*.png binary\n*.jpg binary\n*.webp binary\n*.pdf binary\n*.ico binary\n", encoding="utf-8", newline="\n")
        log(".gitattributes olusturuldu (LF)")
    if integ(cfg, "graphify"):
        install_graphify_files(root, sdir)
    install_claude_md(root, cfg, sdir)


def print_next_steps(root, cfg):
    py = python_bin(cfg)
    print("\nSonraki adimlar:")
    if not (root / ".git").exists():
        print("  1. git init -b main            # once git; Drive/Obsidian surum kontrolu degildir")
    print(f"  - {py} .claude/scripts/kf.py hooks      # pre-commit (gizli bilgi) + post-commit (end-phase)")
    print(f"  - {py} .claude/scripts/kf.py selftest   # kurulumu dogrula")
    if integ(cfg, "graphify"):
        print(f"  - {cfg.get('graphify_bin', 'graphify')} update .   # ilk kod haritasi (sonra: graphify install --project istege bagli)")
    print("  - Ajanlar birkac saniye icinde yuklenir (hot reload). 'Agent type not found' gorursen yeni oturum ac.")
    print("  - Faz baslatmak icin Claude'a: \"Siradaki fazi baslat.\"")


def cmd_init(args):
    root = project_root()
    sdir = skill_dir()
    if not sdir:
        die("skill kopyasi bulunamadi (assets/ yok). init'i ~/.claude/skills/kod-fabrikasi/scripts/kf.py ile calistir.")
    existing = load_config(root, required=False)
    if existing and not args.force:
        log(f"config zaten var ({config_path(root).relative_to(root).as_posix()}). Eksikleri tamamlamak icin: repair; yapiyi tasimak icin: migrate; ustune yazmak icin: init --force")
        return 2
    if not args.framework:
        die("--framework zorunlu (flutter|go|php-laravel|python|node|rust|dotnet|none)")
    cfg = build_config(args, root)
    save_config(root, cfg)
    log(f"config yazildi: {config_path(root).relative_to(root).as_posix()}")
    run_install(root, cfg, sdir, force_agents=args.force)
    log("kurulum tamam.")
    print_next_steps(root, cfg)
    return 0


def cmd_repair(args):
    root = project_root()
    sdir = skill_dir()
    if not sdir:
        die("skill kopyasi bulunamadi (assets/ yok).")
    cfg = load_config(root)
    if cfg.get("version") != VERSION:
        die(f"config v{cfg.get('version', 1)}. Once: kf.py migrate")
    run_install(root, cfg, sdir, force_agents=args.force_agents)
    log("repair tamam.")
    return 0


# ---------------------------------------------------------------- migrate
def convert_legacy_config(old, root):
    """v1/v2 config -> v3 sema. Eski alanlar korunur, yenileri eklenir."""
    drive = old.get("drive_folder_path") or ""
    nb = old.get("notebook_id") or ""
    cfg = {
        "_comment": "Kod Fabrikasi v3 (migrate ile donusturuldu).",
        "version": VERSION,
        "project_name": old.get("project_name") or root.name,
        "language": old.get("language", "tr"),
        "python_bin": old.get("python_bin") or sys.executable,
        "graphify_bin": old.get("graphify_bin") or "graphify",
        "framework": old.get("framework", "none"),
        "test_commands": old.get("test_commands") or {
            "flutter": ["flutter analyze", "flutter test"], "go": ["go test ./..."],
            "php-laravel": ["php artisan test"], "python": ["pytest"], "node": ["npm test"],
        }.get(old.get("framework", "none"), []),
        "build_commands": old.get("build_commands") or [],
        "live_write_commands": old.get("live_write_commands") or [],
        "high_risk_areas": old.get("high_risk_areas") or [],
        "agents": old.get("agents") or {"core": list(CORE_AGENTS), "optional": [], "domain_experts": [], "max_parallel_editors": 3},
        "phase_files": dict(DEFAULT_PHASE_FILES),
        "integrations": {
            "graphify": {"enabled": True, "viz_node_limit": 15000},
            "drive": {"enabled": bool(drive), "folder_path": drive},
            "notebooklm": {
                "enabled": bool(nb) and old.get("sync_to_notebooklm", True), "notebook_id": nb,
                "allowed_extensions": old.get("notebooklm_allowed_extensions", [".md", ".txt", ".pdf"]),
                "ignore_dirs": old.get("notebooklm_ignore_dirs", ["cache", "__pycache__"]),
                "max_file_size_mb": old.get("notebooklm_max_file_size_mb", 50),
            },
            "obsidian": {"enabled": bool(old.get("obsidian_vault_path")), "vault_path": old.get("obsidian_vault_path", "")},
        },
        "bundle": {
            "allowed_extensions": old.get("allowed_extensions") or build_config(argparse.Namespace(
                name=None, language="tr", python=None, graphify=None, framework="none", test_cmd=[], build_cmd=[],
                live_cmd=[], risk=[], agents=None, expert=[], max_parallel=3, no_graphify=False, drive=None,
                notebook=None, obsidian=None), root)["bundle"]["allowed_extensions"],
            "skip_files": ["package-lock.json", "pnpm-lock.yaml", "yarn.lock", "composer.lock", "pubspec.lock", "Cargo.lock", "poetry.lock"],
            "skip_prefixes": [".claude/skills/", "graphify-out/"],
            "sync_dirs": [".claude/archives", "graphify-out"],
            # v1/v2 bundle.py'nin Drive kokune yazdigi dosyalar; v3 bunlari kod/ ve belgeler/ altina koyar
            "stale_patterns": old.get("stale_drive_patterns") or [
                "tum_kodlar.txt", "CLAUDE_*.md", "ROADMAP.md", "MEMORY.md", "QA_REPORTS.md",
                "NOTEBOOKLM_SUMMARY.md", "GRAPHIFY_NOTES.md", "FAZ_PROMPT.md", "KNOWN_BUGS.md",
            ],
        },
        "hooks": {"pre_commit_secret_scan": True, "post_commit_end_phase": True,
                  "secret_name_patterns": list(DEFAULT_SECRET_NAME_PATTERNS)},
    }
    return cfg


def move_file(root, src_rel, dst_rel, dry):
    s, d = root / src_rel, root / dst_rel
    if not s.exists() or s.resolve() == d.resolve():
        return False
    if d.exists():
        log(f"UYARI: hedef zaten var, atlandi: {src_rel} -> {dst_rel}")
        return False
    log(f"tasi: {src_rel} -> {dst_rel}")
    if dry:
        return True
    d.parent.mkdir(parents=True, exist_ok=True)
    if is_tracked(root, src_rel):
        run(["git", "mv", src_rel, dst_rel], cwd=root, check=True)
    else:
        shutil.move(str(s), str(d))
    return True


def cmd_migrate(args):
    root = project_root()
    sdir = skill_dir()
    if not sdir:
        die("skill kopyasi bulunamadi (assets/ yok).")
    kind, old = detect_structure(root)
    if kind == "v3":
        log("zaten v3. Eksikler icin: repair")
        return 0
    if kind == "yok":
        die("kurulu Kod Fabrikasi bulunamadi; yeni kurulum icin: init")
    dry = args.dry_run
    log(f"tespit: {kind}{' (dry-run)' if dry else ''}")
    cfg = convert_legacy_config(old or {}, root)
    files = phase_files(cfg)
    # eski config'teki phase_files yollarini da aday olarak ekle
    for key, rel in ((old or {}).get("phase_files") or {}).items():
        if key in files and rel and rel != files[key]:
            LEGACY_LOCATIONS[rel] = key
    moved = 0
    for src_rel, key in LEGACY_LOCATIONS.items():
        if key in files:
            moved += move_file(root, src_rel, files[key], dry)
    # faz raporlari: reports/fazNN_x.md -> .claude/archives/PHASE_NN_x.md
    for rep_dir in ("reports", ".claude/reports"):
        rd = root / rep_dir
        if rd.is_dir():
            for f in sorted(rd.glob("*.md")):
                m = re.match(r"(?:faz|phase|PHASE)[_-]?(\d+(?:[._]\d+)*)[_-]?(.*)\.md$", f.name, re.I)
                if m:
                    num = m.group(1).replace(".", "_")
                    if "_" in num:
                        head, tail = num.split("_", 1)
                        num = head.zfill(2) + "_" + tail
                    else:
                        num = num.zfill(2)
                    new = f"PHASE_{num}" + (f"_{m.group(2)}" if m.group(2) else "") + ".md"
                else:
                    new = f.name
                moved += move_file(root, f"{rep_dir}/{f.name}", f".claude/archives/{new}", dry)
            if not dry and rd.is_dir() and not any(rd.iterdir()):
                rd.rmdir()
    # eski skill betikleri (kok): yalnizca Kod Fabrikasi imzasi tasiyorsa kaldir
    for name in ("bundle.py", "setup-hooks.sh", "Makefile"):
        p = root / name
        if p.exists():
            head = p.read_text(encoding="utf-8", errors="replace")[:600]
            if "Kod Fabrikas" in head or "kod-fabrikasi" in head:
                if args.remove_legacy:
                    log(f"eski betik kaldiriliyor: {name}")
                    if not dry:
                        if is_tracked(root, name):
                            run(["git", "rm", "-q", name], cwd=root, check=True)
                        else:
                            p.unlink()
                else:
                    log(f"eski betik duruyor: {name} (kaldirmak icin --remove-legacy)")
    if dry:
        log(f"dry-run: {moved} dosya tasinacak, config v3'e cevrilecek, eksik ajan/belge/hook eklenecek.")
        return 0
    backup = config_path(root).with_suffix(".json.v%s.bak" % (2 if kind == "v2" else 1))
    if config_path(root).exists():
        shutil.copy2(config_path(root), backup)
        log(f"eski config yedegi: {backup.relative_to(root).as_posix()}")
    save_config(root, cfg)
    run_install(root, cfg, sdir)
    log(f"migrate tamam ({moved} dosya tasindi). Simdi: kf.py hooks  (eski post-commit kok bundle.py'yi cagiriyor) ve kf.py selftest")
    if integ(cfg, "drive"):
        log("Drive: v3 duzeni kod/ + belgeler/ + sync_dirs. Eski kok dosyalar ilk bundle'da stale_patterns ile temizlenir.")
    return 0


# ---------------------------------------------------------------- hooks
def cmd_hooks(args):
    root = project_root()
    cfg = load_config(root)
    hooks_dir = root / ".git" / "hooks"
    if not hooks_dir.parent.is_dir():
        die("git deposu yok. Once: git init -b main")
    hooks_dir.mkdir(exist_ok=True)
    py = Path(python_bin(cfg)).as_posix()
    kf = "$(git rev-parse --show-toplevel)/.claude/scripts/kf.py"
    hcfg = cfg.get("hooks") or {}

    def write_hook(name, body):
        p = hooks_dir / name
        old = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        if old and MARK not in old:
            bak = hooks_dir / f"{name}.pre-kf.bak"
            shutil.copy2(p, bak)
            log(f"UYARI: mevcut {name} hook'u yedeklendi -> {bak.name}. Icerigi kf.py cagrisinin yanina elle ekle (ornegin graphify hook install ciktisi).")
        text = f"#!/bin/sh\n{MARK}\n{body}\n{MARK_END}\n"
        p.write_text(text, encoding="utf-8", newline="\n")
        try:
            p.chmod(p.stat().st_mode | 0o111)
        except OSError:
            pass
        log(f"{name} yazildi")

    if hcfg.get("pre_commit_secret_scan", True):
        write_hook("pre-commit", f'"{py}" "{kf}" secret-scan --staged || exit 1')
    if hcfg.get("post_commit_end_phase", True):
        write_hook("post-commit",
                   'if [ -n "$KF_SKIP" ]; then exit 0; fi\n'
                   f'"{py}" "{kf}" end-phase --from-hook 2>&1 | tail -15\nexit 0')
    log("hook'lar hazir. Gecici atlamak icin: KF_SKIP=1 git commit ...  |  `graphify hook install` KULLANMA (post-commit'i ezer; graphify update'i end-phase cagirir)")
    return 0


# ---------------------------------------------------------------- secret-scan
def cmd_secret_scan(args):
    root = project_root()
    cfg = load_config(root, required=False) or {}
    patterns = (cfg.get("hooks") or {}).get("secret_name_patterns") or DEFAULT_SECRET_NAME_PATTERNS
    if args.staged:
        r = run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"], cwd=root)
        files = [f for f in r.stdout.splitlines() if f]
    else:
        files = tracked_files(root)
    bad = [f for f in files if any(re.search(p, f, re.I) for p in patterns) and not f.endswith(".example")]
    problems = []
    if bad:
        problems.append("Gizli/ticari gorunumlu dosya adlari:\n  " + "\n  ".join(bad))
    # .env degerleri izlenen/staged icerikte geciyor mu (degeri yazdirmadan)
    for env in [p for p in root.glob(".env*") if p.is_file() and not p.name.endswith(".example")]:
        for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            # yalnizca tamamen sayi/boolean/yerel adres olan degerler sir sayilmaz
            if len(v) < 8 or re.fullmatch(r"(true|false|\d+|(https?://)?(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?(/[\w./-]*)?)", v, re.I):
                continue
            g = run(["git", "grep", "--cached", "-lF", "--", v], cwd=root)
            hits = [h for h in g.stdout.splitlines() if h and not Path(h).name.startswith(".env")]
            if hits:
                problems.append(f".env anahtari {k.strip()} degeri su dosyalarda geciyor: {', '.join(hits)}")
    # staged diff icinde anahtar/token kalibi (yalnizca uyari)
    if args.staged:
        d = run(["git", "diff", "--cached", "-U0"], cwd=root).stdout
        hits = re.findall(r"^\+.*?(?:api[_-]?key|secret|passw(?:or)?d|token|private[_-]?key)\s*[:=]\s*['\"]?([A-Za-z0-9_\-/+=]{16,})", d, re.I | re.M)
        if hits:
            print(f"[kf] UYARI: staged diff'te {len(hits)} olasi anahtar/token satiri var. Degerleri kontrol et (deger yazdirilmadi).")
    if problems:
        print("[kf] GIZLI BILGI TARAMASI BASARISIZ:\n" + "\n".join(problems))
        print("[kf] Dosyayi .gitignore'a al ya da degeri .env'e tasi. Bilincli devam: KF_SKIP_SECRET=1 (onerilmez).")
        return 0 if os.environ.get("KF_SKIP_SECRET") else 1
    log("gizli bilgi taramasi temiz")
    return 0


# ---------------------------------------------------------------- graphify
def cmd_graphify(args):
    root = project_root()
    cfg = load_config(root)
    g = integ(cfg, "graphify")
    if not g:
        log("graphify kapali (config integrations.graphify.enabled=false)")
        return 0
    binp = cfg.get("graphify_bin") or "graphify"
    if not shutil.which(binp) and not Path(binp).exists():
        log(f"graphify bulunamadi ({binp}). Kurulum: uv tool install \"graphifyy[sql]\" --python 3.13")
        return 0 if args.from_hook else 1
    env = dict(os.environ, GRAPHIFY_VIZ_NODE_LIMIT=str(g.get("viz_node_limit", 15000)))
    r = run([binp, "update", "."], cwd=root, env=env, timeout=1800)
    tail = (r.stdout or r.stderr).strip().splitlines()[-3:]
    log("graphify update: " + (" | ".join(tail) if tail else f"exit {r.returncode}"))
    return 0 if r.returncode == 0 or args.from_hook else r.returncode


# ---------------------------------------------------------------- bundle
def bundle_dir(root, cfg):
    d = integ(cfg, "drive")
    if d and d.get("folder_path"):
        p = Path(d["folder_path"])
        if p.is_dir():
            return p, True
        log(f"Drive klasoru yok ({p}); yerel cikti kullaniliyor (Drive masaustu calisiyor mu?)")
    return root / ".claude" / "bundle-out", False


def doc_files(root, cfg, tracked):
    ts = set(tracked)
    docs = []
    for rel in list(phase_files(cfg).values()) + ["README.md", "CLAUDE.md", ".claude/CLAUDE.md"]:
        if "*" in rel:
            docs += [t for t in ts if fnmatch.fnmatch(t, rel)]
        elif rel in ts:
            docs.append(rel)
    docs += [t for t in ts if (t.startswith(".claude/") and t.endswith(".md") and "/skills/" not in t) or (t.startswith("docs/") and t.endswith(".md"))]
    seen, out = set(), []
    for d in docs:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def replace_dir(path: Path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def cmd_bundle(args):
    root = project_root()
    cfg = load_config(root)
    b = cfg.get("bundle") or {}
    tracked = tracked_files(root)
    if not tracked:
        log("git izlenen dosya yok (repo degil ya da bos). Paket uretilmedi.")
        return 0
    exts = set(b.get("allowed_extensions") or [])
    skip_files = set(b.get("skip_files") or [])
    skip_prefix = tuple(b.get("skip_prefixes") or [])
    code = [t for t in tracked if Path(t).suffix in exts and Path(t).name not in skip_files
            and not t.startswith(skip_prefix) and not Path(t).name.startswith(".env")]
    docs = doc_files(root, cfg, tracked)
    out_dir, is_drive = bundle_dir(root, cfg)
    log(f"paket: {len(code)} kaynak dosya + {len(docs)} belge -> {out_dir}{' (Drive)' if is_drive else ' (yerel)'}")
    if args.dry_run:
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    commit = run(["git", "rev-parse", "--short", "HEAD"], cwd=root).stdout.strip()

    kod = out_dir / "kod"
    replace_dir(kod)
    with (kod / "tum_kodlar.txt").open("w", encoding="utf-8") as f:
        f.write(f"# {cfg.get('project_name', root.name)} - kaynak kod paketi\n# commit {commit} - {_dt.datetime.now():%Y-%m-%d %H:%M}\n")
        f.write("# Yalnizca git'in izledigi dosyalar. Gizli dosyalar git disindadir.\n\n")
        f.write("## Klasor yapisi\n")
        for t in code:
            f.write(f"  {t}\n")
        f.write("\n")
        for rel in code:
            try:
                text = (root / rel).read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            f.write(f"\n\n===== {rel} =====\n{text}")

    belgeler = out_dir / "belgeler"
    replace_dir(belgeler)
    for rel in docs:
        shutil.copy2(root / rel, belgeler / flat(rel))
    report = root / "graphify-out" / "GRAPH_REPORT.md"
    if report.exists():
        shutil.copy2(report, belgeler / "graphify-out__GRAPH_REPORT.md")

    for sd in b.get("sync_dirs") or []:
        src = root / sd
        if src.is_dir():
            dest = out_dir / flat(sd)
            if sd == "graphify-out":
                # buyuk html/json NotebookLM'e gitmez; yalnizca .md kopyala
                replace_dir(dest)
                for f_ in src.glob("*.md"):
                    shutil.copy2(f_, dest / f_.name)
            else:
                shutil.rmtree(dest, ignore_errors=True)
                shutil.copytree(src, dest)
            log(f"aynalandi: {sd}/")

    cleanup_stale(out_dir, b.get("stale_patterns") or [])
    nb = integ(cfg, "notebooklm")
    if nb and nb.get("notebook_id"):
        asyncio.run(notebooklm_mirror(out_dir, nb))
    elif nb:
        log("notebooklm etkin ama notebook_id bos; atlandi")
    return 0


def cleanup_stale(out_dir: Path, patterns):
    if not patterns:
        return
    for p in out_dir.iterdir():
        if p.is_file() and any(fnmatch.fnmatch(p.name, pat) for pat in patterns):
            try:
                p.unlink()
                log(f"eski artik dosya silindi: {p.name}")
            except OSError as e:
                log(f"{p.name} silinemedi: {e}")


# ---- NotebookLM (tuzaklar.md #1, #2, #4, #6, #9 — mantigi DEGISTIRME) ----
def collect_sources(out_dir: Path, nb):
    allowed = set(nb.get("allowed_extensions") or [".md", ".txt", ".pdf"])
    ignore = set(nb.get("ignore_dirs") or [])
    max_size = int(nb.get("max_file_size_mb", 50)) * 1024 * 1024
    collected, seen = [], set()
    for r, dirs, files in os.walk(out_dir):
        dirs[:] = [d for d in dirs if d not in ignore and not d.startswith(".")]
        for fname in sorted(files):
            if fname.startswith(".") or Path(fname).suffix.lower() not in allowed:
                continue
            full = Path(r) / fname
            try:
                size = full.stat().st_size
            except OSError:
                continue
            if size == 0:
                continue
            if size > max_size:
                log(f"{fname} cok buyuk ({size // 1024 // 1024} MB), atlandi")
                continue
            title = full.relative_to(out_dir).as_posix().replace("/", "__")
            if title in seen:
                log(f"baslik cakismasi '{title}', atlandi")
                continue
            seen.add(title)
            collected.append((title, full))
    return collected


async def notebooklm_mirror(out_dir: Path, nb):
    sources = collect_sources(out_dir, nb)
    if not sources:
        log("paket klasoru bos; GUVENLIK FRENI: NotebookLM'e dokunulmuyor")
        return
    try:
        from notebooklm import NotebookLMClient  # type: ignore
    except ImportError:
        log("notebooklm-py kurulu degil (pip install 'notebooklm-py[browser]'); NotebookLM atlandi")
        return
    nid = nb["notebook_id"]
    log(f"NotebookLM: {len(sources)} kaynak birebir aynalaniyor")
    staging = Path(tempfile.mkdtemp(prefix="kf_nblm_"))
    try:
        async with await NotebookLMClient.from_storage() as client:
            old = await client.sources.list(nid)  # LISTE olarak dolas, dict YAPMA
            desired = {t for t, _ in sources}
            ok = set()
            for title, path in sources:
                try:
                    if path.name == title:
                        await client.sources.add_file(nid, str(path), wait=True, wait_timeout=300)
                    else:
                        staged = staging / title
                        shutil.copy(path, staged)
                        await client.sources.add_file(nid, str(staged), wait=True, wait_timeout=300)
                    ok.add(title)
                except Exception as e:
                    log(f"'{title}' yuklenemedi: {e}")
            for s in old:
                if s.title not in desired:
                    reason = "klasorde yok"
                elif s.title in ok:
                    reason = "eski nusha"
                else:
                    log(f"'{s.title}' eski nushasi korunuyor (yeni yukleme basarisiz)")
                    continue
                try:
                    await client.sources.delete(nid, s.id)
                    log(f"silindi: '{s.title}' ({reason})")
                except Exception as e:
                    log(f"'{s.title}' silinemedi: {e}")
    except Exception as e:
        log(f"NotebookLM genel hata: {e}")
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    log("NotebookLM web arayuzunde 'Yenile' tusuna basmayi unutma.")


# ---------------------------------------------------------------- sync (Obsidian)
def cmd_sync(args):
    root = project_root()
    cfg = load_config(root)
    ob = integ(cfg, "obsidian")
    if not ob or not ob.get("vault_path"):
        log("obsidian kapali")
        return 0
    vault = Path(ob["vault_path"])
    if not (vault / ".obsidian").is_dir():
        log(f"Obsidian kasasi bulunamadi (.obsidian yok): {vault}; atlandi")
        return 0
    proje = vault / "Proje"
    if not proje.exists():
        log(f"Obsidian: {proje} -> .claude junction")
        if not args.dry_run:
            if os.name == "nt":
                run(["cmd", "/c", "mklink", "/J", str(proje), str(root / ".claude")], check=True)
            else:
                proje.symlink_to(root / ".claude", target_is_directory=True)
    tracked = tracked_files(root)
    docs = [t for t in tracked if t.startswith("docs/") and t.endswith(".md")]
    log(f"Obsidian: {len(docs)} belge -> Belgeler/")
    if not args.dry_run:
        (vault / "Belgeler").mkdir(exist_ok=True)
        for rel in docs:
            shutil.copy2(root / rel, vault / "Belgeler" / Path(rel).name)
    g = cfg.get("graphify_bin") or "graphify"
    if (root / "graphify-out" / "graph.json").exists() and (shutil.which(g) or Path(g).exists()):
        log("Obsidian: kod haritasi -> Kod Haritasi/")
        if not args.dry_run:
            r = run([g, "export", "obsidian", "--dir", str(vault / "Kod Haritasi")], cwd=root, timeout=600)
            line = (r.stdout or r.stderr).strip().splitlines()
            log(line[0] if line else f"graphify export exit {r.returncode}")
    return 0


# ---------------------------------------------------------------- end-phase
def cmd_end_phase(args):
    root = project_root()
    cfg = load_config(root)
    ns = argparse.Namespace(from_hook=args.from_hook, dry_run=False)
    for name, fn in (("graphify", cmd_graphify), ("bundle", cmd_bundle), ("sync", cmd_sync)):
        try:
            fn(ns)
        except Exception as e:  # hook'tan cagrildiginda commit'i asla bozma
            log(f"{name} hatasi: {e}")
            if not args.from_hook:
                return 1
    log("end-phase tamam")
    return 0


# ---------------------------------------------------------------- selftest
def cmd_selftest(args):
    root = project_root()
    results = []

    def rec(status, msg):
        results.append((status, msg))
        print(f"{status:<4} {msg}")

    cfg = load_config(root, required=False)
    if not cfg:
        rec("FAIL", "config yok")
        return 1
    rec("PASS" if cfg.get("version") == VERSION else "FAIL", f"config version = {cfg.get('version')}")
    for k in ("framework", "python_bin", "test_commands"):
        rec("PASS" if k in cfg else "FAIL", f"config alani: {k}")
    pyb = python_bin(cfg)
    rec("PASS" if Path(pyb).exists() or shutil.which(pyb) else "FAIL", f"python_bin bulunuyor: {pyb}")
    for key, rel in phase_files(cfg).items():
        if "*" in rel:
            continue
        rec("PASS" if (root / rel).exists() else ("WARN" if key in ("graphify_notes", "notebooklm_summary", "faz_prompt") else "FAIL"), f"belge: {rel}")
    # ajanlar
    adir = root / ".claude" / "agents"
    ag = cfg.get("agents", {})
    expected = list(ag.get("core", CORE_AGENTS)) + list(ag.get("optional", [])) + [e["name"] for e in ag.get("domain_experts", [])]
    for name in expected:
        p = adir / f"{name}.md"
        if not p.exists():
            rec("FAIL", f"ajan dosyasi yok: {name}.md")
            continue
        fm, body = read_frontmatter(p)
        ok = fm.get("name") == name and bool(fm.get("description"))
        rec("PASS" if ok else "FAIL", f"ajan {name}: name/description")
        tools = {t.strip() for t in fm.get("tools", "").strip("[]").split(",") if t.strip()}
        ro = name in READ_ONLY_AGENTS or name in [e["name"] for e in ag.get("domain_experts", [])]
        if ro:
            rec("PASS" if tools and not (tools & EDIT_TOOLS) else "FAIL", f"ajan {name}: salt okunur (Edit/Write yok)")
        if name == "faz-arsivcisi":
            rec("PASS" if "Bash" not in tools else "WARN", "ajan faz-arsivcisi: Bash yok")
        rec("PASS" if "Verimli" in body else "WARN", f"ajan {name}: 'Verimli calis' blogu")
        rec("PASS" if "PROAKT" in fm.get("description", "").upper() or name in ("gelistirici", "mimar") else "WARN", f"ajan {name}: description proaktif tetikleyici")
    # settings
    sp = root / ".claude" / "settings.json"
    if sp.exists():
        try:
            s = json.loads(sp.read_text(encoding="utf-8"))
            rec("PASS", "settings.json gecerli JSON")
            deny = (s.get("permissions") or {}).get("deny") or []
            rec("PASS" if any(".env" in d for d in deny) else "FAIL", "settings deny: .env")
            ss = (s.get("hooks") or {}).get("SessionStart") or []
            rec("PASS" if any("faz_hafiza.py" in json.dumps(g) for g in ss) else "FAIL", "settings SessionStart hook: faz_hafiza.py")
        except json.JSONDecodeError as e:
            rec("FAIL", f"settings.json bozuk: {e}")
    else:
        rec("FAIL", "settings.json yok")
    # hook calisiyor mu
    hp = root / ".claude" / "hooks" / "faz_hafiza.py"
    if hp.exists():
        r = run([pyb, str(hp)], cwd=Path(tempfile.gettempdir()), env=dict(os.environ, CLAUDE_PROJECT_DIR=str(root)), timeout=30)
        rec("PASS" if r.returncode == 0 and "Proje hafizasi" in r.stdout else "FAIL", "faz_hafiza.py calisiyor (exit 0, cikti var)")
    else:
        rec("FAIL", "faz_hafiza.py yok")
    # scripts
    rec("PASS" if (root / ".claude" / "scripts" / "kf.py").exists() else "FAIL", ".claude/scripts/kf.py")
    for n in ("bundle.py", "setup-hooks.sh"):
        if (root / n).exists():
            rec("WARN", f"eski kok betik duruyor: {n} (migrate --remove-legacy)")
    # gitignore
    gi = root / ".gitignore"
    gl = set(gi.read_text(encoding="utf-8", errors="replace").splitlines()) if gi.exists() else set()
    for line in ("graphify-out/", ".claude/settings.local.json", ".claude/bundle-out/"):
        rec("PASS" if line in gl else "FAIL", f".gitignore: {line}")
    # git hooks
    hd = root / ".git" / "hooks"
    pc = hd / "post-commit"
    if pc.exists():
        t = pc.read_text(encoding="utf-8", errors="replace")
        rec("PASS" if MARK in t else "WARN", "post-commit hook kod-fabrikasi'ye ait")
        rec("WARN" if ("graphify" in t and MARK not in t) else "PASS", "post-commit: graphify hook install cakismasi yok")
    else:
        rec("WARN", "post-commit hook kurulmamis (kf.py hooks)")
    rec("PASS" if (hd / "pre-commit").exists() else "WARN", "pre-commit hook (gizli bilgi taramasi)")
    # CLAUDE.md
    cm = [p for p in (root / "CLAUDE.md", root / ".claude" / "CLAUDE.md") if p.exists()]
    rec("PASS" if any(CLAUDE_MD_MARK in p.read_text(encoding="utf-8", errors="replace") for p in cm) else "WARN", "CLAUDE.md: kod-fabrikasi bolumu")
    for p in cm:
        n = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        rec("PASS" if n <= 200 else "WARN", f"{p.name} {n} satir (hedef <= 200)")
    # entegrasyonlar
    if integ(cfg, "graphify"):
        g = cfg.get("graphify_bin") or "graphify"
        rec("PASS" if shutil.which(g) or Path(g).exists() else "WARN", f"graphify bulunuyor: {g}")
    if integ(cfg, "notebooklm"):
        r = run([pyb, "-c", "import notebooklm"], timeout=60)
        rec("PASS" if r.returncode == 0 else "FAIL", "notebooklm-py python_bin'e kurulu")
    if integ(cfg, "drive"):
        rec("PASS" if Path(integ(cfg, "drive").get("folder_path", "")).is_dir() else "WARN", "Drive klasoru erisilebilir")
    # gizli bilgi
    r = run([pyb, str(root / ".claude" / "scripts" / "kf.py"), "secret-scan"], cwd=root, timeout=120)
    rec("PASS" if r.returncode == 0 else "FAIL", "izlenen dosyalarda gizli bilgi taramasi temiz")
    if r.returncode != 0:
        for line in r.stdout.strip().splitlines()[1:6]:
            print(f"       {line.strip()}")

    fails = sum(1 for s, _ in results if s == "FAIL")
    warns = sum(1 for s, _ in results if s == "WARN")
    print(f"\n{len(results)} kontrol: {fails} FAIL, {warns} WARN")
    return 1 if fails else 0


# ---------------------------------------------------------------- status
def cmd_status(args):
    root = project_root()
    hp = root / ".claude" / "hooks" / "faz_hafiza.py"
    if not hp.exists():
        hp = HERE / "faz_hafiza.py"
    cfg = load_config(root, required=False) or {}
    r = run([python_bin(cfg), str(hp)], cwd=root, env=dict(os.environ, CLAUDE_PROJECT_DIR=str(root)), timeout=30)
    print(r.stdout or r.stderr)
    return 0


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(prog="kf.py", description="Kod Fabrikasi v3 CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="kurulum durumu").set_defaults(fn=cmd_check)

    p = sub.add_parser("init", help="etkilesimsiz kurulum")
    p.add_argument("--name"); p.add_argument("--language", default="tr")
    p.add_argument("--framework", help="flutter|go|php-laravel|python|node|rust|dotnet|none")
    p.add_argument("--test-cmd", action="append", help="tekrarlanabilir")
    p.add_argument("--build-cmd", action="append")
    p.add_argument("--live-cmd", action="append", help="canliya yazan / geri alinamaz komut (ask listesine girer)")
    p.add_argument("--risk", action="append", help="yuksek riskli alan (auth, payments, ...)")
    p.add_argument("--agents", help="istege bagli ajanlar, virgulle: mimar,guvenlik-inceleyici")
    p.add_argument("--expert", action="append", help="alan uzmani: ad:Alan:yol1,yol2:docs_url")
    p.add_argument("--max-parallel", type=int, default=3)
    p.add_argument("--python"); p.add_argument("--graphify")
    p.add_argument("--no-graphify", action="store_true")
    p.add_argument("--drive", help="Google Drive klasoru (bos = kapali)")
    p.add_argument("--notebook", help="NotebookLM notebook id (bos = kapali)")
    p.add_argument("--obsidian", help="Obsidian kasa yolu (bos = kapali)")
    p.add_argument("--force", action="store_true", help="config ve ajanlarin ustune yaz")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("repair", help="eksikleri tamamla")
    p.add_argument("--force-agents", action="store_true", help="ajan dosyalarini sablondan yenile")
    p.set_defaults(fn=cmd_repair)

    p = sub.add_parser("migrate", help="v1/v2 -> v3")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--remove-legacy", action="store_true", help="kokteki eski bundle.py/Makefile/setup-hooks.sh kaldir")
    p.set_defaults(fn=cmd_migrate)

    sub.add_parser("hooks", help="git hook'larini kur").set_defaults(fn=cmd_hooks)

    p = sub.add_parser("secret-scan", help="gizli bilgi taramasi")
    p.add_argument("--staged", action="store_true")
    p.set_defaults(fn=cmd_secret_scan)

    p = sub.add_parser("graphify", help="kod haritasi")
    p.add_argument("--from-hook", action="store_true")
    p.set_defaults(fn=cmd_graphify)

    p = sub.add_parser("bundle", help="paket + Drive + NotebookLM")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_bundle)

    p = sub.add_parser("sync", help="Obsidian")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_sync)

    p = sub.add_parser("end-phase", help="graphify + bundle + sync")
    p.add_argument("--from-hook", action="store_true")
    p.set_defaults(fn=cmd_end_phase)

    sub.add_parser("selftest", help="kurulumu dogrula").set_defaults(fn=cmd_selftest)
    sub.add_parser("status", help="faz hafizasi").set_defaults(fn=cmd_status)

    args = ap.parse_args(argv)
    try:
        return args.fn(args) or 0
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
