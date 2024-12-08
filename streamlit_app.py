import os
import streamlit as st
import pandas as pd
import openai

# -------------------------------
# 설정: OpenAI API Key
# -------------------------------
# 환경 변수에서 OpenAI API Key를 가져옵니다.
openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------------
# 챗봇 이름 및 브랜딩
# -------------------------------
CHATBOT_NAME = "성실당 챗봇"
WELCOME_MESSAGE = (
    f"안녕하세요! 저는 대전 중구 지역경제 활성화를 위해 노력하는 {CHATBOT_NAME}입니다. "
    "관광 명소, 소상공인 정보, 장소 추천 등 궁금한 점이 있다면 편하게 질문해주세요! "
    "좌측 상단 추천 필터의 카테고리와 여유 시간을 선택하여 추천을 받을 수 있습니다.\n\n"
    "주의: 이 챗봇은 오직 **대전 중구 관련 정보**만 제공합니다."
)

# -------------------------------
# Streamlit 기본 설정
# -------------------------------
st.set_page_config(
    layout="wide",
    page_title="성실당 챗봇",
    page_icon="🍞"
)

# -------------------------------
# CSS 스타일 적용
# -------------------------------
st.markdown(
    """
    <style>
    body {
        font-family: 'Noto Sans KR', sans-serif;
        background: linear-gradient(to bottom right, #fdfbfb, #ebedee);
    }
    .title-container {
        margin-bottom: 30px;
        text-align: center;
        padding-top: 30px;
    }
    .title-container h1 {
        margin-bottom: 10px;
        font-size: 2.2em;
        font-weight: bold;
        color: #333;
    }
    .title-container p {
        font-size: 1.1em;
        color: #555;
    }
    .chat-container {
        margin-top: 20px; 
        display: flex; 
        flex-direction: column; 
        gap: 20px;
    }
    .user-message, .bot-message {
        display: flex; 
        align-items: center;
    }
    .user-message {
        justify-content: flex-end; 
    }
    .bot-message {
        justify-content: flex-start;
    }
    .message-bubble {
        padding: 12px 18px; 
        border-radius: 20px; 
        font-size: 1em; 
        max-width: 70%; 
        line-height: 1.5;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .user-bubble {
        background: #d4f1c5; 
        color: #333; 
    }
    .bot-bubble {
        background: #ffffff; 
        color: #333;
    }
    .recommendation {
        background-color: #FFF9E6; 
        padding: 10px; 
        border-radius: 10px; 
        margin: 10px 0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        font-size: 0.95em;
    }
    .recommendation b {
        color: #333;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------
# 상단 제목 영역
# -------------------------------
st.markdown(
    f"""
    <div class="title-container">
        <h1>성실당 챗봇 서비스</h1>
        <p>여기는 여러분을 도와줄 <strong>{CHATBOT_NAME}</strong>의 공간입니다!</p>
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------------------
# 데이터 로드 함수
# -------------------------------
@st.cache_data
def load_data():
    tourism_data_path = "./data/대전관광명소.csv"
    small_business_data_path = "./data/소상공인_성심당_거리계산.csv"
    
    tourism_data = pd.read_csv(tourism_data_path)
    small_business_data = pd.read_csv(small_business_data_path)

    tourism_data['카테고리'] = tourism_data['구분']
    tourism_data['이름'] = tourism_data['명소명']
    tourism_data['주소'] = tourism_data['소재지']
    tourism_data['거리(km)'] = tourism_data['이동시간_분_차'] * 0.06
    tourism_data['이동시간_분_차'] = tourism_data['이동시간_분_차']
    tourism_data['이동시간_분_보행'] = tourism_data['이동시간_분_보행']

    small_business_data['카테고리'] = small_business_data['상권업종소분류명']
    small_business_data['이름'] = small_business_data['상호명']
    small_business_data['주소'] = small_business_data['도로명주소']
    small_business_data['거리(km)'] = small_business_data['이동시간_분_차'] * 0.06
    small_business_data['이동시간_분_차'] = small_business_data['이동시간_분_차']
    small_business_data['이동시간_분_보행'] = small_business_data['이동시간_분_보행']

    combined_data = pd.concat(
        [
            tourism_data[['카테고리', '이름', '주소', '거리(km)', '이동시간_분_차', '이동시간_분_보행']],
            small_business_data[['카테고리', '이름', '주소', '거리(km)', '이동시간_분_차', '이동시간_분_보행']]
        ], 
        ignore_index=True
    )
    return combined_data

combined_data = load_data()

# -------------------------------
# 상태 초기화
# -------------------------------
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.chat_history.append(("Bot", WELCOME_MESSAGE))

if 'recommendations' not in st.session_state:
    st.session_state.recommendations = []

# -------------------------------
# 추천 함수
# -------------------------------
def recommend_places(category, time_limit):
    try:
        distance_limit = {"10분": 1, "20분": 2, "30분": 3, "1시간 이내": 5}[time_limit]
        filtered_data = combined_data[
            (combined_data['카테고리'] == category) & 
            (combined_data['거리(km)'] <= distance_limit)
        ]
        if not filtered_data.empty:
            recommendations = filtered_data.sample(n=min(3, len(filtered_data))).to_dict('records')
            return recommendations
        else:
            return None
    except Exception as e:
        st.error(f"추천 중 오류 발생: {e}")
        return None

# -------------------------------
# 사용자 메시지 처리
# -------------------------------
def handle_user_question(user_message):
    try:
        if ("대전" not in user_message) and ("중구" not in user_message):
            return "이 서비스는 대전 중구 관련 정보만 제공합니다. 대전 중구와 관련된 질문을 해주세요."
        
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"당신은 대전 중구 관련 도움을 제공하는 {CHATBOT_NAME}입니다."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return completion['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"오류 발생: {e}"

# -------------------------------
# Streamlit UI 구성
# -------------------------------
st.sidebar.header("추천 필터")
all_categories = combined_data['카테고리'].dropna().unique().tolist()
category = st.sidebar.selectbox("카테고리", ["선택하세요"] + all_categories, key="category")
time_limit = st.sidebar.selectbox("시간", ["선택하세요", "10분", "20분", "30분", "1시간 이내"], key="time_limit")

if st.sidebar.button("추천받기"):
    recommendations = recommend_places(category, time_limit)
    st.session_state.recommendations = recommendations if recommendations else []

if st.session_state.recommendations:
    for rec in st.session_state.recommendations:
        st.markdown(
            f"<div class='recommendation'>"
            f"<b>{rec['이름']}</b><br>"
            f"주소: {rec['주소']}<br>"
            f"거리: {rec['거리(km)']:.2f}km<br>"
            f"이동시간(차량): {rec['이동시간_분_차']}분<br>"
            f"이동시간(보행): {rec['이동시간_분_보행']}분</div>",
            unsafe_allow_html=True
        )

st.text_input("메시지를 입력하세요:", key="user_message", on_change=lambda: st.session_state.chat_history.append(
    ("User", st.session_state["user_message"])
))
