"""노선별 운영 효율 분석.

노선별 일평균 하차, 운행대수당·운행 1회당·정류장당 하차를 계산하고
노선유형별로 비교한 뒤, 과잉/부족 공급 노선과 배차간격 조정안을 제시한다.

실행: .venv/bin/python analysis/route_efficiency.py
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

OUT_DIR = ROOT / "reports" / "route-efficiency"

# 공급 판정 기준: 운행 1회당 하차가 전체 중앙값 대비 이 배수 밖이면 과잉/부족
OVER_RATIO = 0.7
UNDER_RATIO = 1.3
# 배차간격 조정 시 허용 범위(분)와 반올림 단위
MIN_HEADWAY, MAX_HEADWAY, HEADWAY_STEP = 5, 40, 5

plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False


def service_minutes(first: str, last: str) -> int:
    h1, m1 = map(int, first.split(":"))
    h2, m2 = map(int, last.split(":"))
    return (h2 * 60 + m2) - (h1 * 60 + m1)


def build_metrics(routes: pd.DataFrame, route_stops: pd.DataFrame,
                  alighting: pd.DataFrame) -> pd.DataFrame:
    n_days = alighting["일자"].nunique()
    daily = (alighting.groupby("노선번호")["하차인원"].sum() / n_days).rename("일평균하차")
    n_stops = route_stops.groupby("노선번호").size().rename("정류장수")

    df = routes.set_index("노선번호").join([daily, n_stops])
    df["운행시간(분)"] = [service_minutes(f, l) for f, l in zip(df["첫차"], df["막차"])]
    # 일 운행횟수 = 운행시간 / 배차간격 (한 방향 기준 추정치)
    df["일운행횟수"] = df["운행시간(분)"] / df["배차간격(분)"]
    df["대당하차"] = df["일평균하차"] / df["운행대수"]
    df["회당하차"] = df["일평균하차"] / df["일운행횟수"]
    df["정류장당하차"] = df["일평균하차"] / df["정류장수"]
    # 차량 가동도: 한 대가 하루에 맡는 운행횟수. 낮으면 배차간격 대비 차량이 남는다는 신호
    df["대당운행횟수"] = df["일운행횟수"] / df["운행대수"]
    return df


def classify_and_simulate(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    target = df["회당하차"].median()
    ratio = df["회당하차"] / target
    df["효율지수"] = ratio
    df["판정"] = "적정"
    df.loc[ratio < OVER_RATIO, "판정"] = "과잉공급"
    df.loc[ratio > UNDER_RATIO, "판정"] = "부족공급"

    # 회당하차가 중앙값(target)이 되도록 운행횟수를 맞춘 배차간격
    needed_trips = df["일평균하차"] / target
    raw = df["운행시간(분)"] / needed_trips
    rounded = (raw / HEADWAY_STEP).round() * HEADWAY_STEP
    df["제안배차간격(분)"] = rounded.clip(MIN_HEADWAY, MAX_HEADWAY).astype(int)
    df.loc[df["판정"] == "적정", "제안배차간격(분)"] = df["배차간격(분)"]

    df["제안운행횟수"] = df["운행시간(분)"] / df["제안배차간격(분)"]
    df["제안회당하차"] = df["일평균하차"] / df["제안운행횟수"]
    df["운행횟수증감"] = df["제안운행횟수"] - df["일운행횟수"]
    # 차량 가동도(대당운행횟수)를 현재대로 유지한다고 볼 때 필요한 대수
    df["제안운행대수"] = (df["제안운행횟수"] / df["대당운행횟수"]).round().astype(int)
    # 가동도를 전체 중앙값까지만 올려도 되는 경우의 최소 대수
    util = df["대당운행횟수"].median()
    df["최소운행대수(가동도중앙값)"] = (df["제안운행횟수"] / util).round().astype(int)
    df.attrs["target"] = target
    return df


def save_charts(df: pd.DataFrame) -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    colors = {"과잉공급": "#d9534f", "적정": "#8a8a8a", "부족공급": "#2c7fb8"}
    paths = []

    # 1) 운행 1회당 하차 순위 (판정 색상)
    s = df.sort_values("회당하차")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels = [f"{i} ({t})" for i, t in zip(s.index, s["노선유형"])]
    ax.barh(labels, s["회당하차"], color=[colors[j] for j in s["판정"]])
    target = df.attrs["target"]
    median_line = ax.axvline(target, color="black", ls="--", lw=1)
    for y, v in enumerate(s["회당하차"]):
        ax.text(v, y, f" {v:.1f}", va="center", fontsize=9)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors.values()]
    ax.legend(handles + [median_line], [*colors.keys(), f"중앙값 {target:.1f}명"],
              loc="lower right", frameon=False)
    ax.set_xlabel("운행 1회당 일평균 하차(명)")
    ax.set_title("노선별 운행 1회당 하차 — 공급 판정")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    p = OUT_DIR / "per_trip_ranking.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    paths.append(p)

    # 2) 배차간격 현재 vs 제안
    s = df.sort_values("회당하차")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    y = range(len(s))
    ax.barh([i + 0.2 for i in y], s["배차간격(분)"], height=0.4, color="#bdbdbd", label="현재")
    ax.barh([i - 0.2 for i in y], s["제안배차간격(분)"], height=0.4,
            color=[colors[j] for j in s["판정"]], label="제안")
    ax.set_yticks(list(y), s.index)
    ax.set_xlabel("배차간격(분)")
    ax.set_title("배차간격 조정 시뮬레이션 (회당하차를 중앙값에 맞춤)")
    ax.set_xlim(0, 48)
    ax.legend(frameon=False, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    p = OUT_DIR / "headway_simulation.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    paths.append(p)
    return paths


def main() -> None:
    routes, route_stops = load_routes()
    alighting = load_alighting()
    df = classify_and_simulate(build_metrics(routes, route_stops, alighting))

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    cols = ["노선유형", "배차간격(분)", "운행대수", "정류장수", "일평균하차",
            "대당하차", "일운행횟수", "대당운행횟수", "회당하차", "정류장당하차", "효율지수", "판정"]
    print("== 노선별 효율 (회당하차 내림차순) ==")
    print(df[cols].sort_values("회당하차", ascending=False).round(1), "\n")

    print("== 노선유형별 비교 ==")
    by_type = df.groupby("노선유형").agg(
        노선수=("일평균하차", "size"), 일평균하차=("일평균하차", "sum"),
        운행대수=("운행대수", "sum"), 일운행횟수=("일운행횟수", "sum"),
        정류장수=("정류장수", "sum"))
    by_type["대당하차"] = by_type["일평균하차"] / by_type["운행대수"]
    by_type["회당하차"] = by_type["일평균하차"] / by_type["일운행횟수"]
    by_type["정류장당하차"] = by_type["일평균하차"] / by_type["정류장수"]
    print(by_type.sort_values("회당하차", ascending=False).round(1), "\n")

    print(f"== 배차간격 조정 시뮬레이션 (목표 회당하차 = 중앙값 {df.attrs['target']:.1f}명) ==")
    sim_cols = ["판정", "배차간격(분)", "제안배차간격(분)", "일운행횟수", "제안운행횟수",
                "운행횟수증감", "회당하차", "제안회당하차", "운행대수", "대당운행횟수", "제안운행대수", "최소운행대수(가동도중앙값)"]
    print(df.loc[df["판정"] != "적정", sim_cols].round(1), "\n")
    print(f"총 일운행횟수: 현재 {df['일운행횟수'].sum():.0f} → 제안 {df['제안운행횟수'].sum():.0f}")
    print(f"총 운행대수:   현재 {df['운행대수'].sum()} → 제안(가동도 유지) {df['제안운행대수'].sum()}")
    print(f"대당운행횟수 중앙값: {df['대당운행횟수'].median():.1f}회\n")

    for p in save_charts(df):
        print(f"차트 저장: {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
