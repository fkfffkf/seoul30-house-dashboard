import os
import io
import xml.etree.ElementTree as ET
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus, unquote

import pandas as pd
import requests
import streamlit as st
import plotly.express as px
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="서울30평꿀집샀다", page_icon="🏠", layout="wide")

TARGET = 12.42
WATCH_14 = 14.0
WATCH_15 = 15.0
AREA_MIN = 74
AREA_MAX = 85
CACHE_SECONDS = 3600

CANDIDATES_CSV = 'region,area,candidate_rank,complex_name,api_name,lawd_cd,build_year,households,walk_station_min,nearest_station,elementary_school,middle_school,commute_eulji_min,priority,screening,note,source_url,static_data_status\n서울,미아,1,SK북한산시티,SK북한산시티,11305,2004.0,3830.0,15.0,미아사거리,미양초,미양중,45.0,관찰,TOP 후보,가격 여유형,,기초검증\n서울,미아,2,벽산라이브파크,벽산라이브파크,11305,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,미아,3,삼각산아이원,삼각산아이원,11305,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,미아,4,두산위브트레지움,두산위브트레지움,11305,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,미아,5,꿈의숲롯데캐슬,꿈의숲롯데캐슬,11305,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,개봉,1,한마을,한마을,11530,1999.0,1983.0,12.0,개봉,개봉초,경인중,45.0,관찰,TOP 후보,가격 여유형,,기초검증\n서울,개봉,2,개봉푸르지오,개봉푸르지오,11530,2014.0,978.0,12.0,오류동,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,기초검증\n서울,개봉,3,개봉한진,개봉한진,11530,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,개봉,4,개봉삼환,개봉삼환,11530,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,개봉,5,두산,두산,11530,1999.0,529.0,8.0,창신,창신초,한성여중,25.0,핵심,TOP 후보,도심 통근 강점,,기초검증\n서울,신림,1,신림푸르지오,신림푸르지오,11620,2005.0,1456.0,18.0,신림,미성초,난우중,45.0,핵심,TOP 후보,10~11억대 Sweet spot 후보,,기초검증\n서울,신림,2,신림현대,신림현대,11620,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,신림,3,관악산휴먼시아2단지,관악산휴먼시아2단지,11620,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,신림,4,관악산휴먼시아1단지,관악산휴먼시아1단지,11620,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,창신·숭인,1,두산,두산,11110,1999.0,529.0,8.0,창신,창신초,한성여중,25.0,핵심,TOP 후보,도심 통근 강점,,기초검증\n서울,창신·숭인,2,창신쌍용1,창신쌍용1,11110,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,창신·숭인,3,창신쌍용2,창신쌍용2,11110,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,창신·숭인,4,종로센트레빌,종로센트레빌,11110,2008.0,416.0,2.0,창신,숭신초,한성여중,20.0,관찰,TOP 후보,416세대로 500세대 기준 미달. 입지 비교가치 때문에 예외 관찰 후보로 유지.,,기초검증\n서울,이문·신이문,1,대림e편한세상,대림e편한세상,11230,2003.0,1378.0,6.0,신이문,이문초,경희중,35.0,핵심,TOP 후보,TARGET권 핵심 후보,,기초검증\n서울,이문·신이문,2,래미안라그란데,래미안라그란데,11230,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,이문·신이문,3,이문아이파크자이,이문아이파크자이,11230,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,이문·신이문,4,이문쌍용,이문쌍용,11230,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,봉천·서울대입구,1,관악드림타운,관악드림타운,11620,2003.0,3544.0,18.0,봉천,구암초,구암중,40.0,핵심,TOP 후보,TARGET 경계,,기초검증\n서울,봉천·서울대입구,2,봉천우성,봉천우성,11620,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,봉천·서울대입구,3,e편한세상서울대입구1단지,e편한세상서울대입구1단지,11620,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,봉천·서울대입구,4,관악벽산블루밍1차,관악벽산블루밍1차,11620,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,봉천·서울대입구,5,서울대입구아이원,서울대입구아이원,11620,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,등촌,1,등촌아이파크,등촌아이파크,11500,2004.0,1653.0,12.0,등촌,등촌초,백석중,35.0,핵심,TOP 후보,TARGET 경계,,기초검증\n서울,등촌,2,등촌주공5단지,등촌주공5단지,11500,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,등촌,3,등촌주공6단지,등촌주공6단지,11500,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,등촌,4,등촌동부센트레빌,등촌동부센트레빌,11500,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,등촌,5,등촌대림,등촌대림,11500,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,홍제,1,홍제원현대,홍제원현대,11410,2000.0,939.0,,,인왕초,인왕중,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,기초검증\n서울,홍제,2,홍제한양,홍제한양,11410,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,홍제,3,홍제현대,홍제현대,11410,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,홍제,4,인왕산현대,인왕산현대,11410,2000.0,700.0,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,기초검증\n서울,홍제,5,청구1차,청구1차,11410,1994.0,862.0,12.0,홍제,인왕초,인왕중,30.0,핵심,TOP 후보,TARGET 중심 변동,,기초검증\n서울,장안·장한평,1,장안현대홈타운1차,장안현대홈타운1차,11230,2003.0,2182.0,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,기초검증\n서울,장안·장한평,2,장안삼성래미안2차,장안삼성래미안2차,11230,,1786.0,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,기초검증\n서울,장안·장한평,3,장안힐스테이트,장안힐스테이트,11230,,859.0,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,기초검증\n서울,장안·장한평,4,장안삼성래미안1차,장안삼성래미안1차,11230,,558.0,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,기초검증\n서울,장안·장한평,5,장안삼성쉐르빌,장안삼성쉐르빌,11230,,540.0,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,기초검증\n서울,가양,1,강나루현대,강나루현대,11500,1999.0,642.0,4.0,가양,가양초,등원중,40.0,관찰,TOP 후보,MAX 근접,,기초검증\n서울,가양,2,강서한강자이,강서한강자이,11500,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,가양,3,가양우성,가양우성,11500,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,신대방·보라매,1,보라매파크빌,보라매파크빌,11590,2002.0,423.0,7.0,보라매,대방초,대방중,35.0,관찰,TOP 후보,세대수 기준 재검증 필요,,기초검증\n서울,신대방·보라매,2,신대방현대,신대방현대,11590,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,신대방·보라매,3,보라매자이더포레스트,보라매자이더포레스트,11590,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,신대방·보라매,4,롯데낙천대,롯데낙천대,11590,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,신대방·보라매,5,신대방경남교수,신대방경남교수,11590,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,발산·마곡,1,마곡수명산파크1단지,마곡수명산파크1단지,11500,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,발산·마곡,2,마곡수명산파크2단지,마곡수명산파크2단지,11500,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,발산·마곡,3,마곡수명산파크3단지,마곡수명산파크3단지,11500,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,발산·마곡,4,마곡수명산파크4단지,마곡수명산파크4단지,11500,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,발산·마곡,5,마곡수명산파크7단지,마곡수명산파크7단지,11500,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,암사·천호,1,선사현대,선사현대,11740,2000.0,2938.0,6.0,암사,선사초,신암중,40.0,보류,TOP 후보,84급 예산 초과,,기초검증\n서울,암사·천호,2,강동롯데캐슬퍼스트,강동롯데캐슬퍼스트,11740,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,암사·천호,3,프라이어팰리스,프라이어팰리스,11740,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,암사·천호,4,래미안강동팰리스,래미안강동팰리스,11740,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,답십리,1,래미안위브,래미안위브,11230,2014.0,2652.0,12.0,답십리,답십리초,전농중,30.0,보류,TOP 후보,74㎡ 재검사 필요,,기초검증\n서울,답십리,2,답십리파크자이,답십리파크자이,11230,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,답십리,3,힐스테이트청계,힐스테이트청계,11230,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,답십리,4,답십리두산위브,답십리두산위브,11230,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,답십리,5,청계한신휴플러스,청계한신휴플러스,11230,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,청량리·전농,1,래미안크레시티,래미안크레시티,11230,2014.0,2397.0,15.0,청량리,전농초,전농중,30.0,보류,TOP 후보,74㎡ 재검사 필요,,기초검증\n서울,청량리·전농,2,전농SK,전농SK,11230,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,청량리·전농,3,래미안아름숲,래미안아름숲,11230,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,청량리·전농,4,청량리역롯데캐슬SKY-L65,청량리역롯데캐슬SKY-L65,11230,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,청량리·전농,5,청량리역한양수자인그라시엘,청량리역한양수자인그라시엘,11230,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,신정,1,목동힐스테이트,목동힐스테이트,11470,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,신정,2,신트리1단지,신트리1단지,11470,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,신정,3,신트리4단지,신트리4단지,11470,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,신정,4,목동신시가지13단지,목동신시가지13단지,11470,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,신정,5,목동신시가지12단지,목동신시가지12단지,11470,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,염창,1,염창동아3차,염창동아3차,11500,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,염창,2,염창현대1차,염창현대1차,11500,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,염창,3,e편한세상염창,e편한세상염창,11500,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,염창,4,강변힐스테이트,강변힐스테이트,11500,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,상도,1,상도더샵1차,상도더샵1차,11590,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,상도,2,상도두산위브트레지움,상도두산위브트레지움,11590,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,상도,3,e편한세상상도노빌리티,e편한세상상도노빌리티,11590,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,상도,4,상도역롯데캐슬파크엘,상도역롯데캐슬파크엘,11590,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n서울,상도,5,래미안상도3차,래미안상도3차,11590,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,성복,1,성복역아이파크,성복역아이파크,41465,2012.0,584.0,9.0,성복,성복초,성복중,55.0,핵심,TOP 후보,신분당선 접근,,기초검증\n경기남부,성복,2,성복역롯데캐슬골드타운,성복역롯데캐슬골드타운,41465,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,성복,3,성복자이1차,성복자이1차,41465,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,성복,4,성복자이2차,성복자이2차,41465,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,성복,5,버들치마을경남아너스빌1차,버들치마을경남아너스빌1차,41465,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,수지구청,1,현대,현대,41465,1994.0,1168.0,7.0,수지구청,토월초,문정중,50.0,핵심,조건충족,"전용 84㎡·수지구청역 도보권. 구축·주차는 감점, 학원가/생활편의 강점.",https://zippoom.com/%EB%B6%80%EB%8F%99%EC%82%B0/%EA%B2%BD%EA%B8%B0-%EC%9A%A9%EC%9D%B8%EC%8B%9C-%EC%88%98%EC%A7%80%EA%B5%AC-%ED%92%8D%EB%8D%95%EC%B2%9C%EB%8F%99-%ED%98%84%EB%8C%80%EC%95%84%ED%8C%8C%ED%8A%B8/tf1tl3,기초검증\n경기남부,수지구청,2,진산마을삼성5차,진산마을삼성5차,41465,2001.0,611.0,13.0,수지구청,풍천초,이현중,55.0,핵심,조건충족,전용 84㎡·대단지·풍천초 인접. 역은 현대보다 멀지만 단지/학군 균형이 좋음.,https://m.richgo.ai/realty/danji/a4skJfn,기초검증\n경기남부,수지구청,3,e편한세상수지,e편한세상수지,41465,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,수지구청,4,신정마을9단지LG,신정마을9단지LG,41465,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,수지구청,5,신정마을1단지주공,신정마을1단지주공,41465,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,인덕원,1,동편마을3단지,동편마을(관양휴먼시아3단지),41173,2012.0,1042.0,20.0,인덕원,해오름초,관양중,60.0,핵심,조건충족,전용 74~84㎡·2012년식. 역거리 20분으로 상한선이지만 가격/연식 균형이 좋음.,https://zippoom.com/%EB%B6%80%EB%8F%99%EC%82%B0/%EA%B2%BD%EA%B8%B0-%EC%95%88%EC%96%91%EC%8B%9C-%EB%8F%99%EC%95%88%EA%B5%AC-%EA%B4%80%EC%96%91%EB%8F%99-%EB%8F%99%ED%8E%B8%EB%A7%88%EC%9D%843%EB%8B%A8%EC%A7%80/2v44a6,기초검증\n경기남부,인덕원,2,인덕원대우,인덕원대우,41173,2001.0,1996.0,13.0,인덕원,벌말초,인덕원중,58.0,핵심,조건충족,"전용 84.96㎡·1,996세대·인덕원역 도보권. 현재 TARGET권으로 핵심 비교대상.",https://www.aptrank.com/apt_detail.php?aptnameuid=15882,기초검증\n경기남부,인덕원,3,인덕원마을삼성,인덕원마을(삼성),41173,1998.0,1314.0,6.0,인덕원,인덕원초,인덕원중,55.0,관찰,가격경계,역 접근은 매우 좋지만 전용 84.93㎡는 14억 거래도 있어 MAX 초과 가능성 큼.,https://realty.daangn.com/complexes/15077022,기초검증\n경기남부,철산,1,철산주공12단지,철산주공12단지,41210,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,철산,2,철산래미안자이,철산래미안자이,41210,2009.0,2072.0,13.0,철산,철산초,철산중,48.0,보류,가격초과,"전용 84㎡·2,072세대·상품성 우수. 84㎡ 매물/시세가 현재 MAX를 넘어 예산 관찰용.",https://zippoom.com/%EB%B6%80%EB%8F%99%EC%82%B0/%EA%B2%BD%EA%B8%B0-%EA%B4%91%EB%AA%85%EC%8B%9C-%EC%B2%A0%EC%82%B0%EB%8F%99-%EB%9E%98%EB%AF%B8%EC%95%88%EC%9E%90%EC%9D%B4/x5uwew,기초검증\n경기남부,철산,3,철산자이더헤리티지,철산자이더헤리티지,41210,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,철산,4,철산센트럴푸르지오,철산센트럴푸르지오,41210,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,철산,5,철산푸르지오하늘채,철산푸르지오하늘채,41210,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,범계,1,목련2단지대우선경,목련2단지대우선경,41173,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,범계,2,목련3단지우성,목련3단지우성,41173,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,범계,3,무궁화효성,무궁화효성,41173,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,범계,4,샛별한양4단지,샛별한양4단지,41173,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,범계,5,목련우성5단지,목련우성5단지,41173,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,광명사거리,1,광명한진타운,광명한진타운,41210,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,광명사거리,2,광명해모로이연,광명해모로이연,41210,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,광명사거리,3,광명아크포레자이위브,광명아크포레자이위브,41210,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,광명사거리,4,광명푸르지오센트베르,광명푸르지오센트베르,41210,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,광명사거리,5,광명호반써밋그랜드에비뉴,광명호반써밋그랜드에비뉴,41210,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,미사,1,미사강변센트럴자이,미사강변센트럴자이,41450,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,미사,2,미사강변푸르지오,미사강변푸르지오,41450,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,미사,3,미사강변리버뷰자이,미사강변리버뷰자이,41450,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,미사,4,미사강변동원로얄듀크,미사강변동원로얄듀크,41450,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,미사,5,미사강변센트리버,미사강변센트리버,41450,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,평촌,1,초원대림,초원마을대림,41173,1993.0,1035.0,13.0,평촌,귀인초,평촌중,60.0,핵심,가격경계,전용 84㎡·귀인초/평촌 학군. 84㎡ 최근 13.34억으로 MAX 바로 아래 경계.,https://kbland.kr/se/c/4772,기초검증\n경기남부,평촌,2,한가람삼성,한가람삼성,41173,1995.0,708.0,15.0,평촌,안양부안초,부림중,60.0,핵심,조건충족,전용 84.93㎡·708세대. 평촌역 도보권에서 가격 여유가 큰 가성비 비교대상.,https://kbland.kr/c/4764,기초검증\n경기남부,평촌,3,향촌롯데,향촌롯데,41173,1993.0,530.0,12.0,범계,평촌초,평촌중,58.0,보류,가격초과,"전용 84㎡·귀인중 학군 강점. 현재 84㎡는 15억대라 MAX 초과, 가격 하락 시 재진입 후보.",https://realty.daangn.com/complexes/15075176,기초검증\n경기남부,평촌,4,귀인마을현대홈타운,귀인마을현대홈타운,41173,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,평촌,5,꿈마을라이프,꿈마을라이프,41173,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,영통,1,영통아이파크캐슬1단지,영통아이파크캐슬1단지,41117,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,영통,2,영통아이파크캐슬2단지,영통아이파크캐슬2단지,41117,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,영통,3,청명마을4단지삼성,청명마을4단지삼성,41117,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,영통,4,신나무실5단지주공,신나무실5단지주공,41117,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,영통,5,벽적골8단지주공,벽적골8단지주공,41117,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,망포,1,힐스테이트영통,힐스테이트영통,41117,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,망포,2,영통아이파크캐슬2단지,영통아이파크캐슬2단지,41117,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,망포,3,망포마을쌍용1차,망포마을쌍용1차,41117,,,,,,,,핵심,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,망포,4,그대가프리미어,그대가프리미어,41117,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n경기남부,망포,5,영통SK뷰,영통SK뷰,41117,,,,,,,,관찰,TOP 후보,생활권 TOP 후보. 가격은 국토부 API로 자동 갱신; 세대수·역거리·학교 등 정적조건은 상세 검증 보강 예정.,,추가검증\n'
SEED_CSV = 'complex_name,area_m2,low_2026,high_2026,source_note\nSK북한산시티,84.0,8.1,8.4,대화 중 1차 검증치\n벽산라이브파크,,,,\n삼각산아이원,,,,\n두산위브트레지움,,,,\n꿈의숲롯데캐슬,,,,\n한마을,84.0,9.8,10.7,대화 중 1차 검증치\n개봉푸르지오,,,,\n개봉한진,,,,\n개봉삼환,,,,\n두산,84.0,10.4,11.8,대화 중 1차 검증치\n신림푸르지오,84.0,10.5,11.3,대화 중 1차 검증치\n신림현대,,,,\n관악산휴먼시아2단지,,,,\n관악산휴먼시아1단지,,,,\n두산,84.0,10.4,11.8,대화 중 1차 검증치\n창신쌍용1,,,,\n창신쌍용2,,,,\n종로센트레빌,84.0,12.5,12.5,대화 중 1차 검증치\n대림e편한세상,84.0,11.7,12.4,이문 후보 1차 검증치\n래미안라그란데,,,,\n이문아이파크자이,,,,\n이문쌍용,,,,\n관악드림타운,84.0,12.1,12.7,대화 중 1차 검증치\n봉천우성,,,,\ne편한세상서울대입구1단지,,,,\n관악벽산블루밍1차,,,,\n서울대입구아이원,,,,\n등촌아이파크,84.0,12.0,12.8,대화 중 1차 검증치\n등촌주공5단지,,,,\n등촌주공6단지,,,,\n등촌동부센트레빌,,,,\n등촌대림,,,,\n홍제원현대,,,,\n홍제한양,,,,\n홍제현대,,,,\n인왕산현대,,,,\n청구1차,84.78,11.75,12.65,대화 중 1차 검증치\n장안현대홈타운1차,,,,\n장안삼성래미안2차,,,,\n장안힐스테이트,,,,\n장안삼성래미안1차,,,,\n장안삼성쉐르빌,,,,\n강나루현대,84.0,12.6,13.3,대화 중 1차 검증치\n강서한강자이,,,,\n가양우성,,,,\n보라매파크빌,84.0,13.1,13.5,대화 중 1차 검증치\n신대방현대,,,,\n보라매자이더포레스트,,,,\n롯데낙천대,,,,\n신대방경남교수,,,,\n마곡수명산파크1단지,,,,\n마곡수명산파크2단지,,,,\n마곡수명산파크3단지,,,,\n마곡수명산파크4단지,,,,\n마곡수명산파크7단지,,,,\n선사현대,83.0,16.9,20.0,대화 중 1차 검증치\n강동롯데캐슬퍼스트,,,,\n프라이어팰리스,,,,\n래미안강동팰리스,,,,\n래미안위브,84.0,16.2,18.0,대화 중 1차 검증치\n답십리파크자이,,,,\n힐스테이트청계,,,,\n답십리두산위브,,,,\n청계한신휴플러스,,,,\n래미안크레시티,84.0,16.4,18.0,대화 중 1차 검증치\n전농SK,,,,\n래미안아름숲,,,,\n청량리역롯데캐슬SKY-L65,,,,\n청량리역한양수자인그라시엘,,,,\n목동힐스테이트,,,,\n신트리1단지,,,,\n신트리4단지,,,,\n목동신시가지13단지,,,,\n목동신시가지12단지,,,,\n염창동아3차,,,,\n염창현대1차,,,,\ne편한세상염창,,,,\n강변힐스테이트,,,,\n상도더샵1차,,,,\n상도두산위브트레지움,,,,\ne편한세상상도노빌리티,,,,\n상도역롯데캐슬파크엘,,,,\n래미안상도3차,,,,\n성복역아이파크,84.0,10.4,11.3,대화 중 1차 검증치\n성복역롯데캐슬골드타운,,,,\n성복자이1차,,,,\n성복자이2차,,,,\n버들치마을경남아너스빌1차,,,,\n현대,84.51,12.1,12.5,"2026-08 웹 재검증: 수지구청역 도보권, 31평형 시세/최근거래"\n진산마을삼성5차,84.9,12.3,12.9,2026-08 웹 재검증: 34평형 시세 약 12.6억 중심\ne편한세상수지,,,,\n신정마을9단지LG,,,,\n신정마을1단지주공,,,,\n동편마을3단지,84.8,11.2,11.7,"2026-08 웹 재검증: 최근 84㎡ 11.2억, 시세 약 11.7억"\n인덕원대우,84.96,12.0,12.3,2026-08 웹 재검증: 전용84 최근 12.3억\n인덕원마을삼성,84.93,11.1,14.0,2026-08 웹 재검증: 84.93㎡ 거래 11.1~14.0억 확인\n철산주공12단지,,,,\n철산래미안자이,84.5,14.0,14.6,2026-08 웹 재검증: 33평 전용84 시세/매물 14억대\n철산자이더헤리티지,,,,\n철산센트럴푸르지오,,,,\n철산푸르지오하늘채,,,,\n목련2단지대우선경,,,,\n목련3단지우성,,,,\n무궁화효성,,,,\n샛별한양4단지,,,,\n목련우성5단지,,,,\n광명한진타운,,,,\n광명해모로이연,,,,\n광명아크포레자이위브,,,,\n광명푸르지오센트베르,,,,\n광명호반써밋그랜드에비뉴,,,,\n미사강변센트럴자이,,,,\n미사강변푸르지오,,,,\n미사강변리버뷰자이,,,,\n미사강변동원로얄듀크,,,,\n미사강변센트리버,,,,\n초원대림,84.0,12.5,13.34,"2026-08 웹 재검증: KB 12.5억, 최근 13.34억"\n한가람삼성,84.93,9.7,10.05,"2026-08 웹 재검증: KB 일반가 10.05억, 최근 9.7억"\n향촌롯데,84.0,14.6,15.3,"2026-08 웹 재검증: 33평 시세 14.6억, 최근 15.25~15.3억"\n귀인마을현대홈타운,,,,\n꿈마을라이프,,,,\n영통아이파크캐슬1단지,,,,\n영통아이파크캐슬2단지,,,,\n청명마을4단지삼성,,,,\n신나무실5단지주공,,,,\n벽적골8단지주공,,,,\n힐스테이트영통,,,,\n영통아이파크캐슬2단지,,,,\n망포마을쌍용1차,,,,\n그대가프리미어,,,,\n영통SK뷰,,,,\n'

