---
title: 'Ingress는 길이 아니라 주문서다. EKS 실습기 ⑪, 도메인과 HTTPS 붙이기'
date: '2026-11-21'
tags:
  - AWS
  - EKS
series: AWS EKS 실습기
emoji: ''
---
> **AWS 프리티어 \$200으로 EKS 실습하기 ⑪** · 💰 클러스터를 켜는 한 시간 남짓에 정가로 약 **\$0.2**, 인증서는 **\$0**

⑩편까지 앱을 볼 때는 늘 `kubectl port-forward`를 썼습니다. 노트북의 포트를 클러스터 안의 파드에 이어 붙이는 방법이라 노트북을 덮으면 길도 함께 사라집니다. ⑥편에서는 Service를 `LoadBalancer`로 두지 않았습니다. 그렇게 만든 로드밸런서는 OpenTofu의 state 밖에 생겨서 `tofu destroy`가 지우지 못하기 때문입니다. 그렇다면 바깥에서 들어오는 길은 누가 만들고 누가 지워야 할까요?


이번 편에서는 그 길을 정식으로 냅니다. 쿠버네티스에 Ingress라는 주문서를 내고 그 주문서를 읽어 로드밸런서를 세우는 컨트롤러를 설치합니다. 그리고 내 도메인으로 인증서를 받아 HTTPS로 `hello from eks-lab`을 받아 봅니다. 본편은 이 편으로 끝나니 마지막에는 만든 것을 지우는 순서까지 확인합니다.

> 길은 컨트롤러가 내고, 인증서는 도메인이 기억한다.

---


## Ingress는 길이 아니라 주문서이고 길은 컨트롤러가 냅니다


Ingress라는 이름 때문에 이것을 들어오는 길 그 자체로 생각하기 쉽습니다. 하지만 Ingress는 "이 주소로 오는 요청은 이 Service로 보내 달라"고 적은 객체일 뿐입니다. 그 자체로는 아무 일도 하지 않고 로드밸런서를 실제로 세우는 것은 그 주문서를 지켜보는 Ingress 컨트롤러입니다. AWS에서는 AWS Load Balancer Controller(이하 컨트롤러)가 그 역할을 맡습니다.


```plain text
사람        kubectl apply -f k8s/ingress.yaml   → Ingress 객체가 생깁니다. 아직 아무 일도 없습니다
컨트롤러    Ingress 를 발견합니다               → 빌린 IAM 역할로 AWS API 를 부릅니다
AWS         ALB, 리스너, 타겟 그룹을 만듭니다   → 파드 IP 를 타겟으로 등록합니다
인터넷      https://<내 도메인>/hello           → ALB 가 파드로 곧장 보냅니다
```


그래서 컨트롤러가 없거나 제대로 못 뜨면 Ingress는 영원히 주문서로만 남습니다. `kubectl get ingress`에는 객체가 멀쩡히 보이고 주소 칸만 비어 있습니다. 무엇이 잘못됐는지 바로 알아채기 어려운 모습이라 이번 편의 절반은 컨트롤러를 제대로 띄우는 데 씁니다.


컨트롤러가 만든 로드밸런서도 ⑥편의 `LoadBalancer`처럼 state 밖에 있습니다. 대신 Ingress를 지우면 컨트롤러가 그것을 보고 로드밸런서를 함께 지워 줍니다. 그러니 정리할 때 Ingress를 먼저 지우기만 하면 되고 그 순서는 이 편의 끝에서 다시 봅니다. 아래 그림은 주문서 한 장이 로드밸런서가 되기까지의 다섯 칸입니다. 사람이 하는 일은 첫째 칸뿐이라는 점을 보시기 바랍니다.


