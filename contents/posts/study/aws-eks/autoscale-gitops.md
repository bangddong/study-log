---
title: '자동화 둘이 같은 칸을 쓰면 싸운다. EKS 실습기 ⑫, 번외 오토스케일과 GitOps 맛보기'
date: '2026-11-22'
tags:
  - AWS
  - EKS
series: AWS EKS 실습기
emoji: ''
---
> **AWS 프리티어 \$200으로 EKS 실습하기 ⑫** · 번외 · 💰 이 편은 읽는 편이라 **\$0**, 원본에서 재현을 뺀 여덟 번에 정가로 약 **\$1.9**

⑪편까지 클러스터에서 일어난 일은 전부 사람이 쳤습니다. 파드를 늘리고 싶으면 `kubectl scale`을 쳤고 배포할 때마다 `sed`로 이미지 태그를 바꿔 `kubectl apply`에 넘겼습니다. 로그를 보려면 파드가 살아 있는 동안 `kubectl logs`를 쳐야 했습니다. 쿠버네티스를 쓰는 이유가 이런 일을 사람 대신 맡기기 위해서라면, 맡긴 뒤에는 무엇이 달라질까요?


이번 번외 편은 그 질문을 원본 서비스에서 단계마다 클러스터를 켜 보며 확인한 기록입니다. 파드 수를 맡는 HPA, 노드 수를 맡는 Karpenter, 배포를 맡는 ArgoCD를 차례로 들였습니다. 마지막에는 클러스터가 사라진 뒤에도 읽을 수 있는 로그를 밖에 쌓았습니다. 결론부터 말씀드리면 자동화를 하나씩 붙일 때는 각자 잘 돌았습니다. 둘이 같은 칸을 고쳐 쓰기 시작하자 문제가 생겼습니다.

> 자동화는 사람 대신 칸을 고쳐 쓴다. 같은 칸을 둘이 쓰면 싸운다.

이 편은 ⑥~⑪편처럼 eks-lab으로 따라 하는 편이 아닙니다. ①편에서는 처음에 클러스터에 직접 올려 보는 선택 과정으로 소개했는데, 쓰면서 읽는 편으로 바꿨습니다.


원본은 앱 세 개와 노드 서너 대를 두고 HPA와 Karpenter 단계에서는 부하 생성기까지 띄워 단계마다 따로 클러스터를 켰습니다. 그 구성을 eks-lab에 옮기면 앞 편들의 몇 배 되는 분량이 되므로 이 편은 그날의 숫자와 출력을 읽는 편으로 두었습니다. 직접 해 보고 싶으시면 글 끝의 원본 튜토리얼 Stage 5에 명령이 전부 있습니다. 건너뛰셔도 ⑭편으로 바로 이어집니다.


---


## HPA는 지표를 읽고 파드 수 한 칸을 고칩니다


HPA(Horizontal Pod Autoscaler)는 파드를 직접 만들지 않습니다. Deployment의 `replicas` 한 칸을 고쳐 쓸 뿐입니다. 15초마다 파드들의 CPU 사용률을 읽고 아래 식으로 필요한 수를 구해 그 칸에 적습니다. 파드를 실제로 늘리고 줄이는 것은 그 칸을 보고 있던 Deployment의 몫입니다.


```plain text
필요한 파드 수 = 올림( 지금 파드 수 × 지금 사용률 ÷ 목표 사용률 )
사용률         = 실제 CPU 사용량 ÷ requests.cpu      ← limits 도, 노드 용량도 아닙니다
```


여기서 쓰는 사용량은 metrics-server가 노드마다 모아 내놓는 값입니다. 그래서 원본은 metrics-server를 EKS 애드온으로 먼저 올렸고 HPA는 원본의 `daily-api`에 걸었습니다. `requests.cpu`가 200m이고 목표를 70%로 두었으니 파드당 평균 140m를 넘으면 늘립니다. `requests`가 없는 컨테이너는 사용률을 계산할 수 없어서 HPA가 `<unknown>`을 냅니다.


