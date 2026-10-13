"""xlsx 버스 노선·하차 데이터를 pandas 로 읽고 간단히 집계한다."""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

# 노선번호·정류장ID 는 숫자처럼 보여도 문자열로 읽어야 앞자리 0 이나 '마을1' 같은 값이 섞여도 안전하다
ID_DTYPES = {"노선번호": str, "정류장ID": str}


def load_routes(path: Path = DATA_DIR / "bus_routes.xlsx") -> tuple[pd.DataFrame, pd.DataFrame]:
    # sheet_name=None 이면 모든 시트를 {시트명: DataFrame} 딕셔너리로 읽는다
    sheets = pd.read_excel(path, sheet_name=None, dtype=ID_DTYPES)
    return sheets["노선"], sheets["노선정류장"]


def load_alighting(path: Path = DATA_DIR / "bus_alighting.xlsx") -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="하차", dtype=ID_DTYPES, parse_dates=["일자"])
    return df


def main() -> None:
    routes, route_stops = load_routes()
    alighting = load_alighting()

    print("== 노선 ==")
    print(routes.head(), "\n")
    print("== 노선정류장 ==")
    print(route_stops.head(), "\n")
    print("== 하차 ==")
    print(alighting.head(), "\n")
    alighting.info()
    print()

    # 하차 데이터에 노선 정보(노선유형 등)를 붙인다
    merged = alighting.merge(routes[["노선번호", "노선명", "노선유형"]], on="노선번호", how="left")

    print("== 노선별 총 하차인원 ==")
    print(merged.groupby(["노선번호", "노선유형"])["하차인원"].sum()
          .sort_values(ascending=False), "\n")

    print("== 시간대별 총 하차인원 ==")
    print(merged.groupby("시간대")["하차인원"].sum(), "\n")

    print("== 하차 많은 정류장 TOP 5 ==")
    print(merged.groupby("정류장명")["하차인원"].sum().nlargest(5), "\n")

    print("== 일자 × 노선유형 피벗 ==")
    print(merged.pivot_table(index="일자", columns="노선유형", values="하차인원", aggfunc="sum"))


if __name__ == "__main__":
    main()
