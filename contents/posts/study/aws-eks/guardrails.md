---
title: '켜져 있는 알림이 울리지 않을 수 있다. EKS 실습기 ③, 비용 가드레일을 코드로 만드는 법'
date: '2026-10-06'
tags:
  - AWS
  - EKS
series: AWS EKS 실습기
emoji: "\U0001F6A8"
---
> **AWS 프리티어 \$200으로 EKS 실습하기 ③** · 💰 이 편도 돈이 나가지 않습니다. 비용 **\$0**

신규 AWS 계정에는 이상 지출을 알려 주는 장치가 처음부터 켜져 있습니다. 저는 그 사실을 한참 동안 몰랐습니다. 같은 장치를 직접 만들려다가 한도를 넘었다는 에러를 받고서야 알았고, 그제야 어떤 조건에서 알려 주는지 설정을 열어 봤습니다. 알림 조건은 \$100 이상이면서 평소보다 40% 이상 튈 때였습니다. 크레딧이 \$200인 계정이라면 절반이 사라진 뒤에야 울리는 값입니다.


그 설정을 보고 생각이 하나 바뀌었는데, 가드레일에서 가장 위험한 상태는 없는 상태가 아니라, 켜져 있는데 울리지 않는 상태라는 것입니다. 아무것도 없으면 불안해서라도 청구서를 가끔 들여다보게 됩니다. 반면 뭔가 켜져 있다는 것을 알게 되면 그것을 믿고 보지 않게 됩니다. 저도 설정을 열어 보지 않았다면 그랬을 것입니다. 그래서 이번 편에서는 새로 만드는 일만큼이나, 이미 있는 것이 제대로 울리게 고치는 일에 시간을 씁니다.


이번 편에서 처음으로 `tofu apply`를 실행합니다. 만드는 것은 state 저장소와 예산 알림, 이상 지출 탐지 세 가지이고 전부 무료입니다. 무료이니 이 편에서 만든 것은 시리즈가 끝날 때까지 지우지 않고 그대로 둡니다.

> 켜져 있는 알림이 울리지 않을 수 있다.

---


## 코드를 실행하려면 상태를 둘 곳부터 있어야 합니다


가드레일을 만들기 전에 준비할 것이 하나 있습니다. OpenTofu는 자기가 무엇을 만들었는지를 state라는 파일에 적어 두고, 다음에 실행할 때 이 파일과 코드를 비교해서 무엇을 더하고 뺄지 정합니다. 그러면 이 파일을 잃어버리면 어떻게 될까요? OpenTofu는 이미 만든 리소스가 있다는 사실을 모르게 되고, 전부 처음부터 다시 만들려고 합니다.


기본값은 state를 내 컴퓨터의 파일로 두는 것입니다. 혼자 한 대에서만 쓴다면 그래도 되지만, 노트북을 바꾸거나 폴더를 실수로 지우는 순간 복구할 방법이 없습니다. 그래서 이 시리즈는 state를 처음부터 S3 버킷에 두고, 두 곳에서 동시에 실행해 서로 덮어쓰는 일이 없도록 DynamoDB 테이블로 잠금도 겁니다. 버킷에 들어가는 파일은 수 KB이고 테이블은 쓴 만큼만 내는 방식이라 둘 다 사실상 \$0입니다.


이제 폴더를 하나 만들고 파일을 채웁니다. 폴더 이름은 `0-bootstrap`으로 하겠습니다. 가장 먼저 어떤 버전의 도구와 어느 리전을 쓸지 적습니다.


```hcl
# versions.tf
terraform {
  required_version = ">= 1.8.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}

provider "aws" {
  region = "ap-northeast-2"
}
```


다음은 버킷과 잠금 테이블인데, 버킷에는 버전 관리를 켜서 state가 잘못 덮어써져도 이전 것으로 되돌릴 수 있게 하고, 퍼블릭 접근은 네 가지를 전부 막습니다.


```hcl
# backend-state.tf
resource "aws_s3_bucket" "tfstate" {
  bucket = var.state_bucket_name
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "tflock" {
  name         = "eks-lab-tflock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}
```


