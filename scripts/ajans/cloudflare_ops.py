#!/usr/bin/env python3
"""Cloudflare API v4 operasyon araci (Kod Fabrikasi ajans profili; yalnizca stdlib).

Kimlik: CLOUDFLARE_API_TOKEN (zorunlu), CLOUDFLARE_ACCOUNT_ID (Pages icin; yoksa /accounts'tan ilk hesap).
Degerler .credentials/.env'den ya da ortamdan okunur; hicbir zaman yazdirilmaz.

OKUMA (serbest; settings.json'da sorulmaz):
  zones                                  hesaptaki zone'lar
  check            --zone X | --client s saglik ozeti (status, SSL, HTTPS, TLS, dev mode, WAF, DNSSEC, cache...)
  settings         --zone X              tum zone ayarlari
  dns list         --zone X [--type A]   DNS kayitlari
  ssl              --zone X              sertifika paketleri + SSL modu
  analytics        --zone X [--days 7]   istek / bant / tehdit / cache orani (GraphQL)
  security-events  --zone X [--hours 24] WAF ve bot olaylari (GraphQL)
  firewall list    --zone X              ozel WAF kurallari
  redirects list   --zone X              dinamik yonlendirme kurallari
  pagerules list   --zone X              page rules
  pages list                             Cloudflare Pages projeleri
  pages deployments --project P [--n 5]  son dagitimlar

YAZMA (--yes olmadan yalnizca PLAN basar; settings.json `ask` listesindedir):
  purge            --zone X --urls u1 u2 | --prefixes p | --tags t | --hosts h
  purge-all        --zone X              tum onbellek (agir; nadiren)
  redirect add     --zone X --from /eski --to https://.../yeni [--status 301|302] [--preserve-query]
  redirect remove  --zone X --id RULE_ID
  dns add          --zone X --type A --name www --content 1.2.3.4 [--proxied] [--ttl 1]
  dns update       --zone X --id REC_ID [--content ..] [--proxied|--no-proxied] [--ttl ..]
  setting set      --zone X --key always_use_https --value on
  dev-mode         --zone X on|off
  under-attack     --zone X on|off
  firewall add     --zone X --expression '(ip.src eq 1.2.3.4)' --action block [--description ..]
  firewall remove  --zone X --id RULE_ID

YASAK (settings.json DENY; yalnizca insan dashboard'dan):
  dns delete       --zone X --id REC_ID
  (zone silme hic uygulanmadi)

Her yazma islemi <musteri>/infra/cloudflare-log.md (ya da .claude/references/CLOUDFLARE_LOG.md) dosyasina kaydedilir.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ortak import (add_common_args, agency_cfg, append_log, client_cfg, client_dir, delta, die,  # noqa: E402
                    emit, flag, fmt_bytes, fmt_num, http, log, md_table, need, optional, pct, project_root)

API = "https://api.cloudflare.com/client/v4"
GQL = "https://api.cloudflare.com/client/v4/graphql"

GOOD_SSL = {"strict": "✅", "full": "⚠️ (strict onerilir)", "flexible": "❌ (karma icerik/yonlendirme dongusu riski)", "off": "❌"}


# ---------------------------------------------------------------- API
def hdrs():
    return {"Authorization": f"Bearer {need('CLOUDFLARE_API_TOKEN', 'API Token (Zone:Read, DNS, Cache Purge, Zone Settings, WAF, Analytics)')}"}


def cf(method, path, data=None, ok_codes=(200,)):
    status, body = http(method, API + path, headers=hdrs(), data=data, timeout=40)
    if status == 0:
        die(f"ag hatasi: {body.get('error')}")
    if isinstance(body, dict) and body.get("success") is False or status not in ok_codes:
        errs = body.get("errors") if isinstance(body, dict) else body
        die(f"Cloudflare {method} {path} -> HTTP {status}: {json.dumps(errs, ensure_ascii=False)[:600]}")
    return body.get("result") if isinstance(body, dict) else body


def cf_try(method, path, data=None):
    """Yetki yoksa (403/404) None doner; check raporunda 'okunamadi' olarak gecer."""
    status, body = http(method, API + path, headers=hdrs(), data=data, timeout=40)
    if status == 200 and isinstance(body, dict) and body.get("success", True):
        return body.get("result")
    return None


def cf_all(path, per_page=100):
    out, page = [], 1
    sep = "&" if "?" in path else "?"
    while True:
        res = cf("GET", f"{path}{sep}per_page={per_page}&page={page}")
        if not isinstance(res, list):
            return res
        out.extend(res)
        if len(res) < per_page:
            return out
        page += 1


def gql(query, variables):
    status, body = http("POST", GQL, headers=hdrs(), data={"query": query, "variables": variables}, timeout=60)
    if status != 200 or not isinstance(body, dict):
        die(f"GraphQL HTTP {status}: {str(body)[:300]}")
    if body.get("errors"):
        die(f"GraphQL: {json.dumps(body['errors'], ensure_ascii=False)[:500]}")
    return body.get("data") or {}


def resolve_zone(args):
    name = args.zone
    if not name and args.client:
        c = client_cfg(args.client)
        name = c.get("cloudflare_zone") or c.get("domain")
    if not name:
        die("--zone <alanadi> ya da --client <slug> gerekli")
    res = cf("GET", f"/zones?name={name}")
    if not res:
        die(f"zone bulunamadi: {name} (token bu zone'a erisebiliyor mu?)")
    z = res[0]
    return z["id"], z


def account_id():
    aid = optional("CLOUDFLARE_ACCOUNT_ID")
    if aid:
        return aid
    accs = cf("GET", "/accounts")
    if not accs:
        die("hesap bulunamadi; CLOUDFLARE_ACCOUNT_ID ver")
    return accs[0]["id"]


def setting(zid, key):
    r = cf_try("GET", f"/zones/{zid}/settings/{key}")
    return r.get("value") if isinstance(r, dict) else None


def write_guard(args, plan_lines):
    """--yes yoksa plani bas ve cik (dry-run)."""
    print("PLAN (dry-run; uygulamak icin --yes ekle):")
    for l in plan_lines:
        print(f"  - {l}")
    if not args.yes:
        sys.exit(0)


def audit(args, line):
    if args.client:
        p = client_dir(args.client) / "infra" / "cloudflare-log.md"
    else:
        p = project_root() / ".claude" / "references" / "CLOUDFLARE_LOG.md"
    append_log(p, line)


# ---------------------------------------------------------------- okuma komutlari
def cmd_zones(args):
    zs = cf_all("/zones")
    rows = [(z["name"], z["status"], (z.get("plan") or {}).get("name", "-"), z["id"][:8] + "…",
             ", ".join(z.get("name_servers") or [])[:60]) for z in zs]
    emit({"zones": zs}, args, "## Cloudflare zone'lar\n\n" + md_table(rows, ["Zone", "Durum", "Plan", "ID", "NS"]))


def cmd_settings(args):
    zid, z = resolve_zone(args)
    st = cf("GET", f"/zones/{zid}/settings")
    rows = sorted((s["id"], json.dumps(s.get("value"), ensure_ascii=False)[:80], s.get("editable", "")) for s in st)
    emit({"zone": z["name"], "settings": st}, args, f"## Ayarlar — {z['name']}\n\n" + md_table(rows, ["Ayar", "Deger", "Duzenlenebilir"]))


def cmd_dns_list(args):
    zid, z = resolve_zone(args)
    q = f"/zones/{zid}/dns_records" + (f"?type={args.type}" if args.type else "")
    recs = cf_all(q)
    rows = [(r["type"], r["name"], str(r["content"])[:60], "☁️" if r.get("proxied") else "DNS", r.get("ttl"), r["id"][:8] + "…") for r in recs]
    emit({"zone": z["name"], "records": recs}, args, f"## DNS — {z['name']} ({len(recs)} kayit)\n\n" + md_table(rows, ["Tip", "Ad", "Icerik", "Proxy", "TTL", "ID"]))


def cmd_ssl(args):
    zid, z = resolve_zone(args)
    packs = cf_try("GET", f"/zones/{zid}/ssl/certificate_packs?status=all") or []
    mode = setting(zid, "ssl")
    rows = [(p.get("type"), p.get("status"), ", ".join(p.get("hosts") or [])[:60], p.get("certificate_authority", "-"),
             (p.get("certificates") or [{}])[0].get("expires_on", "-")[:10]) for p in packs]
    md = f"## SSL — {z['name']}\n\nMod: **{mode}** {GOOD_SSL.get(mode, '')}\n\n" + md_table(rows, ["Tip", "Durum", "Hostlar", "CA", "Bitis"])
    emit({"zone": z["name"], "ssl_mode": mode, "certificate_packs": packs}, args, md)


ANALYTICS_Q = """
query($zone:String!,$since:Date!,$until:Date!){ viewer { zones(filter:{zoneTag:$zone}) {
  httpRequests1dGroups(limit:100, filter:{date_geq:$since, date_leq:$until}, orderBy:[date_ASC]) {
    dimensions{date} sum{requests bytes cachedRequests cachedBytes threats pageViews} uniq{uniques} } } } }"""


def cmd_analytics(args):
    zid, z = resolve_zone(args)
    days = args.days
    until = dt.date.today()
    since = until - dt.timedelta(days=days - 1)
    prev_since = since - dt.timedelta(days=days)
    data = gql(ANALYTICS_Q, {"zone": zid, "since": prev_since.isoformat(), "until": until.isoformat()})
    groups = ((data.get("viewer") or {}).get("zones") or [{}])[0].get("httpRequests1dGroups") or []
    cur = [g for g in groups if g["dimensions"]["date"] >= since.isoformat()]
    prev = [g for g in groups if g["dimensions"]["date"] < since.isoformat()]

    def tot(gs, k):
        return sum((g["sum"] or {}).get(k, 0) for g in gs)

    def uq(gs):
        return sum((g.get("uniq") or {}).get("uniques", 0) for g in gs)

    rows = []
    for k, label in (("requests", "Istek"), ("pageViews", "Sayfa goruntuleme"), ("threats", "Tehdit (engellenen)")):
        rows.append((label, fmt_num(tot(cur, k)), fmt_num(tot(prev, k)), delta(tot(cur, k), tot(prev, k))))
    rows.append(("Tekil ziyaretci (gunluk toplam)", fmt_num(uq(cur)), fmt_num(uq(prev)), delta(uq(cur), uq(prev))))
    rows.append(("Bant genisligi", fmt_bytes(tot(cur, "bytes")), fmt_bytes(tot(prev, "bytes")), delta(tot(cur, "bytes"), tot(prev, "bytes"))))
    rows.append(("Cache orani (istek)", pct(tot(cur, "cachedRequests"), tot(cur, "requests")), pct(tot(prev, "cachedRequests"), tot(prev, "requests")), "-"))
    rows.append(("Cache orani (bant)", pct(tot(cur, "cachedBytes"), tot(cur, "bytes")), pct(tot(prev, "cachedBytes"), tot(prev, "bytes")), "-"))
    daily = [(g["dimensions"]["date"], fmt_num(g["sum"]["requests"]), fmt_num(g["sum"]["threats"]), pct(g["sum"]["cachedRequests"], g["sum"]["requests"])) for g in cur]
    md = (f"## Trafik — {z['name']} (son {days} gun vs onceki {days} gun)\n\n" + md_table(rows, ["Metrik", "Simdi", "Once", "Degisim"])
          + "\n\n### Gunluk\n\n" + md_table(daily, ["Gun", "Istek", "Tehdit", "Cache"]))
    emit({"zone": z["name"], "days": days, "current": cur, "previous": prev}, args, md)


EVENTS_Q = """
query($zone:String!,$since:String!){ viewer { zones(filter:{zoneTag:$zone}) {
  byAction: firewallEventsAdaptiveGroups(limit:20, filter:{datetime_geq:$since}, orderBy:[count_DESC]) { count dimensions{action source} }
  byCountry: firewallEventsAdaptiveGroups(limit:10, filter:{datetime_geq:$since}, orderBy:[count_DESC]) { count dimensions{clientCountryName} }
  byPath: firewallEventsAdaptiveGroups(limit:10, filter:{datetime_geq:$since}, orderBy:[count_DESC]) { count dimensions{clientRequestPath action} }
} } }"""


def cmd_security_events(args):
    zid, z = resolve_zone(args)
    since = (dt.datetime.utcnow() - dt.timedelta(hours=args.hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = gql(EVENTS_Q, {"zone": zid, "since": since})
    zone = ((data.get("viewer") or {}).get("zones") or [{}])[0]
    a = [(g["dimensions"]["action"], g["dimensions"]["source"], fmt_num(g["count"])) for g in zone.get("byAction") or []]
    c = [(g["dimensions"]["clientCountryName"], fmt_num(g["count"])) for g in zone.get("byCountry") or []]
    p = [(g["dimensions"]["clientRequestPath"][:60], g["dimensions"]["action"], fmt_num(g["count"])) for g in zone.get("byPath") or []]
    md = (f"## Guvenlik olaylari — {z['name']} (son {args.hours} saat)\n\n### Aksiyon / kaynak\n\n" + md_table(a, ["Aksiyon", "Kaynak", "Adet"])
          + "\n\n### Ulke\n\n" + md_table(c, ["Ulke", "Adet"]) + "\n\n### Hedef yol\n\n" + md_table(p, ["Yol", "Aksiyon", "Adet"]))
    emit({"zone": z["name"], "hours": args.hours, "events": zone}, args, md)


def ruleset_entry(zid, phase):
    """Phase entrypoint ruleset'i (yoksa None)."""
    return cf_try("GET", f"/zones/{zid}/rulesets/phases/{phase}/entrypoint")


