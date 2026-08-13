import os
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import requests
import streamlit as st
import plotly.express as px
from urllib.parse import quote_plus

st.set_page_config(page_title="서울30평꿀집샀다", page_icon="🏠", layout="wide")

TARGET = 12.42
MAX_BUDGET = 13.42
AREA_MIN = 74
AREA_MAX = 85

@st.cache_data(ttl=3600)
def load_candidates():
    return pd.read_csv("candidates.csv")

@st.cache_data(ttl=3600)
def load_seed_prices():
    return pd.read_csv("seed_prices.csv")

def get_api_key():
    try:
        return st.secrets["DATA_GO_KR_SERVICE_KEY"]
    except Exception:
        return os.getenv("DATA_GO_KR_SERVICE_KEY", "")

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_month(lawd_cd: str, yyyymm: str, service_key: str):
    if not service_key:
        return pd.DataFrame()
    url = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
    params = {
        "serviceKey": service_key,
        "LAWD_CD": str(lawd_cd),
        "DEAL_YMD": yyyymm,
        "numOfRows": 9999,
        "pageNo": 1,
        "_type": "json",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if isinstance(items, dict):
        items = [items]
    if not items:
        return pd.DataFrame()
    return pd.DataFrame(items)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_recent_trades(lawd_cd: str, months: int, service_key: str):
    frames = []
    base = date.today().replace(day=1)
    for i in range(months):
        dt = base - relativedelta(months=i)
        ym = dt.strftime("%Y%m")
        try:
            df = fetch_month(lawd_cd, ym, service_key)
            if not df.empty:
                frames.append(df)
        except Exception:
            pass
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    rename = {
        "aptNm":"complex_name", "excluUseAr":"area_m2", "dealAmount":"deal_amount",
        "dealYear":"year", "dealMonth":"month", "dealDay":"day", "floor":"floor",
        "buildYear":"build_year", "umdNm":"dong", "jibun":"jibun",
        "cdealType":"cancel_type", "cdealDay":"cancel_day"
    }
    df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})
    if "deal_amount" in df:
        df["deal_amount_won"] = pd.to_numeric(df["deal_amount"].astype(str).str.replace(",","", regex=False), errors="coerce") * 10000
        df["price_eok"] = df["deal_amount_won"] / 100000000
    if "area_m2" in df:
        df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce")
    for c in ["year","month","day"]:
        if c in df: df[c] = pd.to_numeric(df[c], errors="coerce")
    if all(c in df for c in ["year","month","day"]):
        df["deal_date"] = pd.to_datetime(dict(year=df.year, month=df.month, day=df.day), errors="coerce")
    return df

def normalize_name(s):
    return str(s).replace(" ", "").replace("(주)", "").lower()

def filter_complex(df, complex_name):
    if df.empty or "complex_name" not in df: return pd.DataFrame()
    target = normalize_name(complex_name)
    norm = df["complex_name"].astype(str).apply(normalize_name)
    mask = norm.eq(target) | norm.str.contains(target, regex=False) | pd.Series([target in x for x in norm], index=df.index)
    out = df[mask].copy()
    if "area_m2" in out:
        out = out[(out.area_m2 >= AREA_MIN) & (out.area_m2 <= AREA_MAX)]
    return out.sort_values("deal_date", ascending=False) if "deal_date" in out else out

def price_status(price):
    if pd.isna(price): return "데이터 대기"
    if price <= TARGET: return "적극검토"
    if price <= MAX_BUDGET: return "경계"
    return "예산초과"

def naver_land_search_url(row):
    # 네이버페이 부동산의 단지 고유번호는 외부에서 안정적으로 자동수집하기 어려워
    # 네이버 검색을 통해 해당 단지의 네이버부동산 결과로 연결한다.
    query = f"네이버페이 부동산 {row['complex_name']} {row['area']}"
    return "https://search.naver.com/search.naver?query=" + quote_plus(query)

def trade_summary(df):
    if df.empty or "price_eok" not in df: return None
    df = df.dropna(subset=["price_eok", "deal_date"])
    if df.empty: return None
    latest = df.sort_values("deal_date", ascending=False).iloc[0]
    now = pd.Timestamp.today()
    def median_since(months):
        x = df[df.deal_date >= now - pd.DateOffset(months=months)]
        return x.price_eok.median() if len(x) else None
    m3, m12 = median_since(3), median_since(12)
    return {
        "latest": float(latest.price_eok), "latest_date": latest.deal_date.date(),
        "m3": None if pd.isna(m3) else float(m3), "m12": None if pd.isna(m12) else float(m12),
        "count3": int((df.deal_date >= now - pd.DateOffset(months=3)).sum()),
        "count12": int((df.deal_date >= now - pd.DateOffset(months=12)).sum()),
    }

