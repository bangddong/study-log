---
title: '네트워크는 공짜지만 나가는 길은 공짜가 아니다. EKS 실습기 ④, VPC와 서브넷을 코드로 만드는 법'
date: '2026-11-06'
tags:
  - AWS
  - EKS
series: AWS EKS 실습기
emoji: "\U0001F310"
---
> **AWS 프리티어 \$200으로 EKS 실습하기 ④** · 💰 이 편도 돈이 나가지 않습니다. 비용 **\$0**

EKS 튜토리얼을 따라 `eksctl create cluster` 한 줄을 쳐 본 적이 있으신가요? 클러스터가 뜨기를 기다리는 동안 VPC와 서브넷이 알아서 만들어지고, 그 사이에 NAT 게이트웨이도 하나 생깁니다. eksctl의 기본값이 NAT 게이트웨이 하나를 두는 것이기 때문입니다. 클러스터를 지우면 함께 사라지니 대개는 신경 쓸 일이 없지만, 네트워크를 클러스터와 따로 오래 두는 순간 이야기가 달라집니다.


이 시리즈는 네트워크를 따로 둡니다. 클러스터는 실습할 때마다 세우고 부수지만, 그 클러스터가 들어갈 VPC는 시리즈가 끝날 때까지 그대로 남겨 둡니다. 그래서 이번 편에서는 VPC 안에 무엇을 둘지만큼이나 무엇을 두지 않을지를 정하는 데 시간을 씁니다. 만드는 것은 VPC와 서브넷 두 개, 인터넷 게이트웨이, 라우팅 테이블까지 리소스 일곱 개이고 전부 무료입니다.

> 네트워크는 공짜지만 나가는 길은 공짜가 아니다.

---


## 네트워크를 클러스터와 따로 두는 것은 수명이 다르기 때문입니다


③편에서 state 파일의 `key`에 폴더 이름을 넣어 두었던 것을 기억하실 겁니다. 이 시리즈의 OpenTofu 코드는 폴더 세 개로 나뉘고, 폴더마다 state를 따로 둡니다. 나누는 기준은 기능이 아니라 수명입니다. 수명이 다른 것을 한 폴더에 두면, 하나를 지울 때 다른 것까지 지워지거나 반대로 지우지 못하게 됩니다. 세 층을 수명과 요금으로 늘어놓으면 아래와 같으니, 오른쪽 두 칸을 함께 보시기 바랍니다.


```plain text
층            무엇                                      수명               요금
0-bootstrap   state 저장소, 예산 알림, 이상 지출 탐지   시리즈 내내 둔다   $0
1-network     VPC, 서브넷, 인터넷 게이트웨이            시리즈 내내 둔다   $0   ← 이번 편
2-cluster     EKS 클러스터, 노드                        실습마다 지운다    시간당 요금
```


두 칸은 서로 맞물려 있습니다. 오래 두는 층은 전부 \$0이고, 돈이 나가는 층은 지우는 층 하나뿐입니다. ⑤편부터는 실습이 끝날 때마다 `2-cluster`에서 `tofu destroy`를 치게 되는데, 그때 네트워크는 건드리지 않습니다. 매번 VPC까지 지웠다가 다시 만들 수도 있지만, 무료인 것을 굳이 부술 이유가 없고 지울 것이 적을수록 빠뜨릴 것도 적어집니다.


그런데 이 배치에는 규칙이 하나 숨어 있습니다. 오래 두는 층에 시간당 요금이 붙는 것을 넣으면 안 된다는 것입니다. 클러스터는 실습이 끝나면 지워지므로 시간당 요금이 붙어도 켜 둔 시간만큼만 냅니다. 하지만 네트워크 층에 들어간 것은 아무도 지우지 않으니, 실습을 하든 안 하든 하루 24시간 내내 요금이 나갑니다.


---


## 노드가 인터넷에 나가는 길에 요금이 붙습니다


