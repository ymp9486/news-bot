#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""워크플로우 만료(60일) 방지 + 텔레그램 경고 알림

GitHub은 저장소에 60일간 활동이 없으면 schedule 트리거를 자동 비활성화한다.
이 스크립트는 매주 실행되어:
  1) keepalive 파일을 갱신·커밋하여 만료 타이머를 리셋한다
  2) 마지막 커밋 이후 경과일을 계산해 위험 구간이면 텔레그램으로 경고한다
"""
import os, sys, json, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
REPO = os.environ.get("GITHUB_REPOSITORY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "").strip()
WARN_DAYS = int(os.environ.get("WARN_DAYS", "45"))   # 이 날짜를 넘기면 경고
STAMP = "keepalive.txt"


def gh(path, method="GET", body=None):
    url = "https://api.github.com" + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", "Bearer " + GH_TOKEN)
    r.add_header("Accept", "application/vnd.github+json")
    r.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except Exception as e:
        return 0, {"error": str(e)}


def tg(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        print("텔레그램 설정 없음", file=sys.stderr)
        return False
    url = "https://api.telegram.org/bot{}/sendMessage".format(token)
    data = urllib.parse.urlencode({
        "chat_id": chat, "text": text,
        "disable_web_page_preview": "true"}).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=30) as r:
            return json.loads(r.read().decode()).get("ok", False)
    except Exception as e:
        print("텔레그램 발송 실패:", e, file=sys.stderr)
        return False


def main():
    now = datetime.now(timezone.utc)

    # 1) 마지막 커밋 시점 조회
    st, commits = gh("/repos/{}/commits?per_page=1".format(REPO))
    days = None
    if st == 200 and commits:
        last = commits[0]["commit"]["committer"]["date"]
        dt = datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
        days = (now - dt).days
        print("마지막 커밋: {} ({}일 전)".format(last, days))

    # 2) keepalive 커밋으로 만료 타이머 리셋
    body = now.astimezone(KST).strftime(
        "last keepalive: %Y-%m-%d %H:%M KST\n")
    import base64
    payload = {"message": "chore: keepalive",
               "content": base64.b64encode(body.encode()).decode()}
    st, cur = gh("/repos/{}/contents/{}".format(REPO, STAMP))
    if st == 200 and isinstance(cur, dict) and cur.get("sha"):
        payload["sha"] = cur["sha"]
    st, r = gh("/repos/{}/contents/{}".format(REPO, STAMP), "PUT", payload)
    ok = st in (200, 201)
    print("keepalive 커밋:", "성공" if ok else r)

    # 3) 알림 판단
    if not ok:
        tg("⚠️ 뉴스봇 자동 연장 실패\n\n"
           "keepalive 커밋에 실패했습니다.\n"
           "60일이 지나면 매일 9시 발송이 중단됩니다.\n\n"
           "확인: https://github.com/{}/actions".format(REPO))
        sys.exit(1)

    if days is not None and days >= WARN_DAYS:
        tg("🔔 뉴스봇 자동 연장 완료\n\n"
           "마지막 활동으로부터 {}일이 지나\n"
           "방금 자동으로 연장했습니다.\n\n"
           "✅ 매일 09:00 뉴스 발송 정상 유지\n"
           "✅ 별도 조치는 필요 없습니다\n\n"
           "저장소: https://github.com/{}".format(days, REPO))
        print("연장 알림 발송 완료")
    else:
        print("정상 (경고 불필요, 경과 {}일 < 기준 {}일)".format(
            days, WARN_DAYS))


if __name__ == "__main__":
    main()
