import streamlit as st
import google.generativeai as genai
import os

# Gemini 모델 설정
# API 키는 직접 노출보다는 환경 변수 등으로 관리하는 것이 좋습니다.
# 실제 배포 시에는 Streamlit Secrets (secrets.toml)를 사용하거나,
# 환경 변수를 통해 주입하는 방식을 권장합니다.
try:
    # 환경 변수에서 API 키 로드 시도
    # os.getenv로 환경 변수도 고려할 수 있지만, Streamlit Cloud 배포 시에는 st.secrets가 일반적입니다.
    # 여기서는 st.secrets만 사용하도록 코드를 간결하게 했습니다.
    api_key = st.secrets["GOOGLE_API_KEY"]

    if not api_key:
         # API 키가 여전히 없으면 오류 발생 (secrets에 설정되어 있지 않은 경우)
        st.error("Streamlit Secrets에 'GOOGLE_API_KEY'가 설정되지 않았습니다.")
        st.stop() # 앱 실행 중단

    genai.configure(api_key=api_key)

except KeyError:
     # st.secrets["GOOGLE_API_KEY"] 접근 시 키가 없을 경우 발생하는 오류 처리
     st.error("Streamlit Secrets에 'GOOGLE_API_KEY'가 설정되지 않았습니다. 앱 설정에서 Secrets를 확인해주세요.")
     st.stop()
except Exception as e:
    st.error(f"API 키 설정 중 예상치 못한 오류 발생: {e}")
    st.stop()


# 초등학생 눈높이에 맞는 답변을 위한 시스템 명령어 설정 (그림/사진에 대한 조언 초점 + 개선점 포함)
system_instruction_text = """
당신은 초등학생 친구들을 위한 친절한 그림 선생님 도우미예요!
친구들이 올린 그림이나 사진을 보고, 재미있거나 멋진 점을 이야기해주세요.

**먼저, 그림의 좋은 점을 충분히 칭찬해주세요.** 색깔을 예쁘게 썼다거나, 재미있는 상상을 했다거나, 열심히 그린 부분 등 칭찬할 점을 구체적으로 찾아 이야기해주세요.

**친구의 그림/사진을 잘 살펴봐 주세요.** 그림을 더 풍성하고 재미있게 만들 수 있는 아이디어가 떠오른다면 (예: 비어 있는 배경, 부족한 색칠, 이야기 추가 등), **그때** 아주 부드럽고 조심스럽게 개선 아이디어를 이야기해주세요.

**하지만 만약 그림이 이미 멋지게 완성되어 있거나, 추가 조언이 어울리지 않는 경우라면, 개선 아이디어는 생략하고 칭찬으로만 마무리해도 괜찮습니다.**

**절대 '틀렸다', '이상하다', '나쁘다' 같은 부정적인 말은 사용하지 않아요.** 항상 '이렇게 해보면 더 멋져질 거야!' 와 같이 긍정적으로 이야기해주세요.

어려운 단어는 쓰지 말고, 초등학생 친구들이 기분 좋게 이해하고 다음에 그림 그릴 때 도움이 될 수 있도록 상냥하고 따뜻하게 말해주세요.
"""

# 사용할 모델 지정 및 시스템 명령어 적용
model = genai.GenerativeModel(
    'gemini-1.5-flash-latest', # 비전(이미지) 처리가 가능한 모델 사용
    system_instruction=system_instruction_text
)

st.title("곡수초 O학년 그림 이야기 챗봇~")

# 채팅 기록 초기화 (표시용 - 텍스트와 이미지를 함께 저장)
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "안녕! 그림이나 사진을 올리거나 카메라로 찍어서 아래 버튼을 누르면 선생님이 멋진 점과 더 재미있게 그릴 아이디어를 이야기해줄게!", "type": "text"}]

# 채팅 메시지 표시
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        if message["type"] == "text":
            st.markdown(message["content"])
        elif message["type"] == "image":
            # Streamlit의 이미지 표시 기능 사용
            # 이미지 바이트 데이터를 st.image로 바로 표시
            st.image(message["content"], caption="친구 그림/사진", use_container_width=True)

# --- 모드 선택을 위한 상태 변수 초기화 ---
# True이면 카메라 모드, False이면 파일 업로드 모드
if 'use_camera' not in st.session_state:
    st.session_state['use_camera'] = False

# --- 모드 선택 버튼 ---
# 현재 모드에 따라 버튼 텍스트를 변경하고, 클릭 시 모드 상태를 토글
if st.button("📸 카메라로 찍기" if not st.session_state['use_camera'] else "📁 파일로 올리기"):
    st.session_state['use_camera'] = not st.session_state['use_camera']
    st.rerun() # 모드 변경 후 UI 갱신을 위해 재실행