그러면 네트워크에 무엇이 들어가야 할까요? 노드는 생각보다 바깥과 말을 많이 합니다. 컨테이너 이미지를 받아 와야 하고, 클러스터의 관제탑인 컨트롤플레인과도 통신해야 합니다. 그래서 노드가 놓이는 서브넷에는 인터넷으로 나가는 길이 꼭 있어야 합니다.


교과서적인 답은 노드를 프라이빗 서브넷에 두고 NAT 게이트웨이를 거쳐 나가게 하는 것입니다. 노드는 공인 IP 없이 숨어 있고, 밖으로 나가는 요청만 NAT가 대신 내보내 줍니다. AWS 문서도 가능하면 프라이빗 서브넷을 쓰라고 권합니다. 다만 서울 리전의 NAT 게이트웨이는 켜 두기만 해도 시간당 \$0.059입니다. 통과하는 데이터에도 GB당 \$0.059가 따로 붙습니다.


시간당 6센트면 작아 보이지만 이것을 오래 두는 층에 넣으면 계산이 달라집니다. 한 달이면 약 \$43이고, 크레딧이 만료되는 반년 동안 켜 두면 시간 요금만 \$259입니다. 크레딧 \$200을 NAT 게이트웨이 하나가 넘겨 버리는 셈입니다. 컨트롤플레인 요금보다 싸다는 이유로 가볍게 넣었다가는, 실습을 한 번도 하지 않은 달에도 크레딧이 줄어듭니다.


그래서 이 시리즈는 다른 길을 고릅니다. 노드를 퍼블릭 서브넷에 두고 공인 IP를 하나씩 주어서, 인터넷 게이트웨이로 직접 나가게 합니다. 인터넷 게이트웨이는 요금이 없습니다. 아래 그림은 두 구성에서 요금이 어디에 붙는지를 나란히 놓은 것인데, 각 요금이 어느 층에 사는지를 보시기 바랍니다.


```plain text
교과서 구성                         이 시리즈의 구성

  노드 (공인 IP 없음)                 노드 + 공인 IP   $0.005/h   [2-cluster]
   │  프라이빗 서브넷                  │  퍼블릭 서브넷
   ▼                                   │
  NAT 게이트웨이   [1-network]         │
    $0.059/h + $0.059/GB               │
   │  퍼블릭 서브넷                    │
   ▼                                   ▼
  인터넷 게이트웨이   $0              인터넷 게이트웨이   $0

  클러스터를 지워도                   클러스터를 지우면
  NAT 요금은 계속 나갑니다            공인 IP 요금도 사라집니다
```


요금이 아예 없어지는 것은 아닙니다. 공인 IP에는 시간당 \$0.005가 붙습니다. 하지만 이 요금은 노드에 붙어 있으므로 노드와 함께 `2-cluster` 층에 삽니다. 클러스터를 지우면 노드가 사라지고, 노드가 사라지면 공인 IP 요금도 함께 멈춥니다. 오래 두는 층을 \$0으로 지키면서 요금을 지우는 층으로 옮긴 것이 이 구성의 핵심입니다.


---


## 기본 VPC로도 되지만 코드 밖에 있습니다


여기까지 읽고 이런 생각이 드셨을 수도 있습니다. 퍼블릭 서브넷에 공인 IP를 주는 구성이라면, AWS 계정에 처음부터 있는 기본 VPC가 바로 그것 아닌가요? 실제로 제 계정의 서울 리전을 조회해 보면, 기본 VPC에는 이미 퍼블릭 서브넷이 가용 영역마다 하나씩 있습니다.


```bash
aws ec2 describe-subnets --filters Name=default-for-az,Values=true \
  --query 'Subnets[].[AvailabilityZone,CidrBlock,MapPublicIpOnLaunch,AvailableIpAddressCount]' \
  --output text | sort
```


```plain text
ap-northeast-2a   172.31.0.0/20    True   4091
ap-northeast-2b   172.31.16.0/20   True   4091
ap-northeast-2c   172.31.32.0/20   True   4091
ap-northeast-2d   172.31.48.0/20   True   4091
```


