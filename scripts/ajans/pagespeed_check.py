#!/usr/bin/env python3
"""Google PageSpeed Insights v5: Core Web Vitals (lab + alan verisi) ve firsatlar (yalnizca stdlib).

Kullanim:
  pagespeed_check.py https://site.com/ [--strategy mobile|desktop|both] [--json] [--out rapor.md]
  pagespeed_check.py --client musteri-a          # config pagespeed_urls (yoksa https://domain/)

Anahtar: PAGESPEED_API_KEY (istege bagli; yoksa dusuk kota ile anahtarsiz calisir).
Esikler (Google): LCP <=2.5s iyi, INP <=200ms iyi, CLS <=0.1 iyi, TBT <=200ms, FCP <=1.8s.
"""
import argparse
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ortak import add_common_args, client_cfg, die, emit, flag, http, md_table, optional  # noqa: E402

PSI = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
THRESH = {"largest-contentful-paint": (2500, 4000), "interaction-to-next-paint": (200, 500), "cumulative-layout-shift": (0.1, 0.25),
          "total-blocking-time": (200, 600), "first-contentful-paint": (1800, 3000), "speed-index": (3400, 5800)}
LABELS = {"largest-contentful-paint": "LCP", "interaction-to-next-paint": "INP", "cumulative-layout-shift": "CLS",
          "total-blocking-time": "TBT", "first-contentful-paint": "FCP", "speed-index": "Speed Index"}


def grade(key, val):
    good, poor = THRESH[key]
    if val is None:
        return "-"
    return "✅ iyi" if val <= good else ("⚠️ gelişmeli" if val <= poor else "❌ zayıf")


def fmt(key, val):
    if val is None:
        return "-"
    return f"{val:.3f}" if key == "cumulative-layout-shift" else f"{val / 1000:.2f} s" if val >= 1000 else f"{val:.0f} ms"


def run_one(url, strategy):
    q = {"url": url, "strategy": strategy, "category": ["performance", "seo", "accessibility", "best-practices"]}
    key = optional("PAGESPEED_API_KEY")
    if key:
        q["key"] = key
    full = PSI + "?" + urllib.parse.urlencode(q, doseq=True)
    status, body = http("GET", full, timeout=120, retries=1)
    if status != 200 or not isinstance(body, dict):
        err = body.get("error", {}).get("message") if isinstance(body, dict) else str(body)[:200]
        hint = " | anahtarsiz kota doldu: PAGESPEED_API_KEY ekle (Google Cloud > PageSpeed Insights API)" if status == 429 else ""
        die(f"PSI HTTP {status}: {err}{hint}")
    lh = body.get("lighthouseResult") or {}
    cats = lh.get("categories") or {}
    audits = lh.get("audits") or {}
    scores = {k: round((v.get("score") or 0) * 100) for k, v in cats.items()}
    lab = {k: (audits.get(k) or {}).get("numericValue") for k in THRESH}
    field = {}
    for src in ("loadingExperience", "originLoadingExperience"):
        m = (body.get(src) or {}).get("metrics") or {}
        if m:
            field = {"scope": "sayfa" if src == "loadingExperience" else "origin", "category": (body.get(src) or {}).get("overall_category"),
                     "LCP": (m.get("LARGEST_CONTENTFUL_PAINT_MS") or {}), "INP": (m.get("INTERACTION_TO_NEXT_PAINT") or {}),
                     "CLS": (m.get("CUMULATIVE_LAYOUT_SHIFT_SCORE") or {})}
            break
    opps = []
    for k, a in audits.items():
        d = a.get("details") or {}
        if d.get("type") == "opportunity" and (d.get("overallSavingsMs") or 0) >= 100:
            opps.append((a.get("title", k), int(d.get("overallSavingsMs") or 0), int((d.get("overallSavingsBytes") or 0) / 1024)))
    opps.sort(key=lambda x: -x[1])
    diag = [a.get("title") for k, a in audits.items() if a.get("score") is not None and a["score"] < 0.5 and (a.get("details") or {}).get("type") == "table" and a.get("scoreDisplayMode") == "binary"]
    return {"url": url, "strategy": strategy, "scores": scores, "lab": lab, "field": field, "opportunities": opps[:10], "failed_audits": diag[:12],
            "fetch_time": lh.get("fetchTime"), "final_url": lh.get("finalUrl")}


def render(r):
    md = [f"### {r['strategy'].upper()} — {r['url']}", "",
          md_table([(k, f"{v}") for k, v in r["scores"].items()], ["Kategori", "Skor"]), "",
          "**Lab (Lighthouse)**", "",
          md_table([(LABELS[k], fmt(k, v), grade(k, v)) for k, v in r["lab"].items()], ["Metrik", "Değer", "Durum"]), ""]
    f = r["field"]
    if f:
        rows = []
        for m in ("LCP", "INP", "CLS"):
            d = f.get(m) or {}
            p = d.get("percentile")
            rows.append((m, (f"{p / 1000:.2f} s" if m != "CLS" and p and p >= 1000 else (f"{p / 100:.2f}" if m == "CLS" and p is not None else (f"{p} ms" if p is not None else "-"))), d.get("category", "-")))
        md += [f"**Alan verisi (CrUX, {f['scope']}, genel: {f.get('category')})**", "", md_table(rows, ["Metrik", "p75", "Kategori"]), ""]
    else:
        md += ["_Alan verisi (CrUX) yok: yeterli gerçek kullanıcı trafiği toplanmamış._", ""]
    if r["opportunities"]:
        md += ["**Fırsatlar (tahmini kazanç)**", "", md_table(r["opportunities"], ["Öneri", "ms", "KB"]), ""]
    if r["failed_audits"]:
        md += ["**Başarısız denetimler**", ""] + [f"- {t}" for t in r["failed_audits"]] + [""]
    return "\n".join(md)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pagespeed_check.py", description="PageSpeed Insights / Core Web Vitals")
    ap.add_argument("url", nargs="*")
    ap.add_argument("--strategy", choices=["mobile", "desktop", "both"], default="mobile")
    add_common_args(ap)
    args = ap.parse_args(argv)
    urls = list(args.url)
    if not urls and args.client:
        c = client_cfg(args.client)
        urls = c.get("pagespeed_urls") or ([f"https://{c['domain']}/"] if c.get("domain") else [])
    if not urls:
        die("URL ya da --client gerekli")
    strategies = ["mobile", "desktop"] if args.strategy == "both" else [args.strategy]
    results = [run_one(u if u.startswith("http") else "https://" + u, s) for u in urls for s in strategies]
    md = "# PageSpeed raporu\n\n" + "\n".join(render(r) for r in results)
    emit({"results": results}, args, md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