@st.cache_data
def load_candidates():
    df = pd.read_csv(io.StringIO(CANDIDATES_CSV))
    for c in ["candidate_rank","households","build_year","walk_station_min","commute_eulji_min","lawd_cd"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["candidate_rank"] = df["candidate_rank"].fillna(99).astype(int)
    return df

@st.cache_data
def load_seed():
    return pd.read_csv(io.StringIO(SEED_CSV))

def api_key():
    try:
        return str(st.secrets["DATA_GO_KR_SERVICE_KEY"]).strip()
    except Exception:
        return str(os.getenv("DATA_GO_KR_SERVICE_KEY","")).strip()

def safe_text(v, fallback="검증 중"):
    if pd.isna(v) or str(v).strip() in ["", "0", "0.0", "nan", "None"]:
        return fallback
    return str(v)

def fmt_num(v, suffix="", digits=0, fallback="검증 중"):
    if pd.isna(v):
        return fallback
    try:
        if digits == 0:
            return f"{int(round(float(v))):,}{suffix}"
        return f"{float(v):,.{digits}f}{suffix}"
    except Exception:
        return fallback

def normalize_name(s):
    return str(s).replace(" ","").replace("·","").replace("-","").replace("_","").lower()

def parse_xml_items(text):
    root = ET.fromstring(text)
    result_code = root.findtext(".//resultCode") or ""
    result_msg = root.findtext(".//resultMsg") or ""
    items = []
    for node in root.findall(".//item"):
        item = {}
        for child in list(node):
            item[child.tag] = child.text
        items.append(item)
    return items, result_code, result_msg

@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def fetch_month(lawd_cd, yyyymm, service_key):
    if not service_key:
        return pd.DataFrame(), "NO_KEY"
    endpoint = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
    # 공공데이터포털이 Encoding 키를 보여주는 경우 requests가 %를 다시 인코딩하지 않도록 먼저 decode.
    key = unquote(service_key) if "%" in service_key else service_key
    params = {
        "serviceKey": key,
        "LAWD_CD": str(int(float(lawd_cd))).zfill(5),
        "DEAL_YMD": str(yyyymm),
        "numOfRows": 9999,
        "pageNo": 1,
    }
    try:
        r = requests.get(endpoint, params=params, timeout=18)
        if r.status_code != 200:
            return pd.DataFrame(), f"HTTP {r.status_code}"
        items, code, msg = parse_xml_items(r.text)
        if code and code not in ("000","00"):
            return pd.DataFrame(), f"{code}: {msg}"
        return pd.DataFrame(items), "OK"
    except Exception as e:
        return pd.DataFrame(), f"{type(e).__name__}"

def clean_trades(df):
    if df.empty:
        return df
    rename = {
        "aptNm":"complex_name","excluUseAr":"area_m2","dealAmount":"deal_amount",
        "dealYear":"year","dealMonth":"month","dealDay":"day","floor":"floor",
        "buildYear":"build_year","umdNm":"dong","jibun":"jibun",
        "cdealType":"cancel_type","cdealDay":"cancel_day"
    }
    df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})
    if "deal_amount" in df:
        df["deal_amount_won"] = pd.to_numeric(
            df["deal_amount"].astype(str).str.replace(",","",regex=False), errors="coerce"
        ) * 10000
        df["price_eok"] = df["deal_amount_won"] / 100000000
    if "area_m2" in df:
        df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce")
    for c in ["year","month","day","floor","build_year"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if all(c in df for c in ["year","month","day"]):
        df["deal_date"] = pd.to_datetime(
            dict(year=df["year"],month=df["month"],day=df["day"]), errors="coerce"
        )
    if "cancel_type" in df:
        # 해제된 거래는 비교에서 제외
        cancel = df["cancel_type"].astype(str).str.strip()
        df = df[(cancel=="") | (cancel=="nan") | (cancel=="None")]
    return df

@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def fetch_recent(lawd_cd, months, service_key):
    base = date.today().replace(day=1)
    jobs = []
    for i in range(months):
        ym = (base - relativedelta(months=i)).strftime("%Y%m")
        jobs.append((lawd_cd, ym, service_key))
    frames, statuses = [], []
    # 월별 호출을 병렬화해 첫 화면 시간을 줄임.
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(jobs)))) as ex:
        futs = [ex.submit(fetch_month, *j) for j in jobs]
        for fut in as_completed(futs):
            df, status = fut.result()
            statuses.append(status)
            if not df.empty:
                frames.append(df)
    if not frames:
        return pd.DataFrame(), next((s for s in statuses if s != "OK"), "NO_DATA")
    return clean_trades(pd.concat(frames, ignore_index=True)), "OK"