세 번째 칸의 `True`는 여기 뜨는 인스턴스에 공인 IP를 준다는 뜻이니, 이번 편에서 만들 것과 모양이 거의 같습니다. 그런데도 새로 만드는 이유는 기본 VPC가 코드 밖에 있기 때문입니다.


state에 들어 있지 않으니 OpenTofu는 이 VPC가 어떤 상태인지 모릅니다. 뒤에서 볼 로드밸런서용 태그를 더하려면 state 밖에 있는 리소스에 덧붙이는 식이 되는데, 그렇게 붙인 설정은 다음에 다시 만들 때 빠뜨리기 쉽습니다. 게다가 기본 VPC는 계정 안의 모든 실험이 함께 쓰는 공간입니다.


다른 이유로 띄운 인스턴스가 같은 서브넷에 섞이면, 나중에 무엇이 실습용이고 무엇이 아닌지 가려내기가 번거로워집니다. 이 시리즈가 ③편에서 콘솔 대신 코드로 가드레일을 만든 것과 같은 이유로, 네트워크도 처음부터 코드로 만들어 둡니다.


---


## 코드는 리소스 일곱 개로 끝납니다


이제 `0-bootstrap` 옆에 `1-network` 폴더를 나란히 만들고 그 안으로 들어갑니다. ③편을 막 마쳤다면 지금 `0-bootstrap` 안에 있을 테니 한 칸 올라가서 만들면 됩니다.


```bash
cd ..
mkdir 1-network && cd 1-network
```


먼저 state를 둘 곳을 정하는데, ③편의 버킷과 잠금 테이블을 그대로 쓰고 `key`만 이 폴더 이름으로 바꿉니다. 버킷이 이미 있으니 이번에는 로컬 state로 시작했다가 이사시키는 과정이 필요 없습니다.


```hcl
# backend.tf
terraform {
  backend "s3" {
    bucket         = "<본인만의-버킷-이름>"
    key            = "1-network/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "eks-lab-tflock"
    encrypt        = true
  }
}
```


`versions.tf`는 ③편의 것을 그대로 복사해 옵니다. 변수에는 VPC 전체의 주소 범위와, 서브넷을 둘 가용 영역 두 곳, 그리고 각 서브넷의 주소 범위를 적습니다.


```hcl
# variables.tf
variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

# EKS 는 서로 다른 AZ 두 곳 이상의 서브넷을 요구합니다
variable "azs" {
  type    = list(string)
  default = ["ap-northeast-2a", "ap-northeast-2c"]
}

# azs 와 순서대로 짝을 이룹니다. /20 은 서브넷마다 4,096개
variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.0.0/20", "10.0.16.0/20"]
}
```


가용 영역을 두 곳으로 잡은 것은 제 선택이 아니라 EKS의 요구 사항입니다. 클러스터를 만들 때 서로 다른 가용 영역에 있는 서브넷을 두 개 이상 주지 않으면 EKS가 받아 주지 않습니다. 서브넷마다 `/20`, 그러니까 주소 4,096개를 준 것은 넉넉해 보이지만 이유가 있습니다. EKS의 기본 네트워크 플러그인은 파드마다 VPC의 실제 주소를 나눠 줍니다. 그래서 노드만이 아니라 파드도 서브넷의 주소를 씁니다.


다음은 본체입니다. 리소스는 다섯 종류이고, 서브넷과 연결이 두 개씩이라 모두 일곱 개가 만들어집니다.


```hcl
# network.tf
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true # 둘 중 하나라도 꺼져 있으면
  enable_dns_support   = true # 노드가 클러스터에 등록되지 않습니다

  tags = { Name = "eks-lab-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "eks-lab-igw" }
}

resource "aws_subnet" "public" {
  count                   = length(var.azs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true # 여기 뜨는 노드는 공인 IP 를 받습니다

  tags = {
    Name                     = "eks-lab-public-${var.azs[count.index]}"
    "kubernetes.io/role/elb" = "1" # 인터넷용 로드밸런서를 둘 서브넷이라는 표시
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "eks-lab-public-rt" }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
```


