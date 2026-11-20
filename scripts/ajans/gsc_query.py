#!/usr/bin/env python3
"""Google Search Console API: filtrelenmis, token-ekonomik ozetler.

Kullanim:
  gsc_query.py --site "sc-domain:site.com" --mode summary|drops|ctr-gap|pages|queries|inspect [--days 28] [--limit 25]
  gsc_query.py --client musteri-a --mode drops          # config gsc_site
  gsc_query.py --site ... --mode queries --page https://site.com/urun   # bir sayfanin sorgulari
  gsc_query.py --site ... --mode inspect --url https://site.com/yeni   # indeks durumu (URL Inspection API)

Modlar:
  summary   son N gun vs onceki N gun: tiklama, gosterim, CTR, pozisyon
  drops     pozisyon kaybeden sorgular (gosterim >= --min-impressions), kayip buyuklugune gore
  ctr-gap   ilk sayfada (poz <= 10) olup CTR'si pozisyon beklentisinin altinda kalan sayfalar
  pages     en cok tiklanan sayfalar · queries  en cok tiklanan sorgular (--page ile sayfa bazli)
  inspect   --url icin indeks/kapsam/mobil durumu

Kimlik: GOOGLE_APPLICATION_CREDENTIALS (service account JSON yolu; varsayilan .credentials/service-account.json).
Service account e-postasi Search Console'da ilgili mulke "Tam" ya da "Kisitli" kullanici olarak eklenmis olmali.
Bagimlilik: pip install google-auth google-api-python-client
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ortak import (add_common_args, client_cfg, credentials_dir, days_range, delta, die, emit, fmt_num,  # noqa: E402
                    load_env, md_table, optional)

EXPECTED_CTR = {1: 0.28, 2: 0.15, 3: 0.11, 4: 0.08, 5: 0.07, 6: 0.05, 7: 0.04, 8: 0.035, 9: 0.03, 10: 0.025}


def service():
    load_env()
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        die("google kutuphaneleri yok: pip install google-auth google-api-python-client")
    path = optional("GOOGLE_APPLICATION_CREDENTIALS") or str(credentials_dir() / "service-account.json")
    if not Path(path).exists():
        die(f"service account dosyasi yok: {path}")
    creds = service_account.Credentials.from_service_account_file(path, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def query(svc, site, start, end, dimensions, row_limit=1000, filters=None):
    body = {"startDate": start, "endDate": end, "dimensions": dimensions, "rowLimit": row_limit, "dataState": "final"}
    if filters:
        body["dimensionFilterGroups"] = [{"filters": filters}]
    rows = svc.searchanalytics().query(siteUrl=site, body=body).execute().get("rows", [])
    return [{"keys": r.get("keys", []), "clicks": r.get("clicks", 0), "impressions": r.get("impressions", 0), "ctr": r.get("ctr", 0.0), "position": r.get("position", 0.0)} for r in rows]


def totals(rows):
    c = sum(r["clicks"] for r in rows)
    i = sum(r["impressions"] for r in rows)
    pos = (sum(r["position"] * r["impressions"] for r in rows) / i) if i else 0
    return {"clicks": c, "impressions": i, "ctr": (c / i) if i else 0, "position": pos}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gsc_query.py", description="Search Console ozetleri")
    ap.add_argument("--site", help="sc-domain:site.com ya da https://site.com/")
    ap.add_argument("--mode", choices=["summary", "drops", "ctr-gap", "pages", "queries", "inspect"], default="summary")
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--min-impressions", type=int, default=50)
    ap.add_argument("--page", help="queries modunda sayfa URL'si")
    ap.add_argument("--url", help="inspect modunda URL")
    add_common_args(ap)
    args = ap.parse_args(argv)
    site = args.site
    if not site and args.client:
        site = client_cfg(args.client).get("gsc_site")
    if not site:
        die("--site ya da --client (gsc_site) gerekli")
    svc = service()
    cur_s, cur_e = days_range(args.days, end_offset=3)      # GSC ~3 gun gecikmeli
    prev_s, prev_e = days_range(args.days, end_offset=3 + args.days)

    if args.mode == "inspect":
        if not args.url:
            die("--url gerekli")
        r = svc.urlInspection().index().inspect(body={"inspectionUrl": args.url, "siteUrl": site}).execute()
        ir = (r.get("inspectionResult") or {}).get("indexStatusResult") or {}
        mob = (r.get("inspectionResult") or {}).get("mobileUsabilityResult") or {}
        rows = [("Karar", ir.get("verdict")), ("Kapsam", ir.get("coverageState")), ("Robots", ir.get("robotsTxtState")), ("Indeksleme", ir.get("indexingState")),
                ("Son tarama", ir.get("lastCrawlTime")), ("Google canonical", ir.get("googleCanonical")), ("Kullanici canonical", ir.get("userCanonical")),
                ("Mobil", mob.get("verdict", "-"))]
        emit({"url": args.url, "result": r}, args, f"## URL denetimi — {args.url}\n\n" + md_table(rows, ["Alan", "Deger"]))
        return 0

    if args.mode == "summary":
        cur, prev = query(svc, site, cur_s, cur_e, ["date"]), query(svc, site, prev_s, prev_e, ["date"])
        tc, tp = totals(cur), totals(prev)
        rows = [("Tiklama", fmt_num(tc["clicks"]), fmt_num(tp["clicks"]), delta(tc["clicks"], tp["clicks"])),
                ("Gosterim", fmt_num(tc["impressions"]), fmt_num(tp["impressions"]), delta(tc["impressions"], tp["impressions"])),
                ("CTR", f"{tc['ctr'] * 100:.2f}%", f"{tp['ctr'] * 100:.2f}%", delta(tc["ctr"], tp["ctr"])),
                ("Ort. pozisyon", f"{tc['position']:.1f}", f"{tp['position']:.1f}", f"{tc['position'] - tp['position']:+.1f}")]
        md = f"## GSC ozet — {site} ({cur_s}..{cur_e} vs {prev_s}..{prev_e})\n\n" + md_table(rows, ["Metrik", "Simdi", "Once", "Degisim"])
        emit({"site": site, "current": tc, "previous": tp, "period": [cur_s, cur_e]}, args, md)
        return 0

    if args.mode == "drops":
        cur = {r["keys"][0]: r for r in query(svc, site, cur_s, cur_e, ["query"], 5000)}
        prev = {r["keys"][0]: r for r in query(svc, site, prev_s, prev_e, ["query"], 5000)}
        rows = []
        for q, p in prev.items():
            c = cur.get(q)
            if p["impressions"] < args.min_impressions:
                continue
            if not c:
                rows.append((q, f"{p['position']:.1f}", "-", "kayboldu", fmt_num(p["clicks"]), "0"))
                continue
            d = c["position"] - p["position"]
            if d >= 1.0:
                rows.append((q, f"{p['position']:.1f}", f"{c['position']:.1f}", f"{d:+.1f}", fmt_num(p["clicks"]), fmt_num(c["clicks"])))
        rows.sort(key=lambda r: -(float(r[3]) if r[3] != "kayboldu" else 99))
        md = f"## Pozisyon kaybeden sorgular — {site} (gosterim >= {args.min_impressions}, son {args.days} gun vs onceki)\n\n" + md_table(rows[:args.limit], ["Sorgu", "Once", "Simdi", "Degisim", "Tik once", "Tik simdi"])
        emit({"site": site, "rows": rows[:args.limit]}, args, md)
        return 0

    if args.mode == "ctr-gap":
        rows = []
        for r in query(svc, site, cur_s, cur_e, ["page"], 5000):
            pos = r["position"]
            if pos > 10 or r["impressions"] < args.min_impressions:
                continue
            exp = EXPECTED_CTR.get(max(1, round(pos)), 0.025)
            if r["ctr"] < exp * 0.6:
                rows.append((r["keys"][0], f"{pos:.1f}", fmt_num(r["impressions"]), f"{r['ctr'] * 100:.1f}%", f"{exp * 100:.0f}%", fmt_num(int((exp - r["ctr"]) * r["impressions"]))))
        rows.sort(key=lambda r: -int(r[5].replace(",", "")))
        md = f"## CTR acigi olan sayfalar — {site} (poz <= 10; beklenen CTR'nin %60 alti)\n\n" + md_table(rows[:args.limit], ["Sayfa", "Poz", "Gosterim", "CTR", "Beklenen", "Kacan tik"]) + "\n\nOneri: title/description'i sorguya gore yeniden yaz, zengin sonuc (schema) ekle."
        emit({"site": site, "rows": rows[:args.limit]}, args, md)
        return 0

    dim = "page" if args.mode == "pages" else "query"
    filters = [{"dimension": "page", "operator": "equals", "expression": args.page}] if args.page else None
    rows = query(svc, site, cur_s, cur_e, [dim], 5000, filters)
    rows.sort(key=lambda r: -r["clicks"])
    t = [(r["keys"][0][:80], fmt_num(r["clicks"]), fmt_num(r["impressions"]), f"{r['ctr'] * 100:.1f}%", f"{r['position']:.1f}") for r in rows[:args.limit]]
    md = f"## En cok tiklanan {dim} — {site} (son {args.days} gun{', sayfa: ' + args.page if args.page else ''})\n\n" + md_table(t, [dim, "Tik", "Gosterim", "CTR", "Poz"])
    emit({"site": site, "rows": rows[:args.limit]}, args, md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