def filter_complex(df, name):
    if df.empty or "complex_name" not in df:
        return pd.DataFrame()
    target = normalize_name(name)
    n = df["complex_name"].astype(str).apply(normalize_name)
    mask = n.eq(target) | n.str.contains(target, regex=False) | n.apply(lambda x: x in target if x else False)
    out = df[mask].copy()
    if "area_m2" in out:
        out = out[(out["area_m2"] >= AREA_MIN) & (out["area_m2"] <= AREA_MAX)]
    return out.sort_values("deal_date") if "deal_date" in out else out

def summarize(t):
    if t.empty or "price_eok" not in t or "deal_date" not in t:
        return None
    t = t.dropna(subset=["price_eok","deal_date"]).sort_values("deal_date")
    if t.empty:
        return None
    latest = t.iloc[-1]
    prev = t.iloc[-2] if len(t) >= 2 else None
    now = pd.Timestamp.today().normalize()
    r3 = t[t["deal_date"] >= now-pd.DateOffset(months=3)]
    p3 = t[(t["deal_date"] < now-pd.DateOffset(months=3)) &
           (t["deal_date"] >= now-pd.DateOffset(months=6))]
    r12 = t[t["deal_date"] >= now-pd.DateOffset(months=12)]
    m3 = float(r3["price_eok"].median()) if len(r3) else None
    p3m = float(p3["price_eok"].median()) if len(p3) else None
    return {
        "latest": float(latest["price_eok"]),
        "latest_date": latest["deal_date"].date(),
        "previous": float(prev["price_eok"]) if prev is not None else None,
        "m3": m3, "p3": p3m,
        "median_delta": (m3-p3m) if m3 is not None and p3m is not None else None,
        "median_pct": ((m3/p3m)-1)*100 if m3 is not None and p3m else None,
        "count3": len(r3), "count12": len(r12),
        "high": float(t["price_eok"].max()),
        "low": float(t["price_eok"].min()),
    }

