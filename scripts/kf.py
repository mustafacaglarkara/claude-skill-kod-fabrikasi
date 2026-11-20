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

# Profil: "yazilim" (varsayilan) | "ajans" (dijital ajans katmani; cekirdek ekip korunur, asagidakiler eklenir)
PROFILES = ("yazilim", "ajans")
# Departmanlar: kurulumun ILK sorusu ("bu kurulum hangi departmanlar icin?"). Hazir olanlar profile donusur,
# planlananlar config'e yazilir; katman yayimlaninca `kf.py repair` ekler. Sira = soru sirasi.
DEPARTMENTS = {
    "yazilim": {"label": "Yazilim gelistirme (cekirdek ekip; her kurulumda var)", "profile": "yazilim", "status": "hazir"},
    "ajans": {"label": "Dijital ajans (musteri, reklam metni, SEO, site denetimi, Cloudflare)", "profile": "ajans", "status": "hazir"},
    "muhasebe": {"label": "Muhasebe / finans (fatura, tahsilat, nakit akisi, butce)", "profile": None, "status": "planlandi (3.2; references/yol-haritasi.md)"},
    "depo": {"label": "Depo / stok yonetimi (stok, siparis, sayim, ERP okuma)", "profile": None, "status": "planlandi (3.4; references/yol-haritasi.md)"},
}


def departments_of(cfg):
    d = (cfg or {}).get("departments")
    if d:
        return [x for x in d if x in DEPARTMENTS]
    return ["yazilim", "ajans"] if is_agency(cfg) else ["yazilim"]


def profile_from_departments(deps):
    return "ajans" if "ajans" in deps else "yazilim"
AGENCY_AGENTS = ["metin-yazari", "marka-denetcisi", "seo-teknisyeni", "rakip-analisti", "site-denetcisi", "cloudflare-operatoru"]
AGENCY_OPTIONAL_AGENTS = ["reklam-stratejisti"]
AGENCY_READ_ONLY = {"marka-denetcisi", "seo-teknisyeni", "rakip-analisti", "site-denetcisi", "cloudflare-operatoru", "reklam-stratejisti"}
AGENCY_SCRIPTS = ["_ortak.py", "cloudflare_ops.py", "site_audit.py", "pagespeed_check.py", "gsc_query.py", "ga4_query.py", "youtube_fetch.py"]
AGENCY_SHARED_FILES = {"copywriting-frameworks.md": "copywriting-frameworks.md", "ad-policies.md": "ad-policies.md"}
AGENCY_CLIENT_FILES = {"README.md": "README.md", "brand-guide.md": "brand-guide.md", "personas.md": "personas.md"}
AGENCY_CLIENT_DIRS = ["campaigns", "content", "seo/reports", "audits", "research", "youtube-research", "infra"]
# Kimlikler ve geri alinamaz Cloudflare islemleri. Yazma komutlari `ask`: --yes olsa bile her seferinde sorulur.
AGENCY_DENY = [
    "Read({{CRED}}/**)", "Read(**/service-account*.json)", "Bash(cat {{CRED}}/*)", "Bash(type {{CRED}}/*)",
    "Bash(*cloudflare_ops.py dns delete*)", "Bash(*cloudflare_ops.py* dns delete*)",
]
AGENCY_ASK = [
    "Bash(*cloudflare_ops.py purge*)", "Bash(*cloudflare_ops.py redirect add*)", "Bash(*cloudflare_ops.py redirect remove*)",
    "Bash(*cloudflare_ops.py dns add*)", "Bash(*cloudflare_ops.py dns update*)", "Bash(*cloudflare_ops.py setting set*)",
    "Bash(*cloudflare_ops.py dev-mode*)", "Bash(*cloudflare_ops.py under-attack*)", "Bash(*cloudflare_ops.py firewall add*)",
    "Bash(*cloudflare_ops.py firewall remove*)", "Bash(wrangler deploy*)", "Bash(wrangler pages deploy*)",
]

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
    """assets/ klasorunu tasiyan skill kopyasini bul (init/migrate/repair/client add icin).
    Sira: bu dosyanin ust klasoru (skill kopyasi) > KF_SKILL_DIR > config.skill_dir (init kaydeder) > ~/.claude/skills/kod-fabrikasi."""
    cands = [HERE.parent]
    if os.environ.get("KF_SKILL_DIR"):
        cands.append(Path(os.environ["KF_SKILL_DIR"]))
    try:
        cfgp = config_path(project_root())
        if cfgp.exists():
            sd = json.loads(cfgp.read_text(encoding="utf-8")).get("skill_dir")
            if sd:
                cands.append(Path(sd))
    except Exception:
        pass
    cands.append(Path.home() / ".claude" / "skills" / "kod-fabrikasi")
    for cand in cands:
        if (cand / "assets" / "agents").is_dir() and (cand / "assets" / "templates").is_dir():
            return cand.resolve()
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


def profile_of(cfg):
    return (cfg or {}).get("profile") or "yazilim"


def is_agency(cfg):
    return profile_of(cfg) == "ajans"


def agency(cfg):
    return (cfg or {}).get("agency") or {}


def default_agency(optional=None, clients=None):
    return {
        "_note": "Dijital ajans profili. clients[]: slug (klasor adi), name, domain, cloudflare_zone, gsc_site (sc-domain:x.com), ga4_property (sayisal), pagespeed_urls[].",
        "clients_dir": "clients",
        "shared_dir": "shared",
        "credentials_dir": ".credentials",
        "agents": list(AGENCY_AGENTS),
        "optional_agents": [a for a in (optional or []) if a in AGENCY_OPTIONAL_AGENTS],
        "clients": list(clients or []),
    }