def cmd_firewall_list(args):
    zid, z = resolve_zone(args)
    rs = ruleset_entry(zid, "http_request_firewall_custom") or {}
    rules = rs.get("rules") or []
    rows = [(r.get("description", "-")[:50], r.get("action"), (r.get("expression") or "")[:70], "açık" if r.get("enabled", True) else "kapalı", r["id"][:8] + "…") for r in rules]
    sl = setting(zid, "security_level")
    md = f"## WAF ozel kurallar — {z['name']} (security_level: {sl})\n\n" + md_table(rows, ["Aciklama", "Aksiyon", "Ifade", "Durum", "ID"])
    emit({"zone": z["name"], "ruleset_id": rs.get("id"), "rules": rules, "security_level": sl}, args, md)


def cmd_redirects_list(args):
    zid, z = resolve_zone(args)
    rs = ruleset_entry(zid, "http_request_dynamic_redirect") or {}
    rules = rs.get("rules") or []
    rows = []
    for r in rules:
        fv = ((r.get("action_parameters") or {}).get("from_value") or {})
        tgt = (fv.get("target_url") or {})
        rows.append((r.get("description", "-")[:40], (r.get("expression") or "")[:60], tgt.get("value") or tgt.get("expression", "-"), fv.get("status_code", "-"),
                     "açık" if r.get("enabled", True) else "kapalı", r["id"][:8] + "…"))
    md = f"## Yonlendirme kurallari — {z['name']} ({len(rules)} kural)\n\n" + md_table(rows, ["Aciklama", "Ifade", "Hedef", "Kod", "Durum", "ID"])
    emit({"zone": z["name"], "ruleset_id": rs.get("id"), "rules": rules}, args, md)