def band(p):
    if p is None or pd.isna(p): return "데이터 없음"
    if p <= TARGET: return "🎯 12.42억 이내"
    if p <= WATCH_14: return "🟡 14억 이내"
    if p <= WATCH_15: return "🟠 15억 이내"
    return "🔴 15억 초과"

def crossed(current, previous, threshold):
    return current is not None and previous is not None and current <= threshold < previous

def naver_url(row):
    q = f"네이버페이 부동산 {row['complex_name']} {row['area']}"
    return "https://search.naver.com/search.naver?query=" + quote_plus(q)

@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def snapshot(candidates, service_key):
    if not service_key:
        return pd.DataFrame(), "NO_KEY"
    rows, errors = [], []
    # 6개월이면 최근3개월 vs 직전3개월 비교 가능.
    for lawd in candidates["lawd_cd"].dropna().unique():
        all_t, status = fetch_recent(lawd, 6, service_key)
        if status != "OK":
            errors.append(f"{lawd}:{status}")
            continue
        sub = candidates[candidates["lawd_cd"] == lawd]
        for _, r in sub.iterrows():
            api_nm = safe_text(r.get("api_name"), r["complex_name"])
            if api_nm == "검증 중":
                api_nm = r["complex_name"]
            t = filter_complex(all_t, api_nm)
            s = summarize(t)
            if not s:
                continue
            rows.append({
                "권역":r["region"],"생활권":r["area"],"TOP":int(r["candidate_rank"]),
                "단지":r["complex_name"],"최신거래":s["latest"],"계약일":s["latest_date"],
                "직전거래":s["previous"],"최근3개월":s["m3"],"직전3개월":s["p3"],
                "3개월변화":s["median_delta"],"3개월변화율":s["median_pct"],
                "3개월거래":s["count3"],"가격구간":band(s["latest"]),
                "12.42진입":crossed(s["latest"],s["previous"],TARGET),
                "14진입":crossed(s["latest"],s["previous"],WATCH_14),
                "15진입":crossed(s["latest"],s["previous"],WATCH_15),
            })
    return pd.DataFrame(rows), "; ".join(errors[:5]) if errors else "OK"

