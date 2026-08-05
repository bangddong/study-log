---
title: '모델은 실행하지 않는다. Tool Use, 에이전트가 바깥 세계에 손을 뻗는 법'
date: '2026-08-05'
tags:
  - AI
series: Agentic Design Patterns
emoji: "\U0001F6E0️"
---
> Antonio Gulli, _Agentic Design Patterns_(Google / Springer)의 5장 "Tool Use (Function Calling)"을 정리합니다.
> [지난 편](https://dhbang.co.kr/posts/study/agentic-design-patterns/reflection/) Reflection이 "자기 답을 다시 쓰는 법"이었다면, 이번 편은 "자기 밖으로 손을 뻗는 법"입니다.

---


## 모델은 네트워크를 건드리지 않았는데 답은 최신입니다


에이전트에 날씨 API를 붙여 본 적이 있으신가요. 붙이기 전에는 "오늘 런던 날씨"를 물으면 그럴듯한 문장이 돌아옵니다. 학습 데이터에서 끌어온 평균적인 런던 날씨입니다. 붙이고 나면 진짜 기온이 나옵니다.


그런데 로그를 열어 보면 이상합니다. 모델 쪽에서 나간 HTTP 요청이 없습니다. API를 때린 것은 내 프로세스입니다. 모델이 한 일은 JSON 한 덩이를 뱉은 것뿐입니다.


앞선 네 장에서 다룬 패턴은 모두 모델의 안쪽 이야기였습니다. 체이닝은 출력을 다음 단계로 넘기고, 라우팅은 갈래를 고르고, 병렬화는 여러 갈래를 굴리고, 리플렉션은 출력을 되돌립니다. 어느 것도 모델 바깥으로 나가지 않습니다. 책의 표현으로 이 패턴들은 "에이전트의 내부 워크플로 안에서 정보의 흐름을 관리하는" 일입니다.


5장의 Tool Use는 처음으로 바깥으로 나갑니다. 그리고 나가는 순간 질문이 하나 생깁니다.

> 모델이 실행하지 않는다면, 누가 실행하는가?

---


## 함수 호출은 모델이 함수를 부르는 일이 아니라, 불러 달라고 요청하는 일입니다


"Function Calling"이라는 이름은 오해를 부릅니다. 모델이 함수를 호출한다고 읽히니까요. 모델은 아무것도 호출하지 않습니다. **호출해 달라는 요청을 구조화된 형식으로 만들어 낼 뿐**입니다.


책이 제시하는 여섯 단계를 보면 실행 주체가 어디서 바뀌는지 정확히 드러납니다.

1. **도구 정의(Tool Definition).** 외부 함수나 기능을 정의하고 LLM에게 설명합니다. 함수의 목적, 이름, 받는 파라미터와 그 타입·설명이 여기 들어갑니다.
2. **LLM의 판단(LLM Decision).** LLM이 사용자 요청과 도구 정의를 함께 받습니다. 요청을 이해한 결과, 도구를 하나 이상 부르는 것이 필요한지 판단합니다.
3. **호출 생성(Function Call Generation).** 도구를 쓰기로 했다면 구조화된 출력을 만듭니다. 보통 JSON 객체이고, 부를 도구의 이름과 넘길 인자가 담깁니다. 인자는 사용자 요청에서 뽑아냅니다.
4. **도구 실행(Tool Execution).** **에이전틱 프레임워크 또는 오케스트레이션 계층이 이 구조화된 출력을 가로챕니다.** 요청된 도구를 식별해 실제 외부 함수를 주어진 인자로 실행합니다.
5. **관측(Observation/Result).** 실행 결과가 에이전트에게 돌아옵니다.
6. **LLM 처리(선택이지만 흔함).** LLM이 도구의 출력을 맥락으로 받아 최종 응답을 만들거나 다음 단계를 정합니다. 또 다른 도구를 부를 수도, 리플렉션으로 갈 수도, 최종 답을 낼 수도 있습니다.

3번과 4번 사이에 선이 그어져 있습니다. 3번까지가 모델의 몫이고, 4번부터는 내 코드의 몫입니다. 모델의 출력은 실행이 아니라 **실행 요청**입니다.


이 구분이 중요한 이유는 책임의 위치 때문입니다. 도구가 타임아웃되면 그것을 처리할 사람은 모델이 아닙니다. 인자가 잘못 채워져 API가 400을 뱉으면 그 응답을 받는 것도 모델이 아닙니다. 가로채는 쪽입니다.


---


## 도구는 함수보다 넓습니다. 다른 에이전트도 도구입니다


책은 "function calling"이라는 용어가 정확하긴 해도 좁다고 지적합니다. 미리 정의된 코드 함수를 부르는 것을 잘 설명하지만, 에이전트의 능력은 그보다 넓게 뻗을 수 있습니다.


그래서 더 넓은 개념으로 **"tool calling"**을 생각해 보자고 제안합니다. 도구는 전통적인 함수일 수도 있지만, 복잡한 API 엔드포인트일 수도, 데이터베이스 질의일 수도, **다른 전문 에이전트에게 보내는 지시**일 수도 있습니다.


마지막 항목이 특히 중요합니다. 주 에이전트가 복잡한 데이터 분석 과제를 전담 "분석가 에이전트"에게 위임하거나, 외부 지식 베이스를 그 API로 질의하는 그림이 여기서 나옵니다. 도구를 이렇게 보면 에이전트는 다양한 디지털 자원과 다른 지능적 개체들 사이에서 **오케스트레이터**로 행동하게 됩니다.


![Fig.1 — 에이전트가 도구를 쓰는 예시들. 메모리, 데이터베이스, 스토리지, 웹 브라우저, 웹 검색, 그리고 도구로서의 에이전트 (출처: Antonio Gulli, Agentic Design Patterns)](https://dhbang.co.kr/images/agentic-design-patterns/adp-ch5-fig1.png)


그림에서 눈여겨볼 것은 에이전트와 도구 상자 사이에 그려진 화살표입니다. 한 번 나갔다 들어오는 직선이 아니라 **Multi-step Tool Calling**이라고 이름 붙은 순환입니다. 위 여섯 단계의 6번이 다시 2번으로 돌아갈 수 있다는 뜻입니다. 도구를 하나 부르고 그 결과를 보고 다음 도구를 부르는 일이 여기서 벌어집니다.


---


## LLM이 읽는 명세는 시그니처가 아니라 독스트링입니다


LangChain에서 도구를 만드는 일은 두 단계입니다. 먼저 도구를 정의하고, 그 도구를 언어 모델에 **바인딩**합니다. 바인딩이 끝나면 모델은 외부 함수 호출이 필요하다고 판단했을 때 구조화된 도구 사용 요청을 만들어 낼 수 있게 됩니다.


책의 예제는 검색을 흉내 내는 도구 하나입니다.


```python
from langchain_core.tools import tool as langchain_tool

@langchain_tool
def search_information(query: str) -> str:
    """
    Provides factual information on a given topic. Use this tool to find answers to phrases
    like 'capital of France' or 'weather in London?'.
    """
    print(f"\n--- 🛠 Tool Called: search_information with query: '{query}' ---")
    # 미리 정의된 결과 딕셔너리로 검색 도구를 시뮬레이션한다.
    simulated_results = {
        "weather in london": "The weather in London is currently cloudy with a temperature of 15°C.",
        "capital of france": "The capital of France is Paris.",
        "population of earth": "The estimated population of Earth is around 8 billion people.",
        "tallest mountain": "Mount Everest is the tallest mountain above sea level.",
        "default": f"Simulated search result for '{query}': No specific information found, but the topic seems interesting."
    }
    result = simulated_results.get(query.lower(), simulated_results["default"])
    return result

tools = [search_information]
```


`@langchain_tool` 데코레이터 하나가 평범한 파이썬 함수를 도구로 바꿉니다. 여기서 중요한 것은 함수 본문이 아니라 **독스트링**입니다. 1단계의 "함수의 목적을 설명한다"가 코드에서는 독스트링 자리에 들어갑니다. 모델은 이 함수의 구현을 보지 못합니다. 이름, 타입 힌트, 그리고 독스트링만 봅니다.


독스트링을 다시 읽어 보면 설명이 아니라 **사용 지침**에 가깝습니다. "이런 주제의 사실 정보를 제공한다"에서 끝나지 않고 "'capital of France'나 'weather in London?' 같은 문구의 답을 찾을 때 이 도구를 쓰라"고 예시까지 붙였습니다. 문서를 쓰는 것이 아니라 프롬프트를 쓰는 것입니다.


도구를 만들었으면 에이전트에 묶습니다.


```python
# 이 프롬프트 템플릿에는 에이전트의 내부 단계를 담을 `agent_scratchpad` 자리표시자가 필요하다.
agent_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# LLM, 도구, 프롬프트를 하나로 묶어 에이전트를 만든다.
agent = create_tool_calling_agent(llm, tools, agent_prompt)

# AgentExecutor는 에이전트를 호출하고 선택된 도구를 실행하는 런타임이다.
agent_executor = AgentExecutor(agent=agent, verbose=True, tools=tools)
```


`AgentExecutor`에 책이 붙인 설명이 앞 절에서 그은 선을 그대로 옮겨 놓았습니다. "에이전트를 호출하고 **선택된 도구를 실행하는** 런타임." 도구를 고르는 것은 에이전트이고 실행하는 것은 Executor입니다. 4단계에서 말한 가로채는 쪽이 여기 있습니다.


`agent_scratchpad`도 같은 이야기를 합니다. 모델이 만든 호출 요청과 그 실행 결과가 쌓이는 자리입니다. 리플렉션에서 `message_history`가 루프의 상태였던 것처럼, 여기서는 스크래치패드가 도구 호출 사이클의 상태입니다. 모델은 매 호출마다 "내가 지금까지 뭘 불렀고 뭘 받았는지"를 이 자리를 통해 다시 봅니다.


---


## CrewAI는 도구가 실패할 권리를 코드로 인정합니다


CrewAI 예제는 주식 시세를 흉내 내는 도구인데, 성공 경로보다 실패 경로가 더 많은 것을 말해 줍니다.


```python
from crewai.tools import tool

@tool("Stock Price Lookup Tool")
def get_stock_price(ticker: str) -> float:
    """
    Fetches the latest simulated stock price for a given stock ticker symbol.
    Returns the price as a float. Raises a ValueError if the ticker is not found.
    """
    simulated_prices = {"AAPL": 178.15, "GOOGL": 1750.30, "MSFT": 425.50}
    price = simulated_prices.get(ticker.upper())

    if price is not None:
        return price
    else:
        # 문자열을 돌려주는 것보다 구체적인 에러를 던지는 편이 낫다.
        # 에이전트는 예외를 다룰 수 있고 다음 행동을 스스로 정할 수 있다.
        raise ValueError(f"Simulated price for ticker '{ticker.upper()}' not found.")
```


도구가 실패했을 때 `"찾을 수 없습니다"`라는 문자열을 반환하지 않고 `ValueError`를 던집니다. 책이 코드 주석으로 이유를 명시합니다. 구체적인 에러를 던지는 편이 문자열을 돌려주는 것보다 낫고, 에이전트는 예외를 다룰 준비가 되어 있으므로 다음 행동을 스스로 정할 수 있다는 것입니다.


이 선택이 왜 중요한가. 실패를 문자열로 돌려주면 성공과 실패가 같은 통로로 들어옵니다. 모델은 `"AAPL의 가격은 178.15입니다"`와 `"AAPL의 가격을 찾을 수 없습니다"`를 똑같이 도구가 준 사실로 받습니다. 둘을 구분하는 것은 모델의 독해력에 달리게 됩니다. 예외로 던지면 그 구분이 프로토콜 수준으로 올라갑니다. 성공은 `float`이고 실패는 예외입니다.


다만 예외를 던진 뒤 무엇을 할지는 여전히 적어 줘야 합니다. Task 정의를 보면 그 지시가 들어 있습니다.


```python
analyze_aapl_task = Task(
    description=(
        "What is the current simulated stock price for Apple (ticker: AAPL)? "
        "Use the 'Stock Price Lookup Tool' to find it. "
        "If the ticker is not found, you must report that you were unable to retrieve the price."
    ),
    expected_output=(
        "A single, clear sentence stating the simulated stock price for AAPL. "
        "For example: 'The simulated stock price for AAPL is $178.15.' "
        "If the price cannot be found, state that clearly."
    ),
    agent=financial_analyst_agent,
)
```


`description`과 `expected_output` 양쪽 모두에 실패 시 행동이 적혀 있습니다. "티커를 찾지 못하면 가격을 가져올 수 없었다고 보고해야 한다." 도구를 붙였다고 실패 처리가 따라오지는 않습니다. 도구를 붙이는 일과 그 도구가 실패했을 때의 시나리오를 적는 일은 별개의 작업입니다.


---


## ADK는 도구를 만들게 하지 않고 고르게 합니다


Google ADK는 접근이 다릅니다. 직접 정의하는 도구도 물론 쓸 수 있지만, **네이티브로 통합된 도구 라이브러리**를 제공해 에이전트 능력에 곧바로 붙일 수 있게 합니다. 책은 셋을 예로 듭니다.


**Google Search입니다.** 구글 검색 엔진에 대한 직접 인터페이스입니다. 에이전트에 웹 검색으로 외부 정보를 가져오는 기능을 부여합니다.


```python
from google.adk.agents import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="basic_search_agent",
    model="gemini-2.0-flash-exp",
    description="Agent to answer questions using Google Search.",
    instruction="I can answer your questions by searching the internet. Just ask me anything!",
    tools=[google_search]  # Google Search는 검색을 수행하는 사전 제작 도구다.
)
```


LangChain의 `@tool`과 비교하면 사라진 것이 보입니다. 함수 본문도, 독스트링도, API 클라이언트도 없습니다. `tools=[google_search]` 한 줄입니다.


**코드 실행(Code Execution)입니다.** `BuiltInCodeExecutor`가 에이전트에게 **샌드박스된 파이썬 인터프리터**를 제공합니다. 모델이 코드를 써서 실행하고, 계산을 수행하고, 자료구조를 다루고, 절차적 스크립트를 돌릴 수 있습니다. 책은 이 기능이 필요한 이유를 분명히 합니다. **결정론적 논리와 정확한 계산**이 필요한 문제는 확률적 언어 생성만으로는 다룰 수 없는 영역이기 때문입니다.


```python
from google.adk.agents import LlmAgent
from google.adk.code_executors import BuiltInCodeExecutor

code_agent = LlmAgent(
    name="calculator_agent",
    model="gemini-2.0-flash",
    code_executor=BuiltInCodeExecutor(),
    instruction="""You are a calculator agent.
    When given a mathematical expression, write and execute Python code to calculate the result.
    Return only the final numerical result as plain text, without markdown or code blocks.
    """,
    description="Executes Python code to perform calculations.",
)
```


이 에이전트를 돌릴 때 이벤트를 처리하는 코드가 이번 장의 주제를 다시 한번 보여 줍니다.


```python
async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content):
    if event.content and event.content.parts and event.is_final_response():
        for part in event.content.parts:
            if part.executable_code:
                # 실제 코드 문자열은 .code로 접근한다
                print(f"  Debug: Agent generated code:\n{part.executable_code.code}")
            elif part.code_execution_result:
                # outcome과 output을 각각 꺼낸다
                print(f"  Debug: Code Execution Result: {part.code_execution_result.outcome} "
                      f"- Output:\n{part.code_execution_result.output}")
            elif part.text and not part.text.isspace():
                print(f"  Text: '{part.text.strip()}'")
```


`part.executable_code`와 `part.code_execution_result`가 **다른 파트로 분리되어** 옵니다. 모델이 생성한 코드와 그 코드를 실행한 결과가 응답 안에서 별개의 항목입니다. 앞에서 개념으로 말한 "요청과 실행의 분리"가 여기서는 이벤트 스키마로 굳어져 있습니다. 실행 결과에 `outcome`이라는 필드가 따로 붙어 있는 것도 같은 이유입니다. 실행은 성공하거나 실패하는 사건이고, 그 사실을 텍스트에 섞지 않습니다.


**Vertex AI Search입니다.** `VSearchAgent`는 지정된 Vertex AI Search 데이터스토어를 검색해 질문에 답하도록 설계된 에이전트입니다. 사내 문서 같은 비공개 자료를 대상으로 합니다. 응답을 스트리밍으로 받으면서 `event.grounding_metadata`로 **출처 귀속(source attribution)**을 함께 확인할 수 있다는 점이 검색 도구와 다릅니다.


```python
if event.is_final_response():
    if event.grounding_metadata:
        print(f"   (Source Attributions: {len(event.grounding_metadata.grounding_attributions)} sources found)")
    else:
        print("   (No grounding metadata found)")
```


---


## Extension과 함수 호출을 가르는 것은 기능이 아니라 실행 주체입니다


책은 장 후반에 Vertex AI Extension을 소개하면서 함수 호출과의 차이를 한 문장으로 정리합니다. 도입부의 질문에 대한 답이 여기 있습니다.


Extension은 모델이 외부 API에 연결해 실시간 데이터 처리와 액션 실행을 하게 해 주는 **구조화된 API 래퍼**입니다. 엔터프라이즈급 보안, 데이터 프라이버시, 성능 보장을 제공합니다. 코드 생성·실행, 웹사이트 질의, 비공개 데이터스토어 분석 같은 작업에 쓰이고, Code Interpreter나 Vertex AI Search처럼 미리 만들어진 것을 쓰거나 직접 만들 수 있습니다.


기능만 나열하면 함수 호출과 구분이 되지 않습니다. 그래서 책이 핵심 차이를 따로 짚습니다.

> Extension과 함수 호출의 핵심 차이는 실행에 있습니다. **Vertex AI는 Extension을 자동으로 실행하지만, 함수 호출은 사용자나 클라이언트가 직접 실행해야 합니다.**

둘의 차이는 무엇을 할 수 있느냐가 아니라 **누가 4단계를 맡느냐**입니다. 함수 호출에서는 내 코드가 가로채고 실행하고 결과를 되돌려 줍니다. Extension에서는 플랫폼이 그 자리를 대신 맡습니다. 편해지는 대신 실행 시점과 실패 처리에 대한 통제권이 플랫폼으로 넘어갑니다.


![Fig.2 — Tool Use 디자인 패턴. 에이전트와 도구 사이의 화살표가 양방향이다 (출처: Antonio Gulli, Agentic Design Patterns)](https://dhbang.co.kr/images/agentic-design-patterns/adp-ch5-fig2.png)


---


## 어디에 쓰는가


책이 드는 활용처는 에이전트가 텍스트 생성을 넘어 행동하거나 특정한 동적 정보를 가져와야 하는 경우입니다.


| 영역            | 도구                     | 흐름                                                    |
| ------------- | ---------------------- | ----------------------------------------------------- |
| 외부 정보 조회      | 날씨 API                 | "런던 날씨는?" → 도구를 "London"으로 호출 → 데이터 수신 → 사용자용 문장으로 정리 |
| 데이터베이스·API 연동 | 재고 조회, 주문 상태, 결제 API   | "X 재고 있나요?" → 재고 API 호출 → 재고 수량 수신 → 상태 안내            |
| 계산·데이터 분석     | 계산기, 주식 시세 API, 스프레드시트 | 시세 API로 현재가를 받고, 계산기로 손익을 계산한 뒤 응답 구성                 |
| 커뮤니케이션        | 이메일 발송 API             | "존에게 내일 회의 메일 보내 줘" → 수신자·제목·본문을 요청에서 추출해 호출          |
| 코드 실행         | 코드 인터프리터               | 사용자가 준 스니펫을 실행해 보고 그 출력으로 동작을 설명                      |
| 기기 제어         | 스마트 조명 API             | "거실 불 꺼 줘" → 명령과 대상 기기를 인자로 호출                        |


마지막 두 항목의 성격이 앞의 넷과 다릅니다. 조회는 틀려도 다시 물으면 되지만, 메일 발송과 기기 제어는 되돌릴 수 없습니다. 책은 이 패턴이 언어 모델을 "디지털 또는 물리적 세계에서 감지하고, 추론하고, **행동하는**" 에이전트로 바꾼다고 씁니다. 행동에는 취소 버튼이 없습니다.


---


## 도구를 붙이는 순간 실행 책임이 전부 이쪽으로 넘어옵니다


책에 독립된 한계 섹션은 없습니다. 대신 예제 곳곳에 비용이 흩어져 있습니다. 모아 보면 방향이 하나입니다. **모델이 요청만 하고 실행하지 않기 때문에, 실행에 딸린 것들이 전부 개발자 몫으로 남습니다.**


**첫째, 실패 처리가 자동으로 따라오지 않습니다.** CrewAI 예제에서 도구는 `ValueError`를 던지지만, 그 예외를 만난 에이전트가 무엇을 할지는 Task의 `description`과 `expected_output`에 각각 다시 적혀 있습니다. 도구 하나를 붙이면 성공 경로 하나가 아니라 성공 경로 하나와 실패 시나리오 하나가 생깁니다.


**둘째, 자격 증명 관리가 코드 밖의 문제로 남습니다.** 책은 CrewAI 예제 주석에서 프로덕션에서는 더 안전한 키 관리 방식을 권장한다고 명시합니다. 런타임에 로드하는 환경 변수나 시크릿 매니저를 예로 듭니다. LangChain 예제는 `getpass`로 키를 받고, ADK 예제는 `os.environ`에서 읽습니다. 도구가 늘어난다는 것은 관리해야 할 키가 늘어난다는 뜻이기도 합니다.


**셋째, 코드 실행에는 격리가 전제됩니다.** 책은 코드 인터프리터를 소개할 때 "안전한 환경(safe environment)"과 "샌드박스된(sandboxed)"이라는 수식을 빼놓지 않습니다. 모델이 쓴 코드를 그냥 돌리는 것이 아니라 격리된 곳에서 돌리는 것이 이 도구의 정의입니다. 격리를 빼면 도구가 아니라 원격 코드 실행 구멍입니다.


**넷째, 도구 설명의 품질이 그대로 판단의 품질이 됩니다.** 2단계에서 LLM은 사용자 요청과 도구 정의만 보고 판단합니다. 구현은 보지 못합니다. 독스트링이 모호하면 모델은 엉뚱한 도구를 고르거나, 골라야 할 도구를 지나칩니다. 이때 문제는 코드에 없습니다. 코드는 정상 동작합니다.


**다섯째, 도구가 그럴듯한 실패를 반환하면 걸러낼 방법이 없습니다.** LangChain 예제의 검색 도구는 모르는 질의에 대해 `"특정 정보를 찾지 못했으나 주제가 흥미로워 보입니다"`라는 기본값을 돌려줍니다. 형식만 보면 성공한 결과와 구분되지 않습니다. 앞 절의 CrewAI 방식이 이 지점을 정확히 겨냥합니다.


책의 판단 기준(Rule of thumb)은 간명합니다. **에이전트가 LLM의 내부 지식을 벗어나 바깥 세계와 상호작용해야 할 때** 도구를 씁니다. 실시간 데이터, 비공개 정보, 정확한 계산, 코드 실행, 다른 시스템에 대한 액션이 그 자리입니다.


뒤집으면, 내부 지식으로 답이 나오는 질문에 도구를 붙이는 것은 지연과 실패 지점만 늘리는 일입니다. 도구는 능력을 늘리는 만큼 실패할 곳도 늘립니다.


---


## 정리


| 항목        | 내용                                                                                                                                                                               |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 문제 (What) | LLM은 강력한 텍스트 생성기이지만 바깥 세계와 근본적으로 단절돼 있다. 지식은 학습 시점에 고정돼 있고, 행동하거나 실시간 정보를 가져올 능력이 없다                                                                                             |
| 해법 (Why)  | 외부 함수를 LLM이 이해할 형식으로 설명해 두고, 필요하다고 판단하면 어떤 함수를 어떤 인자로 부를지 지정한 구조화된 데이터를 생성하게 한다. 오케스트레이션 계층이 그것을 실행해 결과를 되먹인다                                                                    |
| 여섯 단계     | 도구 정의 → LLM 판단 → 호출 생성 → **도구 실행** → 관측 → LLM 처리(선택)                                                                                                                             |
| 실행 주체     | 3단계까지가 모델, 4단계부터가 프레임워크·오케스트레이션 계층. Vertex Extension은 이 4단계를 플랫폼이 자동 수행한다는 점에서 함수 호출과 갈린다                                                                                        |
| 도구의 범위    | 함수뿐 아니라 API 엔드포인트, DB 질의, 다른 에이전트에 대한 지시까지. 그래서 "function calling"보다 "tool calling"이 넓다                                                                                          |
| 도구        | LangChain(`@tool` 독스트링이 명세, `create_tool_calling_agent`  • `AgentExecutor`) · CrewAI(실패를 예외로 던짐) · Google ADK(`google_search`, `BuiltInCodeExecutor`, `VSearchAgent` 등 사전 제작 도구) |
| 비용        | 실패 시나리오·자격 증명·샌드박스가 모두 개발자 몫. 도구 설명의 품질이 판단의 품질을 결정하고, 그럴듯한 실패 반환은 성공과 구분되지 않는다                                                                                                  |
| 언제 쓰나     | 실시간 데이터, 비공개 정보, 정확한 계산, 코드 실행, 외부 시스템에 대한 액션이 필요할 때                                                                                                                             |


처음의 질문으로 돌아갑니다. 모델이 실행하지 않는다면 누가 실행하는가.


답은 내 코드입니다. LangChain에서는 `AgentExecutor`, ADK에서는 `Runner`, Vertex Extension에서는 플랫폼입니다. 이름이 무엇이든 모델과 세계 사이에 서서 JSON을 받아 실제 호출로 바꾸는 층이 하나 있습니다. 도구를 설계한다는 것은 그 층이 무엇을 하고 무엇을 못 하는지 정하는 일입니다.


체인이 순서를, 라우팅이 선택을, 병렬화가 속도를, 리플렉션이 고쳐 쓸 기회를 줬다면 도구 사용은 **바깥에 닿을 손**을 줍니다. 손이 생기면 다음 문제는 손을 몇 개 붙일 것이냐가 아닙니다. 여러 손을 누가 어떤 순서로 움직이느냐입니다.


---


## 참고

- Antonio Gulli, _Agentic Design Patterns: A Hands-On Guide to Building Intelligent Systems_, Springer, 2025 — Chapter 5: Tool Use (Function Calling)
- [LangChain Documentation (Tools)](https://python.langchain.com/docs/integrations/tools/)
- [Google Agent Developer Kit (ADK) Documentation (Tools)](https://google.github.io/adk-docs/tools/)
- [OpenAI Function Calling Documentation](https://platform.openai.com/docs/guides/function-calling)
- [CrewAI Documentation (Tools)](https://docs.crewai.com/concepts/tools)
