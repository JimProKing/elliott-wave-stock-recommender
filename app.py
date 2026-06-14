#!/usr/bin/env python3
"""
Elliott Wave Stock Recommender - Flask Web Version
Beautiful, calming web UI with feminine soft pastel theme + cute dog & cat images for stress relief while trading.

Based on Elliott Wave Theory for scanning high trading volume stocks with high upward potential.

Local run: python app.py
Access: http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, jsonify, send_file, make_response
from io import BytesIO
import base64
from datetime import datetime
import os

# 기존 스캐너 로직 재사용 (강력 권장)
try:
    from elliott_wave_volume_scanner import (
        scan, 
        generate_chart_bytes,
        HAS_MPL
    )
except ImportError:
    # 개발 편의를 위해 직접 import 경로 조정
    import sys
    sys.path.append(os.path.dirname(__file__))
    from elliott_wave_volume_scanner import scan, generate_chart_bytes, HAS_MPL

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 한글 JSON 정상 처리

# 메모리 캐시 (로컬 단일 사용자용)
_last_scan = {
    "data": None,
    "timestamp": None,
    "params": None
}


def df_to_records(df):
    """pandas DataFrame → list of dict (JSON 직렬화용)"""
    if df is None or df.empty:
        return []
    # 숫자 포맷 정리 (필요 시)
    records = df.to_dict(orient="records")
    return records


@app.route("/")
def index():
    """메인 페이지 (반응형)"""
    return render_template(
        "index.html",
        default_top=100,
        default_min_score=55,
        default_days=550,
        default_reversal=0.032,
        has_mpl=HAS_MPL
    )


@app.route("/api/scan", methods=["POST"])
def api_scan():
    """
    스켄 실행 API (JSON)
    폼 데이터: top, min_score, days, reversal
    """
    try:
        top = int(request.form.get("top", 100))
        min_score = int(request.form.get("min_score", 55))
        days = int(request.form.get("days", 550))
        reversal = float(request.form.get("reversal", 0.032))

        # 범위 제한 (안전)
        top = max(5, min(top, 300))
        min_score = max(0, min(min_score, 100))
        days = max(100, min(days, 1200))
        reversal = max(0.01, min(reversal, 0.10))

        print(f"[Flask] 스켄 시작: top={top}, min_score={min_score}, days={days}, reversal={reversal}")

        df = scan(
            top_n=top,
            history_days=days,
            min_score=min_score,
            reversal_pct=reversal,
            verbose=False   # 웹에서는 출력 최소화
        )

        if df is None or df.empty:
            return jsonify({
                "success": False,
                "message": "조건에 맞는 종목이 없습니다. 최소 점수를 낮춰보세요.",
                "data": [],
                "summary": {}
            }), 200

        records = df_to_records(df)

        # 요약 정보
        avg_score = round(df["EW점수"].mean(), 1) if not df.empty else 0
        high_score_count = int((df["EW점수"] >= 80).sum())
        summary = {
            "total_analyzed": len(df),
            "avg_score": avg_score,
            "high_score_count": high_score_count,
            "top_score": int(df["EW점수"].max()) if not df.empty else 0,
            "params": {"top": top, "min_score": min_score, "days": days, "reversal": reversal}
        }

        # 캐시 저장 (마지막 결과)
        global _last_scan
        _last_scan = {
            "data": records,
            "timestamp": datetime.now().isoformat(),
            "params": summary["params"]
        }

        # 상위 종목 차트 base64 미리 생성 (최대 6개)
        chart_data = {}
        if HAS_MPL:
            top_n_for_chart = min(6, len(records))
            for i in range(top_n_for_chart):
                rec = records[i]
                code = rec.get("종목코드")
                name = rec.get("종목명", "")
                score = rec.get("EW점수", 0)
                wave = rec.get("파동위치추정", "")
                png_bytes = generate_chart_bytes(code, name, score, wave)
                if png_bytes:
                    b64 = base64.b64encode(png_bytes).decode("ascii")
                    chart_data[code] = b64

        return jsonify({
            "success": True,
            "data": records,
            "summary": summary,
            "timestamp": _last_scan["timestamp"],
            "charts": chart_data   # code -> base64 png
        })

    except Exception as e:
        print(f"[Flask ERROR] scan failed: {e}")
        return jsonify({
            "success": False,
            "message": f"스켄 중 오류가 발생했습니다: {str(e)[:120]}",
            "data": [],
            "summary": {}
        }), 500


@app.route("/api/chart/<code>")
def api_chart(code):
    """단일 종목 차트 PNG 즉시 생성 (추가 요청용)"""
    if not HAS_MPL:
        return "matplotlib이 설치되지 않았습니다.", 400

    name = request.args.get("name", code)
    score = int(request.args.get("score", 0))
    wave = request.args.get("wave", "")

    png = generate_chart_bytes(code, name, score, wave)
    if not png:
        return "차트를 생성할 수 없습니다.", 404

    return send_file(
        BytesIO(png),
        mimetype="image/png",
        as_attachment=False,
        download_name=f"chart_{code}.png"
    )


@app.route("/api/last")
def api_last():
    """마지막 스켄 결과 반환 (새로고침 시 빠른 복원)"""
    global _last_scan
    if _last_scan["data"]:
        return jsonify({
            "success": True,
            "data": _last_scan["data"],
            "timestamp": _last_scan["timestamp"],
            "params": _last_scan.get("params", {})
        })
    return jsonify({"success": False, "message": "이전 스켄 결과가 없습니다."})


@app.route("/api/export")
def api_export():
    """현재 캐시된 결과를 CSV로 다운로드"""
    global _last_scan
    if not _last_scan["data"]:
        return "스켄 결과가 없습니다. 먼저 스켄을 실행하세요.", 400

    import pandas as pd
    df = pd.DataFrame(_last_scan["data"])

    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
    csv_buffer.seek(0)

    resp = make_response(csv_buffer.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    resp.headers["Content-Disposition"] = f'attachment; filename=ew_scan_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    return resp


if __name__ == "__main__":
    print("=" * 60)
    print("Elliott Wave Stock Recommender - Web Server Started")
    print("Access: http://127.0.0.1:5000")
    print("Calming feminine UI with pet healing images")
    print("=" * 60)
    # debug=True 는 개발용, 로컬에서 편리
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
