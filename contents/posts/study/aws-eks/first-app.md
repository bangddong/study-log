---
title: '이미지는 노트북이 아니라 CI가 굽는다. EKS 실습기 ⑥, 이미지를 올리고 첫 앱을 띄우는 법'
date: '2026-11-10'
tags:
  - AWS
  - EKS
series: AWS EKS 실습기
emoji: ''
---
> **AWS 프리티어 \$200으로 EKS 실습하기 ⑥** · 💰 클러스터를 켜는 20분쯤에 약 **\$0.05**, 이미지 보관료는 월 1센트 안팎

클러스터를 세웠으니 이제 그 위에 앱을 올릴 차례입니다. 그런데 노드는 내 노트북에 있는 이미지를 볼 수 없습니다. 이미지를 어딘가에 올려 두어야 노드가 받아 갈 수 있고, AWS에서는 그 자리가 ECR이라는 이미지 저장소입니다. 그러면 이미지는 누가 만들어서 올려야 할까요? 노트북에서 `docker build`를 치면 가장 빠르겠지만, 이 시리즈는 GitHub Actions가 굽게 합니다. 그래서 노트북에 Docker가 없어도 됩니다.


이번 편에서는 GitHub에 내 레포를 하나 만들고, 글에 실린 파일 몇 개로 작은 Spring Boot 앱을 만들어 띄웁니다. 그리고 중간중간 일부러 깨 보는 절을 둡니다. 제가 실제로 막혔던 자리를 지금 코드에서 똑같이 막혀 보고, 왜 막히는지 확인한 뒤 되돌리는 순서입니다. 깨 보는 단계는 전부 클러스터를 켜기 전에 하니 요금이 붙지 않습니다.

> 이미지는 노트북이 아니라 CI가 굽는다.

---


## 이미지는 네 곳을 거쳐 노드에 닿습니다


이미지 하나가 노드에 닿기까지 거치는 곳이 생각보다 많습니다. GitHub가 이미지를 굽고, AWS가 그 GitHub를 믿어 주고, ECR이 이미지를 보관하고, 노드가 받아 갑니다. 아래 그림은 그 길을 위에서 아래로 늘어놓은 것이니, 오른쪽에 적은 층 이름을 보시기 바랍니다.


```plain text
내 레포의 main에 push                              GitHub
 └─ GitHub Actions (arm64 러너)가 이미지를 굽는다
     └─ GitHub가 발급한 토큰으로 AWS 역할을 빌린다  0-bootstrap (이번 편)
         └─ ECR에 커밋 sha 태그로 올린다            0-bootstrap (이번 편)
             └─ 노드가 자기 역할로 받아 간다         2-cluster (⑤편)
                 └─ 파드가 뜬다                     kubectl (이번 편)
```


새로 만드는 AWS 리소스는 모두 `0-bootstrap` 층에 들어갑니다. ③편에서 state 저장소와 예산을 둔 층이고, 시리즈가 끝날 때까지 지우지 않는 곳입니다. 노드가 이미지를 받아 가는 권한은 ⑤편에서 이미 노드 역할에 붙여 두었으니, 클러스터 쪽 코드는 고칠 것이 없습니다.


---


## 앱은 글에 실린 파일 네 개로 시작합니다


제가 처음 EKS에 올린 앱은 운영하던 서비스의 백엔드였습니다. 그 앱은 데이터베이스와 비밀값, 외부 로그 서비스까지 갖춰야 뜨는 앱이라, 처음 따라 하기에는 짐이 너무 많습니다. 그래서 이 시리즈는 아주 작은 앱으로 시작해 편마다 필요한 만큼만 키웁니다. 이번 편의 앱은 인사말을 돌려주는 주소 하나와 상태 확인 주소 하나가 전부입니다.


먼저 GitHub CLI를 설치하고 로그인합니다. ②편에서 설치한 도구에는 없던 것이고, 레포 생성과 시크릿 등록, 워크플로 실행을 모두 이것으로 합니다. Linux나 WSL이라면 GitHub CLI 설치 안내의 패키지 관리자 명령을 쓰시면 됩니다.


```bash
brew install gh
gh auth login
git --version
```


`gh auth login`이 묻는 것 가운데 git 통신 방식은 HTTPS를 고르고, GitHub 자격 증명으로 git을 인증하겠냐는 물음에 `Yes`로 답합니다. 그래야 뒤의 `git push`가 따로 비밀번호를 묻지 않습니다. macOS에서 `git --version`이 개발자 도구 설치 창을 띄우면 설치를 마친 뒤 다시 확인합니다.


앱은 ③편부터 쓰던 폴더, 그러니까 `0-bootstrap`과 `1-network`, `2-cluster`가 나란히 있는 곳에 `app` 폴더로 만듭니다. ⑤편을 막 마쳤다면 `2-cluster` 안에 있을 테니 한 칸 올라가서 시작합니다. 뼈대는 Spring 공식 생성기에서 받는데, 웹과 상태 확인(actuator) 기능만 고릅니다.