```yaml
# 원본 k8s/hpa/daily-api-hpa.yaml 의 요지
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: daily-api }
  minReplicas: 1
  maxReplicas: 4
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
  behavior:
    scaleDown: { stabilizationWindowSeconds: 60 } # 기본 300초. 기다리는 시간이 곧 요금이라 줄였습니다
```


2026년 10월 8일에 초당 600건을 보내자 파드 하나의 사용률이 120%가 됐습니다. HPA는 2초 뒤 파드를 2개로 늘렸고 새 파드는 32초 안에 `Ready`가 됐습니다. 부하를 멈추자 1분쯤 뒤 다시 1개로 줄었는데 위에서 줄인 60초와 맞습니다.


그 전에 숫자부터 의심했습니다. `kubectl top`이 내놓는 값이 맞는지, 같은 구간의 컨테이너 자체 CPU 카운터와 비교해 봤습니다. 여섯 번 찍은 평균은 147m, 카운터는 139m로 6%쯤 차이였습니다.


그런데 한 번씩 찍은 값은 84m에서 272m까지 흩어졌고 첫 시도에서 한 번 찍은 값과 45초 평균은 35% 어긋났습니다. 막 뜬 JVM은 초 단위로 출렁이니 순간값 하나로 판단하면 틀리기 쉽습니다. HPA도 같은 순간값을 읽는다는 점은 다음 절에서 다시 나옵니다.


---


## 파드가 늘어도 일이 나뉜다는 보장은 없습니다


파드가 둘이 되면 일도 반씩 나뉠까요? 확장 직후 파드별 CPU를 보니 새 파드는 4m, 기존 파드는 220m였습니다. 기존 파드는 여전히 110%를 쓰는데 둘의 평균이 56%라 HPA는 목표 아래라고 보고 아무것도 하지 않았습니다. 새 파드는 1분 넘게 거의 놀았습니다.


Service가 요청이 아니라 연결 단위로 파드를 고르기 때문입니다. 부하 생성기 k6는 한 번 맺은 연결을 계속 다시 쓰므로 새 파드는 새 연결이 생길 때만 일을 받습니다. 연결을 다시 쓰지 않게 하자 곧바로 나뉘었습니다. 실제 서비스에서는 연결을 오래 물고 있는 다른 서비스의 커넥션 풀이 같은 모습을 만듭니다. 반면 ⑪편의 ALB를 거쳐 들어오는 요청은 ALB가 요청 단위로 나눠 주니 양상이 다릅니다.


```plain text
새 파드 483m · 새 파드 434m · 기존 파드 95m      ← 연결을 다시 쓰지 않게 한 회차
```


그런데 이 줄에 숫자가 하나 더 숨어 있습니다. 같은 몫의 요청을 받는데 새 파드는 기존 파드의 4~5배 CPU를 씁니다. 막 뜬 JVM은 아직 JIT 컴파일이 끝나지 않아 같은 일에 CPU를 훨씬 많이 쓰기 때문입니다. 그 사용률이 평균을 끌어올려 HPA는 2개면 될 것을 4개까지 늘렸습니다. 늘린 파드의 워밍업이 다시 늘릴 근거가 된 셈이고 이것을 막아 준 것은 `maxReplicas: 4`라는 상한뿐이었습니다.


---


## 첫 번째 싸움은 사람과 HPA 사이에서 났습니다


HPA가 4를 원하는 부하 중에, 원본 매니페스트를 평소처럼 다시 적용하면 어떻게 될까요? 그 파일에는 `replicas: 1`이 적혀 있었습니다.


```plain text
02:07:41  kubectl apply           (replicas: 1)
02:07:47  파드 1개만 남음          ← 6초 안에 부하를 받던 파드들이 내려갔습니다
02:08:17  HPA 가 2 로 다시 늘림    ← 36초 뒤
```


사람이 한 일은 늘 하던 배포였고 HPA도 자기 계산대로 움직였습니다. 둘 다 틀리지 않았는데 같은 칸에 서로 다른 값을 적은 것이 문제였습니다. HPA를 계속 쓰려면 매니페스트에서 `replicas` 줄을 빼서 그 칸의 주인을 HPA 하나로 정해야 합니다. 원본은 HPA를 실습 세션에서만 켰기 때문에 이때는 줄을 남겨 두었고 이 결정이 세 번째 싸움에서 다시 돌아옵니다.


