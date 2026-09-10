---
title: '긴 컨텍스트는 기억이 아니다. Memory Management, 세션이 끝나도 남을 것을 정하는 법'
date: '2026-09-10'
tags:
  - AI
series: Agentic Design Patterns
emoji: "\U0001F9E0"
---
> Antonio Gulli, _Agentic Design Patterns_(Google / Springer)의 8장 "Memory Management"를 정리합니다.
> [지난 편](https://dhbang.co.kr/posts/study/agentic-design-patterns/multi-agent-collaboration/) Multi-Agent Collaboration이 "하나의 목표를 여러 에이전트에 나눠 맡기는 법"이었다면, 이번 편은 "세션이 끝나도 남을 것을 정하는 법"입니다.

---


## 어제 다 정해 놓은 것을 오늘 처음부터 다시 설명합니다


어제 에이전트와 한 시간을 들여 프로젝트 규칙을 정해 본 적이 있으신가요. 디렉터리 구조를 설명하고, 쓰지 말아야 할 라이브러리를 알려주고, 커밋 메시지 형식까지 합의했습니다. 대화가 잘 끝났습니다.


오늘 새 세션을 엽니다. 에이전트는 처음 만난 것처럼 굽니다. 어제 쓰지 말라고 한 라이브러리를 제안하고, 커밋 메시지를 다른 형식으로 씁니다.


이 지점에서 대개 컨텍스트 윈도우를 의심합니다. 한 번에 100만 토큰을 넣을 수 있다는 모델도 있는데 왜 어제 것을 못 가져오는가. 그러나 이것은 용량 문제가 아닙니다. 8장은 그 착각을 첫 문단에서 정리합니다.


7장은 에이전트를 여럿으로 나누고 그 사이에 경계를 만들었습니다. 마지막에 책은 다음 질문을 예고했습니다. 이들이 외부 환경과 어떻게 상호작용하는가. 8장이 다루는 외부 환경의 첫 번째가 **저장소**입니다. 세션 밖에 있고, 대화가 끝나도 남아 있고, 에이전트가 질의해서 꺼내 와야 하는 곳입니다.


그런데 저장은 쉬운 쪽입니다. 데이터베이스에 넣으면 되니까요. 어려운 쪽은 반대인데, 쌓인 것이 수천 건이어도 컨텍스트 윈도우에 넣을 수 있는 것은 몇 건뿐입니다. 이 글을 관통하는 질문은 그래서 하나입니다.

> 쌓아둔 것 중에서 무엇이 돌아오는가?

---


## 기억은 하나가 아니라 수명이 다른 둘입니다


에이전트의 기억은 단일한 저장 공간이 아닙니다. 책은 처음부터 두 가지로 갈라 놓습니다. 사람의 기억에 견주는 방식입니다.


**단기 기억(Short-Term Memory)은 맥락 기억(Contextual Memory)입니다.** 지금 처리 중이거나 방금 접근한 정보가 여기 있습니다. LLM을 쓰는 에이전트라면 이것은 곧 컨텍스트 윈도우입니다. 최근 메시지, 에이전트의 답변, 도구 실행 결과, 현재 상호작용에서 나온 에이전트의 리플렉션이 담깁니다.


**장기 기억(Long-Term Memory)은 지속 기억(Persistent Memory)입니다.** 여러 상호작용과 작업, 긴 기간에 걸쳐 유지해야 하는 정보의 저장고입니다. 에이전트의 즉시 처리 환경 **바깥**에 둡니다. 데이터베이스, 지식 그래프, 벡터 데이터베이스입니다.


벡터 데이터베이스를 쓰면 정보가 수치 벡터로 변환되어 저장됩니다. 그래서 조회 방식이 달라집니다. 정확한 키워드 일치가 아니라 **의미적 유사도**로 꺼냅니다. 의미 검색(semantic search)입니다.


둘을 가르는 기준은 용량이 아니라 수명입니다. 단기 기억은 세션과 함께 사라지고, 장기 기억은 세션과 무관하게 남습니다.


---


## 긴 컨텍스트는 단기 기억을 늘릴 뿐 장기 기억이 되지 않습니다


여기가 도입에서 말한 착각이 깨지는 자리입니다. 책은 한 문장으로 못 박습니다.

> '롱 컨텍스트' 윈도우를 갖춘 모델의 등장은 단지 이 단기 기억의 크기를 확장한 것일 뿐이며, 단일 상호작용 안에서 더 많은 정보를 담아둘 수 있게 해줍니다.

컨텍스트 윈도우를 100만 토큰으로 늘리는 것은 장기 기억을 얻는 일이 아닙니다. **단기 기억을 크게 만드는 일**입니다. 책은 곧바로 두 가지 대가를 붙입니다. 첫째, 그 컨텍스트는 여전히 일시적이며 세션이 끝나면 사라집니다. 둘째, 매번 전부 처리하는 것은 비싸고 비효율적입니다.


그래서 결론이 이렇게 나옵니다.

> 따라서 에이전트가 진정한 지속성을 확보하고, 과거 상호작용에서 정보를 회상하고, 지속적인 지식 베이스를 구축하려면 별개의 기억 타입이 필요합니다.

용량을 늘려서 해결되는 문제가 아니라 저장 위치를 옮겨야 하는 문제라는 뜻입니다.


그리고 장기 기억이 어떻게 쓰이는지를 보면, 이 두 기억이 대등한 관계가 아니라는 것이 드러납니다.

> 에이전트가 장기 기억에서 정보를 필요로 할 때, 외부 저장소에 질의하고, 관련 데이터를 검색해, 즉시 사용할 수 있도록 **단기 컨텍스트에 통합**합니다.

장기 기억은 에이전트가 직접 읽는 곳이 아닙니다. 꺼내서 단기 컨텍스트에 **집어넣어야** 모델에 닿습니다. 아무리 많이 쌓아도 통로는 컨텍스트 윈도우 하나이고, 그 통로의 폭은 유한합니다.


![Fig.1 — 메모리 관리 설계 패턴. Agent와 Memory 사이의 화살표가 양방향인 것이 이 패턴의 전부다. 쓰기와 읽기가 별개의 동작이다 (출처: Antonio Gulli, Agentic Design Patterns)](https://dhbang.co.kr/images/agentic-design-patterns/adp-ch8-fig1.png)


도식이 단순한 데는 이유가 있습니다. 이 패턴에서 새로 생기는 것이 상자 하나와 화살표 두 개뿐이기 때문입니다. Agent에서 Memory로 가는 화살표가 쓰기이고, 반대로 오는 화살표가 읽기입니다. 남은 장의 대부분은 이 두 화살표를 프레임워크가 각각 어떤 이름으로 부르는지에 대한 이야기입니다.


---


## ADK는 기억을 셋으로 쪼개 각각에 서비스를 붙였습니다


Google ADK는 앞의 두 갈래를 그대로 쓰지 않습니다. 세 개의 핵심 개념으로 나눕니다.

- **Session.** 개별 채팅 스레드입니다. 그 상호작용의 메시지와 행동을 Event로 기록하고, 해당 대화에 관련된 임시 데이터(State)도 저장합니다.
- **State (session.state).** Session 안에 저장되는 데이터입니다. 현재 활성 채팅 스레드에만 관련된 정보를 담습니다.
- **Memory.** 여러 과거 대화나 외부 소스에서 온 정보의 검색 가능한 저장고입니다. 즉시 대화를 넘어선 데이터 조회의 자원입니다.

그리고 각각에 서비스를 붙입니다. **SessionService**가 채팅 스레드(Session 객체)의 시작과 기록과 종료를 관리하고, **MemoryService**가 장기 지식의 저장과 조회를 감독합니다.


왜 둘로 갈랐는지는 저장 방식 선택지를 보면 드러납니다. 두 서비스 모두 구현체가 여러 개이고, 테스트용 인메모리 옵션은 재시작하면 데이터가 사라집니다.


```python
# Example: Using InMemorySessionService
# This is suitable for local development and testing where data
# persistence across application restarts is not required.
from google.adk.sessions import InMemorySessionService
session_service = InMemorySessionService()
```


직접 관리하는 데이터베이스에 안정적으로 저장하려면 `DatabaseSessionService`입니다.


```python
# Example: Using DatabaseSessionService
# This is suitable for production or development requiring persistent storage.
# You need to configure a database URL (e.g., for SQLite, PostgreSQL, etc.).
# Requires: pip install google-adk[sqlalchemy] and a database driver (e.g., psycopg2 for PostgreSQL)
from google.adk.sessions import DatabaseSessionService
# Example using a local SQLite file:
db_url = "sqlite:///./my_agent_data.db"
session_service = DatabaseSessionService(db_url=db_url)
```


GCP에서 확장 가능한 프로덕션을 노린다면 `VertexAiSessionService`가 Vertex AI 인프라를 씁니다. 여기서 눈에 띄는 것은 `app_name` 자리에 들어가는 값입니다.


```python
# Example: Using VertexAiSessionService
# This is suitable for scalable production on Google Cloud Platform, leveraging
# Vertex AI infrastructure for session management.
# Requires: pip install google-adk[vertexai] and GCP setup/authentication
from google.adk.sessions import VertexAiSessionService

PROJECT_ID = "your-gcp-project-id" # Replace with your GCP project ID
LOCATION = "us-central1" # Replace with your desired GCP location
# The app_name used with this service should correspond to the Reasoning Engine ID or name
REASONING_ENGINE_APP_NAME = "projects/your-gcp-project-id/locations/us-central1/reasoningEngines/your-engine-id" # Replace with your Reasoning Engine resource name

session_service = VertexAiSessionService(project=PROJECT_ID, location=LOCATION)
```


일반적인 애플리케이션 이름이 아니라 Reasoning Engine 리소스 이름입니다. 세션이 관리형 런타임에 묶여 있다는 뜻입니다.


책이 SessionService 선택을 강조하는 이유가 여기 있습니다. 이 선택이 에이전트의 상호작용 이력과 임시 데이터를 어디에 저장할지, 그리고 그것이 얼마나 지속될지를 결정합니다. 코드 한 줄을 바꾸는 것으로 보이지만, 실제로 바뀌는 것은 기억의 수명입니다.


---


## 세션은 대화의 기록이 아니라 이벤트의 로그입니다


Session을 대화 내용이 담긴 그릇으로 이해하면 뒤에 나오는 규칙들이 이해되지 않습니다. Session은 **시간순으로 쌓인 Event 객체의 로그**이고, 상태는 그 로그에 딸린 부산물입니다.


ADK의 Session 객체에는 식별자(id, app_name, user_id), Event 객체의 시간순 기록, 세션별 임시 데이터인 state, 마지막 갱신 시각(last_update_time)이 들어 있습니다. 개발자는 보통 Session을 직접 다루지 않고 SessionService를 통해 간접적으로 다룹니다.


메시지 하나가 오갈 때 무엇이 일어나는지를 책은 순환 과정으로 적어 둡니다.

1. 메시지가 도착합니다.
2. Runner가 SessionService로 Session을 가져오거나 새로 만듭니다.
3. 에이전트가 Session의 컨텍스트(state와 과거 상호작용)로 메시지를 처리합니다.
4. 에이전트가 응답을 생성하고 상태를 갱신할 수 있습니다.
5. Runner가 이것을 Event로 감쌉니다.
6. `session_service.append_event`가 새 이벤트를 기록하고 저장소의 상태를 갱신합니다.
7. Session이 다음 메시지를 기다립니다.

상호작용이 끝나면 `delete_session`으로 세션을 종료하는 것이 이상적입니다.


핵심은 6번입니다. **상태 갱신이 이벤트 기록과 같은 동작 안에 묶여 있습니다.** 상태가 바뀌는 유일한 정상 경로가 `append_event`라는 뜻이고, 이것이 다음 절의 규칙이 나오는 근거입니다.


---


## 상태를 직접 고치지 말라는 규칙은 기록을 남기라는 요구입니다


`session.state`는 딕셔너리입니다. 파이썬 딕셔너리를 받으면 직접 대입하고 싶어집니다. 세션을 가져와서 `session.state["x"] = 1`을 쓰면 될 것 같습니다. 책은 이것을 강력히 권장하지 않는다(strongly discouraged)고 씁니다.


버그가 아니라 설계입니다. 직접 수정이 표준 이벤트 처리 메커니즘을 우회하기 때문인데, 책은 그 결과를 네 가지로 나열합니다.

- 세션의 이벤트 이력에 기록되지 않습니다.
- 선택한 SessionService가 영속화하지 않을 수 있습니다.
- 동시성 문제로 이어질 수 있습니다.
- 타임스탬프 같은 필수 메타데이터가 갱신되지 않습니다.

앞 절의 순환 과정에서 상태 갱신이 `append_event` 안에 묶여 있던 이유가 이것입니다. 이벤트를 건너뛰고 상태를 바꾸면 그 변경은 이력에 없는 변경이 됩니다. 책은 `session.state`를 **기존 데이터를 읽는 용도로 주로 쓰라**고 정리합니다.


그러면 쓰기는 어떻게 하는가. 두 가지 방법이 있습니다.


**첫째, 저장할 것이 최종 텍스트 응답 하나뿐이면 키 이름만 정하면 됩니다.** `LlmAgent`를 만들 때 `output_key`에 그 이름을 넘깁니다.


```python
# Import necessary classes from the Google Agent Developer Kit (ADK)
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService, Session
from google.adk.runners import Runner
from google.genai.types import Content, Part

# Define an LlmAgent with an output_key.
greeting_agent = LlmAgent(
    name="Greeter",
    model="gemini-2.0-flash",
    instruction="Generate a short, friendly greeting.",
    output_key="last_greeting"
)

# --- Setup Runner and Session ---
app_name, user_id, session_id = "state_app", "user1", "session1"
session_service = InMemorySessionService()
runner = Runner(
    agent=greeting_agent,
    app_name=app_name,
    session_service=session_service
)
session = session_service.create_session(
    app_name=app_name,
    user_id=user_id,
    session_id=session_id
)

print(f"Initial state: {session.state}")

# --- Run the Agent ---
user_message = Content(parts=[Part(text="Hello")])
print("\n--- Running the agent ---")
for event in runner.run(
    user_id=user_id,
    session_id=session_id,
    new_message=user_message
):
    if event.is_final_response():
      print("Agent responded.")

# --- Check Updated State ---
# Correctly check the state *after* the runner has finished processing all events.
updated_session = session_service.get_session(app_name, user_id, session_id)
print(f"\nState after agent run: {updated_session.state}")
```


`output_key="last_greeting"` 한 줄이 전부입니다. 나머지는 Runner가 합니다. 책의 설명으로는 Runner가 `output_key`를 보고 `append_event`를 호출할 때 `state_delta`가 담긴 액션을 자동으로 만듭니다.


주석의 강조에 눈여겨볼 것이 있습니다. `# Correctly check the state *after* the runner has finished processing all events.` 상태를 읽는 시점이 이벤트 처리가 끝난 뒤여야 한다는 경고입니다. 그리고 확인할 때 손에 든 `session` 객체가 아니라 `get_session`으로 다시 가져옵니다. 상태의 원본이 객체가 아니라 서비스 쪽에 있다는 사실이 코드에 드러난 자리입니다.


**둘째, 그 밖의 경우는 상태 변경을 직접 서야 합니다.** `EventActions.state_delta`입니다. 여러 키를 한 번에 바꾸거나, 텍스트가 아닌 것을 저장하거나, `user:`나 `app:` 같은 특정 스코프를 노리거나, 에이전트의 최종 텍스트 응답과 무관한 갱신을 할 때입니다. 변경 딕셔너리를 만들어 이벤트의 `EventActions`에 넣습니다.


책이 예제로 내놓는 것은 이 갱신을 도구 안에 넣는 방식입니다.


```python
import time
from google.adk.tools.tool_context import ToolContext
from google.adk.sessions import InMemorySessionService

# --- Define the Recommended Tool-Based Approach ---
def log_user_login(tool_context: ToolContext) -> dict:
    """
    Updates the session state upon a user login event.
    This tool encapsulates all state changes related to a user login.
    Args:
        tool_context: Automatically provided by ADK, gives access to session state.
    Returns:
        A dictionary confirming the action was successful.
    """
    # Access the state directly through the provided context.
    state = tool_context.state

    # Get current values or defaults, then update the state.
    # This is much cleaner and co-locates the logic.
    login_count = state.get("user:login_count", 0) + 1
    state["user:login_count"] = login_count
    state["task_status"] = "active"
    state["user:last_login_ts"] = time.time()
    state["temp:validation_needed"] = True

    print("State updated from within the `log_user_login` tool.")

    return {
        "status": "success",
        "message": f"User login tracked. Total logins: {login_count}."
    }
```


도구는 `ToolContext`를 받고 `tool_context.state`로 상태에 접근합니다. 세션을 가져와서 직접 고치는 것과 형태는 비슷해 보이지만, 이 경로는 ADK가 제공한 컨텍스트를 지나므로 변경이 이벤트 처리에 실려 갑니다.


책이 이 방식을 권장 접근이라고 부르는 이유는 주석에 그대로 적혀 있습니다. `# This is much cleaner and co-locates the logic.` 로그인이라는 사건에 관련된 상태 변경 네 개가 한 함수 안에 모여 있습니다. 상태를 바꾸는 코드가 여기저기 흩어지지 않습니다.


상태 설계에 대한 책의 요약은 다섯 개입니다. 단순하게 유지하기, 기본 자료형 쓰기, 키 이름을 명확하게 짓고 접두사를 올바르게 쓰기, 깊은 중첩을 피하기, 그리고 항상 `append_event` 과정으로 갱신하기입니다.


---


## 접두사는 키 이름의 장식이 아니라 수명 선언입니다


앞 코드에서 `user:login_count`와 `task_status`와 `temp:validation_needed`가 나란히 나왔습니다. 콜론 앞의 조각은 명명 관습이 아닙니다. 그 데이터가 어디까지 미치고 얼마나 사는지를 정합니다.


| 접두사     | 범위              | 지속          |
| ------- | --------------- | ----------- |
| 없음      | 해당 세션 전용        | 세션과 함께      |
| `user:` | 한 사용자 ID의 모든 세션 | 세션을 넘어      |
| `app:`  | 애플리케이션의 모든 사용자  | 세션과 사용자를 넘어 |
| `temp:` | 현재 처리 턴에만 유효    | 영속화되지 않음    |


`user:login_count`가 세션을 넘어 누적되는 이유가 접두사입니다. 접두사가 없다면 세션마다 1로 다시 시작합니다. `temp:validation_needed`는 반대입니다. 이번 턴이 끝나면 저장되지 않고 사라집니다.


앞 절에서 본 두 기억의 구분이 여기서 키 문자열 하나로 접혀 들어옵니다. 접두사 없는 키는 단기 기억이고, `user:`와 `app:`는 장기 기억이며, `temp:`는 단기 기억보다 더 짧습니다. 에이전트가 접근하는 방식은 어느 쪽이든 `session.state` 딕셔너리 하나입니다. 데이터를 가져오고 병합하고 영속화하는 일은 SessionService가 처리합니다.


편리하지만 위험이 하나 있습니다. 읽는 코드에서는 셋이 구분되지 않습니다. `state.get("temp:x")`와 `state.get("user:x")`는 같은 모양이고, 어느 쪽이 다음 세션에 남는지는 문자열을 읽어야 알 수 있습니다.


---


## MemoryService가 정의하는 것은 넣기와 찾기 둘뿐입니다


Session과 State가 단일 채팅 세션의 단기 기억이라면, MemoryService가 관리하는 장기 지식은 지속되고 검색 가능한 저장고입니다. 여러 과거 상호작용이나 외부 소스에서 온 정보가 들어갑니다.


인터페이스는 `BaseMemoryService`이고, 주요 기능은 두 개입니다.

- **정보 추가.** 세션에서 내용을 추출해 `add_session_to_memory`로 저장합니다.
- **정보 조회.** 에이전트가 저장고에 질의해 `search_memory`로 관련 데이터를 받습니다.

앞의 Fig.1로 돌아가면 화살표 두 개가 이 두 메서드입니다. 장기 기억의 인터페이스는 이 이상 복잡해지지 않습니다.


구현체는 역시 테스트용과 프로덕션용으로 갈립니다. `InMemoryMemoryService`는 앱이 멈추면 내용이 사라집니다.


```python
# Example: Using InMemoryMemoryService
# This is suitable for local development and testing where data
# persistence across application restarts is not required.
# Memory content is lost when the app stops.
from google.adk.memory import InMemoryMemoryService
memory_service = InMemoryMemoryService()
```


프로덕션에서는 `VertexAiRagMemoryService`를 씁니다. Google Cloud의 RAG(Retrieval Augmented Generation) 서비스를 써서 확장 가능하고 지속적인 의미 검색을 제공합니다.


```python
# Example: Using VertexAiRagMemoryService
# This is suitable for scalable production on GCP, leveraging
# Vertex AI RAG (Retrieval Augmented Generation) for persistent,
# searchable memory.
# Requires: pip install google-adk[vertexai], GCP
# setup/authentication, and a Vertex AI RAG Corpus.
from google.adk.memory import VertexAiRagMemoryService

# The resource name of your Vertex AI RAG Corpus
RAG_CORPUS_RESOURCE_NAME = "projects/your-gcp-project-id/locations/us-central1/ragCorpora/your-corpus-id" # Replace with your Corpus resource name

# Optional configuration for retrieval behavior
SIMILARITY_TOP_K = 5 # Number of top results to retrieve
VECTOR_DISTANCE_THRESHOLD = 0.7 # Threshold for vector similarity

memory_service = VertexAiRagMemoryService(
    rag_corpus=RAG_CORPUS_RESOURCE_NAME,
    similarity_top_k=SIMILARITY_TOP_K,
    vector_distance_threshold=VECTOR_DISTANCE_THRESHOLD
)
```


책이 선택적 설정(Optional configuration)이라고 적은 두 줄을 기억해 두시기 바랍니다. `similarity_top_k`와 `vector_distance_threshold`입니다. 이 글의 관통 질문에 답하는 자리는 여기입니다. 마지막 절에서 다시 봅니다.


---


## LangChain은 같은 문제를 프롬프트 조립으로 풉니다


LangChain과 LangGraph의 구분도 두 갈래입니다. 다만 단기 기억을 설명하는 표현이 다릅니다.


**단기 기억은 스레드 범위(thread-scoped)입니다.** 단일 세션 또는 스레드 안의 진행 중인 대화를 추적합니다. 즉시 컨텍스트를 제공하지만, 전체 이력은 LLM의 컨텍스트 윈도우를 압박해 오류나 성능 저하로 이어질 수 있습니다. LangGraph는 단기 기억을 에이전트 상태의 일부로 관리하고, 이를 체크포인터(checkpointer)로 영속화해 스레드를 언제든 재개할 수 있게 합니다.


**장기 기억은 사용자별 또는 애플리케이션 수준 데이터를 세션을 넘어 저장합니다.** 대화 스레드 사이에 공유되며, 커스텀 "네임스페이스"에 저장되어 어느 스레드에서든 언제든 회상할 수 있습니다.


단기 기억을 다루는 도구는 수동과 자동 두 층입니다. 격식 있는 체인 밖에서 직접 통제하려면 `ChatMessageHistory`입니다.


```python
from langchain.memory import ChatMessageHistory

# Initialize the history object
history = ChatMessageHistory()

# Add user and AI messages
history.add_user_message("I'm heading to New York next week.")
history.add_ai_message("Great! It's a fantastic city.")

# Access the list of messages
print(history.messages)
```


체인에 기억을 통합하려면 `ConversationBufferMemory`입니다. 파라미터 두 개가 동작을 정합니다.

- `memory_key`. 프롬프트에서 채팅 이력을 담을 변수 이름입니다. 기본값은 `"history"`입니다.
- `return_messages`. 이력의 형식을 정하는 불리언입니다. `False`(기본값)면 포맷된 문자열 하나를 반환하고 표준 LLM에 적합합니다. `True`면 메시지 객체의 리스트를 반환하며, 이것이 챗 모델에 권장되는 형식입니다.

이 두 파라미터가 왜 중요한지는 체인에 넣어 보면 드러납니다.


```python
from langchain_openai import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory

# 1. Define LLM and Prompt
llm = OpenAI(temperature=0)
template = """You are a helpful travel agent.

Previous conversation:
{history}

New question: {question}
Response:"""
prompt = PromptTemplate.from_template(template)

# 2. Configure Memory
# The memory_key "history" matches the variable in the prompt
memory = ConversationBufferMemory(memory_key="history")

# 3. Build the Chain
conversation = LLMChain(llm=llm, prompt=prompt, memory=memory)

# 4. Run the Conversation
response = conversation.predict(question="I want to book a flight.")
print(response)
response = conversation.predict(question="My name is Sam, by the way.")
print(response)
response = conversation.predict(question="What was my name again?")
print(response)
```


프롬프트 템플릿 안의 `{history}`와 `memory_key="history"`가 같은 문자열이라는 점이 이 예제의 전부입니다. 주석도 그것을 지적합니다. `# The memory_key "history" matches the variable in the prompt`


여기서 기억의 정체가 드러납니다. 세 번째 질문 "What was my name again?"에 답할 수 있는 이유는 모델이 이름을 기억하기 때문이 아닙니다. 앞선 두 번의 교환이 문자열로 조립되어 `{history}` 자리에 다시 들어갔기 때문입니다. **기억은 모델 안에 생기지 않고 프롬프트 안에 매번 재조립됩니다.** 앞에서 본 "장기 기억은 단기 컨텍스트에 통합된다"는 문장의 가장 단순한 구현입니다.


챗 모델에서는 `return_messages=True`로 구조화된 메시지 리스트를 쓰는 것이 권장됩니다. 프롬프트 쪽도 `MessagesPlaceholder`로 바뀝니다.


```python
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

# 1. Define Chat Model and Prompt
llm = ChatOpenAI()
prompt = ChatPromptTemplate(
    messages=[
        SystemMessagePromptTemplate.from_template("You are a friendly assistant."),
        MessagesPlaceholder(variable_name="chat_history"),
        HumanMessagePromptTemplate.from_template("{question}")
    ]
)

# 2. Configure Memory
# return_messages=True is essential for chat models
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# 3. Build the Chain
conversation = LLMChain(llm=llm, prompt=prompt, memory=memory)

# 4. Run the Conversation
response = conversation.predict(question="Hi, I'm Jane.")
print(response)
response = conversation.predict(question="Do you remember my name?")
print(response)
```


문자열 하나였던 자리가 메시지 리스트가 꽂히는 자리로 바뀌었습니다. 기억의 내용은 같고 담는 형식만 달라집니다.


---


## LangGraph는 장기 기억을 사람의 기억 분류에 맞춰 셋으로 갈랐습니다


장기 기억을 한 덩어리로 두면 무엇을 어떻게 저장할지 정할 수 없습니다. 책은 사람의 기억에 대응하는 세 가지로 나눕니다.


**의미 기억(Semantic Memory)은 사실을 기억합니다.** 사용자 선호나 도메인 지식 같은 구체적 사실과 개념을 유지합니다. 에이전트의 응답에 근거를 대는 데 쓰입니다. 관리 방식은 두 가지입니다. 지속적으로 갱신되는 사용자 "프로필"(JSON 문서) 하나로 두거나, 개별 사실 문서들의 "컬렉션"으로 두거나.


**일화 기억(Episodic Memory)은 경험을 기억합니다.** 과거 사건이나 행동을 회상합니다. AI 에이전트에서는 작업을 어떻게 완수했는지를 기억하는 데 자주 쓰입니다. 실제 구현은 대개 퓨샷 예시 프롬프팅(few-shot example prompting)입니다. 과거의 성공한 상호작용 시퀀스를 예시로 넣어 배우게 합니다.


**절차 기억(Procedural Memory)은 규칙을 기억합니다.** 작업을 수행하는 방법에 대한 기억이고, 에이전트의 핵심 지시와 행동입니다. 보통 시스템 프롬프트에 담깁니다.


셋 중 절차 기억이 특이합니다. 앞의 둘은 에이전트가 참조하는 데이터인데, 절차 기억은 **에이전트를 규정하는 지시문 자체**입니다. 그리고 책은 에이전트가 자기 프롬프트를 수정해 적응하고 개선하는 것이 흔한 일이라고 씁니다. 효과적인 기법의 이름은 "Reflection"입니다. 현재 지시와 최근 상호작용을 함께 주고 자기 지시를 다듬으라고 요청합니다.


4장에서 본 리플렉션이 여기서 다시 나옵니다. 4장에서는 **출력**을 다시 썼습니다. 여기서는 **지시문**을 다시 씁니다. 그리고 다시 쓴 결과가 저장소에 남아 다음 실행에 쓰입니다.


```python
# Node that updates the agent's instructions
def update_instructions(state: State, store: BaseStore):
   namespace = ("instructions",)
   # Get the current instructions from the store
   current_instructions = store.search(namespace)[0]

   # Create a prompt to ask the LLM to reflect on the conversation
   # and generate new, improved instructions
   prompt = prompt_template.format(
       instructions=current_instructions.value["instructions"],
       conversation=state["messages"]
   )

   # Get the new instructions from the LLM
   output = llm.invoke(prompt)
   new_instructions = output['new_instructions']

   # Save the updated instructions back to the store
   store.put(("agent_instructions",), "agent_a", {"instructions": new_instructions})

# Node that uses the instructions to generate a response
def call_model(state: State, store: BaseStore):
   namespace = ("agent_instructions", )
   # Retrieve the latest instructions
   instructions = store.get(namespace, key="agent_a")[0]

   # Use the retrieved instructions to format the prompt
   prompt = prompt_template.format(instructions=instructions.value["instructions"])
   # ... application logic continues
```


`update_instructions`가 쓰고 `call_model`이 읽습니다. 지시문이 코드에 하드코딩되어 있지 않고 저장소를 거칩니다. 프롬프트가 배포 산출물이 아니라 런타임 데이터가 되는 지점입니다.


저장 구조는 파일 시스템에 가깝습니다. LangGraph는 장기 기억을 저장소의 JSON 문서로 두고, 각 기억을 커스텀 네임스페이스(폴더 같은 것)와 구별되는 키(파일명 같은 것) 아래에 조직합니다.


```python
from langgraph.store.memory import InMemoryStore

# A placeholder for a real embedding function
def embed(texts: list[str]) -> list[list[float]]:
    # In a real application, use a proper embedding model
    return [[1.0, 2.0] for _ in texts]

# Initialize an in-memory store. For production, use a database-backed store.
store = InMemoryStore(index={"embed": embed, "dims": 2})

# Define a namespace for a specific user and application context
user_id = "my-user"
application_context = "chitchat"
namespace = (user_id, application_context)

# 1. Put a memory into the store
store.put(
    namespace,
    "a-memory",  # The key for this memory
    {
        "rules": [
            "User likes short, direct language",
            "User only speaks English & python",
        ],
        "my-key": "my-value",
    },
)

# 2. Get the memory by its namespace and key
item = store.get(namespace, "a-memory")
print("Retrieved Item:", item)

# 3. Search for memories within the namespace, filtering by content
# and sorting by vector similarity to the query.
items = store.search(
    namespace,
    filter={"my-key": "my-value"},
    query="language preferences"
)
print("Search Results:", items)
```


세 동작이 `put`과 `get`과 `search`로 나뉘어 있습니다. `get`은 네임스페이스와 키를 알고 정확히 꺼내는 것이고, `search`는 질의문에 대한 벡터 유사도로 정렬해 가져오는 것입니다. 같은 저장고에서 정확 조회와 유사도 조회가 공존합니다.


`namespace = (user_id, application_context)`가 ADK의 `user:` 접두사와 같은 일을 합니다. 이름과 형식은 다르지만 결정하는 것은 같습니다. 이 기억이 누구의 것이고 어디까지 미치는가.


---


## Memory Bank는 무엇을 기억할지 모델에게 맡깁니다


지금까지 본 것은 모두 개발자가 무엇을 저장할지 정하는 방식입니다. `output_key`를 지정하고, `state_delta`를 만들고, `store.put`을 호출합니다. Vertex AI Agent Engine의 관리형 서비스인 Memory Bank는 그 결정을 옮깁니다.


서비스는 Gemini 모델을 써서 대화 이력을 **비동기적으로 분석**해 핵심 사실과 사용자 선호를 추출합니다. 무엇이 기억할 만한 것인지를 모델이 판단합니다.


그 뒤 처리도 자동입니다. 정보는 사용자 ID 같은 정의된 스코프로 조직되어 지속적으로 저장되고, 새 데이터를 통합하고 **모순을 해소하도록** 지능적으로 갱신됩니다. 새 세션을 시작하면 에이전트가 전체 데이터 회상 또는 임베딩을 이용한 유사도 검색으로 관련 기억을 가져옵니다.


```python
from google.adk.memory import VertexAiMemoryBankService

agent_engine_id = agent_engine.api_resource.name.split("/")[-1]

memory_service = VertexAiMemoryBankService(
    project="PROJECT_ID",
    location="LOCATION",
    agent_engine_id=agent_engine_id
)

session = await session_service.get_session(
    app_name=app_name,
    user_id="USER_ID",
    session_id=session.id
)
await memory_service.add_session_to_memory(session)
```


호출은 `add_session_to_memory(session)` 하나입니다. 세션을 통째로 넘기고 무엇을 남길지는 서비스가 정합니다. 각 기억은 고유한 `USER_ID`와 `APP_NAME`으로 태깅되어 이후 조회의 정확성을 보장합니다.


Memory Bank는 Google ADK와 매끄럽게 통합되며, LangGraph나 CrewAI 같은 다른 프레임워크에서도 직접 API 호출로 지원됩니다.


편의의 방향은 분명합니다. 그런데 넘긴 것도 분명합니다. 무엇을 기억하고 무엇을 버릴지, 그리고 모순되는 두 기억 중 어느 쪽을 남길지를 모델이 결정합니다. 다음 절에서 볼 비용의 상당 부분이 이 결정 위에 얹힙니다.


---


## 어디에 쓰는가


책이 드는 활용처는 여섯 가지입니다. 기억이 없으면 에이전트는 기본적인 질의응답을 넘어서지 못한다는 것이 공통 전제입니다.

- **챗봇과 대화형 AI.** 대화 흐름 유지는 단기 기억에 의존합니다. 일관된 응답을 위해 앞선 사용자 입력을 기억해야 합니다. 장기 기억은 사용자 선호, 과거 이슈, 이전 논의를 회상해 개인화된 연속적 상호작용을 가능하게 합니다.
- **작업 지향 에이전트.** 다단계 작업을 관리하려면 이전 단계, 현재 진행 상황, 전체 목표를 추적할 단기 기억이 필요합니다. 즉시 컨텍스트에 없는 사용자 관련 데이터에 접근하려면 장기 기억이 필요합니다.
- **개인화된 경험.** 장기 기억으로 사용자 선호, 과거 행동, 개인 정보를 저장하고 조회해 응답과 제안을 맞춰 갑니다.
- **학습과 개선.** 과거 상호작용에서 배워 성능을 다듬습니다. 성공한 전략, 실수, 새 정보를 장기 기억에 저장해 이후 적응에 씁니다. 강화학습 에이전트가 학습한 전략이나 지식을 이런 방식으로 저장합니다.
- **정보 검색(RAG).** 질의응답 에이전트는 지식 베이스, 즉 자신의 장기 기억에 접근합니다. RAG로 구현되는 경우가 많습니다.
- **자율 시스템.** 로봇이나 자율주행차는 지도, 경로, 물체 위치, 학습된 행동을 위한 기억이 필요합니다. 즉시 주변 환경에는 단기 기억을, 일반적 환경 지식에는 장기 기억을 씁니다.

판단 기준(Rule of thumb)은 이렇게 정리됩니다. 에이전트가 **단일 질문에 답하는 것 이상**을 해야 할 때 씁니다. 대화 전체에 걸쳐 컨텍스트를 유지해야 하거나, 다단계 작업의 진행을 추적해야 하거나, 사용자 선호와 이력을 회상해 상호작용을 개인화해야 하는 경우입니다. 과거의 성공과 실패, 새로 얻은 정보를 바탕으로 학습하거나 적응하기를 기대한다면 구현합니다.


---


## 기억의 비용은 저장이 아니라 선택에서 발생합니다


책에 독립된 한계 섹션은 없습니다. 7장과 같습니다. 각 구현을 설명하면서 약점을 그 자리에 적어 두었습니다. 모아 보면 방향이 하나입니다. **저장은 싸고, 무엇을 돌려보낼지 정하는 일이 비쌉니다.**


**첫째, 통로가 하나뿐입니다.** 장기 기억을 얼마나 쌓든 모델에 닿는 경로는 단기 컨텍스트에 통합되는 것뿐이고, 저장고를 100배로 늘려도 한 번에 넣을 수 있는 양은 그대로입니다. 늘어나는 것은 선택해야 할 후보의 수뿐입니다.


**둘째, 다 넣으면 성능이 떨어집니다.** 책은 LangChain의 단기 기억을 설명하며 전체 이력이 컨텍스트 윈도우를 압박해 오류나 성능 저하로 이어질 수 있다고 적습니다. 그래서 오래된 대화 조각을 요약하거나 핵심을 강조하는 기법이 등장합니다. 그런데 요약은 손실입니다. 무엇을 버릴지 정하는 판단이 다시 필요합니다.


**셋째, 롱 컨텍스트는 매번 값을 냅니다.** 컨텍스트 윈도우를 늘려 해결하려 하면 "매번 전부 처리하는 것은 비싸고 비효율적"이라는 대가가 옵니다. 게다가 세션이 끝나면 사라지므로 지속성 문제는 남아 있습니다. 돈을 쓰고도 원래 문제를 못 풉니다.


**넷째, 의미 검색은 맞는 것을 준다고 보장하지 않습니다.** 벡터 검색은 정확한 키워드 일치가 아니라 유사도로 가져옵니다. 이것이 장점인 이유와 위험한 이유가 같습니다. 질의와 의미가 가까운 것이 오지, 정답이 오는 것이 아닙니다. `search_memory`가 빈손으로 오거나 엉뚱한 것을 물어 오면 에이전트는 그 사실을 모릅니다. 없는 기억과 못 찾은 기억이 구분되지 않습니다.


**다섯째, 무엇이 돌아올지는 숫자 두 개가 정합니다.** `similarity_top_k=5`와 `vector_distance_threshold=0.7`입니다. 책이 선택적 설정이라고 부른 두 줄이 실제로는 에이전트가 무엇을 기억하는지를 결정합니다. 이 값을 정한 근거는 코드에도 본문에도 없습니다.


**여섯째, 접두사와 네임스페이스를 틀리면 조용히 실패합니다.** `temp:`를 붙인 키는 영속화되지 않고, 접두사를 빼먹은 키는 세션이 끝나면 사라집니다. 읽는 쪽 코드는 `state.get(...)`으로 똑같이 생겼습니다. 저장이 실패한 것이 아니라 저장하지 않기로 되어 있던 것이므로 예외도 나지 않습니다. 다음 세션에 데이터가 없는 것으로만 드러납니다.


**일곱째, 상태를 직접 고치는 우회로가 열려 있습니다.** `session.state`는 파이썬 딕셔너리이고 대입이 동작합니다. 강력히 권장하지 않는다고 적혀 있을 뿐 막혀 있지는 않습니다. 우회하면 이벤트 이력에 남지 않고, 영속화되지 않을 수 있고, 동시성 문제가 생길 수 있고, 타임스탬프가 갱신되지 않습니다. 넷 중 어느 것도 그 자리에서 에러를 내지 않습니다.


**여덟째, 모순 해소를 모델에게 맡기면 그 판단이 보이지 않습니다.** Memory Bank는 새 데이터를 통합하고 모순을 해소하도록 지능적으로 갱신합니다. 사용자가 선호를 바꿨을 때 갱신되는 것은 좋은 일입니다. 문제는 잘못 판단했을 때입니다. 추출도 통합도 비동기이므로 무엇이 왜 남았는지 확인할 지점이 개발자 코드 안에 없습니다.


**아홉째, 절차 기억은 에이전트가 자기 지시문을 덮어씁니다.** `update_instructions`는 LLM의 출력을 그대로 `store.put`으로 저장하고, `call_model`이 그것을 읽어 프롬프트를 만듭니다. 개선이 누적되면 좋지만, 나빠지는 방향의 수정도 같은 경로로 누적됩니다. 그리고 다음 실행의 지시문은 저장소에 있으므로 코드를 읽어서는 에이전트가 지금 무슨 지시를 따르는지 알 수 없습니다.


마지막으로 프레임워크가 대신 내주지 않는 비용이 하나 있습니다. 무엇을 기억할 가치가 있는지에 대한 판단입니다. ADK는 저장할 자리와 갱신 규약을 주고, LangGraph는 네임스페이스와 세 가지 기억 유형을 주고, Memory Bank는 추출까지 대신합니다. 그러나 이 대화에서 남길 것이 사용자의 선호인지 지나가는 말인지는 여전히 설계 결정입니다.


---


## 정리


| 항목                    | 내용                                                                                                                                                                |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 문제 (What)             | 기억 메커니즘이 없으면 에이전트는 상태가 없다. 대화 컨텍스트를 유지하지 못하고, 경험에서 배우지 못하고, 응답을 개인화하지 못한다. 단순한 일회성 상호작용에 갇혀 다단계 과정이나 변해 가는 사용자 요구를 다루지 못한다                                        |
| 해법 (Why)              | 단기와 장기를 구분하는 이중 구성 기억 시스템을 둔다. 단기 맥락 기억은 최근 상호작용 데이터를 컨텍스트 윈도우 안에 두고, 지속되어야 하는 정보는 외부 데이터베이스(주로 벡터 저장소)에 두어 의미적으로 조회한다                                            |
| 두 기억의 관계              | 대등하지 않다. 장기 기억은 질의해서 꺼내 단기 컨텍스트에 통합해야 모델에 닿는다. 롱 컨텍스트 윈도우는 단기 기억의 크기를 늘릴 뿐 장기 기억이 아니다                                                                             |
| ADK 구성                | Session(이벤트 로그) · State(세션 임시 데이터) · Memory(검색 가능한 장기 지식). 각각 SessionService와 MemoryService가 관리한다                                                                 |
| 상태 갱신                 | `output_key`(최종 텍스트 응답) 또는 `EventActions.state_delta`(복잡한 갱신). `session.state` 직접 수정은 이벤트 이력·영속화·동시성·타임스탬프를 모두 건너뛴다                                               |
| 수명 선언                 | 접두사 없음(세션 전용) · `user:`(사용자의 모든 세션) · `app:`(모든 사용자) · `temp:`(현재 턴, 영속화 안 됨)                                                                                     |
| MemoryService         | `add_session_to_memory`로 넣고 `search_memory`로 찾는다. `InMemoryMemoryService`(테스트) · `VertexAiRagMemoryService`(프로덕션)                                                 |
| LangChain · LangGraph | `ChatMessageHistory`(수동) · `ConversationBufferMemory`(체인 통합, `memory_key`와 `return_messages`) · 장기 기억은 네임스페이스와 키로 조직된 JSON 문서                                     |
| 장기 기억 세 유형            | 의미 기억(사실, 프로필 또는 컬렉션) · 일화 기억(경험, 퓨샷 예시) · 절차 기억(규칙, 시스템 프롬프트를 Reflection으로 갱신)                                                                                   |
| Memory Bank           | Gemini가 대화 이력을 비동기로 분석해 핵심 사실과 선호를 추출하고, 모순을 해소하며 갱신한다. 무엇을 기억할지의 결정이 모델로 넘어간다                                                                                    |
| 비용                    | 통로는 컨텍스트 윈도우 하나 · 다 넣으면 성능 저하 · 롱 컨텍스트는 매번 과금 · 의미 검색은 정답을 보장하지 않음 · 조회 범위는 설정값 두 개가 결정 · 접두사 실수는 조용히 실패 · 직접 수정 우회로가 열려 있음 · 모델의 모순 해소는 불투명 · 절차 기억은 자기 지시문을 덮어씀 |
| 언제 쓰나                 | 단일 질문에 답하는 것 이상을 해야 할 때. 대화 전체의 컨텍스트 유지, 다단계 작업의 진행 추적, 선호와 이력에 근거한 개인화, 과거 성공과 실패로부터의 학습                                                                         |


처음의 질문으로 돌아갑니다. 쌓아둔 것 중에서 무엇이 돌아오는가.


이 장에서 가장 철학적으로 들리는 질문의 답은 설정 블록 안에 있었습니다.


```python
SIMILARITY_TOP_K = 5 # Number of top results to retrieve
VECTOR_DISTANCE_THRESHOLD = 0.7 # Threshold for vector similarity
```


상위 5개, 거리 0.7 이내입니다. 에이전트가 기억한다고 말할 때 실제로 벌어지는 일은 이 조건에 걸린 항목들이 프롬프트에 붙는 것입니다. 나머지는 저장고에 남아 있지만 이번 턴에는 존재하지 않는 것과 같습니다.


그래서 기억 관리에서 실제로 설계해야 하는 것은 저장 위치가 아닙니다. 저장 위치는 대개 선택지가 몇 개뿐이고 문서에 적혀 있습니다. 정해야 하는 것은 **무엇이 돌아올 자격이 있는지**이고, 그 판단이 접두사와 네임스페이스와 `similarity_top_k`에 흩어져 들어갑니다. 이 값들이 기본값으로 남아 있다면, 에이전트의 기억을 설계한 사람은 아직 없는 것입니다.


체인이 순서를, 라우팅이 선택을, 병렬화가 속도를, 리플렉션이 고쳐 쓸 기회를, 도구 사용이 바깥에 닿을 손을, 계획이 순서를 만들 권한을, 멀티 에이전트가 경계를 줬다면 기억은 **시간**을 줍니다. 세션 하나보다 긴 시간입니다.


그리고 시간이 생기면 다음 질문이 따라옵니다. 과거를 참조할 수 있게 된 에이전트가 과거에 비추어 자신을 바꿀 수도 있는가. 절차 기억에서 이미 그 조각을 봤습니다. 책도 같은 방향으로 장을 닫습니다.

> 이제 에이전트가 단기와 장기 양쪽으로 어떻게 기억하는지 다루었으니, 이들이 어떻게 학습하고 적응하는지로 넘어갈 수 있습니다. 다음 패턴 "Learning and Adaptation"은 에이전트가 새로운 경험이나 데이터에 근거해 사고 방식과 행동, 아는 것을 바꾸는 일에 관한 것입니다.

---


## 참고

- Antonio Gulli, _Agentic Design Patterns: A Hands-On Guide to Building Intelligent Systems_, Springer, 2025 — Chapter 8: Memory Management
- [ADK Memory](https://google.github.io/adk-docs/sessions/memory/)
- [LangGraph Memory](https://langchain-ai.github.io/langgraph/concepts/memory/)
- [Vertex AI Agent Engine Memory Bank](https://cloud.google.com/blog/products/ai-machine-learning/vertex-ai-memory-bank-in-public-preview)