C = load_candidates()
SEED = load_seed()
KEY = api_key()

st.title("🏠 서울30평꿀집샀다")
st.caption("서울·경기남부 후보 아파트의 가격 변화와 입지·단지 조건을 한곳에서 추적합니다.")

with st.sidebar:
    page = st.radio("보기", ["한눈에 보기","후보 찾기","단지 상세","생활권 비교","설정/진단"])
    st.divider()
    st.markdown("**가격 관찰선**")
    st.write(f"🎯 {TARGET:.2f}억  ·  🟡 14억  ·  🟠 15억")
    st.caption("전용 74~84㎡ · 500세대 이상 선호 · 역 도보 20분 이내 · 초중 접근")

# 실제 호출 성공 여부를 설정/진단에서 보여주고, 메인에서는 키 존재만으로 '연결됨'이라고 과장하지 않는다.
if KEY:
    st.info("실거래 API 인증키가 등록되어 있습니다. 아래 시세 영역에서 실제 조회 성공 여부를 확인합니다.")
else:
    st.warning("실거래 API 인증키가 없습니다. 가격 자동조회는 동작하지 않습니다.")

if page == "한눈에 보기":
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("후보 단지", f"{len(C)}개")
    k2.metric("생활권", f"{C['area'].nunique()}곳")
    k3.metric("서울 / 경기남부", f"{C[C.region=='서울'].area.nunique()} / {C[C.region=='경기남부'].area.nunique()}")
    k4.metric("가격선", "12.42 / 14 / 15억")

    st.subheader("이번에 먼저 볼 것")
    snap = pd.DataFrame()
    err = ""
    if KEY:
        with st.spinner("후보 단지의 최근 6개월 실거래를 불러오는 중입니다. 첫 조회는 조금 걸릴 수 있어요."):
            snap, err = snapshot(C, KEY)

    if not snap.empty:
        cheaper = snap[snap["3개월변화율"].notna() & (snap["3개월변화율"] < 0)].sort_values("3개월변화율")
        c1242 = snap[snap["12.42진입"]]
        c14 = snap[snap["14진입"]]
        c15 = snap[snap["15진입"]]
        a,b,c,d = st.columns(4)
        a.metric("지난 3개월보다 ↓", f"{len(cheaper)}곳")
        b.metric("12.42억 신규 진입", f"{len(c1242)}곳")
        c.metric("14억 신규 진입", f"{len(c14)}곳")
        d.metric("15억 신규 진입", f"{len(c15)}곳")

        left, right = st.columns([1.15,1])
        with left:
            st.markdown("#### 📉 지난 3개월보다 싸진 곳")
            if len(cheaper):
                show = cheaper[["생활권","TOP","단지","최근3개월","직전3개월","3개월변화","3개월변화율","최신거래"]].head(15).copy()
                st.dataframe(show, use_container_width=True, hide_index=True,
                             column_config={
                                 "최근3개월":st.column_config.NumberColumn(format="%.2f억"),
                                 "직전3개월":st.column_config.NumberColumn(format="%.2f억"),
                                 "3개월변화":st.column_config.NumberColumn(format="%+.2f억"),
                                 "3개월변화율":st.column_config.NumberColumn(format="%+.1f%%"),
                                 "최신거래":st.column_config.NumberColumn(format="%.2f억"),
                             })
            else:
                st.caption("현재 비교 가능한 거래 중 최근 3개월 중앙값이 낮아진 단지가 없습니다.")
        with right:
            st.markdown("#### 🎯 가격선 안으로 들어온 곳")
            entered = []
            for label,df in [("12.42억",c1242),("14억",c14),("15억",c15)]:
                for _,r in df.iterrows():
                    entered.append([label,r["생활권"],r["단지"],r["직전거래"],r["최신거래"],r["계약일"]])
            if entered:
                st.dataframe(pd.DataFrame(entered,columns=["진입선","생활권","단지","직전거래","최신거래","계약일"]),
                             use_container_width=True, hide_index=True)
            else:
                st.caption("직전 거래 대비 새로 가격선 아래로 내려온 단지가 없습니다.")

        st.markdown("#### 전체 후보 현재 실거래")
        f1,f2,f3 = st.columns([1,1,2])
        reg = f1.multiselect("권역",["서울","경기남부"],default=["서울","경기남부"])
        bands = f2.multiselect("가격구간",["🎯 12.42억 이내","🟡 14억 이내","🟠 15억 이내","🔴 15억 초과"],
                               default=["🎯 12.42억 이내","🟡 14억 이내","🟠 15억 이내","🔴 15억 초과"])
        search = f3.text_input("생활권·단지 검색",placeholder="예: 이문, 평촌, 푸르지오")
        view = snap[snap["권역"].isin(reg) & snap["가격구간"].isin(bands)].copy()
        if search.strip():
            q = search.strip()
            view = view[view["생활권"].str.contains(q,case=False,na=False) | view["단지"].str.contains(q,case=False,na=False)]
        view = view.sort_values(["최신거래","생활권"])
        st.dataframe(view[["권역","생활권","TOP","단지","최신거래","계약일","최근3개월","직전3개월","3개월변화율","3개월거래","가격구간"]],
                     use_container_width=True, hide_index=True,
                     column_config={
                         "최신거래":st.column_config.NumberColumn(format="%.2f억"),
                         "최근3개월":st.column_config.NumberColumn(format="%.2f억"),
                         "직전3개월":st.column_config.NumberColumn(format="%.2f억"),
                         "3개월변화율":st.column_config.NumberColumn(format="%+.1f%%"),
                     })
        st.caption("‘싸진 곳’은 개별 한 건이 아니라 최근 3개월 중앙값과 직전 3개월 중앙값을 비교합니다.")
    else:
        st.error("최신 실거래를 아직 불러오지 못했습니다.")
        if err:
            st.caption(f"API 응답 진단: {err}")
        st.info("왼쪽의 **설정/진단**에서 실제 API 테스트를 먼저 확인해 주세요. 후보 목록 자체는 아래 메뉴에서 정상적으로 볼 수 있습니다.")