```bash
cd ..
curl -sS https://start.spring.io/starter.tgz \
  -d type=gradle-project-kotlin -d language=java -d javaVersion=21 \
  -d groupId=lab.eks -d artifactId=app -d packageName=lab.eks.app \
  -d dependencies=web,actuator -d baseDir=app | tar -xzf -
```


`app` 폴더 안에 `build.gradle.kts`와 `src`가 생기면 됩니다. 이 글은 2026년 11월에 받은 Spring Boot 4.1.2를 기준으로 썼습니다. 받은 뼈대에 컨트롤러 하나를 더합니다.


```java
// app/src/main/java/lab/eks/app/HelloController.java
package lab.eks.app;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HelloController {

    @GetMapping("/hello")
    public String hello() {
        return "hello from eks-lab";
    }
}
```


설정은 `application.properties`를 지우고 `application.yml` 하나로 둡니다. 상태 확인 주소는 `/actuator/health` 하나만 열어 둡니다.


```yaml
# app/src/main/resources/application.yml
server:
  port: 8080

management:
  endpoints:
    web:
      exposure:
        include: health
```


마지막이 이미지를 만드는 `Dockerfile`입니다. 빌드 단계에서 jar를 만들어 이름을 `app.jar`로 고정하고, 실행 단계에는 JRE와 그 jar 하나만 담아 이미지를 작게 유지합니다.


```docker
# app/Dockerfile
# 빌드 단계: Gradle 로 실행 가능한 jar 를 만들어 이름을 고정합니다
FROM gradle:9.8-jdk21 AS build
WORKDIR /src
COPY . .
RUN gradle bootJar --no-daemon && cp build/libs/*.jar app.jar

# 실행 단계: JRE 와 jar 하나만 담습니다
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=build /src/app.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```


`app/.dockerignore`에 `build`와 `.gradle` 두 줄을 적어 두면, 노트북에서 빌드해 본 흔적이 이미지에 섞이지 않습니다. 빌드 명령이 `build`가 아니라 `bootJar`인 데는 이유가 있는데, 그 이유는 뒤에서 일부러 깨 보면서 확인합니다.


---


## 이미지 저장소는 클러스터보다 오래 살아야 합니다


ECR은 어느 층에 두어야 할까요? 저는 처음에 클러스터 층에 넣을 생각이었는데, 그러면 클러스터를 부술 때마다 이미지도 함께 사라집니다. 이 시리즈는 실습이 끝날 때마다 클러스터를 부수니, 매번 이미지를 다시 구워야 한다는 뜻입니다. 그래서 7월 26일에 ECR을 `0-bootstrap`으로 옮겼고, 덕분에 다음 날 클러스터를 부순 뒤에도 이미지가 남았습니다.


`0-bootstrap` 폴더에 파일을 하나 더합니다. 저장소 이름은 ⑤편의 클러스터 이름에 맞춰 `eks-lab/app`으로 짓습니다.


```hcl
# ecr.tf
resource "aws_ecr_repository" "app" {
  name                 = "eks-lab/app"
  image_tag_mutability = "IMMUTABLE" # 한 번 붙은 태그는 다른 이미지를 가리킬 수 없습니다

  image_scanning_configuration {
    scan_on_push = true # 기본 취약점 스캔, 무료
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "최근 이미지 10개만 남긴다"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}
```


ECR은 저장한 용량만큼 돈을 받습니다. 서울 리전은 GB당 월 \$0.10이고, 이번 앱은 노트북에서 구워 보니 압축을 풀어도 93MB쯤이라 한 장에 한 달 1센트가 되지 않습니다. 대신 쌓이는 만큼 늘어나므로 아래쪽 정책으로 최근 열 장만 남기고 나머지는 자동으로 지웁니다.


`IMMUTABLE`은 태그 하나가 언제나 같은 이미지를 가리키게 하는 설정입니다. 태그를 커밋의 sha로 붙이면, 태그만 보고 어느 커밋의 코드인지 알 수 있습니다. 제 원본은 처음에 `latest` 태그를 함께 붙이느라 덮어쓰기를 허용했다가, 10월에 `latest`를 없애면서 이 설정으로 바꿨습니다. 이 글은 처음부터 sha 태그 하나만 씁니다.


---


## CI가 AWS에 들어갈 때는 키 대신 토큰을 씁니다


GitHub Actions가 ECR에 이미지를 올리려면 AWS에 로그인해야 하는데, 무엇으로 로그인하게 해야 할까요? 가장 쉬운 방법은 ②편에서 만든 것 같은 액세스 키를 GitHub 시크릿에 넣는 것입니다. 하지만 그 키는 지우기 전까지 계속 유효해서, 한 번 새면 누가 언제 써도 막을 수 없습니다. 그래서 이 시리즈는 키를 넣지 않고 OIDC라는 방식을 씁니다.