### 세 줄이 빠져도 이번 편에서는 아무 일도 일어나지 않습니다


이 코드에서 가장 조심해야 할 것은 VPC의 DNS 두 줄과 서브넷의 `map_public_ip_on_launch`입니다. 셋 다 빠뜨려도 이번 편의 `apply`는 아무 문제 없이 끝나고, 문제가 드러나는 것은 다음 편에서 클러스터를 세운 뒤입니다. 에러는 15분쯤 기다린 끝에야 노드가 클러스터에 붙지 못했다는 두루뭉술한 문구로 나오기 때문에, 원인을 네트워크에서 찾기까지 한참이 걸립니다.


DNS 두 줄은 VPC 안의 인스턴스가 이름을 갖고 이름으로 서로를 찾게 해 줍니다. AWS 문서는 이 둘이 꺼져 있으면 노드가 클러스터에 등록되지 못한다고 적고 있습니다. `map_public_ip_on_launch`는 앞 절에서 고른 구성의 실체입니다. 관리형 노드 그룹은 노드에 공인 IP를 직접 붙여 주지 않으므로, 서브넷이 자동으로 주도록 켜 두어야 노드가 밖으로 나갈 수 있습니다.


서브넷의 `kubernetes.io/role/elb` 태그는 ⑪편에서 쓰입니다. 도메인과 HTTPS를 붙일 때 로드밸런서를 만드는 컨트롤러가 이 태그를 보고 어느 서브넷에 로드밸런서를 둘지 고릅니다.


예전 자료에는 `kubernetes.io/cluster/<클러스터 이름>` 태그도 함께 달라고 나와 있는데, 지금은 필요하지 않습니다. AWS 문서에 따르면 Kubernetes 1.18 이하에서 쓰던 태그이고, 로드밸런서 컨트롤러도 2.1.1 이하만 요구합니다. 이 태그를 빼면 네트워크가 클러스터 이름을 몰라도 되므로 두 층이 한결 독립적이 됩니다.


마지막으로 다음 편이 읽어 갈 값을 내보냅니다. `2-cluster`는 이 폴더의 state를 읽어서, 클러스터를 어느 VPC의 어느 서브넷에 둘지 정합니다.


```hcl
# outputs.tf
output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}
```


---


## 적용하고, 나가는 길이 하나뿐인지 확인합니다


파일을 다 만들었으면 초기화하고 계획을 봅니다. 버킷이 이미 있으므로 ③편처럼 state를 옮기는 단계 없이 `init` 한 번으로 저장소가 연결됩니다.


```bash
tofu init
tofu plan
```


`plan`의 마지막 줄이 `Plan: 7 to add, 0 to change, 0 to destroy.`여야 합니다. VPC, 인터넷 게이트웨이, 라우팅 테이블이 하나씩이고 서브넷과 라우팅 테이블 연결이 두 개씩입니다. 숫자가 맞으면 `tofu apply`를 실행하고 `yes`를 입력합니다. 만드는 것이 전부 무료 리소스이니 이 단계에서는 마음 편히 기다리셔도 됩니다.


`Apply complete!`가 나왔다고 끝난 것은 아닙니다. 앞 절의 세 줄이 정말 들어갔는지는 지금 확인해 두어야 다음 편에서 헤매지 않습니다. 서브넷부터 보는데, 아래 출력은 앞의 기본 VPC 조회와 같은 형식으로 이렇게 나와야 한다는 예상값입니다.


```bash
VPC=$(tofu output -raw vpc_id)

aws ec2 describe-subnets --filters Name=vpc-id,Values=$VPC \
  --query 'Subnets[].[AvailabilityZone,CidrBlock,MapPublicIpOnLaunch,AvailableIpAddressCount]' \
  --output text | sort
```


```plain text
ap-northeast-2a   10.0.0.0/20    True   4091
ap-northeast-2c   10.0.16.0/20   True   4091
```