# 이미지 업로드 또는 카메라 촬영을 위한 폼
# 선택된 모드에 따라 다른 입력 위젯이 폼 안에 표시됩니다.
with st.form(key="image_upload_form") as form:
    st.write(f"💡 현재 모드: {'카메라 촬영' if st.session_state['use_camera'] else '파일 업로드'}")

    image_to_process = None # 처리할 이미지 데이터를 담을 변수
    image_mime_type = None # 이미지 마임 타입을 담을 변수
    input_widget_key = "current_image_input" # 현재 활성화된 입력 위젯의 고유 키

    # --- 선택된 모드에 따라 입력 위젯 조건부 표시 ---
    if st.session_state['use_camera']:
        # 카메라 모드일 때 카메라 입력 위젯 표시
        camera_image = st.camera_input("카메라로 그림/사진 찍기", key=input_widget_key)

        # --- 추가된 부분: 카메라 버튼 설명 ---
        if st.session_state['use_camera']:
             st.info("카메라가 켜지면 보이는 화면에서 [Take Photo] 버튼을 눌러 사진을 찍고, [Clear photo] 버튼은 찍은 사진을 다시 지울 때 사용해요.")
        # ------------------------------------

        if camera_image is not None:
            image_to_process = camera_image.getvalue()
            image_mime_type = camera_image.type


    else:
        # 파일 업로드 모드일 때 파일 업로더 위젯 표시
        uploaded_file = st.file_uploader("컴퓨터에서 그림/사진 올리기", type=["png", "jpg", "jpeg", "gif"], key=input_widget_key)
        if uploaded_file is not None:
            image_to_process = uploaded_file.getvalue()
            image_mime_type = uploaded_file.type


    # 제출 버튼
    submit_button = st.form_submit_button("선생님께 그림/사진 보여주기!")

    # '보여주기' 버튼이 눌렸을 때 처리 시작
    if submit_button:
        # 이 시점에서 image_to_process와 image_mime_type 변수에 이미 값이 할당되어 있습니다 (입력 위젯에 파일/사진이 있다면).

        if image_to_process is not None and image_mime_type is not None:
            # 사용자의 입력 (이미지)을 채팅 기록에 추가 (표시용)
            st.session_state["messages"].append({"role": "user", "content": image_to_process, "type": "image"})

            # AI에게 전달할 이미지 및 텍스트 내용 구성
            content = [
                {"mime_type": image_mime_type, "data": image_to_process},
                "이 그림/사진을 보고 초등학생 친구에게 이야기하듯이 설명해줘. 먼저 그림의 멋진 점을 충분히 칭찬해주고, 만약 필요하다면 더 멋져질 수 있는 부분을 부드럽게 조언해줘. 네가 초등학생 친구에게 말하듯이 친절하고 상냥하게 이야기해야 해."
            ]

            # AI 응답 생성 및 표시
            with st.chat_message("assistant"):
                # 답변을 생성하는 동안 로딩 스피너 표시
                with st.spinner("친구 그림/사진을 살펴보고 있어요..."):
                    try:
                        # generate_content를 사용하여 이미지와 텍스트를 함께 전달하고 응답 받기
                        response = model.generate_content(content)

                        # 응답 텍스트 가져오기
                        assistant_response = response.text

                        # 챗봇 응답 저장 (표시용)
                        st.session_state["messages"].append({"role": "assistant", "content": assistant_response, "type": "text"})

                        # 챗봇 응답 표시
                        st.markdown(assistant_response)

                        # --- Form 초기화 ---
                        # 처리가 완료되면 form의 입력 필드를 초기 상태로 되돌립니다.
                        # form 객체가 None이 아닌지 확인 후 reset 호출
                        if form is not None: # 'NoneType' 오류 방지 확인
                           form.reset()
                           # 폼 리셋 후, 현재 모드를 다시 파일 업로드 모드로 변경하여 초기 상태로 돌아가게 할 수도 있습니다.
                           # st.session_state['use_camera'] = False # 필요하다면 이 라인 추가
                        # -------------------

                    except Exception as e:
                        # 오류 발생 시 처리
                        error_message = f"앗, 그림/사진을 살펴보다가 문제가 생겼어요. 다시 시도해주거나 다른 그림/사진을 올려줄래? (오류: {e})"
                        st.session_state["messages"].append({"role": "assistant", "content": error_message, "type": "text"})
                        st.markdown(error_message)

            # AI 처리 및 응답 표시 후 UI 업데이트를 위해 앱 다시 실행
            st.rerun() # 처리 완료 후 UI 갱신 및 form 초기화 적용

        else:
             # 제출 버튼을 눌렀지만, 선택된 모드의 입력 위젯에 이미지가 없는 경우
             if st.session_state['use_camera']:
                 st.warning("카메라로 사진을 찍은 후 버튼을 눌러야 해요!")
             else:
                 st.warning("그림/사진 파일을 올린 후 버튼을 눌러야 해요!")
