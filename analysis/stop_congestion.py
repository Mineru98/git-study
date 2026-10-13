"""정류장 혼잡도 분석과 HTML 시각화.

혼잡도 = 정류장 × 시간대별 일평균 하차인원(여러 노선이 서는 정류장은 노선 합산).
정류장×시간대 히트맵, 가장 혼잡한 정류장·시간대 순위, 시간대별 평균 혼잡도를
plotly 인터랙티브 차트로 그려 reports/stop-congestion/stop_congestion.html 한 파일로 저장한다.

실행: .venv/bin/python analysis/stop_congestion.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from read_bus_data import load_alighting  # noqa: E402

OUT_DIR = ROOT / "reports" / "stop-congestion"
TOP_N = 15
FONT = "Pretendard, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"


def congestion_matrix(alighting: pd.DataFrame) -> pd.DataFrame:
    """정류장명 × 시간대 일평균 하차 표. 행은 일평균 총하차가 많은 정류장부터 정렬한다."""
    n_days = alighting["일자"].nunique()
    matrix = (alighting.pivot_table(index="정류장명", columns="시간대", values="하차인원",
                                    aggfunc="sum", fill_value=0) / n_days)
    return matrix.loc[matrix.sum(axis=1).sort_values(ascending=False).index]


def top_slots(matrix: pd.DataFrame, n: int = TOP_N) -> pd.DataFrame:
    """일평균 하차가 가장 많은 (정류장, 시간대) 조합 상위 n개."""
    long = matrix.stack().rename("일평균하차").reset_index()
    long["구간"] = long["정류장명"] + " " + long["시간대"].astype(str) + "시"
    return long.nlargest(n, "일평균하차").reset_index(drop=True)


def stop_table(matrix: pd.DataFrame) -> pd.DataFrame:
    """정류장별 일평균 하차, 피크 시간대, 피크 시간 일평균 하차."""
    df = pd.DataFrame({
        "일평균하차": matrix.sum(axis=1),
        "피크시간대": matrix.idxmax(axis=1),
        "피크시간일평균하차": matrix.max(axis=1),
    })
    df["피크집중도"] = df["피크시간일평균하차"] / df["일평균하차"]
    return df


def heatmap(matrix: pd.DataFrame) -> go.Figure:
    fig = px.imshow(
        matrix, color_continuous_scale="YlOrRd", aspect="auto",
        labels={"x": "시간대", "y": "정류장", "color": "일평균 하차(명)"},
    )
    fig.update_traces(hovertemplate="%{y} %{x}시<br>일평균 하차 %{z:.1f}명<extra></extra>")
    # 시간대 눈금을 위로 올리면 축 제목이 차트 제목과 겹치므로 축 제목은 지운다
    fig.update_xaxes(dtick=1, ticksuffix="시", side="top", title=None)
    fig.update_layout(title="정류장 × 시간대 혼잡도 (위쪽일수록 하루 하차가 많은 정류장)",
                      height=max(500, 24 * len(matrix)))
    return fig


def top_slots_bar(slots: pd.DataFrame) -> go.Figure:
    fig = px.bar(slots[::-1], x="일평균하차", y="구간", orientation="h",
                 color="일평균하차", color_continuous_scale="YlOrRd",
                 labels={"일평균하차": "일평균 하차(명)", "구간": ""})
    fig.update_traces(hovertemplate="%{y}<br>일평균 하차 %{x:.1f}명<extra></extra>")
    fig.update_layout(title=f"가장 혼잡한 정류장·시간대 TOP {len(slots)}",
                      coloraxis_showscale=False, height=520)
    return fig


def hourly_line(matrix: pd.DataFrame) -> go.Figure:
    hourly = pd.DataFrame({"평균": matrix.mean(), "최대": matrix.max()})
    fig = go.Figure()
    fig.add_scatter(x=hourly.index, y=hourly["최대"], name="가장 붐비는 정류장",
                    mode="lines+markers", line={"color": "#d1495b"},
                    hovertemplate="%{x}시 최대 %{y:.1f}명<extra></extra>")
    fig.add_scatter(x=hourly.index, y=hourly["평균"], name="정류장 평균",
                    mode="lines+markers", line={"color": "#00798c"},
                    hovertemplate="%{x}시 평균 %{y:.1f}명<extra></extra>")
    fig.update_xaxes(title="시간대", dtick=1, ticksuffix="시",
                     range=[hourly.index.min() - 0.5, hourly.index.max() + 0.5])
    fig.update_yaxes(title="일평균 하차(명)")
    fig.update_layout(title="시간대별 혼잡도: 정류장 평균과 최대", height=420)
    return fig


def build_html(alighting: pd.DataFrame, matrix: pd.DataFrame, slots: pd.DataFrame,
               stops: pd.DataFrame) -> str:
    figs = [heatmap(matrix), top_slots_bar(slots), hourly_line(matrix)]
    for fig in figs:
        fig.update_layout(font_family=FONT, margin={"l": 10, "r": 10, "t": 90, "b": 40},
                          template="plotly_white")
    # 첫 차트만 plotly.js 를 CDN 으로 불러오고 나머지는 재사용한다
    charts = "\n".join(
        f'<section class="card">{fig.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False)}</section>'
        for i, fig in enumerate(figs)
    )

    top = slots.iloc[0]
    busiest_hour = int(matrix.sum().idxmax())
    period = f"{alighting['일자'].min():%Y-%m-%d} ~ {alighting['일자'].max():%Y-%m-%d}"
    table = (stops.head(10)
             .assign(일평균하차=lambda d: d["일평균하차"].round(1),
                     피크시간대=lambda d: d["피크시간대"].astype(str) + "시",
                     피크시간일평균하차=lambda d: d["피크시간일평균하차"].round(1),
                     피크집중도=lambda d: (d["피크집중도"] * 100).round(1).astype(str) + "%")
             .rename(columns={"일평균하차": "일평균 하차(명)", "피크시간대": "피크 시간대",
                              "피크시간일평균하차": "피크 시간 하차(명)", "피크집중도": "피크 집중도"})
             .to_html(classes="table", border=0, index_names=False))

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>정류장 혼잡도 리포트</title>
<style>
  body {{ margin: 0; background: #f5f6f8; color: #1f2933; font-family: {FONT}; }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 24px 16px 48px; }}
  h1 {{ margin: 0 0 4px; font-size: 26px; }}
  .sub {{ color: #616e7c; margin: 0 0 20px; }}
  .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 16px; }}
  .kpi, .card {{ background: #fff; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .kpi {{ padding: 14px 16px; }}
  .kpi b {{ display: block; font-size: 22px; margin-top: 4px; font-variant-numeric: tabular-nums; }}
  .kpi span {{ color: #616e7c; font-size: 13px; }}
  .card {{ padding: 8px; margin-bottom: 16px; overflow-x: auto; }}
  .card h2 {{ font-size: 17px; margin: 8px 8px 12px; }}
  .table {{ width: 100%; border-collapse: collapse; font-size: 14px; font-variant-numeric: tabular-nums; }}
  .table th, .table td {{ padding: 8px 10px; border-bottom: 1px solid #e4e7eb; text-align: right; }}
  .table th:first-child, .table td:first-child {{ text-align: left; }}
  .note {{ color: #616e7c; font-size: 13px; }}
</style>
</head>
<body>
<main>
  <h1>정류장 혼잡도 리포트</h1>
  <p class="sub">기간 {period} · 정류장 {len(matrix)}곳 · 혼잡도 = 정류장·시간대별 일평균 하차인원</p>
  <div class="kpis">
    <div class="kpi"><span>가장 혼잡한 구간</span><b>{top['구간']}</b><span>일평균 {top['일평균하차']:.1f}명</span></div>
    <div class="kpi"><span>가장 붐비는 정류장</span><b>{stops.index[0]}</b><span>일평균 {stops['일평균하차'].iloc[0]:.1f}명</span></div>
    <div class="kpi"><span>전체가 가장 붐비는 시간대</span><b>{busiest_hour}시</b><span>정류장 합계 일평균 {matrix[busiest_hour].sum():.1f}명</span></div>
  </div>
  {charts}
  <section class="card">
    <h2>정류장별 혼잡도 TOP 10</h2>
    {table}
    <p class="note">피크 집중도 = 피크 시간 하차 ÷ 하루 하차. 높을수록 특정 시간에 몰린다.</p>
  </section>
</main>
</body>
</html>
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 160)

    alighting = load_alighting()
    matrix = congestion_matrix(alighting)
    slots = top_slots(matrix)
    stops = stop_table(matrix)

    print("== 가장 혼잡한 정류장·시간대 TOP 10 ==")
    print(slots[["정류장명", "시간대", "일평균하차"]].head(10).round(1), "\n")
    print("== 정류장별 혼잡도 TOP 10 ==")
    print(stops.head(10).round(2), "\n")

    path = OUT_DIR / "stop_congestion.html"
    path.write_text(build_html(alighting, matrix, slots, stops), encoding="utf-8")
    print(f"리포트 저장: {path}")


if __name__ == "__main__":
    main()
