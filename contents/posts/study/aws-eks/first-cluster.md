---
title: '지웠다는 말은 AWS가 해야 한다. EKS 실습기 ⑤, 첫 클러스터를 세우고 부수는 법'
date: '2026-11-09'
tags:
  - AWS
  - EKS
series: AWS EKS 실습기
emoji: "\U0001F3D7️"
---
> **AWS 프리티어 \$200으로 EKS 실습하기 ⑤** · 💰 이 편에서 처음 돈이 나갑니다. 비용 약 **\$0.1**

`tofu apply`를 치기 직전에 손이 멈춘 적이 있으신가요? 계획 출력은 화면을 넘어가도록 길게 이어집니다. 그 안 어딘가에 시간당 요금이 붙는 리소스가 섞여 있다는 것만 압니다. 지금까지 네 편은 무엇을 만들든 \$0이었지만, 이번 편의 `apply`는 누르는 순간부터 시계가 돕니다. ①편에서 말씀드린 대로 컨트롤플레인은 놀고 있어도 시간당 \$0.10을 받기 때문입니다.


그래서 이번 편은 한 번에 끝까지 갑니다. ④편의 VPC 위에 클러스터를 세우고 노드가 붙었는지 확인한 뒤, 같은 자리에서 부숩니다. 그리고 정말 사라졌는지 AWS에 직접 물어보는 데까지가 한 묶음입니다. 제가 처음 이 왕복을 했을 때는 마지막 확인까지 50분쯤 걸렸고, 비용은 \$0.1이 되지 않았습니다. 그 50분 동안 어디서 돈이 나가고 어디서 실수하기 쉬운지 순서대로 따라가 보겠습니다.

> 지웠다는 말은 AWS가 해야 한다.

---


## 클러스터 하나는 리소스 열네 개이고, 그중 돈을 받는 것은 둘뿐입니다


EKS 클러스터를 만든다고 하면 리소스 하나를 떠올리기 쉽습니다. 하지만 실제로는 서로 기대는 리소스 열네 개가 함께 만들어집니다. 클러스터가 내 계정에서 AWS를 움직이려면 권한이 필요하고, 노드가 클러스터에 붙는 데도 권한이 따로 필요합니다. 노드 위에서 네트워크와 이름 풀이를 맡을 구성 요소도 설치해야 합니다. 아래 그림은 열네 개를 묶어 늘어놓은 것이니, 오른쪽 요금 칸이 어디서 차 있는지 보시기 바랍니다.


```plain text
2-cluster 층 (리소스 14개)                         요금
IAM 역할 2개, 정책 연결 4개                        $0
EKS 클러스터 (컨트롤플레인)                        $0.10/시간   ← 대부분
 ├─ OIDC 공급자 1개                                $0
 ├─ 접근 항목, 권한 연결 2개                       $0
 ├─ 애드온 3개 (vpc-cni, kube-proxy, coredns)      $0
 └─ 노드 그룹 1개 → EC2 t4g.small 1대              $0.0208/시간
                    + 공인 IP 1개                  $0.005/시간
                    + 디스크 20GB                  월 $1.82
```


시간당 요금이 붙는 것은 컨트롤플레인과 노드 그룹 둘뿐이고, 공인 IP까지 합쳐 시간당 \$0.13쯤 됩니다. 나머지 열두 개는 권한과 설정이라 몇 시간을 두어도 요금이 없습니다. 노드의 디스크는 월 단위로 값이 매겨지지만, 노드와 함께 생기고 함께 지워지니 디스크도 켜 둔 시간만큼만 냅니다. 이번 편에서 아낄 것은 리소스의 개수가 아니라 클러스터가 떠 있는 시간입니다.


---


## 코드는 네트워크 층이 남긴 출력을 읽는 데서 시작합니다


이제 `1-network` 옆에 `2-cluster` 폴더를 만듭니다. ④편을 막 마쳤다면 `1-network` 안에 있을 테니, 이번에도 한 칸 올라가서 만들면 됩니다.


```bash
cd ..
mkdir 2-cluster && cd 2-cluster
```