def cmd_pagerules_list(args):
    zid, z = resolve_zone(args)
    prs = cf_try("GET", f"/zones/{zid}/pagerules") or []
    rows = [(", ".join(t.get("constraint", {}).get("value", "") for t in p.get("targets", []))[:60],
             ", ".join(f"{a['id']}={a.get('value')}" for a in p.get("actions", []))[:70], p.get("status")) for p in prs]
    emit({"zone": z["name"], "pagerules": prs}, args, f"## Page Rules — {z['name']}\n\n" + md_table(rows, ["Hedef", "Aksiyonlar", "Durum"]))


def cmd_pages_list(args):
    aid = account_id()
    projs = cf_all(f"/accounts/{aid}/pages/projects")
    rows = [(p["name"], ", ".join(p.get("domains") or [])[:60], (p.get("latest_deployment") or {}).get("environment", "-"),
             ((p.get("latest_deployment") or {}).get("latest_stage") or {}).get("status", "-"), (p.get("latest_deployment") or {}).get("modified_on", "-")[:16]) for p in projs]
    emit({"projects": projs}, args, "## Cloudflare Pages projeleri\n\n" + md_table(rows, ["Proje", "Domainler", "Ortam", "Son durum", "Tarih"]))


def cmd_pages_deployments(args):
    aid = account_id()
    deps = cf("GET", f"/accounts/{aid}/pages/projects/{args.project}/deployments?per_page={args.n}")
    rows = [(d["id"][:8] + "…", d.get("environment"), (d.get("latest_stage") or {}).get("status"), (d.get("deployment_trigger") or {}).get("metadata", {}).get("branch", "-"),
             ((d.get("deployment_trigger") or {}).get("metadata", {}).get("commit_message") or "-")[:50], d.get("created_on", "")[:16], d.get("url", "")) for d in deps]
    emit({"project": args.project, "deployments": deps}, args, f"## Pages dagitimlari — {args.project}\n\n" + md_table(rows, ["ID", "Ortam", "Durum", "Dal", "Commit", "Tarih", "URL"]))


