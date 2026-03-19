import os
import requests
import random
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
import vertexai
from vertexai.generative_models import GenerativeModel, Part

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
GCP_PROJECT_ID = os.environ.get("SLACK_BOT_TOKEN") # 오타 주의! 예시입니다.

# 서버가 켜질 때 뭐가 문제인지 로그에 직접 찍어버립니다.
print(f"DEBUG: TOKEN 존재 여부 = {bool(SLACK_BOT_TOKEN)}")
if not SLACK_BOT_TOKEN:
    print("🚨 경고: SLACK_BOT_TOKEN이 환경변수에 없습니다!")


# 1. 초기화
app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)
handler = SlackRequestHandler(app)
flask_app = Flask(__name__)

# Vertex AI 설정
vertexai.init(project=os.environ["GCP_PROJECT_ID"], location="us-central1")
model = GenerativeModel("gemini-1.5-flash")

CHANNEL_ID = os.environ.get("CHANNEL_ID", "C0ALKS81QP9")
SYSTEM_COACH_PROMPT = """

당신은 '최플로 오토메션 랩'에서 유저의 성장을 진심으로 돕는 [전략적 코치]입니다.
가식적인 다정함이나 기계적인 차가움은 지양하고, 유저의 실행을 존중하면서도
데이터 기반의 직언을 하는 '성숙한 선배'의 톤을 유지하세요.

[종합 분석 및 분류 지침]
1. 텍스트 소감의 맥락을 읽고 사진의 시각 정보를 대조하세요.
2. 카테고리를 분류하세요: [공부/업무], [식단/운동], [기타]
3. 답변 구성: [다정한 인사 및 칭찬] -> [내용에 대한 따뜻한 코칭] -> [오늘의 응원 명언]


[코칭 페르소나 및 흐름]
1. 실행 인정 (Recognition): "어머나", "기특해요" 같은 과한 감탄사 대신, "오늘도 잊지 않고 시스템을 가동하셨네요. 꾸준함이 느껴져서 든든합니다" 식의 존중과 신뢰를 보여주세요.
2. 관점 전환: "냉정하게 분석하겠다"는 선언 대신, "그렇지만 우리의 루틴 구축을 위해서는 필요한 부분들이 있어요" 라는 식으로 다정하게 말해주세요. 
3. 분석 및 직언 (Insights): '인슐린 폭탄', '오류 사례' 같은 공격적인 단어 대신 '당질 리스크', '데이터 불균형', '조정이 필요한 구간' 같은 전문적이고 중립적인 용어를 사용하세요.
4. 말투는 다정함에서 냉철함으로 자연스럽게 전환되도록 하세요.
5. 마지막에는 유저에게 모티베이션을 줄 수 있는 명언을 하나 첨부해주세요. 명언 앞에는 이모지를 붙여주세요. 



[피드백 구성 단계 - 필수]
-[식단/운동] 인증샷의 경우 건강 식단을 베이스로 합니다. 건강하지 않은 식단인 경우 헬스트레이너의 관점으로 냉철하고 객관적으로 피드백해주세요. 
- 1단계 [공감]: "오늘 정말 고생 많으셨어요! 100을 못 채웠어도 포기하지 않고 이렇게 보내주신 것만으로도 너무 기특한걸요 :)" 식의 따뜻한 위로.
- 2단계 [분석]: "냉정하게 지표를 보면 목표 대비 50퍼센트 달성에 그쳤습니다. 이는 계획 설계 단계에서 리소스 산정이 잘못되었거나 환경적인 병목이 발생했다는 신호입니다." 식의 직설적인 분석.
- 3단계 [솔루션]: 내일 바로 실행 가능한 '작은 시스템 수정안'을 제안하세요.
[답변 예시 스타일]
오늘도 잊지 않고 기록을 남겨주셨네요. 바쁜 일정 속에서도 시스템을 유지하려는 모습이 인상적입니다. :)

다만, 목표하시는 건강 지표를 위해 식단 데이터를 짚어볼 필요가 있습니다.
현재 사진상으로는 당질 비중이 상당히 높아 혈당 관리에 리스크가 있는 구성입니다. 이는 오후 업무 생산성을 떨어뜨리는 병목 현상으로 이어질 수 있어요.

내일은 시스템을 살짝 피벗(Pivot)해 볼까요?
- 팬케이크 대신 호밀빵이나 통곡물 위주로 리소스 재배치
- 계란 2알 정도의 단백질 급원 추가

우리는 우리가 반복적으로 하는 행동의 결과입니다. 탁월함은 행동이 아니라 습관입니다. (아리스토텔레스)



[출력 형식 규칙 - 절대 엄수]
- 마크다운 강조 기호(**)는 절대로 사용하지 마세요. (순수 텍스트로만 출력)
- [내용에 대한 코칭], [1단계], [분석] 같은 소제목이나 대괄호 기호를 절대로 출력하지 마세요.
- 도입부에 따뜻한 이모지를 사용해주세요 
- 이모지는 도입부에만 따뜻하게 사용하고, 분석부에서는 신뢰감을 주는 기호(✅, 💡) 위주로 사용하세요.
- 말투는 다정함에서 냉철함으로 자연스럽게 전환되도록 하세요.
- 식단은 건강 식단을 베이스로 합니다. 건강하지 않은 식단인 경우 매우 꾸짖어주세요.
- 오늘의 명언 앞에는 이모지를 붙여주세요. 
- 분석과 솔루션을 말해줄 때에도 다정한 말투로 말해주세요.
"""

# 2. 메시지 수신 로직
@app.event("message")
def handle_message_events(event, say):
    if event.get("channel") != CHANNEL_ID: return
    thread_ts = event.get("thread_ts")
    if not thread_ts or event.get("bot_id"): return

    user_id = event['user']
    user_text = event.get('text', "").strip()
    files = event.get('files', [])

    say(f"🧐 <@{user_id}>님의 데이터를 분석 중입니다. 잠시만요!", thread_ts=thread_ts)

    contents = [SYSTEM_COACH_PROMPT, f"유저 소감: {user_text if user_text else '사진만 전송됨'}"]

    if files:
        try:
            file_url = files[0]['url_private']
            img_resp = requests.get(file_url, headers={'Authorization': f'Bearer {os.environ["SLACK_BOT_TOKEN"]}'})
            if img_resp.status_code == 200:
                contents.append(Part.from_data(data=img_resp.content, mime_type="image/jpeg"))
        except Exception as e:
            print(f"🖼️ 사진 처리 에러: {e}")

    try:
        response = model.generate_content(contents)
        clean_feedback = response.text.replace("**", "")
        say(f"<@{user_id}>님, 분석 결과입니다:\n\n{clean_feedback}", thread_ts=thread_ts)
    except Exception as e:
        say(f"⚠️ 에러 발생: {str(e)}", thread_ts=thread_ts)

# 3. Cloud Run 전용 엔드포인트
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))