candidates = load_candidates()
seed = load_seed_prices()
api_key = get_api_key()

st.title("🏠 서울30평꿀집샀다")
st.caption("서울·경기남부 후보 아파트를 실거래가·입지·단지조건으로 추적하는 개인 대시보드")

if api_key:
    st.success("국토교통부 실거래 API 연결됨 · 데이터는 최대 1시간 캐시 후 다시 조회됩니다.")
else:
    st.warning("현재는 DEMO 모드입니다. 공공데이터포털 인증키를 연결하면 최신 실거래가가 자동 갱신됩니다.")

page = st.sidebar.radio("보기", ["전체 후보", "단지 상세", "지역 비교", "설정/사용법"])
st.sidebar.markdown(f"**매수 기준**  TARGET {TARGET:.2f}억 · MAX {MAX_BUDGET:.2f}억")
st.sidebar.caption("전용 74~84㎡ 중심 · 500세대 이상 선호 · 역 도보 20분 이내 · 초중 인접")

if page == "전체 후보":
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("등록 생활권/단지", len(candidates))
    c2.metric("서울", int((candidates.region=="서울").sum()))
    c3.metric("경기남부", int((candidates.region=="경기남부").sum()))
    c4.metric("TARGET / MAX", f"{TARGET:.2f} / {MAX_BUDGET:.2f}억")

    region_filter = st.multiselect("권역", ["서울","경기남부"], default=["서울","경기남부"])
    pri_filter = st.multiselect("후보 상태", sorted(candidates.priority.unique()), default=list(sorted(candidates.priority.unique())))
    view = candidates[candidates.region.isin(region_filter) & candidates.priority.isin(pri_filter)].copy()
    view = view.merge(seed[["complex_name","low_2026","high_2026"]], on="complex_name", how="left")
    view["seed_mid"] = (view.low_2026 + view.high_2026)/2
    view["예산판정(초기값)"] = view.seed_mid.apply(price_status)
    show_cols = ["region","area","complex_name","priority","screening","seed_mid","예산판정(초기값)","households","walk_station_min","nearest_station","commute_eulji_min","note"]
    st.dataframe(view[show_cols].rename(columns={
        "region":"권역","area":"생활권","complex_name":"단지","priority":"우선순위","screening":"스크리닝","seed_mid":"초기 대표가(억)",
        "households":"세대수","walk_station_min":"역 도보(분)","nearest_station":"역","commute_eulji_min":"을지로 통근(분)","note":"메모"
    }), use_container_width=True, hide_index=True)
    st.caption("초기 대표가는 지금까지 대화에서 1차 검증한 값입니다. API 연결 후에는 최신 실거래가를 우선 표시합니다.")