elif page == "후보 찾기":
    st.subheader("생활권별 후보 TOP 5")
    a,b,c = st.columns([1,1,2])
    region = a.selectbox("권역",["전체","서울","경기남부"])
    area_options = sorted(C["area"].unique().tolist())
    area = b.selectbox("생활권",["전체"]+area_options)
    q = c.text_input("단지 검색",placeholder="단지명 입력")
    v = C.copy()
    if region != "전체": v = v[v["region"]==region]
    if area != "전체": v = v[v["area"]==area]
    if q.strip(): v = v[v["complex_name"].str.contains(q.strip(),case=False,na=False)]
    v = v.sort_values(["region","area","candidate_rank"])
    show = v[["region","area","candidate_rank","complex_name","households","build_year","nearest_station",
              "walk_station_min","elementary_school","middle_school","commute_eulji_min","static_data_status","note"]].copy()
    show.columns = ["권역","생활권","TOP","단지","세대수","준공","역","역도보(분)","초등","중등","을지로(분)","조건검증","메모"]
    st.dataframe(show,use_container_width=True,hide_index=True)
    st.caption("TOP은 현재의 후보 순번입니다. ‘추가검증’ 단지는 세대수·학교·역거리 등을 더 확인한 뒤 최종순위가 바뀔 수 있습니다.")