OIDC에서는 워크플로가 실행될 때마다 GitHub가 짧게 사는 토큰을 발급합니다. 이 토큰에는 어느 레포의 어느 브랜치에서 실행됐는지가 적혀 있고, AWS는 그 내용을 보고 정해 둔 역할을 잠깐 빌려줍니다. 저장해 둘 비밀이 없으니 샐 것도 없습니다. 이를 위해 AWS에 GitHub를 믿을 만한 발급자로 등록하고, 토큰을 받아 줄 역할을 하나 만듭니다.


```hcl
# github-oidc.tf
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

resource "aws_iam_role" "github_ecr_push" {
  name = "github-actions-ecr-push" # eks-lab 으로 시작하지 않게 짓습니다

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:ref:refs/heads/main"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_ecr_push" {
  name = "ecr-push"
  role = aws_iam_role.github_ecr_push.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken" # 로그인은 레포를 가리지 않습니다
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
          "ecr:BatchGetImage",
        ]
        Resource = aws_ecr_repository.app.arn
      },
    ]
  })
}
```


이 파일에서 가장 중요한 줄은 `sub` 조건입니다. 이 조건이 없으면 GitHub에 있는 아무 레포나 이 역할을 빌려 갈 수 있습니다. 여기서는 내 레포의 `main` 브랜치에서 실행된 워크플로만 받아 주니, 같은 레포라도 다른 브랜치에서 돌린 워크플로는 거절됩니다. 이 거절은 뒤에서 직접 받아 봅니다.


권한은 이미지를 올리는 데 필요한 동작만 줍니다. 로그인 토큰을 받는 동작 하나는 저장소를 지정할 수 없어 `*`이고, 나머지는 방금 만든 저장소 하나로 묶었습니다. 제 원본은 처음에 이 역할에 관리자 권한을 주고 PR에서도 빌릴 수 있게 했습니다. 10월에야 쓰기는 `main` 전용 역할로 따로 나눴는데, 이 글은 처음부터 좁게 시작합니다.


⑤편에서 클러스터의 OIDC 공급자를 만들 때는 인증서 지문(`thumbprint_list`)을 `tls` 공급자로 읽어 넣었습니다. 이번에는 그 칸을 비워 두었는데, 이 코드가 쓰는 AWS 공급자에서는 선택 항목이라 비워 두면 AWS가 채웁니다. 제 원본은 ⑤편처럼 지문을 읽어 넣었지만, 줄일 수 있는 것은 줄였습니다.


레포 이름은 변수로 받습니다. 레포는 다음 절에서 `eks-lab`이라는 이름으로 만들 것이니, 그 이름으로 적어 둡니다.


```hcl
# variables.tf 에 더합니다
variable "github_repo" {
  type        = string
  description = "이미지를 빌드할 GitHub 레포 (<아이디>/<레포 이름>)"
}
```


```hcl
# terraform.tfvars 에 더합니다
github_repo = "<본인 GitHub 아이디>/eks-lab"
```


다음 단계에서 쓸 값 두 개도 내보냅니다. 저장소 주소는 매니페스트에 넣을 때, 역할의 ARN은 GitHub에 알려 줄 때 씁니다. `outputs.tf`가 아직 없다면 새로 만들면 됩니다.


```hcl
# outputs.tf
output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "github_role_arn" {
  value = aws_iam_role.github_ecr_push.arn
}
```


파일을 다 더했으면 계획을 봅니다. 공급자가 늘지 않았으니 `init`을 다시 할 필요는 없고, state는 ③편에서 옮겨 둔 S3에서 그대로 읽어 옵니다. 여기까지도 요금은 없습니다.


```bash
cd 0-bootstrap
tofu plan
```


```plain text
Plan: 5 to add, 0 to change, 0 to destroy.
```


다섯 개는 저장소와 정리 정책, OIDC 공급자, 역할과 그 권한입니다. ③편에서 만든 예산과 버킷은 손대지 않았으니 `0 to change, 0 to destroy`여야 합니다. 그렇게 나오면 적용하는데, 다섯 개 모두 만들어 두는 것만으로는 요금이 없습니다.


```bash
tofu apply
```


```plain text
Apply complete! Resources: 5 added, 0 changed, 0 destroyed.
```


만약 계정에 이미 GitHub OIDC 공급자가 있다면 `EntityAlreadyExists`로 멈춥니다. 같은 주소의 공급자는 계정에 하나만 둘 수 있으니, 그때는 있는 것을 `tofu import`로 가져오면 됩니다.


---


## 레포는 공개로 만들고, 워크플로는 브랜치에서 시작합니다