`backend.tf`는 ④편의 것을 복사해서 `key`만 `2-cluster/terraform.tfstate`로 바꿉니다. `versions.tf`도 가져오는데, 이번에는 `tls` 공급자가 하나 더 필요합니다. 뒤에서 만들 OIDC 공급자가 클러스터 인증서의 지문을 요구하고, 그 지문을 읽는 것이 `tls` 공급자입니다.


```hcl
# versions.tf
terraform {
  required_version = ">= 1.8.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = "ap-northeast-2"
}
```


클러스터를 둘 서브넷은 직접 적지 않고 네트워크 층의 state에서 읽어 옵니다. ④편 끝에서 내보낸 `public_subnet_ids`를 아래 데이터 소스가 가져오니, 서브넷 ID를 손으로 옮겨 적을 일이 없습니다. 네트워크를 다시 만들어 ID가 바뀌어도 이쪽 코드는 그대로입니다.


다만 `bucket`과 `key`는 ④편의 `backend.tf`와 똑같아야 하고, 한 글자라도 다르면 state를 찾지 못해 `plan`에서 멈춥니다. 돈이 나가기 전에 멈추는 것이니 고쳐서 다시 돌리면 됩니다.


```hcl
# remote-state.tf
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "<본인만의-버킷-이름>"
    key    = "1-network/terraform.tfstate"
    region = "ap-northeast-2"
  }
}
```


변수는 클러스터 이름과 쿠버네티스 버전, 노드의 인스턴스 종류 세 개뿐입니다.


```hcl
# variables.tf
variable "cluster_name" {
  type    = string
  default = "eks-lab"
}

# apply 직전에 표준 지원 중인 버전인지 다시 확인합니다
variable "kubernetes_version" {
  type    = string
  default = "1.36"
}

variable "node_instance_type" {
  type    = string
  default = "t4g.small"
}
```


### 버전은 apply 직전에 다시 확인합니다


`1.36`은 고정값처럼 보이지만, 적어 둔 날과 apply하는 날 사이에 지원이 끝날 수 있습니다. 저도 처음 계획에는 `1.32`를 적어 두었는데, 코드를 쓰다가 조회해 보니 이미 표준 지원 목록에 없었고, `1.33`마저 9일 뒤에 지원이 끝날 참이었습니다. 그래서 apply하기 전에 아래 명령으로 지원 중인 버전을 한 번 더 보는데, 이 조회에는 요금이 없습니다.


```bash
aws eks describe-cluster-versions --region ap-northeast-2 \
  --query 'clusterVersions[?status==`STANDARD_SUPPORT`].[clusterVersion,defaultVersion,endOfStandardSupportDate]' \
  --output table
```


```plain text
------------------------------------------------
|            DescribeClusterVersions           |
+------+--------+------------------------------+
|  1.37|  True  |  2027-12-01T09:00:00+09:00   |
|  1.36|  False |  2027-08-02T09:00:00+09:00   |
|  1.35|  False |  2027-03-27T09:00:00+09:00   |
|  1.34|  False |  2026-12-02T09:00:00+09:00   |
+------+--------+------------------------------+
```


2026년 11월 6일에 조회하면 기본 버전은 이미 `1.37`입니다. 그래도 이 시리즈는 `1.36`을 그대로 씁니다. ②편에서 설치한 `kubectl`이 1.36이고, 제가 실제로 띄워서 확인한 것도 1.36이기 때문입니다. 지원이 끝나는 2027년 8월 2일도 제 크레딧 만료일인 2027년 1월 15일보다 한참 뒤입니다.


확인할 것은 두 가지로, 내 버전이 목록에 있는지와 종료일이 실습 기간보다 넉넉한지입니다. 한 가지 함정은 필터 이름입니다. `status`를 다른 이름으로 잘못 쓰면 오류 없이 아무것도 출력되지 않습니다. 지원 중인 버전이 하나도 없는 것처럼 보이더라도, 당황하지 말고 필터 이름부터 확인하시면 됩니다.


---


## 권한은 사람보다 클러스터와 노드에 먼저 줍니다


