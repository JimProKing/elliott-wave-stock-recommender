#!/usr/bin/env python3
"""
Elliott Wave Stock Recommender
High-volume Korean stock scanner based on Elliott Wave Theory.

- Uses FinanceDataReader (Korean market)
- Ranks top N stocks by trading value/volume
- Uses ZigZag + technical indicators to approximate wave structures
- Scores stocks for impulse momentum and upward potential
- Outputs ranked list with reasons + CSV export + optional charts

Disclaimer: Elliott Wave analysis is subjective. This is a heuristic reference tool only.
Investment decisions are your own responsibility.
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

import numpy as np
import pandas as pd
import FinanceDataReader as fdr

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


# -------------------- 지표 계산 --------------------

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """EMA + RSI + 상대거래량 추가 (원본 수정 없이 복사)"""
    out = df.copy()
    out["EMA21"] = out["Close"].ewm(span=21, adjust=False).mean()
    out["EMA55"] = out["Close"].ewm(span=55, adjust=False).mean()
    out["EMA200"] = out["Close"].ewm(span=200, adjust=False).mean()
    out["RSI"] = compute_rsi(out["Close"], 14)
    vol_ma = out["Volume"].rolling(window=20, min_periods=5).mean()
    out["RelVol"] = out["Volume"] / vol_ma
    out["RelVol"] = out["RelVol"].fillna(1.0)
    return out


# -------------------- 스윙(피벗) 검출 - ZigZag 스타일 --------------------

def detect_zigzag_swings(
    df: pd.DataFrame,
    pct_reversal: float = 0.032,
    min_bars_between: int = 3
) -> List[Dict]:
    """
    단순 % 되돌림 기반 ZigZag 스윙 검출.
    - pct_reversal: 반전으로 인정할 최소 되돌림 비율 (0.025~0.04 추천)
    - 반환: [{'idx': int, 'date': Timestamp, 'price': float, 'is_high': bool}, ...]
    """
    if len(df) < 10:
        return []

    closes = df["Close"].values
    dates = df.index

    swings = []
    last_price = closes[0]
    last_idx = 0
    direction = 0  # 1: 상승 스윙 중, -1: 하락 스윙 중

    for i in range(1, len(closes)):
        chg = (closes[i] - last_price) / last_price if last_price != 0 else 0

        if direction == 0:
            if abs(chg) >= pct_reversal:
                direction = 1 if chg > 0 else -1
                last_price = closes[i]
                last_idx = i
        else:
            # 기존 방향 지속 중 반전 확인
            if direction == 1 and chg <= -pct_reversal:
                # 고점 확정, 새 저점 시작
                swings.append({
                    "idx": last_idx,
                    "date": dates[last_idx],
                    "price": last_price,
                    "is_high": True
                })
                direction = -1
                last_price = closes[i]
                last_idx = i
            elif direction == -1 and chg >= pct_reversal:
                # 저점 확정, 새 고점 시작
                swings.append({
                    "idx": last_idx,
                    "date": dates[last_idx],
                    "price": last_price,
                    "is_high": False
                })
                direction = 1
                last_price = closes[i]
                last_idx = i
            else:
                # 같은 방향이면 extreme 갱신 (더 높은 고점 / 더 낮은 저점)
                if (direction == 1 and closes[i] > last_price) or (direction == -1 and closes[i] < last_price):
                    last_price = closes[i]
                    last_idx = i

    # 루프 종료 후 마지막 스윙 추가 (미완성이라도 최근 방향성 반영)
    if direction != 0 and (len(swings) == 0 or last_idx != swings[-1]["idx"]):
        swings.append({
            "idx": last_idx,
            "date": dates[last_idx],
            "price": last_price,
            "is_high": direction == 1
        })

    # 너무 가까운 스윙 필터 (노이즈 제거)
    filtered = []
    for s in swings:
        if not filtered or (s["idx"] - filtered[-1]["idx"] >= min_bars_between):
            filtered.append(s)
    return filtered


# -------------------- 엘리어트 스타일 스코어링 --------------------

def analyze_elliott_setup(df: pd.DataFrame, swings: List[Dict]) -> Tuple[int, List[str], str]:
    """
    엘리어트 파동 이론의 주요 개념을 반영한 상승 가능성 스코어 (0~100)
    - Impulse (1-2-3-4-5) 중 특히 Wave 3 또는 Wave 5 초입 / Wave 1 후반 ~ Wave 3
    - Shallow correction (Wave 2/4) 후 강한 impulse 재개
    - Volume confirmation (impulse wave에서 거래량 확대)
    - Trend alignment (EMA 구조)
    - RSI healthy zone
    - Fibonacci-like retracement (0.382~0.618 zone 선호)

    반환: (score, reasons_kr, wave_position)
    """
    if len(df) < 60 or len(swings) < 3:
        return 25, ["데이터 부족 (최소 60거래일 + 3개 이상 스윙 필요)"], "N/A"

    latest = df.iloc[-1]
    close = float(latest["Close"])
    ema21 = float(latest["EMA21"])
    ema55 = float(latest["EMA55"])
    ema200 = float(latest["EMA200"])
    rsi = float(latest["RSI"])
    rel_vol = float(latest["RelVol"])

    score = 40
    reasons: List[str] = []
    wave_pos = "불명확"

    # 1. 장기 추세 (Wave count의 기반)
    if close > ema200:
        score += 14
        reasons.append("종가 > EMA200 (장기 상승 추세 유지)")
    else:
        score -= 8
        reasons.append("EMA200 하회 (추세 약화 주의)")

    # 2. 단기~중기 구조 (EMA21/55 정렬 = impulse wave 진행 중에 자주 보이는 구조)
    if ema21 > ema55 > ema200:
        score += 10
        reasons.append("EMA 정배열 (21>55>200)")
    elif ema21 > ema55:
        score += 6
        reasons.append("단기 EMA 상승 정렬")

    # 3. 최근 스윙 분석 (가장 중요)
    n = len(swings)
    recent = swings[-min(7, n):]

    # 최근 저점/고점 패턴 카운트 (Higher High / Higher Low)
    hh = hl = 0
    for j in range(1, len(recent)):
        if recent[j]["price"] > recent[j-1]["price"]:
            if recent[j]["is_high"]:
                hh += 1
            else:
                hl += 1

    if hh >= 2 and hl >= 1:
        score += 12
        reasons.append("Higher High + Higher Low 구조 (상승 impulse 진행 중)")
    elif hl >= 2:
        score += 5
        reasons.append("저점 상승 패턴 관찰")

    # 4. 마지막 되돌림(Fib zone) 품질 + impulse 재개 여부
    if len(recent) >= 4:
        p_prev_high = recent[-3]["price"] if recent[-3]["is_high"] else recent[-4]["price"] if len(recent) > 4 else recent[-3]["price"]
        p_last_low = recent[-2]["price"] if not recent[-2]["is_high"] else recent[-3]["price"]
        p_last_high = recent[-1]["price"] if recent[-1]["is_high"] else close

        leg_impulse = abs(p_prev_high - p_last_low)   # 직전 impulse 구간 대랍
        leg_correct = abs(p_last_low - (recent[-3]["price"] if recent[-3]["is_high"] else p_prev_high))

        if leg_impulse > 1e-6:
            retr_ratio = leg_correct / leg_impulse
            if 0.32 <= retr_ratio <= 0.68:
                score += 13
                reasons.append(f"마지막 되돌림 비율 양호 ({retr_ratio*100:.1f}%, Fib 38~62% zone)")
            elif retr_ratio < 0.25:
                score += 4
                reasons.append("얕은 되돌림 (강한 추세)")
            elif retr_ratio > 0.80:
                score -= 6
                reasons.append(f"깊은 되돌림 ({retr_ratio*100:.1f}%) - 추세 전환 가능성")

        # 현재 위치 대랍 추정
        if recent[-1]["is_high"]:
            # 최근 고점 형성 중 → Wave 3 또는 5 가능성
            if hh >= 2:
                wave_pos = "Wave 3 또는 Wave 5 진행 중"
            else:
                wave_pos = "상승 파동 (impulse) 후반"
        else:
            # 최근 저점 → Wave 2 또는 Wave 4 종료 후 Wave 3/5 시작 기대
            if close > ema55:
                wave_pos = "Wave 2/4 종료 후 Wave 3/5 초기 반등 가능성 높음"
                score += 8
            else:
                wave_pos = "저점 확인 중 (반등 확인 필요)"

    # 5. 거래량 확인 (Elliott의 핵심: impulse wave에서 volume 확대)
    if rel_vol >= 1.4:
        score += 9
        reasons.append(f"상대거래량 급증 (RelVol={rel_vol:.1f}) - impulse wave 확인 강도 높음")
    elif rel_vol >= 1.15:
        score += 5
        reasons.append(f"거래량 양호 (RelVol={rel_vol:.1f})")

    # 6. RSI 모멘텀 (Wave 3은 보통 RSI 50~75 구간에서 강하게 진행)
    if 46 <= rsi <= 74:
        score += 9
        reasons.append(f"RSI 양호 구간 ({rsi:.0f}) - 추가 상승 여력")
    elif rsi > 82:
        score -= 7
        reasons.append(f"RSI 과열 ({rsi:.0f}) - Wave 5 exhaustion 위험")
    elif rsi < 38:
        score += 3
        reasons.append(f"RSI 침체 ({rsi:.0f}) - 반등 시 Wave 1 시작 후보")

    # 7. 최근 가격 모멘텀 (간단 확인)
    if len(df) >= 6:
        ret_5 = (close / df["Close"].iloc[-6] - 1.0) * 100
        if ret_5 >= 6.0:
            score += 7
            reasons.append(f"최근 5거래일 강한 상승 (+{ret_5:.1f}%)")
        elif ret_5 <= -6.0:
            score -= 4

    # 최종 보정
    score = max(0, min(100, int(round(score))))

    if not reasons:
        reasons.append("중립적 구조")

    return score, reasons, wave_pos


# -------------------- 메인 스켄 로직 --------------------

def get_top_volume_tickers(top_n: int = 100, by: str = "Amount") -> pd.DataFrame:
    """
    FDR KRX listing에서 거래대금(Amount) 또는 거래량(Volume) 기준 상위 종목 추출.
    스팩/ETF/ETN 등은 간단 필터로 제외 시도.
    """
    listing = fdr.StockListing("KRX")
    # 영문 컬럼: Code, Name, Market, Volume, Amount ...
    df = listing.copy()

    # 기본 필터: KOSPI / KOSDAQ 만
    df = df[df["Market"].isin(["KOSPI", "KOSDAQ"])]

    # 비주식 성격 대랍 제외 (이름 기반)
    exclude_keywords = ["ETF", "ETN", "인버스", "레버리지", "스팩", "SPAC", "TIGER", "KODEX", "ARIRANG", "HANARO", "SOL", "KBSTAR"]
    for kw in exclude_keywords:
        df = df[~df["Name"].str.contains(kw, case=False, na=False)]

    # 거래대금 우선, 없으면 Volume
    sort_col = "Amount" if by.lower() == "amount" and "Amount" in df.columns else "Volume"
    if sort_col not in df.columns:
        sort_col = "Volume"

    df = df.sort_values(sort_col, ascending=False).head(top_n).reset_index(drop=True)
    return df[["Code", "Name", "Market", "Close", "Volume", "Amount", "Marcap"]]


def fetch_history(code: str, days: int = 550) -> Optional[pd.DataFrame]:
    """최근 N거래일 히스토리 로드 (영업일 기준 여유있게)"""
    end = datetime.now()
    start = end - timedelta(days=days + 30)
    try:
        df = fdr.DataReader(code, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
        if df is None or len(df) < 30:
            return None
        # 표준화
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        return df
    except Exception:
        return None


def scan(
    top_n: int = 100,
    history_days: int = 550,
    min_score: int = 0,
    reversal_pct: float = 0.032,
    verbose: bool = True
) -> pd.DataFrame:
    """
    상위 거래량 종목 대상 엘리어트 기반 스켄 실행.
    반환: 분석 결과 DataFrame (점수 내림차순)
    """
    if verbose:
        print(f"[1/3] 거래대금 상위 {top_n}개 종목 로드 중 ...")
    tickers = get_top_volume_tickers(top_n)
    if verbose:
        print(f"      -> {len(tickers)}개 후보 선정 완료")

    results = []

    if verbose:
        print(f"[2/3] 각 종목 히스토리({history_days}일) + 파동 분석 중 ... (시간 소요될 수 있음)")

    for i, row in tickers.iterrows():
        code = row["Code"]
        name = row["Name"]
        market = row["Market"]
        latest_close = row["Close"]
        latest_vol = row["Volume"]
        latest_amt = row.get("Amount", 0)

        if verbose and (i % 10 == 0 or i < 5):
            print(f"  [{i+1:3d}/{len(tickers)}] {code} {name}")

        hist = fetch_history(code, history_days)
        if hist is None:
            continue

        hist = add_indicators(hist)
        swings = detect_zigzag_swings(hist, pct_reversal=reversal_pct)

        score, reasons, wave_pos = analyze_elliott_setup(hist, swings)

        if score < min_score:
            continue

        latest_row = hist.iloc[-1]

        results.append({
            "순위": 0,  # 나중에 재할당
            "종목코드": code,
            "종목명": name,
            "시장": market,
            "현재가": round(latest_close, 0),
            "거래량": int(latest_vol),
            "거래대금(억)": round(latest_amt / 1e8, 1) if latest_amt else 0,
            "EW점수": score,
            "파동위치추정": wave_pos,
            "RSI": round(float(latest_row["RSI"]), 1),
            "RelVol": round(float(latest_row["RelVol"]), 2),
            "사유": " / ".join(reasons[:3]),   # 상위 3개만
            "분석일": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

    if not results:
        print("조건에 맞는 종목이 없습니다.")
        return pd.DataFrame()

    res_df = pd.DataFrame(results)
    res_df = res_df.sort_values("EW점수", ascending=False).reset_index(drop=True)
    res_df["순위"] = range(1, len(res_df) + 1)

    # 컬럼 순서 정리
    cols = ["순위", "종목코드", "종목명", "시장", "현재가", "거래량", "거래대금(억)",
            "EW점수", "파동위치추정", "RSI", "RelVol", "사유", "분석일"]
    res_df = res_df[cols]

    if verbose:
        print(f"[3/3] 분석 완료. 조건 통과 종목: {len(res_df)}개")

    return res_df


# -------------------- 결과 출력 / 저장 / 플롯 --------------------

def pretty_print(df: pd.DataFrame, top_k: int = 20):
    if df.empty:
        print("결과 없음")
        return
    print("\n" + "=" * 100)
    print("엘리어트 파동 기반 고거래량 종목 상승 스켄 결과 (상위 {})개".format(min(top_k, len(df))))
    print("=" * 100)
    view = df.head(top_k)[["순위", "종목코드", "종목명", "현재가", "EW점수", "파동위치추정", "RSI", "사유"]].copy()
    # 보기 좋게
    pd.set_option("display.max_colwidth", 70)
    pd.set_option("display.width", 200)
    print(view.to_string(index=False))
    print("=" * 100)
    print("EW점수: 엘리어트 파동 impulse 구조 + 거래량 + 되돌림 품질 + 모멘텀 종합 (100점 만점)")
    print("파동위치추정: 최근 ZigZag 스윙 기준 휴리스틱 (정확한 파동 카운트는 차트에서 직접 확인 권장)")
    print("=" * 100 + "\n")


def save_csv(df: pd.DataFrame, path: str = "ew_volume_scan_results.csv"):
    if df.empty:
        return
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"CSV 저장 완료: {path}")


def _setup_korean_font():
    """Windows/Linux/macOS에서 한글 폰트 자동 설정 시도 (matplotlib 차트용)"""
    if not HAS_MPL:
        return
    import os
    import matplotlib.font_manager as fm
    import matplotlib.pyplot as plt
    candidates = [
        "Malgun Gothic", "맑은 고딕", "AppleGothic", "NanumGothic", "Noto Sans CJK KR",
        "DejaVu Sans", "sans-serif"
    ]
    for name in candidates:
        try:
            # 시스템에 설치된 폰트 중 이름 매칭
            font_path = fm.findfont(fm.FontProperties(family=name))
            if font_path and os.path.exists(font_path):
                plt.rcParams["font.family"] = name
                plt.rcParams["axes.unicode_minus"] = False
                return
        except Exception:
            pass
    # fallback
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False


def plot_top_candidates(df_results: pd.DataFrame, top_k: int = 5, save_dir: str = "."):
    """
    상위 종목에 대해 간단 차트 + 최근 스윙 표시 (matplotlib 필요)
    """
    if not HAS_MPL or df_results.empty:
        print("matplotlib 미설치 또는 결과 없음 → 차트 생략")
        return

    _setup_korean_font()

    import os
    os.makedirs(save_dir, exist_ok=True)

    print(f"\n상위 {min(top_k, len(df_results))}개 종목 차트 생성 중...")
    for _, r in df_results.head(top_k).iterrows():
        code = r["종목코드"]
        name = r["종목명"]
        score = r["EW점수"]

        hist = fetch_history(code, 450)
        if hist is None or len(hist) < 30:
            continue

        hist = add_indicators(hist)
        swings = detect_zigzag_swings(hist, pct_reversal=0.032)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), gridspec_kw={"height_ratios": [3, 1]}, sharex=True)

        # 가격 + EMA
        ax1.plot(hist.index, hist["Close"], label="Close", linewidth=1.5, color="#222222")
        ax1.plot(hist.index, hist["EMA21"], label="EMA21", linewidth=1, alpha=0.8)
        ax1.plot(hist.index, hist["EMA55"], label="EMA55", linewidth=1, alpha=0.8)
        ax1.plot(hist.index, hist["EMA200"], label="EMA200", linewidth=1.2, linestyle="--", alpha=0.7)

        # 스윙 표시
        for s in swings[-10:]:  # 최근 10개만
            color = "red" if s["is_high"] else "blue"
            marker = "^" if s["is_high"] else "v"
            ax1.scatter(s["date"], s["price"], marker=marker, s=70, color=color, zorder=5, edgecolors="white", linewidths=0.5)

        ax1.set_title(f"{name} ({code})  |  EW Score: {score}  |  {r['파동위치추정']}")
        ax1.legend(loc="upper left", fontsize=9)
        ax1.grid(True, alpha=0.3)
        ax1.set_ylabel("Price")

        # RSI
        ax2.plot(hist.index, hist["RSI"], color="purple", linewidth=1)
        ax2.axhline(70, color="red", linestyle="--", alpha=0.5)
        ax2.axhline(30, color="blue", linestyle="--", alpha=0.5)
        ax2.fill_between(hist.index, 30, 70, alpha=0.08)
        ax2.set_ylim(0, 100)
        ax2.set_ylabel("RSI(14)")
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        safe_name = name.replace("/", "_").replace(" ", "")
        out_path = f"{save_dir}/ew_{code}_{safe_name}.png"
        plt.savefig(out_path, dpi=140, bbox_inches="tight")
        plt.close()
        print(f"  차트 저장: {out_path}")


# -------------------- 웹/재사용용 헬퍼 (Flask 연동용) --------------------

def generate_chart_bytes(code: str, name: str = "", score: int = 0, wave_pos: str = "") -> Optional[bytes]:
    """
    단일 종목에 대해 엘리어트 분석 차트 PNG를 bytes로 생성해서 반환.
    Flask에서 바로 응답하거나 base64로 템플릿에 임베드할 때 사용.
    """
    if not HAS_MPL:
        return None
    try:
        hist = fetch_history(code, 450)
        if hist is None or len(hist) < 30:
            return None
        hist = add_indicators(hist)
        swings = detect_zigzag_swings(hist, pct_reversal=0.032)

        _setup_korean_font()  # 이미 scanner에 있음

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), gridspec_kw={"height_ratios": [3, 1]}, sharex=True)

        ax1.plot(hist.index, hist["Close"], label="Close", linewidth=1.6, color="#222222")
        ax1.plot(hist.index, hist["EMA21"], label="EMA21", linewidth=1.1, alpha=0.85)
        ax1.plot(hist.index, hist["EMA55"], label="EMA55", linewidth=1.1, alpha=0.85)
        ax1.plot(hist.index, hist["EMA200"], label="EMA200", linewidth=1.3, linestyle="--", alpha=0.75, color="#c0392b")

        for s in swings[-9:]:
            color = "#c0392b" if s["is_high"] else "#2980b9"
            marker = "^" if s["is_high"] else "v"
            ax1.scatter(s["date"], s["price"], marker=marker, s=85, color=color, zorder=5,
                        edgecolors="white", linewidths=0.6)

        title = f"{name or code} ({code})"
        if score:
            title += f"  |  EW Score: {score}"
        if wave_pos:
            title += f"  |  {wave_pos}"
        ax1.set_title(title, fontsize=13, pad=10)
        ax1.legend(loc="upper left", fontsize=9, framealpha=0.9)
        ax1.grid(True, alpha=0.25)
        ax1.set_ylabel("Price (KRW)")

        ax2.plot(hist.index, hist["RSI"], color="#6f42c1", linewidth=1.2)
        ax2.axhline(70, color="#dc3545", linestyle="--", linewidth=0.9, alpha=0.7)
        ax2.axhline(30, color="#0d6efd", linestyle="--", linewidth=0.9, alpha=0.7)
        ax2.fill_between(hist.index, 30, 70, alpha=0.06, color="#6f42c1")
        ax2.set_ylim(0, 100)
        ax2.set_ylabel("RSI (14)")
        ax2.grid(True, alpha=0.25)

        plt.tight_layout()

        from io import BytesIO
        buf = BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        if 'fig' in locals():
            plt.close(fig)
        return None


# -------------------- CLI --------------------

def main():
    parser = argparse.ArgumentParser(
        description="Elliott Wave Stock Recommender - High volume stock scanner based on Elliott Wave Theory"
    )
    parser.add_argument("--top", type=int, default=100, help="거래대금 상위 N개 (기본 100)")
    parser.add_argument("--days", type=int, default=550, help="히스토리 조회 기간 (거래일 여유 포함, 기본 550)")
    parser.add_argument("--min-score", type=int, default=55, help="최소 EW 점수 필터 (기본 55)")
    parser.add_argument("--reversal", type=float, default=0.032, help="ZigZag 반전 민감도 (기본 3.2%%)")
    parser.add_argument("--output", type=str, default="ew_scan_results.csv", help="결과 CSV 파일명")
    parser.add_argument("--plot", action="store_true", help="상위 종목 차트 PNG 저장 (matplotlib 필요)")
    parser.add_argument("--plot-dir", type=str, default="ew_charts", help="차트 저장 폴더")
    parser.add_argument("--no-print", action="store_true", help="콘솔 테이블 출력 생략")
    args = parser.parse_args()

    print("\n[엘리어트 파동 + 고거래량 스켄너] 시작")
    print(f"  - 상위 거래대금 종목: {args.top}개")
    print(f"  - 분석 기간: 최근 ~{args.days}일")
    print(f"  - 최소 점수: {args.min_score}")
    print(f"  - ZigZag 민감도: {args.reversal*100:.1f}%")
    print()

    df = scan(
        top_n=args.top,
        history_days=args.days,
        min_score=args.min_score,
        reversal_pct=args.reversal,
        verbose=True
    )

    if df.empty:
        print("스켄 결과가 없습니다. (조건을 완화해보세요: --min-score 40)")
        sys.exit(0)

    if not args.no_print:
        pretty_print(df, top_k=25)

    save_csv(df, args.output)

    if args.plot:
        if not HAS_MPL:
            print("matplotlib이 설치되어 있지 않아 차트를 생성할 수 없습니다.")
            print("pip install matplotlib 후 --plot 옵션 사용")
        else:
            plot_top_candidates(df, top_k=6, save_dir=args.plot_dir)

    print("\n완료. 결과 파일:", args.output)
    print("팁: --plot 으로 상위 종목의 스윙 차트를 함께 확인하세요.")
    print("     --min-score 조정, --reversal 조정으로 민감도 변경 가능\n")


if __name__ == "__main__":
    main()