이제 폴더 전체를 GitHub 레포로 올립니다. 공개 레포로 만드는 것은 뒤에서 쓸 arm64 러너가 공개 레포에서 무료이기 때문입니다. 대신 누구나 볼 수 있으니 올리기 전에 `.gitignore`부터 확인합니다. ③편에서 넣은 두 줄에 아래 두 줄을 더해, 내려받은 공급자 파일과 저장해 둔 계획 파일이 올라가지 않게 합니다.


```plain text
terraform.tfvars
*.tfstate*
.terraform/
*.tfplan
```


```bash
cd ..
git init -b main   # 이미 git 폴더라면 건너뜁니다
git add .
git status         # terraform.tfvars 가 목록에 없어야 합니다
git commit -m "eks-lab: 인프라 코드와 첫 앱"
gh repo create eks-lab --public --source=. --push
```


`git status`에서 `terraform.tfvars`가 보이면 커밋하지 말고 `.gitignore`부터 고칩니다. 이메일 주소가 들어 있는 파일입니다. 한편 세 층의 `backend.tf`에 적은 state 버킷 이름은 그대로 공개됩니다. 이름은 자격 증명이 아니고 ③편에서 퍼블릭 접근을 네 가지 모두 막아 두었으니 괜찮지만, 이름에 개인 정보를 넣지 않았는지는 한 번 보시기 바랍니다.


워크플로가 빌릴 역할의 ARN은 레포 시크릿에 넣습니다. ARN 안에 계정 ID가 들어 있어서, 워크플로 파일에 바로 적으면 공개 레포에 그대로 드러나기 때문입니다.


```bash
gh secret set AWS_ROLE_ARN --body "$(tofu -chdir=0-bootstrap output -raw github_role_arn)"
```


`✓ Set Actions secret AWS_ROLE_ARN`이 나오면 됩니다. 이제 워크플로를 만드는데, 바로 `main`에 넣지 않고 브랜치에서 시작합니다. 제가 그랬기 때문이고, 그 길에서 만나는 첫 번째 막힘을 함께 보려는 것입니다.


```bash
git switch -c add-ci
```


```yaml
# .github/workflows/ecr-push.yml
name: ECR Push

on:
  push:
    branches: [main]
    paths:
      - "app/**"
      - ".github/workflows/ecr-push.yml"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build-push:
    runs-on: ubuntu-24.04-arm # 노드가 arm64 라서 arm64 러너에서 바로 굽습니다
    permissions:
      id-token: write # GitHub 토큰을 받아 AWS 역할을 빌립니다
      contents: read
    steps:
      - uses: actions/checkout@v4

      # AWS 에 들어가기 전에 먼저 굽습니다. 권한은 올리는 순간에만 빌립니다
      - name: 이미지 빌드
        run: docker build -t app:build app

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ap-northeast-2

      # 공개 레포의 로그는 누구나 봅니다. 이미지 주소에 계정 ID 가 들어 있어 미리 가립니다
      - name: 계정 ID 가리기
        run: |
          ACCT=$(aws sts get-caller-identity --query Account --output text)
          [[ "$ACCT" =~ ^[0-9]{12}$ ]] || { echo "계정 ID 조회 실패"; exit 1; }
          echo "::add-mask::$ACCT"

      - id: ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: 푸시
        env:
          IMAGE: ${{ steps.ecr.outputs.registry }}/eks-lab/app:${{ github.sha }}
        run: |
          docker tag app:build "$IMAGE"
          docker push "$IMAGE"
```


러너를 `ubuntu-24.04-arm`으로 고른 것은 ⑤편의 노드가 arm64인 Graviton이기 때문입니다. 굽는 곳과 도는 곳의 아키텍처가 다르면 어떻게 되는지는 뒤에서 따로 다룹니다.


계정 ID를 가리는 단계에는 사연이 있습니다. 제가 7월에 처음 만든 워크플로는 이미지 주소를 실행 요약에 그대로 찍었습니다. ECR 주소는 `<계정 ID>.dkr.ecr...`로 시작하니, 공개 레포의 요약에 계정 ID가 실린 셈입니다. 9월 중순에야 알아채고 고쳤고, 이 글의 워크플로는 주소를 아예 찍지 않고 로그에서도 가립니다.


### 일부러 깨 보기 ①: 브랜치에만 있는 워크플로는 실행할 수 없습니다


7월 27일에 저는 워크플로를 브랜치에 만든 채로 직접 실행해 보려 했고, HTTP 404를 받았습니다. 지금 상태에서 똑같이 해 보면 같은 자리에서 막힙니다.


```bash
git add .github/workflows/ecr-push.yml
git commit -m "ci: ECR 푸시 워크플로"
git push -u origin add-ci
gh workflow run ecr-push.yml --ref add-ci
```