EKS에서 권한이라고 하면 누구의 권한을 먼저 만들어야 할까요? 내 IAM 사용자를 떠올리기 쉽지만, 이 층에서 가장 먼저 만드는 권한은 사람이 아니라 AWS 서비스의 것입니다. 컨트롤플레인은 내 계정 안에 네트워크 인터페이스와 보안 그룹을 만들어야 합니다. 노드는 클러스터에 자신을 등록하고 컨테이너 이미지를 받아 와야 합니다. 둘 다 내 손을 거치지 않는 일이라서, 각자가 쓸 역할(role)을 미리 만들어 둡니다.


```hcl
# iam.tf
data "aws_iam_policy_document" "cluster_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cluster" {
  name               = "${var.cluster_name}-cluster-role"
  assume_role_policy = data.aws_iam_policy_document.cluster_assume.json
}

resource "aws_iam_role_policy_attachment" "cluster" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

data "aws_iam_policy_document" "node_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "node" {
  name               = "${var.cluster_name}-node-role"
  assume_role_policy = data.aws_iam_policy_document.node_assume.json
}

resource "aws_iam_role_policy_attachment" "node" {
  for_each = toset([
    "AmazonEKSWorkerNodePolicy",          # 클러스터에 노드로 등록
    "AmazonEKS_CNI_Policy",               # 파드에 VPC 주소 나눠 주기
    "AmazonEC2ContainerRegistryReadOnly", # 이미지 받아 오기
  ])
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/${each.value}"
}
```


역할마다 붙은 `assume_role_policy`는 누가 이 역할을 쓸 수 있는지 정합니다. 클러스터 역할은 `eks.amazonaws.com`만, 노드 역할은 `ec2.amazonaws.com`만 쓸 수 있으니, 같은 계정의 다른 사용자나 서비스가 이 권한을 빌려 갈 수 없습니다.


노드 쪽 정책 세 개는 AWS 문서가 노드 역할에 요구하는 것으로, 주석에 적은 일에 하나씩 대응합니다. 셋 중 하나라도 빠지면 인스턴스는 떠도 쓸 수 있는 노드가 되지 못합니다.


---


## 클러스터를 만든 사람도 저절로 관리자가 되지는 않습니다


클러스터 본체는 `vpc_config`의 `subnet_ids`로 ④편의 퍼블릭 서브넷 두 개를 받습니다. 가용 영역이 다른 서브넷 두 개라는 EKS의 요구를 ④편에서 맞춰 둔 것이 여기서 쓰입니다. 아래쪽의 OIDC 공급자는 이번 편에서 쓰지 않습니다. ⑧편에서 파드에 AWS 권한을 줄 때 필요한 신원 확인 창구인데, 그 주소가 클러스터를 만들 때 정해지므로 지금 함께 만들어 둡니다.


```hcl
# cluster.tf
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  version  = var.kubernetes_version
  role_arn = aws_iam_role.cluster.arn

  vpc_config {
    subnet_ids              = data.terraform_remote_state.network.outputs.public_subnet_ids
    endpoint_public_access  = true
    endpoint_private_access = false
  }

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = false
  }

  depends_on = [aws_iam_role_policy_attachment.cluster]
}

# 뒤 편에서 파드에 AWS 권한을 줄 때 쓰는 신원 확인 창구
data "tls_certificate" "oidc" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "oidc" {
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.oidc.certificates[0].sha1_fingerprint]
}
```


코드에는 없지만, 클러스터가 만들어질 때 EKS가 클러스터 보안 그룹을 하나 함께 만듭니다. ④편에서 노드로 들어오는 요청을 막는다고 한 것이 이 보안 그룹입니다. 관리형 노드 그룹의 노드에 자동으로 붙고, 클러스터를 지우면 함께 사라집니다. 다만 내가 만든 것이 아니라 state에는 없으므로, 뒤에서 정리를 확인할 때 따로 찾아봅니다.


눈여겨보실 것은 `access_config`입니다. EKS는 기본값으로 클러스터를 만든 IAM 사용자에게 관리자 권한을 자동으로 줍니다. 여기서는 `bootstrap_cluster_creator_admin_permissions`를 `false`로 꺼서 그 자동 권한을 받지 않습니다. 켜 둔 채로 아래의 접근 항목을 코드로 또 만들면, 같은 사용자의 항목이 두 번 생기려다 apply가 실패하기 때문입니다.