elif page == "단지 상세":
    s1,s2 = st.columns([1,2])
    areas = sorted(C["area"].unique())
    area = s1.selectbox("생활권",areas)
    sub = C[C["area"]==area].sort_values("candidate_rank")
    labels = [f"TOP {r.candidate_rank} · {r.complex_name}" for _,r in sub.iterrows()]
    selected = s2.selectbox("단지",labels)
    rank = int(selected.split(" · ")[0].replace("TOP ",""))
    row = sub[sub["candidate_rank"]==rank].iloc[0]

    st.subheader(f"{row['area']} · TOP {rank} · {row['complex_name']}")
    price_col, info_col = st.columns([1.7,1])

    with info_col:
        st.markdown("#### 입지·단지 조건")
        st.write(f"**세대수**  {fmt_num(row['households'],'세대')}")
        st.write(f"**준공**  {fmt_num(row['build_year'],'년')}")
        station = safe_text(row["nearest_station"])
        walk = fmt_num(row["walk_station_min"],"분")
        st.write(f"**역 접근**  {station} · 도보 {walk}")
        st.write(f"**초등**  {safe_text(row['elementary_school'])}")
        st.write(f"**중등**  {safe_text(row['middle_school'])}")
        st.write(f"**을지로입구**  약 {fmt_num(row['commute_eulji_min'],'분')}")
        st.write(f"**조건 검증**  {safe_text(row['static_data_status'])}")
        if pd.notna(row.get("note")):
            st.info(str(row["note"]))
        st.link_button("🏠 네이버부동산 현재 매물 찾기",naver_url(row),use_container_width=True)
        st.link_button("🏛️ 국토부 실거래가 공개시스템","https://rt.molit.go.kr/",use_container_width=True)

    with price_col:
        if KEY and pd.notna(row["lawd_cd"]):
            with st.spinner("이 단지 최근 5년 74~84㎡ 거래를 불러오는 중..."):
                all_t,status = fetch_recent(row["lawd_cd"],60,KEY)
            api_nm = safe_text(row.get("api_name"),row["complex_name"])
            if api_nm=="검증 중": api_nm=row["complex_name"]
            t = filter_complex(all_t,api_nm)
            s = summarize(t)
            if s:
                m1,m2,m3,m4 = st.columns(4)
                m1.metric("최신 실거래",f"{s['latest']:.2f}억",str(s["latest_date"]))
                m2.metric("최근 3개월 중앙값",f"{s['m3']:.2f}억" if s["m3"] is not None else "-")
                m3.metric("최근 12개월 거래",f"{s['count12']}건")
                m4.metric("현재 가격구간",band(s["latest"]))
                if s["p3"] is not None and s["m3"] is not None:
                    st.caption(f"직전 3개월 중앙값 {s['p3']:.2f}억 → 최근 3개월 {s['m3']:.2f}억 "
                               f"({s['median_pct']:+.1f}%)")
                st.caption(f"조회된 5년 최고 {s['high']:.2f}억 / 최저 {s['low']:.2f}억 · "
                           f"최신은 최고가 대비 {(s['latest']/s['high']-1)*100:+.1f}%")
                plot = t.dropna(subset=["deal_date","price_eok"]).sort_values("deal_date")
                fig = px.scatter(plot,x="deal_date",y="price_eok",hover_data=["area_m2","floor"],
                                 labels={"deal_date":"계약일","price_eok":"거래가(억)"},
                                 title="최근 5년 74~84㎡ 실거래")
                fig.add_hline(y=TARGET,line_dash="dash",annotation_text="12.42억")
                fig.add_hline(y=WATCH_14,line_dash="dot",annotation_text="14억")
                fig.add_hline(y=WATCH_15,line_dash="dashdot",annotation_text="15억")
                st.plotly_chart(fig,use_container_width=True)
                st.dataframe(plot.sort_values("deal_date",ascending=False)[
                    [c for c in ["deal_date","price_eok","area_m2","floor","dong","jibun"] if c in plot.columns]
                ].head(30),use_container_width=True,hide_index=True,
                column_config={"price_eok":st.column_config.NumberColumn(format="%.2f억"),
                               "area_m2":st.column_config.NumberColumn(format="%.1f㎡")})
            else:
                st.warning("국토부 데이터는 받아왔지만 이 단지명이 정확히 매칭되지 않았습니다. 후보DB의 API 단지명을 보정해야 합니다.")
        else:
            st.info("API 키 또는 법정구 코드가 없어 가격을 불러올 수 없습니다.")

