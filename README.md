# 🌸 Elliott Wave Stock Recommender

| 분류 | 상태 | 스택 | 바로 보기 |
| --- | --- | --- | --- |
| 핀테크 · 도구 | 보관 | Python · Flask · pandas | — |

# 엘리어트 파동 주식 추천기

**Elliott Wave Theory-based scanner for high-volume Korean stocks with strong upward potential.**

**엘리어트 파동 이론 기반 고거래량 종목 상승 가능성 분석 도구**

A practical Python tool (CLI + beautiful calming web UI) that analyzes the top trading volume stocks using Elliott Wave-inspired heuristics.

거래량(거래대금) 많은 상위 종목 중 엘리어트 파동 관점에서 상승 가능성이 높은 종목을 찾아주는 파이썬 프로그램입니다.

> "Trade calmly." / "마음 편하게 거래하세요."  
> 부드러운 여성향 UI + 강아지·고양이 사진으로 주식할 때 마음이 편안해지도록 설계했습니다. 🐶🐱💕

---

## ✨ 주요 기능 (Features)

### 한국어
- **엘리어트 파동 기반 스마트 스코어링**  
  Impulse 구조, 건강한 조정(피보나치 38~62%), 거래량 확인, EMA 정배열, RSI 건강 구간 등을 종합하여 상승 가능성 점수화
- **고유동성 종목 집중 분석**  
  KOSPI + KOSDAQ 거래대금 상위 N개 자동 선정
- **강력한 CLI 지원**  
  파라미터 조정, CSV 내보내기, matplotlib 차트 생성
- **아름다운 웹 UI (Flask)**  
  - 소프트 파스텔 여성향 디자인 (라벤더 + 블러시 핑크)
  - 완전 반응형 (모바일 완벽 지원)
  - 실시간 정렬·필터 가능한 결과 테이블
  - 점수 배지 시각화
  - 차트 모달 (상위 종목 미리 생성 또는 즉시 생성)
  - **"오늘의 마음 챙김"** 섹션 — 귀여운 강아지·고양이 사진 + 따뜻한 위로 문구
  - 주식하다 지칠 때 마음을 편하게 해주는 것이 목표

### English
- Smart Elliott Wave scoring (impulse detection, Fib retracements, volume confirmation, EMA alignment, RSI zones)
- Focus on high-liquidity stocks (top N by trading value)
- Full-featured CLI with CSV export and charts
- Gorgeous calming web UI with feminine soft pastel design
- "Today's Healing" pet photo gallery for mental relief while trading

---

## 🚀 설치 및 실행 (Installation & Quick Start)

### 설치
```bash
git clone https://github.com/JimProKing/elliott-wave-stock-recommender.git
cd elliott-wave-stock-recommender
pip install -r requirements.txt
```

### 웹 UI 실행 (추천)
```bash
python app.py
```
브라우저에서 http://127.0.0.1:5000 접속

### CLI 사용
```bash
python elliott_wave_volume_scanner.py --top 80 --min-score 55 --plot
```

**주요 옵션 (Common Options)**

| 옵션            | 기본값 | 설명                                      |
|-----------------|--------|-------------------------------------------|
| `--top`         | 100    | 거래대금 상위 N개 종목 스캔               |
| `--min-score`   | 55     | 최소 EW 점수 필터 (0~100)                 |
| `--days`        | 550    | 분석에 사용할 과거 데이터 일수            |
| `--reversal`    | 0.032  | ZigZag 반전 민감도                        |
| `--plot`        | -      | 상위 종목 차트 생성                       |
| `--output`      | csv    | 결과 CSV 파일명                           |

---

## 📊 스코어링 원리 (How the Scoring Works)

### 한국어
이 도구는 실제 엘리어트 파동 카운팅을 근사하는 실용적인 휴리스틱을 사용합니다:
- 장기 상승 추세 (종가 > EMA200)
- EMA 정배열 (21 > 55 > 200)
- 최근 스윙에서 Higher High / Higher Low 구조
- 얕은 되돌림 (대략 피보나치 38~62% 구간 선호)
- Impulse 구간에서의 거래량 확대
- 추가 상승 여력이 있는 RSI 구간 (46~74)

점수가 높을수록 Wave 3 또는 초기 Wave 5 진입 가능성이 높은 것으로 봅니다.

### English
The tool uses practical heuristics that approximate Elliott Wave principles:
- Strong trend (price above EMA200)
- EMA alignment
- Higher Highs / Higher Lows in recent swings
- Healthy corrective retracements (~38-62% Fib zone)
- Volume expansion on impulse moves
- RSI with room to run

Higher scores indicate stronger confluence for potential strong upward moves.

---

## 🛡️ 면책 조항 (Disclaimer)

**이 프로젝트는 교육 및 개인 연구 목적으로만 사용하세요.**

- 엘리어트 파동 이론은 주관적 해석이 많습니다.
- 과거 성과가 미래 수익을 보장하지 않습니다.
- 이 도구의 결과로 인한 어떠한 손실에 대해서도 책임지지 않습니다.
- 실제 투자 결정은 본인의 판단과 충분한 검토, 리스크 관리를 통해 진행해 주세요.

**This project is for educational and personal research purposes only.**

Elliott Wave analysis is highly subjective. The authors are not responsible for any financial losses. Always do your own research.

---

## 🛠 기술 스택 (Tech Stack)

- Python (pandas, numpy, FinanceDataReader, matplotlib)
- Flask (웹 UI)
- Bootstrap 5 + 부드러운 파스텔 커스텀 CSS
- 마음의 평안을 위해 고안된 디자인 (강아지·고양이 사진 포함)

---

## 📁 프로젝트 구조 (Project Structure)

```
.
├── app.py                              # Flask 웹 서버
├── elliott_wave_volume_scanner.py      # 핵심 스캐너 + CLI
├── requirements.txt
├── README.md
├── templates/
│   └── index.html                      # 여성향 calming 웹 UI
└── static/
    └── css/
        └── main.css
```

---

## ❤️ 왜 이렇게 부드러운 디자인인가요?

주식 하다 보면 정말 마음이 지칠 때가 많아요.  
그래서 웹 인터페이스를 일부러 따뜻하고 여성스러운 파스텔 톤으로 만들었고, 분석하는 동안 귀여운 강아지·고양이 사진을 볼 수 있게 했습니다.

조금이라도 마음의 여유를 가지면서 분석할 수 있기를 바랍니다. 🌸

Because trading can be mentally exhausting, the web UI was intentionally made soft, feminine, and calming with cute pet images.

---

## 📝 라이선스

MIT License — 개인 사용 및 수정 자유롭게 하세요.

---

**파도 3을 찾는 모든 트레이더들을 응원합니다.**  
Take a breath. You've got this. 🐾💕

Enjoy responsibly!

---

**관련 저장소** · [xrp-dashboard](https://github.com/JimProKing/xrp-dashboard) · [elliott-wave-scanner](https://github.com/JimProKing/elliott-wave-scanner) · [longshort-han-nune](https://github.com/JimProKing/longshort-han-nune) · [xrpl_examples](https://github.com/JimProKing/xrpl_examples)

<sub>[JimProKing](https://github.com/JimProKing) · 이영찬 — 전체 저장소는 프로필의 프로젝트 지도에서 분야별로 볼 수 있습니다.</sub>
<!-- jpk-footer -->