대신 `authentication_mode`를 `API`로 두어, 누가 들어올지를 접근 항목(access entry)으로만 정합니다. 클러스터에 들어올 권한은 만든 사람이라서 생기는 것이 아니라, 코드에 적힌 접근 항목이 있어서 생기는 것입니다.


```hcl
# access.tf
data "aws_caller_identity" "current" {}

resource "aws_eks_access_entry" "admin" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = data.aws_caller_identity.current.arn
}

resource "aws_eks_access_policy_association" "admin" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = data.aws_caller_identity.current.arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

  access_scope {
    type = "cluster"
  }

  depends_on = [aws_eks_access_entry.admin]
}
```


`aws_caller_identity`는 지금 `tofu`를 실행하는 사람이 누구인지 알려 주는 데이터 소스입니다. ②편에서 만든 IAM 사용자로 apply하면 그 사용자가 접근 항목에 들어갑니다. 여기에 `AmazonEKSClusterAdminPolicy`가 붙어 클러스터 전체의 관리자가 됩니다.


그래서 apply한 사람과 `kubectl`을 쓸 사람이 같다면 손댈 것이 없습니다. 반대로 apply와 `kubectl`의 자격 증명이 다르면, apply는 성공했는데 `kubectl`만 거부당합니다. apply 전에 `aws sts get-caller-identity`로 지금 누구인지 보아 두시기 바랍니다.


---


## 노드는 한 대를 온디맨드로 둡니다


노드를 띄우는 일은 EC2 인스턴스를 직접 만드는 대신 EKS의 노드 그룹에 맡깁니다. 인스턴스 종류와 대수만 정해 주면 EKS가 인스턴스를 띄웁니다. 이어서 그 인스턴스가 클러스터에 노드로 붙을 때까지 기다립니다.


④편에서 DNS 설정이나 공인 IP 자동 부여가 빠지면 15분쯤 기다린 끝에 실패한다고 했는데, 그때 기다리는 것이 이 단계입니다. 노드 그룹이 `NodeCreationFailure`로 실패했다면 ④편의 확인 명령으로 돌아가 DNS 두 값과 서브넷의 공인 IP 설정부터 다시 보시기 바랍니다.


```hcl
# nodes.tf
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.cluster_name}-ng"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = data.terraform_remote_state.network.outputs.public_subnet_ids

  ami_type       = "AL2023_ARM_64_STANDARD" # t4g 는 ARM(Graviton)
  instance_types = [var.node_instance_type]
  capacity_type  = "ON_DEMAND" # 신규 계정은 Spot 한도가 0 입니다

  scaling_config {
    desired_size = 1
    min_size     = 1
    max_size     = 2
  }

  depends_on = [aws_iam_role_policy_attachment.node]
}
```


`capacity_type`에는 사연이 있습니다. 처음 계획에서는 요금이 싼 Spot 인스턴스를 쓸 생각이었습니다. 그런데 첫 apply 전에 신규 계정의 Spot vCPU 한도가 0이라는 것을 확인하고 온디맨드로 바꿨습니다.


한도가 0이면 Spot 인스턴스를 한 대도 받지 못하니, 그대로 두었다면 첫 apply는 노드 그룹에서 실패했을 것입니다. Service Quotas에서 한도를 올려 받으면 Spot도 쓸 수 있지만, 한 대를 짧게 쓰는 실습에서는 아낄 돈이 크지 않습니다.


노드가 섰다고 바로 일을 받을 수 있는 것은 아닙니다. 파드에 주소를 주고 클러스터 안의 이름을 풀어 줄 구성 요소가 있어야 하는데, EKS는 이것들을 애드온으로 설치합니다.


```hcl
# addons.tf
resource "aws_eks_addon" "vpc_cni" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "vpc-cni"
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "kube-proxy"
}

resource "aws_eks_addon" "coredns" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "coredns"
  depends_on   = [aws_eks_node_group.main] # 파드가 올라갈 노드가 먼저 있어야 합니다
}
```


애드온 세 개는 노드가 제 역할을 하는 데 필요한 구성 요소입니다. `vpc-cni`는 파드에 VPC 주소를 나눠 주고, `kube-proxy`는 서비스 주소로 온 요청을 파드로 넘깁니다. `coredns`는 클러스터 안의 이름을 주소로 바꿔 줍니다.