HPA에는 한계가 하나 더 있었습니다. 4번째 파드를 만들어 달라고 했지만 노드에 자리가 없어 `Pending`으로 남았습니다. 아래의 `unschedulable` 하나는 부하 생성기 전용으로 비워 둔 노드이고 나머지 셋은 메모리가 모자랐습니다. HPA는 파드 수만 고칠 뿐 노드를 늘리지 못합니다.


```plain text
0/4 nodes are available: 1 node(s) were unschedulable, 3 Insufficient memory.
```


---


## Karpenter는 Pending을 보고 EC2를 직접 띄웁니다


그 `Pending`을 받는 것이 Karpenter입니다. ⑤편의 관리형 노드 그룹에서는 "몇 대"라는 칸을 사람이 정했습니다. Karpenter는 자리를 못 찾은 파드를 보고 그 파드가 들어갈 EC2를 직접 띄워 노드로 붙입니다. 노드가 비면 지웁니다. 어떤 인스턴스를 얼마까지 만들어도 되는지는 NodePool에, 어떤 서브넷과 AMI로 만드는지는 EC2NodeClass에 적습니다.


10월 12일에 4번째 파드가 `Pending`이 된 순간부터 `Ready`가 될 때까지를 재 보니 이랬습니다. 노드가 클러스터에 붙기까지 21초, 그 뒤 앱이 `Ready`가 되기까지 40초가 걸렸습니다.


```plain text
14:44:50    파드 생성, 자리 없음                  0초
14:44:51.6  Karpenter 가 발견하고 NodeClaim 생성   1.6초
14:44:54    EC2 생성 호출 완료 (t4g.small)         4초
14:45:11    노드가 클러스터에 등록                 21초
14:45:51    파드 Ready (앱 기동 24초 포함)         61초
```


이때 후보에는 `t4g.small`과 함께 `t4g.medium`도 들어 있었습니다. 몇 분 뒤 HPA를 6으로 고정해 `Pending` 파드 셋을 한꺼번에 만들어 보자 Karpenter는 셋을 한 대에 담을 수 있는 medium을 골랐습니다. 그리고 AWS가 거절했습니다.


```plain text
ERROR … InvalidParameterCombination: The specified instance type is not eligible for Free Tier.
```


이 계정이 띄울 수 있는 인스턴스는 프리티어 대상 목록뿐이었고 그 목록에 `t4g.small`은 있어도 medium은 없었습니다. Karpenter는 small 두 대로 바꿔 다시 시도하지 않았고 NodeClaim이 멈춘 채로 파드는 계속 `Pending`이었습니다.


HPA를 4로 되돌리고 멈춘 NodeClaim을 지우자 그제야 small이 떴습니다. 그 뒤 후보를 small 하나로 좁혔고 10월 16일 처음부터 다시 따라 해 본 재현에서 그 파일로 노드가 정상으로 떴습니다.


Karpenter가 만든 EC2는 OpenTofu의 state에 없다는 점도 ⑪편의 로드밸런서와 같습니다. 그래서 원본은 `tofu destroy` 순서 한가운데에 Karpenter의 노드를 먼저 치우는 단계를 끼워 넣었습니다. 10월 12일에는 그 단계가 돌기 전에 Karpenter가 스스로 노드를 지워 확인하지 못했고 16일 재현에서 Karpenter 노드를 살려 둔 채 부숴 그 단계가 EC2를 지우는 것을 확인했습니다.


---


## 두 번째 싸움은 HPA와 Karpenter가 서로의 입력이 되면서 났습니다


Karpenter는 빈 노드만 지우는 것이 아닙니다. 원본의 NodePool은 `WhenEmptyOrUnderutilized`로, 노드가 덜 차 있어도 그 위의 파드를 다른 노드로 옮길 수 있으면 지웁니다. 그런데 이 동작이 부하가 걸려 있는 중에 일어났습니다.