![Ingress를 적용하면 컨트롤러가 그것을 읽고 ALB를 세운 뒤 파드 IP를 타겟으로 등록하며, 443 리스너가 인증서를 냅니다](https://dhbang.co.kr/images/aws-eks/anim09-ingress.svg)


---


## 인증서는 클러스터가 아니라 도메인과 함께 삽니다


HTTPS를 하려면 인증서가 있어야 합니다. AWS Certificate Manager(ACM)는 공개 인증서를 무료로 발급하는데 그 전에 이 도메인이 정말 내 것인지를 확인합니다. 방법은 ACM이 알려 주는 CNAME 레코드 하나를 내 DNS에 넣는 것입니다.


이 일은 사람이 DNS 관리 화면에서 손으로 하므로 이 편을 따라 하려면 레코드를 넣을 수 있는 도메인이 하나 필요합니다. 저는 원본에서 Cloudflare로 관리하던 도메인의 하위 이름을 학습용으로 썼습니다.


검증을 손으로 한다는 점이 인증서를 둘 층을 정합니다. 인증서를 `2-cluster`에 두면 클러스터를 부술 때마다 인증서도 지워집니다. 그러면 다시 세울 때마다 새 검증 레코드를 넣어야 합니다. 반면 도메인은 클러스터가 몇 번 바뀌어도 그대로이니 인증서는 ⑧편의 시크릿이나 ⑩편의 디스크처럼 `0-bootstrap`에 둡니다.


```hcl
# cert.tf
variable "app_domain" {
  type    = string
  default = "eks-lab.example.com" # 본인 도메인의 하위 이름으로 바꿉니다
}

# 검증을 사람이 DNS 에 넣으므로, 인증서는 클러스터가 아니라 도메인과 같이 삽니다
resource "aws_acm_certificate" "app" {
  domain_name       = var.app_domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# DNS 에 넣을 검증 레코드. 이름과 값을 그대로 복사합니다
output "cert_validation" {
  value = [for o in aws_acm_certificate.app.domain_validation_options : {
    name  = o.resource_record_name
    type  = o.resource_record_type
    value = o.resource_record_value
  }]
}

output "cert_arn" {
  value = aws_acm_certificate.app.arn
}

output "app_domain" {
  value = var.app_domain
}
```


검증이 끝날 때까지 기다려 주는 `aws_acm_certificate_validation` 리소스도 있지만 일부러 넣지 않았습니다. 그 리소스는 레코드가 들어올 때까지 `tofu apply`가 끝나지 않고 기다리게 만듭니다. 레코드는 사람이 넣으니 언제 끝날지 알 수 없습니다.


원본에서는 main에 머지할 때마다 CI가 이 층을 `apply`했으므로 그 리소스를 넣었다면 CI가 사람을 기다리다 멈췄을 것입니다. 그래서 인증서만 만들고 검증 레코드는 출력으로 꺼내 둡니다.


`prevent_destroy`를 걸지 않은 것도 ⑩편의 디스크와 다른 점입니다. 인증서는 도메인 이름을 바꾸면 새로 만들어야 하는 리소스라 막아 두면 그날의 `apply`가 막힙니다. 잃어도 다시 발급하면 되고 비용도 들지 않습니다.


```bash
tofu -chdir=0-bootstrap apply                     # 1 to add
tofu -chdir=0-bootstrap output cert_validation
```


출력에 나온 `name`과 `value`로 DNS에 CNAME 레코드를 하나 만듭니다. Cloudflare를 쓴다면 새 레코드의 기본값인 주황색 구름(Proxied)을 꺼서 **DNS only**로 둡니다. 프록시를 켜 두면 레코드를 조회했을 때 원래 값 대신 Cloudflare의 주소가 나옵니다. 앱 주소까지 프록시로 두면 브라우저가 받는 인증서도 ACM의 것이 아니게 됩니다.


원본에서도 2026년 4월에 운영 도메인을 Proxied로 두었다가 SSL 핸드셰이크가 실패한 적이 있고 DNS only로 바꿔 해결했습니다.


```bash
aws acm describe-certificate --region ap-northeast-2 \
  --certificate-arn "$(tofu -chdir=0-bootstrap output -raw cert_arn)" \
  --query 'Certificate.[Status,RenewalEligibility]' --output text
```


```plain text
ISSUED	INELIGIBLE
```


원본에서는 레코드를 넣고 3분쯤 지나 `ISSUED`가 됐습니다. 레코드를 72시간 안에 넣지 않으면 검증이 시간 초과로 끝나고 그때는 인증서를 새로 만들어야 합니다. 옆의 `INELIGIBLE`은 자동 갱신 대상이 아니라는 뜻입니다. 아직 어떤 로드밸런서에도 붙지 않았기 때문인데 이 값은 한계 절에서 다시 봅니다.


이 단계를 클러스터보다 먼저 하는 데에는 돈 문제가 걸려 있습니다. 원본에서도 레코드를 넣는 일이 사람 손을 타면서 다음 날로 넘어갔습니다. 그동안 클러스터를 켜 두었다면 컨트롤플레인 요금만 19시간치, \$1.9쯤이 나갔을 것입니다. 실제로는 인증서만 먼저 만들고 클러스터를 켜지 않아서 그 구간의 비용은 \$0이었습니다. 사람을 기다리는 단계는 요금이 나가는 구간 밖으로 빼는 편이 좋습니다.


---


## 컨트롤러에게도 ⑧편처럼 역할을 빌려 줍니다


컨트롤러는 로드밸런서와 타겟 그룹, 보안 그룹을 만들고 지워야 하니 AWS 권한이 필요합니다. 그 권한은 노드에 주지 않고 컨트롤러의 서비스 계정에 묶습니다. ⑧편의 ESO와 ⑨편의 디스크 드라이버에서 쓴 IRSA를 그대로 쓰고 바뀌는 것은 서비스 계정 이름과 붙이는 정책뿐입니다.


정책은 컨트롤러 프로젝트가 공개한 JSON 파일을 그대로 씁니다. 차트와 같은 버전의 파일을 받고 받은 파일이 맞는지 해시까지 확인합니다. 아래 해시는 이 글을 쓰며 받아 본 값입니다.


```bash
curl -fsSLo 2-cluster/iam-policy-alb.json \
  https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v3.5.0/docs/install/iam_policy.json
shasum -a 256 2-cluster/iam-policy-alb.json
```


```plain text
16f232c9d9f79366fe949c4550ad517a202380058a9e48d45a4e215044a20a6a  2-cluster/iam-policy-alb.json
```


```hcl
# irsa-alb.tf
data "aws_iam_policy_document" "alb_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.oidc.arn]
    }
    # 차트가 kube-system 에 이 이름으로 서비스 계정을 만듭니다
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:sub"
      values   = ["system:serviceaccount:kube-system:aws-load-balancer-controller"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "alb" {
  name               = "${var.cluster_name}-alb-controller"
  assume_role_policy = data.aws_iam_policy_document.alb_trust.json
}

# 공식 정책 파일(v3.5.0)을 그대로 씁니다. 공백을 걷어 내는 감싸기는 원본을 따른 것입니다
resource "aws_iam_policy" "alb" {
  name   = "${var.cluster_name}-alb-controller"
  policy = jsonencode(jsondecode(file("${path.module}/iam-policy-alb.json")))
}

resource "aws_iam_role_policy_attachment" "alb" {
  role       = aws_iam_role.alb.name
  policy_arn = aws_iam_policy.alb.arn
}
```


```hcl
# outputs.tf 에 더합니다
output "alb_role_arn" {
  value = aws_iam_role.alb.arn
}
```


`jsonencode(jsondecode(...))`는 파일을 한 번 풀었다 다시 묶어 공백을 걷어 내는 감싸기입니다. 원본은 들여쓰기를 포함한 8,955자가 IAM 정책의 상한 6,144자를 넘는다고 보고 착수 전에 이것을 넣었습니다.


하지만 IAM 문서에 따르면 이 상한은 공백을 빼고 셉니다. 그러니 이 감싸기는 필수가 아니고 실패를 직접 겪은 것도 아닙니다. 기준이 되는 크기는 공백을 뺀 5,196자이고 여유는 948자입니다. 나중에 버전을 올리면 크기부터 다시 재 보시기 바랍니다.


그리고 이 정책을 열어 보면 16개 문장 가운데 10개의 대상이 `"*"`입니다. ⑧편에서 시크릿 하나만 읽게 좁힌 것과 비교하면 지나치게 넓어 보이지만 줄이지 않습니다. 컨트롤러는 앞으로 만들 로드밸런서의 ARN을 미리 알 수 없습니다. 그래서 대상을 `"*"`로 두고 컨트롤러가 붙인 태그 같은 조건으로 좁히는 것이 공식 설계입니다. 임의로 깎으면 요금이 나가는 중에 `AccessDenied`를 만나게 됩니다.


---


## 노드 한 대에는 컨트롤러가 들어갈 자리가 없습니다


⑨편에서 노드 한 대의 파드 자리 11개가 이미 다 찼습니다. 컨트롤러 파드가 하나 더 들어오면 어떻게 될까요? 자리가 없으니 `Pending`으로 기다릴 것 같지만 실제로는 반대입니다. 이 차트는 컨트롤러에 `system-cluster-critical`이라는 높은 우선순위를 붙입니다. 그래서 자리가 없으면 기다리는 대신 우선순위가 낮은 파드를 밀어내고 그 자리에 들어갑니다.


2026년 10월 16일, 원본에서 이 순서를 처음부터 다시 따라 해 봤을 때 정확히 이 일이 있었습니다. `helm install`은 `deployed`로 끝났고 컨트롤러도 `1/1 Running`이었습니다. 로드밸런서도 `active`가 됐는데 5분이 지나도 등록된 타겟이 0개였습니다. 이벤트를 보니 앱 파드가 밀려나 있었습니다.


```plain text
Normal   Preempted         pod/core-api-…   Preempted by pod 75e45ca6-… on node ip-10-0-11-190…
Warning  FailedScheduling  pod/core-api-…   0/1 nodes are available: 1 Insufficient memory, 1 Too many pods …
```


설치 화면과 로드밸런서 상태만 보면 전부 성공이라 앱이 사라진 것은 타겟 수로 알아챘습니다. 그날은 노드를 두 대로 늘리자 1분쯤 뒤 둘째 노드가 준비됐고 앱이 그리로 옮겨 갔습니다. 그래서 이번에는 처음부터 노드 그룹의 `desired_size`를 2로 둡니다. ⑤편에서 `max_size`를 2로 잡아 두었으니 그 안에서 늘리는 것입니다. ⑩편에서 노드를 디스크의 AZ 하나로 묶었으므로 두 대 모두 같은 AZ에 뜹니다.


```hcl
# 2-cluster/nodes.tf 의 scaling_config 를 이렇게 바꿉니다
  scaling_config {
    desired_size = 2 # 로드밸런서 컨트롤러가 들어갈 자리를 만듭니다
    min_size     = 1
    max_size     = 2
  }
```


노드가 한 대 늘면 시간당 노드 요금 \$0.0208과 공인 IP \$0.005가 한 번 더 붙습니다. 컨트롤러 하나 때문에 노드를 늘리는 것이 아깝다면 다른 파드를 줄이는 방법도 있습니다. 다만 무엇을 줄여도 그 기능을 잃으니 한 시간 남짓만 켜는 이 시리즈에서는 노드를 늘리는 쪽을 골랐습니다.


---


## 컨트롤러는 Helm으로 설치하고 인자 세 개를 꼭 적습니다


⑩편 끝에서 클러스터를 부쉈으니 다시 세웁니다. ⑩편의 19개에 이번 편의 역할과 정책, 연결 세 개가 더해지므로 `plan`에는 22개가 나와야 합니다. 그다음은 ⑩편에서 클러스터를 다시 세운 순서 그대로입니다. 접속 정보를 새로 받고 ⑧편의 ESO를 설치하고 데이터베이스와 앱을 올립니다.


```bash
cd 2-cluster
tofu apply                     # 22 to add
aws eks update-kubeconfig --name eks-lab --region ap-northeast-2
# ⑧편의 ESO 단계와 ⑩편의 db-static.yaml, db.yaml, app.yaml 적용까지 그대로 합니다
```


컨트롤러는 EKS 애드온으로 제공되지 않아서 ⑧편의 ESO처럼 Helm으로 설치합니다. 원본에서 2026년 9월 11일에 애드온 목록을 조회했을 때 이 컨트롤러는 `None`이었습니다. ESO 단계 끝의 `cd ..`로 레포 맨 위 폴더에 돌아와 있을 테니 이 편의 나머지 명령은 전부 거기서 칩니다.


설치 전에 역할 주소와 VPC ID를 읽고 ⑧편에서처럼 값의 모양부터 확인합니다. `tofu output`은 실패해도 종료 코드 0으로 경고문을 내놓을 수 있기 때문입니다.


```bash
ROLE=$(tofu -chdir=2-cluster output -raw alb_role_arn)
VPC=$(tofu -chdir=1-network output -raw vpc_id)
case "$ROLE" in arn:aws:iam::*:role/*) echo "OK $ROLE" ;; *) echo "역할 주소가 아닙니다. 여기서 멈춥니다" ;; esac
case "$VPC" in vpc-*) echo "OK $VPC" ;; *) echo "VPC ID가 아닙니다. 여기서 멈춥니다" ;; esac
```


두 줄 다 `OK`로 시작할 때만 설치로 넘어갑니다.


```bash
helm repo add eks https://aws.github.io/eks-charts && helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --version 3.5.0 --namespace kube-system \
  --set clusterName=eks-lab \
  --set region=ap-northeast-2 \
  --set vpcId="$VPC" \
  --set replicaCount=1 \
  --set resources.requests.cpu=50m \
  --set resources.requests.memory=96Mi \
  --set resources.limits.memory=192Mi \
  --set "serviceAccount.annotations.eks\.amazonaws\.com/role-arn=$ROLE" \
  --wait --timeout 5m
```


`region`과 `vpcId`를 적지 않으면 컨트롤러는 노드의 메타데이터 서버에 물어서 알아내려 합니다. 그런데 파드에서 그 서버에 닿을 수 있는지는 노드 설정에 달려 있어서 직접 적어 줍니다. `replicaCount`는 기본값이 2입니다. 노드 두 대가 같은 AZ에 있는 실습에서는 두 개를 띄워도 얻는 것이 적어 하나로 줄였습니다.


`resources`는 차트 기본값이 비어 있어서 적었지만 앞 절에서 본 대로 이 값을 적어도 컨트롤러가 기다려 주지는 않습니다.


역할 주소를 넣는 줄의 `\.`도 빠뜨리면 안 됩니다. Helm은 `--set`의 점을 경로 구분자로 읽습니다. 이스케이프하지 않으면 `eks` 아래 `amazonaws` 아래 `com/role-arn`이라는 중첩 구조를 만들려 합니다. 원본 문서에는 이때 에러 없이 엉뚱한 구조가 들어간다고 적어 두었습니다. 그런데 이 글을 쓰며 같은 차트 버전으로 `helm template`을 돌려 보니 실제로는 설치 전에 멈췄습니다.


```plain text
Error: YAML parse error on aws-load-balancer-controller/templates/serviceaccount.yaml: error unmarshaling JSON: while decoding JSON: json: cannot unmarshal object into Go struct field .metadata.annotations of type string
```


조용히 넘어가지 않으니 다행이지만 이 문구만 보고 `\.`를 떠올리기는 어렵습니다. 역할이 정말 붙었는지는 Helm의 출력 대신 파드 안의 환경변수로 확인합니다. ⑧편에서 본 것처럼 IRSA는 파드가 만들어질 때 아래 두 값을 넣어 줍니다. 아래는 ⑧편의 출력 모양에 이 편의 역할 이름을 넣은 기대 출력이고 원본에서는 첫 줄이 `role/devquest-eks-alb-controller`였습니다.


```bash
kubectl -n kube-system get pod -l app.kubernetes.io/name=aws-load-balancer-controller \
  -o jsonpath='{range .items[0].spec.containers[0].env[*]}{.name}={.value}{"\n"}{end}' | grep AWS_
```


```plain text
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/eks-lab-alb-controller
AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
```


원본에서 컨트롤러 설치는 19초 걸렸습니다. 설치한 뒤에는 `kubectl get pods -A`로 앱과 데이터베이스가 여전히 `Running`인지도 함께 봅니다. 노드를 두 대로 늘렸다면 밀려난 파드가 없어야 합니다.


---


## Ingress에서는 `target-type`과 헬스 체크 경로가 조용한 실패를 막습니다


이제 주문서를 씁니다. 앱의 `/hello` 하나만 바깥에 엽니다. 80번으로 오면 443번으로 돌려보내고 443번에서는 앞에서 받은 인증서를 냅니다.


```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing # 기본값 internal 이면 VPC 안에서만 닿습니다
    alb.ingress.kubernetes.io/target-type: ip # Service 가 ClusterIP 라 반드시 ip 입니다
    alb.ingress.kubernetes.io/healthcheck-path: /actuator/health/liveness # 기본값 / 는 이 앱에서 404 입니다
    alb.ingress.kubernetes.io/certificate-arn: CERT_ARN_PLACEHOLDER
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80},{"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
spec:
  ingressClassName: alb # 차트가 만든 IngressClass 입니다
  rules:
    - http:
        paths:
          - path: /hello
            pathType: Prefix
            backend:
              service:
                name: app
                port:
                  number: 8080
```


가장 중요한 줄은 `target-type: ip`입니다. 기본값인 `instance`는 로드밸런서가 노드의 포트로 보내는 방식이라 Service가 `NodePort`여야 합니다. 그런데 ⑥편의 Service는 `ClusterIP`입니다. 그대로 두면 `kubectl apply`는 성공하지만 로드밸런서가 생기지 않고 그 이유는 `kubectl describe ingress`의 이벤트에만 남습니다.


`ip` 모드는 로드밸런서가 파드 IP로 곧장 보내는 방식입니다. ④편에서 본 대로 EKS의 파드는 VPC 안의 진짜 IP를 받으니 이렇게 할 수 있습니다.


둘째는 헬스 체크 경로입니다. 로드밸런서는 타겟이 살아 있는지 기본으로 `/`를 불러 확인합니다. 이 앱에는 `/` 주소가 없으니 404가 돌아오고 타겟이 전부 건강하지 않은 것으로 빠집니다. 그러면 바깥에서는 502를 받는데 `kubectl get pods`는 `Running`이라 앱이 고장 난 것으로 착각하기 쉽습니다. 원본은 기본 경로가 인증에 걸릴 것으로 보고 처음부터 상태 확인 전용 경로를 적어 두었습니다.


그런데 왜 `/actuator/health`가 아니라 `/liveness`일까요? ⑦편 이후의 `/actuator/health`는 데이터베이스 연결까지 확인합니다. 그 경로를 쓰면 데이터베이스가 잠깐 흔들릴 때 로드밸런서가 타겟을 전부 빼 버려서 작은 장애가 바깥의 502로 커집니다. 원본도 같은 이유로 앱이 살아 있는지만 답하는 경로를 골랐습니다. ⑨편에서 본 것처럼 이 앱의 상태 확인에는 `liveness` 그룹이 있어서 이 경로를 쓸 수 있습니다.


셋째는 규칙에 적은 경로입니다. 규칙에 `/hello`만 두었으니 `/actuator` 아래 주소는 바깥에서 닿지 않습니다. 헬스 체크는 로드밸런서가 파드 IP로 직접 부르는 것이라 규칙과 상관없이 동작합니다. 그래서 상태 정보를 인터넷에 열지 않고도 헬스 체크를 할 수 있습니다.


annotations의 마지막 세 줄(`certificate-arn`, `listen-ports`, `ssl-redirect`)은 함께 넣어야 합니다. 443번 리스너 없이 리다이렉트만 들어가면 갈 곳 없는 포트로 돌려보내게 되기 때문입니다. 인증서 ARN에는 계정 ID가 들어 있으니 파일에 적지 않고 ⑥편의 이미지처럼 적용할 때 바꿔 넣습니다.


여기서도 바꿔 넣기 전에 모양을 봅니다. 잘못된 값이 들어가도 `kubectl apply`는 성공하고 컨트롤러의 에러는 이벤트에만 남습니다. 그러니 이 확인이 유일한 방어선입니다.


```bash
CERT=$(tofu -chdir=0-bootstrap output -raw cert_arn)
case "$CERT" in arn:aws:acm:ap-northeast-2:*:certificate/*) echo "OK" ;; *) echo "인증서 ARN이 아닙니다. 여기서 멈춥니다" ;; esac
sed "s|CERT_ARN_PLACEHOLDER|$CERT|" k8s/ingress.yaml | kubectl apply -f -
```


이 줄부터 로드밸런서 요금이 나갑니다.


---


## 주소가 채워지고 타겟이 파드 IP인지 봅니다


적용하고 나면 무엇부터 봐야 할까요? 컨트롤러가 주문서를 읽었다면 Ingress의 주소 칸이 먼저 채워집니다.


```bash
kubectl get ingress app
```


```plain text
devquest   alb   *   k8s-default-devquest-3675af8c03-775497815.ap-northeast-2.elb.amazonaws.com   80   20s
```


원본의 출력이라 이름이 `devquest`인데 여러분의 것은 `app`입니다. 원본에서는 적용하고 20초 만에 `ADDRESS` 칸이 채워졌습니다. 이 칸이 채워졌다면 컨트롤러가 역할을 빌려 로드밸런서를 만든 것이고 `target-type`이 맞았다는 증거이기도 합니다. 로드밸런서는 ④편에서 `kubernetes.io/role/elb` 태그를 붙여 둔 두 공개 서브넷에 섭니다. 컨트롤러가 그 태그를 보고 서브넷을 고르기 때문입니다.


다만 주소가 생겼다고 바로 요청이 통하지는 않습니다. 원본에서는 로드밸런서가 `active`가 되고 타겟이 `healthy`가 되기까지 2분 30초가 걸렸습니다. 그동안 타겟이 무엇으로 등록됐는지 봅니다.


```bash
TG=$(aws elbv2 describe-target-groups --region ap-northeast-2 \
  --query "TargetGroups[?contains(TargetGroupName,'app')].TargetGroupArn | [0]" --output text)
aws elbv2 describe-target-health --region ap-northeast-2 --target-group-arn "$TG" \
  --query 'TargetHealthDescriptions[].[Target.Id,Target.Port,TargetHealth.State]' --output text
kubectl get pod -l app=app -o custom-columns=NAME:.metadata.name,IP:.status.podIP
```


타겟의 IP와 앱 파드의 IP가 같아야 합니다. 원본에서도 타겟 그룹이 `10.0.3.131 8080 healthy`를 보여 줬고 `kubectl`이 보여 준 파드 IP도 같았습니다. 노드의 IP 대신 파드의 IP가 등록된 것이 `ip` 모드의 실물입니다. 콘솔에서는 타겟 그룹 자체의 포트가 `1`로 보일 수 있습니다. `ip` 모드에서는 타겟마다 포트를 따로 가지므로 그 값은 의미 없는 자리표시자이고 봐야 할 것은 위 명령의 `Target.Port`입니다.


---


## DNS 레코드 없이도 진짜 HTTPS인지 확인할 수 있습니다


이제 `https://<내 도메인>/hello`를 불러 보면 될 것 같은데 내 도메인은 아직 이 로드밸런서를 가리키지 않습니다. 가리키게 하려면 DNS에 레코드를 또 넣어야 하는데 로드밸런서의 이름은 클러스터를 세울 때마다 바뀝니다. 매번 DNS 화면을 열어 레코드를 고치고 퍼지기를 기다려야 할까요? 그러면 앞 절에서 피한 "요금이 나가는 동안 사람을 기다리는" 상황이 다시 생깁니다.


그래서 확인은 `curl --resolve`로 합니다. 이 옵션은 DNS를 묻지 않고 "이 도메인의 443번은 이 IP다"라고 정해 주는 것입니다. 그 밖의 TLS 검증은 평소와 똑같이 하므로 `-k` 없이 통과했다면 인증서의 체인과 이름이 실제로 맞습니다. 로드밸런서는 두 AZ에 IP를 하나씩 가지니 한쪽만 보고 판정하지 않도록 둘 다 부릅니다.


```bash
ALB=$(kubectl get ingress app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
HOST=$(tofu -chdir=0-bootstrap output -raw app_domain)
for IP in $(dig +short "$ALB"); do
  echo "== $IP"
  for p in /hello /actuator/health /; do
    printf "  %-18s %s\n" "$p" "$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
      --resolve "$HOST:443:$IP" "https://$HOST$p")"
  done
done
```


이 앱이라면 두 IP 모두 `/hello`가 200이고 나머지 둘은 404여야 합니다. `/actuator/health`가 404로 돌아오면 상태 정보는 바깥에 열려 있지 않습니다. 원본에서는 2026년 9월 16일에 같은 방식으로 경로 다섯 개를 불렀고 두 IP가 모든 경로에서 같은 코드를 돌려줬습니다. 그중 상태 확인 경로는 이 편과 마찬가지로 404였습니다.


응답 본문도 한 번 찍어 봅니다. 이 앱이라면 `hello from eks-lab`이 나와야 합니다.


```bash
curl -s --resolve "$HOST:443:$(dig +short "$ALB" | head -1)" "https://$HOST/hello"
```


인증서는 `curl -v`로 봅니다.


```bash
curl -sv -o /dev/null --resolve "$HOST:443:$(dig +short "$ALB" | head -1)" "https://$HOST/hello" 2>&1 \
  | grep -E 'SSL connection|subject:|issuer:|expire'
```


```plain text
* SSL connection using TLSv1.2 / ECDHE-RSA-AES128-GCM-SHA256
*  subject: CN=eks.quest.dhbang.co.kr
*  issuer: C=US; O=Amazon; CN=Amazon RSA 2048 M04
*  expire date: Apr  1 23:59:59 2027 GMT
```


원본의 출력이라 이름이 제 학습용 도메인이고 여러분의 출력에는 `subject`에 여러분의 도메인이 나와야 합니다. 80번으로 보내면 301이 돌아오는지도 확인합니다. 이때는 `--resolve`를 80번에 줍니다.


```bash
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' \
  --resolve "$HOST:80:$(dig +short "$ALB" | head -1)" "http://$HOST/hello"
```


원본에서는 `301`과 함께 `https://eks.quest.dhbang.co.kr:443/…`이 돌아왔습니다. 처음에는 리다이렉트 주소가 로드밸런서의 이름으로 바뀌어 인증서와 어긋날 거라고 예상했습니다. 실제로는 요청의 호스트 이름이 그대로 남았으니 `-L`을 붙여 리다이렉트를 따라가도 됩니다. 그때는 80번과 443번 모두에 `--resolve`를 줍니다.


리스너의 규칙을 보고 싶다면 리스너를 포트로 골라야 합니다. 리스너가 80번과 443번 둘인데 순서가 정해져 있지 않기 때문입니다. `Listeners[0]`으로 잡았다가 80번이 걸리면 리다이렉트 규칙 하나만 보입니다.


```bash
LB=$(aws elbv2 describe-load-balancers --region ap-northeast-2 \
  --query "LoadBalancers[?DNSName=='$ALB'].LoadBalancerArn | [0]" --output text)
LSN=$(aws elbv2 describe-listeners --region ap-northeast-2 --load-balancer-arn "$LB" \
  --query 'Listeners[?Port==`443`].ListenerArn | [0]' --output text)
aws elbv2 describe-rules --region ap-northeast-2 --listener-arn "$LSN" \
  --query 'Rules[].[Priority,Conditions[0].Values[0]]' --output text
```


`1`번 규칙에 `/hello`가, 마지막에 `default`가 보이면 됩니다. 휴대폰 브라우저처럼 `--resolve`를 쓸 수 없는 곳에서 열어 보고 싶을 수도 있습니다. 그때는 DNS에 내 도메인을 `$ALB`로 가리키는 CNAME을 하나 넣고 Cloudflare라면 이것도 DNS only로 둡니다. 다만 저는 원본에서 앞의 이유로 이 레코드를 넣지 않았습니다. 넣는다면 로드밸런서가 바뀔 때마다 고쳐야 한다는 점도 기억해 두시기 바랍니다.


---


## 정리는 Ingress부터, 그리고 로드밸런서가 0인 것을 보고 부숩니다


⑤편에서 쿠버네티스가 직접 만든 것은 `tofu destroy`가 지우지 못한다고 했습니다. 로드밸런서가 바로 그런 것이라 클러스터를 부수기 전에 Ingress를 먼저 지워 컨트롤러가 로드밸런서를 지우게 합니다.


순서를 바꿔 클러스터부터 부수면 어떻게 될까요? 로드밸런서를 지울 컨트롤러가 먼저 사라지니 로드밸런서는 주인 없이 남아 한 달에 \$16 넘게 받습니다. 그 로드밸런서가 쓰던 보안 그룹 때문에 `tofu destroy` 자체가 실패할 수도 있습니다.


```bash
kubectl delete ingress app --timeout=180s
aws elbv2 describe-load-balancers --region ap-northeast-2 \
  --query 'length(LoadBalancers)' --output text        # 0
```


원본에서 `kubectl delete ingress`는 바로 돌아오지 않고 16초가 걸렸습니다. Ingress에 finalizer라는 표시가 붙어 있어서 컨트롤러가 로드밸런서를 실제로 지운 뒤에야 객체가 사라지기 때문입니다. 컨트롤러가 이미 죽어 있다면 이 명령은 끝나지 않고 기다리기만 하니 타임아웃을 걸었습니다. 끝에 0이 나와야 다음으로 가고 0이 아니라면 여기서 멈추고 콘솔에서 남은 로드밸런서를 확인합니다.


그다음은 ⑩편의 정리와 같습니다. 앱과 데이터베이스, ESO 객체를 지우고 PVC와 PV를 지웁니다. 디스크가 `available`이 된 것을 보고 클러스터를 부수면 되고 컨트롤러는 클러스터와 함께 사라지니 `helm uninstall`은 하지 않아도 됩니다.


```bash
cd 2-cluster && tofu destroy && cd ..                 # 22 destroyed
```


①편에서 말씀드린 하룻밤 사고가 바로 이 편의 원본 세션 끝에서 났습니다. 2026년 9월 16일에 HTTPS 확인을 다 마치고 `tofu destroy`를 걸었습니다. 그런데 그 명령이 도중에 멈춘 것을 확인하지 않고 자리를 떴습니다.


그러니 ⑤편의 확인 명령과 앞의 로드밸런서 수 확인으로, 클러스터와 인스턴스, 로드밸런서가 모두 0인 것을 눈으로 본 뒤에 터미널을 닫으시기 바랍니다. 이번 편부터는 그 확인 목록에 로드밸런서가 하나 더 붙는 셈입니다.


---


## 로드밸런서는 켜 둔 시간만큼, 인증서는 쓰지 않으면 갱신되지 않습니다


로드밸런서는 요청이 하나도 없어도 시간당 \$0.0225를 받습니다. 두 AZ에 하나씩 붙는 공인 IP가 \$0.005씩 더해지니 합쳐서 시간당 \$0.0325이고 ⑤편의 클러스터 단가 \$0.13에 25%쯤을 더하는 셈입니다. 그래서 로드밸런서는 맨 마지막에 켜고 맨 먼저 끄는 편이 좋습니다.


원본의 9월 11일 세션은 30분 44초에 \$0.0996이 들었습니다. 로드밸런서를 마지막 7분 22초만 켰기 때문에 그 몫은 전체의 4%였으니 같은 요금표라도 켜는 순서가 비용을 정합니다.


여기에 요청량에 따라 붙는 LCU라는 단위가 따로 있습니다. 이 편처럼 몇 번 부르는 정도로는 거의 0입니다. 하지만 원본에서 초당 1,200건을 보내던 부하 시험을 로드밸런서로 받았다면, 최악의 경우 시간당 \$0.096쯤으로 고정 요금의 4배가 됐을 것입니다. 그래서 원본에서는 부하 시험과 로드밸런서 실습을 같은 세션에 넣지 않았습니다.


인증서 쪽에도 조건이 하나 숨어 있습니다. ACM은 인증서를 자동으로 갱신해 주지만 어딘가에 붙어 있는 인증서만 갱신합니다. 앞에서 본 `INELIGIBLE`이 그 뜻입니다. 원본에서는 로드밸런서에 붙어 있는 동안 `ELIGIBLE`이었다가 정리하자 다시 `INELIGIBLE`로 돌아갔습니다.


매번 부수는 이 시리즈에서는 인증서가 대부분의 시간을 혼자 지내니 만료일이 다가오면 다시 발급해야 합니다. 원본의 인증서는 9월 16일에 발급돼 만료가 2027년 4월 2일(한국 시각)이었으니 반년 남짓입니다.


마지막으로, 실제 서비스라면 이 편의 방식을 그대로 쓰지 않습니다. 로드밸런서를 매번 새로 만들지 않고 계속 띄워 둡니다. DNS 레코드도 사람이 넣지 않고 external-dns 같은 도구가 Route 53에 넣게 합니다. 그리고 ⑩편에서 노드를 한 AZ로 묶었으니 로드밸런서가 두 AZ에 서 있어도 앱은 한 AZ에만 있습니다. 이 시리즈는 한 시간 켜고 부수는 실습이라 사람이 레코드를 한 번 넣는 쪽을 골랐습니다.


---


## 정리


| 할 일      | 명령이나 파일                                | 확인                    |
| -------- | -------------------------------------- | --------------------- |
| 인증서      | `0-bootstrap/cert.tf`, DNS에 CNAME      | `ISSUED`              |
| 컨트롤러의 역할 | `2-cluster/irsa-alb.tf` (공식 정책 v3.5.0) | `22 to add`           |
| 파드 자리    | `nodes.tf`의 `desired_size = 2`         | 앱과 DB가 밀려나지 않음        |
| 컨트롤러 설치  | `helm install` (region, vpcId, 역할)     | 파드 안 `AWS_ROLE_ARN`   |
| 주문서      | `k8s/ingress.yaml` (`ip`, 헬스 체크, 인증서)  | `ADDRESS`, 타겟이 파드 IP  |
| HTTPS 확인 | `curl --resolve`, `-k` 없이              | `/hello` 200, 80은 301 |
| 정리       | Ingress 먼저, 로드밸런서 0 확인 후 destroy       | `22 destroyed`        |


바깥으로 나가는 길은 사람이 아니라 주문서를 받은 컨트롤러가 만듭니다. 그래서 정리할 때도 주문서를 먼저 거둬 컨트롤러가 길을 치우게 합니다. 사람 손이 필요한 인증서 검증은 요금이 나가기 전에 끝내 둡니다.


본편은 여기까지입니다. 다음 ⑫편은 번외로, 원본에서 오토스케일과 GitOps를 더해 본 기록을 읽어 봅니다. 건너뛰셔도 ⑭편의 정리와 비용 결산으로 바로 이어집니다.


---


## 참고

- [AWS Load Balancer Controller, 설치 안내](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/deploy/installation/)
- [AWS Load Balancer Controller, Ingress annotations](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/annotations/)
- [AWS Certificate Manager 사용 설명서, DNS 검증](https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html)
- [AWS Certificate Manager 사용 설명서, 관리형 갱신](https://docs.aws.amazon.com/acm/latest/userguide/managed-renewal.html)
- [IAM 사용 설명서, IAM과 STS의 할당량(정책 크기)](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_iam-quotas.html)
- 로드밸런서와 공인 IP 단가(서울 리전, 시간당 \$0.0225와 \$0.005)는 제 원본의 2026년 9월 11일 일지에 적은 값이고 노드 단가는 ⑤편의 값입니다.
- 제 원본 작업 일지와 전체 코드는 [switch-job-quest](https://github.com/bangddong/switch-job-quest) 레포에 있습니다. 서비스를 닫으면서 보관(archive)해 두었습니다.
> 이 편은 ⑧⑨⑩편과 달리 이 글을 쓰면서 클러스터를 다시 띄우지 않았습니다. 같은 단계를 원본에서 세 번 실제로 돌렸기 때문입니다. 2026년 9월 11일에 컨트롤러와 로드밸런서를, 9월 16일에 인증서와 HTTPS를, 10월 16일에 처음부터 다시 따라 하는 재현을 했고, 원본의 것이라고 밝힌 출력과 시간은 그날 제 일지의 기록입니다. `ISSUED INELIGIBLE` 줄은 일지에 적힌 두 값을 이 편의 명령 모양으로 옮긴 것이고, 파드 안 환경변수는 기대 출력입니다. `22 to add`도 ⑩편의 19개에 이 편의 세 개를 더한 계산값입니다. 원본 출력 속 이름은 제 원본 서비스의 것이고, 원본은 앱 두 개를 경로로 나눠 열었지만 이 편은 `/hello` 하나로 줄였습니다. 이 편의 `cert.tf`와 `irsa-alb.tf`, `nodes.tf` 변경은 이 글을 위해 새로 썼습니다. 2026년 11월 23일에 ⑤⑧⑨⑩편에 실린 코드와 함께 `tofu validate`를 통과하는 것을 보았고, 인증서는 `plan`(1개 추가)까지 확인했습니다. 같은 날 정책 파일의 해시와 크기를 다시 쟀고, 차트 3.5.0의 기본값과 Helm 인자의 결과는 `helm template`으로 확인했습니다. `ingress.yaml`과 이 앱에서의 응답 코드는 실제 클러스터에서 돌려 보지 못했으니, 다르게 나오면 알려 주시기 바랍니다. 비용은 ⑤편의 시간당 \$0.13에 노드 한 대와 로드밸런서 몫을 더해 한 시간 남짓으로 어림한 정가이고, 청구서에는 노드 요금이 \$0으로 찍혔다는 이야기는 ⑤편에 적었습니다. 차트의 최신 버전은 3.6.3이지만 원본에서 검증한 3.5.0을 그대로 썼습니다.
>
> 이 글의 그림은 AI가 그렸습니다.
>
>