가용 영역 두 곳에 서브넷이 하나씩 있고 세 번째 칸이 둘 다 `True`이면 됩니다. 마지막 칸이 4,096이 아니라 4,091인 이유는 AWS가 서브넷마다 주소 다섯 개를 자기 용도로 떼어 두기 때문입니다. 이어서 DNS와 나가는 길을 확인합니다.


```bash
for ATTR in enableDnsHostnames enableDnsSupport; do
  aws ec2 describe-vpc-attribute --vpc-id $VPC --attribute $ATTR --output text \
    --query "*.Value | [0]"                                # 두 번 모두 True 가 나와야 합니다
done

aws ec2 describe-nat-gateways --filter Name=vpc-id,Values=$VPC \
  --query 'length(NatGateways)'                            # 0 이 나와야 합니다

aws ec2 describe-route-tables --filters Name=vpc-id,Values=$VPC Name=tag:Name,Values=eks-lab-public-rt \
  --query 'RouteTables[].Routes[].[DestinationCidrBlock,GatewayId]' --output text
```


```plain text
10.0.0.0/16   local
0.0.0.0/0     igw-0123456789abcdef0
```


라우팅 테이블에는 두 줄이 나옵니다. 첫 줄의 `local`은 VPC 안끼리 오가는 길로 AWS가 모든 라우팅 테이블에 넣어 두는 것이고, 바깥으로 나가는 길은 둘째 줄의 인터넷 게이트웨이(`igw-`) 하나뿐입니다.


가운데의 NAT 게이트웨이 조회가 이 편의 비용을 확인하는 명령입니다. 이 VPC에서 시간당 요금이 붙을 수 있는 것은 NAT 게이트웨이뿐이었으니, 0이 나오면 이 층이 \$0이라는 뜻입니다. 이 VPC는 지우지 않고 시리즈가 끝날 때까지 둡니다.

> 원본 코드는 이 글보다 깁니다. 리소스 이름을 바꿨고, 공통 태그와 보안 검사기용 주석, 위에서 말한 클러스터 태그, 그리고 ⑩편 무렵에 더한 가용 영역별 출력을 덜어냈습니다. 원본 폴더에 있는 `db.tf`는 번외 ⑬편에서 다룰 작업에서 더한 것이라 이 글과 관계없습니다. 원본은 2026년 7월에 `plan`으로 7개 추가를 확인한 뒤 CI로 적용했습니다. 이 글의 줄인 코드는 저장소 설정을 뺀 채로 `validate`와 `plan`(7개 추가)까지 확인했고, 확인 명령의 출력 형식은 기본 VPC에 같은 명령을 돌려 맞췄습니다. 이 순서 그대로 `apply`해 보지는 못했으니, 막히는 곳이 있으면 알려 주시기 바랍니다.

---


## 이 네트워크의 값은 노드마다 붙는 공인 IP로 치릅니다


NAT를 빼서 아낀 값은 어디로 갔을까요? 앞에서 본 대로 노드마다 붙는 공인 IP로 옮겨 갔습니다. 노드 한 대가 한 시간 떠 있으면 \$0.005로 1센트도 안 되지만, 노드 수만큼 곱해지고 노드가 떠 있는 내내 붙습니다. 7월부터 10월 초까지 제 계정에 청구된 공인 IP 요금은 63.8시간분 \$0.319였습니다.


작은 돈이라 잊기 쉽다는 것이 오히려 문제입니다. 저도 노드 구성을 비교하면서 비용을 계산할 때 이 공인 IP 요금을 빼먹은 적이 있습니다. 작은 노드 두 대와 큰 노드 한 대를 비교하면서 인스턴스 요금만 더했는데, 공인 IP까지 넣으면 두 대 쪽이 시간당 \$0.005 더 비쌌습니다. 노드를 늘리는 계산을 할 때는 인스턴스 요금과 함께 이 값을 같이 곱해야 합니다.


