"""시간대별 하차 수요와 출퇴근 피크를 분석하고 차트를 reports/peak/ 에 저장한다."""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from read_bus_data import load_alighting, load_routes  # noqa: E402

OUT_DIR = ROOT / "reports" / "peak"
AM_HOURS = range(5, 12)   # 출근 피크 탐색 구간
PM_HOURS = range(15, 22)  # 퇴근 피크 탐색 구간

plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False


def load() -> pd.DataFrame:
    routes, _ = load_routes()
    df = load_alighting().merge(routes[["노선번호", "노선유형"]], on="노선번호", how="left")
    df["구분"] = df["일자"].dt.dayofweek.map(lambda d: "주말" if d >= 5 else "평일")
    return df


def find_peaks(hourly: pd.Series) -> tuple[int, int]:
    return int(hourly.loc[list(AM_HOURS)].idxmax()), int(hourly.loc[list(PM_HOURS)].idxmax())


def per_day_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """구분(평일/주말)별 '하루 평균' 시간대 하차 — 평일 5일, 주말 2일이라 일수로 나눠 비교한다."""
    days = df.groupby("구분")["일자"].nunique()
    tot = df.pivot_table(index="시간대", columns="구분", values="하차인원", aggfunc="sum")
    return tot / days


def main() -> None:
    df = load()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 시간대별 총 하차
    hourly = df.groupby("시간대")["하차인원"].sum()
    total = hourly.sum()
    print("== 시간대별 총 하차 (7일 합) ==")
    print(pd.DataFrame({"하차": hourly, "비중%": (hourly / total * 100).round(1)}), "\n")

    # 2. 피크 식별 (평일 기준 — 출퇴근은 평일 현상)
    daily = per_day_hourly(df)
    am, pm = find_peaks(daily["평일"])
    print(f"== 평일 피크: 출근 {am}시 / 퇴근 {pm}시 ==")
    print(daily.round(1), "\n")

    # 3. 피크 집중도: 피크 2개 시간대가 하루 하차에서 차지하는 비율 (일자별)
    by_day = df.pivot_table(index="일자", columns="시간대", values="하차인원", aggfunc="sum")
    conc = ((by_day[am] + by_day[pm]) / by_day.sum(axis=1) * 100).round(1)
    day_type = by_day.index.dayofweek.map(lambda d: "주말" if d >= 5 else "평일")
    conc_df = pd.DataFrame({"구분": day_type, "피크집중도%": conc, "일하차": by_day.sum(axis=1)})
    print(f"== 일자별 피크 집중도 ({am}시+{pm}시 / 일 하차) ==")
    print(conc_df, "\n")
    print("구분별 평균 집중도%:", conc_df.groupby("구분")["피크집중도%"].mean().round(1).to_dict(), "\n")

    # 4. 노선유형별 시간대 프로파일 (평일, 유형 내 비중%)
    wk = df[df["구분"] == "평일"]
    type_prof = wk.pivot_table(index="시간대", columns="노선유형", values="하차인원", aggfunc="sum")
    type_share = type_prof / type_prof.sum() * 100
    print("== 노선유형별 평일 시간대 비중% ==")
    print(type_share.round(1), "\n")
    type_peak = pd.DataFrame({
        "출근피크": type_share.loc[list(AM_HOURS)].idxmax(),
        "퇴근피크": type_share.loc[list(PM_HOURS)].idxmax(),
        "피크2시간비중%": (type_share.loc[am] + type_share.loc[pm]).round(1),
    })
    print("== 노선유형별 피크 ==")
    print(type_peak, "\n")

    # 5. 평일 vs 주말 패턴 차이
    share = daily / daily.sum() * 100
    diff = (share["평일"] - share["주말"]).round(1)
    print("== 평일 vs 주말 (하루 평균) ==")
    print(f"하루 평균 하차: 평일 {daily['평일'].sum():.0f} / 주말 {daily['주말'].sum():.0f} "
          f"(주말/평일 {daily['주말'].sum() / daily['평일'].sum() * 100:.0f}%)")
    print(f"주말 최대 시간대: {int(daily['주말'].idxmax())}시")
    print("시간대별 비중 차이(평일-주말, %p):")
    print(diff.to_string(), "\n")

    # 차트 1: 평일 vs 주말 하루 평균 시간대 프로파일
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(daily.index, daily["평일"], marker="o", color="#1f5fbf", label="평일 (하루 평균)")
    ax.plot(daily.index, daily["주말"], marker="o", color="#e07b00", label="주말 (하루 평균)")
    for h, name in [(am, "출근 피크"), (pm, "퇴근 피크")]:
        ax.axvspan(h - 0.5, h + 0.5, color="#1f5fbf", alpha=0.1)
        ax.annotate(f"{name} {h}시", (h, daily.loc[h, "평일"]), textcoords="offset points",
                    xytext=(0, 8), ha="center")
    ax.set(title="시간대별 하차인원: 평일 vs 주말", xlabel="시간대(시)", ylabel="하차인원(명/일)",
           xticks=list(daily.index))
    ax.set_ylim(0, daily.values.max() * 1.12)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "hourly_weekday_weekend.png", dpi=120)
    plt.close(fig)

    # 차트 2: 노선유형별 평일 시간대 비중
    fig, ax = plt.subplots(figsize=(10, 5))
    for col in type_share.columns:
        ax.plot(type_share.index, type_share[col], marker=".", label=col)
    ax.set(title="노선유형별 평일 시간대 하차 비중", xlabel="시간대(시)", ylabel="유형 내 비중(%)",
           xticks=list(type_share.index))
    ax.grid(alpha=0.3)
    ax.legend(title="노선유형")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "hourly_by_route_type.png", dpi=120)
    plt.close(fig)

    print(f"차트 저장: {OUT_DIR}")


if __name__ == "__main__":
    main()