def cmd_check(args):
    zid, z = resolve_zone(args)
    st = {s["id"]: s.get("value") for s in (cf_try("GET", f"/zones/{zid}/settings") or [])}
    dnssec = cf_try("GET", f"/zones/{zid}/dnssec") or {}
    packs = cf_try("GET", f"/zones/{zid}/ssl/certificate_packs") or []
    recs = cf_try("GET", f"/zones/{zid}/dns_records?per_page=100") or []
    waf = (ruleset_entry(zid, "http_request_firewall_custom") or {}).get("rules") or []
    redirects = (ruleset_entry(zid, "http_request_dynamic_redirect") or {}).get("rules") or []
    bot = cf_try("GET", f"/zones/{zid}/bot_management")
    hsts = ((st.get("security_header") or {}).get("strict_transport_security") or {})
    active_pack = any(p.get("status") == "active" for p in packs)
    proxied = [r for r in recs if r.get("proxied")]
    apex_unproxied = [r for r in recs if r["type"] in ("A", "AAAA", "CNAME") and r["name"] == z["name"] and not r.get("proxied")]

    def row(label, val, ok, warn=False, note=""):
        return (flag(ok, warn), label, "okunamadi" if val is None else val, note)

    ssl_mode = st.get("ssl")
    rows = [
        row("Zone durumu", z.get("status"), z.get("status") == "active"),
        row("Plan", (z.get("plan") or {}).get("name"), True),
        row("SSL modu", ssl_mode, ssl_mode == "strict", warn=ssl_mode == "full", note=GOOD_SSL.get(ssl_mode, "")),
        row("Universal SSL sertifikasi", "aktif" if active_pack else f"{len(packs)} paket, aktif yok", active_pack),
        row("Always Use HTTPS", st.get("always_use_https"), st.get("always_use_https") == "on"),
        row("Automatic HTTPS Rewrites", st.get("automatic_https_rewrites"), st.get("automatic_https_rewrites") == "on", warn=True),
        row("Min TLS", st.get("min_tls_version"), str(st.get("min_tls_version")) >= "1.2", warn=True),
        row("TLS 1.3", st.get("tls_1_3"), st.get("tls_1_3") in ("on", "zrt"), warn=True),
        row("HSTS", "acik" if hsts.get("enabled") else "kapali", bool(hsts.get("enabled")), warn=True, note=f"max-age={hsts.get('max_age', '-')}"),
        row("DNSSEC", dnssec.get("status"), dnssec.get("status") == "active", warn=True),
        row("Development Mode", st.get("development_mode"), st.get("development_mode") == "off", note="ON ise onbellek KAPALI; unutulmus olabilir"),
        row("Cache Level", st.get("cache_level"), st.get("cache_level") == "aggressive", warn=True),
        row("Browser Cache TTL", st.get("browser_cache_ttl"), True),
        row("Brotli", st.get("brotli"), st.get("brotli") == "on", warn=True),
        row("HTTP/3", st.get("http3"), st.get("http3") == "on", warn=True),
        row("Early Hints", st.get("early_hints"), st.get("early_hints") == "on", warn=True),
        row("Security Level", st.get("security_level"), st.get("security_level") not in ("under_attack", "essentially_off"), warn=True,
            note="under_attack ise ziyaretcilere challenge gider" if st.get("security_level") == "under_attack" else ""),
        row("Browser Integrity Check", st.get("browser_check"), st.get("browser_check") == "on", warn=True),
        row("Bot Fight Mode", None if bot is None else ("acik" if bot.get("fight_mode") else "kapali"), bool(bot and bot.get("fight_mode")), warn=True),
        row("Ozel WAF kurali", len(waf), True),
        row("Yonlendirme kurali", len(redirects), True),
        row("DNS kayitlari", f"{len(recs)} kayit, {len(proxied)} proxy'li", True),
        row("Apex proxy", "proxy'siz: " + ", ".join(f"{r['type']} {r['content']}" for r in apex_unproxied) if apex_unproxied else "apex proxy'li", not apex_unproxied, warn=True,
            note="proxy'siz apex: WAF/cache/gercek IP gizleme devre disi"),
        row("Email Obfuscation", st.get("email_obfuscation"), st.get("email_obfuscation") == "on", warn=True),
        row("Rocket Loader", st.get("rocket_loader"), st.get("rocket_loader") == "off", warn=True, note="on ise JS siralama sorunlari yasanabilir"),
    ]
    bad = [r for r in rows if r[0] == "❌"]
    warnv = [r for r in rows if r[0] == "⚠️"]
    md = (f"## Cloudflare saglik — {z['name']}\n\nSonuc: {len(bad)} kritik, {len(warnv)} uyari, {len(rows) - len(bad) - len(warnv)} tamam\n\n"
          + md_table(rows, ["", "Kontrol", "Deger", "Not"]))
    emit({"zone": z["name"], "zone_id": zid, "critical": len(bad), "warnings": len(warnv), "rows": rows, "settings": st}, args, md)