보안 쪽의 값도 있습니다. 노드가 공인 IP를 갖는다는 것은 인터넷에서 노드의 주소가 보인다는 뜻입니다. 들어오는 요청은 ⑤편에서 클러스터와 함께 생기는 보안 그룹이 막지만, 숨어 있는 노드와 보이지만 막혀 있는 노드는 다른 이야기입니다.


실제로 원본 코드를 보안 검사기(tfsec)에 돌리면 경고가 두 건 나왔습니다. 하나는 서브넷이 공인 IP를 준다는 것이고, 다른 하나는 VPC의 트래픽 기록(flow logs)이 꺼져 있다는 것이었습니다. 둘 다 의도한 것이어서 이유를 주석으로 남기고 넘어갔지만, 학습용이니까 넘어간 것이지 문제가 아니라서 넘어간 것은 아닙니다.


그래서 실제 서비스라면 이 편의 선택을 그대로 쓰지 않습니다. ①편에서 운영과 달라지는 지점을 그때마다 적겠다고 했는데, 이 편에서는 노드를 프라이빗 서브넷으로 옮기는 것이 그 지점입니다. 나가는 길은 NAT 게이트웨이를 두거나, 노드가 쓰는 AWS 서비스마다 VPC 엔드포인트를 만들어 해결합니다. 어느 쪽이든 시간당 요금이 생기는데, 실제 서비스는 어차피 24시간 떠 있으니 그 요금을 내는 것이 맞습니다.


---


## 정리


| 만든 것           | 핵심 설정                        | 이유                         |
| -------------- | ---------------------------- | -------------------------- |
| VPC            | `10.0.0.0/16`, DNS 두 줄 켬     | 꺼져 있으면 노드가 클러스터에 등록되지 않습니다 |
| 퍼블릭 서브넷 2개     | 가용 영역 2곳, `/20`, 공인 IP 자동 부여 | EKS의 최소 요건이고, 파드도 주소를 씁니다  |
| 인터넷 게이트웨이와 라우팅 | `0.0.0.0/0` → IGW, NAT 없음    | 오래 두는 층에 시간당 요금을 두지 않습니다   |
| 로드밸런서 태그       | `kubernetes.io/role/elb = 1` | ⑪편의 로드밸런서가 이 서브넷을 찾습니다     |


네트워크를 만드는 것 자체는 무료지만, 노드가 바깥으로 나가는 길에는 어떻게든 요금이 붙습니다. 그 요금을 피할 수는 없으니 이 편에서는 요금이 붙을 자리를 골랐고, 오래 두는 층이 아니라 실습이 끝나면 지워지는 층에 두었습니다. 무엇을 만들지보다 어느 층에 둘지를 먼저 묻는 습관은 다음 편부터 돈이 나가기 시작하면 더 중요해집니다.


다음 편에서는 드디어 이 VPC 위에 첫 클러스터를 세웁니다. 이 시리즈에서 처음으로 돈이 나가는 편이고, 세운 클러스터를 같은 날 부수고 정말 사라졌는지 확인하는 데까지 갑니다.


---


## 참고

- [Amazon EKS, View Amazon EKS networking requirements for VPC and subnets](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [eksctl, VPC Configuration](https://docs.aws.amazon.com/eks/latest/eksctl/vpc-configuration.html)
- [Amazon VPC 요금](https://aws.amazon.com/vpc/pricing/)
- [Terraform AWS Provider, aws_subnet](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/subnet)
- NAT 게이트웨이와 공인 IPv4 단가는 2026-11-06에 AWS Pricing API로 서울 리전(`ap-northeast-2`)을 조회한 값입니다.
- 비용은 실제 청구 기록이고, 코드는 원본의 `plan` 결과로 확인했습니다. 줄인 코드의 `apply` 뒤 출력은 예상값입니다. 원본 작업 일지와 전체 코드는 [switch-job-quest](https://github.com/bangddong/switch-job-quest) 레포에 있습니다.
> 이 글의 그림은 AI가 코드 블록 안 글자로 그렸습니다. 단가는 위 Pricing API 조회 값이고, 그림보다 본문의 숫자를 기준으로 읽어 주시기 바랍니다.