```plain text
14:43:28  HPA 4 → 3                 (관리형 노드의 파드가 하나 줄어 자리가 생겼습니다)
14:43:36  disrupting node(s) Underutilized … delete
14:44:07  deleted node              (그 노드의 파드는 관리형 노드에서 새로 뜹니다)
14:44:51  found provisionable pod(s) ← 44초 뒤, 노드를 또 만듭니다
```


옮겨진 파드는 새로 뜬 JVM이라 앞에서 본 것처럼 CPU를 몇 배나 씁니다. 이날은 새 노드의 파드가 480m, 나머지가 73~91m였습니다. 그 사용률이 HPA를 다시 4로 올리고 4번째 파드는 방금 지운 노드를 다시 부릅니다. HPA는 파드 수를, Karpenter는 노드 수를 각자 최적화합니다. 그런데 한쪽의 결정이 다른 쪽의 입력이 되면서 노드를 지운 지 44초 만에 다시 노드를 찾기 시작했습니다.


같은 칸을 쓰지는 않았지만 구조는 첫 번째 싸움과 같습니다. 운영에서는 정책을 빈 노드만 지우는 `WhenEmpty`로 바꾸는 방법이 알려져 있습니다. 지우기 전 기다리는 시간을 HPA가 줄이는 시간보다 길게 잡기도 합니다. 원본에서는 이 완화책들을 실제로 재 보지는 못했습니다.


---


## ArgoCD는 사람이 밀어 넣던 배포를 git에서 끌어옵니다


지금까지 배포는 사람이 클러스터에 밀어 넣는 방식이었습니다. ArgoCD는 클러스터 안에서 돌면서 git을 계속 읽고 git에 적힌 모습과 클러스터의 실제 모습이 다르면 git 쪽으로 맞춥니다. 정답을 git에 두는 이 운영 방식을 GitOps라고 부릅니다. ArgoCD에 내는 주문서는 Application으로, "이 git 폴더를 이 클러스터에 맞춰 두라"는 내용입니다.


```yaml
# 원본 k8s/gitops/application.yaml(10월 15일 판)에서 git 을 읽는 부분만 남긴 요지
spec:
  sources:
    - repoURL: https://github.com/bangddong/switch-job-quest.git
      path: k8s/gitops/apps
  destination:
    server: https://kubernetes.default.svc # ArgoCD 가 설치된 바로 그 클러스터
    namespace: default
  syncPolicy:
    automated:
      selfHeal: true # 누가 손으로 바꾸면 git 대로 되돌립니다
      prune: true    # git 에서 지운 것은 클러스터에서도 지웁니다
```


10월 13일에 이것을 적용하고 15초 뒤 `Synced`가 됐습니다. 그 뒤로 앱에는 `kubectl apply`를 한 번도 치지 않았습니다. 손으로 `kubectl scale`을 치면 1~2초 만에 git의 값으로 돌아왔습니다. Service를 지우면 2초 뒤 같은 이름으로 다시 생겼습니다.


반대로 git에 커밋한 변경은 네 번 재 보니 1분 8초에서 2분 51초 뒤에 반영됐습니다. 클러스터의 변화는 통지를 받지만 git은 기본 3분쯤마다 물어봐야 알기 때문입니다.


원본에서 ArgoCD에 전부를 맡기지는 않았습니다. 처음에는 앱과 네트워크 정책, HPA만 맡기고 데이터베이스는 손으로 올렸습니다. `prune`은 git에서 빠진 것을 지우는데 데이터가 걸린 것을 그 경로에 두고 싶지 않았기 때문입니다.


---


## 세 번째 싸움은 HPA와 ArgoCD 사이에서 났습니다


첫 번째 싸움에서 `replicas: 1`을 남겨 두었다고 했습니다. 이제 그 파일을 사람이 아니라 ArgoCD가 계속 적용합니다. 그 상태로 HPA의 최소 파드 수를 2로 바꾸면 어떻게 될까요? 아래 그림의 다섯 칸이 그날 일어난 일인데 빨간 두 칸이 같은 일을 되풀이하는 구간입니다.


