"""정류장 핫스팟·환승 거점 분석.

정류장별 하차 순위, 경유 노선 수(환승 후보), 하차 집중도(파레토), 피크 시간대,
노선 내 위치(기점/중간/종점부)별 하차 패턴을 집계하고 차트를 reports/stop-hotspot/ 에 저장한다.

실행: .venv/bin/python analysis/stop_hotspot.py
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from read_bus_data import load_alighting, load_routes  # noqa: E402

OUT_DIR = ROOT / "reports" / "stop-hotspot"

plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False


def stop_summary(alighting: pd.DataFrame, route_stops: pd.DataFrame) -> pd.DataFrame:
    """정류장별 총/일평균 하차, 경유 노선 수, 피크 시간대를 한 표로 만든다."""
    n_days = alighting["일자"].nunique()
    total = alighting.groupby(["정류장ID", "정류장명"])["하차인원"].sum().rename("총하차")

    n_routes = route_stops.groupby("정류장ID")["노선번호"].nunique().rename("경유노선수")
    routes_list = (route_stops.groupby("정류장ID")["노선번호"]
                   .apply(lambda s: ",".join(sorted(s.unique()))).rename("경유노선"))

    by_hour = alighting.groupby(["정류장ID", "시간대"])["하차인원"].sum().unstack(fill_value=0)
    peak_hour = by_hour.idxmax(axis=1).rename("피크시간대")
    peak_share = (by_hour.max(axis=1) / by_hour.sum(axis=1)).rename("피크시간점유율")

    df = (total.reset_index()
          .join(n_routes, on="정류장ID").join(routes_list, on="정류장ID")
          .join(peak_hour, on="정류장ID").join(peak_share, on="정류장ID"))
    df["일평균하차"] = df["총하차"] / n_days
    df["노선당일평균하차"] = df["일평균하차"] / df["경유노선수"]
    df = df.sort_values("총하차", ascending=False).reset_index(drop=True)
    df.index = df.index + 1
    df.index.name = "순위"
    df["누적점유율"] = df["총하차"].cumsum() / df["총하차"].sum()
    return df


def position_pattern(alighting: pd.DataFrame, route_stops: pd.DataFrame) -> pd.DataFrame:
    """노선 내 정류장순번 상대위치를 기점부/중간부/종점부로 나눠 하차를 비교한다."""
    rs = route_stops.copy()
    n_stops = rs.groupby("노선번호")["정류장순번"].transform("max")
    rel = (rs["정류장순번"] - 1) / (n_stops - 1)
    rs["위치"] = pd.cut(rel, bins=[-0.01, 1 / 3, 2 / 3, 1.0], labels=["기점부", "중간부", "종점부"])

    per_route_stop = (alighting.groupby(["노선번호", "정류장ID"])["하차인원"].sum()
                      .rename("하차").reset_index()
                      .merge(rs[["노선번호", "정류장ID", "위치"]], on=["노선번호", "정류장ID"]))
    n_days = alighting["일자"].nunique()
    out = per_route_stop.groupby("위치", observed=True).agg(
        정류장수=("정류장ID", "size"), 총하차=("하차", "sum"), 정류장당하차=("하차", "mean"))
    out["정류장당일평균하차"] = out["정류장당하차"] / n_days
    out["하차점유율"] = out["총하차"] / out["총하차"].sum()
    return out


def plot_pareto(summary: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 5.5))
    colors = ["#d1495b" if r >= 3 else "#8da9c4" for r in summary["경유노선수"]]
    ax.bar(summary["정류장명"], summary["일평균하차"], color=colors)
    ax.set_ylabel("일평균 하차인원(명)")
    ax.set_title("정류장별 일평균 하차와 누적 점유율 (빨강: 경유 노선 3개 이상)")
    ax.tick_params(axis="x", rotation=70, labelsize=8)
    ax2 = ax.twinx()
    ax2.plot(summary["정류장명"], summary["누적점유율"] * 100, color="#2e4057", marker="o", ms=3)
    ax2.axhline(80, color="gray", ls="--", lw=0.8)
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("누적 점유율(%)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_routes_vs_volume(summary: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.scatter(summary["경유노선수"], summary["일평균하차"], s=50, color="#00798c", alpha=0.8)
    for _, row in summary.head(6).iterrows():
        ax.annotate(row["정류장명"], (row["경유노선수"], row["일평균하차"]),
                    textcoords="offset points", xytext=(5, 3), fontsize=8)
    mean_by_n = summary.groupby("경유노선수")["일평균하차"].mean()
    ax.plot(mean_by_n.index, mean_by_n.values, color="#d1495b", marker="s", label="경유 노선 수별 평균")
    ax.set_xlabel("경유 노선 수")
    ax.set_ylabel("일평균 하차인원(명)")
    ax.set_title("경유 노선 수와 정류장 하차량")
    ax.set_xticks(sorted(summary["경유노선수"].unique()))
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)

    _, route_stops = load_routes()
    alighting = load_alighting()

    summary = stop_summary(alighting, route_stops)
    grand = summary["총하차"].sum()

    print("== 정류장별 하차 순위 TOP 10 ==")
    cols = ["정류장명", "총하차", "일평균하차", "경유노선수", "경유노선", "피크시간대", "피크시간점유율"]
    print(summary[cols].head(10).round(2), "\n")

    print("== 환승 후보 (경유 노선 3개 이상) ==")
    hubs = summary[summary["경유노선수"] >= 3]
    print(hubs[["정류장명", "경유노선수", "경유노선", "일평균하차"]].round(1), "\n")

    print("== 경유 노선 수별 하차 ==")
    by_n = summary.groupby("경유노선수").agg(정류장수=("정류장ID", "size"),
                                         평균일하차=("일평균하차", "mean"),
                                         노선당일하차=("노선당일평균하차", "mean"))
    print(by_n.round(1))
    corr = summary["경유노선수"].corr(summary["일평균하차"])
    print(f"상관계수(경유노선수 vs 일평균하차) = {corr:.3f}\n")

    n_top = max(1, round(len(summary) * 0.2))
    top_share = summary["총하차"].head(n_top).sum() / grand
    n_80 = int((summary["누적점유율"] < 0.8).sum()) + 1
    print("== 하차 집중도 ==")
    print(f"정류장 {len(summary)}개 중 상위 20%({n_top}개) 점유율 = {top_share:.1%}")
    print(f"하차 80% 도달에 필요한 정류장 수 = {n_80}개 ({n_80 / len(summary):.0%})\n")

    print("== 피크 시간대 분포 (정류장 수) ==")
    print(summary["피크시간대"].value_counts().sort_index(), "\n")

    print("== 노선 내 위치별 하차 패턴 ==")
    print(position_pattern(alighting, route_stops).round(3), "\n")

    plot_pareto(summary, OUT_DIR / "stop_pareto.png")
    plot_routes_vs_volume(summary, OUT_DIR / "routes_vs_alighting.png")
    print(f"차트 저장: {OUT_DIR}")


if __name__ == "__main__":
    main()
