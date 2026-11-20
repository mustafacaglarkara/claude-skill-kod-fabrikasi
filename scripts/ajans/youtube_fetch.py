#!/usr/bin/env python3
"""YouTube arastirma: rakip videolarin transkripti + yorumlari + kanal/arama istatistikleri.

Kullanim:
  youtube_fetch.py --video <id|url> [--video ...] [--comments 200] [--lang tr,en] --out clients/x/youtube-research
  youtube_fetch.py --search "arac kiralama" [--max 10] --out ...        # en cok izlenen videolar + istatistik
  youtube_fetch.py --channel <channelId|@handle> [--max 10] --out ...  # kanalin en cok izlenen videolari

Cikti: <out>/<videoId>.md (meta + transkript + yorumlar) ve <out>/_index.md. Bu dosyalar NotebookLM'e
kaynak olarak eklenir (notebooklm MCP `source_add` ya da `notebooklm source add`).

Kimlik: YOUTUBE_API_KEY (Data API v3; yorum, arama, istatistik icin). Transkript icin anahtar gerekmez.
Bagimlilik: pip install youtube-transcript-api   (Data API icin stdlib yeter)
"""
import argparse
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ortak import die, http, log, md_table, optional  # noqa: E402

API = "https://www.googleapis.com/youtube/v3"


def video_id(s):
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})", s)
    return m.group(1) if m else (s if re.fullmatch(r"[A-Za-z0-9_-]{11}", s) else None)


def yt(path, **params):
    key = optional("YOUTUBE_API_KEY")
    if not key:
        die("YOUTUBE_API_KEY yok (.credentials/.env)")
    params["key"] = key
    status, body = http("GET", f"{API}/{path}?" + urllib.parse.urlencode(params, doseq=True), timeout=40)
    if status != 200 or not isinstance(body, dict):
        die(f"YouTube API HTTP {status}: {str(body)[:300]}")
    return body


def transcript(vid, langs):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        log("youtube-transcript-api yok (pip install youtube-transcript-api); transkript atlandi")
        return "", ""
    try:
        api = YouTubeTranscriptApi()
        tr = api.fetch(vid, languages=langs)
        lang = getattr(tr, "language_code", "?")
        parts = []
        for s in tr:
            start = int(getattr(s, "start", 0))
            parts.append(f"[{start // 60:02d}:{start % 60:02d}] {getattr(s, 'text', '')}")
        return "\n".join(parts), lang
    except Exception as e:
        log(f"transkript alinamadi {vid}: {str(e)[:120]}")
        return "", ""


def meta(vid):
    r = yt("videos", part="snippet,statistics,contentDetails", id=vid)
    items = r.get("items") or []
    if not items:
        return {}
    it = items[0]
    sn, st = it.get("snippet", {}), it.get("statistics", {})
    return {"id": vid, "title": sn.get("title"), "channel": sn.get("channelTitle"), "published": sn.get("publishedAt", "")[:10],
            "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)), "comments": int(st.get("commentCount", 0)),
            "duration": it.get("contentDetails", {}).get("duration"), "tags": sn.get("tags", [])[:15], "description": sn.get("description", "")[:1500]}


def comments(vid, n):
    out, token = [], None
    while len(out) < n:
        params = dict(part="snippet", videoId=vid, maxResults=100, order="relevance", textFormat="plainText")
        if token:
            params["pageToken"] = token
        r = yt("commentThreads", **params)
        for it in r.get("items", []):
            c = it["snippet"]["topLevelComment"]["snippet"]
            out.append((int(c.get("likeCount", 0)), c.get("textDisplay", "").replace("\n", " ")[:400]))
        token = r.get("nextPageToken")
        if not token:
            break
    out.sort(key=lambda x: -x[0])
    return out[:n]