변수는 한 파일에 모아 두고, 예산 알림에서 쓸 것까지 여기에 미리 넣어 두겠습니다.


```hcl
# variables.tf
variable "state_bucket_name" {
  type        = string
  description = "state 를 담을 S3 버킷 이름. 전 세계에서 유일해야 합니다"
}

variable "alert_email" {
  type        = string
  description = "알림을 받을 이메일"
  sensitive   = true
}

variable "credit_total_usd" {
  type    = number
  default = 200
}

variable "alert_step_usd" {
  type    = number
  default = 10
}

variable "budget_period_start" {
  type        = string
  description = "크레딧을 받은 달의 1일 (YYYY-MM-DD_HH:MM)"
}
```


실제 값은 `terraform.tfvars`에 적습니다. `budget_period_start`에는 크레딧을 받은 달의 1일을 적는데, 아래 예시의 날짜는 제 것이니 본인의 가입 월로 바꿔 주세요. 그리고 여기에는 이메일 주소가 들어가므로 이 파일은 커밋하지 않습니다. 그러니 값을 적기 전에 `.gitignore`에 `terraform.tfvars`와 `*.tfstate*`를 먼저 넣어 두시기 바랍니다.


```hcl
# terraform.tfvars
state_bucket_name   = "<본인만의-버킷-이름>"
alert_email         = "<본인 이메일>"
budget_period_start = "2026-07-01_00:00"
```


### 버킷을 만드는 코드의 state는 그 버킷에 둘 수 없습니다


그런데 여기서 이상한 점을 눈치채셨을지도 모르겠습니다. state를 S3에 두려면 버킷이 먼저 있어야 합니다. 그런데 그 버킷을 만드는 것이 바로 지금 쓰고 있는 코드입니다. 그러면 이 코드의 state는 어디에 둬야 할까요? 닭이 먼저냐 달걀이 먼저냐 하는 문제이고, 실제로 아직 없는 버킷을 저장소로 지정하면 `tofu init`부터 실패합니다.


이 문제는 두 단계로 나눠서 푸는데, 먼저 내 컴퓨터에 state를 둔 채로 버킷을 만들고, 그다음에 그 state를 방금 만든 버킷으로 이사시키는 것입니다. 이사는 이 편의 맨 끝에서 하고 그 전까지는 로컬 state로 진행합니다. 우선 폴더를 초기화만 해 둡니다.


```bash
cd 0-bootstrap
tofu init
```


`OpenTofu has been successfully initialized!`가 나오면 된 것입니다. 아직 `apply`는 하지 않습니다. 가드레일 코드를 마저 쓰고 나서 한 번에 실행하는 편이 무엇이 만들어지는지 확인하기에 좋기 때문입니다.


---


## 예산 알림을 콘솔로 만들면 두 번 틀립니다


이제 가드레일을 만들 차례인데, 예산 알림은 콘솔에서 3분이면 만들 수 있습니다. 그런데 왜 굳이 코드로 만들까요? 저도 처음에는 콘솔로 만들었고, 그 자리에서 두 번 걸렸습니다. 하나는 바로 고쳤지만 다른 하나는 그날 고칠 방법이 없었습니다.


고치지 못한 쪽부터 말씀드리면 크레딧 문제입니다. ②편에서 사용액을 조회할 때 본 것과 같은 이야기로, 쓴 돈과 크레딧이 서로 지워져서 순액이 0이 됩니다. 예산이 그 순액을 보지 않게 하려면 크레딧을 계산에서 제외하는 설정을 걸어야 하는데, 갓 만든 계정에서는 그 설정의 선택 목록이 비어 있어서 걸 수가 없었습니다. 그대로 두면 어떤 일이 벌어질까요? 아래 그림은 같은 지출을 두 가지 방식으로 잰 것을 예시로 그린 것입니다. 빨간 선이 끝까지 어디에 머무는지, 그리고 초록 선이 점선을 넘는 순간에 무슨 일이 생기는지 지켜보시기 바랍니다.


