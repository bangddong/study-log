---
title: '한 번에 다 시키면 왜 무너지는가 — Prompt Chaining, 모든 에이전트 패턴의 출발점'
date: '2026-07-06'
tags:
  - AI
series: Agentic Design Patterns
emoji: ⛓️
---
> Antonio Gulli, _Agentic Design Patterns_(Google / Springer)의 1장 "Prompt Chaining"을 정리합니다.
> 시리즈의 첫 번째 패턴입니다. 가장 단순하지만, 뒤에 나올 모든 패턴이 이 위에 서 있습니다.

---


## 요약만 잘하고, 나머지는 대충 하는 AI


복잡한 요청을 프롬프트 하나에 다 담아본 적이 있으신가요? "이 시장조사 보고서를 분석해서, 핵심을 요약하고, 데이터 근거와 함께 트렌드를 뽑고, 마케팅팀에 보낼 메일까지 써줘." 돌아온 결과를 보면 요약은 그럴듯한데, 데이터 추출은 빠져 있고, 메일은 형식만 갖춘 빈 껍데기입니다.


이것은 모델이 부족해서가 아닙니다. **한 번의 호출에 얹힌 인지 부하(cognitive load)가 임계를 넘었기 때문**입니다. 1장이 다루는 Prompt Chaining은 이 문제에 대한 가장 오래되고 확실한 답입니다. 복잡한 작업을 작은 하위 문제로 쪼개고, 앞 단계의 출력을 다음 단계의 입력으로 넘기는 것. 그래서 파이프라인 패턴(Pipeline pattern)이라고도 부릅니다.