elif page == "단지 상세":
    named = candidates[~candidates.complex_name.str.contains("후보", na=False)].copy()
    selected = st.selectbox("단지를 선택하세요", named.complex_name.tolist())
    row = named[named.complex_name==selected].iloc[0]
    st.subheader(f"{selected} · {row['area']}")

    left,right = st.columns([2,1])
    with right:
        st.markdown("#### 입지·단지 조건")
        st.write(f"- 권역: **{row['region']} / {row['area']}**")
        st.write(f"- 세대수: **{int(row['households']) if pd.notna(row['households']) else '미입력'}세대**")
        st.write(f"- 준공: **{int(row['build_year']) if pd.notna(row['build_year']) else '미입력'}년**")
        st.write(f"- 최근역: **{row['nearest_station']} / 도보 약 {row['walk_station_min']}분**")
        st.write(f"- 초등: **{row['elementary_school'] if pd.notna(row['elementary_school']) else '검증 예정'}**")
        st.write(f"- 중등: **{row['middle_school'] if pd.notna(row['middle_school']) else '검증 예정'}**")
        st.write(f"- 을지로입구 예상 통근: **약 {row['commute_eulji_min']}분**")
        if 'screening' in row and pd.notna(row['screening']):
            st.write(f"- 현재 스크리닝: **{row['screening']}**")
        st.info(row['note'])
        st.markdown("#### 현재 매물·외부 확인")
        st.link_button("🏠 네이버부동산에서 이 단지 검색", naver_land_search_url(row), use_container_width=True)
        if 'source_url' in row and pd.notna(row['source_url']) and str(row['source_url']).startswith('http'):
            st.link_button("🔎 단지정보 출처 열기", str(row['source_url']), use_container_width=True)
        st.caption("네이버 매물은 실시간 호가 확인용입니다. 대시보드의 공식 가격 추적은 국토부 실거래를 기준으로 합니다.")

    trades = pd.DataFrame()
    if api_key:
        with st.spinner("최근 24개월 실거래를 조회하는 중..."):
            all_trades = fetch_recent_trades(str(row['lawd_cd']), 24, api_key)
            api_target = row['api_name'] if 'api_name' in row and pd.notna(row['api_name']) and str(row['api_name']).strip() else selected
            trades = filter_complex(all_trades, api_target)
    summary = trade_summary(trades)

    with left:
        if summary:
            a,b,c,d = st.columns(4)
            a.metric("최신 거래", f"{summary['latest']:.2f}억", str(summary['latest_date']))
            a_status = price_status(summary['latest'])
            b.metric("예산판정", a_status)
            b.caption(f"TARGET 대비 {TARGET-summary['latest']:+.2f}억")
            c.metric("최근 3개월 중앙값", f"{summary['m3']:.2f}억" if summary['m3'] else "-")
            d.metric("12개월 거래수", summary['count12'])
            plot_df = trades.dropna(subset=["deal_date","price_eok"]).sort_values("deal_date")
            fig = px.scatter(plot_df, x="deal_date", y="price_eok", hover_data=[c for c in ["area_m2","floor"] if c in plot_df.columns],
                             labels={"deal_date":"계약일","price_eok":"거래가(억원)"}, title="최근 24개월 74~84㎡ 실거래")
            fig.add_hline(y=TARGET, line_dash="dash", annotation_text="TARGET")
            fig.add_hline(y=MAX_BUDGET, line_dash="dot", annotation_text="MAX")
            st.plotly_chart(fig, use_container_width=True)
            cols = [c for c in ["deal_date","price_eok","area_m2","floor","dong","jibun"] if c in trades.columns]
            st.dataframe(trades[cols].head(30), use_container_width=True, hide_index=True)
        else:
            seedrow = seed[seed.complex_name==selected]
            if len(seedrow):
                s=seedrow.iloc[0]
                mid=(s.low_2026+s.high_2026)/2
                st.metric("현재 표시값 (초기 검증치)", f"{mid:.2f}억", f"범위 {s.low_2026:.2f}~{s.high_2026:.2f}억")
                st.write(f"가격판정: **{price_status(mid)}**")
            st.info("API 인증키를 연결하면 이 자리에 최신 실거래 그래프와 과거 24개월 거래내역이 자동으로 나타납니다.")

elif page == "지역 비교":
    st.subheader("생활권 비교")
    areas = st.multiselect("비교할 생활권", candidates.area.unique().tolist(), default=["신림","이문","홍제","성복"])
    comp = candidates[candidates.area.isin(areas)].copy()
    comp = comp.merge(seed[["complex_name","low_2026","high_2026"]], on="complex_name", how="left")
    comp["초기대표가"]=(comp.low_2026+comp.high_2026)/2
    cols=["region","area","complex_name","초기대표가","households","walk_station_min","nearest_station","commute_eulji_min","priority","screening","note"]
    st.dataframe(comp[cols].rename(columns={"region":"권역","area":"생활권","complex_name":"대표단지","households":"세대수","walk_station_min":"역도보","nearest_station":"역","commute_eulji_min":"을지로 통근","priority":"우선순위","screening":"스크리닝","note":"메모"}), use_container_width=True, hide_index=True)
    st.caption("V2에서는 학군·교통·연식·생활편의·가격여유를 가중치로 점수화해 같은 화면에서 순위를 만들 예정입니다.")

else:
    st.subheader("처음 쓰는 사람용 설정")
    st.markdown("""
1. **공공데이터포털(data.go.kr)**에서 회원가입 후 `국토교통부_아파트 매매 실거래가 자료` 활용신청을 합니다.
2. 발급된 **일반 인증키(Encoding)**를 복사합니다.
3. Streamlit Community Cloud에서 이 앱을 배포할 때 **Secrets**에 아래처럼 붙여넣습니다.
    """)
    st.code('DATA_GO_KR_SERVICE_KEY = "발급받은_인증키"', language="toml")
    st.markdown("""
4. 그 뒤부터는 사이트에 들어갈 때 최신 실거래 데이터를 조회합니다. 조회량을 줄이기 위해 결과는 **1시간 캐시**합니다.
5. 후보를 추가/삭제하려면 `candidates.csv` 한 줄만 수정하면 됩니다.
6. 단지 상세 화면의 **네이버부동산에서 이 단지 검색** 버튼을 누르면 현재 등록된 매물·호가를 별도로 확인할 수 있습니다.

**주의:** 실거래 신고는 계약 직후 즉시 완전히 확정되는 데이터가 아닙니다. 가장 최근 수치는 이후 추가·정정될 수 있으므로, 이 앱은 '최신 신고 현황'을 보는 용도로 사용하고 실제 계약 직전에는 국토부 실거래가 공개시스템과 매물 현장을 함께 확인해야 합니다.
""")