`coredns`에만 `depends_on`을 붙인 것은, 노드 위에 파드로 떠야 준비가 끝나는 애드온이기 때문입니다. 노드보다 먼저 설치되면 파드가 올라갈 자리가 없어 준비 상태에 이르지 못하고, apply는 그 상태가 풀리기를 기다리다 시간 초과로 끝납니다.


마지막으로 다음 편에서 쓸 클러스터 이름을 내보냅니다.


```hcl
# outputs.tf
output "cluster_name" {
  value = aws_eks_cluster.main.name
}
```


---


## plan에서 볼 것은 개수보다 뒤의 0 두 개입니다


파일이 다 모였으면 초기화하고 계획을 봅니다. 여기까지는 여전히 \$0입니다. `-out`으로 계획을 파일에 저장해 두면, 다음 단계의 apply가 방금 본 계획을 그대로 실행합니다.


```bash
tofu init
tofu plan -out=cluster.tfplan
```


```plain text
Plan: 14 to add, 0 to change, 0 to destroy.
```


`14`는 앞의 그림에서 센 열네 개와 같습니다. 하지만 이 숫자보다 중요한 것은 뒤의 `0 to change, 0 to destroy`입니다. 개수는 이 층에 코드를 더할수록 늘어나서, 제 원본도 열네 개로 시작해 8월에는 스물아홉 개가 됐습니다.


반면 빈 곳에 새로 짓는 계획이라면 고치거나 부술 대상이 없으니 뒤의 두 숫자는 언제나 0입니다. 하나라도 0이 아니면 state에 지난번의 무언가가 남아 있다는 뜻이므로, apply하지 말고 그것부터 찾습니다.


---


## apply를 누른 순간부터 시계가 돕니다


이제 돈이 나가기 시작합니다. 저장해 둔 계획을 적용합니다.


```bash
tofu apply cluster.tfplan
```


```plain text
aws_eks_cluster.main: Creation complete after 7m54s [id=eks-lab]
aws_eks_addon.vpc_cni: Creation complete after 14s [id=eks-lab:vpc-cni]
aws_eks_addon.kube_proxy: Creation complete after 24s [id=eks-lab:kube-proxy]
aws_eks_node_group.main: Creation complete after 1m27s [id=eks-lab:eks-lab-ng]
aws_eks_addon.coredns: Creation complete after 14s [id=eks-lab:coredns]

Apply complete! Resources: 14 added, 0 changed, 0 destroyed.
```


위 출력은 제 첫 apply 날 일지에 적은 소요 시간을 출력 모양으로 다시 적은 것이고, 이름은 이 글의 코드에 맞췄습니다. 전체 10분 가운데 8분이 컨트롤플레인을 기다리는 시간이라, 그동안 화면에는 `Still creating...`만 이어집니다.


자리를 비우고 싶어지는 시간이지만, apply가 중간에 실패해도 만들어진 리소스는 남아서 요금이 나갑니다. 실패하면 원인을 고쳐 다시 apply합니다. 오늘은 접을 생각이라면 `tofu destroy`로 만들어진 것을 지운 뒤에 자리를 뜹니다.


---


## 노드가 Ready이면 클러스터가 선 것입니다


apply가 끝났다고 클러스터를 쓸 수 있는 것은 아닙니다. 노드가 클러스터에 붙어 일을 받을 준비가 되었는지는 `kubectl`로 물어봐야 압니다. 그 전에 내 컴퓨터에 클러스터의 주소와 인증 방법을 알려 줘야 합니다.


```bash
aws eks update-kubeconfig --name eks-lab --region ap-northeast-2
kubectl get nodes -o wide -L kubernetes.io/arch
```


```plain text
Added new context arn:aws:eks:ap-northeast-2:123456789012:cluster/eks-lab to /Users/<사용자>/.kube/config
NAME              STATUS   ROLES    AGE   VERSION        INTERNAL-IP   EXTERNAL-IP   ...   ARCH
ip-10-0-8-101…    Ready    <none>   3m    v1.36.2-eks…   10.0.8.101    <공인 IP>     ...   arm64
```