[지난 편](https://dhbang.co.kr/posts/study/agentic-design-patterns/what-is-an-agent/)의 레벨 스펙트럼으로 말하면, 이 패턴은 Level 1~2 에이전트의 핵심 능력 — "여러 단계에 걸쳐 바깥 세상과 상호작용하는 능력" — 을 떠받치는 뼈대입니다.


---


## 한 방 프롬프트가 무너지는 5가지 방식

> 실패는 무작위가 아닙니다. 인지 부하가 커질 때 모델이 무너지는 경로는 정해져 있습니다.

| 실패 모드                          | 무슨 일이 일어나나                         |
| ------------------------------ | ---------------------------------- |
| **지시 누락(instruction neglect)** | 프롬프트의 일부 지시가 통채로 무시된다              |
| **맥락 표류(contextual drift)**    | 작업이 길어지면서 초기 맥락을 잃어버린다             |
| **오류 전파(error propagation)**   | 초반의 작은 오류가 뒤로 갈수록 증폭된다             |
| **컨텍스트 윈도우 부족**                | 필요한 정보가 창 안에 다 들어가지 못해 불충분한 답이 나온다 |
| **환각(hallucination)**          | 인지 부하가 커질수록 틀린 정보를 생성할 확률이 올라간다    |


앞의 시장조사 예시가 정확히 이 케이스입니다. 요약·추출·작문이라는 성격이 다른 세 작업을 한 번에 요구하면, 모델은 잔여 주의(attention)를 쪼개어 쓰다가 어느 하나를 희생시킵니다.


---


## 패턴: 나눠서, 순서대로, 이어붙인다

> 각 단계는 하나의 일만 합니다. 앞 단계의 출력이 다음 단계의 입력이 되는 의존의 사슬(chain) — 이것이 이름의 유래입니다.

위 실패 케이스를 체인으로 재구성하면 이렇게 됩니다.

1. **요약** — "다음 시장조사 보고서의 핵심을 요약하라: [원문]" — 모델은 요약에만 집중한다.
2. **트렌드 추출** — "이 요약을 바탕으로 상위 3개 트렌드와 근거 데이터를 추출하라: [1단계 출력]" — 검증된 출력 위에서 더 좁은 문제를 푼다.
3. **메일 작성** — "다음 트렌드와 근거를 담은 메일을 작성하라: [2단계 출력]"

![Fig.2 — Prompt Chaining 패턴: 각 에이전트의 출력이 다음 에이전트의 입력이 된다 (출처: Antonio Gulli, Agentic Design Patterns)](https://dhbang.co.kr/images/agentic-design-patterns/adp-ch1-fig2.png)


여기에 두 가지 장치를 더 얹을 수 있습니다.

- **단계별 역할 부여** — 1단계는 "시장 분석가", 2단계는 "트렌드 분석가", 3단계는 "문서 작성 전문가". 같은 모델이라도 단계마다 페르소나를 최적화하면 정확도가 올라갑니다.
- **단계 사이의 결정론적 로직** — LLM 호출과 호출 사이에 일반 코드가 끼어듭니다. 출력 검증, 조건 분기, 외부 도구 호출. 하나의 거대한 확률적 호출이, 결정론적 프레임워크가 관리하는 여러 개의 작은 확률적 호출로 바뀝니다.

---


## 사슬을 지탱하는 것: 구조화된 출력

> 체인의 신뢰성은 단계 사이를 오가는 데이터의 무결성에 달려 있습니다.

앞 단계 출력이 모호하거나 형식이 들쑥날쑥하면, 다음 단계는 오염된 입력으로 시작합니다. 그래서 단계 사이에는 자연어가 아니라 JSON 같은 **구조화된 포맷을 강제**하는 것이 정석입니다.


```json
{
  "trends": [
    {
      "trend_name": "AI-Powered Personalization",
      "supporting_data": "73% of consumers prefer to do business with brands that use personal information to make their shopping experiences more relevant."
    },
    {
      "trend_name": "Sustainable and Ethical Brands",
      "supporting_data": "Sales of products with ESG-related claims grew 28% over the last five years."
    }
  ]
}
```


자연어 해석의 여지를 없애고 기계가 정확히 파싱해 다음 프롬프트에 주입할 수 있게 됩니다. 체인이 길어질수록 이 규율의 가치는 복리로 커집니다.


---


## 어디에 쓰는가 — 7가지 시나리오

> 공통점은 하나입니다. 단계 사이에 논리적 의존이 있는 작업.

| # | 시나리오              | 체인 구성 예                                                 |
| - | ----------------- | ------------------------------------------------------- |
| 1 | 정보 처리 워크플로우       | 텍스트 추출 → 요약 → 엔티티 추출 → 지식베이스 검색 → 보고서 생성                |
| 2 | 복합 질의 응답          | 하위 질문 분해 → 각각 검색 → 종합 답변 합성                             |
| 3 | 데이터 추출·변환 (OCR 등) | 추출 → 정규화("천오십"→1050) → 계산은 외부 계산기 도구에 위임 → 검증, 미달 시 재시도 |
| 4 | 콘텐츠 생성            | 아이디어 → 개요 → 섹션별 초안(앞 섹션을 맥락으로) → 통합 퇴고                  |
| 5 | 상태 있는 대화 에이전트     | 발화 → 의도·엔티티 추출 → 상태 갱신 → 상태 기반 응답 (턴마다 반복)              |
| 6 | 코드 생성·정제          | 의사코드 → 초안 → 정적 분석·문제 식별 → 수정 → 문서·테스트 추가                |
| 7 | 멀티모달 추론           | 이미지 내 텍스트 추출 → 라벨과 연결 → 표 데이터로 해석                       |


한 가지 오해는 짚고 가겠습니다. 체이닝이 모든 것을 직렬로 만든다는 것은 아닙니다. 예를 들어 리서치 에이전트가 수십 개 기사에서 정보를 추출하는 일은 기사끼리 독립이므로 **병렬**로 돉니다. 하지만 그 다음 — 취합 → 합성 → 퇴고 — 는 앞 단계 없이 불가능한 **순차** 작업이고, 여기서 체인이 등장합니다. 실전 시스템은 독립 수집은 병렬, 의존적 합성은 체인으로 조합합니다.


---


## 코드로 보는 체인 — LangChain LCEL

> 파이프 연산자 하나로 프롬프트 → 모델 → 파서가 이어집니다.

책의 예제는 비구조 텍스트에서 사양을 추출하고(1단계), 그것을 JSON으로 변환하는(2단계) 최소 체인입니다.


```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatOpenAI(temperature=0)

# 1단계 — 비구조 텍스트에서 기술 사양 추출
prompt_extract = ChatPromptTemplate.from_template(
    "Extract the technical specifications from the following text:\n\n{text_input}"
)

# 2단계 — 추출된 사양을 JSON으로 변환
prompt_transform = ChatPromptTemplate.from_template(
    "Transform the following specifications into a JSON object with "
    "'cpu', 'memory', and 'storage' as keys:\n\n{specifications}"
)

# LCEL: 파이프 연산자로 체인 구성
extraction_chain = prompt_extract | llm | StrOutputParser()

full_chain = (
    {"specifications": extraction_chain}  # 1단계 출력이 2단계 입력으로
    | prompt_transform
    | llm
    | StrOutputParser()
)

input_text = "The new laptop model features a 3.5 GHz octa-core processor, 16GB of RAM, and a 1TB NVMe SSD."
final_result = full_chain.invoke({"text_input": input_text})
```


핵심은 `full_chain`의 첫 줄입니다. `{"specifications": extraction_chain}` — 1단계 체인 전체가 2단계 프롬프트의 변수 하나로 꽂혔니다. 출력→입력 연결이 문법 수준에서 표현됩니다. 선형 체인은 LangChain으로 충분하고, 상태·순환이 필요해지면 LangGraph로 넘어갑니다(이후 패턴에서 다똼니다).


---


## Context Engineering — 프롬프트를 넘어 환경을 설계한다

> 출력 품질을 좌우하는 것은 모델 아키텍처보다, 모델에게 제공된 컨텍스트의 풍부함입니다.

[지난 편](https://dhbang.co.kr/posts/study/agentic-design-patterns/what-is-an-agent/)에서 "레벨 2의 심장"이라 불렀던 컨텍스트 엔지니어링(Context Engineering)을, 1장은 그림 하나로 정리합니다.


![Fig.1 — Context Engineering은 프롬프트 엔지니어링·RAG·메모리·상태·구조화 출력을 포괄하는 상위 규율이다 (출처: Antonio Gulli, Agentic Design Patterns)](https://dhbang.co.kr/images/agentic-design-patterns/adp-ch1-fig1.png)


프롬프트 엔지니어링이 "지금 이 질문을 어떻게 쓸 것인가"라면, 컨텍스트 엔지니어링은 **토큰 생성 이전에 모델에게 제공될 정보 환경 전체를 설계하는 규율**입니다. 그림이 말하듯 프롬프트 엔지니어링은 그 안의 부분집합입니다. 시스템 프롬프트, 검색된 문서(RAG), 도구 출력, 대화 상태·이력, 메모리, 그리고 사용자 정체성 같은 암묵적 데이터까지 — 이 모든 층이 함께 출력 품질을 결정합니다.


체이닝과의 연결점이 여기 있습니다. 체인의 각 단계는 결국 "다음 호출에 어떤 컨텍스트를 만들어 줄 것인가"의 문제입니다. 요약 단계가 원문 전체가 아니라 정제된 요약만 다음 단계에 넘기는 것 — 그것이 바로 컨텍스트 큐레이션이고, 체이닝은 컨텍스트 엔지니어링을 실행 구조로 구현하는 가장 기본적인 형태입니다.


---


## 정리


| 항목                    | 내용                                                                                  |
| --------------------- | ----------------------------------------------------------------------------------- |
| 문제 (What)             | 복합 작업을 한 방 프롬프트로 처리하면 지시 누락·맥락 표류·오류 전파·환각이 발생한다                                    |
| 해법 (Why)              | 작업을 집중된 하위 단계로 분해하고 출력→입력으로 연결. 단계 사이에 검증·분기·도구를 끼워 신뢰성과 통제력을 확보                    |
| 언제 쓰나 (Rule of thumb) | 단일 프롬프트로 버거운 복잡도 / 서로 다른 처리 단계 여러 개 / 단계 사이 외부 도구 필요 / 멀티스텝 추론과 상태 유지가 필요한 에이전틱 시스템 |
| 핵심 기법                 | 단계별 역할 부여 · 구조화된 출력(JSON) · 단계 사이 결정론적 로직 · 독립 수집은 병렬·의존 합성은 체인                     |
| 도구                    | LangChain(선형 체인, LCEL) · LangGraph(상태·순환) · Crew AI · Google ADK                    |


한 번에 다 시키지 말고, 하나씩 시키고 이어붙이세요. 가장 단순한 이 규칙이 뒤에 나올 모든 에이전트 패턴의 출발점입니다.


---


## 참고

- Antonio Gulli, _Agentic Design Patterns: A Hands-On Guide to Building Intelligent Systems_, Springer, 2025 — Chapter 1: Prompt Chaining
- [LangChain LCEL Documentation](https://python.langchain.com/v0.2/docs/core_modules/expression_language/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Prompt Engineering Guide — Chaining Prompts](https://www.promptingguide.ai/techniques/chaining)
- [Vertex AI Prompt Optimizer](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/prompt-optimizer)