`HTTP 404`와 함께 기본 브랜치에서 워크플로를 찾지 못했다는 오류가 나면 제대로 막힌 것입니다. 오류 문구는 `gh` 버전에 따라 조금 다르지만, 404라는 점은 같습니다. GitHub는 직접 실행하는 워크플로의 정의를 기본 브랜치에서만 찾습니다. `--ref`로 브랜치를 알려 줘도, 파일이 `main`에 없으면 없는 워크플로로 봅니다.


그러니 파일을 `main`에 넣습니다. 혼자 쓰는 레포이지만 PR을 거쳐 합치면 무엇이 들어가는지 한 번 더 보게 됩니다. 합치는 순간 `main`에 워크플로 파일이 생기고, `paths` 조건에 걸려 첫 빌드가 바로 시작됩니다.


```bash
gh pr create --fill
gh pr merge --merge --delete-branch
git switch main && git pull
sleep 5 && gh run watch
```


실행이 만들어지기까지 몇 초가 걸려서 `sleep 5`를 앞에 두었습니다. `gh run watch`가 초록으로 끝나면 ECR에 이미지가 들어왔는지 AWS에 물어봅니다.


```bash
aws ecr describe-images --repository-name eks-lab/app --region ap-northeast-2 \
  --query 'imageDetails[].imageTags' --output text
git rev-parse HEAD
```


두 줄이 같은 40자리 sha를 보여 주면 성공입니다. 이미지 태그가 방금 합친 커밋 그대로라는 뜻이고, 이 값이 뒤에서 배포할 태그가 됩니다.


### 일부러 깨 보기 ②: main이 아닌 곳에서 돌리면 AWS가 거절합니다


이제는 워크플로가 `main`에 있으니 브랜치를 지정해 실행할 수 있습니다. 그날 저는 브랜치 push로 실행되게 바꿔서 돌렸는데, 이번에는 AWS가 거절했습니다. 시험용 브랜치를 하나 만들어 똑같이 돌려 봅니다.


```bash
git switch -c try-branch
git push -u origin try-branch
gh workflow run ecr-push.yml --ref try-branch
sleep 5 && gh run watch
```


이미지는 구워지지만, 그다음 AWS 로그인 단계에서 제가 그날 받은 것과 같은 오류로 멈춥니다.


```plain text
Could not assume role with OIDC: Not authorized to perform sts:AssumeRoleWithWebIdentity
```


브랜치에서 발급된 토큰의 `sub`는 `ref:refs/heads/try-branch`로 끝납니다. 그런데 역할이 받아 주는 값은 `ref:refs/heads/main` 하나뿐입니다. 앞에서 넣은 `sub` 조건이 정확히 제 일을 한 것입니다. 저는 그날 조건을 풀지 않았고, 이 글에서도 풀지 않습니다. 브랜치의 변경을 이미지로 보고 싶으면 `main`에 합치면 됩니다.


### 일부러 깨 보기 ③: jar가 두 개면 이미지 빌드가 멈춥니다


같은 브랜치에서 하나를 더 깨 봅니다. `Dockerfile`의 빌드 명령이 `bootJar`인 이유를 확인하려는 것이니, `build`로 바꿔 봅니다.


```docker
# app/Dockerfile 의 빌드 명령 한 줄에서 bootJar 만 build 로 바꿉니다 (확인 후 되돌립니다)
RUN gradle build -x test --no-daemon && cp build/libs/*.jar app.jar
```


```bash
git commit -am "test: 빌드 명령 바꿔 보기"
git push
gh workflow run ecr-push.yml --ref try-branch
sleep 5 && gh run watch
```


이번에는 AWS에 닿기도 전에 이미지 빌드 단계에서 멈춥니다. 저도 노트북에서 이 한 줄만 바꿔 구워 보았는데, `cp`가 이렇게 거절했습니다.


```plain text
cp: target 'app.jar': No such file or directory
```


GitHub 러너의 로그에서는 이 줄 앞뒤에 빌드 도구가 붙이는 형식이 조금 달라 보일 수 있지만, `cp`가 거절한 이 한 줄은 같습니다.


`build`는 실행 가능한 jar 말고도 의존성을 뺀 `-plain.jar`를 하나 더 만듭니다. 그러자 `*.jar`가 파일 두 개로 펼쳐지고, `cp`는 파일 여럿을 받으면 마지막 인자를 폴더로 여기는데 그런 폴더가 없으니 멈춘 것입니다. 저는 7월 27일 배포 전에 다른 서비스의 빌드에서 바로 이 `cp` 함정을 미리 발견해, 실행 가능한 jar 하나만 집도록 고쳐 두었습니다.