`update-kubeconfig`는 `~/.kube/config`에 접속 정보를 적어 둘 뿐이고, 들어갈 수 있는지는 앞의 접근 항목이 정합니다. 출력에서는 `STATUS`가 `Ready`인지, `VERSION`이 1.36인지 봅니다.


`EXTERNAL-IP`에 공인 IP가 붙어 있는지도 봅니다. 이것은 ④편에서 NAT 없이 노드를 인터넷에 내보내려고 고른 설계가 동작한다는 확인입니다. `ARCH`의 `arm64`는 노드가 Graviton 인스턴스라는 뜻입니다.


노드가 섰으면 그 위에 시스템 파드들이 떴는지도 봅니다.


```bash
kubectl get pods -n kube-system
```


```plain text
NAME                       READY   STATUS    RESTARTS   AGE
aws-node-xxxxx             2/2     Running   0          3m
coredns-xxxxxxxxxx-xxxxx   1/1     Running   0          3m
coredns-xxxxxxxxxx-xxxxx   1/1     Running   0          3m
kube-proxy-xxxxx           1/1     Running   0          3m
```


`aws-node`가 `vpc-cni` 애드온의 실체입니다. `coredns` 두 개와 `kube-proxy`까지 네 개가 전부 `Running`이면 클러스터가 제대로 선 것입니다. 그런데 이 노드에는 파드가 몇 개나 더 들어갈 수 있을까요?


```bash
kubectl get node -o jsonpath='{.items[0].status.allocatable.pods}'
```


```plain text
11
```


열한 개라는 숫자는 메모리나 CPU가 아니라 네트워크 인터페이스에서 나옵니다. `vpc-cni`는 파드마다 VPC의 실제 주소를 하나씩 줍니다. 그런데 `t4g.small`은 인터페이스를 세 개까지 붙일 수 있고, 인터페이스마다 주소가 네 개씩입니다.


첫 주소는 인터페이스 자신의 몫이라 파드에 줄 수 있는 것은 3 × (4 − 1) = 9개입니다. 여기에 노드의 주소를 그대로 쓰는 파드 몫 2를 더해 11이 됩니다. 시스템 파드 네 개를 빼면 일곱 자리가 남으니, 이 클러스터에서는 메모리보다 이 숫자가 먼저 바닥날 수 있습니다.


---


## 확인이 끝나면 바로 부수고, 사라졌는지 AWS에 묻습니다


확인이 끝났으면, 다음 편으로 바로 이어 갈 생각이 아닌 한 지금 부숩니다. `tofu destroy`는 지울 목록을 보여 주고 `yes`를 입력받은 뒤에 시작합니다.


```bash
tofu destroy
```


```plain text
aws_eks_node_group.main: Destruction complete after 2m16s
aws_eks_cluster.main: Destruction complete after 1m23s

Destroy complete! Resources: 14 destroyed.
```


지우는 순서는 만든 순서의 반대입니다. 노드에 기대는 coredns가 먼저 지워집니다. 이어서 노드 그룹과 접근 항목, 나머지 애드온, OIDC 공급자가 함께 지워지고, 컨트롤플레인과 IAM 역할 순으로 끝납니다. 여기서는 마지막 줄의 숫자가 apply 때의 `14`와 같은지 봅니다. 숫자가 모자라면 일부가 지워지지 않았다는 뜻이고, 그대로 자리를 뜨면 남은 것이 요금이 됩니다.


그러면 `Destroy complete!`를 보았으니 끝난 것일까요? `tofu destroy`는 state에 적힌 것만 알고, 그 바깥에서 생긴 것은 모릅니다. ①편에서 말씀드린 하룻밤의 사고도 destroy를 실행해 두고 끝까지 지켜보지 않은 데서 시작됐습니다. 그래서 이 시리즈는 destroy 뒤에 AWS에 직접 묻는 단계를 둡니다. 아래 명령은 전부 조회라서 요금이 없습니다.


