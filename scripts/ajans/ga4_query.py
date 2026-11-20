#!/usr/bin/env python3
"""Google Analytics 4 Data API: kanal, sayfa, donusum ozetleri (token-ekonomik).

Kullanim:
  ga4_query.py --property 123456789 --mode summary|channels|pages|landing|conversions [--days 28] [--limit 25]
  ga4_query.py --client musteri-a --mode channels          # config ga4_property

Kimlik: GOOGLE_APPLICATION_CREDENTIALS (service account JSON; varsayilan .credentials/service-account.json).
Service account e-postasi GA4 mulkunde "Goruntuleyici" olarak eklenmis olmali.
Bagimlilik: pip install google-analytics-data
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ortak import add_common_args, client_cfg, credentials_dir, days_range, delta, die, emit, fmt_num, load_env, md_table, optional  # noqa: E402


def client():
    load_env()
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.oauth2 import service_account
    except ImportError:
        die("pip install google-analytics-data")
    path = optional("GOOGLE_APPLICATION_CREDENTIALS") or str(credentials_dir() / "service-account.json")
    if not Path(path).exists():
        die(f"service account dosyasi yok: {path}")
    creds = service_account.Credentials.from_service_account_file(path, scopes=["https://www.googleapis.com/auth/analytics.readonly"])
    return BetaAnalyticsDataClient(credentials=creds)


def report(c, prop, start, end, dims, mets, limit=1000, order_metric=None):
    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, OrderBy, RunReportRequest
    req = RunReportRequest(property=f"properties/{prop}", date_ranges=[DateRange(start_date=start, end_date=end)],
                           dimensions=[Dimension(name=d) for d in dims], metrics=[Metric(name=m) for m in mets], limit=limit)
    if order_metric:
        req.order_bys = [OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_metric), desc=True)]
    resp = c.run_report(req)
    out = []
    for r in resp.rows:
        out.append({"dims": [d.value for d in r.dimension_values], "mets": [float(m.value) for m in r.metric_values]})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ga4_query.py", description="GA4 ozetleri")
    ap.add_argument("--property", help="GA4 property id (sayisal)")
    ap.add_argument("--mode", choices=["summary", "channels", "pages", "landing", "conversions"], default="summary")
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--limit", type=int, default=25)
    add_common_args(ap)
    args = ap.parse_args(argv)
    prop = args.property
    if not prop and args.client:
        prop = client_cfg(args.client).get("ga4_property")
    if not prop:
        die("--property ya da --client (ga4_property) gerekli")
    c = client()
    cs, ce = days_range(args.days, end_offset=1)
    ps, pe = days_range(args.days, end_offset=1 + args.days)
    base_mets = ["sessions", "totalUsers", "engagementRate", "keyEvents", "totalRevenue"]

    if args.mode == "summary":
        cur = report(c, prop, cs, ce, [], base_mets)
        prev = report(c, prop, ps, pe, [], base_mets)
        cm = cur[0]["mets"] if cur else [0] * 5
        pm = prev[0]["mets"] if prev else [0] * 5
        labels = ["Oturum", "Kullanici", "Etkilesim orani", "Donusum (key events)", "Gelir"]
        rows = []
        for i, l in enumerate(labels):
            v, p = cm[i], pm[i]
            f = (lambda x: f"{x * 100:.1f}%") if i == 2 else (lambda x: fmt_num(round(x, 2) if i == 4 else int(x)))
            rows.append((l, f(v), f(p), delta(v, p)))
        md = f"## GA4 ozet — {prop} ({cs}..{ce} vs onceki {args.days} gun)\n\n" + md_table(rows, ["Metrik", "Simdi", "Once", "Degisim"])
        emit({"property": prop, "current": cm, "previous": pm}, args, md)
        return 0

    spec = {
        "channels": (["sessionDefaultChannelGroup"], ["sessions", "totalUsers", "engagementRate", "keyEvents"], "sessions", "Kanal"),
        "pages": (["pagePath"], ["screenPageViews", "totalUsers", "averageSessionDuration"], "screenPageViews", "Sayfa"),
        "landing": (["landingPagePlusQueryString"], ["sessions", "keyEvents", "bounceRate"], "sessions", "Acilis sayfasi"),
        "conversions": (["eventName"], ["keyEvents", "totalUsers"], "keyEvents", "Olay"),
    }[args.mode]
    dims, mets, order, label = spec
    cur = report(c, prop, cs, ce, dims, mets, args.limit, order)
    prev = {r["dims"][0]: r for r in report(c, prop, ps, pe, dims, mets, 5000)}
    rows = []
    for r in cur:
        p = prev.get(r["dims"][0])
        vals = []
        for i, m in enumerate(mets):
            v = r["mets"][i]
            vals.append(f"{v * 100:.1f}%" if m in ("engagementRate", "bounceRate") else (f"{v:.0f} sn" if m == "averageSessionDuration" else fmt_num(int(v))))
        rows.append((r["dims"][0][:70], *vals, delta(r["mets"][0], p["mets"][0]) if p else "yeni"))
    md = f"## GA4 {args.mode} — {prop} (son {args.days} gun)\n\n" + md_table(rows, [label, *mets, f"{mets[0]} degisim"])
    emit({"property": prop, "mode": args.mode, "rows": cur}, args, md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
