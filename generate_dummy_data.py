"""버스 노선·하차 더미 데이터를 만들어 xlsx 로 저장한다.

생성 파일
- data/bus_routes.xlsx
    - 시트 '노선'        : 노선 마스터 (노선별 1행)
    - 시트 '노선정류장'  : 노선별 경유 정류장과 순번
- data/bus_alighting.xlsx
    - 시트 '하차'        : 일자 × 노선 × 정류장 × 시간대별 하차 인원
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
DATA_DIR = Path(__file__).parent / "data"
START_DATE = "2026-10-01"
DAYS = 7
HOURS = range(5, 24)  # 05시 ~ 23시 운행

STOP_NAMES = [
    "시청앞", "중앙시장", "시외버스터미널", "기차역", "시립도서관", "종합운동장",
    "대학교정문", "대학병원", "구청", "우체국", "농협사거리", "신도시1단지",
    "신도시2단지", "산업단지입구", "물류센터", "공원입구", "문화예술회관", "보건소",
    "초등학교", "중학교", "고등학교", "법원", "세무서", "경찰서",
    "소방서", "하나아파트", "푸른마을", "강변공원", "호수공원", "아울렛",
]

ROUTES = [
    # 노선번호, 노선유형, 배차간격(분), 경유 정류장 수
    ("101", "간선", 10, 14),
    ("102", "간선", 12, 13),
    ("201", "지선", 15, 10),
    ("202", "지선", 15, 9),
    ("301", "광역", 20, 8),
    ("9001", "광역", 30, 6),
    ("마을1", "마을", 20, 7),
    ("마을2", "마을", 25, 6),
]

# 시간대별 수요 가중치: 출근(07~09시)·퇴근(17~19시) 피크
HOUR_WEIGHT = {
    5: 0.2, 6: 0.5, 7: 1.4, 8: 2.0, 9: 1.2, 10: 0.7, 11: 0.6, 12: 0.8,
    13: 0.7, 14: 0.6, 15: 0.7, 16: 0.9, 17: 1.5, 18: 2.0, 19: 1.3,
    20: 0.8, 21: 0.6, 22: 0.4, 23: 0.2,
}
ROUTE_TYPE_SCALE = {"간선": 1.0, "지선": 0.6, "광역": 1.3, "마을": 0.3}


def make_stops() -> pd.DataFrame:
    return pd.DataFrame({
        "정류장ID": [f"ST{i:04d}" for i in range(1, len(STOP_NAMES) + 1)],
        "정류장명": STOP_NAMES,
    })


def make_routes(rng: np.random.Generator, stops: pd.DataFrame):
    route_rows, route_stop_rows = [], []
    for route_no, route_type, interval, n_stops in ROUTES:
        picked = stops.sample(n=n_stops, random_state=rng.integers(1_000_000))
        first, last = picked.iloc[0]["정류장명"], picked.iloc[-1]["정류장명"]
        route_rows.append({
            "노선번호": route_no,
            "노선명": f"{first}~{last}",
            "노선유형": route_type,
            "기점": first,
            "종점": last,
            "배차간격(분)": interval,
            "운행대수": int(rng.integers(3, 15)),
            "첫차": "05:00",
            "막차": "23:00",
        })
        for seq, (_, stop) in enumerate(picked.iterrows(), start=1):
            route_stop_rows.append({
                "노선번호": route_no,
                "정류장순번": seq,
                "정류장ID": stop["정류장ID"],
                "정류장명": stop["정류장명"],
            })
    return pd.DataFrame(route_rows), pd.DataFrame(route_stop_rows)


def make_alighting(rng: np.random.Generator, routes: pd.DataFrame,
                   route_stops: pd.DataFrame) -> pd.DataFrame:
    route_type = routes.set_index("노선번호")["노선유형"]
    dates = pd.date_range(START_DATE, periods=DAYS, freq="D")

    rows = []
    for date in dates:
        weekend_scale = 0.6 if date.dayofweek >= 5 else 1.0
        for _, rs in route_stops.iterrows():
            # 정류장마다 인기도가 다르다 (기점에서는 하차가 거의 없다)
            popularity = 0.1 if rs["정류장순번"] == 1 else rng.uniform(0.5, 1.8)
            scale = ROUTE_TYPE_SCALE[route_type[rs["노선번호"]]]
            for hour in HOURS:
                lam = 8 * HOUR_WEIGHT[hour] * scale * popularity * weekend_scale
                rows.append({
                    "일자": date.date(),
                    "노선번호": rs["노선번호"],
                    "정류장ID": rs["정류장ID"],
                    "정류장명": rs["정류장명"],
                    "시간대": hour,
                    "하차인원": int(rng.poisson(lam)),
                })
    return pd.DataFrame(rows)


def main() -> None:
    rng = np.random.default_rng(SEED)
    DATA_DIR.mkdir(exist_ok=True)

    stops = make_stops()
    routes, route_stops = make_routes(rng, stops)
    alighting = make_alighting(rng, routes, route_stops)

    with pd.ExcelWriter(DATA_DIR / "bus_routes.xlsx", engine="openpyxl") as writer:
        routes.to_excel(writer, sheet_name="노선", index=False)
        route_stops.to_excel(writer, sheet_name="노선정류장", index=False)

    alighting.to_excel(DATA_DIR / "bus_alighting.xlsx", sheet_name="하차", index=False)

    print(f"노선 {len(routes)}개, 노선정류장 {len(route_stops)}행, 하차 {len(alighting)}행 생성")


if __name__ == "__main__":
    main()
