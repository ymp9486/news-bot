# 한일 뉴스 브리핑 봇

매일 아침 9시(KST) 일본·한국 주요 뉴스를 3줄로 요약해 텔레그램으로 발송합니다.

## 기능

- **자동 발송** — 매일 09:00 KST
- **요청 응답** — 텔레그램에 `뉴스` 입력 시 즉시 발송

## 뉴스 소스

| 국가 | 매체 |
|---|---|
| 🇯🇵 일본 | NHK (사회·정치·경제) |
| 🇰🇷 한국 | 연합뉴스, 한겨레, 경향신문 |

## 설정 방법

### 1. Secrets 등록

저장소 **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather에서 받은 토큰 |
| `TELEGRAM_CHAT_ID` | 내 채팅방 ID |

### 2. Actions 활성화

**Actions** 탭 → `I understand my workflows, go ahead and enable them`

### 3. 테스트

**Actions → 뉴스 브리핑 → Run workflow** 로 즉시 실행

## 파일 구성

```
news.py                          뉴스 수집 + 3줄 요약 + 발송
bot.py                           텔레그램 요청 응답 폴링
keepalive.py                     60일 만료 방지 + 알림
.github/workflows/news.yml       매일 9시 자동 발송
.github/workflows/bot.yml        50분마다 봇 폴링
.github/workflows/keepalive.yml  매주 월요일 자동 연장
```

## 자동 연장

GitHub은 저장소에 60일간 활동이 없으면 스케줄을 자동으로 중지합니다.
`keepalive.yml` 이 **매주 월요일** 실행되어 자동으로 커밋을 남기므로
사용자가 직접 조치할 필요가 없습니다.

- 자동 연장 실패 시 텔레그램으로 즉시 경고
- 마지막 활동이 45일을 넘으면 알림 발송

## 시간 변경

`.github/workflows/news.yml` 의 cron 값을 수정합니다. **UTC 기준**이므로 한국시간에서 9를 뺍니다.

| 원하는 시각 (KST) | cron |
|---|---|
| 07:00 | `0 22 * * *` |
| 08:00 | `0 23 * * *` |
| 09:00 | `0 0 * * *` |
| 12:00 | `0 3 * * *` |

## 참고

- GitHub Actions의 스케줄은 서버 부하에 따라 **수 분~수십 분 지연**될 수 있습니다.
- 퍼블릭 저장소는 Actions 사용량이 무료입니다.
- 60일 만료는 `keepalive.yml` 이 자동으로 방지합니다.