```bash
R=ap-northeast-2
tofu state list
aws eks list-clusters --region $R
aws ec2 describe-instances --region $R \
  --filters Name=instance-state-name,Values=pending,running,stopping,stopped \
  --query 'Reservations[].Instances[].InstanceId'
aws ec2 describe-volumes --region $R --filters Name=status,Values=available \
  --query 'Volumes[].VolumeId'
aws ec2 describe-security-groups --region $R \
  --filters Name=tag:aws:eks:cluster-name,Values=eks-lab \
  --query 'SecurityGroups[].GroupId'
aws iam list-roles --query "Roles[?starts_with(RoleName,'eks-lab')].RoleName"
aws iam list-open-id-connect-providers \
  --query "OpenIDConnectProviderList[?contains(Arn,'oidc.eks')].Arn"
```


```plain text
{
    "clusters": []
}
[]
[]
[]
[]
[]
```


`tofu state list`는 아무것도 출력하지 않고, 클러스터 목록은 빈 배열, 나머지 다섯 개는 `[]`가 나와야 합니다. 인스턴스를 물을 때 `terminated`를 빼는 것은, 종료된 인스턴스가 한동안 목록에 남지만 요금은 붙지 않기 때문입니다.


주인 없는 디스크(`available`)와 클러스터 보안 그룹은 state 밖이라 destroy가 보증하지 않습니다. ⑩편부터는 일부러 남기는 디스크가 하나 생기는데, 그때는 그 하나만 보여야 합니다. 첫 왕복 날 일지에서 이 명령들에 해당하는 항목은 state, 클러스터, 인스턴스, 디스크, 보안 그룹입니다. 모두 비어 있었고, 그제야 이 층을 지웠다고 적었습니다. IAM 역할과 OIDC 공급자 두 줄은 이 글을 쓰면서 더한 것입니다.


---


## 이 클러스터는 켜 둔 시간과 기다린 시간으로 값을 치릅니다


첫 왕복은 apply를 시작해 마지막 확인을 마칠 때까지 50분쯤 걸렸습니다. 정가로 계산하면 컨트롤플레인이 떠 있던 40분쯤이 \$0.07, 노드가 \$0.01 남짓이라 합쳐서 \$0.1이 되지 않습니다. ①편에서 말씀드린 대로 제 청구서에는 노드 요금이 \$0로 찍혔으니, 실제로 나간 돈은 이보다도 적습니다.


그런데 50분 가운데 명령이 실제로 일한 시간은 apply 10분과 destroy 5분 정도였고, 나머지는 확인하고 기다린 시간이었습니다. 이 방식은 쓰지 않는 시간의 요금을 없애는 대신, 실습할 때마다 클러스터가 설 때까지 10분을 기다리게 합니다.


③편에서 걸어 둔 예산 알림도 이 왕복을 지켜 주지는 못합니다. 이 클러스터를 하루 꼬박 켜 두어도 \$3쯤이라 첫 알림 문턱인 \$10에 닿지 않고, 청구 데이터가 예산에 반영되기까지 길게는 하루가 걸립니다. ③편에서 말씀드린 대로 알림은 며칠씩 이어지는 사고를 막는 그물입니다. 오늘 켠 클러스터를 오늘 껐는지는 앞의 조회 명령으로 직접 확인해야 합니다.


보안 쪽에서 내려놓은 것도 있습니다. API 엔드포인트를 공개로 두고 허용 범위를 적지 않았으니, 기본값대로 인터넷 어디서나 접속을 시도할 수 있습니다. 실제로 들어오는 것을 막는 쪽은 IAM 인증과 접근 항목입니다. 원본 코드를 보안 검사기(tfsec)에 돌리면 이 공개 엔드포인트 두 건과 함께, 컨트롤플레인 로그와 시크릿 암호화가 꺼져 있다는 경고가 나왔습니다.


로그는 CloudWatch에, 암호화는 KMS에 요금이 붙어서 학습용으로는 끄고 이유를 주석으로 남겼습니다. 하지만 실제 서비스라면 엔드포인트를 회사 주소로 좁히거나 비공개로 돌리고, 로그와 암호화도 켭니다. 이 편에서 운영과 갈라지는 지점은 엔드포인트와 로그, 암호화 세 가지입니다.