# ---------------------------------------------------------------- yazma komutlari
def cmd_purge(args):
    zid, z = resolve_zone(args)
    body, what = {}, ""
    if args.urls:
        body, what = {"files": args.urls}, f"{len(args.urls)} URL"
    elif args.prefixes:
        body, what = {"prefixes": args.prefixes}, f"{len(args.prefixes)} prefix"
    elif args.tags:
        body, what = {"tags": args.tags}, f"{len(args.tags)} tag"
    elif args.hosts:
        body, what = {"hosts": args.hosts}, f"{len(args.hosts)} host"
    else:
        die("--urls | --prefixes | --tags | --hosts gerekli (tumu icin purge-all)")
    write_guard(args, [f"zone {z['name']}: onbellek temizle -> {what}"] + [f"  {v}" for v in list(body.values())[0]])
    cf("POST", f"/zones/{zid}/purge_cache", body)
    audit(args, f"purge {z['name']} {what}: {' '.join(list(body.values())[0])[:300]}")
    print(f"OK: {z['name']} {what} temizlendi")


def cmd_purge_all(args):
    zid, z = resolve_zone(args)
    write_guard(args, [f"zone {z['name']}: TUM onbellek temizlenecek (origin yuku artar)"])
    cf("POST", f"/zones/{zid}/purge_cache", {"purge_everything": True})
    audit(args, f"purge-all {z['name']}")
    print(f"OK: {z['name']} tum onbellek temizlendi")