이 글이 처음부터 실행 가능한 jar만 만드는 `bootJar`를 쓰는 것도 같은 이유입니다. `cp`를 거치는 데도 이유가 하나 더 있습니다. 같은 글롭을 `COPY`에 바로 쓰면 빌드 도구에 따라 결과가 갈리는데, GitHub 러너가 쓰는 BuildKit은 멈추지 않고 파일 하나만 조용히 골라 담습니다. 실패가 드러나지 않는 쪽이 더 위험하니, 이 글은 이름을 `cp`로 한 번 고정해 두고 받습니다. 확인했으면 브랜치를 지우고 `main`으로 돌아갑니다.


```bash
git switch main
git branch -D try-branch
git push origin --delete try-branch
```


### 굽는 곳과 도는 곳의 아키텍처가 다르면 실행하는 순간 죽습니다


이것은 제가 겪은 실패가 아닙니다. 저는 처음부터 arm64 러너에서 구웠기 때문인데, 원리는 알아 둘 만합니다. 보통의 `ubuntu-latest` 러너는 x86이라 거기서 구운 이미지도 x86용입니다. 그 이미지를 arm64 노드에 올리면 노드는 이미지를 받기까지는 하지만, 실행하는 순간 `exec format error`를 내고 죽습니다.


다시 말해 이미지 받기가 성공했다고 아키텍처가 맞다는 보장은 없습니다. 에뮬레이션으로 x86 러너에서 arm64를 굽는 방법도 있지만 Gradle 빌드가 몇 배 느려진다고 알려져 있습니다. 그러니 처음부터 arm64 러너에서 굽는 편이 낫습니다. 노트북이 Apple Silicon이라면 거기서 구운 이미지는 이미 arm64입니다.


---


## 앱은 OpenTofu가 아니라 매니페스트로 올립니다


여기서부터 돈이 나갑니다. ⑤편의 `2-cluster` 폴더로 가서 클러스터를 다시 세웁니다. ⑤편에서 부수고 사라진 것까지 확인했다면 계획은 다시 `14 to add, 0 to change, 0 to destroy`여야 합니다.


```bash
cd 2-cluster
tofu plan -out=cluster.tfplan
tofu apply cluster.tfplan
aws eks update-kubeconfig --name eks-lab --region ap-northeast-2
kubectl get nodes
cd ..
```


노드가 `Ready`가 되면 앱을 올립니다. 앱은 OpenTofu가 아니라 `kubectl`로 올립니다. 쿠버네티스 안의 것까지 state에 넣으면 `tofu destroy`가 앱까지 책임지게 되어 층의 경계가 흐려지기 때문입니다. 그래서 클라우드 리소스는 OpenTofu로, 쿠버네티스 안의 것은 매니페스트 파일로 나눠 둡니다. 레포 맨 위에 `k8s` 폴더를 만들고 파일을 하나 둡니다.


```yaml
# k8s/app.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app # 아래 template 의 라벨과 같아야 합니다
  template:
    metadata:
      labels:
        app: app
    spec:
      containers:
        - name: app
          image: IMAGE_PLACEHOLDER # 적용할 때 sha 태그로 바꿉니다
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: app
spec:
  type: ClusterIP # 클러스터 안에서만 닿는 주소입니다
  selector:
    app: app
  ports:
    - port: 8080
      targetPort: 8080
```


Deployment는 "이 이미지를 하나 띄우고, 죽으면 다시 띄워 달라"는 선언입니다. 메모리는 2GB짜리 노드에 시스템 파드까지 함께 올라가야 하니 작게 잡았습니다.


Service를 `LoadBalancer`가 아니라 `ClusterIP`로 둔 데는 돈 문제가 걸려 있습니다. `LoadBalancer`로 만들면 쿠버네티스가 AWS에 로드밸런서를 직접 만듭니다. 그 로드밸런서는 OpenTofu의 state 밖이라 `tofu destroy`가 지우지 못합니다. 바깥에서 들어오는 길은 ⑪편에서 정식으로 내고, 그때 정리하는 순서도 함께 다룹니다.


이미지 자리에는 `latest`가 아니라 앞에서 확인한 sha 태그를 넣습니다. `latest`로 배포하면 지금 도는 것이 어느 커밋인지 알 수 없고, 되돌릴 기준도 사라집니다. 태그는 `git rev-parse HEAD`가 아니라 ECR에 가장 최근에 올라간 것으로 고릅니다. `k8s` 폴더만 커밋해도 HEAD는 바뀌는데, 그 커밋은 `paths` 조건에 걸리지 않아 이미지가 없기 때문입니다.


```bash
REPO=$(tofu -chdir=0-bootstrap output -raw ecr_repository_url)
SHA=$(aws ecr describe-images --repository-name eks-lab/app --region ap-northeast-2 \
  --query 'sort_by(imageDetails,&imagePushedAt)[-1].imageTags[0]' --output text)
sed "s|IMAGE_PLACEHOLDER|$REPO:$SHA|" k8s/app.yaml | kubectl apply -f -
```


