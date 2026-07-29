#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""한일 주요 뉴스 3줄 요약 → 텔레그램 발송 (GitHub Actions용)"""
import os, re, sys, html, json, urllib.request, urllib.parse
from collections import Counter
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET

KST = timezone(timedelta(hours=9))

FEEDS = [
    ("JP", "사회", "https://www.nhk.or.jp/rss/news/cat0.xml"),
    ("JP", "사회", "https://www.nhk.or.jp/rss/news/cat1.xml"),
    ("JP", "정치", "https://www.nhk.or.jp/rss/news/cat4.xml"),
    ("JP", "경제", "https://www.nhk.or.jp/rss/news/cat5.xml"),
    ("KR", "종합", "https://www.yna.co.kr/rss/news.xml"),
    ("KR", "종합", "https://www.hani.co.kr/rss/"),
    ("KR", "종합", "https://www.khan.co.kr/rss/rssdata/total_news.xml"),
]

SKIP = ("[알림]", "저작권", "[부고]", "[인사]", "광고", "구독")
SKIP_RE = re.compile(
    r"^【地震情報】|^【\d+日】|ライフライン|津波の心配なし|震度\d[弱強]?\s*$")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")


def fetch(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print("fetch fail {}: {}".format(url, e), file=sys.stderr)
        return b""


def clean(s):
    if not s:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def parse(raw, limit=15):
    out = []
    if not raw:
        return out
    try:
        root = ET.fromstring(raw)
    except Exception:
        return out
    for it in root.iter("item"):
        t = clean(it.findtext("title"))
        if not t or any(s in t for s in SKIP) or SKIP_RE.search(t):
            continue
        out.append({"title": t, "link": (it.findtext("link") or "").strip()})
        if len(out) >= limit:
            break
    return out


STOP = set("""의 가 이 은 는 을 를 에 와 과 도 로 으로 에서 에게 만 및 등 이날
그 저 것 수 년 월 일 시 분 대한 관련 위해 통해 대해 오늘 어제 내일 발표 밝혀
した して する され こと ため これ その この もの さん など から まで より
""".split())


def keywords(text):
    ws = re.findall(r"[가-힣]{2,}|[ぁ-んァ-ヶ一-龥]{2,}|[A-Za-z]{3,}", text)
    return [w for w in ws if w not in STOP]


def top_stories(items, n=3):
    freq = Counter()
    for it in items:
        freq.update(set(keywords(it["title"])))
    scored = []
    for it in items:
        kws = set(keywords(it["title"]))
        scored.append((sum(freq[w] for w in kws), it, kws))
    scored.sort(key=lambda x: -x[0])

    picked, used, cats = [], set(), Counter()
    for _, it, kws in scored:
        if kws & used or cats[it.get("cat", "")] >= 2:
            continue
        picked.append(it); used |= kws; cats[it.get("cat", "")] += 1
        if len(picked) >= n:
            return picked
    for _, it, kws in scored:
        if any(it is p for p in picked):
            continue
        if kws and len(kws & used) >= max(2, len(kws) * 2 // 3):
            continue
        picked.append(it); used |= kws
        if len(picked) >= n:
            break
    return picked


def summarize(it, maxlen=70):
    t = re.sub(r"^\[[^\]]{1,10}\]\s*", "", it["title"])
    t = re.sub(r"\s*\((?:종합\d?|영상|포토)\)$", "", t)
    t = re.sub(r"（\d{1,2}:\d{2}）", "", t).strip()
    return t[:maxlen].rstrip() + "…" if len(t) > maxlen else t


def translate(text, src="ja", dst="ko"):
    """일본어 → 한국어 번역 (실패 시 빈 문자열)"""
    try:
        q = urllib.parse.quote(text[:480])
        url = ("https://api.mymemory.translated.net/get"
               "?q={}&langpair={}|{}".format(q, src, dst))
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode())
        out = (d.get("responseData") or {}).get("translatedText", "")
        out = html.unescape(out).strip()
        # 번역 실패 시 API가 경고문을 반환하는 경우 제외
        if not out or "MYMEMORY WARNING" in out.upper():
            return ""
        if out == text:
            return ""
        return out
    except Exception as e:
        print("translate fail: {}".format(e), file=sys.stderr)
        return ""


def build():
    jp, kr = [], []
    for cc, cat, url in FEEDS:
        got = parse(fetch(url))
        for g in got:
            g["cat"] = cat
        (jp if cc == "JP" else kr).extend(got)

    def dedup(lst):
        seen, out = set(), []
        for it in lst:
            k = it["title"][:25]
            if k in seen:
                continue
            seen.add(k); out.append(it)
        return out

    jp, kr = dedup(jp), dedup(kr)
    now = datetime.now(KST)
    L = ["📰 한일 뉴스 3줄 요약",
         now.strftime("%Y년 %m월 %d일 (%a) %H:%M"), "", "🇯🇵 일본"]
    for i, it in enumerate(top_stories(jp), 1):
        orig = summarize(it)
        L.append("{}. {}".format(i, orig))
        ko = translate(orig)
        if ko:
            L.append("   ↳ {}".format(ko))
    L += ["", "🇰🇷 한국"]
    for i, it in enumerate(top_stories(kr), 1):
        L.append("{}. {}".format(i, summarize(it)))
    return "\n".join(L)


def send(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        print("ERROR: TOKEN/CHAT_ID 미설정", file=sys.stderr)
        sys.exit(2)
    url = "https://api.telegram.org/bot{}/sendMessage".format(token)
    data = urllib.parse.urlencode({
        "chat_id": chat, "text": text,
        "disable_web_page_preview": "true"}).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=30) as r:
            res = json.loads(r.read().decode())
            print("발송:", "OK" if res.get("ok") else res)
            return res.get("ok", False)
    except Exception as e:
        print("발송 실패:", e, file=sys.stderr)
        return False


if __name__ == "__main__":
    body = build()
    print(body)
    sys.exit(0 if send(body) else 1)