![Anim.5 — 같은 지출도 크레딧을 빼고 재면 0에 붙어 있고, 크레딧 전 금액으로 재면 \$10 선을 넘어 알림이 옵니다. 곡선은 설명을 위한 예시이고, 그림은 AI가 코드로 그렸습니다](https://dhbang.co.kr/images/aws-eks/anim05-budget-credit.svg)


크레딧을 빼고 재는 예산은 크레딧이 남아 있는 동안 아무리 써도 0에 붙어 있습니다. 알림 선에 닿을 일이 없으니 알림도 오지 않습니다. 크레딧으로 실습하는 사람에게 알림이 필요한 때는 바로 크레딧이 남아 있는 동안인데, 정작 그 기간 내내 꺼져 있는 셈입니다.


바로 고친 쪽은 숫자의 단위입니다. 콘솔 입력란의 기본 단위는 금액이 아니라 예산 대비 퍼센트였습니다. 저는 \$10, \$50, \$150에서 알림을 받으려고 10, 50, 150을 넣었는데, 그대로 두면 \$200 예산의 10%, 50%, 150%인 \$20, \$100, \$300이 됩니다. 특히 마지막 것은 크레딧이 \$200뿐이니 무슨 일이 있어도 울릴 수 없는 알림입니다. 단위를 금액으로 바꾸고 요약에 \$10로 표시되는 것까지 확인해서 고쳤지만, 단위를 눈여겨보지 않았다면 그대로 저장됐을 것입니다.


코드에서는 이 두 값을 눈에 보이게 적습니다. 조금 길지만 전체를 먼저 보고, 중요한 줄을 아래에서 짚겠습니다.


```hcl
# budget.tf
locals {
  # $10, $20, ... $200
  thresholds = [
    for i in range(1, ceil(var.credit_total_usd / var.alert_step_usd) + 1) :
    i * var.alert_step_usd
  ]

  # 예산 하나에 알림은 10개까지만 붙습니다. 10개씩 끊어 예산을 나눕니다
  chunks = chunklist(local.thresholds, 10)
}

resource "aws_budgets_budget" "credit_burn" {
  count = length(local.chunks)

  name = format("eks-lab-credit-%03d-%03d",
    local.chunks[count.index][0],
    local.chunks[count.index][length(local.chunks[count.index]) - 1],
  )

  budget_type  = "COST"
  limit_amount = tostring(var.credit_total_usd)
  limit_unit   = "USD"

  # 매달 0으로 돌아가지 않고 계속 쌓입니다
  time_unit         = "ANNUALLY"
  time_period_start = var.budget_period_start

  # 크레딧이 대신 낸 금액도 쓴 돈으로 셉니다
  cost_types {
    include_credit = false
    include_refund = false
  }

  dynamic "notification" {
    for_each = local.chunks[count.index]
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "ABSOLUTE_VALUE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.alert_email]
    }
  }
}
```


`include_credit = false`가 첫 번째 함정을 막는 줄입니다. 청구 내역에서 크레딧은 음수로 잡히는데, 그 음수를 계산에 넣지 말라는 뜻입니다. 그래서 크레딧이 대신 낸 돈도 쓴 돈으로 잡힙니다. 그림의 초록 선이 바로 이 설정입니다. 덕분에 이 예산이 보여 주는 숫자가 곧 지금까지 소진한 크레딧이 됩니다. 두 번째 함정은 `threshold_type = "ABSOLUTE_VALUE"`가 막습니다. 이렇게 적어 두면 10은 10%가 아니라 \$10입니다.


`time_unit = "ANNUALLY"`도 이유가 있어서 고른 값입니다. 보통 예산은 월 단위로 만드는데, 월간 예산은 매달 1일에 0으로 돌아갑니다. 하지만 크레딧은 달이 바뀐다고 다시 채워지지 않습니다. 우리가 알고 싶은 것은 이번 달 지출이 아니라 크레딧을 받은 날부터의 누적이므로, 시작일을 고정한 연 단위 예산을 씁니다.


그렇다고 코드로 옮기면 함정이 사라지는 것은 아닙니다. 다만 조심하라고 적어 두는 것과 틀린 값이 들어갈 자리를 아예 없애는 것은 다른 일이고, 코드는 뒤쪽을 할 수 있습니다. 3분이면 되는 일을 굳이 코드로 만드는 이유가 여기에 있습니다.


### 알림은 예산 하나에 열 개까지만 붙습니다


코드에 `chunklist`라는 낯선 함수가 하나 있었습니다. 이것이 왜 필요한지는 AWS의 제한 하나를 보면 바로 이해됩니다. \$10마다 알림을 받으려면 알림이 스무 개 필요합니다. 그런데 예산 하나에 스무 개를 전부 넣으면 적용하는 순간 이런 에러가 납니다.


```plain text
ValidationException: Value at 'notificationsWithSubscribers' failed to satisfy
constraint: Member must have length less than or equal to 10
```


예산 하나에 붙일 수 있는 알림이 열 개까지라는 제한이 있는 것입니다. 만들 때만 막는 것도 아니어서, 열 개로 만든 뒤에 하나를 더 추가해도 결과는 같습니다.


```plain text
CreationLimitExceededException: one budget can only have 10 notifications
```


여기서 더 중요한 것은 에러 자체보다 에러가 난 시점입니다. `tofu plan`은 이 제한을 미리 알려 주지 않습니다. `plan`은 무엇을 만들고 바꿀지를 계산할 뿐, 그 요청을 AWS가 받아 줄지까지 미리 물어보지는 않기 때문입니다. 그래서 알림 스무 개짜리 예산도 문제없다고 나오고, `apply`를 실행하고 나서야 터집니다. 이 시리즈에서 앞으로 여러 번 만나게 될 일이니 기억해 두시면 좋습니다.


`chunklist`는 이 제한을 피해 가는 장치입니다. 임계값 스무 개를 열 개씩 끊어서 예산을 둘로 나누고, 이름에 담당 구간을 넣습니다. 결과로 `eks-lab-credit-010-100`과 `eks-lab-credit-110-200`이 생기고, 알림 메일만 봐도 어느 구간에서 온 것인지 알 수 있습니다. 참고로 알림만 보내는 예산은 몇 개를 만들어도 무료입니다.


---


## 이상 지출 탐지는 만드는 것이 아니라 넘겨받는 것입니다


예산 알림에는 금액이 선을 넘어야 울린다는 빈틈이 하나 있습니다. 그러면 \$10을 넘기 전에는 어떨까요? 무슨 일이 벌어지고 있어도 조용합니다. 이상 지출 탐지(Cost Anomaly Detection)는 이 빈틈을 다른 방식으로 메웁니다. 금액이 아니라 패턴을 보기 때문에, 평소 쓰지 않던 서비스에서 갑자기 요금이 나오기 시작하면 금액이 작아도 알려 줍니다. 실습 계정에서 그런 상황은 거의 언제나 지우는 것을 잊은 리소스입니다. 코드는 무엇을 감시할지 정하는 모니터와, 누구에게 어떻게 알릴지 정하는 구독 두 부분으로 되어 있습니다.


```hcl
# cost-anomaly.tf
resource "aws_ce_anomaly_monitor" "services" {
  name              = "eks-lab-service-monitor"
  monitor_type      = "DIMENSIONAL"
  monitor_dimension = "SERVICE"
}

resource "aws_ce_anomaly_subscription" "alerts" {
  name             = "eks-lab-anomaly-alerts"
  monitor_arn_list = [aws_ce_anomaly_monitor.services.arn]
  frequency        = "DAILY"

  subscriber {
    type    = "EMAIL"
    address = var.alert_email
  }

  threshold_expression {
    dimension {
      key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
      match_options = ["GREATER_THAN_OR_EQUAL"]
      values        = ["5"]
    }
  }
}
```


그런데 이 코드를 그대로 `apply`하면 실패합니다. 제가 받은 에러는 아래와 같았습니다(괄호 안의 리소스 이름만 이 글에 맞게 바꿨습니다).


```plain text
Error: creating Cost Explorer Anomaly Monitor (eks-lab-service-monitor):
operation error Cost Explorer: CreateAnomalyMonitor, https response error StatusCode: 400,
api error ValidationException: Limit exceeded on dimensional spend monitor creation
```


한도를 넘었다는데, 저는 모니터를 만든 적이 없었습니다. 어떻게 된 일일까요? 도입부에서 말씀드린 그 장치 때문입니다. AWS가 신규 계정에 `Default-Services-Monitor`라는 모니터를 미리 만들어 두었는데, 서비스 단위 모니터는 계정에 하나만 둘 수 있습니다. 그러니까 없는 것을 만들려던 것이 아니라 이미 있는 것을 하나 더 만들려다 막힌 것입니다. 이번에도 `plan`은 도움이 되지 않았습니다. 계정에 이미 무엇이 있는지 모르기 때문에 태연하게 새로 만들겠다고 나옵니다.


### 이미 있는 리소스는 import로 state에 넣습니다


그러면 기존 모니터를 지우고 다시 만들어야 할까요? 그럴 필요 없이 넘겨받으면 됩니다. `tofu import`는 이미 존재하는 리소스를 state에 등록해서 그때부터 코드가 관리하게 해 줍니다. 넘겨받기 전에 먼저 계정에 무엇이 있는지부터 확인합니다.


```bash
aws ce get-anomaly-monitors \
  --query 'AnomalyMonitors[].[MonitorName,MonitorType,MonitorDimension]' --output table
aws ce get-anomaly-subscriptions \
  --query 'AnomalySubscriptions[].[SubscriptionName,Frequency]' --output table
```


목록을 확인했으면 이름으로 골라서 넘겨받습니다. 이때 목록의 첫 번째를 집는 방식(`AnomalyMonitors[0]`)은 쓰지 않는 편이 좋습니다. 새 계정은 모니터가 하나뿐이라 우연히 맞겠지만, 모니터가 여러 개인 계정에서는 엉뚱한 것을 넘겨받게 되고 그다음 `apply`가 남의 설정을 바꿔 버리기 때문입니다.


```bash
MON=$(aws ce get-anomaly-monitors \
  --query "AnomalyMonitors[?MonitorName=='Default-Services-Monitor'].MonitorArn | [0]" --output text)
SUB=$(aws ce get-anomaly-subscriptions \
  --query "AnomalySubscriptions[?SubscriptionName=='Default-Services-Subscription'].SubscriptionArn | [0]" --output text)

[ "$MON" != "None" ] && [ "$SUB" != "None" ] && echo "OK" || echo "이름이 다릅니다. 위 목록을 확인하세요"

tofu import aws_ce_anomaly_monitor.services    "$MON"
tofu import aws_ce_anomaly_subscription.alerts "$SUB"
```


가운데 줄에서 `OK`가 나오지 않았다면 아래 두 줄의 `tofu import`는 실행하지 마시고, 위에서 본 목록의 이름과 명령의 이름을 맞춘 뒤에 다시 해 주세요. 제대로 넘겨받으면 각각 `Import successful!`이 나옵니다. 넘겨받은 뒤에는 `tofu plan`으로 무엇이 바뀌는지 꼭 확인합니다. 아래 표와 같이 나와야 합니다.


| 리소스 | 계획에 나와야 하는 것       | 이유                                         |
| --- | ------------------ | ------------------------------------------ |
| 모니터 | `updated in-place` | 이름만 바뀝니다                                   |
| 구독  | `must be replaced` | 이름을 바꾸면 다시 만들어야 하는 리소스입니다. 무료이고 바로 다시 생깁니다 |
| 나머지 | `will be created`  | S3, DynamoDB, 예산 2개                        |


🔴 만약 모니터가 `replaced`로 나온다면 거기서 멈추셔야 합니다. 교체는 지우고 다시 만드는 순서로 진행되는데, 그러면 앞에서 본 한도 에러를 다시 만나게 됩니다.


### 기본 임계값을 그대로 두면 꺼져 있는 것과 같습니다


넘겨받은 구독의 조건이 도입부에서 말한 그 값, \$100 이상이면서 40% 이상입니다. 위 코드는 이것을 \$5로 낮춥니다. 왜 하필 \$5일까요? 예산의 첫 단계가 \$10이므로, 그보다 낮게 잡아서 예산이 울리기 전에 이쪽이 먼저 걸리게 하려는 것입니다.


한편 `frequency`가 `DAILY`인 것은 제가 고른 값이 아닙니다. 즉시 알림은 SNS라는 다른 서비스로 받을 때만 가능하고, 이메일로는 하루 한 번 요약이 최선입니다. `IMMEDIATE`와 이메일을 같이 적으면 `apply`가 거부하는데, 이것 역시 `plan`에서는 통과하고 적용할 때에야 알게 되는 제한입니다.


---


## 적용하고, state를 이사시킵니다


이제 준비가 끝났으니 지금까지 쓴 코드를 한 번에 실행합니다.


```bash
tofu apply
```


`apply`는 계획을 한 번 더 보여 주고 `yes`를 기다립니다. 앞의 표와 같은지 한 줄씩 확인한 다음에 입력하면 리소스가 차례로 만들어지고 마지막에 `Apply complete!`가 나옵니다. 끝났으면 예산이 의도한 대로 들어갔는지 확인해 봅니다.


```bash
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

aws budgets describe-budgets --account-id "$ACCOUNT" \
  --query 'Budgets[].[BudgetName,TimeUnit,CostTypes.IncludeCredit]' --output text
```


```plain text
eks-lab-credit-010-100   ANNUALLY   False
eks-lab-credit-110-200   ANNUALLY   False
```


예산이 둘이고, 둘 다 연 단위이고, 크레딧을 포함하지 않는다고 나오면 맞게 들어간 것입니다. 이제 마지막으로 미뤄 둔 이사를 합니다. 저장소를 S3로 지정하는 파일을 하나 추가합니다.


```hcl
# backend.tf
terraform {
  backend "s3" {
    bucket         = "<본인만의-버킷-이름>"
    key            = "0-bootstrap/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "eks-lab-tflock"
    encrypt        = true
  }
}
```


⚠️ 이 블록에는 변수를 쓸 수 없다는 점을 주의하셔야 합니다. OpenTofu가 저장소 설정을 읽는 시점이 변수를 계산하기 전이라서, `var.state_bucket_name`이라고 적으면 에러가 납니다. 버킷 이름을 `terraform.tfvars`와 여기 두 곳에 손으로 똑같이 적어야 하고, 처음 해 보면 여기서 가장 자주 틀립니다.


```bash
tofu init -migrate-state
```


state를 옮기겠냐고 물으면 `yes`를 입력하고, `Successfully configured the backend "s3"!`가 나오는지 봅니다. 다만 명령이 끝났다고 이사가 끝난 것은 아니고, 아래 세 가지를 모두 확인해야 합니다.


```bash
# <본인만의-버킷-이름> 은 꺾쇠까지 지우고 실제 이름으로 바꿉니다
aws s3 ls s3://<본인만의-버킷-이름>/0-bootstrap/   # terraform.tfstate 가 보여야 합니다
ls -l terraform.tfstate                            # 0바이트로 비어 있어야 합니다
tofu plan                                          # No changes. 가 나와야 합니다
```


이제 이 코드는 자기 state를 자기가 만든 버킷에 둡니다. 그리고 `key`에 폴더 이름을 넣어 둔 덕분에, 다음 편에서 만들 네트워크도 같은 버킷을 쓰되 서로 겹치지 않습니다.

> 저는 이 파일들을 며칠에 걸쳐 나눠 적용했습니다. 위는 그것을 한 번에 따라 할 수 있게 정리한 순서입니다. 코드도 원본에서 줄였는데, 리소스 이름을 바꿨고 버킷과 테이블의 암호화 설정, 공통 태그, 입력값 검증을 덜어냈습니다. 이렇게 줄인 코드는 `validate`와 `plan`까지만 확인했고 이 순서 그대로 `apply`해 보지는 못했으니, 막히는 곳이 있으면 알려 주시기 바랍니다.

---


## 이 그물은 하룻밤 사고를 잡지 못합니다


가드레일을 만들었으니 이제 안심해도 될까요? 아쉽지만 그렇지 않은데, 우선 두 장치 모두 느립니다. 예산 알림은 청구 데이터가 반영되는 데 최대 하루가 걸리기 때문에 그만큼 늦게 오고, 이상 지출 탐지는 이메일로 받는 이상 하루 한 번 요약이 전부입니다. 다시 말해 알림을 받는 시점에는 이미 하루치 요금이 나간 뒤입니다.


더 큰 문제는 금액이 작으면 아예 울리지 않는다는 점입니다. ①편에서 말한 하룻밤 사고가 정확히 그런 경우였습니다. 클러스터를 16시간 가까이 켜 둔 값은 다 합쳐 \$2 가까이였고, 누적 지출은 지금도 \$10 아래입니다. 예산의 첫 단계에 닿은 적이 없으니 예산 알림은 울릴 수가 없었습니다. 그 하룻밤의 금액은 이상 지출 탐지의 \$5에도 미치지 못했습니다.


그렇다면 임계값을 더 낮추면 되지 않을까요? 낮출 수는 있지만 그러면 정상적인 실습 한 번에도 알림이 울리기 시작하고, 자주 울리는 알림은 곧 읽지 않게 됩니다. 결국 정작 진짜 신호가 왔을 때 그것도 같이 묻히게 됩니다.


그래서 이 두 장치의 자리는 마지막 그물이라고 보는 것이 맞습니다. 며칠째 켜 둔 것을 모르고 있을 때 \$10에서 한 번은 붙잡아 주지만, 하룻밤을 지켜 주지는 못합니다. 하룻밤을 지키는 것은 결국 사람의 습관입니다. `tofu destroy`를 친 것과 클러스터가 사라진 것은 다르므로, 지운 뒤에 정말 지워졌는지를 눈으로 확인하고 자리를 떠야 합니다. 그 확인 절차는 클러스터를 처음 세우는 ⑤편에서 함께 익히겠습니다.


---


## 정리


| 만든 것           | 핵심 설정                                                  | 막는 것                        |
| -------------- | ------------------------------------------------------ | --------------------------- |
| S3 버킷과 잠금 테이블  | 버전 관리, 퍼블릭 차단                                          | state 분실과 동시 실행             |
| 예산 2개, 알림 20단계 | `include_credit = false`, `ABSOLUTE_VALUE`, `ANNUALLY` | 크레딧에 가려진 지출, 퍼센트 오해, 월초 초기화 |
| 이상 지출 탐지       | 기본 모니터를 import, 임계값 \$100에서 \$5로                         | 켜져 있지만 울리지 않는 기본값           |


기본값이 있다는 것과 그 기본값이 나를 지켜 준다는 것은 다른 이야기입니다. 실제로 이번 편에서 한 일의 절반은 새로 만드는 것이 아니라 이미 있던 것이 제대로 울리게 고치는 것이었습니다. 그렇게 고친 뒤에도 이 장치들이 잡지 못하는 사고가 있다는 것까지 확인했습니다.


다음 편에서는 클러스터가 들어갈 네트워크를 만듭니다. VPC와 서브넷을 다루는데, 여기까지도 돈은 나가지 않습니다.


---


## 참고

- [OpenTofu, S3 backend](https://opentofu.org/docs/language/settings/backends/s3/)
- [OpenTofu, import 명령](https://opentofu.org/docs/cli/import/)
- [AWS Budgets 사용 설명서](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
- [AWS Cost Anomaly Detection](https://docs.aws.amazon.com/cost-management/latest/userguide/manage-ad.html)
- [Terraform AWS Provider, aws_budgets_budget](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/budgets_budget)
- 이 시리즈의 명령어와 비용은 모두 실제 실행·청구 기록입니다. 원본 작업 일지와 전체 코드는 [switch-job-quest](https://github.com/bangddong/switch-job-quest) 레포에 있습니다.
> 이 글의 그림은 AI가 코드로 그렸습니다. Anim.5의 곡선은 설명을 위한 예시이고 실제 청구 기록이 아닙니다.
