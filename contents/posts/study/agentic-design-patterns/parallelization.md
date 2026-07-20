---
title: '기다림은 합산된다 — Parallelization, 독립 작업을 동시에 달리게 하는 법'
date: '2026-07-20'
tags:
  - AI
series: Agentic Design Patterns
emoji: "\U0001F6E3️"
---
> Antonio Gulli, _Agentic Design Patterns_(Google / Springer)의 3장 "Parallelization"을 정리합니다.
> [지난 편](https://dhbang.co.kr/posts/study/agentic-design-patterns/routing/) Routing이 "갈림길에서 고르는 법"이었다면, 이번 편은 "여러 길을 동시에 달리는 법"입니다.

---


## 열심히 일하는데도 느린 에이전트


리서치 에이전트에게 주제 하나를 조사시켰는데, 답이 나올 때까지 한참을 기다린 적이 있으신가요? 로그를 열어 보면 에이전트는 놀고 있지 않습니다. 소스 A를 검색하고, 요약하고, 소스 B를 검색하고, 요약하고 — 쉬지 않고 일하는데도 느립니다.


이것은 에이전트가 게을러서가 아닙니다. **모든 작업이 한 줄로 서 있기 때문**입니다. 순차 실행에서 전체 처리 시간은 개별 작업 시간의 합입니다. 특히 API 호출이나 데이터베이스 조회처럼 지연(latency)이 있는 외부 서비스를 상대할 때 병목이 두드러집니다. 앞 작업의 응답을 기다리는 동안 뒤 작업은 시작조차 못 하니까요.


그런데 잘 보면 이상합니다. 소스 A 검색과 소스 B 검색은 서로의 결과가 전혀 필요 없습니다. 서로 독립인 작업이 굳이 순서를 지킬 이유가 있을까요?


3장이 다루는 Parallelization은 이 질문에 대한 답입니다. LLM 호출, 도구 사용, 나아가 서브에이전트 전체를 **동시에(concurrently) 실행**해서, 독립적인 부분들로 쪼갤 수 있는 작업의 전체 실행 시간을 크게 줄이는 패턴입니다.


---


## 핵심 개념 — 합을 최댓값으로 바꾸기

> 병렬화의 본질은 "서로의 출력에 의존하지 않는 부분"을 찾아내, 그 구간만 동시에 실행하는 것입니다.

책의 리서치 에이전트 예시로 두 방식을 비교하면 이렇습니다.


**순차 접근 — 5단계**

1. 소스 A 검색
2. 소스 A 요약
3. 소스 B 검색
4. 소스 B 요약
5. 요약 A·B로 최종 답변 합성

**병렬 접근 — 3단계**

1. 소스 A 검색 **과** 소스 B 검색을 동시에
2. 두 검색이 끝나면, 요약 A **와** 요약 B를 동시에
3. 요약 A·B로 최종 답변 합성

![Fig.1 — Parallelization 패턴: 하나의 입력이 여러 서브에이전트에 동시에 전달되고, 각자 독립적으로 출력을 만든다 (출처: Antonio Gulli, Agentic Design Patterns)](https://dhbang.co.kr/images/agentic-design-patterns/adp-ch3-fig1.png)


주목할 것은 마지막 단계입니다. 합성(synthesize)은 병렬 접근에서도 **여전히 순차**입니다. 앞의 병렬 작업들이 모두 끝나기를 기다렸다가 실행되는 합류 지점(convergence point)이죠. 병렬화는 "전부를 동시에 돌리는 것"이 아니라, **의존성 없는 구간을 골라 동시화하고, 의존성 있는 지점에서 합류하는 것**입니다.


프레임워크는 이 패턴을 각자의 방식으로 지원합니다.


| 프레임워크            | 병렬 실행 방식                                                                 |
| ---------------- | ------------------------------------------------------------------------ |
| LangChain (LCEL) | 러너블들을 딕셔너리·리스트로 묶어 다음 컴포넌트에 넘기면, LCEL 런타임이 안의 러너블들을 동시에 실행               |
| LangGraph        | 그래프 토폴로지로 표현 — 직접적 순차 의존이 없는 여러 노드를 하나의 공통 노드에서 시작시키고, 이후 합류 노드에서 결과를 집계 |
| Google ADK       | ParallelAgent 등 네이티브 프리미티브로 멀티에이전트의 동시 실행을 관리                            |


---


## 코드로 보는 병렬화 1 — LangChain의 RunnableParallel

> 딕셔너리에 체인들을 담으면, LCEL 런타임이 그것들을 동시에 실행합니다.

책의 LangChain 예제는 하나의 토픽에 대해 요약·질문 생성·핵심 용어 추출이라는 세 가지 독립 작업을 동시에 수행하고, 그 결과를 하나의 답으로 합성하는 구조입니다. 핵심만 추리면 세 부분입니다.


```python
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

# 1) 독립 체인 셋 — 요약 / 질문 생성 / 핵심 용어 추출
summarize_chain = (
    ChatPromptTemplate.from_messages([
        ("system", "Summarize the following topic concisely:"),
        ("user", "{topic}")
    ]) | llm | StrOutputParser()
)
questions_chain = (
    ChatPromptTemplate.from_messages([
        ("system", "Generate three interesting questions about the following topic:"),
        ("user", "{topic}")
    ]) | llm | StrOutputParser()
)
terms_chain = (
    ChatPromptTemplate.from_messages([
        ("system", "Identify 5-10 key terms from the following topic, separated by commas:"),
        ("user", "{topic}")
    ]) | llm | StrOutputParser()
)

# 2) 병렬 블록 — 딕셔너리 안의 러너블들이 동시에 실행된다
map_chain = RunnableParallel({
    "summary": summarize_chain,
    "questions": questions_chain,
    "key_terms": terms_chain,
    "topic": RunnablePassthrough(),   # 원본 토픽도 함께 다음 단계로
})

# 3) 합성 — 병렬 결과 셋을 받아 하나의 답으로 (합류 지점)
synthesis_prompt = ChatPromptTemplate.from_messages([
    ("system", """Based on the following information:
     Summary: {summary}
     Related Questions: {questions}
     Key Terms: {key_terms}
     Synthesize a comprehensive answer."""),
    ("user", "Original topic: {topic}")
])

full_parallel_chain = map_chain | synthesis_prompt | llm | StrOutputParser()

# 실행 — 토픽 하나가 map_chain의 각 러너블에 전달된다
response = await full_parallel_chain.ainvoke("The history of space exploration")
```


눈여겨볼 지점이 두 곳입니다.

- **`RunnablePassthrough`****의 재등장** — 병렬 결과(요약·질문·용어)와 함께 원본 토픽을 그대로 합성 단계에 넘깁니다. 지난 편 Routing에서 "결정 + 원본의 병렬 전달"로 봤던 구조가, 여기서는 "병렬 결과들 + 원본"으로 확장됩니다. 패턴이 달라져도 **다음 단계에 필요한 컨텍스트를 흘려보내는 문법**은 같습니다.
- **asyncio는 동시성이지 병렬성이 아니다** — 책이 명시적으로 짚는 부분입니다. `asyncio`는 단일 스레드 위에서 이벤트 루프가 "한 작업이 대기 중일 때(예: 네트워크 응답 대기) 다른 작업으로 전환"하는 방식입니다. 코드는 여전히 파이썬 GIL(Global Interpreter Lock)에 묶인 한 스레드에서 실행됩니다. 그런데도 효과가 큰 이유는, LLM 호출의 시간 대부분이 CPU 연산이 아니라 **네트워크 대기**이기 때문입니다. 기다림이 지배하는 작업에는 동시성만으로 충분합니다.

---


## 코드로 보는 병렬화 2 — Google ADK의 ParallelAgent + SequentialAgent

> 병렬 구간과 순차 구간을 각각 에이전트로 선언하고, 세션 상태(state)로 결과를 주고받습니다.

책의 ADK 예제는 세 명의 리서처 에이전트가 서로 다른 주제(재생에너지·전기차·탄소 포집)를 동시에 조사하고, 합성 에이전트가 그 결과를 하나의 보고서로 묶는 구조입니다.


```python
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.tools import google_search

# 1) 리서처 서브에이전트 — 각자 결과를 세션 상태(state)에 저장
researcher_agent_1 = LlmAgent(
    name="RenewableEnergyResearcher",
    model="gemini-2.0-flash",
    instruction="Research the latest advancements in 'renewable energy sources'. "
                "Summarize your key findings concisely (1-2 sentences). "
                "Output *only* the summary.",
    tools=[google_search],
    output_key="renewable_energy_result",   # 결과를 state에 저장하는 열쇠
)
# researcher_agent_2 (EVResearcher, output_key="ev_technology_result"),
# researcher_agent_3 (CarbonCaptureResearcher, output_key="carbon_capture_result")
# — 주제만 다르고 구조는 동일

# 2) 병렬 구간 — 세 리서처를 동시에 실행
parallel_research_agent = ParallelAgent(
    name="ParallelWebResearchAgent",
    sub_agents=[researcher_agent_1, researcher_agent_2, researcher_agent_3],
)

# 3) 합성 에이전트 — state에 쌓인 요약만으로 보고서 작성
merger_agent = LlmAgent(
    name="SynthesisAgent",
    model="gemini-2.0-flash",
    instruction="""Synthesize the following research summaries into a structured report.
**Crucially: Your entire response MUST be grounded *exclusively* on the
information provided below. Do NOT add any external knowledge.**

* Renewable Energy: {renewable_energy_result}
* Electric Vehicles: {ev_technology_result}
* Carbon Capture: {carbon_capture_result}
""",
)

# 4) 전체 흐름 — [병렬 리서치] → [합성]을 순차로 연결
root_agent = SequentialAgent(
    name="ResearchAndSynthesisPipeline",
    sub_agents=[parallel_research_agent, merger_agent],
)
```


이 코드에서 패턴의 구조가 문법 그대로 드러납니다.

- **`output_key`****가 통신 채널입니다** — 병렬로 도는 에이전트들은 서로 대화하지 않습니다. 각자 세션 상태의 자기 자리(`renewable_energy_result` 등)에 결과를 써 두면, 합성 에이전트가 instruction 안의 `{placeholder}`로 읽어 갑니다. 직접 호출 대신 **상태를 매개로 한 간접 연결**이라, 리서처를 늘리거나 빼도 서로를 몰라도 됩니다.
- **합성 프롬프트의 접지(grounding) 제약** — "제공된 요약에만 근거하고 외부 지식을 추가하지 말라"는 지시가 굵게 강조되어 있습니다. 병렬 결과를 합칠 때 LLM이 자기 지식을 섞으면, 병렬 단계가 실제로 조사한 내용과 최종 보고서가 어긋납니다. 합류 지점에서의 환각 방지 장치입니다.
- **`SequentialAgent[ParallelAgent[...], merger]`** — 펼침(fan-out)과 합침(fan-in)이라는 패턴의 골격이 선언 한 줄에 그대로 보입니다. 지난 두 편의 패턴(순차·분기)과 병렬이 **조합 가능한 부품**이라는 것도 이 구조가 보여줍니다.

---


## 어디에 쓰는가

> 공통점은 하나입니다. 서로 의존하지 않는 여러 작업이 최종 결과를 위해 모두 필요한 시스템.

| 사용처          | 병렬로 도는 작업들                                               |
| ------------ | -------------------------------------------------------- |
| 정보 수집·리서치    | 기업 조사 에이전트가 뉴스 검색, 주가 조회, 소셜 미디어 언급 확인, 사내 DB 질의를 동시에 수행 |
| 데이터 처리·분석    | 고객 피드백 배치에 감성 분석, 키워드 추출, 카테고리 분류, 긴급 이슈 식별을 동시에 적용      |
| 멀티 API·도구 호출 | 여행 플래너가 항공권 가격, 호텔 공실, 지역 이벤트, 맛집 추천을 동시에 조회             |
| 콘텐츠 생성       | 마케팅 이메일의 제목, 본문, 이미지, CTA 버튼 문구를 동시에 생성 후 조립             |
| 검증·확인        | 사용자 입력의 이메일 형식, 전화번호, 주소 대조, 욕설 필터를 동시에 검사               |
| 멀티모달 처리      | 소셜 포스트의 텍스트(감성·키워드)와 이미지(객체·장면)를 동시에 분석                  |
| A/B·다중 옵션 생성 | 살짝 다른 프롬프트나 모델로 헤드라인 3종을 동시에 생성해 비교·선택                   |


다만 책은 공짜가 아니라는 점도 분명히 합니다. 동시·병렬 아키텍처의 도입은 **설계, 디버깅, 로깅에 상당한 복잡성과 비용**을 더합니다. 순차 로그는 위에서 아래로 읽으면 되지만, 병렬 로그는 여러 작업의 흐름이 교차합니다. 지연이 문제가 아닌 곳에 병렬화를 넣으면, 얻는 것 없이 이 비용만 지불하게 됩니다.


---


## 정리


![Fig.2 — Parallelization 디자인 패턴: 하나의 프롬프트가 여러 에이전트에 동시에 전달되고, 각 출력이 사용자에게 돌아온다 (출처: Antonio Gulli, Agentic Design Patterns)](https://dhbang.co.kr/images/agentic-design-patterns/adp-ch3-fig2.png)


| 항목                    | 내용                                                                                                                     |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| 문제 (What)             | 순차 실행의 전체 처리 시간은 개별 작업 시간의 합이다. 외부 API·DB 호출처럼 I/O 지연이 있는 작업이 많을수록 병목이 커진다                                             |
| 해법 (Why)              | 서로의 출력에 의존하지 않는 컴포넌트(LLM 호출·도구 사용·서브에이전트)를 식별해 동시에 실행하고, 합류 지점에서 결과를 집계한다                                              |
| 언제 쓰나 (Rule of thumb) | 여러 API에서 데이터 가져오기, 데이터 청크 분산 처리, 합성 전 다중 콘텐츠 생성 등 — 독립적인 작업 여러 개가 동시에 돌 수 있을 때                                         |
| 핵심 기법                 | 독립 구간 식별 · 펼침/합침(fan-out/fan-in) 구조 · 상태 기반 결과 전달(output_key) · 합류 지점의 접지 제약                                           |
| 도구                    | LangChain LCEL(RunnableParallel) · LangGraph(그래프 분기·합류) · Google ADK(ParallelAgent + SequentialAgent) · Python asyncio |
| 비용                    | 설계·디버깅·로깅 복잡성 증가 — 지연이 병목일 때만 지불할 가치가 있다                                                                               |


체인이 순서를, 라우팅이 선택을 줬다면, 병렬화는 **속도**를 줍니다. 그리고 순차(chaining)·조건(routing)·병렬(parallelization)은 서로 배타적이지 않습니다 — 셋을 조합할 때 비로소 복잡한 작업을 감당하는 고성능 시스템이 됩니다. 다음 편은 실행이 아니라 **되돌아보는** 이야기 — 에이전트가 자기 결과물을 스스로 검토하고 고치는 Reflection입니다.


---


## 참고

- Antonio Gulli, _Agentic Design Patterns: A Hands-On Guide to Building Intelligent Systems_, Springer, 2025 — Chapter 3: Parallelization
- [LangChain Expression Language (LCEL) Documentation](https://python.langchain.com/docs/concepts/lcel/)
- [Google ADK Documentation — Multi-Agent Systems](https://google.github.io/adk-docs/agents/multi-agents/)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
