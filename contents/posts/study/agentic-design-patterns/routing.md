---
title: '체인은 갈림길을 모른다 — Routing, 에이전트가 스스로 경로를 고르는 법'
date: '2026-07-15'
tags:
  - AI
series: Agentic Design Patterns
emoji: "\U0001F500"
---
> Antonio Gulli, _Agentic Design Patterns_(Google / Springer)의 2장 "Routing"을 정리합니다.
> [지난 편](https://dhbang.co.kr/posts/study/agentic-design-patterns/prompt-chaining/) Prompt Chaining이 "쪼개서 잇는 법"이었다면, 이번 편은 "갈림길에서 고르는 법"입니다.

---


## 모든 문의가 같은 길을 타는 봇


고객 문의 봇을 체인으로 잘 만들어 놨는데, 이상한 답이 돌아온 적이 있으신가요? "주문 언제 와요?"에는 완벽하게 답하던 봇이, "환불 규정이 어떻게 되나요?"라는 질문에도 똑같이 주문 데이터베이스를 뒤지고 배송 조회 결과를 내놓습니다.


이것은 체인이 잘못 만들어져서가 아닙니다. **체인은 애초에 하나의 길만 알기 때문**입니다. 지난 편에서 본 Prompt Chaining은 결정론적·선형 워크플로우를 위한 기법입니다. 어떤 입력이 오든 1단계 → 2단계 → 3단계, 정해진 순서를 타죠. 그런데 현실의 요청은 한 종류가 아닙니다. 주문 조회, 상품 문의, 기술 지원, 그리고 무슨 말인지 알 수 없는 요청까지 — 입력의 성격에 따라 **가야 할 길 자체가 달라집니다**.


2장이 다루는 Routing은 이 갈림길 문제에 대한 답입니다. 에이전트의 실행 흐름에 조건부 로직(conditional logic)을 도입해서, 고정된 실행 경로를 "상황을 평가하고 다음 행동을 고르는" 동적 모델로 바꾸는 것입니다.


---


## 핵심 개념 — 흐름을 지배하는 결정 지점

> 라우팅의 본질은 "다음에 무엇을 할지"를 코드가 미리 정하지 않고, 실행 시점에 판단하게 만드는 것입니다.

앞의 고객 문의 봇에 라우팅을 넣으면 이렇게 됩니다.

1. **분석** — 사용자 질의를 먼저 분석해 의도(intent)를 파악한다.
2. **분기** — 의도에 따라 제어 흐름을 넘긴다.
    - "주문 상태 확인" → 주문 데이터베이스와 연동하는 체인으로
    - "상품 정보" → 상품 카탈로그를 검색하는 체인으로
    - "기술 지원" → 트러블슈팅 가이드 접근 또는 사람에게 에스컬레이션
    - **의도 불명** → 명확화(clarification)를 요청하는 체인으로

![Fig.1 — Router 패턴: LLM이 라우터가 되어 프롬프트를 분석하고, 적합한 전문 에이전트로 제어 흐름을 넘긴다 (출처: Antonio Gulli, Agentic Design Patterns)](https://dhbang.co.kr/images/agentic-design-patterns/adp-ch2-fig1.png)


주목할 것은 마지막 분기입니다. 잘 설계된 라우터는 "어디로 보낼지 모르겠다"는 경우까지 하나의 경로로 취급합니다. 분류 불가능한 입력은 현실에서 반드시 들어오고, 이를 위한 **기본 경로(fallback)** 가 없으면 시스템은 임의의 잘못된 길로 요청을 밀어 넣습니다.


라우팅이 끼어들 수 있는 지점은 한 곳이 아닙니다.


| 적용 지점    | 무엇을 결정하나                |
| -------- | ----------------------- |
| 워크플로우 시작 | 들어온 작업의 유형 분류 (triage)  |
| 체인 중간    | 앞 단계 결과에 따라 다음 행동 선택    |
| 서브루틴 내부  | 주어진 도구 셋에서 가장 적합한 도구 선택 |


즉 라우팅은 "입구에서 한 번 분류하고 끝"이 아니라, 에이전트의 운영 사이클 곳곳에 박히는 **결정 메커니즘**입니다.


---


## 메커니즘 — 라우터를 만드는 4가지 방법

> 누가 결정을 내리는가에 따라 라우팅의 유연성과 결정론성이 갈립니다.

책은 라우팅 메커니즘의 구현 방식을 네 가지로 정리합니다.


| 방식            | 결정 주체                      | 특징                                                                       |
| ------------- | -------------------------- | ------------------------------------------------------------------------ |
| **LLM 기반**    | 프롬프트를 받은 언어 모델             | "다음 중 하나만 출력하라: 'Order Status', 'Product Info', …" 식으로 분류를 지시. 유연하지만 확률적 |
| **임베딩 기반**    | 벡터 유사도                     | 질의를 임베딩으로 변환해 각 경로의 임베딩과 비교. 키워드가 아닌 **의미**로 라우팅(semantic routing)       |
| **규칙 기반**     | if-else, switch 등 사전 정의 로직 | 키워드·패턴·구조화 데이터 기반. 빠르고 결정론적이지만, 미묘하거나 새로운 입력에 약함                         |
| **ML 분류기 기반** | 파인튜닝된 판별 모델                | 라벨링된 소규모 코퍼스로 지도학습한 분류기. 라우팅 로직이 프롬프트가 아니라 **학습된 가중치에 인코딩**됨             |


네 번째가 낯설 수 있어 짚고 갑니다. ML 분류기 기반은 임베딩 기반과 개념적으로 비슷해 보이지만, 핵심 차이는 **지도 파인튜닝**입니다. 추론 시점에 생성 모델이 프롬프트를 실행하는 것이 아니라, 라우팅 전용으로 파라미터가 조정된 판별 모델이 결정을 내립니다. LLM이 쓰인다면 학습 데이터를 합성 생성하는 전처리 단계에서일 뿐, 실시간 라우팅 결정에는 관여하지 않습니다.


프레임워크 차원에서는 LangChain, LangGraph, Google ADK가 조건부 로직을 정의하는 명시적 구조를 제공합니다. 특히 LangGraph는 상태 기반 그래프 아키텍처여서, **시스템 전체에 누적된 상태에 따라 결정이 달라지는** 복잡한 라우팅 시나리오에 잘 맞습니다.


---


## 코드로 보는 라우팅 1 — LangChain의 명시적 분기

> 라우터 체인이 한 단어의 결정을 내리고, RunnableBranch가 그 결정대로 흐름을 넘깁니다.

책의 LangChain 예제는 "코디네이터"가 사용자 요청의 의도(예약 / 정보 / 불명)를 분류해 시뮬레이션된 서브에이전트 핸들러에 위임하는 구조입니다. 핵심만 추리면 세 부분입니다.


```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableBranch

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# 1) 라우터 체인 — 요청을 'booker' / 'info' / 'unclear' 한 단어로 분류
coordinator_router_prompt = ChatPromptTemplate.from_messages([
    ("system", """Analyze the user's request and determine which specialist
     handler should process it.
     - If the request is related to booking flights or hotels, output 'booker'.
     - For all other general information questions, output 'info'.
     - If the request is unclear or doesn't fit either category, output 'unclear'.
     ONLY output one word: 'booker', 'info', or 'unclear'."""),
    ("user", "{request}")
])
coordinator_router_chain = coordinator_router_prompt | llm | StrOutputParser()

# 2) 분기 — 라우터의 결정(decision)에 따라 핸들러를 선택
delegation_branch = RunnableBranch(
    (lambda x: x['decision'].strip() == 'booker', branches["booker"]),
    (lambda x: x['decision'].strip() == 'info',   branches["info"]),
    branches["unclear"],   # 기본 경로 — 그 외 모든 출력은 여기로
)

# 3) 결합 — 라우터의 결정과 원본 요청을 함께 분기에 전달
coordinator_agent = {
    "decision": coordinator_router_chain,
    "request": RunnablePassthrough()
} | delegation_branch | (lambda x: x['output'])
```


눈여겨볼 지점이 두 곳입니다.

- **`{"decision": ..., "request": RunnablePassthrough()}`** — 라우터의 분류 결과와 원본 요청을 나란히 다음 단계로 넘깁니다. 결정은 흐름을 고르는 데 쓰이고, 실제 처리 대상은 원본 그대로 핸들러에 도착합니다. 지난 편에서 본 "출력→입력 연결"이 여기서는 "결정+원본의 병렬 전달"로 확장된 셈입니다.
- **`.strip()`****과 기본 경로** — LLM 기반 라우터는 그 자체가 확률적 컴포넌트입니다. 앞뒤 공백이 붙거나, 세 단어 밖의 출력이 나올 수 있습니다. `.strip()`으로 공백을 방어하고, 매칭되지 않는 모든 출력을 `unclear` 경로로 흘려보내는 것 — 라우터의 불확실성을 구조로 감싸는 최소한의 안전장치입니다.

---


## 코드로 보는 라우팅 2 — Google ADK의 선언적 위임

> 그래프를 그리는 대신, 전문가 에이전트를 선언하고 위임 규칙을 지시문에 씁니다. 라우팅은 프레임워크가 합니다.

같은 시나리오를 Google ADK(Agent Development Kit)로 구현하면 접근이 완전히 달라집니다.


```python
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

# 전문 서브에이전트 — 각자 자기 도구를 가진다
booking_agent = Agent(
    name="Booker",
    model="gemini-2.0-flash",
    description="A specialized agent that handles all flight and hotel "
                "booking requests by calling the booking tool.",
    tools=[FunctionTool(booking_handler)]
)

info_agent = Agent(
    name="Info",
    model="gemini-2.0-flash",
    description="A specialized agent that provides general information "
                "and answers user questions by calling the info tool.",
    tools=[FunctionTool(info_handler)]
)

# 코디네이터 — 위임 규칙은 instruction(자연어)으로 기술
coordinator = Agent(
    name="Coordinator",
    model="gemini-2.0-flash",
    instruction=(
        "You are the main coordinator. Your only task is to analyze incoming "
        "user requests and delegate them to the appropriate specialist agent. "
        "Do not try to answer the user directly.\n"
        "- For any requests related to booking flights or hotels, "
        "delegate to the 'Booker' agent.\n"
        "- For all other general information questions, delegate to the 'Info' agent."
    ),
    # sub_agents가 정의되어 있으면 LLM 주도 위임(Auto-Flow)이 기본 활성화된다
    sub_agents=[booking_agent, info_agent]
)
```


여기에는 `RunnableBranch` 같은 분기 구조물이 없습니다. 코디네이터에 `sub_agents`를 정의하는 것만으로 ADK의 **Auto-Flow** 메커니즘이 작동합니다. 내부 모델이 사용자 의도를 각 서브에이전트의 `description`과 대조해 적합한 쪽으로 요청을 넘기는 것입니다.


두 프레임워크의 철학 차이를 정리하면 이렇습니다.


|           | LangChain / LangGraph     | Google ADK                          |
| --------- | ------------------------- | ----------------------------------- |
| 라우팅 정의    | 개발자가 분기·그래프를 **명시적으로 구성** | 도구·서브에이전트를 선언하면 프레임워크가 **내부적으로 매칭** |
| 결정 로직의 위치 | 코드(조건 함수, 그래프 엣지)         | 자연어 instruction + 프레임워크 내부 로직       |
| 잘 맞는 경우   | 누적 상태에 따라 갈리는 복잡한 다단계 라우팅 | 잘 정의된 이산적 기능 셋을 가진 에이전트             |


어느 쪽이 우월하다는 이야기가 아닙니다. 명시적 그래프는 통제력과 가시성을, 선언적 위임은 단순함을 삽니다. 시스템의 라우팅 복잡도가 어디까지 갈지에 따라 고르는 문제입니다.


---


## 어디에 쓰는가

> 공통점은 하나입니다. 입력의 성격에 따라 처리 경로가 달라져야 하는 시스템.

| 도메인               | 라우팅의 역할                                                                      |
| ----------------- | ---------------------------------------------------------------------------- |
| 가상 비서 · AI 튜터     | 자연어 질의의 의도를 해석해 정보 검색 도구 호출, 사람 에스컬레이션, 다음 커리큘럼 모듈 선택 등을 결정                  |
| 데이터 · 문서 처리 파이프라인 | 이메일·티켓·API 페이로드를 내용·메타데이터·형식으로 분류해 대응 워크플로우(영업 리드 처리, 포맷별 변환, 긴급 에스컬레이션)로 분배 |
| 멀티 에이전트 시스템       | 검색·요약·분석 에이전트로 구성된 리서치 시스템에서, 현재 목표에 가장 적합한 에이전트에 작업을 배정하는 고수준 디스패처          |
| AI 코딩 어시스턴트       | 프로그래밍 언어와 의도(디버그 / 설명 / 변환)를 식별한 뒤 코드 스니펫을 맞는 전문 도구로 전달                      |


결국 라우팅이 하는 일은 **논리적 중재(logical arbitration)** 입니다. 미리 정의된 시퀀스를 그대로 실행하는 정적 실행기를, 변화하는 조건 아래에서 가장 효과적인 방법을 고르는 동적 시스템으로 바꿉니다.


---


## 정리


| 항목                    | 내용                                                                                                               |
| --------------------- | ---------------------------------------------------------------------------------------------------------------- |
| 문제 (What)             | 단일 선형 프로세스는 다양한 입력·상황에 대응하지 못한다. 맥락 기반 결정 능력이 없으면 시스템은 경직되고 비적응적이다                                               |
| 해법 (Why)              | 들어온 질의를 먼저 분석해 의도를 파악하고, 제어 흐름을 가장 적합한 전문 도구·함수·서브에이전트로 동적으로 넘긴다                                                 |
| 언제 쓰나 (Rule of thumb) | 입력이나 현재 상태에 따라 서로 다른 워크플로우·도구·서브에이전트 중 하나를 골라야 할 때 / 유형 분류(triage)가 필요한 시스템 (예: 영업 문의·기술 지원·계정 문의를 구분하는 고객 지원 봇) |
| 핵심 기법                 | LLM · 임베딩 · 규칙 · ML 분류기 기반 라우팅 · 기본 경로(fallback) 확보 · 적용 지점 선택(시작 / 중간 / 도구 선택)                                  |
| 도구                    | LangChain(RunnableBranch) · LangGraph(상태 기반 조건부 분기) · Google ADK(sub_agents + Auto-Flow)                         |


체인이 에이전트에게 순서를 줬다면, 라우팅은 선택을 줍니다. 다음 편은 갈림길이 아니라 **동시에 여러 길을 달리는** 이야기 — Parallelization입니다.


---


## 참고

- Antonio Gulli, _Agentic Design Patterns: A Hands-On Guide to Building Intelligent Systems_, Springer, 2025 — Chapter 2: Routing
- [LangGraph Documentation](https://www.langchain.com/)
- [Google Agent Developer Kit Documentation](https://google.github.io/adk-docs/)