elif page == "생활권 비교":
    st.subheader("생활권 비교")
    choices = st.multiselect("비교할 생활권",sorted(C["area"].unique()),default=["신림","이문·신이문","평촌","성복"])
    v = C[C["area"].isin(choices)].sort_values(["area","candidate_rank"])
    show = v[["region","area","candidate_rank","complex_name","households","build_year","nearest_station",
              "walk_station_min","commute_eulji_min","static_data_status","note"]].copy()
    show.columns=["권역","생활권","TOP","단지","세대수","준공","역","역도보(분)","을지로(분)","조건검증","메모"]
    st.dataframe(show,use_container_width=True,hide_index=True)
    st.caption("가격은 ‘한눈에 보기’와 ‘단지 상세’에서 실거래 기준으로 확인하고, 이 화면은 입지·단지조건을 나란히 보는 용도입니다.")

else:
    st.subheader("설정 / API 진단")
    st.write("이 버전은 후보DB를 **app.py 안에 내장**했습니다. 앞으로 CSV 파일 버전이 섞여 `33개/TOP99`가 나오는 문제를 막습니다.")
    st.write(f"- 내장 후보 단지: **{len(C)}개**")
    st.write(f"- 생활권: **{C['area'].nunique()}곳**")
    st.write("- 데이터 캐시: **1시간**")
    if st.button("캐시 지우고 다시 조회"):
        st.cache_data.clear()
        st.rerun()
    if KEY:
        test_row = C[C["lawd_cd"].notna()].iloc[0]
        ym = date.today().strftime("%Y%m")
        if st.button("국토부 API 실제 연결 테스트"):
            with st.spinner("테스트 중..."):
                d,status = fetch_month(test_row["lawd_cd"],ym,KEY)
            if status=="OK":
                st.success(f"API 실제 호출 성공 · {ym} · 응답 {len(d)}건")
            else:
                st.error(f"API 실제 호출 실패: {status}")
                st.caption("공공데이터포털에서 신청한 API가 ‘아파트 매매 실거래가 자료’인지, 인증키가 유효한지 확인하세요.")
    else:
        st.error("DATA_GO_KR_SERVICE_KEY가 Streamlit Secrets에 없습니다.")

st.divider()
st.caption("가격 데이터: 국토교통부 아파트 매매 실거래가 Open API. 최근 신고는 추후 추가·정정될 수 있습니다. 네이버부동산 버튼은 현재 호가 확인용 외부 검색 링크입니다.")
