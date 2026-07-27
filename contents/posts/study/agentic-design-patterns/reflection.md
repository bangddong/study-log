---
title: '첫 출력은 초안이다. Reflection, 에이전트가 자기 답을 다시 쓰게 만드는 법'
date: '2026-07-27'
tags:
  - AI
series: Agentic Design Patterns
emoji: "\U0001F501"
---
> Antonio Gulli, _Agentic Design Patterns_(Google / Springer)의 4장 "Reflection"을 정리합니다.
> [지난 편](https://dhbang.co.kr/posts/study/agentic-design-patterns/parallelization/) Parallelization이 "여러 길을 동시에 달리는 법"이었다면, 이번 편은 "달려온 길을 되돌아보는 법"입니다.

---


## 처음 나온 답이 그대로 최종 답이 되는 구조


에이전트에게 코드를 짜 달라고 했더니 얼추 맞는데 엣지 케이스가 빠진 결과물을 받아 본 적이 있으신가요? 다시 물어보면 대개 스스로 고칩니다. "음수 입력은 어떻게 처리하나요?"라고 한 마디만 던져도 예외 처리를 붙여서 다시 내놓습니다.


이상한 일입니다. 고칠 능력이 있었다면 왜 처음부터 고쳐서 주지 않았을까요.


능력이 없어서가 아닙니다. **워크플로에 자기 출력을 다시 볼 자리가 없었기 때문**입니다. 앞선 세 장에서 다룬 패턴들은 모두 앞으로만 흐릅니다. 체이닝(Chaining)은 출력을 다음 단계로 넘기고, 라우팅(Routing)은 갈래를 고르고, 병렬화(Parallelization)는 여러 갈래를 동시에 굴립니다. 정교한 워크플로를 짜도 첫 출력이 곧 최종 출력입니다. 품질과 무관하게요.


4장이 다루는 Reflection은 여기에 되돌아오는 경로 하나를 추가합니다. 에이전트가 자기 작업물이나 내부 상태를 스스로 평가하고, 그 평가를 근거로 결과물을 다시 씁니다.


다만 되돌아오는 경로를 만드는 순간 새로운 문제가 생깁니다. 앞으로만 흐르는 워크플로는 끝이 자명하지만, 루프는 그렇지 않습니다.

> 이 루프는 언제 멈추는가?

---


## 리플렉션은 출력을 한 번 더 다듬는 일이 아니라, 출력을 다시 입력으로 되돌리는 일입니다


리플렉션을 "결과물에 윤을 내는 후처리 단계"로 이해하면 앞선 패턴들과 구분이 되지 않습니다. 후처리도 결국 파이프라인의 마지막 칸일 뿐이니까요.


책은 이 차이를 정확히 짚습니다. 출력을 다음 단계로 그대로 넘기는 단순 순차 체인과 다르고, 경로를 고르는 라우팅과도 다릅니다. 리플렉션이 도입하는 것은 **피드백 루프**입니다. 에이전트는 출력을 만드는 데서 멈추지 않고, 그 출력(또는 그것을 만들어 낸 과정)을 다시 들여다보고, 문제나 개선점을 찾아내고, 그 발견을 재료 삼아 더 나은 버전을 만듭니다.


방향이 다릅니다. 다듬기는 결과물을 앞으로 밀고, 리플렉션은 결과물을 뒤로 되돌립니다. 되돌아온 출력은 다음 회차의 입력이 됩니다.


![Fig.1 — Reflection 디자인 패턴, 자기 성찰: 에이전트의 출력이 다시 자신에게 되돌아온다 (출처: Antonio Gulli, Agentic Design Patterns)](https://dhbang.co.kr/images/agentic-design-patterns/adp-ch4-fig1.png)


---


## 루프는 네 단계로 끊어야 멈출 수 있습니다


책이 제시하는 리플렉션 과정은 네 단계입니다.

1. **실행(Execution).** 에이전트가 작업을 수행해 초기 출력을 만듭니다.
2. **평가·비평(Evaluation/Critique).** 앞 단계의 결과를 분석합니다. 보통 또 한 번의 LLM 호출이거나 규칙 집합입니다. 사실 정확성, 일관성, 문체, 완결성, 지시 준수 여부 같은 기준으로 봅니다.
3. **정제(Reflection/Refinement).** 비평을 근거로 어떻게 개선할지 정합니다. 결과물을 다시 쓰는 것일 수도 있고, 다음 단계의 파라미터를 조정하거나 계획 자체를 수정하는 것일 수도 있습니다.
4. **반복(Iteration).** 정제된 출력으로 다시 실행하고, 만족스러운 결과가 나오거나 **정지 조건을 만날 때까지** 반복합니다.

여기서 눈여겨볼 것은 4번에 책이 붙여 둔 단서입니다. "선택이지만 흔한(Optional but common)". 반복은 패턴의 필수 구성 요소가 아니라 옵션입니다.


이 구분이 중요한 이유는 뒤에서 다룰 비용 때문입니다. 1회전만 도는 리플렉션과 N회전 도는 리플렉션은 얻는 것도 다르지만 무엇보다 **지불하는 것이 다릅니다.** 반복을 기본값으로 깔아 두면 비용이 조용히 늘어납니다.


---


## 자기 출력을 자기가 검토하면, 자기가 놓친 이유로 또 놓칩니다


한 에이전트가 생성과 평가를 모두 맡는 자기 성찰도 가능합니다. 다만 책은 더 효과적인 구현으로 역할을 둘로 쪼개는 방식을 제시합니다. **Producer와 Critic**입니다. Generator-Critic 또는 Producer-Reviewer 모델이라고도 부릅니다.

- **Producer 에이전트입니다.** 작업의 초기 실행만 담당합니다. 코드를 쓰든 블로그 글 초안을 잡든 계획을 세우든, 콘텐츠를 만들어 내는 데만 집중합니다.
- **Critic 에이전트입니다.** Producer의 출력을 평가하는 것이 유일한 목적입니다. 다른 지시와 별도의 페르소나를 받습니다. "당신은 시니어 소프트웨어 엔지니어입니다", "당신은 꼼꼼한 팩트체커입니다" 같은 식으로요.

왜 나누는가. 책의 표현으로는 에이전트가 자기 작업을 검토할 때 생기는 **인지 편향(cognitive bias)을 막기 위해서**입니다. 이 표현이 정확합니다. 같은 맥락과 같은 전제를 그대로 들고 자기 결과물을 보면, 처음에 그 결과물을 만들게 한 그 판단이 검토에도 그대로 작동합니다. 놓친 이유가 남아 있는 채로 다시 보는 셈입니다.


Critic은 신선한 관점으로 접근합니다. 오로지 오류와 개선점을 찾는 데만 배정된 역할이니까요. Critic의 피드백은 Producer에게 되돌아가고, Producer는 그것을 지침 삼아 새 버전을 만듭니다.


![Fig.2 — Reflection 디자인 패턴, Producer와 Critique 에이전트: 비평이 Producer에게 되돌아간다 (출처: Antonio Gulli, Agentic Design Patterns)](https://dhbang.co.kr/images/agentic-design-patterns/adp-ch4-fig2.png)


---


## 비평가를 만드는 것은 인격 설정이 아니라 판정 기준과 정지 신호입니다


"당신은 시니어 엔지니어입니다"라는 문장이 Critic을 만든다고 생각하기 쉽습니다. 페르소나는 입구일 뿐입니다. 루프를 실제로 굴리는 것은 세 가지입니다.


**첫째, 무엇을 볼지 정한 판정 기준입니다.** 책의 LangChain 예제에서 Critic은 버그, 스타일 문제, 누락된 엣지 케이스, 개선 여지를 원래 과제 요구사항에 비추어 보라는 지시를 받습니다. "잘 검토해 달라"가 아니라 볼 항목이 지정돼 있습니다.


**둘째, 구조화된 출력입니다.** ADK 예제의 Critic은 산문이 아니라 딕셔너리를 반환합니다. `status`는 `"ACCURATE"` 또는 `"INACCURATE"`, `reasoning`은 그 판정의 근거입니다. 판정과 근거가 분리돼 있으니 다음 단계가 프로그램으로 분기할 수 있습니다.


**셋째, 정지 신호입니다.** LangChain 예제의 Critic은 코드가 완벽하고 모든 요구사항을 만족하면 다른 말 없이 `CODE_IS_PERFECT`라는 문구 하나만 반환하도록 지시받습니다. 그 외의 경우에만 비평 목록을 냅니다.


세 번째가 도입부의 질문에 대한 절반의 답입니다. 루프는 "충분히 좋아졌으니 그만"이라고 스스로 판단해서 멈추지 않습니다. **멈추라고 말할 문구를 미리 정해 두었기 때문에** 멈춥니다.


---


## LangChain에서는 대화 이력 자체가 루프의 상태입니다


완전한 반복 리플렉션은 상태 관리와 순환 실행 장치가 필요합니다. LangGraph 같은 그래프 기반 프레임워크가 이를 기본 제공하지만, 한 사이클의 원리는 LCEL로도 충분히 드러납니다.


책의 예제는 팩토리얼 함수를 생성하고 정제하는 루프입니다. 핵심은 `message_history` 하나입니다.


```python
# 각 단계에 맥락을 제공하기 위해 대화 이력을 쌓아 나간다.
message_history = [HumanMessage(content=task_prompt)]

for i in range(max_iterations):
    # --- 1. 생성 / 정제 단계 ---
    if i == 0:
        # 첫 회차의 메시지는 과제 프롬프트뿐이다.
        response = llm.invoke(message_history)
        current_code = response.content
    else:
        # 이제 이력에는 과제, 직전 코드, 직전 비평이 들어 있다.
        message_history.append(
            HumanMessage(content="Please refine the code using the critiques provided.")
        )
        response = llm.invoke(message_history)
        current_code = response.content

    message_history.append(response)  # 생성된 코드를 이력에 추가
```


같은 `llm.invoke`가 첫 회차에는 생성기로, 이후 회차에는 정제기로 동작합니다. 프롬프트를 바꿔서가 아니라 **넘겨주는 이력이 달라져서**입니다. 이력에 비평이 들어 있으면 그 다음 호출은 자동으로 정제 작업이 됩니다. 루프의 상태가 별도 변수가 아니라 대화 이력 그 자체입니다.


비평 단계는 반대로 갑니다.


```python
reflector_prompt = [
    SystemMessage(content="""
        You are a senior software engineer and an expert in Python.
        Your role is to perform a meticulous code review.
        Critically evaluate the provided Python code based
        on the original task requirements.
        Look for bugs, style issues, missing edge cases,
        and areas for improvement.
        If the code is perfect and meets all requirements,
        respond with the single phrase 'CODE_IS_PERFECT'.
        Otherwise, provide a bulleted list of your critiques.
    """),
    HumanMessage(content=f"Original Task:\n{task_prompt}\n\nCode to Review:\n{current_code}")
]

critique_response = llm.invoke(reflector_prompt)
critique = critique_response.content

# --- 3. 정지 조건 ---
if "CODE_IS_PERFECT" in critique:
    break

# 다음 정제 회차를 위해 비평을 이력에 추가한다.
message_history.append(HumanMessage(content=f"Critique of the previous code:\n{critique}"))
```


`reflector_prompt`가 `message_history`와 **별개의 리스트**라는 점이 설계의 핵심입니다. Critic은 누적된 이력 밖에서 호출됩니다. 원래 과제와 검토 대상 코드만 받고, Producer가 어떤 사고 과정을 거쳐 그 코드에 도달했는지는 받지 않습니다. 앞 절에서 말한 신선한 관점이 코드 수준에서는 이렇게 구현됩니다. **맥락을 물려주지 않는 것**입니다.


그리고 비평 결과는 다시 `message_history`에 들어갑니다. 되돌아오는 경로가 여기서 닫힙니다.


한 바퀴를 끝까지 따라가면 이렇습니다. 과제 프롬프트가 들어가고, v1 코드가 나오고, 이력 밖의 Critic이 그것을 읽고 비평 목록을 만들고, 그 목록이 이력에 붙고, 같은 모델이 이력 전체를 보며 v2를 쓰고, 다시 Critic이 봅니다. `CODE_IS_PERFECT`가 나오면 `break`, 안 나오면 `max_iterations`에서 끊깁니다.


---


## ADK에서는 상태 키가 루프를 잇습니다


Google ADK는 같은 구조를 다른 방식으로 표현합니다. 대화 이력이 아니라 **상태 키(state key)** 로 두 에이전트를 잇습니다.


```python
from google.adk.agents import SequentialAgent, LlmAgent

# 첫 번째 에이전트가 초안을 만든다.
generator = LlmAgent(
    name="DraftWriter",
    description="Generates initial draft content on a given subject.",
    instruction="Write a short, informative paragraph about the user's subject.",
    output_key="draft_text"  # 출력이 이 상태 키에 저장된다.
)

# 두 번째 에이전트가 첫 번째의 초안을 비평한다.
reviewer = LlmAgent(
    name="FactChecker",
    description="Reviews a given text for factual accuracy and provides a structured critique.",
    instruction="""
    You are a meticulous fact-checker.
    1. Read the text provided in the state key 'draft_text'.
    2. Carefully verify the factual accuracy of all claims.
    3. Your final output must be a dictionary containing two keys:
       - "status": A string, either "ACCURATE" or "INACCURATE".
       - "reasoning": A string providing a clear explanation for your status,
         citing specific issues if any are found.
    """,
    output_key="review_output"  # 구조화된 딕셔너리가 여기 저장된다.
)

# SequentialAgent가 generator를 reviewer보다 먼저 실행하도록 보장한다.
review_pipeline = SequentialAgent(
    name="WriteAndReview_Pipeline",
    sub_agents=[generator, reviewer]
)
```


`output_key`는 지난 편에서 이미 만난 장치입니다. 병렬화에서는 동시에 달린 서브에이전트들의 결과를 각자의 칸에 담아 두었다가 합류 지점에서 모으는 **수집 채널**이었습니다. 여기서는 같은 장치가 **되먹임 채널**로 쓰입니다. `generator`가 `draft_text`에 쓰고, `reviewer`가 그것을 읽어 `review_output`에 판정을 씁니다.


패턴이 달라도 상태를 다루는 방식은 하나입니다. 에이전트끼리 직접 주고받지 않고 상태를 경유합니다. 그래서 순차·병렬·되먹임을 같은 문법으로 조립할 수 있습니다.


위 코드는 한 방향으로 한 번만 흐르는 파이프라인입니다. 진짜 반복이 필요하면 ADK의 `LoopAgent`를 쓰는 대안이 있다고 책은 덧붙입니다.


---


## 어디에 쓰는가


책이 드는 활용처는 출력 품질이나 정확성, 복잡한 제약 준수가 결정적인 경우에 몰려 있습니다.


| 영역        | 리플렉션이 하는 일                                            |
| --------- | ----------------------------------------------------- |
| 창작·콘텐츠 생성 | 초안을 만들고 흐름·톤·명료성을 비평한 뒤 다시 쓴다. 품질 기준을 만족할 때까지 반복      |
| 코드 생성·디버깅 | 초기 코드를 쓰고 테스트나 정적 분석을 돌려 오류·비효율을 찾은 뒤 수정              |
| 복잡한 문제 해결 | 한 단계를 제안하고, 해답에 가까워지는지 모순이 생기는지 평가한 뒤 되돌아가거나 다른 단계 선택 |
| 요약·정보 종합  | 초기 요약을 원문의 핵심 항목과 대조해 누락을 채우고 정확성을 높임                 |
| 계획·전략     | 계획을 세우고 실행을 시뮬레이션하거나 제약 대비 실현 가능성을 평가한 뒤 수정           |
| 대화형 에이전트  | 직전 대화와 마지막 응답을 검토해 일관성을 확인하고 오해를 바로잡음                 |


책은 리플렉션과 다른 장의 접점도 짚습니다. **목표 설정·모니터링**(11장)과 만나면 목표가 자기 평가의 기준점을 제공하고, 리플렉션은 관측된 편차를 분석해 전략을 조정하는 교정 엔진 역할을 합니다. **메모리**(8장)와 만나면 성격이 더 크게 달라집니다. 메모리가 없으면 매 리플렉션은 그 자리에서 끝나는 독립 사건이지만, 메모리가 있으면 각 사이클이 앞 사이클 위에 쌓이는 누적 과정이 됩니다. 지난 비평에서 배우고 같은 실수를 반복하지 않게 됩니다.


---


## 리플렉션은 품질을 토큰과 지연으로 삽니다


책은 결론에 앞서 트레이드오프를 분명히 합니다.


**첫째, 매 정제 회차가 새 LLM 호출입니다.** 반복 과정은 강력하지만 비용과 지연을 함께 늘립니다. 책은 시간에 민감한 애플리케이션에는 최적이 아니라고 못 박습니다. 사용자가 응답을 기다리고 있는 자리에 3회전 루프를 넣으면, 품질은 올라가도 체감은 나빠집니다.


**둘째, 메모리를 많이 씁니다.** 반복할 때마다 대화 이력이 팽창합니다. 초기 출력, 비평, 그 다음 정제본이 차곡차곡 쌓이니까요. 앞서 본 LangChain 예제에서 `message_history`가 계속 `append`되기만 하고 줄어들지 않는다는 점을 떠올리면 됩니다.


**셋째, 그래서 모델의 컨텍스트 윈도우를 넘길 위험과 API 스로틀링에 걸릴 위험이 함께 커집니다.** 책이 핵심 정리에서 명시하는 비용입니다. 루프를 오래 돌수록 위험이 커지는데, 정작 루프를 오래 돌고 싶어지는 상황은 결과가 잘 안 나올 때입니다. 위험과 유혹이 같은 방향을 봅니다.


책의 판단 기준(Rule of thumb)은 간명합니다. **최종 출력의 품질·정확성·디테일이 속도와 비용보다 중요할 때** 리플렉션을 씁니다. 다듬어진 장문 콘텐츠, 코드 작성과 디버깅, 상세한 계획 수립이 대표적입니다. 그리고 높은 객관성이나 전문적 평가가 필요할 때, 즉 범용 Producer가 놓칠 만한 것을 봐야 할 때 별도의 Critic 에이전트를 씁니다.


뒤집으면 이렇습니다. 응답 속도가 중요한 곳, 첫 출력으로 충분한 단순 작업, 평가 기준을 명확히 적을 수 없는 작업에는 넣지 않는 편이 낫습니다. 마지막 항목이 특히 중요합니다. 무엇을 볼지 지정하지 못하면 Critic은 판정 기준 없이 도는 추가 호출일 뿐입니다.


---


## 정리


| 항목        | 내용                                                                                                              |
| --------- | --------------------------------------------------------------------------------------------------------------- |
| 문제 (What) | 에이전트의 첫 출력은 부정확하거나 불완전한 경우가 많은데, 기본 워크플로에는 자기 오류를 인식하고 고칠 절차가 없다                                                |
| 해법 (Why)  | 실행 → 평가·비평 → 정제로 이어지는 피드백 루프를 둔다. 비평을 근거로 개선된 버전을 만드는 과정을 반복해 품질을 끌어올린다                                         |
| 핵심 구현     | Producer-Critic 모델. 생성과 평가를 다른 역할에 맡겨 자기 검토의 인지 편향을 피하고, 구조화된 피드백을 얻는다                                          |
| 멈추는 장치    | 최대 반복 횟수와 명시적 정지 신호(`CODE_IS_PERFECT`, `status: "ACCURATE"`)                                                    |
| 도구        | LangChain LCEL(대화 이력이 곧 상태) · LangGraph(상태 기반 순환) · Google ADK(SequentialAgent + `output_key`, 반복은 `LoopAgent`) |
| 비용        | 회차마다 LLM 호출 추가로 비용·지연 증가, 이력 팽창, 컨텍스트 윈도우 초과와 API 스로틀링 위험                                                       |
| 언제 쓰나     | 품질·정확성·디테일이 속도·비용보다 중요할 때. 객관성이나 전문 평가가 필요하면 Critic을 분리                                                         |


처음의 질문으로 돌아갑니다. 이 루프는 언제 멈추는가.


리플렉션에서 답의 품질을 결정하는 것은 얼마나 잘 비평하느냐만이 아닙니다. **무엇을 보고 언제 멈출지를 미리 적어 두었느냐**입니다. 판정 기준이 없으면 비평은 늘어나기만 하고, 정지 신호가 없으면 루프는 예산이 떨어질 때까지 돕니다. 되돌아오는 경로를 만드는 일은 곧 그 경로를 끊는 조건을 만드는 일입니다.


체인이 순서를, 라우팅이 선택을, 병렬화가 속도를 줬다면 리플렉션은 **고쳐 쓸 기회**를 줍니다. 다음 편은 에이전트가 자기 머릿속 밖으로 손을 뻗는 이야기입니다. 외부 도구를 호출해 실제 세계와 상호작용하는 Tool Use입니다.


---


## 참고

- Antonio Gulli, _Agentic Design Patterns: A Hands-On Guide to Building Intelligent Systems_, Springer, 2025 — Chapter 4: Reflection
- [Training Language Models to Self-Correct via Reinforcement Learning](https://arxiv.org/abs/2409.12917)
- [LangChain Expression Language (LCEL) Documentation](https://python.langchain.com/docs/introduction/)
- [LangGraph Documentation](https://www.langchain.com/langgraph)
- [Google ADK Documentation — Multi-Agent Systems](https://google.github.io/adk-docs/agents/multi-agents/)