def cmd_redirect_add(args):
    zid, z = resolve_zone(args)
    src = args.src
    if src.startswith("http"):
        die("--from yol olmali (ornek /eski-sayfa); host zaten zone")
    expr = f'(http.request.uri.path eq "{src}")' if not args.wildcard else f'(starts_with(http.request.uri.path, "{src}"))'
    rule = {"action": "redirect", "expression": expr, "description": args.description or f"{src} -> {args.to}", "enabled": True,
            "action_parameters": {"from_value": {"status_code": args.status, "target_url": {"value": args.to}, "preserve_query_string": bool(args.preserve_query)}}}
    write_guard(args, [f"zone {z['name']}: yonlendirme {args.status} {src} -> {args.to} (query korunur: {bool(args.preserve_query)})", f"ifade: {expr}"])
    rs = ruleset_entry(zid, "http_request_dynamic_redirect")
    if rs and rs.get("id"):
        res = cf("POST", f"/zones/{zid}/rulesets/{rs['id']}/rules", rule)
    else:
        res = cf("POST", f"/zones/{zid}/rulesets", {"name": "default", "kind": "zone", "phase": "http_request_dynamic_redirect", "rules": [rule]})
    new = [r for r in (res.get("rules") or []) if r.get("expression") == expr]
    rid = new[-1]["id"] if new else "?"
    audit(args, f"redirect add {z['name']} {args.status} {src} -> {args.to} (rule {rid})")
    print(f"OK: kural eklendi (id {rid}). Dogrulama: curl -sI https://{z['name']}{src} | head -5")


def cmd_redirect_remove(args):
    zid, z = resolve_zone(args)
    rs = ruleset_entry(zid, "http_request_dynamic_redirect") or {}
    rule = next((r for r in rs.get("rules") or [] if r["id"] == args.id or r["id"].startswith(args.id)), None)
    if not rule:
        die(f"kural bulunamadi: {args.id}")
    write_guard(args, [f"zone {z['name']}: kural silinecek -> {rule.get('description')} [{rule.get('expression')}]"])
    cf("DELETE", f"/zones/{zid}/rulesets/{rs['id']}/rules/{rule['id']}")
    audit(args, f"redirect remove {z['name']} {rule['id']} {rule.get('description')}")
    print("OK: kural silindi")


def cmd_dns_add(args):
    zid, z = resolve_zone(args)
    body = {"type": args.type.upper(), "name": args.name, "content": args.content, "ttl": args.ttl, "proxied": bool(args.proxied)}
    if args.priority is not None:
        body["priority"] = args.priority
    write_guard(args, [f"zone {z['name']}: DNS ekle {body['type']} {body['name']} -> {body['content']} proxy={body['proxied']} ttl={body['ttl']}"])
    res = cf("POST", f"/zones/{zid}/dns_records", body)
    audit(args, f"dns add {z['name']} {body['type']} {body['name']} -> {body['content']} ({res.get('id')})")
    print(f"OK: kayit eklendi (id {res.get('id')})")