```plain text
deployment.apps/app created
service/app created
```


---


## 합격선은 Pulled 한 줄과 인사말 한 줄입니다


먼저 ECR에 올린 이미지가 노드로 내려왔는지 봅니다. 파드가 아직 뜨는 중이어도 상관없습니다. 이미지를 받아 온 기록은 파드의 이벤트에 먼저 남기 때문입니다.


```bash
kubectl describe pod -l app=app | grep -E "Pulling|Pulled"
```


```plain text
Normal  Pulling  kubelet  Pulling image ".../eks-lab/app:<sha>"
Normal  Pulled   kubelet  Successfully pulled image ".../eks-lab/app:<sha>" in <몇 초>
```


`Successfully pulled image`가 보이면 첫 관문은 넘은 것입니다. 제가 처음 올린 서비스의 이미지는 166MB쯤이었는데 3.2초 만에 받았고, ECR과 노드가 같은 리전에 있어서 빠른 것입니다.


눈여겨보실 것은 비밀번호를 하나도 주지 않았는데 받아 왔다는 점입니다. 다른 저장소의 비공개 이미지라면 `imagePullSecret`으로 로그인 정보를 따로 넣어야 합니다. 여기서는 ⑤편에서 노드 역할에 붙인 `AmazonEC2ContainerRegistryReadOnly`가 그 일을 대신합니다. 노드가 자기 역할로 ECR에 로그인하는 것입니다. 같은 계정의 같은 리전이라 이것만으로 충분합니다.


받기만 한 것이 아니라 실제로 도는지도 봅니다. 파드가 `Running`이 되면, `ClusterIP`라 바깥에서는 닿지 않으니 내 노트북의 포트를 잠깐 클러스터로 이어 줍니다.


```bash
kubectl get pods -l app=app
kubectl port-forward svc/app 8080:8080
```


다른 터미널에서 두 주소를 불러 봅니다.


```bash
curl -s localhost:8080/hello
curl -s localhost:8080/actuator/health
```


```plain text
hello from eks-lab
{"groups":["liveness","readiness"],"status":"UP"}
```


이 두 줄은 같은 이미지를 노트북의 Docker에서 띄워 받은 응답이고, 클러스터에서도 같은 응답이 나와야 합니다. 인사말이 돌아오면 이번 편은 합격입니다. 확인이 끝나면 `port-forward`는 `Ctrl+C`로 닫습니다.


---


## 정리할 때 이미지는 남기고 클러스터만 부숩니다


앱부터 지우고 클러스터를 부숩니다. 이번 편의 Service는 `ClusterIP`라 AWS에 따로 생긴 것이 없지만, 쿠버네티스 쪽부터 지우는 순서를 지금부터 손에 익혀 둡니다. ⑪편에서 로드밸런서가 생기면 이 순서를 지켜야 요금이 남지 않습니다.


```bash
kubectl delete -f k8s/app.yaml
cd 2-cluster && tofu destroy && cd ..
```


`Destroy complete! Resources: 14 destroyed.`가 나오면 ⑤편의 확인 명령 일곱 개를 그대로 돌려 전부 비었는지 봅니다. 지금은 `2-cluster` 밖에 있으니 `tofu state list` 줄만 `tofu -chdir=2-cluster state list`로 바꿔 칩니다.


이번 편의 역할 이름을 `eks-lab`으로 시작하지 않게 지은 것도 이 확인 때문입니다. `eks-lab`으로 시작하게 지었다면 ⑤편의 역할 조회에 걸려 `[]`가 나오지 않았을 것입니다. 그리고 이번에는 하나를 더 묻는데, 이것은 비어 있으면 안 되는 쪽입니다.


```bash
aws ecr describe-images --repository-name eks-lab/app --region ap-northeast-2 \
  --query 'imageDetails[].imageTags' --output text
```


조금 전과 같은 sha가 그대로 나와야 합니다. 클러스터가 사라져도 이미지는 `0-bootstrap`에 남아 있으니, 다음에는 클러스터를 세우고 같은 매니페스트를 적용하기만 하면 됩니다. 이번 편에서 만든 ECR과 역할, `eks-lab` 레포는 ⑭편의 정리 목록에서 함께 지웁니다. 제 첫 앱 배포 때는 apply부터 destroy까지 20분쯤이었고, 비용은 \$0.05 정도였습니다.


---


## 이 방식은 기다리는 시간과 공개 범위로 값을 치릅니다


노트북에서 굽는 것과 비교하면 이 방식은 느립니다. 코드 한 줄을 고쳐도 커밋하고 합친 뒤, 러너가 Gradle 빌드를 처음부터 다시 하는 동안 기다려야 합니다. 대신 이미지마다 어느 커밋에서 구웠는지 기록이 남고, 노트북에만 있던 파일이 이미지에 몰래 섞이는 일이 없습니다.