![HPA가 파드 수를 2로 올리면 ArgoCD가 git에 적힌 1로 되돌리고, 이것이 반복되다가 git에서 replicas 칸을 빼자 멈춥니다](https://dhbang.co.kr/images/aws-eks/anim10-replicas-fight.svg)


```plain text
16:45:53 spec=1 hpa=1/2 Synced     Running Terminating     ← HPA 가 올린 2 를 ArgoCD 가 1 로
16:46:35 spec=2 hpa=1/2 OutOfSync  Running Running(2s)
16:46:41 spec=1 hpa=1/2 Synced     Running
16:46:53 spec=2 hpa=1/2 OutOfSync  Running Running(5s)
```


3분 동안 둘째 파드가 네 번 새로 만들어졌습니다. 무한히 빠르게 싸우지는 않았는데 ArgoCD가 같은 커밋으로 다시 맞추는 간격을 41초에서 2분 41초로 늘렸기 때문입니다. 그래서 잠깐 멈춘 것처럼 보여도 싸움이 끝나지는 않았습니다.


해결은 첫 번째 싸움과 같았습니다. ArgoCD가 읽는 묶음에서 `replicas` 칸을 빼, 그 칸의 주인을 HPA 하나로 정했습니다. 손으로 올리는 절차도 같은 파일을 쓰니 파일은 그대로 두고 ArgoCD가 읽을 때만 그 칸을 지우게 했습니다.


```yaml
# 원본 k8s/gitops/apps/kustomization.yaml 의 요지
patches:
  - target: { kind: Deployment, name: daily-api }
    patch: |-
      - op: remove
        path: /spec/replicas
```


이 패치가 반영되는 순간에는 파드 수가 한 번 1로 떨어졌습니다. 적용하던 칸을 빼면 기본값으로 돌아가기 때문이고 6초 뒤 HPA가 다시 올린 다음부터는 되돌림이 없었습니다.


---


## Synced라는 표시는 누군가 방금 확인했다는 뜻이 아닙니다


ArgoCD가 죽으면 앱도 멈출까요? 원본에서 ArgoCD의 본체 컨트롤러를 0개로 내려 보니 앱은 그대로 돌았습니다. 다만 손으로 바꾼 것을 되돌리는 힘이 사라져 `replicas`를 2로 바꾸자 25초가 지나도 2로 남았습니다. 컨트롤러를 다시 올리자 4초 만에 1로 돌아왔습니다.


그런데 컨트롤러가 없는 동안 Application의 상태는 계속 `Synced`였습니다. 아무도 상태를 갱신하지 않으니 마지막에 적힌 값이 그대로 남아 있었습니다. 화면의 `Synced`를 "지금 git과 같다"로 읽으면 틀리고 "마지막으로 확인했을 때 같았다"로 읽어야 맞습니다.


10월 15일에는 데이터베이스와 시크릿까지 Application 하나로 옮겼습니다. 여기서는 순서가 문제였습니다. ESO가 떠야 시크릿을 만들 수 있고 시크릿이 있어야 데이터베이스가 뜨기 때문입니다. ArgoCD는 리소스에 번호(sync wave)를 붙이면 작은 번호부터 적용하고 그 번호가 전부 정상이 된 뒤에 다음으로 넘어갑니다. 실제로 앱은 데이터베이스가 `Ready`가 되고 1초 뒤에 만들어졌습니다.


이 작업의 첫 세션은 ArgoCD가 클러스터를 아예 읽지 못해 \$0.15만 쓰고 접었습니다. 그날 EKS가 기본으로 깐 metrics-server 애드온은 새 버전이었습니다. 이 버전이 API 서버의 protobuf 형식 스키마 응답을 503으로 만들었고 ArgoCD는 그 응답을 읽지 못했습니다. 원본은 애드온 버전을 이전 것으로 고정해 피했습니다. 자동화를 하나 더 올리면 그 아래 깔린 것의 버전까지 신경 써야 합니다.


---


## 로그는 클러스터가 사라진 뒤에 읽으려고 밖에 둡니다


`kubectl logs`는 노드 디스크의 파일을 읽어 옵니다. 파드가 지워지면 그 파일도 지워지고 이 시리즈처럼 클러스터를 매번 부수면 전부 사라집니다. 어젯밤 죽은 파드가 왜 죽었는지 알고 싶다면 로그를 클러스터 밖에 쌓아야 합니다. 원본은 노드마다 Fluent Bit 수집기를 띄워 CloudWatch Logs로 보냈습니다. 받는 로그 그룹은 ⑩편의 디스크처럼 `0-bootstrap`에 두었습니다.


10월 15일에 파드 하나를 지우자 `kubectl logs`는 `NotFound`를 냈습니다. 하지만 CloudWatch에서는 그 파드가 종료 직전까지 남긴 268건이 나왔습니다. 클러스터를 부순 뒤에 같은 질의를 다시 돌려도 같은 결과였습니다.


그런데 없는 이미지를 받으려다 실패한 파드는 컨테이너가 한 번도 뜨지 않아 앱 로그가 0건이었습니다. 이 장애는 쿠버네티스 이벤트(`ErrImagePull`, `ImagePullBackOff`)에만 남는데 이벤트는 API 서버에 한 시간쯤만 머뭅니다. 그래서 원본은 처음부터 수집기를 두 벌 두어 이벤트도 따로 보냈습니다. 로그가 "앱이 말한 것"이라면 이벤트는 "클러스터가 앱에게 한 것"이라, 앱이 아예 못 뜨는 장애는 이벤트에서만 보입니다.


10월 16일에는 마지막으로 "누가 그랬나"를 물었습니다. EKS 컨트롤플레인의 감사(audit) 로그에는 API 서버에 들어온 요청마다 누가 무엇을 했는지가 남습니다. 사람이 `ai-api` Deployment를 지우자 0.9초 뒤 ArgoCD의 컨트롤러가 그것을 다시 만든 기록이 나란히 남았습니다.


```plain text
00:36:57.919Z  arn:aws:iam::123456789012:user/bootstrap-admin                delete 200
00:36:58.817Z  system:serviceaccount:argocd:argocd-application-controller    patch  201
```


ArgoCD가 되살린 기록을 `create`로 찾으면 나오지 않습니다. 생성도 `patch`로 보내고 새로 만든 것인지는 응답 코드 201로 구분합니다. 그리고 이 감사 로그가 컨트롤플레인 로그 양의 98%였습니다.


---


## 맡긴 만큼 확인할 곳과 요금이 늘어납니다


감사 로그는 평소에 시간당 88MB쯤 쌓였습니다. 수집 요금으로 치면 시간당 \$0.067로, 노드 세 대짜리 클러스터 요금의 36%를 더하는 양입니다. 나머지 종류는 30분에 1MB 남짓이라 거의 무료였습니다. 그래서 원본은 감사 로그를 기본으로 꺼 두고 "누가 그랬나"를 물을 일이 있는 세션에서만 켜기로 했습니다.


요금은 자동화보다 사람 쪽에서 더 크게 샜습니다. 10월 8일 HPA 세션은 측정을 33분 만에 끝냈는데 클러스터를 끄는 명령이 승인을 기다리며 113분 멈췄습니다. 그 사이 노트북이 잠든 것으로 보여 안전장치도 돌지 못했고 예상 \$0.23이 \$0.59가 됐습니다.


10월 12일 Karpenter 세션도 같은 이유로 \$0.27 예상이 \$0.53이 됐습니다. 두 세션 모두 요금의 4분의 3 넘게가 아무것도 하지 않은 시간이었습니다.


그리고 자동화 하나를 붙일 때마다 "잘 돌고 있다"를 확인할 곳이 늘었습니다. HPA라면 metrics-server가 `Available`인지 봐야 했고 Karpenter라면 NodeClaim이 멈추지 않았는지 봐야 했습니다. ArgoCD는 `Synced`가 방금 갱신된 값인지도 따로 확인해야 했습니다.


앱 하나를 한 시간 띄우는 이 시리즈의 실습에는 셋 다 과합니다. 파드 수와 노드 수, 배포가 사람 손으로 감당이 안 될 때 하나씩 들이는 편이 맞습니다.


---


## 정리


| 무엇을 맡겼나   | 고쳐 쓰는 칸                | 원본에서 본 것                                           |
| --------- | ---------------------- | -------------------------------------------------- |
| HPA       | Deployment의 `replicas` | 120%에서 2초 뒤 확장, 새 JVM 탓에 4까지 과확장                   |
| Karpenter | 노드 수 (EC2)             | `Pending`부터 `Ready`까지 61초, 덜 찬 노드를 지우고 44초 뒤 다시 찾음 |
| ArgoCD    | git에 적힌 모든 칸           | 손 변경은 1~2초, 커밋은 1~3분 뒤 반영                          |
| 로그 수집     | 없음 (읽기만)               | 파드와 클러스터가 사라진 뒤에도 같은 질의에 같은 답                      |


자동화는 사람 대신 칸을 고쳐 씁니다. 그러니 하나를 들일 때마다 그것이 어느 칸을 쓰는지 적어 두고 한 칸에는 주인을 하나만 둡니다. 세 번의 싸움은 모두 그 주인이 둘이었기 때문에 났습니다.


다음 ⑬편도 번외입니다. 원본 서비스를 평일 낮에만 EKS로 옮겨 보려고 창을 몇 번 열어 보다가 결국 서비스를 닫기까지의 기록입니다.


---


## 참고

- [Kubernetes Docs, Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Karpenter Docs, Disruption](https://karpenter.sh/docs/concepts/disruption/)
- [Argo CD Docs, Automated Sync Policy](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Argo CD Docs, Sync Phases and Waves](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)
- [Amazon EKS 사용 설명서, 컨트롤플레인 로그](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- 제 원본 튜토리얼의 Stage 5a~5f와 작업 일지, 전체 코드는 [switch-job-quest](https://github.com/bangddong/switch-job-quest) 레포의 `docs/eks-tutorial-steps.md`와 `docs/eks-migration-log.md`에 있습니다. 서비스를 닫으면서 보관(archive)해 두었습니다.
> 이 편의 숫자와 출력은 전부 제 원본 서비스에서 2026년 10월 8일(HPA), 12일(Karpenter), 13일(ArgoCD), 14일과 15일(로그 수집, 데이터베이스까지 ArgoCD), 16일(컨트롤플레인 로그)에 클러스터를 여덟 번 켜고 받은 일지의 기록입니다. 16일 오후에는 이 단계들을 처음부터 다시 따라 해 보는 재현을 두 번 더 했고, Karpenter 절에서 재현이라고 밝힌 두 문장은 그 기록입니다. 이 두 번은 머리말의 횟수와 금액에 넣지 않았습니다. 이 글을 쓰면서 다시 돌리지는 않았고, 코드도 eks-lab으로 옮기지 않았습니다. 인용한 YAML은 원본 파일에서 이 편에 필요한 줄만 남긴 요지입니다. 감사 로그 출력의 계정 ID는 `123456789012`로 바꿨습니다. 머리말의 \$1.9는 단계마다 처음 켠 세션만 센 여섯 단계의 정가 어림(\$0.59, \$0.53, \$0.18, \$0.15, \$0.29, \$0.14)을 더한 값으로, 로그 수집과 데이터베이스 단계는 중단한 첫 세션까지 넣었습니다. 10월 13일 ArgoCD를 처음 적용한 판은 출처가 하나(`source:`)였고, 인용한 것은 이틀 뒤 여러 출처로 바꾼 판이지만 인용한 줄의 내용은 같습니다. 청구서에는 노드 요금이 \$0으로 찍혔다는 이야기는 ⑤편에 적었습니다. 자세한 결산은 ⑭편에서 본편과 번외를 나눠 다시 봅니다.
>
> 이 글의 그림은 AI가 그렸습니다.
>
>
