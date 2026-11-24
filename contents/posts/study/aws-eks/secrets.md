---
title: '비밀값은 사람이 아니라 파드가 넣는다. EKS 실습기 ⑧, IRSA와 ESO로 시크릿 받아 오기'
date: '2026-11-13'
tags:
  - AWS
  - EKS
series: AWS EKS 실습기
emoji: ''
---
> **AWS 프리티어 \$200으로 EKS 실습하기 ⑧** · 💰 클러스터를 켜는 한 시간 안쪽에 약 **\$0.1**, 그리고 시크릿 하나에 월 **\$0.40**

⑦편 마지막에 Secret을 `kubectl create secret`으로 만들고 앱을 살렸습니다. 그런데 그 값은 지금 어디에 남아 있을까요? 클러스터를 부쉈으니 Secret도 함께 사라졌고 비밀번호와 서명 키는 셸에서 한 번 쓰고 버렸습니다. 다시 클러스터를 세우면 같은 명령을 또 쳐야 하고 그때 뽑은 값은 지난번과 다릅니다.


이번 편에서는 비밀값의 원본을 클러스터 밖, AWS Secrets Manager에 둡니다. 그리고 클러스터 안의 작은 프로그램이 그 값을 읽어 와 ⑦편과 똑같은 이름의 Secret을 대신 만들게 합니다. 앱과 데이터베이스 매니페스트는 한 줄도 고치지 않습니다. 바뀌는 것은 Secret을 누가 만드느냐 하나뿐입니다.

> 비밀값을 클러스터에 넣는 일은 사람이 아니라, 권한을 빌린 파드가 한다.

---


## 파드에 AWS 권한을 줄 때는 노드가 아니라 서비스 계정에 줍니다


Secrets Manager에서 값을 읽으려면 그 일을 하는 파드가 AWS에 로그인해야 합니다. 가장 먼저 떠오르는 방법은 ②편 같은 액세스 키를 Secret에 넣어 두는 것입니다. 하지만 그러면 지우기 전까지 유효한 키가 클러스터 안에 상주하고 우리가 없애려던 "손으로 넣은 비밀값"이 하나 더 생깁니다.


다른 방법은 ⑤편에서 노드에 붙인 IAM 역할에 권한을 더하는 방법입니다. 키는 없어지지만 경계가 노드 단위라서 그 노드에 뜬 파드는 모두 같은 권한을 갖습니다. 다시 말해 인사말을 돌려주는 앱도 비밀값을 읽을 수 있게 됩니다.


그래서 EKS는 IRSA(IAM Roles for Service Accounts)라는 길을 따로 둡니다. 파드는 저마다 서비스 계정을 갖고 쿠버네티스는 그 계정 이름이 적힌 토큰을 파드에 넣어 줍니다.


AWS는 ⑤편에서 등록해 둔 클러스터의 OIDC 공급자로 그 토큰이 진짜인지 확인하고, 정해 둔 서비스 계정에만 역할을 잠깐 빌려줍니다. 저장해 둔 키가 없으니 샐 것도 없습니다. ⑤편에서 파드에 AWS 권한을 줄 때 필요한 신원 확인 창구라고 소개한 그 공급자가 이번에 처음 일을 합니다.


이번 편에서 그 역할을 빌리는 쪽은 External Secrets Operator(줄여서 ESO)입니다. 클러스터에 설치하는 오픈소스 프로그램으로, Secrets Manager의 값을 읽어 쿠버네티스 Secret으로 옮겨 적는 일만 합니다. 값이 지나가는 길을 그림으로 먼저 보겠습니다. 상자가 하나씩 켜지는 동안 맨 마지막 상자의 조건을 눈여겨보시기 바랍니다.