def parse_client_spec(spec):
    """'slug:Ad:domain[:zone[:gsc_site[:ga4_property]]]' -> dict"""
    parts = [p.strip() for p in spec.split(":")]
    if len(parts) < 3 or not parts[0] or not parts[2]:
        die(f"--client bicimi: slug:Ad:domain[:zone[:gsc_site[:ga4]]] (verilen: {spec})")
    slug = re.sub(r"[^a-z0-9-]", "-", parts[0].lower())
    return {"slug": slug, "name": parts[1] or slug, "domain": parts[2],
            "cloudflare_zone": parts[3] if len(parts) > 3 and parts[3] else parts[2],
            "gsc_site": parts[4] if len(parts) > 4 and parts[4] else f"sc-domain:{parts[2]}",
            "ga4_property": parts[5] if len(parts) > 5 else "",
            "pagespeed_urls": [f"https://{parts[2]}/"]}


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
        with path.open("a", encoding="utf-8", newline="\n") as f:
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
    if cfg:
        deps = departments_of(cfg)
        print("DEPARTMAN  : " + ", ".join(d + ("" if DEPARTMENTS[d]["status"] == "hazir" else " (katman bekliyor)") for d in deps))
        print(f"PROFIL     : {profile_of(cfg)}" + (f" ({len(agency(cfg).get('clients', []))} musteri)" if is_agency(cfg) else ""))
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
    if cfg:
        try:
            inst = installed_plugins()
            rel = [e for e in PLUGIN_CATALOG if plugin_relevant(e, cfg)]
            applied = set((cfg.get("plugins") or {}).get("applied") or [])
            kurulu = [e["id"] for e in rel if e["id"] in inst]
            bekleyen = [i for i in kurulu if i not in applied]
            eksik = [e["id"] for e in rel if e["id"] not in inst]
            print(f"PLUGIN     : uygulanmis {len(applied)} · kurulu-bekleyen {len(bekleyen)}{' (' + ', '.join(bekleyen) + ' -> kf.py plugins --apply)' if bekleyen else ''} · onerilen-eksik {len(eksik)} (kf.py plugins)")
        except Exception as e:
            print(f"PLUGIN     : tespit edilemedi ({e})")


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
    deps = []
    for d in (getattr(args, "department", None) or []):
        for x in d.split(","):
            x = x.strip().lower()
            if x and x not in DEPARTMENTS:
                die(f"bilinmeyen departman: {x} (secenekler: {', '.join(DEPARTMENTS)})")
            if x and x not in deps:
                deps.append(x)
    if "yazilim" not in deps:
        deps.insert(0, "yazilim")
    profile = getattr(args, "profile", None) or profile_from_departments(deps)
    if profile == "ajans" and "ajans" not in deps:
        deps.append("ajans")
    for d in deps:
        if DEPARTMENTS[d]["status"] != "hazir":
            log(f"departman '{d}': katman henuz {DEPARTMENTS[d]['status']}; config'e kaydedildi, yayimlaninca `kf.py repair` ekler.")
    cfg = {
        "_comment": "Kod Fabrikasi v3. Bos/kapali entegrasyon atlanir. Paket yalnizca git'in izledigi dosyalardan olusur.",
        "version": VERSION,
        "project_name": args.name or root.name,
        "language": args.language,
        "departments": deps,
        "profile": profile,
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
    if profile == "ajans":
        opt = (getattr(args, "agency_agents", None) or "").split(",")
        clients = [parse_client_spec(s) for s in (getattr(args, "client", None) or [])]
        cfg["agency"] = default_agency(opt, clients)
    return cfg


def template_ctx(cfg):
    def bullets(items, empty="- (yok)"):
        return "\n".join(f"- `{i}`" for i in items) if items else empty
    ag = cfg.get("agents", {})
    a = agency(cfg)
    ctx = {
        "PROJECT_NAME": cfg.get("project_name", ""),
        "DATE": today(),
        "CLIENTS_DIR": a.get("clients_dir", "clients"),
        "SHARED_DIR": a.get("shared_dir", "shared"),
        "CREDENTIALS_DIR": a.get("credentials_dir", ".credentials"),
        "CLIENT_LIST": ", ".join(f"`{c['slug']}` ({c.get('domain', '')})" for c in a.get("clients", [])) or "(henüz yok)",
        "AGENCY_OPTIONAL_ROWS": "\n".join(filter(None, [
            "| Kampanya planı, kanal/bütçe dağılımı, UTM, test planı | `reklam-stratejisti` (salt okunur; reklam hesabına dokunmaz) |" if "reklam-stratejisti" in a.get("optional_agents", []) else "",
        ])),
        "PROFILE_SECTION": "",
    }
    ctx.update({
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
    })
    if is_agency(cfg):
        sdir = skill_dir()
        tpl = (sdir / "assets" / "templates" / "ajans" / "CLAUDE_SECTION_AJANS.md") if sdir else None
        if tpl and tpl.exists():
            ctx["PROFILE_SECTION"] = render(tpl.read_text(encoding="utf-8"), ctx)
    return ctx


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
    if is_agency(cfg):
        asrc = src / "ajans"
        a = agency(cfg)
        for name in list(a.get("agents", AGENCY_AGENTS)) + list(a.get("optional_agents", [])):
            s = asrc / f"{name}.md"
            d = dst / f"{name}.md"
            if not s.exists():
                log(f"ajans ajan sablonu yok: {name}.md (atlandi)")
                continue
            if d.exists() and not force:
                log(f"ajan korunuyor: {d.relative_to(root).as_posix()}")
                continue
            d.write_text(render(s.read_text(encoding="utf-8"), ctx), encoding="utf-8", newline="\n")
            log(f"ajans ajani yazildi: {d.relative_to(root).as_posix()}")


def client_dir_of(root, cfg, slug):
    return root / agency(cfg).get("clients_dir", "clients") / slug


def install_client_dir(root, cfg, sdir, client):
    """Musteri klasoru: README, brand-guide, personas + alt klasorler (.gitkeep). Mevcut dosyaya dokunmaz."""
    tdir = sdir / "assets" / "templates" / "ajans"
    cdir = client_dir_of(root, cfg, client["slug"])
    cdir.mkdir(parents=True, exist_ok=True)
    ctx = dict(template_ctx(cfg), CLIENT_SLUG=client["slug"], CLIENT_NAME=client.get("name", client["slug"]),
               CLIENT_DOMAIN=client.get("domain", ""), CLOUDFLARE_ZONE=client.get("cloudflare_zone", ""),
               GSC_SITE=client.get("gsc_site", ""), GA4_PROPERTY=client.get("ga4_property", "") or "(yok)")
    for dst_name, tpl_name in AGENCY_CLIENT_FILES.items():
        d = cdir / dst_name
        s = tdir / tpl_name
        if d.exists() or not s.exists():
            continue
        d.write_text(render(s.read_text(encoding="utf-8"), ctx), encoding="utf-8", newline="\n")
        log(f"musteri dosyasi: {d.relative_to(root).as_posix()}")
    for sub in AGENCY_CLIENT_DIRS:
        p = cdir / sub
        p.mkdir(parents=True, exist_ok=True)
        keep = p / ".gitkeep"
        if not any(p.iterdir()):
            keep.write_text("", encoding="utf-8")


def install_agency_workspace(root, cfg, sdir):
    a = agency(cfg)
    tdir = sdir / "assets" / "templates" / "ajans"
    shared = root / a.get("shared_dir", "shared")
    shared.mkdir(parents=True, exist_ok=True)
    ctx = template_ctx(cfg)
    for dst_name, tpl_name in AGENCY_SHARED_FILES.items():
        d = shared / dst_name
        if not d.exists() and (tdir / tpl_name).exists():
            d.write_text(render((tdir / tpl_name).read_text(encoding="utf-8"), ctx), encoding="utf-8", newline="\n")
            log(f"ortak dosya: {d.relative_to(root).as_posix()}")
    cred = root / a.get("credentials_dir", ".credentials")
    cred.mkdir(parents=True, exist_ok=True)
    for dst_name, tpl_name in (("README.md", "credentials-README.md"), ("env.example", "env.example")):
        d = cred / dst_name
        if not d.exists() and (tdir / tpl_name).exists():
            d.write_text(render((tdir / tpl_name).read_text(encoding="utf-8"), ctx), encoding="utf-8", newline="\n")
            log(f"kimlik klasoru: {d.relative_to(root).as_posix()}")
    for c in a.get("clients", []):
        install_client_dir(root, cfg, sdir, c)
    (root / a.get("clients_dir", "clients")).mkdir(parents=True, exist_ok=True)


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


def install_scripts(root, sdir, cfg=None):
    pairs = [
        (sdir / "scripts" / "kf.py", root / ".claude" / "scripts" / "kf.py"),
        (sdir / "scripts" / "faz_hafiza.py", root / ".claude" / "hooks" / "faz_hafiza.py"),
    ]
    if is_agency(cfg):
        pairs += [(sdir / "scripts" / "ajans" / n, root / ".claude" / "scripts" / "ajans" / n) for n in AGENCY_SCRIPTS]
    for s, d in pairs:
        if not s.exists():
            log(f"betik sablonu yok: {s.name} (atlandi)")
            continue
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
    if is_agency(cfg):
        cred = agency(cfg).get("credentials_dir", ".credentials")
        for rule in AGENCY_DENY:
            rule = rule.replace("{{CRED}}", cred)
            if rule not in deny:
                deny.append(rule)
        for rule in AGENCY_ASK:
            if rule not in ask:
                ask.append(rule)
    hooks = data.setdefault("hooks", {})
    ss = hooks.setdefault("SessionStart", [])
    hook_cmd = f'"{python_bin(cfg)}" "$CLAUDE_PROJECT_DIR/.claude/hooks/faz_hafiza.py"'
    if not any("faz_hafiza.py" in json.dumps(g) for g in ss):
        ss.append({"matcher": "startup|resume|clear|compact",
                   "hooks": [{"type": "command", "command": hook_cmd, "timeout": 15}]})
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    log("settings.json birlestirildi (deny: .env/pem/key" + ("/.credentials/dns delete" if is_agency(cfg) else "") + ", ask: push/reset/canli komutlar"
        + ("/cloudflare yazma" if is_agency(cfg) else "") + ", SessionStart hook)")


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
    install_scripts(root, sdir, cfg)
    merge_settings(root, cfg)
    gi_lines = list(GITIGNORE_LINES)
    if is_agency(cfg):
        cred = agency(cfg).get("credentials_dir", ".credentials").strip("/")
        # `{cred}/*` (klasor degil): git, haric tutulan klasorun icinden dosya geri alamaz; README ve env.example izlensin
        gi_lines += [f"{cred}/*", f"!{cred}/README.md", f"!{cred}/env.example", "*service-account*.json"]
        install_agency_workspace(root, cfg, sdir)
    ensure_lines(root / ".gitignore", gi_lines, ".gitignore")
    ga = root / ".gitattributes"
    if not ga.exists():
        ga.write_text("* text=auto eol=lf\n*.png binary\n*.jpg binary\n*.webp binary\n*.pdf binary\n*.ico binary\n", encoding="utf-8", newline="\n")
        log(".gitattributes olusturuldu (LF)")
    if integ(cfg, "graphify"):
        install_graphify_files(root, sdir)
    install_claude_md(root, cfg, sdir)


def print_next_steps(root, cfg):
    py = python_bin(cfg)
    py = f'"{py}"' if " " in py else py
    print("\nSonraki adimlar:")
    if not (root / ".git").exists():
        print("  1. git init -b main            # once git; Drive/Obsidian surum kontrolu degildir")
    print(f"  - {py} .claude/scripts/kf.py hooks      # pre-commit (gizli bilgi) + post-commit (end-phase)")
    print(f"  - {py} .claude/scripts/kf.py selftest   # kurulumu dogrula")
    if integ(cfg, "graphify"):
        print(f"  - {cfg.get('graphify_bin', 'graphify')} update .   # ilk kod haritasi (sonra: graphify install --project istege bagli)")
    print("  - Ajanlar birkac saniye icinde yuklenir (hot reload). 'Agent type not found' gorursen yeni oturum ac.")
    if is_agency(cfg):
        cred = agency(cfg).get("credentials_dir", ".credentials")
        print(f"  - {cred}/env.example -> {cred}/.env (Cloudflare token, PageSpeed/YouTube key, service-account.json). Claude bu klasoru okuyamaz.")
        print(f"  - Musteri ekle: {py} .claude/scripts/kf.py client add --slug musteri-a --name \"Musteri A\" --domain musteri-a.com")
        print(f"  - Site denetimi: {py} .claude/scripts/ajans/site_audit.py --client musteri-a --crawl 10 --links")
        print("  - pip install certifi google-auth google-api-python-client google-analytics-data youtube-transcript-api (gerektikce)")
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
    cfg["skill_dir"] = str(sdir)   # proje kopyasindaki kf.py (client add, repair) sablonlari buradan bulur
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
    if cfg.get("skill_dir") != str(sdir):
        cfg["skill_dir"] = str(sdir)
        save_config(root, cfg)
    run_install(root, cfg, sdir, force_agents=args.force_agents)
    log("repair tamam.")
    return 0


# ---------------------------------------------------------------- profile / client (ajans)
def cmd_profile(args):
    """Mevcut v3 projeyi baska profile gecirir (ajans: ajanlar + betikler + calisma alani + settings eklenir)."""
    root = project_root()
    sdir = skill_dir()
    if not sdir:
        die("skill kopyasi bulunamadi (assets/ yok).")
    cfg = load_config(root)
    if cfg.get("version") != VERSION:
        die(f"config v{cfg.get('version', 1)}. Once: kf.py migrate")
    cfg["profile"] = args.profile
    deps = departments_of(cfg)
    if args.profile == "ajans" and "ajans" not in deps:
        deps.append("ajans")
    if args.profile == "yazilim" and "ajans" in deps:
        deps.remove("ajans")
    cfg["departments"] = deps
    if args.profile == "ajans" and not cfg.get("agency"):
        cfg["agency"] = default_agency((args.agency_agents or "").split(","), [parse_client_spec(s) for s in (args.client or [])])
    elif args.profile == "ajans":
        for s in args.client or []:
            c = parse_client_spec(s)
            if not any(x["slug"] == c["slug"] for x in cfg["agency"].setdefault("clients", [])):
                cfg["agency"]["clients"].append(c)
        for a in (args.agency_agents or "").split(","):
            if a in AGENCY_OPTIONAL_AGENTS and a not in cfg["agency"].setdefault("optional_agents", []):
                cfg["agency"]["optional_agents"].append(a)
    save_config(root, cfg)
    log(f"profil = {args.profile}")
    run_install(root, cfg, sdir)
    if args.profile == "yazilim":
        log("not: ajans ajanlari/betikleri silinmedi (elle kaldir: .claude/agents/<ajans ajanlari>.md, .claude/scripts/ajans/).")
    print_next_steps(root, cfg)
    return 0


def cmd_client(args):
    root = project_root()
    cfg = load_config(root)
    if not is_agency(cfg):
        die("profil 'ajans' degil. Once: kf.py profile ajans")
    a = cfg.setdefault("agency", default_agency())
    clients = a.setdefault("clients", [])
    if args.op == "list":
        if not clients:
            print("(musteri yok) -> kf.py client add --slug x --name \"X\" --domain x.com")
            return 0
        for c in clients:
            d = client_dir_of(root, cfg, c["slug"])
            print(f"{c['slug']:<20} {c.get('name', ''):<24} {c.get('domain', ''):<28} zone={c.get('cloudflare_zone', '-')} gsc={c.get('gsc_site', '-')} ga4={c.get('ga4_property') or '-'} {'' if d.is_dir() else '(klasor YOK: repair)'}")
        return 0
    if args.op == "add":
        if not (args.slug and args.domain):
            die("client add --slug <slug> --name \"<Ad>\" --domain <alanadi> [--zone] [--gsc] [--ga4] [--url ...]")
        spec = parse_client_spec(f"{args.slug}:{args.name or args.slug}:{args.domain}:{args.zone or ''}:{args.gsc or ''}:{args.ga4 or ''}")
        if args.url:
            spec["pagespeed_urls"] = list(args.url)
        if any(c["slug"] == spec["slug"] for c in clients):
            die(f"musteri zaten var: {spec['slug']} (config'i elle duzenle ya da client remove)")
        clients.append(spec)
        save_config(root, cfg)
        sdir = skill_dir()
        if sdir:
            install_client_dir(root, cfg, sdir, spec)
            install_claude_md(root, cfg, sdir)
        else:
            log("skill kopyasi yok; musteri klasoru sablonsuz acildi. Sonra: kf.py repair")
            client_dir_of(root, cfg, spec["slug"]).mkdir(parents=True, exist_ok=True)
        log(f"musteri eklendi: {spec['slug']} ({spec['domain']}) -> {client_dir_of(root, cfg, spec['slug']).relative_to(root).as_posix()}/")
        print("Sonraki: brand-guide.md ve personas.md doldur; Cloudflare token bu zone'u goruyor mu: "
              f"python .claude/scripts/ajans/cloudflare_ops.py check --client {spec['slug']}")
        return 0
    if args.op == "remove":
        before = len(clients)
        a["clients"] = [c for c in clients if c["slug"] != args.slug]
        if len(a["clients"]) == before:
            die(f"musteri yok: {args.slug}")
        save_config(root, cfg)
        sdir = skill_dir()
        if sdir:
            install_claude_md(root, cfg, sdir)
        log(f"config'ten cikarildi: {args.slug}. Klasor SILINMEDI ({client_dir_of(root, cfg, args.slug).relative_to(root).as_posix()}/); arsivlemek sana kalmis.")
        return 0
    return 0


# ---------------------------------------------------------------- plugins (guclendirme)
PLUG_MARK = "<!-- kf:plugins:start -->"
PLUG_MARK_END = "<!-- kf:plugins:end -->"
OFFICIAL = "claude-plugins-official"
# Katalog: Anthropic'in yayimladigi plugin'ler (resmi marketplace ya da claude.ai Plugin Dizini) -> hangi ajan hangi skill'i ne zaman cagirir.
# market: official (claude plugin install <id>@claude-plugins-official) | synced (claude.ai -> Ayarlar -> Plugin'ler; terminalde <id>@synced)
# seviye: agents (alt ajan Skill araciyla cagirir) | orchestrator (ana oturum; ajan baslatan skill'ler) | env (kurulu olmasi yeter: LSP, hook)
PLUGIN_CATALOG = [
    {"id": "typescript-lsp", "market": "official", "profile": "her ikisi", "frameworks": ["node"], "env": True,
     "why": "TS/JS kod zekasi: tanim/referans, tip hatalari (kesifci, gelistirici, tester daha az arama yapar)"},
    {"id": "pyright-lsp", "market": "official", "profile": "her ikisi", "frameworks": ["python"], "env": True, "why": "Python tip denetimi ve kod zekasi"},
    {"id": "gopls-lsp", "market": "official", "profile": "her ikisi", "frameworks": ["go"], "env": True, "why": "Go kod zekasi"},
    {"id": "php-lsp", "market": "official", "profile": "her ikisi", "frameworks": ["php-laravel"], "env": True, "why": "PHP (Intelephense) kod zekasi"},
    {"id": "rust-analyzer-lsp", "market": "official", "profile": "her ikisi", "frameworks": ["rust"], "env": True, "why": "Rust kod zekasi"},
    {"id": "csharp-lsp", "market": "official", "profile": "her ikisi", "frameworks": ["dotnet"], "env": True, "why": "C# kod zekasi"},
    {"id": "security-guidance", "market": "official", "profile": "her ikisi", "env": True,
     "why": "Her duzenlemede guvenlik kalip uyarisi + Stop'ta diff incelemesi; gelistirici'nin isine otomatik eslik eder (hook tabanli)"},
    {"id": "pr-review-toolkit", "market": "official", "profile": "her ikisi",
     "why": "6 uzman inceleme ajani (sessiz hata, test, tip tasarimi, yorum, kalite)",
     "orchestrator": [("/pr-review-toolkit:review-pr", "Adim 5'te reviewer ile PARALEL ikinci goz; bulgular yine koda bakilarak teyit edilir")]},
    {"id": "claude-security", "market": "official", "profile": "her ikisi",
     "why": "Derin zafiyet taramasi; her bulgu dogrulanir",
     "orchestrator": [("/claude-security:claude-security", "Yuksek riskli alan dokunan fazda guvenlik-inceleyici'den ONCE; raporu brife ekle")]},
    {"id": "feature-dev", "market": "official", "profile": "her ikisi",
     "why": "Kesif + mimari + inceleme ajanlariyla ozellik gelistirme akisi",
     "orchestrator": [("/feature-dev:feature-dev", "Buyuk ozellikte Adim 1-2 alternatifi (kesif + tasarim); cikan plan yine kullanici ONAY'ina gelir, uygulama gelistirici ile")]},
    {"id": "frontend-design", "market": "official", "profile": "her ikisi",
     "why": "Jenerik AI gorunumunden uzak, uretim kalitesinde arayuz",
     "agents": {"gelistirici": [("/frontend-design:frontend-design", "UI / sayfa / komponent / landing page isinde, kod yazmadan once")]}},
    {"id": "claude-md-management", "market": "official", "profile": "her ikisi",
     "why": "CLAUDE.md kalite denetimi ve sadelestirme",
     "orchestrator": [("/claude-md-management:revise-claude-md", "CLAUDE.md 200 satiri astiginda ya da oturum ogrenimlerini isleyerken (isaretli kod-fabrikasi bolumune dokunma)")]},
    {"id": "engineering", "market": "synced", "profile": "her ikisi",
     "why": "Anthropic 'knowledge work' muhendislik skill'leri: mimari, sistem tasarimi, hata ayiklama, test stratejisi, dagitim kontrol listesi",
     "agents": {"mimar": [("/engineering:architecture", "tasarim karari / ADR adayi uretirken"), ("/engineering:system-design", "yeni servis / veri akisi tasarlarken"), ("/engineering:debug", "kok neden analizinde")],
                "tester": [("/engineering:testing-strategy", "brifte 'eksik test onerisi' istendiginde; test yazmazsin, oneri uretirsin")]},
     "orchestrator": [("/engineering:deploy-checklist", "canliya yazan komut / deploy oncesi (kullanici isterse)")]},
    {"id": "coding-skills", "market": "synced", "profile": "her ikisi",
     "why": "Kod incelemesini gecip uretimde patlayan hatalar (write skew, idempotency, zaman dilimi, coordinated omission)",
     "agents": {"gelistirici": [("/coding-skills:<ilgili-skill>", "eszamanlilik, idempotency, zaman/tarih, yeniden deneme dokunan iste; once `coding-skills` skill listesine bak")],
                "reviewer": [("/coding-skills:<ilgili-skill>", "diff eszamanlilik / veri tutarliligi iceriyorsa kontrol listesi olarak")]}},
    {"id": "backend-design", "market": "synced", "profile": "her ikisi",
     "why": "Kidemli backend reflexleri: API, veri modeli, servis sinirlari",
     "agents": {"mimar": [("/backend-design:<ilgili-skill>", "API / servis / veri modeli tasarlarken")]}},
    {"id": "searchfit-seo", "market": "synced", "profile": "ajans",
     "why": "SEO araci seti (SearchFit; Anthropic katalogunda): teknik SEO, on-page, schema, ic baglanti, anahtar kelime kumeleme, icerik stratejisi, AI gorunurlugu",
     "agents": {"seo-teknisyeni": [("/searchfit-seo:technical-seo", "betik bulgularini derinlestirip aksiyona cevirirken"), ("/searchfit-seo:on-page-seo", "tek sayfa optimizasyon onerisinde"),
                                   ("/searchfit-seo:schema-markup", "JSON-LD eksiginde hazir sema uretmek icin"), ("/searchfit-seo:internal-linking", "ic baglanti / yetim sayfa analizinde"),
                                   ("/searchfit-seo:keyword-clustering", "GSC sorgu listesini kumelerken")],
                "site-denetcisi": [("/searchfit-seo:seo-audit", "site_audit.py raporuna ek kontrol listesi olarak (ayni siteyi tekrar tarama)"), ("/searchfit-seo:broken-links", "kirik baglanti bulgusunu siniflarken")],
                "rakip-analisti": [("/searchfit-seo:content-strategy", "icerik boslugu tablosundan plan cikarirken"), ("/searchfit-seo:content-brief", "ilk 3 icerik onerisini brife cevirirken"), ("/searchfit-seo:ai-visibility", "markanin AI cevaplarinda gorunurlugu sorulursa")],
                "metin-yazari": [("/searchfit-seo:content-brief", "blog / SEO icerigi yazmadan once brif yoksa")]},
     "orchestrator": [("searchfit-seo:competitor-analyzer (ajan)", "rakip-analisti ile paralel ikinci goz; cikti yine musteri klasorune, slug izolasyonu brife yazilir")]},
    {"id": "marketing", "market": "synced", "profile": "ajans",
     "why": "Anthropic 'knowledge work' pazarlama skill'leri: icerik, kampanya plani, marka incelemesi, e-posta dizisi, performans raporu",
     "agents": {"metin-yazari": [("/marketing:content-creation", "uzun icerik / blog"), ("/marketing:draft-content", "sosyal / reklam varyantlari"), ("/marketing:email-sequence", "e-posta dizisi")],
                "marka-denetcisi": [("/marketing:brand-review", "marka tonu denetiminde ikinci kontrol listesi; karar yine senin")],
                "reklam-stratejisti": [("/marketing:campaign-plan", "kampanya plani iskeleti"), ("/marketing:competitive-brief", "rakip ozeti"), ("/marketing:performance-report", "kampanya sonuc raporu")],
                "seo-teknisyeni": [("/marketing:performance-report", "aylik rapor formati icin")]}},
    {"id": "cloudflare", "market": "synced", "profile": "ajans",
     "why": "Cloudflare platform rehberi skill'leri (workers, wrangler, web-perf) + resmi Cloudflare MCP sunucusu",
     "agents": {"cloudflare-operatoru": [("/cloudflare:cloudflare", "ayar / urun sorusunda resmi rehber"), ("/cloudflare:web-perf", "cache / CWV iyilestirme onerisinde"), ("/cloudflare:wrangler", "Pages/Workers dagitim durumu sorusunda")],
                "gelistirici": [("/cloudflare:frameworks-on-cloudflare", "site Pages/Workers'a dagitilacaksa"), ("/cloudflare:workers-best-practices", "Worker kodu yazarken")]},
     "settings_ask": ["mcp__plugin_cloudflare_cloudflare", "mcp__cloudflare"],
     "note": "MCP sunucusu yazma da yapabilir: operatör MCP ile yalnizca okur, yazma yalnizca cloudflare_ops.py (--yes). settings ask kurali eklenir."},
    {"id": "website-design", "market": "synced", "profile": "ajans",
     "why": "Gercek sitelerden tasarim yonu secen landing page akisi (UXKIN; Anthropic dizininde)",
     "agents": {"gelistirici": [("/website-design:<ilgili-skill>", "landing page / site tasarimina baslarken DESIGN.md uretmek icin")]}},
]


def installed_plugins():
    """{kisa_ad: {"id":..., "scope":..., "enabled":...}}. Once `claude plugin list --json`, olmazsa dosyalardan."""
    found = {}
    exe = shutil.which("claude")
    if exe:
        try:
            r = run([exe, "plugin", "list", "--json"], timeout=60)
            if r.returncode == 0 and r.stdout.strip().startswith("["):
                for p in json.loads(r.stdout):
                    pid = p.get("id", "")
                    found[pid.split("@")[0]] = {"id": pid, "scope": p.get("scope", "?"), "enabled": p.get("enabled", True)}
                return found
        except Exception:
            pass
    reg = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    try:
        for pid in (json.loads(reg.read_text(encoding="utf-8")).get("plugins") or {}):
            found[pid.split("@")[0]] = {"id": pid, "scope": "user", "enabled": True}
    except Exception:
        pass
    for sdir_ in (Path.home() / ".claude" / "plugins" / "synced").glob("*/"):
        for d in sdir_.iterdir():
            if not d.is_dir():
                continue
            pj = d / ".claude-plugin" / "plugin.json"
            if pj.exists():
                try:
                    name = json.loads(pj.read_text(encoding="utf-8")).get("name") or d.name
                except Exception:
                    name = d.name
                name = name.split("~")[0]
                found.setdefault(name, {"id": f"{name}@synced", "scope": "synced", "enabled": True})
    return found


def plugin_relevant(entry, cfg):
    prof = profile_of(cfg)
    if entry.get("profile") not in ("her ikisi", prof):
        return False
    fw = entry.get("frameworks")
    if fw and (cfg.get("framework") or "none") not in fw:
        return False
    return True


DIRECTORY = "anthropic-plugin-directory"   # claude.ai Plugin Dizini; Claude Code'da yerlesik marketplace


def plugin_spec(entry):
    return f"{entry['id']}@{OFFICIAL if entry['market'] == 'official' else DIRECTORY}"


def plugin_install_hint(entry):
    return f"kf.py plugins --install --only {entry['id']}   (= claude plugin install {plugin_spec(entry)})"


def install_plugins(entries, scope="user"):
    """`claude plugin install` ile kurar; (kurulan, basarisiz) listeleri dondurur. Etkilesimsiz (-y --json)."""
    exe = shutil.which("claude")
    if not exe:
        die("claude CLI PATH'te yok; plugin kurulamaz. Elle: claude plugin install <id>@<marketplace>")
    r = run([exe, "plugin", "marketplace", "list"], timeout=60)
    if OFFICIAL not in (r.stdout or ""):
        log(f"marketplace ekleniyor: {OFFICIAL}")
        run([exe, "plugin", "marketplace", "add", "anthropics/claude-plugins-official"], timeout=180)
    ok, bad = [], []
    for e in entries:
        spec = plugin_spec(e)
        log(f"kuruluyor: {spec} (scope {scope})")
        r = run([exe, "plugin", "install", spec, "--scope", scope, "-y", "--json"], timeout=600)
        out = (r.stdout or "").strip().splitlines()
        res = {}
        for line in reversed(out):
            if line.startswith("{"):
                try:
                    res = json.loads(line)
                except json.JSONDecodeError:
                    pass
                break
        if r.returncode == 0 and not res.get("error"):
            ok.append(e["id"])
        else:
            msg = res.get("error") or res.get("message") or (r.stderr or r.stdout or "").strip()[-300:]
            bad.append((e["id"], msg))
            log(f"KURULAMADI {spec}: {msg}")
            if e["market"] == "synced":
                log(f"  alternatif: claude.ai -> Ayarlar -> Plugin'ler -> Dizin'den '{e['id']}' yukle (terminalde {e['id']}@synced)")
    return ok, bad


def plugin_block_for_agent(agent, entries):
    lines = []
    for e in entries:
        for skill, when in (e.get("agents") or {}).get(agent, []):
            lines.append(f"- `{skill}` — {when}")
    if not lines:
        return ""
    return (f"{PLUG_MARK}\n## Güçlendirmeler (kurulu plugin skill'leri)\n\n"
            "Brif gerektirdiğinde şu skill'leri `Skill` aracıyla çağır; skill yoksa ya da hata verirse normal akışla devam et. "
            "Skill çıktısı öneri niteliğindedir: bu dosyadaki kurallar (yazma sınırı, salt okunurluk, rapor formatı) her zaman üstündür. Başka ajan başlatan skill çağırma.\n\n"
            + "\n".join(lines) + f"\n{PLUG_MARK_END}\n")


def set_agent_plugin_block(path: Path, block):
    """Isaretli blogu ekler/gunceller/siler ve `Skill` aracini tools'a ekler/cikarir. Degisiklik olduysa True."""
    text = path.read_text(encoding="utf-8")
    orig = text
    if PLUG_MARK in text:
        text = re.sub(re.escape(PLUG_MARK) + r".*?" + re.escape(PLUG_MARK_END) + r"\n?", block, text, flags=re.S)
    elif block:
        if "\n## Verimli çalış" in text:
            text = text.replace("\n## Verimli çalış", "\n" + block + "\n## Verimli çalış", 1)
        else:
            text = text.rstrip("\n") + "\n\n" + block
    m = re.search(r"^tools:\s*(.*)$", text, re.M)
    if m:
        tools = [t.strip() for t in m.group(1).strip("[]").split(",") if t.strip()]
        if block and "Skill" not in tools:
            tools.append("Skill")
        if not block and "Skill" in tools:
            tools.remove("Skill")
        text = text[:m.start()] + "tools: " + ", ".join(tools) + text[m.end():]
    if text != orig:
        path.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def set_marked_block(path: Path, block, title_hint=""):
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    orig = text
    if PLUG_MARK in text:
        text = re.sub(re.escape(PLUG_MARK) + r".*?" + re.escape(PLUG_MARK_END) + r"\n?", block, text, flags=re.S)
    elif block:
        text = text.rstrip("\n") + "\n\n" + block
    if text != orig:
        path.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def cmd_plugins(args):
    root = project_root()
    cfg = load_config(root)
    inst = installed_plugins()
    relevant = [e for e in PLUGIN_CATALOG if plugin_relevant(e, cfg)]
    agents_installed = {p.stem for p in (root / ".claude" / "agents").glob("*.md")}
    applied = set((cfg.get("plugins") or {}).get("applied") or [])

    if args.remove:
        n = 0
        for p in (root / ".claude" / "agents").glob("*.md"):
            n += set_agent_plugin_block(p, "")
        set_marked_block(root / phase_files(cfg)["faz_prompt"], "")
        cfg["plugins"] = {"applied": [], "skill_tool_added_to": []}
        save_config(root, cfg)
        log(f"guclendirme bloklari kaldirildi ({n} ajan dosyasi). settings.json ask kurallari elle kaldirilabilir (mcp__cloudflare...).")
        return 0

    if args.install:
        want = {s.strip() for s in args.only.split(",")} if args.only else {e["id"] for e in relevant}
        targets = [e for e in relevant if e["id"] in want and e["id"] not in inst]
        unknown = want - {e["id"] for e in relevant}
        if unknown:
            log(f"katalogda/profilde yok, atlandi: {', '.join(sorted(unknown))}")
        if not targets:
            log("kurulacak yeni plugin yok (hepsi kurulu ya da secim bos).")
        else:
            ok, bad = install_plugins(targets, scope=args.scope)
            log(f"kuruldu: {', '.join(ok) or '-'}" + (f" | basarisiz: {', '.join(b for b, _ in bad)}" if bad else ""))
            inst = installed_plugins()
        args.apply = True
        args.only = None   # kurulu olan tum ilgili plugin'ler uygulanir

    rows = []
    to_apply = []
    for e in relevant:
        st = inst.get(e["id"])
        if st and not st.get("enabled", True):
            durum = "kurulu (DEVRE DISI)"
        elif st:
            durum = "uygulanmis" if e["id"] in applied else "kurulu"
            to_apply.append(e)
        else:
            durum = "yok"
        targets = sorted((e.get("agents") or {}).keys())
        if e.get("orchestrator"):
            targets.append("ana oturum")
        if e.get("env"):
            targets.append("ortam")
        rows.append((e["id"], e["market"], durum, ", ".join(targets), e["why"], plugin_install_hint(e)))

    if args.apply:
        if args.only:
            want = {s.strip() for s in args.only.split(",")}
            to_apply = [e for e in to_apply if e["id"] in want]
        changed = []
        for agent in sorted(agents_installed):
            block = plugin_block_for_agent(agent, to_apply)
            if set_agent_plugin_block(root / ".claude" / "agents" / f"{agent}.md", block):
                changed.append(agent)
        orch = [(e["id"], s, w) for e in to_apply for s, w in (e.get("orchestrator") or [])]
        env = [(e["id"], e["why"]) for e in to_apply if e.get("env")]
        oblock = ""
        if orch or env:
            oblock = f"{PLUG_MARK}\n## Güçlendirmeler (ana oturum; `kf.py plugins --apply` yazdı)\n\n"
            if orch:
                oblock += "Kurulu plugin skill'leri; ilgili adımda çağır, çıktıyı yine koda bakarak teyit et:\n\n" + "\n".join(f"- `{s}` ({pid}) — {w}" for pid, s, w in orch) + "\n"
            if env:
                oblock += "\nOrtam plugin'leri (otomatik çalışır): " + ", ".join(f"`{pid}` ({w})" for pid, w in env) + "\n"
            oblock += PLUG_MARK_END + "\n"
        set_marked_block(root / phase_files(cfg)["faz_prompt"], oblock)
        asks = [r for e in to_apply for r in (e.get("settings_ask") or [])]
        if asks:
            sp = root / ".claude" / "settings.json"
            try:
                s = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
                ask = s.setdefault("permissions", {}).setdefault("ask", [])
                added = [r for r in asks if r not in ask]
                ask.extend(added)
                if added:
                    sp.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
                    log(f"settings ask eklendi: {', '.join(added)}")
            except json.JSONDecodeError as e:
                log(f"settings.json bozuk ({e}); ask kurali eklenmedi")
        cfg["plugins"] = {"applied": sorted(e["id"] for e in to_apply),
                          "skill_tool_added_to": sorted(a for a in agents_installed if plugin_block_for_agent(a, to_apply))}
        save_config(root, cfg)
        log(f"uygulandi: {', '.join(cfg['plugins']['applied']) or '(kurulu ilgili plugin yok)'}; ajan dosyasi guncellendi: {', '.join(changed) or '-'}")
        if any(e.get("note") for e in to_apply):
            for e in to_apply:
                if e.get("note"):
                    log(f"NOT {e['id']}: {e['note']}")
        log("ajan dosyalari degisti: Claude Code birkac saniyede yeniden yukler; olmazsa yeni oturum.")
        return 0

    print(f"Profil: {profile_of(cfg)} · framework: {cfg.get('framework')} · kurulu plugin: {len(inst)}\n")
    w = max(len(r[0]) for r in rows) if rows else 10
    for pid, market, durum, targets, why, hint in rows:
        print(f"{pid:<{w}}  {market:<8}  {durum:<20}  -> {targets}")
        print(f"{'':<{w}}  {why}")
        if durum == "yok":
            print(f"{'':<{w}}  kur: {hint}")
    missing = [r for r in rows if r[2] == "yok"]
    ready = [r for r in rows if r[2] == "kurulu"]
    print(f"\n{len(rows)} oneri: {len(ready)} kurulu/uygulanmamis, {len([r for r in rows if r[2] == 'uygulanmis'])} uygulanmis, {len(missing)} yok.")
    if ready:
        print("Uygula: python .claude/scripts/kf.py plugins --apply   (ajan dosyalarina 'Guclendirmeler' blogu + Skill araci)")
    if missing:
        print(f"Kur + uygula: python .claude/scripts/kf.py plugins --install --only {','.join(r[0] for r in missing)}   (secimi kisalt)")
    print("Kaldir: python .claude/scripts/kf.py plugins --remove")
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
    if is_agency(cfg):
        expected += list(agency(cfg).get("agents", AGENCY_AGENTS)) + list(agency(cfg).get("optional_agents", []))
    for name in expected:
        p = adir / f"{name}.md"
        if not p.exists():
            rec("FAIL", f"ajan dosyasi yok: {name}.md")
            continue
        fm, body = read_frontmatter(p)
        ok = fm.get("name") == name and bool(fm.get("description"))
        rec("PASS" if ok else "FAIL", f"ajan {name}: name/description")
        tools = {t.strip() for t in fm.get("tools", "").strip("[]").split(",") if t.strip()}
        ro = name in READ_ONLY_AGENTS or name in AGENCY_READ_ONLY or name in [e["name"] for e in ag.get("domain_experts", [])]
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
    # departmanlar
    for d in departments_of(cfg):
        st = DEPARTMENTS[d]["status"]
        rec("PASS" if st == "hazir" else "WARN", f"departman {d}: " + ("katman kurulu" if st == "hazir" else f"katman {st}"))
    # plugin guclendirmeleri
    pl = cfg.get("plugins") or {}
    if pl.get("applied"):
        inst = installed_plugins()
        for pid in pl["applied"]:
            rec("PASS" if pid in inst and inst[pid].get("enabled", True) else "WARN", f"plugin uygulanmis ve kurulu: {pid}" + ("" if pid in inst else " (kaldirilmis; kf.py plugins --apply ile yenile)"))
        for name in pl.get("skill_tool_added_to", []):
            p = adir / f"{name}.md"
            if p.exists():
                fm, body = read_frontmatter(p)
                rec("PASS" if "Skill" in fm.get("tools", "") and PLUG_MARK in body else "WARN", f"ajan {name}: guclendirme blogu + Skill araci")
    # ajans profili
    if is_agency(cfg):
        a = agency(cfg)
        cred = a.get("credentials_dir", ".credentials").strip("/")
        for n in AGENCY_SCRIPTS:
            rec("PASS" if (root / ".claude" / "scripts" / "ajans" / n).exists() else "FAIL", f"ajans betigi: .claude/scripts/ajans/{n}")
        rec("PASS" if (f"{cred}/*" in gl or f"{cred}/" in gl) else "FAIL", f".gitignore: {cred}/*")
        r = run(["git", "ls-files", cred], cwd=root)
        tracked_cred = [f for f in r.stdout.splitlines() if f and not f.endswith(("README.md", "env.example"))]
        rec("PASS" if not tracked_cred else "FAIL", f"{cred}/ icinde git'in izledigi sir yok" + (f": {', '.join(tracked_cred)}" if tracked_cred else ""))
        if sp.exists():
            try:
                s = json.loads(sp.read_text(encoding="utf-8"))
                deny = (s.get("permissions") or {}).get("deny") or []
                ask = (s.get("permissions") or {}).get("ask") or []
                rec("PASS" if any(cred in d for d in deny) else "FAIL", f"settings deny: {cred}/")
                rec("PASS" if any("dns delete" in d for d in deny) else "FAIL", "settings deny: cloudflare dns delete")
                rec("PASS" if any("cloudflare_ops.py purge" in x for x in ask) else "FAIL", "settings ask: cloudflare purge/yazma")
            except json.JSONDecodeError:
                pass
        for d in (a.get("shared_dir", "shared"), a.get("clients_dir", "clients")):
            rec("PASS" if (root / d).is_dir() else "FAIL", f"klasor: {d}/")
        for c in a.get("clients", []):
            cd = client_dir_of(root, cfg, c["slug"])
            rec("PASS" if (cd / "brand-guide.md").exists() else "FAIL", f"musteri {c['slug']}: brand-guide.md")
            rec("PASS" if c.get("domain") else "WARN", f"musteri {c['slug']}: domain")
        rec("PASS" if run([pyb, "-c", "import certifi"], timeout=60).returncode == 0 else "WARN", "certifi kurulu (TLS kok sertifikalari; pip install certifi)")
        rec("PASS" if (root / cred / ".env").exists() else "WARN", f"{cred}/.env var (Cloudflare/Google anahtarlari)")
        rec("PASS" if (root / cred / "service-account.json").exists() else "WARN", f"{cred}/service-account.json var (GSC/GA4)")
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
    p.add_argument("--department", action="append", help="kurulumun ilk sorusu: yazilim | ajans | muhasebe | depo (tekrarlanabilir ya da virgulle; hazir olanlar profile donusur)")
    p.add_argument("--profile", choices=PROFILES, default=None, help="(eski) yazilim | ajans; verilmezse --department'tan turetilir")
    p.add_argument("--client", action="append", help="ajans: slug:Ad:domain[:zone[:gsc_site[:ga4]]] (tekrarlanabilir)")
    p.add_argument("--agency-agents", help="ajans istege bagli ajanlar, virgulle: reklam-stratejisti")
    p.add_argument("--force", action="store_true", help="config ve ajanlarin ustune yaz")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("repair", help="eksikleri tamamla")
    p.add_argument("--force-agents", action="store_true", help="ajan dosyalarini sablondan yenile")
    p.set_defaults(fn=cmd_repair)

    p = sub.add_parser("migrate", help="v1/v2 -> v3")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--remove-legacy", action="store_true", help="kokteki eski bundle.py/Makefile/setup-hooks.sh kaldir")
    p.set_defaults(fn=cmd_migrate)

    p = sub.add_parser("profile", help="profil degistir: yazilim | ajans (mevcut v3 projeye ajans katmani ekler)")
    p.add_argument("profile", choices=PROFILES)
    p.add_argument("--client", action="append", help="slug:Ad:domain[:zone[:gsc_site[:ga4]]]")
    p.add_argument("--agency-agents", help="reklam-stratejisti")
    p.set_defaults(fn=cmd_profile)

    p = sub.add_parser("client", help="ajans musterileri: list | add | remove")
    p.add_argument("op", choices=["list", "add", "remove"])
    p.add_argument("--slug"); p.add_argument("--name"); p.add_argument("--domain")
    p.add_argument("--zone", help="Cloudflare zone (varsayilan domain)"); p.add_argument("--gsc", help="sc-domain:x.com ya da https://x.com/")
    p.add_argument("--ga4", help="GA4 property id"); p.add_argument("--url", action="append", help="PageSpeed icin URL (tekrarlanabilir)")
    p.set_defaults(fn=cmd_client)

    p = sub.add_parser("plugins", help="onerilen Anthropic plugin'leri: listele | --apply (ajanlara entegre et) | --remove")
    p.add_argument("--apply", action="store_true", help="kurulu ve ilgili plugin'leri ajan dosyalarina isle")
    p.add_argument("--install", action="store_true", help="eksik onerilen plugin'leri `claude plugin install` ile kur (--only ile sec), sonra --apply")
    p.add_argument("--scope", choices=["user", "project", "local"], default="user", help="--install kapsami (varsayilan user)")
    p.add_argument("--only", help="yalnizca su plugin id'leri (virgulle)")
    p.add_argument("--remove", action="store_true", help="guclendirme bloklarini kaldir")
    p.set_defaults(fn=cmd_plugins)

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