def cmd_dns_update(args):
    zid, z = resolve_zone(args)
    recs = cf_all(f"/zones/{zid}/dns_records")
    rec = next((r for r in recs if r["id"] == args.id or r["id"].startswith(args.id)), None)
    if not rec:
        die(f"kayit bulunamadi: {args.id}")
    patch = {}
    if args.content:
        patch["content"] = args.content
    if args.proxied:
        patch["proxied"] = True
    if args.no_proxied:
        patch["proxied"] = False
    if args.ttl:
        patch["ttl"] = args.ttl
    if not patch:
        die("degisecek bir sey yok (--content/--proxied/--no-proxied/--ttl)")
    write_guard(args, [f"zone {z['name']}: DNS guncelle {rec['type']} {rec['name']} ({rec['content']}, proxy={rec.get('proxied')}) -> {patch}"])
    cf("PATCH", f"/zones/{zid}/dns_records/{rec['id']}", patch)
    audit(args, f"dns update {z['name']} {rec['type']} {rec['name']} {patch}")
    print("OK: kayit guncellendi")


def cmd_dns_delete(args):
    zid, z = resolve_zone(args)
    recs = cf_all(f"/zones/{zid}/dns_records")
    rec = next((r for r in recs if r["id"] == args.id or r["id"].startswith(args.id)), None)
    if not rec:
        die(f"kayit bulunamadi: {args.id}")
    write_guard(args, [f"zone {z['name']}: DNS SIL {rec['type']} {rec['name']} -> {rec['content']}  (settings.json: Claude icin DENY)"])
    cf("DELETE", f"/zones/{zid}/dns_records/{rec['id']}")
    audit(args, f"dns delete {z['name']} {rec['type']} {rec['name']} {rec['content']}")
    print("OK: kayit silindi")


def cmd_setting_set(args):
    zid, z = resolve_zone(args)
    val = args.value
    if val.isdigit():
        val = int(val)
    elif val.lower() in ("true", "false"):
        val = val.lower() == "true"
    cur = setting(zid, args.key)
    write_guard(args, [f"zone {z['name']}: ayar {args.key}: {cur} -> {val}"])
    cf("PATCH", f"/zones/{zid}/settings/{args.key}", {"value": val})
    audit(args, f"setting {z['name']} {args.key}: {cur} -> {val}")
    print(f"OK: {args.key} = {val}")


def cmd_dev_mode(args):
    args.key, args.value = "development_mode", args.state
    cmd_setting_set(args)


def cmd_under_attack(args):
    zid, z = resolve_zone(args)
    cur = setting(zid, "security_level")
    new = "under_attack" if args.state == "on" else (args.restore or "medium")
    write_guard(args, [f"zone {z['name']}: security_level {cur} -> {new}"])
    cf("PATCH", f"/zones/{zid}/settings/security_level", {"value": new})
    audit(args, f"under-attack {z['name']} {args.state} (security_level {cur} -> {new})")
    print(f"OK: security_level = {new}")


def cmd_firewall_add(args):
    zid, z = resolve_zone(args)
    rule = {"action": args.action, "expression": args.expression, "description": args.description or f"kf {args.action}", "enabled": True}
    write_guard(args, [f"zone {z['name']}: WAF kurali {args.action} :: {args.expression}"])
    rs = ruleset_entry(zid, "http_request_firewall_custom")
    if rs and rs.get("id"):
        res = cf("POST", f"/zones/{zid}/rulesets/{rs['id']}/rules", rule)
    else:
        res = cf("POST", f"/zones/{zid}/rulesets", {"name": "default", "kind": "zone", "phase": "http_request_firewall_custom", "rules": [rule]})
    new = [r for r in (res.get("rules") or []) if r.get("expression") == args.expression]
    rid = new[-1]["id"] if new else "?"
    audit(args, f"firewall add {z['name']} {args.action} {args.expression} (rule {rid})")
    print(f"OK: WAF kurali eklendi (id {rid})")