def write_video(vid, out_dir, n_comments, langs):
    m = meta(vid) if optional("YOUTUBE_API_KEY") else {"id": vid}
    tr, lang = transcript(vid, langs)
    cm = comments(vid, n_comments) if (n_comments and optional("YOUTUBE_API_KEY")) else []
    md = [f"# {m.get('title') or vid}", "", f"- URL: https://www.youtube.com/watch?v={vid}", f"- Kanal: {m.get('channel', '-')} · Yayin: {m.get('published', '-')} · Sure: {m.get('duration', '-')}",
          f"- Izlenme: {m.get('views', '-')} · Begeni: {m.get('likes', '-')} · Yorum: {m.get('comments', '-')}", f"- Etiketler: {', '.join(m.get('tags', []))}", "",
          "## Aciklama", "", m.get("description", "-"), "", f"## Transkript ({lang or 'yok'})", "", tr or "_(transkript yok)_", "",
          f"## Yorumlar (begeniye gore ilk {len(cm)})", ""] + [f"- ({l}) {t}" for l, t in cm]
    p = out_dir / f"{vid}.md"
    p.write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    log(f"yazildi: {p} (transkript {len(tr)} kr, {len(cm)} yorum)")
    return m


def main(argv=None):
    ap = argparse.ArgumentParser(prog="youtube_fetch.py", description="YouTube transkript + yorum + istatistik")
    ap.add_argument("--video", action="append", help="video id ya da URL (tekrarlanabilir)")
    ap.add_argument("--search", help="arama sorgusu; en cok izlenen videolar")
    ap.add_argument("--channel", help="kanal id ya da @handle")
    ap.add_argument("--max", type=int, default=10)
    ap.add_argument("--comments", type=int, default=200)
    ap.add_argument("--lang", default="tr,en")
    ap.add_argument("--out", required=True, help="cikti klasoru (clients/<musteri>/youtube-research)")
    ap.add_argument("--no-fetch", action="store_true", help="arama/kanal: yalnizca listele, transkript cekme")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    langs = [l.strip() for l in args.lang.split(",") if l.strip()]
    ids = []
    for v in args.video or []:
        vid = video_id(v)
        if not vid:
            die(f"video id cozulemedi: {v}")
        ids.append(vid)
    listing = []
    if args.search:
        r = yt("search", part="id", q=args.search, type="video", order="viewCount", maxResults=min(args.max, 50))
        ids += [it["id"]["videoId"] for it in r.get("items", [])]
    if args.channel:
        ch = args.channel
        if ch.startswith("@"):
            r = yt("channels", part="id", forHandle=ch)
            ch = (r.get("items") or [{}])[0].get("id") or die(f"kanal bulunamadi: {args.channel}")
        r = yt("search", part="id", channelId=ch, type="video", order="viewCount", maxResults=min(args.max, 50))
        ids += [it["id"]["videoId"] for it in r.get("items", [])]
    if not ids:
        die("--video / --search / --channel gerekli")
    seen = []
    for vid in ids:
        if vid in seen:
            continue
        seen.append(vid)
        if args.no_fetch and (args.search or args.channel):
            listing.append(meta(vid))
        else:
            listing.append(write_video(vid, out, args.comments, langs))
    rows = [(m.get("id"), (m.get("title") or "-")[:60], m.get("channel", "-"), m.get("views", "-"), m.get("published", "-")) for m in listing]
    idx = out / "_index.md"
    idx.write_text(f"# YouTube arastirma dizini\n\n" + md_table(rows, ["ID", "Baslik", "Kanal", "Izlenme", "Tarih"]) + "\n", encoding="utf-8", newline="\n")
    print(md_table(rows, ["ID", "Baslik", "Kanal", "Izlenme", "Tarih"]))
    print(f"\nKlasor: {out}  → NotebookLM'e kaynak olarak ekle (source_add). Sorular: kanca analizi · aci noktalari · icerik boslugu")
    return 0


if __name__ == "__main__":
    sys.exit(main())
