#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""텔레그램 봇 폴링 (GitHub Actions용)
정해진 시간 동안 '뉴스' 요청을 감시하고 응답한다.
"""
import os, sys, json, time, urllib.request, urllib.parse
import news as N

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
API = "https://api.telegram.org/bot{}/{}"
TRIGGERS = ("뉴스", "news", "/news", "ニュース", "브리핑")
RUN_SEC = int(os.environ.get("RUN_SECONDS", "3000"))


def api(method, params=None, timeout=40):
    url = API.format(TOKEN, method)
    data = urllib.parse.urlencode(params).encode() if params else None
    try:
        with urllib.request.urlopen(url, data=data, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"ok": False, "err": str(e)}


def send(chat, text):
    return api("sendMessage", {"chat_id": chat, "text": text,
                               "disable_web_page_preview": "true"})


def main():
    if not TOKEN:
        print("TOKEN 미설정", file=sys.stderr)
        sys.exit(2)

    # 시작 시점의 미처리 메시지는 건너뛴다
    res = api("getUpdates", {"offset": -1}, 30)
    offset = 0
    if res.get("ok") and res.get("result"):
        offset = res["result"][-1]["update_id"] + 1

    deadline = time.time() + RUN_SEC
    handled = 0
    print("폴링 시작 ({}초)".format(RUN_SEC))

    while time.time() < deadline:
        wait = max(1, min(25, int(deadline - time.time())))
        res = api("getUpdates",
                  {"offset": offset, "timeout": wait}, wait + 20)
        if not res.get("ok"):
            time.sleep(3)
            continue

        for u in res.get("result", []):
            offset = u["update_id"] + 1
            m = u.get("message") or {}
            text = (m.get("text") or "").strip()
            chat = (m.get("chat") or {}).get("id")
            if not chat or not text:
                continue
            low = text.lower()
            if any(low == t or low.startswith(t) for t in TRIGGERS):
                send(chat, "📰 뉴스를 수집하고 있습니다...")
                try:
                    send(chat, N.build())
                except Exception as e:
                    send(chat, "❌ 수집 실패: {}".format(e))
                handled += 1
                print("응답:", text)
            elif low in ("/start", "/help"):
                send(chat, "안녕하세요! '뉴스'라고 보내시면 "
                           "한일 뉴스 3줄 요약을 보내드립니다.\n"
                           "매일 아침 9시에도 자동으로 발송됩니다.")
                handled += 1

    print("종료 (처리 {}건)".format(handled))


if __name__ == "__main__":
    main()
