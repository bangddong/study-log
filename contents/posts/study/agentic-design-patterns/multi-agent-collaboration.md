---
title: '분업의 성패는 통신이 가른다. Multi-Agent Collaboration, 하나의 목표를 여러 에이전트에 나눠 맡기는 법'
date: '2026-09-02'
tags:
  - AI
series: Agentic Design Patterns
emoji: "\U0001F91D"
---
> Antonio Gulli, _Agentic Design Patterns_(Google / Springer)의 7장 "Multi-Agent Collaboration"을 정리합니다.
> [지난 편](https://dhbang.co.kr/posts/study/agentic-design-patterns/planning/) Planning이 "목표에서 단계를 만들어 내는 법"이었다면, 이번 편은 "그 단계들을 서로 다른 에이전트에게 나눠 맡기는 법"입니다.

---


## 도구를 스무 개 붙인 에이전트가 엉뚱한 도구를 고릅니다


에이전트 하나에 일을 계속 얹어 본 적이 있으신가요. 처음에는 검색만 시켰습니다. 그다음 결과를 표로 정리하게 했고, 사내 DB도 조회하게 했고, 마지막에 리포트까지 쓰게 했습니다. 시스템 프롬프트는 스크롤을 세 번 내려야 끝나고 도구 목록은 스무 개가 넘습니다.


그러다 어느 순간부터 이상해집니다. 통계 조회를 시켰는데 웹 검색을 돌리고, 리포트 형식을 앞에서 지정해 뒀는데 무시합니다. 지시가 틀린 것이 아니라 지시가 너무 많습니다.


6장에서 에이전트는 목표를 받아 단계의 목록을 만들어 냈습니다. 그 목록을 보면 각 단계가 요구하는 것이 서로 다릅니다. 검색은 웹 도구가 필요하고, 통계는 코드 실행이 필요하고, 작성은 문체 지시가 필요합니다. 7장의 질문은 여기서 시작합니다. 이 단계들을 전부 한 에이전트가 해야 하는가.


책은 아니라고 답한 다음, 곧바로 조건을 붙입니다.

> 이런 시스템의 효능은 단순히 분업에서 오는 것이 아니라, 에이전트 사이의 통신 메커니즘에 결정적으로 달려 있습니다.

나누는 것은 시작일 뿐이라는 뜻입니다. 이 글을 관통하는 질문은 그래서 하나입니다.

> 나눈 다음, 그 사이로 무엇이 흐르는가?

---


## 멀티 에이전트는 에이전트를 여럿 두는 일이 아니라 셋을 설계하는 일입니다


멀티 에이전트 협업(Multi-Agent Collaboration)은 에이전트의 개수를 늘리는 패턴이 아닙니다. 책은 시스템의 구성 요소를 세 가지로 못 박습니다.

1. **역할과 책임의 획정.** 어떤 에이전트가 무엇을 맡는가.
2. **통신 채널의 확립.** 정보가 어느 통로로 오가는가.
3. **작업 흐름 또는 상호작용 규약의 수립.** 협업의 순서를 무엇이 지시하는가.

에이전트를 세 개 만들어 놓고 두 번째와 세 번째를 정하지 않으면 그것은 멀티 에이전트 시스템이 아니라 서로를 모르는 에이전트 세 개입니다.


![Fig.1 — 멀티 에이전트 팀의 예. 사용자와 대화하는 것은 Supervisor 하나뿐이고, 그 아래 Specialist들이 다시 하위 에이전트를 거느린다 (출처: Antonio Gulli, Agentic Design Patterns)](https://dhbang.co.kr/images/agentic-design-patterns/adp-ch7-fig1.png)


도식에서 눈여겨볼 것은 사용자와 팀 사이에 걸린 화살표가 하나뿐이라는 점입니다. 사용자는 Supervisor하고만 이야기합니다. Specialist들은 사용자를 모릅니다. 그리고 오른쪽 Specialist 아래에 다시 두 개가 붙어 있습니다. 계층은 한 단으로 끝나지 않습니다.


이 구조가 왜 이득인지도 책은 명시합니다. 모듈성, 확장성, 그리고 **견고성**입니다. 에이전트 하나가 실패해도 시스템 전체가 반드시 무너지지는 않습니다. 앞의 둘은 설계상의 편의지만 견고성은 성격이 다릅니다. 하나의 거대 에이전트에서는 실패가 곧 전체 실패인데, 여기서는 실패의 범위가 경계 안에 갇힙니다.


---


## 협업의 형태는 결과를 누가 합치느냐로 갈립니다


책은 협업의 형태를 여섯 가지로 나열합니다. 나열만 보면 비슷해 보이지만, 결과를 합치는 주체를 기준으로 놓으면 구분이 선명해집니다.


| 형태                              | 흐름                                        | 결과를 합치는 주체                    |
| ------------------------------- | ----------------------------------------- | ----------------------------- |
| 순차 인계 (Sequential Handoffs)     | 한 에이전트의 출력이 다음 에이전트의 입력이 된다               | 합칠 것이 없다. 마지막 에이전트의 출력이 곧 결과다 |
| 병렬 처리 (Parallel Processing)     | 여러 에이전트가 문제의 다른 부분을 동시에 처리한다              | 나중에 결과를 결합하는 별도의 자리가 필요하다     |
| 토론과 합의 (Debate and Consensus)   | 관점과 정보원이 다른 에이전트들이 선택지를 놓고 논의한다           | 에이전트들 자신이 합의에 도달한다            |
| 계층 구조 (Hierarchical Structures) | 매니저 에이전트가 도구 접근 권한에 따라 동적으로 작업을 위임한다      | 매니저가 결과를 종합한다                 |
| 전문가 팀 (Expert Teams)            | 연구자·작성자·편집자처럼 도메인 지식이 다른 에이전트들이 협업한다      | 파이프라인의 마지막 역할이 맡는다            |
| 비평-검토 (Critic-Reviewer)         | 한 그룹이 초안을 만들고 다른 그룹이 정책·보안·정확성을 기준으로 평가한다 | 원저자나 최종 에이전트가 피드백을 반영해 수정한다   |


순차 인계는 6장의 계획 패턴과 흐름이 같습니다. 차이는 각 단계를 **명시적으로 서로 다른 에이전트가** 맡는다는 점뿐이라고 책은 덧붙입니다.


여섯 개 중에서 책이 유독 길게 설명하는 것은 비평-검토입니다. 코드 생성, 리서치 작성, 논리 검사, 윤리적 정렬 확인에 특히 효과적이고, 이점으로 견고성 향상과 품질 개선, 그리고 **환각과 오류의 가능성 감소**를 듭니다.


여기서 4장의 리플렉션과 겹쳐 보입니다. 생성하고, 비평하고, 고쳐 쓰는 순환은 같습니다. 달라진 것은 비평하는 쪽이 같은 모델의 다른 턴이 아니라 **다른 에이전트**라는 점입니다. 자기 출력을 자기가 검토할 때의 구조적 한계, 즉 만든 근거와 검토하는 근거가 같다는 문제를 역할 분리로 밀어내려는 시도입니다.


계층 구조 설명에는 짧지만 실용적인 문장이 하나 섞여 있습니다.

> 각 에이전트는 모든 도구를 한 에이전트가 다루는 대신, 관련된 도구들의 묶음을 맡을 수도 있습니다.

도입부의 장면이 여기서 해소됩니다. 도구 스무 개를 한 에이전트에 붙이는 대신 다섯 개씩 네 에이전트에 나누면, 각 에이전트가 매번 고려해야 할 선택지가 넷으로 줍니다.


---


## 통신 구조는 조정 권한을 어디에 두느냐의 스펙트럼입니다


책은 통신 모델을 여섯 가지로 정리하고 도식 하나에 모아 둡니다. 이 여섯은 병렬적인 선택지가 아니라 **조정 권한이 흩어져 있는 정도**에 따라 늘어선 스펙트럼입니다.


![Fig.2 — 에이전트가 상호작용하고 통신하는 여러 방식. Single Agent에서 Custom까지 여섯 가지 모델 (출처: Antonio Gulli, Agentic Design Patterns)](https://dhbang.co.kr/images/agentic-design-patterns/adp-ch7-fig2.png)


| 모델                    | 조정 권한                                    | 책이 인정한 약점                     |
| --------------------- | ---------------------------------------- | ----------------------------- |
| Single Agent          | 없음. 단일 에이전트가 자율적으로 동작한다                  | 개별 에이전트의 범위와 자원이 곧 한계다        |
| Network               | 완전히 분산. 피어 투 피어로 직접 주고받는다                | 통신 오버헤드 관리와 일관된 의사결정이 어렵다     |
| Supervisor            | 한 곳에 집중. 감독자가 통신·할당·충돌 해결의 허브다           | 단일 실패 지점이고, 하위가 많아지면 병목이 된다   |
| Supervisor (as Tools) | 집중되어 있으나 명령이 아니라 지원. 도구·데이터·연산 서비스를 제공한다 | 위에서 아래로 찍어 누르지 않는 대신 통제력도 약하다 |
| Hierarchical          | 계층별로 분할. 상위 감독자가 하위 감독자를 관리한다            | 정의된 경계 안에서만 분산 의사결정이 성립한다     |
| Custom                | 임의로 설계. 하이브리드거나 완전히 새로운 구조다              | 멀티 에이전트 원리에 대한 깊은 이해가 필요하다    |


Supervisor 항목의 약점이 특히 눈에 띕니다. 단일 실패 지점이라는 지적은 앞 절에서 멀티 에이전트의 이점으로 내세운 견고성과 정면으로 부딪힙니다. **에이전트를 나눠서 얻은 견고성을 감독자 하나가 도로 반납합니다.** 나누는 것과 튼튼해지는 것은 자동으로 이어지지 않습니다.


Supervisor as a Tool은 이름이 헷갈리기 쉬운데, 감독자를 도구로 쓴다는 뜻이 아닙니다. 감독자의 역할이 직접적인 지휘 통제보다 **자원·안내·분석 지원 제공**에 가까워진 형태입니다. 다른 에이전트가 일을 더 잘하게 만들되 매 행동을 지시하지는 않습니다.


책은 마지막에 선택 기준을 나열합니다. 작업의 복잡도, 에이전트의 수, 원하는 자율성 수준, 견고성 요구, 그리고 **감내할 수 있는 통신 오버헤드**입니다. 앞의 넷은 얻고 싶은 것이고 마지막 하나는 내야 하는 것입니다.


---


## CrewAI는 역할이 아니라 컨텍스트로 에이전트를 잇습니다


책의 CrewAI 예제는 AI 트렌드 블로그 글을 만드는 2인 팀입니다. 역할 정의부터 봅니다.


```python
researcher = Agent(
   role='Senior Research Analyst',
   goal='Find and summarize the latest trends in AI.',
   backstory="You are an experienced research analyst with a knack for identifying key trends and synthesizing information.",
   verbose=True,
   allow_delegation=False,
)

writer = Agent(
   role='Technical Content Writer',
   goal='Write a clear and engaging blog post based on research findings.',
   backstory="You are a skilled writer who can translate complex technical topics into accessible content.",
   verbose=True,
   allow_delegation=False,
)
```


`role`, `goal`, `backstory` 세 필드가 앞 절에서 말한 **역할과 책임의 획정**입니다. 그런데 이것만으로는 둘이 이어지지 않습니다. 두 에이전트는 서로의 존재를 모릅니다. `allow_delegation=False`라서 서로에게 일을 넘길 수도 없습니다.


연결은 태스크 쪽에 있습니다.


```python
research_task = Task(
   description="Research the top 3 emerging trends in Artificial Intelligence in 2024-2025. ...",
   expected_output="A detailed summary of the top 3 AI trends, including key points and sources.",
   agent=researcher,
)

writing_task = Task(
   description="Write a 500-word blog post based on the research findings. ...",
   expected_output="A complete 500-word blog post about the latest AI trends.",
   agent=writer,
   context=[research_task],
)
```


`context=[research_task]` 한 줄이 통신 채널입니다. writer는 researcher를 호출하지 않습니다. researcher가 만든 **결과물**을 컨텍스트로 받을 뿐입니다.


이 설계의 함의가 큽니다. 두 에이전트는 대화하지 않습니다. 한쪽이 끝낸 결과가 다른 쪽의 입력이 되는 단방향 전달입니다. writer가 리서치 내용에 의문이 생겨도 되물을 상대가 없습니다.


`expected_output`이 그래서 중요해집니다. 되물을 수 없다면 넘어가는 것의 형식을 미리 합의해 두는 수밖에 없습니다. 이것이 책 서두에서 말한 **표준화된 통신 규약과 공유된 온톨로지**의 가장 소박한 구현입니다.


마지막으로 흐름을 정의합니다.


```python
blog_creation_crew = Crew(
   agents=[researcher, writer],
   tasks=[research_task, writing_task],
   process=Process.sequential,
   llm=llm,
   verbose=2  # 실행 로그를 상세히 남긴다
)

result = blog_creation_crew.kickoff()
```


`process=Process.sequential`이 **상호작용 규약**입니다. 순서는 코드에 적혀 있고 에이전트가 정하지 않습니다. 6장에서 계획을 만들어 내던 자율성이 여기서는 조정 층으로 올라가지 않았습니다. 각 에이전트는 자기 태스크 안에서만 자율적입니다.


---


## ADK는 조정 방식을 프롬프트가 아니라 클래스로 굳혔습니다


Google ADK 예제들은 CrewAI와 접근이 다릅니다. 조정 방식마다 **전용 에이전트 타입**이 있습니다.


먼저 계층 구조입니다.


```python
greeter = LlmAgent(
   name="Greeter",
   model="gemini-2.0-flash-exp",
   instruction="You are a friendly greeter."
)
task_doer = TaskExecutor()  # BaseAgent를 상속한 비-LLM 에이전트

coordinator = LlmAgent(
   name="Coordinator",
   model="gemini-2.0-flash-exp",
   description="A coordinator that can greet users and execute tasks.",
   instruction="When asked to greet, delegate to the Greeter. When asked to perform a task, delegate to the TaskExecutor.",
   sub_agents=[
       greeter,
       task_doer
   ]
)

assert greeter.parent_agent == coordinator
assert task_doer.parent_agent == coordinator
```


`sub_agents`에 넣기만 하면 부모-자식 관계가 자동으로 맺힙니다. 그런데 **위임 판단 자체는** **`instruction`** **문자열에 들어 있습니다.** "인사를 요청받으면 Greeter에게, 작업 수행을 요청받으면 TaskExecutor에게 위임하라"는 자연어입니다. 구조는 코드로 고정되어 있지만 그 구조를 타고 흐르는 판단은 프롬프트에 맡겨져 있습니다.


`task_doer`가 `LlmAgent`가 아니라 `BaseAgent` 상속이라는 점도 짚을 만합니다. 멀티 에이전트 시스템의 구성원 전부가 LLM일 필요는 없습니다.


```python
class TaskExecutor(BaseAgent):
   """A specialized agent with custom, non-LLM behavior."""
   name: str = "TaskExecutor"
   description: str = "Executes a predefined task."

   async def _run_async_impl(self, context: InvocationContext) -> AsyncGenerator[Event, None]:
       # 여기에 실제 로직이 들어간다. 예제에서는 이벤트 하나만 내보낸다.
       yield Event(author=self.name, content="Task finished successfully.")
```


반면 순차·병렬·반복은 판단을 프롬프트에 맡기지 않습니다.


```python
step1 = Agent(name="Step1_Fetch", output_key="data")

step2 = Agent(
   name="Step2_Process",
   instruction="Analyze the information found in state['data'] and provide a summary."
)

pipeline = SequentialAgent(
   name="MyPipeline",
   sub_agents=[step1, step2]
)
```


`SequentialAgent`는 순서를 코드로 확정합니다. 그리고 통신 채널의 정체가 여기서 드러납니다. `output_key="data"`로 저장된 값을 다음 에이전트가 `state['data']`로 읽습니다. **두 에이전트는 서로를 호출하지 않고 세션 상태를 거칩니다.**


병렬도 같은 방식입니다.


```python
weather_fetcher = Agent(
   name="weather_fetcher",
   model="gemini-2.0-flash-exp",
   instruction="Fetch the weather for the given location and return only the weather report.",
   output_key="weather_data"  # 결과는 session.state["weather_data"]에 저장된다
)

news_fetcher = Agent(
   name="news_fetcher",
   model="gemini-2.0-flash-exp",
   instruction="Fetch the top news story for the given topic and return only that story.",
   output_key="news_data"
)

data_gatherer = ParallelAgent(
   name="data_gatherer",
   sub_agents=[
       weather_fetcher,
       news_fetcher
   ]
)
```


`output_key`가 서로 달라야 한다는 점이 병렬의 조건입니다. 같은 키를 쓰면 덮어씁니다. 3장 병렬화에서 결과를 어디에 모을지 정하던 문제가 여기서는 키 이름 문제로 나타납니다.


반복 구조는 종료 조건이 별도의 에이전트입니다.


```python
class ConditionChecker(BaseAgent):
   """A custom agent that checks for a 'completed' status in the session state."""
   name: str = "ConditionChecker"
   description: str = "Checks if a process is complete and signals the loop to stop."

   async def _run_async_impl(self, context: InvocationContext) -> AsyncGenerator[Event, None]:
       status = context.session.state.get("status", "pending")
       is_done = (status == "completed")

       if is_done:
           # 조건이 충족되면 escalate로 루프를 끝낸다
           yield Event(author=self.name, actions=EventActions(escalate=True))
       else:
           yield Event(author=self.name, content="Condition not met, continuing loop.")

poller = LoopAgent(
   name="StatusPoller",
   max_iterations=10,
   sub_agents=[
       process_step,
       ConditionChecker()
   ]
)
```


`max_iterations=10`이 있습니다. 종료 조건을 에이전트에게 맡기면서도 상한은 코드가 잡습니다. 4장 리플렉션에서 루프에 상한을 두던 것과 같은 대비입니다.


정리하면 ADK는 조정 방식을 두 층으로 나눠 놓았습니다.


| 층        | 무엇이 결정하는가            | 예                                                                 |
| -------- | -------------------- | ----------------------------------------------------------------- |
| 흐름의 골격   | 코드. 클래스 선택으로 확정된다    | `SequentialAgent`, `ParallelAgent`, `LoopAgent`, `max_iterations` |
| 흐름 안의 판단 | 프롬프트. 실행 시점에 모델이 정한다 | `LlmAgent`의 `instruction`에 적힌 위임 규칙, 루프 종료 여부                     |


**흔들려도 되는 것만 프롬프트에 남겨 두는 설계입니다.**


---


## Agent as a Tool은 위임을 호출로 바꿔 제어권을 돌려받습니다


마지막 예제가 5장 도구 사용과 이번 장을 잇습니다.


```python
image_generator_agent = LlmAgent(
   name="ImageGen",
   model="gemini-2.0-flash",
   description="Generates an image based on a detailed text prompt.",
   instruction=(
       "You are an image generation specialist. Your task is to take the user's request "
       "and use the `generate_image` tool to create the image. ..."
   ),
   tools=[generate_image]
)

image_tool = agent_tool.AgentTool(
   agent=image_generator_agent,
   description="Use this tool to generate an image. The input should be a descriptive prompt of the desired image."
)

artist_agent = LlmAgent(
   name="Artist",
   model="gemini-2.0-flash",
   instruction=(
       "You are a creative artist. First, invent a creative and descriptive prompt for an image. "
       "Then, use the `ImageGen` tool to generate the image using your prompt."
   ),
   tools=[image_tool]
)
```


`AgentTool`이 에이전트를 도구로 감쌉니다. artist는 image_generator를 하위 에이전트로 두지 않고 **도구 목록에** 넣습니다.


이 차이가 겉보기보다 큽니다. `sub_agents`로 위임하면 제어권이 넘어갑니다. 하위 에이전트가 사용자와 이어진 대화를 이어받습니다. `AgentTool`로 호출하면 제어권이 돌아옵니다. 함수 호출처럼 값을 받아 자기 흐름을 계속합니다.


Fig.2의 "Supervisor (as Tools)"가 도식에서 뜻하던 것이 여기서 코드로 나타납니다. 감독자가 아래로 명령을 내려보내고 손을 떼는 것이 아니라, 필요한 것을 불러 쓰고 결과를 자기가 안고 갑니다.


`AgentTool`에 붙은 `description`도 눈여겨볼 자리입니다. 주석에 이렇게 적혀 있습니다.


```python
# The description here is what the parent agent sees.
```


부모가 보는 것은 하위 에이전트의 `instruction`이 아니라 이 `description`입니다. 5장에서 도구의 독스트링이 모델이 보는 계약이었던 것과 정확히 같은 구조입니다. **에이전트를 도구로 감싸는 순간 그 안쪽은 부모에게 불투명해집니다.**


책은 이 예제를 "계층적 에이전트 시스템"이라고 부르지만, 계층이라는 말이 앞의 `sub_agents` 예제와 다른 것을 가리킵니다. 앞에서는 조직도의 계층이었고 여기서는 호출 스택의 계층입니다.


---


## 어디에 쓰는가


![Fig.3 — 멀티 에이전트 디자인 패턴. 프롬프트가 에이전트 묶음으로 들어가고 출력이 사용자를 거쳐 다시 프롬프트로 돌아온다 (출처: Antonio Gulli, Agentic Design Patterns)](https://dhbang.co.kr/images/agentic-design-patterns/adp-ch7-fig3.png)


도식 아래 각주가 이 패턴의 조건을 한 줄로 적어 둡니다. "에이전트는 여러 에이전트와 연결될 수 있다." 상자 안에 에이전트를 늘어놓는 것만으로는 부족하고, 그 사이의 연결이 이 패턴의 내용입니다.


| 영역           | 나누는 기준    | 팀 구성                                      |
| ------------ | --------- | ----------------------------------------- |
| 복잡한 리서치·분석   | 조사 단계별    | 학술 DB 검색 · 결과 요약 · 트렌드 식별 · 리포트 종합        |
| 소프트웨어 개발     | 개발 공정별    | 요구사항 분석 · 코드 생성 · 테스트 · 문서 작성             |
| 창작 콘텐츠 생성    | 제작 직무별    | 시장 조사 · 카피라이팅 · 이미지 생성 · 소셜 미디어 스케줄링      |
| 금융 분석        | 분석 방법론별   | 주가 데이터 수집 · 뉴스 감성 분석 · 기술적 분석 · 투자 추천 생성  |
| 고객 지원 에스컬레이션 | 문제 난이도별   | 1차 응대 담당이 복잡한 건을 기술·과금 전문가에게 넘긴다          |
| 공급망 최적화      | 조직 노드별    | 공급자 · 제조사 · 유통사가 각각 에이전트가 되어 재고와 물류를 조율한다 |
| 네트워크 분석·복구   | 장애 처리 단계별 | 여러 에이전트가 협업해 트리아지하고 최적 조치를 제안한다           |


앞의 넷은 나누는 기준이 **작업**이고, 뒤의 셋은 기준이 **원래 존재하던 조직 구조**입니다. 공급망은 공급자와 제조사가 이미 나뉘어 있어서 에이전트로도 나뉩니다. 고객 지원의 에스컬레이션도 사람 조직에 이미 있던 경계입니다.


네트워크 복구 사례에는 조건 하나가 더 붙습니다. 이 에이전트들이 **기존 머신러닝 모델과 툴링에 통합될 수 있어야** 한다고 책은 씁니다. 멀티 에이전트로 갈아엎는 것이 아니라 이미 있는 시스템을 살리면서 생성형 AI의 이점을 얹는 방식입니다.


---


## 나누는 순간 통신이 비용이 됩니다


책에 독립된 한계 섹션은 없습니다. 대신 통신 모델을 하나씩 설명하면서 각각의 약점을 그 자리에 적어 두었습니다. 모아 보면 방향이 하나로 모입니다. **분업으로 아낀 것을 통신으로 다시 냅니다.**


**첫째, 조정자는 이점이자 취약점입니다.** 책이 직접 쓴 비용입니다. Supervisor 모델은 명확한 지휘 계통을 주지만 단일 실패 지점을 만들고, 하위 에이전트가 많거나 작업이 복잡해지면 병목이 됩니다. 나눠서 얻은 견고성이 조정자 한 곳에서 상쇄됩니다.


**둘째, 조정자를 없애면 통신 오버헤드가 대신 옵니다.** Network 모델의 약점으로 책이 적은 것은 통신 오버헤드 관리와 일관된 의사결정입니다. 에이전트가 n개면 통로는 최대 n(n-1)/2개입니다. 조정 권한을 흩뿌린 대가는 그 통로들을 누가 감당하느냐입니다.


**셋째, 컨텍스트가 경계에서 잘립니다.** CrewAI의 `context=[research_task]`도 ADK의 `state['data']`도 넘어가는 것은 **최종 산출물**입니다. researcher가 검색 중에 본 것 중에 요약에 담기지 않은 정보는 writer에게 도달하지 않습니다. 한 에이전트 안이었다면 같은 컨텍스트에 남아 있었을 것들입니다. 나눈다는 것은 그 사이에 정보 손실 지점을 하나 만든다는 뜻입니다.


**넷째, 역할을 나눈다고 능력이 나뉘지는 않습니다.** 예제의 researcher와 writer는 같은 `gemini-2.0-flash`입니다. 다른 것은 `role`과 `backstory` 문자열뿐입니다. 전문가 팀이라는 말은 은유이고, 실제로 갈린 것은 프롬프트입니다. 비평-검토가 환각을 줄인다는 기대도 여기서 조심스러워집니다. 검토자가 생성자와 같은 모델이면 같은 오류를 그럴듯하다고 판단할 수 있습니다.


**다섯째, 실패 지점이 곱으로 늘어납니다.** 결과가 틀렸을 때 원인은 이제 세 곳입니다. 어느 에이전트가 틀렸거나, 넘기는 형식이 어긋났거나, 조정 판단이 틀렸거나. 6장에서 계획과 실행 둘을 갈라야 했다면 여기서는 에이전트 수만큼 갈라야 합니다. `verbose=2`가 예제에 들어 있는 이유입니다.


**여섯째, 설계 비용이 사람에게 남습니다.** 책은 Custom 모델을 설명하며 "멀티 에이전트 시스템 원리에 대한 깊은 이해와 통신 프로토콜·조정 메커니즘·창발적 행동에 대한 신중한 고려가 필요하다"고 씁니다. 유연성의 대가를 프레임워크가 아니라 설계자가 낸다는 인정입니다.


책의 판단 기준(Rule of thumb)은 조건 두 개를 붙여 둡니다. **단일 에이전트가 감당하기에 너무 복잡하고**, 그리고 **특화된 기술이나 도구를 요구하는 별개의 하위 작업으로 분해될 수 있을 때**입니다.


뒤 조건이 실질적인 문턱입니다. 복잡하기만 하고 깨끗하게 분해되지 않는 일에 에이전트를 여럿 붙이면, 얻는 것은 전문성이 아니라 경계마다 생기는 손실입니다.


---


## 정리


| 항목        | 내용                                                                                                                                                                                                                      |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 문제 (What) | 복잡한 문제는 단일 에이전트의 능력을 넘어선다. 다양한 특화 기술이나 특정 도구 접근이 모자라 병목이 생기고, 다영역 목표에서 불완전하거나 차선의 결과가 나온다                                                                                                                               |
| 해법 (Why)  | 문제를 하위 문제로 분해하고 각각에 맞는 도구와 능력을 가진 전문 에이전트를 배정한다. 순차 인계·병렬 처리·계층적 위임 같은 상호작용 모델과 통신 규약으로 이들을 잇는다                                                                                                                         |
| 구성 요소     | 역할과 책임의 획정 · 통신 채널의 확립 · 작업 흐름과 상호작용 규약의 수립. 셋 중 하나라도 없으면 서로를 모르는 에이전트 묶음이다                                                                                                                                             |
| 결정적 조건    | 효능은 분업 자체가 아니라 에이전트 사이의 통신 메커니즘에 달려 있다                                                                                                                                                                                  |
| 통신 모델     | Single · Network(분산, 오버헤드) · Supervisor(집중, 단일 실패 지점) · Supervisor as Tools(지원형) · Hierarchical(다층) · Custom(설계 비용은 사람 몫)                                                                                               |
| 사례        | CrewAI(`role`·`goal`·`backstory`로 역할, `context=[...]`로 연결, `Process.sequential`로 흐름) · Google ADK(`sub_agents`로 위임, `SequentialAgent`·`ParallelAgent`·`LoopAgent`로 골격 고정, `output_key`와 세션 상태로 통신, `AgentTool`로 호출형 위임) |
| 비용        | 조정자는 병목이자 단일 실패 지점, 조정자를 없애면 통신 오버헤드, 경계마다 컨텍스트 손실, 역할 분리가 능력 분리는 아님, 실패 지점 증가, 설계 비용은 사람 몫                                                                                                                             |
| 언제 쓰나     | 단일 에이전트에 벅찰 만큼 복잡하고, 특화된 기술이나 도구를 요구하는 별개의 하위 작업으로 분해될 때                                                                                                                                                                |


처음의 질문으로 돌아갑니다. 나눈 다음, 그 사이로 무엇이 흐르는가.


예제들이 내놓은 답은 소박합니다. CrewAI는 앞 태스크의 결과물을 컨텍스트에 넣고, ADK는 세션 상태에 키를 하나 만듭니다. 에이전트끼리 대화하지 않습니다. 한쪽이 남긴 것을 다른 쪽이 읽습니다.


그래서 멀티 에이전트 설계에서 실제로 결정해야 하는 것은 에이전트의 개수나 역할 이름이 아닙니다. **경계를 넘어갈 것의 형식**입니다. `expected_output`과 `output_key`가 그 자리이고, 나머지는 그 형식을 잘 채우기 위한 장치입니다.


체인이 순서를, 라우팅이 선택을, 병렬화가 속도를, 리플렉션이 고쳐 쓸 기회를, 도구 사용이 바깥에 닿을 손을, 계획이 순서를 만들 권한을 줬다면 멀티 에이전트는 **경계**를 줍니다. 그리고 경계가 생기면 그 너머를 어떻게 다룰지가 다음 문제가 됩니다. 책도 같은 방향으로 장을 닫습니다.

> 에이전트의 협업을 이해하고 나면 자연스럽게 이들이 외부 환경과 어떻게 상호작용하는지에 대한 질문으로 이어집니다.

---


## 참고

- Antonio Gulli, _Agentic Design Patterns: A Hands-On Guide to Building Intelligent Systems_, Springer, 2025 — Chapter 7: Multi-Agent Collaboration
- [Multi-Agent Collaboration Mechanisms: A Survey of LLMs (arXiv:2501.06322)](https://arxiv.org/abs/2501.06322)
- [Multi-Agent System — The Power of Collaboration](https://aravindakumar.medium.com/introducing-multi-agent-frameworks-the-power-of-collaboration-e9db31bba1b6)
- [CrewAI Documentation](https://docs.crewai.com/)
- [Google Agent Development Kit (ADK) Documentation](https://google.github.io/adk-docs/)
