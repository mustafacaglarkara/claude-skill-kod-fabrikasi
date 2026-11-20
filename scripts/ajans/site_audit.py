#!/usr/bin/env python3
"""Site denetimi: teknik SEO + guvenlik basliklari + kirik baglanti + Cloudflare tespiti (yalnizca stdlib).

Kullanim:
  site_audit.py https://site.com [--crawl 10] [--links] [--competitor] [--timeout 15] [--json] [--out rapor.md]
  site_audit.py --client musteri-a            # config'teki domain

Kontroller (sayfa): durum kodu, yonlendirme zinciri, sure, title/description uzunlugu, canonical, robots meta,
  H1 sayisi, H2/H3 (--competitor: tam hiyerarsi), alt'siz gorsel, JSON-LD tipleri, OG/Twitter, hreflang, lang,
  viewport, kelime sayisi, ic/dis baglanti sayisi, sikistirma, cache-control.
Kontroller (site): http->https, www tutarliligi, robots.txt (+ Sitemap satiri), sitemap.xml (URL sayisi),
  404 sayfasi gercekten 404 mu, guvenlik basliklari (HSTS, CSP, X-Content-Type-Options, X-Frame-Options/
  frame-ancestors, Referrer-Policy, Permissions-Policy), Cloudflare proxy (cf-ray) ve cache durumu (cf-cache-status).
--links: taranan sayfalardaki ic baglantilari (en fazla 200) kontrol eder; 200 olmayanlari listeler.
Hic bir sey yazmaz; yalnizca GET/HEAD. Kibarlik: istekler arasi 0.3 sn.
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
from collections import deque
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ortak import add_common_args, client_cfg, die, emit, flag, http, log, md_table  # noqa: E402

SEC_HEADERS = {
    "strict-transport-security": ("HSTS", "max-age>=15552000 onerilir"),
    "content-security-policy": ("CSP", "en azindan frame-ancestors / default-src"),
    "x-content-type-options": ("X-Content-Type-Options", "nosniff"),
    "x-frame-options": ("X-Frame-Options", "DENY/SAMEORIGIN (ya da CSP frame-ancestors)"),
    "referrer-policy": ("Referrer-Policy", "strict-origin-when-cross-origin"),
    "permissions-policy": ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.in_title = False
        self.meta = {}
        self.canonical = ""
        self.h = {"h1": [], "h2": [], "h3": []}
        self._h = None
        self.imgs = 0
        self.imgs_noalt = 0
        self.links = []
        self.jsonld = []
        self._in_ld = False
        self._ld_buf = ""
        self.lang = ""
        self.hreflang = []
        self.text_words = 0
        self._skip = 0
        self.viewport = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "title":
            self.in_title = True
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key:
                self.meta[key] = a.get("content", "")
            if key == "viewport":
                self.viewport = True
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            if "canonical" in rel:
                self.canonical = a.get("href", "")
            if "alternate" in rel and a.get("hreflang"):
                self.hreflang.append(a.get("hreflang"))
        elif tag in ("h1", "h2", "h3"):
            self._h = tag
            self.h[tag].append("")
        elif tag == "img":
            self.imgs += 1
            if not (a.get("alt") or "").strip():
                self.imgs_noalt += 1
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "script":
            if (a.get("type") or "").lower() == "application/ld+json":
                self._in_ld = True
                self._ld_buf = ""
            else:
                self._skip += 1
        elif tag in ("style", "noscript"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag in ("h1", "h2", "h3"):
            self._h = None
        elif tag == "script":
            if self._in_ld:
                self._in_ld = False
                try:
                    d = json.loads(self._ld_buf)
                    items = d if isinstance(d, list) else [d]
                    for it in items:
                        if isinstance(it, dict):
                            g = it.get("@graph")
                            for x in (g if isinstance(g, list) else [it]):
                                if isinstance(x, dict) and x.get("@type"):
                                    t = x["@type"]
                                    self.jsonld.append(t if isinstance(t, str) else "/".join(t))
                except json.JSONDecodeError:
                    self.jsonld.append("(bozuk JSON-LD)")
            elif self._skip:
                self._skip -= 1
        elif tag in ("style", "noscript") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self._in_ld:
            self._ld_buf += data
            return
        if self._h:
            self.h[self._h][-1] += data
        if not self._skip:
            self.text_words += len(data.split())


def norm(url):
    u = urllib.parse.urlsplit(url.strip())
    return urllib.parse.urlunsplit((u.scheme.lower(), u.netloc.lower(), u.path or "/", u.query, ""))


def same_site(a, b):
    ha, hb = urllib.parse.urlsplit(a).netloc.lower(), urllib.parse.urlsplit(b).netloc.lower()
    return ha.removeprefix("www.") == hb.removeprefix("www.")


def fetch(url, timeout):
    t0 = time.time()
    status, body = http("GET", url, headers={"Accept": "text/html,*/*;q=0.8", "Accept-Encoding": "gzip, br"}, timeout=timeout, retries=1, raw=True)
    ms = int((time.time() - t0) * 1000)
    if status == 0:
        return {"url": url, "status": 0, "error": body.get("error"), "ms": ms}
    hd = {k.lower(): v for k, v in body["headers"].items()}
    raw = body["bytes"]
    enc = hd.get("content-encoding", "")
    try:
        if "gzip" in enc:
            import gzip
            raw = gzip.decompress(raw)
        elif "br" in enc:
            try:
                import brotli  # type: ignore
                raw = brotli.decompress(raw)
            except ImportError:
                raw = b""
    except Exception:
        pass
    text = raw.decode("utf-8", errors="replace") if raw else ""
    return {"url": url, "final_url": body["final_url"], "status": status, "ms": ms, "headers": hd, "html": text, "size": len(body["bytes"])}


def head(url, timeout):
    status, body = http("HEAD", url, timeout=timeout, retries=0, raw=True)
    if status in (0, 405, 403):
        status, body = http("GET", url, timeout=timeout, retries=0, raw=True)
    return status, (body.get("final_url", url) if isinstance(body, dict) else url)


def analyze_page(f, competitor=False):
    p = Page()
    try:
        p.feed(f.get("html", ""))
    except Exception as e:  # bozuk HTML
        log(f"HTML parse uyarisi {f['url']}: {e}")
    title = " ".join(p.title.split())
    desc = p.meta.get("description", "")
    robots = p.meta.get("robots", "")
    hd = f.get("headers", {})
    base = f.get("final_url", f["url"])
    internal, external = set(), set()
    for href in p.links:
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        full = urllib.parse.urljoin(base, href)
        if not full.startswith("http"):
            continue
        (internal if same_site(full, base) else external).add(norm(full))
    issues = []
    if not title:
        issues.append("title yok")
    elif len(title) > 60:
        issues.append(f"title uzun ({len(title)})")
    elif len(title) < 20:
        issues.append(f"title kisa ({len(title)})")
    if not desc:
        issues.append("meta description yok")
    elif len(desc) > 160:
        issues.append(f"description uzun ({len(desc)})")
    elif len(desc) < 70:
        issues.append(f"description kisa ({len(desc)})")
    if len(p.h["h1"]) != 1:
        issues.append(f"H1 sayisi {len(p.h['h1'])}")
    if not p.canonical:
        issues.append("canonical yok")
    elif norm(urllib.parse.urljoin(base, p.canonical)) != norm(base):
        issues.append(f"canonical farkli: {p.canonical}")
    if "noindex" in robots.lower():
        issues.append("NOINDEX!")
    if p.imgs_noalt:
        issues.append(f"{p.imgs_noalt}/{p.imgs} gorsel alt'siz")
    if not p.viewport:
        issues.append("viewport meta yok")
    if not p.lang:
        issues.append("html lang yok")
    if not p.jsonld:
        issues.append("JSON-LD yok")
    if not p.meta.get("og:title") and not p.meta.get("og:image"):
        issues.append("Open Graph yok")
    if p.text_words < 200:
        issues.append(f"icerik az ({p.text_words} kelime)")
    if f["ms"] > 1500:
        issues.append(f"yavas TTFB+indirme {f['ms']} ms")
    if "content-encoding" not in hd:
        issues.append("sikistirma yok")
    res = {
        "url": f["url"], "final_url": base, "status": f["status"], "ms": f["ms"], "size": f.get("size"),
        "title": title, "title_len": len(title), "description": desc, "description_len": len(desc), "robots": robots,
        "canonical": p.canonical, "h1": [" ".join(x.split()) for x in p.h["h1"]], "h2_count": len(p.h["h2"]), "h3_count": len(p.h["h3"]),
        "images": p.imgs, "images_no_alt": p.imgs_noalt, "jsonld": p.jsonld, "og": {k: v for k, v in p.meta.items() if k.startswith(("og:", "twitter:"))},
        "hreflang": p.hreflang, "lang": p.lang, "viewport": p.viewport, "words": p.text_words,
        "internal_links": sorted(internal), "external_links": len(external),
        "encoding": hd.get("content-encoding", ""), "cache_control": hd.get("cache-control", ""), "issues": issues,
    }
    if competitor:
        res["outline"] = [("H1", " ".join(x.split())) for x in p.h["h1"]] + [("H2", " ".join(x.split())) for x in p.h["h2"]] + [("H3", " ".join(x.split())) for x in p.h["h3"]]
    return res


def site_checks(start, timeout):
    u = urllib.parse.urlsplit(start)
    host = u.netloc
    out = {}
    # http -> https
    st, fin = head(f"http://{host}/", timeout)
    out["http_to_https"] = {"ok": fin.startswith("https://"), "status": st, "final": fin}
    # www tutarliligi
    alt = host.removeprefix("www.") if host.startswith("www.") else "www." + host
    st2, fin2 = head(f"https://{alt}/", timeout)
    out["www_variant"] = {"host": alt, "status": st2, "final": fin2, "ok": st2 in (200, 301, 302, 307, 308) and urllib.parse.urlsplit(fin2).netloc == host}
    # robots.txt
    st3, body = http("GET", f"{u.scheme}://{host}/robots.txt", timeout=timeout, retries=0)
    rt = body if isinstance(body, str) else ""
    sitemaps = re.findall(r"(?im)^sitemap:\s*(\S+)", rt)
    # yalnizca `User-agent: *` blogunda `Disallow: /` varsa tum site kapali sayilir
    star_block = re.search(r"(?is)^user-agent:\s*\*\s*\n(.*?)(?=^user-agent:|\Z)", rt, re.M)
    disallow_all = bool(star_block and re.search(r"(?im)^disallow:\s*/\s*$", star_block.group(1)))
    out["robots_txt"] = {"status": st3, "ok": st3 == 200, "sitemaps": sitemaps, "disallow_all": disallow_all}
    # sitemap
    sm_url = sitemaps[0] if sitemaps else f"{u.scheme}://{host}/sitemap.xml"
    st4, body4 = http("GET", sm_url, timeout=timeout, retries=0)
    xml = body4 if isinstance(body4, str) else ""
    out["sitemap"] = {"url": sm_url, "status": st4, "ok": st4 == 200 and "<urlset" in xml or "<sitemapindex" in xml,
                      "urls": len(re.findall(r"<loc>", xml)), "index": "<sitemapindex" in xml}
    # 404
    st5, _ = head(f"{u.scheme}://{host}/kf-olmayan-sayfa-{int(time.time())}", timeout)
    out["not_found"] = {"status": st5, "ok": st5 == 404}
    return out


def security_headers(hd):
    rows, score = [], 0
    for k, (label, hint) in SEC_HEADERS.items():
        v = hd.get(k)
        ok = bool(v)
        if k == "x-frame-options" and not ok and "frame-ancestors" in (hd.get("content-security-policy") or ""):
            ok, v = True, "(CSP frame-ancestors)"
        if k == "strict-transport-security" and ok:
            m = re.search(r"max-age=(\d+)", v)
            ok = bool(m and int(m.group(1)) >= 15552000)
        score += ok
        rows.append((flag(ok, warn=k in ("permissions-policy", "content-security-policy")), label, (v or "-")[:70], hint if not ok else ""))
    return rows, score


def cloudflare_info(hd):
    cf = "cf-ray" in hd or "cloudflare" in (hd.get("server") or "").lower()
    return {"proxied": cf, "cache_status": hd.get("cf-cache-status", "-"), "server": hd.get("server", "-"), "cf_ray": "var" if "cf-ray" in hd else "-"}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="site_audit.py", description="Site denetimi (teknik SEO + guvenlik + baglantilar)")
    ap.add_argument("url", nargs="?")
    ap.add_argument("--crawl", type=int, default=1, help="taranacak sayfa sayisi (BFS, en fazla 50)")
    ap.add_argument("--links", action="store_true", help="ic baglantilari kontrol et (en fazla 200)")
    ap.add_argument("--competitor", action="store_true", help="rakip modu: baslik hiyerarsisi + meta; site kontrolleri atlanir")
    ap.add_argument("--timeout", type=int, default=15)
    add_common_args(ap)
    args = ap.parse_args(argv)

    url = args.url
    if not url and args.client:
        c = client_cfg(args.client)
        url = (c.get("pagespeed_urls") or [None])[0] or ("https://" + c["domain"]) if c.get("domain") else None
    if not url:
        die("URL ya da --client gerekli")
    if not url.startswith("http"):
        url = "https://" + url
    start = norm(url)
    limit = max(1, min(args.crawl, 50))

    pages, seen, q = [], {start}, deque([start])
    while q and len(pages) < limit:
        cur = q.popleft()
        f = fetch(cur, args.timeout)
        if f["status"] == 0:
            pages.append({"url": cur, "status": 0, "issues": [f"erisilemedi: {f.get('error')}"], "internal_links": []})
            continue
        if "html" not in f["headers"].get("content-type", ""):
            pages.append({"url": cur, "status": f["status"], "issues": ["HTML degil"], "internal_links": []})
            continue
        if f["status"] != 200:
            pages.append({"url": cur, "status": f["status"], "ms": f["ms"], "issues": [f"HTTP {f['status']}" + (" (bot korumasi / WAF olabilir)" if f["status"] in (403, 429, 503) else "")],
                          "internal_links": [], "_headers": f["headers"]})
            continue
        pg = analyze_page(f, competitor=args.competitor)
        pg["_headers"] = f["headers"]
        pages.append(pg)
        for l in pg["internal_links"]:
            if l not in seen and len(seen) < limit * 5 and not re.search(r"\.(pdf|jpg|jpeg|png|gif|webp|svg|zip|mp4|css|js)(\?|$)", l, re.I):
                seen.add(l)
                q.append(l)
        time.sleep(0.3)

    first = next((p for p in pages if p.get("_headers")), None)
    hd = first["_headers"] if first else {}
    result = {"start": start, "pages": [{k: v for k, v in p.items() if k != "_headers"} for p in pages]}
    md = [f"# Site denetimi — {start}", f"Taranan sayfa: {len(pages)} · tarih: {time.strftime('%Y-%m-%d %H:%M')}", ""]

    if not args.competitor:
        sc = site_checks(start, args.timeout)
        result["site"] = sc
        cfi = cloudflare_info(hd)
        result["cloudflare"] = cfi
        rows = [
            (flag(sc["http_to_https"]["ok"]), "HTTP -> HTTPS yonlendirme", f"{sc['http_to_https']['status']} -> {sc['http_to_https']['final']}"),
            (flag(sc["www_variant"]["ok"], warn=True), f"www varyanti ({sc['www_variant']['host']})", f"{sc['www_variant']['status']} -> {sc['www_variant']['final']}"),
            (flag(sc["robots_txt"]["ok"] and not sc["robots_txt"]["disallow_all"]), "robots.txt", f"HTTP {sc['robots_txt']['status']}; Sitemap satiri: {len(sc['robots_txt']['sitemaps'])}" + (" · DISALLOW ALL!" if sc["robots_txt"]["disallow_all"] else "")),
            (flag(sc["sitemap"]["ok"]), "Sitemap", f"{sc['sitemap']['url']} HTTP {sc['sitemap']['status']}; {sc['sitemap']['urls']} URL" + (" (index)" if sc["sitemap"]["index"] else "")),
            (flag(sc["not_found"]["ok"]), "Olmayan sayfa 404 donuyor", f"HTTP {sc['not_found']['status']}"),
            (flag(cfi["proxied"], warn=True), "Cloudflare proxy", f"server={cfi['server']} cf-cache-status={cfi['cache_status']}"),
        ]
        md += ["## Site düzeyi", "", md_table(rows, ["", "Kontrol", "Sonuç"]), ""]
        sh, score = security_headers(hd)
        result["security_headers"] = {"score": score, "of": len(SEC_HEADERS), "rows": sh}
        md += [f"## Güvenlik başlıkları ({score}/{len(SEC_HEADERS)})", "", md_table(sh, ["", "Başlık", "Değer", "Öneri"]), ""]

    rows = []
    for p in pages:
        rows.append((p.get("status"), p["url"].replace(start, "/") if p["url"] != start else "/", p.get("ms", "-"), p.get("title_len", "-"), p.get("description_len", "-"),
                     len(p.get("h1", [])) if "h1" in p else "-", ", ".join(p.get("jsonld", []))[:40] or "-", "; ".join(p.get("issues", [])) or "temiz"))
    md += ["## Sayfalar", "", md_table(rows, ["HTTP", "Sayfa", "ms", "title", "desc", "H1", "JSON-LD", "Sorunlar"]), ""]

    if args.competitor:
        for p in pages:
            if p.get("outline"):
                md += [f"### Hiyerarşi — {p['url']}", "", f"**Title:** {p['title']}  ", f"**Description:** {p['description']}", ""]
                md += [f"- {lvl}: {txt[:120]}" for lvl, txt in p["outline"][:60]] + [""]

    if args.links:
        targets = sorted({l for p in pages for l in p.get("internal_links", [])} - {p["url"] for p in pages})[:200]
        broken = []
        for t in targets:
            st, fin = head(t, args.timeout)
            if st != 200:
                broken.append((st, t, fin if fin != t else ""))
            time.sleep(0.2)
        result["links"] = {"checked": len(targets), "broken": broken}
        md += [f"## Bağlantılar ({len(targets)} kontrol edildi, {len(broken)} sorunlu)", "", md_table(broken, ["HTTP", "URL", "Yönlendi"]), ""]

    total_issues = sum(len(p.get("issues", [])) for p in pages)
    result["summary"] = {"pages": len(pages), "page_issues": total_issues}
    md.insert(2, f"Sayfa sorunu: {total_issues}" + (f" · güvenlik başlığı: {result['security_headers']['score']}/{len(SEC_HEADERS)}" if "security_headers" in result else "")
              + (f" · kırık bağlantı: {len(result['links']['broken'])}" if "links" in result else ""))
    emit(result, args, "\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
