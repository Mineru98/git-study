"""평일·주말 하차 비교와 이상치 탐지.

실행: .venv/bin/python analysis/weekday_anomaly.py
결과: 콘솔 출력 + reports/weekday-anomaly/*.png
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from read_bus_data import load_alighting, load_routes  # noqa: E402

OUT_DIR = ROOT / "reports" / "weekday-anomaly"
WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]
Z_THRESHOLD = 3.0
KEY = ["노선번호", "정류장ID", "정류장명", "시간대"]

plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False


def prepare() -> pd.DataFrame:
    routes, _ = load_routes()
    df = load_alighting().merge(routes[["노선번호", "노선유형"]], on="노선번호", how="left")
    df["요일"] = df["일자"].dt.dayofweek.map(lambda d: WEEKDAY_KO[d])
    df["주말"] = df["일자"].dt.dayofweek >= 5
    return df


def section(title: str) -> None:
    print(f"\n== {title} ==")


def quality_check(df: pd.DataFrame) -> None:
    section("데이터 품질")
    print(f"레코드 수: {len(df):,}")
    print(f"결측치: {int(df.isna().sum().sum())}")
    print(f"중복 키(일자×노선×정류장×시간대): {int(df.duplicated(['일자'] + KEY).sum())}")
    print(f"음수 하차: {int((df['하차인원'] < 0).sum())}")
    zero = df["하차인원"].eq(0)
    print(f"하차 0 레코드 비율: {zero.mean():.1%} ({int(zero.sum()):,}건)")
    print("평일/주말별 0 비율:")
    print(df.groupby("주말")["하차인원"].apply(lambda s: f"{s.eq(0).mean():.1%}")
          .rename(index={False: "평일", True: "주말"}).to_string())
    print("노선유형별 0 비율:")
    print(df.groupby("노선유형")["하차인원"].apply(lambda s: f"{s.eq(0).mean():.1%}").to_string())
    # 모든 일자·시간대에 하차 0 인 정류장(죽은 정류장) 확인
    dead = df.groupby(["노선번호", "정류장명"])["하차인원"].sum()
    print(f"7일 내내 하차 0 인 노선×정류장: {int(dead.eq(0).sum())}개")


def daily_totals(df: pd.DataFrame) -> pd.DataFrame:
    section("일자별 총 하차")
    daily = (df.groupby(["일자", "요일", "주말"])["하차인원"].sum().reset_index())
    print(daily.assign(일자=daily["일자"].dt.strftime("%m-%d")).to_string(index=False))
    return daily


def weekend_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """일평균 하차 기준 주말/평일 비율."""
    section("주말/평일 일평균 하차 비율")
    n_days = df.groupby("주말")["일자"].nunique()

    def ratio(group_cols):
        s = df.groupby(group_cols + ["주말"])["하차인원"].sum().unstack("주말")
        s = s.div(n_days, axis=1)
        s.columns = ["평일평균", "주말평균"]
        s["주말비율"] = s["주말평균"] / s["평일평균"]
        return s.round(2)

    total = df.groupby("주말")["하차인원"].sum() / n_days
    print(f"전체: 평일 {total[False]:,.0f}명/일, 주말 {total[True]:,.0f}명/일, "
          f"비율 {total[True] / total[False]:.2f}")
    print("\n[노선유형별]")
    print(ratio(["노선유형"]).sort_values("주말비율").to_string())
    by_route = ratio(["노선번호", "노선유형"]).sort_values("주말비율")
    print("\n[노선별]")
    print(by_route.to_string())
    return by_route


def route_variability(df: pd.DataFrame) -> pd.DataFrame:
    section("노선별 일자 변동성 (변동계수 CV = 표준편차/평균)")
    d = df.groupby(["노선번호", "일자", "주말"])["하차인원"].sum().reset_index()
    cv = lambda s: s.std(ddof=0) / s.mean()  # noqa: E731
    out = pd.DataFrame({
        "전체CV": d.groupby("노선번호")["하차인원"].apply(cv),
        "평일CV": d[~d["주말"]].groupby("노선번호")["하차인원"].apply(cv),
    }).round(3).sort_values("전체CV", ascending=False)
    print(out.to_string())
    return out


def detect_anomalies(df: pd.DataFrame, route_ratio: pd.Series) -> pd.DataFrame:
    """노선×정류장×시간대 단위로 평일 평균을 기대값으로 삼아 z-score 를 구한다.

    주말 레코드는 평일 평균에 해당 노선의 주말비율을 곱해 기대값을 보정한다.
    표준편차는 평일 5일 표본이라 불안정하므로 포아송 근사 sqrt(기대값) 과 1 로 하한을 둔다.
    """
    base = (df[~df["주말"]].groupby(KEY)["하차인원"]
            .agg(평일평균="mean", 평일표준편차="std").reset_index())
    m = df.merge(base, on=KEY, how="left")
    scale = np.where(m["주말"], m["노선번호"].map(route_ratio), 1.0)
    m["기대값"] = m["평일평균"] * scale
    sd = np.maximum.reduce([m["평일표준편차"].fillna(0).to_numpy(),
                            np.sqrt(m["기대값"].to_numpy()), np.ones(len(m))])
    m["z"] = (m["하차인원"] - m["기대값"]) / sd

    # 교차 검증용 IQR(평일 분포 기준) 플래그
    q = (df[~df["주말"]].groupby(KEY)["하차인원"].quantile([0.25, 0.75])
         .unstack().rename(columns={0.25: "q1", 0.75: "q3"}).reset_index())
    m = m.merge(q, on=KEY, how="left")
    iqr = m["q3"] - m["q1"]
    m["IQR이상"] = (m["하차인원"] > m["q3"] * scale + 3 * iqr.clip(lower=1)) | \
                  (m["하차인원"] < m["q1"] * scale - 3 * iqr.clip(lower=1))

    flagged = m[m["z"].abs() >= Z_THRESHOLD]
    section(f"이상치 (|z| >= {Z_THRESHOLD})")
    print(f"이상 레코드: {len(flagged)}건 ({len(flagged) / len(m):.2%}), "
          f"그중 IQR 기준도 이상: {int(flagged['IQR이상'].sum())}건, "
          f"IQR 단독 이상: {int((m['IQR이상'] & (m['z'].abs() < Z_THRESHOLD)).sum())}건")
    print("과대(+) / 과소(-):", int((flagged["z"] > 0).sum()), "/", int((flagged["z"] < 0).sum()))
    top = (m.reindex(m["z"].abs().sort_values(ascending=False).index).head(15)
           .assign(일자=lambda x: x["일자"].dt.strftime("%m-%d"),
                   기대값=lambda x: x["기대값"].round(1), z=lambda x: x["z"].round(1)))
    print("\n[상위 이상 레코드 15]")
    print(top[["일자", "요일", "노선번호", "정류장명", "시간대", "하차인원", "기대값", "z", "IQR이상"]]
          .to_string(index=False))
    print("\n[이상치 분포: 일자별]")
    print(flagged.groupby(flagged["일자"].dt.strftime("%m-%d"))["z"].size().to_string())
    print("\n[이상치 분포: 노선별]")
    print(flagged.groupby("노선번호").size().sort_values(ascending=False).to_string())
    return m


def plot_daily(daily: pd.DataFrame, df: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    labels = daily["일자"].dt.strftime("%m/%d") + "(" + daily["요일"] + ")"
    colors = np.where(daily["주말"], "#d9534f", "#4a6fa5")
    axes[0].bar(labels, daily["하차인원"], color=colors)
    wd_mean = daily.loc[~daily["주말"], "하차인원"].mean()
    axes[0].axhline(wd_mean, ls="--", color="gray", lw=1)
    axes[0].text(2.5, wd_mean * 1.01, f"평일평균 {wd_mean:,.0f}", va="bottom", ha="center",
                 fontsize=9, color="gray")
    axes[0].set_ylim(0, daily["하차인원"].max() * 1.12)
    axes[0].set_title("일자별 총 하차인원 (빨강=주말)")
    axes[0].set_ylabel("하차인원(명)")

    hourly = (df.groupby(["주말", "시간대"])["하차인원"].sum()
              .div(df.groupby("주말")["일자"].nunique(), level="주말").unstack("주말"))
    axes[1].plot(hourly.index, hourly[False], marker="o", color="#4a6fa5", label="평일 일평균")
    axes[1].plot(hourly.index, hourly[True], marker="o", color="#d9534f", label="주말 일평균")
    axes[1].set_title("시간대별 일평균 하차: 평일 vs 주말")
    axes[1].set_xlabel("시간대(시)")
    axes[1].set_xticks(hourly.index)
    axes[1].legend()
    fig.tight_layout()
    path = OUT_DIR / "daily_and_hourly.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def plot_ratio_and_z(by_route: pd.DataFrame, scored: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    r = by_route.reset_index()
    names = r["노선번호"] + "\n(" + r["노선유형"] + ")"
    axes[0].barh(names, r["주말비율"], color="#5b8c5a")
    axes[0].axvline(1.0, ls="--", color="gray", lw=1)
    for i, v in enumerate(r["주말비율"]):
        axes[0].text(v, i, f" {v:.2f}", va="center", fontsize=9)
    axes[0].set_title("노선별 주말/평일 일평균 하차 비율")
    axes[0].set_xlabel("주말비율 (1.0 = 평일과 동일)")

    z = scored["z"].clip(-10, 10)
    axes[1].hist(z, bins=80, color="#888")
    for t in (-Z_THRESHOLD, Z_THRESHOLD):
        axes[1].axvline(t, color="#d9534f", ls="--", lw=1)
    axes[1].set_yscale("log")
    axes[1].set_title(f"z-score 분포 (±{Z_THRESHOLD:g} 밖 = 이상치, ±10에서 절단)")
    axes[1].set_xlabel("z")
    axes[1].set_ylabel("레코드 수(log)")
    fig.tight_layout()
    path = OUT_DIR / "weekend_ratio_and_zscore.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = prepare()
    quality_check(df)
    daily = daily_totals(df)
    by_route = weekend_ratio(df)
    route_variability(df)
    scored = detect_anomalies(df, by_route["주말비율"].droplevel("노선유형"))
    section("차트")
    print(plot_daily(daily, df).relative_to(ROOT))
    print(plot_ratio_and_z(by_route, scored).relative_to(ROOT))


if __name__ == "__main__":
    main()