마지막으로 state의 경계입니다. 지금은 열네 개가 전부 OpenTofu가 만든 것이라 destroy 한 번으로 정리됩니다. 하지만 ⑨편부터는 쿠버네티스가 직접 디스크를, ⑪편에서는 로드밸런서를 만들기 시작합니다. 그런 것은 state에 없어서 `tofu destroy`가 지우지 못하므로, 클러스터를 부수기 전에 쿠버네티스 쪽에서 먼저 지워야 합니다. 그 순서는 그 편들에서 다시 적겠습니다.


---


## 정리


| 단계    | 명령                                             | 확인할 것                                  |
| ----- | ---------------------------------------------- | -------------------------------------- |
| 버전    | `aws eks describe-cluster-versions`            | 1.36이 목록에 있고 종료일이 넉넉한가                 |
| 계획    | `tofu plan -out=cluster.tfplan`                | `14 to add, 0 to change, 0 to destroy` |
| 적용    | `tofu apply cluster.tfplan`                    | 약 10분 뒤 `14 added`                     |
| 확인    | `kubectl get nodes`, `get pods -n kube-system` | `Ready`, 1.36, 공인 IP, 시스템 파드 4개        |
| 부수기   | `tofu destroy`                                 | `14 destroyed`                         |
| 사라졌는지 | `aws eks list-clusters` 외 6개                   | 전부 빈 목록                                |


클러스터를 세우는 것은 10분이면 끝납니다. 이번 편에서 손에 익혀야 할 것은 세우는 법보다 부순 뒤에 묻는 법입니다. `Destroy complete!`는 OpenTofu가 아는 범위의 보고이고, 요금이 멈췄다는 말은 AWS의 조회 결과로만 들을 수 있습니다. 이 왕복을 한 번 끝까지 해 두면, 다음부터는 클러스터를 망가뜨려도 겁낼 이유가 없습니다.


다음 편에서는 같은 클러스터를 다시 세우고, 그 위에 컨테이너 이미지를 올려 첫 앱을 띄웁니다.


---


## 참고

- [Amazon EKS, Amazon EKS cluster IAM role](https://docs.aws.amazon.com/eks/latest/userguide/cluster-iam-role.html)
- [Amazon EKS, Amazon EKS node IAM role](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
- [Amazon EKS, Grant IAM users access to Kubernetes with EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Amazon EKS, Simplify node lifecycle with managed node groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [Amazon EKS, Understand the Kubernetes version lifecycle on EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Amazon EKS 요금](https://aws.amazon.com/eks/pricing/)
- 디스크 단가(gp3, GB당 월 \$0.0912)는 2026-11-06에 AWS Pricing API로 서울 리전을 조회한 값이고, 지원 버전 표도 같은 날 조회했습니다.
> 원본 코드는 이 글보다 깁니다. 이름을 바꿨고, 보안 검사기용 주석과 노드 교체 설정, 기본값과 같은 엔드포인트 허용 범위와 접근 항목의 `type`, 이번 편에서 쓰지 않는 출력 세 개, 변수 설명을 덜어 냈고, `providers.tf`는 `versions.tf`에 합쳤습니다. 리전과 용량 종류, 노드 대수 변수는 값을 코드에 바로 적었고, 노드 정책 연결 세 개는 `for_each` 하나로 묶었으며, AWS 공급자 버전 조건은 ③편에 맞춰 `~> 5.60`으로 적었습니다. 원본 폴더에는 뒤 편에서 더한 데이터베이스와 시크릿 코드가 함께 있지만, 이 글의 코드는 제가 첫 apply를 한 2026년 7월 24일의 구성(리소스 14개)과 같습니다. 줄인 코드는 저장소 설정 없이 네트워크 출력을 임시 값으로 넣어 `validate`와 `plan`(14개 추가)까지 확인했고, 이 순서 그대로 `apply`해 보지는 못했습니다. `apply`와 `destroy`의 출력은 그날 일지에 적은 소요 시간으로 다시 적은 것이니, 막히는 곳이 있으면 알려 주시기 바랍니다. 정리 확인 명령의 빈 출력은 클러스터가 없는 지금의 제 계정에 같은 명령을 돌려 맞췄습니다.
>
> 이 글의 그림은 AI가 코드 블록 안 글자로 그렸습니다. 단가는 ①편의 표와 위 조회 값입니다.
>
>