`IMMUTABLE`에도 대가가 있습니다. 같은 커밋으로 워크플로를 다시 돌리면 그 태그가 이미 있어서 push가 거절됩니다. 이미 있는 이미지이니 무시해도 되지만, 실패 표시가 거슬린다면 push 전에 태그가 있는지 묻는 단계를 더하면 됩니다.


더 조심할 것은 공개 범위입니다. 레포도 Actions 로그도 누구나 볼 수 있습니다. arm64 러너가 무료인 것도 공개 레포이기 때문이라 비공개로 바꾸면 러너의 요금 조건이 달라집니다. 그러니 워크플로에서 무언가를 출력하기 전에 거기에 계정 ID나 비밀값이 섞여 있지 않은지 한 번 더 보시기 바랍니다. 제가 9월에 고친 것 가운데 하나도 실행 요약에 아무 경고 없이 찍히던 한 줄이었습니다.


---


## 정리


| 만든 것                   | 있는 곳                 | 확인할 것                                    |
| ---------------------- | -------------------- | ---------------------------------------- |
| ECR 저장소와 정리 정책         | `0-bootstrap` (남겨 둠) | 클러스터를 부순 뒤에도 sha 태그가 남는가                 |
| GitHub OIDC 공급자와 푸시 역할 | `0-bootstrap` (남겨 둠) | `main`만 받고 브랜치는 거절하는가                    |
| 앱과 워크플로                | 내 공개 레포 `eks-lab`    | arm64 러너, `bootJar`, 계정 ID 가리기           |
| Deployment와 Service    | `kubectl` (매번 지움)    | `Successfully pulled image`, `/hello` 응답 |


이미지를 올리는 일은 결국 신뢰를 잇는 일이었습니다. AWS는 GitHub의 토큰을 믿고, 노드는 자기 역할로 ECR을 믿습니다. 그 사슬 어디에도 오래 사는 비밀번호가 없다는 것이 이번 편에서 만든 구조의 핵심입니다.


다음 편에서는 이 앱이 데이터베이스 주소와 비밀값을 요구하도록 몇 줄을 더한 뒤, 일부러 그 값 없이 띄웁니다. `CrashLoopBackOff`에 빠진 앱의 로그를 읽으면서, 제 서비스가 데이터베이스보다 먼저 엉뚱한 곳에서 죽었던 이야기도 함께 하겠습니다.


---


## 참고

- [Spring Initializr](https://start.spring.io/)
- [GitHub Docs, Configuring OpenID Connect in Amazon Web Services](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [aws-actions/configure-aws-credentials](https://github.com/aws-actions/configure-aws-credentials)
- [aws-actions/amazon-ecr-login](https://github.com/aws-actions/amazon-ecr-login)
- [Amazon ECR, Lifecycle policies](https://docs.aws.amazon.com/AmazonECR/latest/userguide/LifecyclePolicies.html)
- [Amazon EKS, Amazon EKS node IAM role](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
- [Amazon ECR 요금](https://aws.amazon.com/ecr/pricing/)
- ECR 저장 단가(서울, GB당 월 \$0.10)는 2026-11-09에 AWS Pricing API로 조회한 값입니다.
- 제 원본 작업 일지와 전체 코드는 [switch-job-quest](https://github.com/bangddong/switch-job-quest) 레포에 있습니다. 서비스를 닫으면서 보관(archive)해 두었습니다.
> 이 편의 앱은 제 원본이 아니라 이 글을 위해 새로 만든 것입니다. 2026년 11월 9일에 생성기에서 받은 뼈대에 위 파일을 더해 Apple Silicon 노트북의 Docker로 굽고 띄워, 이미지가 arm64이고 `/hello`와 `/actuator/health`가 위와 같이 응답하는 것을 확인했습니다. 일부러 깨 보기 ③의 출력도 그때 노트북에서 받은 것입니다. ECR과 OIDC 역할 코드는 원본에서 이름을 바꾸고 저장소를 하나로 줄였으며, 인증서 지문을 읽는 부분을 덜어 냈습니다. 원본의 관리자 권한 대신 푸시에 필요한 동작만 주도록 새로 썼습니다. 이 코드는 `validate`와 `plan`(5개 추가)까지 확인했습니다. 워크플로와 매니페스트는 이 앱으로 GitHub와 클러스터에서 그대로 돌려 보지는 못했고, ①②의 오류는 7월 27일 제 일지의 기록입니다. 이미지 크기와 받는 시간, 왕복 시간과 비용도 그날 제 원본 서비스로 잰 값이라 이 앱에서는 다를 수 있습니다. 막히는 곳이 있으면 알려 주시기 바랍니다.
>
> 이 글의 그림은 AI가 코드 블록 안 글자로 그렸습니다.
>
>