![ESO 파드의 토큰이 STS를 거쳐 역할이 되고, Secrets Manager의 값이 Secret을 지나 앱의 환경변수가 되기까지](https://dhbang.co.kr/images/aws-eks/anim06-secret-path.svg)


앞의 세 칸은 AWS와 ESO 사이의 일이고 우리가 할 일은 역할과 권한을 정해 두는 것뿐입니다. 뒤의 두 칸은 쿠버네티스 쪽 이야기인데 특히 마지막 칸은 뒤에서 일부러 값을 바꿔 보며 확인합니다.


---


## 비밀값의 원본은 클러스터보다 오래 사는 층에 둡니다


Secrets Manager의 시크릿은 어느 층에서 만들어야 할까요? 클러스터 층(`2-cluster`)에 두면 실습이 끝날 때마다 함께 지워지고 다시 세울 때 새 비밀번호가 뽑힙니다. 지금은 데이터베이스가 임시라서 상관없지만 ⑩편에서 데이터를 디스크에 남기기 시작하면 이야기가 달라집니다. 디스크에 남은 데이터베이스는 처음 만들 때의 비밀번호를 기억하기 때문입니다.


그래서 ⑥편의 ECR처럼 `0-bootstrap`에 둡니다. 값은 사람이 정하지 않고 OpenTofu가 무작위로 뽑게 해서 셸 기록에 남는 일도 없앱니다. 무작위 값을 만드는 `random` 공급자를 쓰므로 `0-bootstrap/versions.tf`의 `required_providers`에 한 줄을 더합니다.


```hcl
# versions.tf 의 required_providers 안, aws 블록 아래에 더합니다
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
```


```hcl
# app-secret.tf
# 비밀번호와 서명 키는 사람이 정하지 않고 OpenTofu 가 뽑습니다
resource "random_password" "db" {
  length  = 32
  special = false # 특수문자는 JDBC 주소와 셸을 오가며 깨지기 쉽습니다
}

resource "random_password" "token" {
  length  = 64
  special = false
}

resource "aws_secretsmanager_secret" "app" {
  name                    = "eks-lab/app"
  recovery_window_in_days = 0 # 지우면 바로 사라져서, 같은 이름으로 다시 만들 수 있습니다
}

# ⑦편에서 손으로 넣은 다섯 값을 JSON 하나에 담습니다
resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    DB_HOST      = "db"
    DB_NAME      = "app"
    DB_USERNAME  = "app"
    DB_PASSWORD  = random_password.db.result
    TOKEN_SECRET = random_password.token.result
  })
}
```


키 다섯 개는 ⑦편에서 `grep`으로 센 그 다섯 개이고 이름도 그대로입니다. 그래야 앱의 `envFrom`과 데이터베이스의 `secretKeyRef`가 아무것도 모른 채 같은 값을 받습니다. `0-bootstrap/outputs.tf`에는 시크릿의 ARN을 내보내는 출력을 하나 더합니다. 클러스터 층이 이 값을 읽어 권한의 범위를 정합니다.


```hcl
# outputs.tf 에 더합니다
output "app_secret_arn" {
  value = aws_secretsmanager_secret.app.arn
}
```


```bash
cd 0-bootstrap
tofu init -upgrade
tofu apply
```


`tofu init -upgrade`는 새로 더한 `random` 공급자를 받아 옵니다. `apply`의 계획은 `4 to add`이고 끝나면 `Apply complete! Resources: 4 added`가 나옵니다. Secrets Manager는 시크릿 하나에 월 \$0.40을 받습니다. 이 층은 클러스터를 부숴도 남으므로 이 시크릿은 시리즈 내내 하루 1.3센트쯤씩 나갑니다.


---


## 역할은 서비스 계정 하나에만 빌려줍니다


이제 `2-cluster`에 ESO가 빌릴 역할을 만듭니다. 먼저 `remote-state.tf`에 `0-bootstrap`의 출력을 읽는 블록을 하나 더합니다. ⑤편의 `network` 블록을 복사해서 이름과 `key`만 바꾸면 됩니다.


```hcl
# remote-state.tf 에 더합니다
data "terraform_remote_state" "bootstrap" {
  backend = "s3"
  config = {
    bucket = "<본인만의-버킷-이름>"
    key    = "0-bootstrap/terraform.tfstate"
    region = "ap-northeast-2"
  }
}
```


역할에서 가장 중요한 것은 누가 빌릴 수 있는지를 정하는 신뢰 정책입니다. 아래의 `sub` 조건은 `external-secrets` 네임스페이스의 같은 이름 서비스 계정만 받아들입니다. `aud` 조건은 토큰이 AWS에 쓰라고 발급된 것인지를 봅니다. 권한 정책은 방금 만든 시크릿 하나를 읽는 동작 둘만 허락합니다.


```hcl
# irsa-eso.tf
locals {
  # https:// 를 뗀 발급자 주소. 신뢰 정책의 조건 이름 앞에 붙습니다
  oidc_host = replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", "")
}

data "aws_iam_policy_document" "eso_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.oidc.arn]
    }
    # 이 네임스페이스의 이 서비스 계정만 역할을 빌릴 수 있습니다
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:sub"
      values   = ["system:serviceaccount:external-secrets:external-secrets"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eso" {
  name               = "${var.cluster_name}-eso"
  assume_role_policy = data.aws_iam_policy_document.eso_trust.json
}

# 읽기만, 그리고 시크릿 하나만
resource "aws_iam_role_policy" "eso" {
  role = aws_iam_role.eso.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
      Resource = data.terraform_remote_state.bootstrap.outputs.app_secret_arn
    }]
  })
}
```


```hcl
# outputs.tf 에 더합니다
output "eso_role_arn" {
  value = aws_iam_role.eso.arn
}
```


여기서 쓰는 OIDC 공급자는 ⑤편의 `cluster.tf`가 이미 만들고 있으니 따로 더할 것이 없습니다. 클러스터를 처음부터 세우는 것이라 계획은 ⑤편의 14개에 역할과 권한 정책 둘을 더한 `16 to add`입니다. 이 글을 쓰며 2026년 11월 17일에 이 코드로 세웠을 때는 컨트롤플레인이 6분 32초, 노드 그룹이 1분 48초 걸렸습니다.


```bash
cd ../2-cluster
tofu plan -out=cluster.tfplan
tofu apply cluster.tfplan
aws eks update-kubeconfig --name eks-lab --region ap-northeast-2
```


---


## ESO에 역할 주소를 넘기기 전에 그것이 정말 주소인지 확인합니다


ESO는 Helm 차트로 설치합니다. 차트는 ESO가 쓸 서비스 계정을 만듭니다. 그 계정에 역할의 ARN을 주석(annotation)으로 붙이면 EKS가 파드에 토큰과 역할 정보를 넣어 줍니다. 그러니 역할 ARN을 변수에 담아 넘기면 되는데 그 앞에 세 줄짜리 확인을 둡니다.


```bash
ESO_ROLE=$(tofu output -raw eso_role_arn)
case "$ESO_ROLE" in
  arn:aws:iam::*:role/*) echo "OK $ESO_ROLE" ;;
  *) echo "역할 ARN이 아닙니다. apply가 끝났는지 확인하고 여기서 멈춥니다" ;;
esac
```


`OK`로 시작하는 줄이 나왔을 때만 다음으로 넘어갑니다. 버전은 이 글을 쓰며 확인한 차트 2.12.0으로 고정합니다. 더 새 버전이 있더라도 같은 결과를 보려면 이 버전을 쓰시기 바랍니다.


```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update
helm install external-secrets external-secrets/external-secrets \
  --version 2.12.0 --namespace external-secrets --create-namespace \
  --set "serviceAccount.annotations.eks\.amazonaws\.com/role-arn=$ESO_ROLE" \
  --wait --timeout 5m
kubectl get pods -n external-secrets
cd ..
```


`STATUS: deployed`가 나오고 파드 세 개가 `Running`이면 설치가 끝났습니다. 마지막 `cd ..`로 레포의 맨 위 폴더로 돌아오는데 뒤의 `k8s/` 경로가 모두 거기서 시작합니다. 이 글을 쓸 때는 40초쯤 걸렸습니다. 그런데 이 확인이 정말 필요할까요? 다음 절에서 확인 없이 넘겼을 때 무슨 일이 생기는지 직접 보겠습니다.


### 일부러 깨 보기 ①: 출력을 너무 일찍 읽으면 경고문이 역할 주소가 됩니다


2026년 8월 12일, 저는 원본 서비스에서 `apply`가 끝나기 전에 `tofu output`으로 역할 ARN을 읽었습니다. 그때 ESO는 역할 없이 떴고 저는 형식 검사를 넣은 뒤 `helm upgrade`로 다시 적용하고 파드를 재시작해서 고쳤습니다. 이번 글을 쓰면서 같은 상황을 다시 만들어 봤습니다. `apply`하기 전의 빈 state에서 출력을 읽으면 이렇습니다.


```bash
ESO_ROLE=$(tofu output -raw eso_role_arn); echo "exit=$?"
echo "$ESO_ROLE"
```


```plain text
exit=0
╷
│ Warning: No outputs found
│
│ The state file either has no outputs defined, or all the defined outputs
│ are empty. ...
╵
```


종료 코드가 0이라서 셸은 성공으로 알고 변수에는 ARN 대신 색상 코드가 섞인 경고문 530자가 담깁니다. 이 값을 그대로 `helm install`에 넘겨도 Helm과 쿠버네티스는 아무 말 없이 받아들입니다. 파드는 세 개 다 `Running`이 되니 설치 화면만 봐서는 아무것도 틀리지 않았습니다.


문제가 드러나는 것은 다음 절에서 SecretStore를 만들 때입니다. 상태가 `unable to validate store`로 멈추고 이벤트에는 이런 줄이 찍힙니다. 앞의 경고문이 어디로 갔는지 보시기 바랍니다.


```plain text
AssumeRoleWithWebIdentity, https response error StatusCode: 400, ...
api error ValidationError: 1 validation error detected: Value '╷ │ Warning: No outputs found ...'
at 'roleArn' failed to satisfy constraint: Member must satisfy regular expression pattern: ...
```


역할 이름 자리에 경고문이 들어갔다는 것을 AWS가 대신 알려 준 셈입니다. 그래서 확인은 Helm의 출력 대신 파드 안에서 합니다. EKS가 넣어 준 환경변수 `AWS_ROLE_ARN`이 `arn:aws:iam::`으로 시작해야 합니다.


```bash
POD=$(kubectl get pod -n external-secrets -l app.kubernetes.io/name=external-secrets \
  -o jsonpath='{.items[0].metadata.name}')
kubectl get pod -n external-secrets "$POD" \
  -o jsonpath='{range .spec.containers[0].env[*]}{.name}={.value}{"\n"}{end}' | grep AWS_
```


```plain text
AWS_STS_REGIONAL_ENDPOINTS=regional
AWS_DEFAULT_REGION=ap-northeast-2
AWS_REGION=ap-northeast-2
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/eks-lab-eso
AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
```


이미 잘못 넣었다면 역할 ARN을 다시 읽어 형식을 확인한 뒤, `helm upgrade`로 주석을 고칩니다. 다만 고친 직후에 파드 안을 다시 보면 여전히 경고문이 들어 있는데 EKS가 환경변수를 넣는 것은 파드를 만들 때 한 번뿐이기 때문입니다. 그래서 파드를 새로 띄우는 `rollout restart`까지 해야 고쳐집니다. 이번 확인에서는 재시작하고 11초 뒤에 동기화가 성공했습니다.


```bash
ESO_ROLE=$(tofu -chdir=2-cluster output -raw eso_role_arn)
case "$ESO_ROLE" in arn:aws:iam::*:role/*) echo "OK $ESO_ROLE" ;; *) echo "아직 아닙니다. 여기서 멈춥니다" ;; esac
helm upgrade external-secrets external-secrets/external-secrets \
  --version 2.12.0 -n external-secrets --reuse-values \
  --set "serviceAccount.annotations.eks\.amazonaws\.com/role-arn=$ESO_ROLE" --wait
kubectl rollout restart deploy -n external-secrets
```


---


## 매니페스트 두 장이 ⑦편의 `kubectl create secret`을 대신합니다


ESO에게 일을 시키는 것은 매니페스트 두 장입니다. SecretStore는 "어디에서 읽는가"를, ExternalSecret은 "무엇을 읽어 어떤 이름의 Secret으로 만드는가"를 적습니다. SecretStore에 로그인 방법을 적지 않으면 ESO는 자기 파드가 받은 역할로 들어갑니다.


```yaml
# k8s/eso/secretstore.yaml
apiVersion: external-secrets.io/v1
kind: SecretStore
metadata:
  name: aws
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
      # auth 를 적지 않으면 ESO 파드가 받은 역할(IRSA)로 들어갑니다
```


```yaml
# k8s/eso/app-env.yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: app-env
spec:
  refreshInterval: 1h # 한 시간마다 Secrets Manager 의 값과 맞춥니다
  secretStoreRef:
    kind: SecretStore
    name: aws
  target:
    name: app-env         # ⑦편에서 손으로 만든 것과 같은 이름
    creationPolicy: Owner # 이 Secret 은 ExternalSecret 의 것입니다
  dataFrom:
    - extract:
        key: eks-lab/app  # JSON 의 키 다섯 개가 그대로 Secret 의 키가 됩니다
```


`apiVersion`이 `v1`인 데는 이유가 있습니다. 인터넷의 예전 글은 대개 `v1beta1`을 쓰는데 2.12.0 차트로 설치한 클러스터에서 확인해 보면 `v1beta1`은 받아 주지조차 않습니다. 2026년 7월 28일 제 원본 서비스의 2.8.0 차트에서도 같았습니다.


```bash
kubectl get crd externalsecrets.external-secrets.io \
  -o jsonpath='{range .spec.versions[*]}{.name}{" served="}{.served}{"\n"}{end}'
```


```plain text
v1 served=true
v1beta1 served=false
```


이제 두 장을 적용하고 상태를 봅니다. ⑦편에서 손으로 만든 `app-env`는 클러스터와 함께 사라졌으니 이름이 겹칠 일이 없습니다. 이번에는 같은 이름의 Secret을 ESO가 만듭니다.


```bash
kubectl apply -f k8s/eso/secretstore.yaml -f k8s/eso/app-env.yaml
kubectl get secretstore,externalsecret
```


```plain text
NAME                                  AGE   STATUS   CAPABILITIES   READY
secretstore.external-secrets.io/aws   80s   Valid    ReadWrite      True

NAME                                         STORETYPE     STORE   REFRESH INTERVAL   STATUS         READY   LAST SYNC
externalsecret.external-secrets.io/app-env   SecretStore   aws     1h                 SecretSynced   True    10s
```


`SecretSynced`가 나오면 `app-env`가 생겼습니다. 값은 화면에 찍지 않고 키 이름만 봅니다. ⑦편에서 센 다섯 개가 그대로 들어 있어야 합니다.


```bash
kubectl get secret app-env -o go-template='{{range $k, $v := .data}}{{$k}}{{"\n"}}{{end}}'
```


```plain text
DB_HOST
DB_NAME
DB_PASSWORD
DB_USERNAME
TOKEN_SECRET
```


---


## 앱과 데이터베이스는 한 줄도 바꾸지 않고 다시 뜹니다


⑦편의 `k8s/db-temp.yaml`과 `k8s/app.yaml`을 그대로 적용합니다. 둘 다 `app-env`라는 이름만 알고 그 Secret을 누가 만들었는지는 모릅니다. 그러니 고칠 것이 없습니다. 이미지는 ⑦편에서 올린 것을 그대로 쓰고 `REPO`와 `SHA`를 정하는 두 줄도 ⑦편과 같습니다.


```bash
kubectl apply -f k8s/db-temp.yaml
kubectl wait --for=condition=Ready pod/db --timeout=120s
kubectl logs db | grep "init process complete"
REPO=$(tofu -chdir=0-bootstrap output -raw ecr_repository_url)
SHA=$(aws ecr describe-images --repository-name eks-lab/app --region ap-northeast-2 \
  --query 'sort_by(imageDetails,&imagePushedAt)[-1].imageTags[0]' --output text)
sed "s|IMAGE_PLACEHOLDER|$REPO:$SHA|" k8s/app.yaml | kubectl apply -f -
kubectl port-forward svc/app 8080:8080
```


```bash
curl -s localhost:8080/hello
curl -s localhost:8080/actuator/health
```


```plain text
hello from eks-lab
{"groups":["liveness","readiness"],"status":"UP"}
```


⑦편은 kind에서만 확인했는데 이번에는 EKS에서 같은 결과를 받았습니다. EKS 노드가 Docker Hub에서 `postgres:17-alpine`을 받는 것도 이번에 확인했습니다. 앱은 7.6초 만에 `Started AppApplication`을 찍었고 `UP`은 데이터베이스까지 확인한 결과입니다.


---


## 거절 메시지가 두 가지라면 막힌 층도 둘입니다


IRSA가 실패할 때 보이는 메시지는 크게 둘인데 생김새가 비슷해서 같은 문제로 읽기 쉽습니다. 하지만 하나는 역할을 빌리는 단계에서, 다른 하나는 빌린 역할로 무언가를 하려는 단계에서 막힌 것입니다. 어느 쪽인지 알면 고칠 곳이 신뢰 정책인지 권한 정책인지가 바로 정해집니다.


### 일부러 깨 보기 ②: 권한 밖의 시크릿과 남의 서비스 계정


먼저 권한 정책에 없는 시크릿을 읽게 해 봅니다. `app-env.yaml`을 복사해 `key`만 `eks-lab/other`로 바꾸고 이름을 `try-other`로 붙여 적용하면, 이벤트에 이런 줄이 찍힙니다.


```plain text
api error AccessDeniedException: User: arn:aws:sts::123456789012:assumed-role/eks-lab-eso/<세션>
is not authorized to perform: secretsmanager:GetSecretValue on resource: eks-lab/other
because no identity-based policy allows the secretsmanager:GetSecretValue action
```


눈여겨볼 곳은 `assumed-role/eks-lab-eso`입니다. 이미 역할을 빌린 주체가 거절당했다는 뜻이니 인증은 통과했고 권한 정책의 범위에서 막힌 것입니다. 저는 7월 28일 원본 서비스에서 권한 정책을 붙이기 전에 이 메시지를 먼저 봤는데 이 줄을 보고 인증은 이미 통과했다고 판단할 수 있었습니다.


반대로 역할의 신뢰 정책에 없는 서비스 계정이 역할을 빌리려 하면 어떻게 될까요? `default` 네임스페이스에 `other`라는 서비스 계정을 만들어 같은 역할 주석을 붙였습니다. 그리고 그 계정으로 로그인하는 SecretStore를 하나 더 만들어 봤습니다. 이 실패는 제 원본에는 없던 일이고, 이번에 일부러 만들었습니다.


```plain text
operation error STS: AssumeRoleWithWebIdentity, https response error StatusCode: 403, ...
api error AccessDenied: Not authorized to perform sts:AssumeRoleWithWebIdentity
```


이번에는 주체 이름이 없고 `AssumeRoleWithWebIdentity`에서 멈췄습니다. 토큰에 적힌 서비스 계정이 `sub` 조건과 한 글자라도 다르면 이렇게 됩니다. 두 실험 모두 결과를 보여 드리려고 이 글을 쓰며 해 본 것이라 따라 하지 않고 메시지의 생김새만 기억해 두셔도 됩니다. 직접 해 보셨다면 만든 ExternalSecret과 서비스 계정, SecretStore를 지웁니다.


---


## 실패가 오래 남아 보이면 권한보다 재시도 간격을 먼저 봅니다


권한을 고쳤는데도 ExternalSecret이 한동안 `SecretSyncedError`에 머무를 때가 있습니다. 7월 28일 제 원본 서비스에서는 정책을 붙인 뒤에도 한 시크릿만 실패로 남아서 정책 문서까지 다시 열어 봤습니다. 원인은 권한이 아니라 ESO가 실패할 때마다 재시도 간격을 점점 두 배씩 늘린다는 데 있었습니다.


이번 `try-other`의 실패 이벤트 시각을 차례로 보면 그 모양이 그대로 보입니다. 처음 세 번은 1초 간격이었다가 4초, 8초, 16초, 32초로 벌어졌습니다. 이 상태에서 권한을 고치면 다음 차례가 올 때까지 실패 표시가 그대로 남습니다.


```bash
kubectl get events --field-selector involvedObject.name=try-other \
  -o custom-columns=LAST:.lastTimestamp --no-headers
```


```plain text
2026-11-17T00:54:47Z
2026-11-17T00:54:48Z
2026-11-17T00:54:49Z
2026-11-17T00:54:53Z
2026-11-17T00:55:01Z
2026-11-17T00:55:17Z
2026-11-17T00:55:49Z
```


그래서 권한을 고친 뒤에는 마지막 시도가 언제였는지부터 봅니다. 기다리기 싫다면 주석 하나로 바로 다시 시도하게 할 수 있는데 저는 그날 이 주석으로 남아 있던 실패를 바로 풀었습니다.


```bash
kubectl annotate externalsecret app-env force-sync="$(date +%s)" --overwrite
```


---


## ESO가 만든 Secret은 지워도 되살아납니다


⑦편에서는 Secret을 사람이 만들었으니 사람이 지우면 끝이었습니다. 이번에는 만든 쪽이 ESO라서 사정이 다릅니다. ESO는 자기가 맡은 Secret이 사라지면 원본을 다시 읽어 새로 만듭니다.


### 일부러 깨 보기 ③: `app-env`를 손으로 지워 보기


`app-env`는 이제 ExternalSecret의 소유물입니다. `creationPolicy: Owner`가 그런 뜻인데, 손으로 지우면 어떻게 될까요?


```bash
kubectl get secret app-env -o jsonpath='{.metadata.uid}{"\n"}'
kubectl delete secret app-env
sleep 3; kubectl get secret app-env -o jsonpath='{.metadata.uid}{"\n"}'
```


```plain text
4433d49b-8183-4346-b32f-87c3a13d3f48
secret "app-env" deleted from default namespace
aa5f7a89-9b58-4280-a80c-c42e0209b75a
```


3초 만에 같은 이름의 다른 객체가 생겼습니다. 7월 28일 원본에서는 8초였습니다. 그러니 Secret을 없애고 싶다면 Secret 대신 소유자인 ExternalSecret을 지워야 하고 그러면 Secret도 함께 지워집니다. 정리 순서가 ExternalSecret부터인 것도 이 때문입니다.


---


## 원본 값을 바꿔도 돌고 있는 앱은 옛 값을 씁니다


Secrets Manager의 값을 바꾸면 앱에는 언제 닿을까요? 그림의 마지막 칸이 바로 이 질문입니다. 이 글을 쓰며 `TOKEN_SECRET`만 새 값으로 바꾸고 `force-sync`로 바로 동기화한 뒤 Secret과 앱 안의 값을 비교했습니다. 원본 값을 바꾸는 실험이라 따라 하지 않고 결과만 보셔도 됩니다. 값을 그대로 찍지 않으려고 앞 여덟 자리 해시만 봅니다.


```plain text
Secret 의 TOKEN_SECRET     0fb566b2   ← 새 값
앱 컨테이너의 TOKEN_SECRET  5173bc33   ← 옛 값
rollout restart 뒤          0fb566b2
```


Secret은 몇 초 만에 새 값이 됐지만 앱은 옛 값을 그대로 들고 있었습니다. `envFrom`으로 받은 환경변수는 컨테이너가 시작할 때 한 번 정해지기 때문입니다. 그래서 값을 바꿨다면 `kubectl rollout restart deploy/app`까지가 한 묶음입니다.


직접 바꿔 보셨다면 값을 원래대로 되돌려야 합니다. 그냥 `tofu apply`를 하면 OpenTofu는 바뀐 것을 알아채지 못하는데 이 글을 쓰며 바꾼 뒤에 `apply`했을 때도 그랬습니다. 그래서 시크릿 버전을 state의 값으로 다시 만들라고 지정해 줍니다.


```bash
tofu -chdir=0-bootstrap apply -replace=aws_secretsmanager_secret_version.app
```


---


## 정리할 때는 소유자부터 지우고, 시크릿 원본은 남깁니다


이번 편에서 클러스터 안에 더한 것은 ESO와 매니페스트 두 장입니다. 앞 절에서 본 대로 ExternalSecret을 먼저 지워야 Secret이 되살아나지 않습니다. ESO 자체는 클러스터와 함께 사라지므로 따로 지우지 않아도 됩니다.


```bash
kubectl delete -f k8s/eso/app-env.yaml -f k8s/eso/secretstore.yaml
kubectl delete -f k8s/app.yaml -f k8s/db-temp.yaml
cd 2-cluster && tofu destroy && cd ..
```


`Destroy complete! Resources: 16 destroyed.`가 나오면 ⑤편의 확인 명령을 돌립니다. 그리고 하나를 더 확인하는데 `0-bootstrap`에 만든 시크릿은 남아 있어야 합니다. 다음에 클러스터를 세우면 ESO가 같은 값을 다시 가져옵니다.


```bash
aws secretsmanager list-secrets --region ap-northeast-2 --query 'SecretList[].Name' --output text
# eks-lab/app
```


`k8s/eso/` 아래 두 파일은 커밋합니다. 들어 있는 것은 시크릿의 이름뿐이고 값은 없으니 공개 레포에 올려도 됩니다.


---


## 이 방식은 state 파일과 파드 세 개로 값을 치릅니다


비밀값이 셸 기록에서는 사라졌지만 완전히 사라진 것은 아닙니다. `random_password`가 뽑은 값은 OpenTofu의 state 파일에 평문으로 적힙니다. ③편에서 state를 암호화된 S3 버킷에 두고 공개 레포에 올리지 않게 한 것이 여기서 의미를 갖습니다. 그래도 버킷을 읽을 수 있는 사람은 비밀번호도 읽을 수 있습니다.


노드의 자리도 씁니다. ESO는 파드 세 개로 돌고, t4g.small 한 대는 ⑤편에서 본 대로 파드 11개가 상한입니다. 이번 편을 마친 시점에 시스템 파드 넷과 ESO 셋, 데이터베이스와 앱까지 아홉 자리가 찼습니다. 다음 편에서 디스크 드라이버를 더하면 남는 자리가 없어지는데 그 이야기는 ⑨편에서 이어집니다.


그리고 이 글은 IRSA를 썼지만 EKS에는 EKS Pod Identity라는 더 새로운 방식도 있습니다. OIDC 공급자와 신뢰 정책의 조건을 직접 쓰지 않아도 되는 대신 애드온을 하나 더 설치해야 합니다. 저는 원본에서 IRSA만 썼기 때문에 이 시리즈도 IRSA로 갑니다. Pod Identity는 직접 돌려 보지 않았으니 공식 문서를 참고하시기 바랍니다.


---


## 정리


| 할 일        | 명령이나 파일                              | 확인                   |
| ---------- | ------------------------------------ | -------------------- |
| 시크릿 원본 만들기 | `0-bootstrap/app-secret.tf`          | `4 added`            |
| 역할 만들기     | `2-cluster/irsa-eso.tf`              | `16 to add`          |
| 역할 주소 확인   | `case "$ESO_ROLE" in arn:aws:iam::*` | `OK`로 시작             |
| ESO 설치 확인  | 파드 안 `AWS_ROLE_ARN`                  | `arn:aws:iam::`로 시작  |
| Secret 만들기 | `k8s/eso/*.yaml`                     | `SecretSynced`, 키 5개 |
| 값을 바꾼 뒤    | `kubectl rollout restart deploy/app` | 앱 안의 값이 새 값          |


비밀값을 클러스터에 넣는 일을 이제 사람 대신 ESO가 맡게 됐습니다. ESO는 액세스 키 없이 자기 서비스 계정으로 역할을 빌리고 그 역할은 시크릿 하나만 읽을 수 있습니다. 실패하면 메시지의 주체를 보고 신뢰 정책과 권한 정책 중 어디서 막혔는지 가릅니다.


다음 편에서는 임시 데이터베이스를 디스크가 붙은 데이터베이스로 바꿉니다. 파드를 지워도 데이터가 남게 하려면 쿠버네티스가 EBS 디스크를 직접 만들어야 하는데 그 일을 하는 드라이버도 이번 편과 같은 방식으로 역할을 빌립니다.


---


## 참고

- [Amazon EKS 사용 설명서, 서비스 계정의 IAM 역할(IRSA)](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Amazon EKS 사용 설명서, EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [External Secrets Operator, AWS Secrets Manager](https://external-secrets.io/latest/provider/aws-secrets-manager/)
- [AWS Secrets Manager 요금](https://aws.amazon.com/secrets-manager/pricing/)
- 시크릿 단가(서울 리전, 시크릿당 월 \$0.40)는 2026년 11월 17일에 AWS Pricing API로 조회한 값입니다.
- 제 원본 작업 일지와 전체 코드는 [switch-job-quest](https://github.com/bangddong/switch-job-quest) 레포에 있습니다. 서비스를 닫으면서 보관(archive)해 두었습니다.
> 이 편의 코드와 매니페스트는 이 글을 위해 새로 쓴 것입니다. 제 원본은 이 단계에서 데이터베이스를 RDS로 두고 Secrets Manager의 시크릿을 셋으로 나눴는데, 이 시리즈는 RDS를 건너뛰고 ⑨편에서 바로 클러스터 안 데이터베이스로 가므로 시크릿을 하나로 줄였습니다. 2026년 11월 17일에 이 코드를 제 계정에 실제로 apply하고, 위의 출력을 그 클러스터에서 받았습니다. 다만 그날은 ECR과 함께 만들어 `0-bootstrap`이 `6 added`였고, ⑨편까지 이어서 한 뒤 부숴서 `19 destroyed`였습니다. 글의 `4 added`와 `16 destroyed`는 거기서 이번 편 몫만 센 값입니다. 그리고 제 확인용 state는 S3 대신 노트북에 두었기 때문에 `remote-state.tf`의 `backend`만 글과 달랐습니다. 비용은 클러스터를 세우고 이번 편을 마치고 부수기까지 한 시간이 넘지 않는다고 보고, ⑤편의 시간당 \$0.13쯤으로 어림한 값입니다. 역할 주소에 경고문이 들어간 일은 8월 12일, 권한 오류와 재시도 간격, Secret이 되살아난 일은 7월 28일 제 일지의 기록입니다. 막히는 곳이 있으면 알려 주시기 바랍니다.
>
> 이 글의 그림은 AI가 그렸습니다.
>
>