def cmd_firewall_remove(args):
    zid, z = resolve_zone(args)
    rs = ruleset_entry(zid, "http_request_firewall_custom") or {}
    rule = next((r for r in rs.get("rules") or [] if r["id"] == args.id or r["id"].startswith(args.id)), None)
    if not rule:
        die(f"kural bulunamadi: {args.id}")
    write_guard(args, [f"zone {z['name']}: WAF kurali silinecek -> {rule.get('description')} [{rule.get('expression')}]"])
    cf("DELETE", f"/zones/{zid}/rulesets/{rs['id']}/rules/{rule['id']}")
    audit(args, f"firewall remove {z['name']} {rule['id']} {rule.get('description')}")
    print("OK: WAF kurali silindi")


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(prog="cloudflare_ops.py", description="Cloudflare API operasyonlari (okuma serbest; yazma --yes + settings.json ask)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def P(name, fn, help="", zone=True, write=False):
        p = sub.add_parser(name, help=help)
        add_common_args(p)
        if zone:
            p.add_argument("--zone", help="alan adi (ornek musteri.com)")
        if write:
            p.add_argument("--yes", action="store_true", help="uygula (yoksa yalnizca PLAN)")
        p.set_defaults(fn=fn)
        return p

    P("zones", cmd_zones, "zone listesi", zone=False)
    P("check", cmd_check, "saglik ozeti")
    P("settings", cmd_settings, "tum ayarlar")
    p = P("analytics", cmd_analytics, "trafik ozeti"); p.add_argument("--days", type=int, default=7)
    p = P("security-events", cmd_security_events, "WAF/bot olaylari"); p.add_argument("--hours", type=int, default=24)
    P("ssl", cmd_ssl, "sertifika durumu")
    p = P("purge", cmd_purge, "secili URL/prefix/tag/host onbellegini temizle", write=True)
    p.add_argument("--urls", nargs="+"); p.add_argument("--prefixes", nargs="+"); p.add_argument("--tags", nargs="+"); p.add_argument("--hosts", nargs="+")
    P("purge-all", cmd_purge_all, "TUM onbellegi temizle", write=True)
    p = P("setting", cmd_setting_set, "zone ayari degistir: setting set --key K --value V", write=True)
    p.add_argument("op", choices=["set"]); p.add_argument("--key", required=True); p.add_argument("--value", required=True)
    p = P("dev-mode", cmd_dev_mode, "Development Mode on|off", write=True); p.add_argument("state", choices=["on", "off"])
    p = P("under-attack", cmd_under_attack, "Under Attack modu on|off", write=True); p.add_argument("state", choices=["on", "off"]); p.add_argument("--restore", help="off icin geri donulecek seviye (varsayilan medium)")

    p = P("dns", None, "dns list|add|update|delete", write=True)
    p.add_argument("op", choices=["list", "add", "update", "delete"])
    p.add_argument("--type"); p.add_argument("--name"); p.add_argument("--content"); p.add_argument("--id")
    p.add_argument("--ttl", type=int, default=1, help="1 = auto"); p.add_argument("--priority", type=int)
    p.add_argument("--proxied", action="store_true"); p.add_argument("--no-proxied", action="store_true")
    p.set_defaults(fn=lambda a: {"list": cmd_dns_list, "add": cmd_dns_add, "update": cmd_dns_update, "delete": cmd_dns_delete}[a.op](a))

    p = P("redirect", None, "redirect list|add|remove", write=True)
    p.add_argument("op", choices=["list", "add", "remove"])
    p.add_argument("--from", dest="src"); p.add_argument("--to"); p.add_argument("--status", type=int, default=301, choices=[301, 302, 307, 308])
    p.add_argument("--preserve-query", action="store_true"); p.add_argument("--wildcard", action="store_true", help="--from ile baslayan tum yollar")
    p.add_argument("--description"); p.add_argument("--id")
    p.set_defaults(fn=lambda a: {"list": cmd_redirects_list, "add": cmd_redirect_add, "remove": cmd_redirect_remove}[a.op](a))
    P("redirects", cmd_redirects_list, "redirect list kisayolu").add_argument("op", nargs="?", default="list")

    p = P("firewall", None, "firewall list|add|remove", write=True)
    p.add_argument("op", choices=["list", "add", "remove"])
    p.add_argument("--expression"); p.add_argument("--action", choices=["block", "challenge", "managed_challenge", "js_challenge", "log", "skip"], default="block")
    p.add_argument("--description"); p.add_argument("--id")
    p.set_defaults(fn=lambda a: {"list": cmd_firewall_list, "add": cmd_firewall_add, "remove": cmd_firewall_remove}[a.op](a))

    p = P("pagerules", cmd_pagerules_list, "page rules"); p.add_argument("op", nargs="?", default="list")
    p = P("pages", None, "pages list | pages deployments --project P", zone=False)
    p.add_argument("op", choices=["list", "deployments"]); p.add_argument("--project"); p.add_argument("--n", type=int, default=5)
    p.set_defaults(fn=lambda a: cmd_pages_list(a) if a.op == "list" else cmd_pages_deployments(a))

    args = ap.parse_args(argv)
    if args.cmd == "pages" and args.op == "deployments" and not args.project:
        die("--project gerekli")
    try:
        return args.fn(args) or 0
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
