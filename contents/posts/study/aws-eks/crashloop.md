---
title: 'CrashLoopBackOff는 고장이 아니라 신호다. EKS 실습기 ⑦, 죽는 앱의 로그를 읽는 법'
date: '2026-11-11'
tags:
  - AWS
  - EKS
series: AWS EKS 실습기
emoji: ''
---
> **AWS 프리티어 \$200으로 EKS 실습하기 ⑦** · 💰 클러스터를 켜는 한 시간 안쪽에 약 **\$0.1**

`kubectl get pods`를 쳤는데 STATUS 칸에 `CrashLoopBackOff`가 떠 있고, 다시 칠 때마다 RESTARTS 숫자가 하나씩 올라가는 화면을 보신 적이 있으신가요? 이름이 길고 낯설어서 무언가 큰 고장처럼 보입니다. 그래서 이 단어를 그대로 검색창에 넣게 되는데, 나오는 답은 대개 너무 일반적이라 내 앱에는 잘 맞지 않습니다.


이번 편에서는 ⑥편의 작은 앱이 데이터베이스 주소와 비밀값을 요구하도록 몇 줄을 더합니다. 그리고 일부러 그 값 없이 띄워 `CrashLoopBackOff`를 직접 만듭니다. 그다음 로그를 어디서 어떻게 꺼내 읽어야 진짜 원인에 닿는지를 순서대로 따라갑니다.

> `CrashLoopBackOff`는 원인이 아니라, 원인을 읽으라는 신호다.

---


## CrashLoopBackOff는 고장의 이름이 아니라 기다리는 중이라는 표시입니다


Deployment로 띄운 파드는 컨테이너가 죽으면 다시 띄웁니다. ⑥편에서 Deployment를 "죽으면 다시 띄워 달라는 선언"이라고 했던 바로 그 동작입니다. 문제는 앱이 뜨자마자 또 죽는 경우인데, 이때 쿠버네티스가 쉬지 않고 다시 띄우면 노드가 재시작만 하다가 지칩니다.


그래서 kubelet은 재시작 사이에 기다리는 시간을 둡니다. 쿠버네티스 문서에 따르면 10초에서 시작해 20초, 40초로 두 배씩 늘고, 5분에서 멈춥니다. 그리고 컨테이너가 10분 동안 문제없이 돌면 이 시계를 처음으로 되돌립니다.


`CrashLoopBackOff`는 바로 이 기다리는 동안 보이는 표시입니다. 다시 말해 "앱이 계속 죽어서 다음 재시작을 기다리는 중"이라는 뜻일 뿐, 왜 죽는지는 하나도 말해 주지 않습니다. 원인은 죽기 직전의 컨테이너가 남긴 로그에 있고, 이번 편은 그 로그를 꺼내 읽는 법이 전부입니다.


---


## 앱에 데이터베이스와 비밀값 자리를 만듭니다


⑥편의 앱은 인사말 하나만 돌려줬으니 바깥에서 받을 값이 없었습니다. 실제 서비스라면 사정이 다른데, 데이터베이스 주소와 계정이 필요하고, 로그인 토큰을 서명할 키도 필요합니다. 그 자리를 작은 앱에도 만들어 봅니다. 먼저 `app/build.gradle.kts`의 `dependencies`에 두 줄을 더합니다.


```kotlin
// app/build.gradle.kts 의 dependencies 블록에 더합니다
implementation("org.springframework.boot:spring-boot-starter-data-jpa")
runtimeOnly("org.postgresql:postgresql")
```


데이터베이스에 닿는 길은 `application.yml`에 적습니다. 주소와 계정은 코드에 박지 않고 `${...}` 자리로 비워 두어, 실행할 때 환경변수로 받습니다. 같은 이미지를 어디에 띄우든 값만 바꿔 넣으면 되기 때문입니다.


```yaml
# app/src/main/resources/application.yml
server:
  port: 8080

spring:
  datasource:
    url: jdbc:postgresql://${DB_HOST}:5432/${DB_NAME}
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}

management:
  endpoints:
    web:
      exposure:
        include: health
```


토큰을 서명할 키는 설정 파일이 아니라 코드에서 바로 받게 합니다. 실제 서비스의 코드에도 이렇게 클래스 안에서 값을 받는 곳이 흔한데, 이 차이가 뒤에서 함정이 됩니다.


```java
// app/src/main/java/lab/eks/app/TokenSigner.java
package lab.eks.app;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class TokenSigner {

    private final String secret;

    public TokenSigner(@Value("${TOKEN_SECRET}") String secret) {
        this.secret = secret;
    }
}
```


이 클래스는 아직 키를 받아 두기만 하고 쓰지는 않습니다. 앱이 뜰 때 이 값이 없으면 어떻게 되는지를 보려는 자리이기 때문입니다. 세 파일을 고쳤으면 `main`에 올립니다. `app` 폴더가 바뀌었으니 ⑥편의 워크플로가 새 이미지를 굽기 시작합니다.


```bash
git add app
git commit -m "app: 데이터베이스와 토큰 키 자리"
git push
sleep 5 && gh run watch
```


`gh run watch`가 초록으로 끝나면 ECR에 sha 태그가 하나 늘어 있습니다. ⑥편의 이미지는 그대로 남아 있으니 저장소에는 태그가 둘입니다. 여기까지는 클러스터가 없어도 되니 요금이 붙지 않습니다.


---


## 값 없이 띄우면 앱은 몇 초 만에 죽고 다시 일어납니다


여기서부터 돈이 나갑니다. ⑥편과 같은 순서로 클러스터를 세우고, ⑥편의 매니페스트를 고치지 않은 채 그대로 올립니다. 이미지 태그는 ⑥편처럼 ECR에서 가장 최근에 올라간 것을 고르니, 방금 구운 이미지가 올라갑니다.


```bash
cd 2-cluster
tofu plan -out=cluster.tfplan
tofu apply cluster.tfplan
aws eks update-kubeconfig --name eks-lab --region ap-northeast-2
kubectl get nodes
cd ..

REPO=$(tofu -chdir=0-bootstrap output -raw ecr_repository_url)
SHA=$(aws ecr describe-images --repository-name eks-lab/app --region ap-northeast-2 \
  --query 'sort_by(imageDetails,&imagePushedAt)[-1].imageTags[0]' --output text)
sed "s|IMAGE_PLACEHOLDER|$REPO:$SHA|" k8s/app.yaml | kubectl apply -f -
```


이번에는 파드를 한 번 보고 끝내지 않고, `-w`를 붙여 상태가 바뀔 때마다 한 줄씩 찍게 합니다. 1분쯤 지켜본 뒤 `Ctrl+C`로 멈춥니다. 한 번씩 찍어 보는 것보다 죽고 다시 뜨는 리듬이 훨씬 잘 보입니다.


```bash
kubectl get pods -l app=app -w
```


```plain text
NAME                   READY   STATUS             RESTARTS      AGE
app-5f88586699-ddnxr   0/1     ContainerCreating  0             0s
app-5f88586699-ddnxr   1/1     Running            0             1s
app-5f88586699-ddnxr   0/1     Error              0             6s
app-5f88586699-ddnxr   1/1     Running            1 (1s ago)    6s
app-5f88586699-ddnxr   0/1     Error              1 (6s ago)    11s
app-5f88586699-ddnxr   0/1     CrashLoopBackOff   1 (15s ago)   25s
app-5f88586699-ddnxr   1/1     Running            2 (16s ago)   26s
app-5f88586699-ddnxr   0/1     Error              2 (20s ago)   30s
app-5f88586699-ddnxr   0/1     CrashLoopBackOff   2 (25s ago)   55s
app-5f88586699-ddnxr   1/1     Running            3 (26s ago)   56s
```


이 출력은 노트북의 연습용 쿠버네티스에서 받은 것이고, 앞서 지운 파드의 줄은 덜어 냈습니다. 파드 이름과 초는 다르게 나오지만 흐름은 같습니다. 앱은 뜬 지 5초쯤 만에 `Error`로 죽고, 쉬는 시간은 갈수록 길어집니다. 실제 간격은 문서의 10초, 20초와 딱 맞지 않고 조금씩 어긋납니다.


한 가지 눈여겨볼 것은 `Running`과 `1/1`이 잠깐씩 보인다는 점입니다. 매니페스트에 앱이 준비됐는지 묻는 장치를 아직 달지 않아서, 쿠버네티스는 프로세스가 살아 있기만 하면 준비된 것으로 칩니다. 그러니 `Running`을 한 번 봤다고 안심하면 안 되고, RESTARTS 숫자가 멈춰 있는지를 함께 봐야 합니다.


---


## 로그는 지금 것이 아니라 직전에 죽은 것을 읽습니다


그러면 왜 죽었을까요? 먼저 `describe`로 파드가 기억하는 마지막 죽음을 봅니다. 출력이 길지만 `Containers:` 아래의 몇 줄만 보면 됩니다.


```bash
kubectl describe pod -l app=app
```


```plain text
State:          Waiting
      Reason:       CrashLoopBackOff
    Last State:     Terminated
      Reason:       Error
      Exit Code:    1
    Restart Count:  5
```


`State`는 지금 상태이고, `Last State`는 바로 전에 죽은 컨테이너의 기록입니다. 지금은 기다리는 중이고, 직전 컨테이너는 종료 코드 1로 끝났다는 뜻입니다. 1은 앱이 스스로 오류를 내고 나갔다는 표시라서, 이제 앱의 로그를 볼 차례입니다. `Restart Count`는 기다린 시간만큼 다르게 나옵니다.


여기서 흔히 두 번 헛걸음을 합니다. 첫째, 그냥 `kubectl logs`를 치면 지금 막 다시 뜬 컨테이너의 로그가 나옵니다. 운이 나쁘면 아직 아무것도 찍지 않았거나 죽기 전의 앞부분만 보입니다. 그래서 직전에 죽은 컨테이너의 로그를 달라고 `--previous`를 붙입니다.


둘째는 파드 이름 대신 `-l app=app`처럼 라벨로 고를 때 생깁니다. `kubectl logs`는 라벨로 고르면 기본으로 마지막 10줄만 보여 주는데, 그 열 줄은 대개 스택의 끝부분이라 원인이 들어 있지 않습니다. 줄 수를 세어 보면 차이가 바로 보입니다.


```bash
kubectl logs -l app=app --previous | wc -l       # 10
kubectl logs deploy/app --previous | wc -l       # 163
```


`deploy/app`처럼 Deployment 이름으로 부르면 그 아래 파드 하나를 골라 전부 보여 줍니다. 라벨로 꼭 골라야 한다면 `--tail=-1`을 붙이면 됩니다. 이제 163줄을 받았으니 읽을 차례입니다.


---


## 마지막 Caused by가 늘 원인은 아닙니다


자바 앱의 긴 로그는 보통 맨 아래 `Caused by`부터 읽으라고 배웁니다. 예외가 예외를 감싸며 올라오니, 가장 안쪽의 것이 뿌리라는 이야기입니다. 그 말대로 맨 아래를 보면 이렇게 적혀 있습니다.


```plain text
Caused by: org.hibernate.HibernateException: Unable to determine Dialect without JDBC metadata
(please set 'jakarta.persistence.jdbc.url' for common cases or 'hibernate.dialect' ...)
```


"방언을 정할 수 없으니 `hibernate.dialect`를 설정하라"는 말입니다. 이 문구로 검색하면 `hibernate.dialect`를 적어 넣으라는 답이 많이 나옵니다. 하지만 그렇게 하면 이 메시지만 사라질 뿐, 데이터베이스에 닿지 못하는 진짜 문제는 그대로 남습니다.


그래서 맨 아래 한 줄만 보지 말고, 로그 전체에서 `Caused by`가 몇 번 나오는지부터 셉니다. 스택의 나머지 줄은 걸러 내고 원인 줄만 모아 보는 것입니다. 이 앱에서는 네 줄이 나옵니다.


```bash
kubectl logs deploy/app --previous | grep "Caused by"
```


```plain text
Caused by: org.postgresql.util.PSQLException: The connection attempt failed.
Caused by: java.net.UnknownHostException: ${DB_HOST}
Caused by: org.hibernate.service.spi.ServiceException: Unable to create requested service ...
Caused by: org.hibernate.HibernateException: Unable to determine Dialect without JDBC metadata ...
```


예외 사슬이 하나가 아니라 둘입니다. 앞의 두 줄은 Hibernate가 데이터베이스에 접속해 보다가 실패한 것이고, 경고(WARN)로 찍힌 뒤 넘어갔습니다. 뒤의 두 줄은 그 실패 때문에 다음 단계가 무너진 결과입니다. 맨 아래 메시지는 이 두 번째 사슬의 끝이라, 결과는 말해도 원인은 말하지 않습니다.


두 사슬을 나란히 놓으면 이렇습니다. 화살표가 붙은 두 줄 가운데 맨 아래 줄은 눈에 먼저 띄는 쪽이고, 원인은 위쪽 사슬의 끝입니다.


```plain text
WARN   접속을 시도하다 실패하고, 경고만 남긴 채 넘어간다
  JDBCConnectionException
    └ Caused by  PSQLException: The connection attempt failed.
        └ Caused by  UnknownHostException: ${DB_HOST}          ← 원인

ERROR  그 실패 때문에 다음 단계가 무너지고 앱이 멈춘다
  BeanCreationException: entityManagerFactory
    └ Caused by  ServiceException: Unable to create requested service
        └ Caused by  HibernateException: Unable to determine Dialect  ← 맨 아래 줄
```


진짜 단서는 두 번째 줄입니다. `UnknownHostException: ${DB_HOST}`, 그러니까 `${DB_HOST}`라는 이름의 호스트를 찾지 못했다는 말입니다. 환경변수가 없으니 Spring이 자리 표시를 글자 그대로 주소에 넣었고, 드라이버는 그 글자를 호스트 이름으로 찾아 나선 것입니다. 로그에서 `${`가 보이면 값이 들어가지 않았다는 뜻으로 읽으면 됩니다.


---


## 제 서비스는 데이터베이스에 닿기도 전에 로그 설정에서 죽었습니다


이 작은 앱은 데이터베이스에서 먼저 죽었지만, 제가 7월 27일에 처음 올린 서비스는 사정이 달랐습니다. 그날 저는 운영 데이터베이스에 학습용 클러스터를 잇지 않기로 하고, 데이터베이스 없이 띄웠습니다. 그러니 데이터베이스 연결 오류로 죽을 것이라 예상했습니다. 실제로는 세 번 죽었고, 앞의 두 번은 엉뚱한 곳이었습니다.


첫 번째는 로그를 외부로 보내는 설정이었습니다. 운영 환경 설정은 로그 서비스로 보내는 장치를 무조건 켜고 있었고, 그 주소가 비어 있자 `URI with undefined scheme`을 내며 로깅을 준비하는 단계에서 앱이 멈췄습니다. 데이터베이스에 닿기 한참 전이었습니다.


그다음으로 드러난 것은 `Could not resolve placeholder 'JWT_SECRET'`이었습니다. 토큰 서명 키가 없어서 그 키를 받는 객체를 만들지 못한 것입니다. 이것까지 넘어서고 나서야 세 번째로, 처음 예상했던 데이터베이스 오류에 닿았습니다.


돌아보면 이 서비스는 그전까지 다른 플랫폼에서 잘 돌던 앱이었습니다. 그 플랫폼에 등록해 둔 비밀값들이 앱의 숨은 의존을 전부 가려 주고 있었던 셈입니다. 그러다 플랫폼을 옮기자 가려졌던 것이 앱이 뜨는 순서대로 하나씩 드러났습니다.


---


## 하나씩 고치지 말고 필요한 값을 먼저 셉니다


죽을 때마다 하나씩 채우는 방식은 두더지 잡기와 같습니다. 클러스터가 켜진 채로 재시작을 기다리는 시간도 길어집니다. 그래서 그날 저는 몇 번 죽고 난 뒤 방식을 바꿔, 설정 파일에서 `${...}` 자리를 전부 찾아 필요한 값을 한 번에 셌습니다.


이 앱에서는 몇 개가 나올까요? 먼저 그날의 저처럼 설정 파일만 뒤져 봅니다. 대문자와 밑줄로 된 `${...}` 자리를 모두 뽑아 겹치는 것을 지우는 한 줄입니다.


```bash
grep -ohE '\$\{[A-Z_]+\}' app/src/main/resources/application.yml | sort -u
```


```plain text
${DB_HOST}
${DB_NAME}
${DB_PASSWORD}
${DB_USERNAME}
```


네 개가 나옵니다. 그날 저는 이렇게 센 일곱 개를 필수 값이라고 계획에 적었습니다. 로그 설정이 따로 요구하는 세 개는 그날 직접 죽어 보고도 그 목록 밖에 두었습니다. 다음 날 계획을 점검하다가 필수 값이 열 개였다는 것, 그리고 제가 권하던 검색이 바로 그 세 개를 놓친다는 것을 알았습니다. 로그 설정 파일은 값을 `${...}`가 아니라 다른 형식으로 불렀기 때문입니다.


### 일부러 깨 보기: 설정 파일만 뒤지면 하나를 놓칩니다


지금 찾은 네 값만 넣고 띄워 보면, 이 앱도 그날 제 서비스처럼 다른 자리에서 다시 죽습니다. 값을 넣으려면 데이터베이스가 있어야 하니 연습용 PostgreSQL을 클러스터 안에 잠깐 띄웁니다. 데이터베이스를 제대로 들이는 것은 ⑨편의 일이라, 여기서는 파드를 지우면 데이터도 함께 사라지는 임시 데이터베이스로 충분합니다.


값은 쿠버네티스의 Secret에 넣습니다. 비밀번호는 손으로 짓지 않고 무작위로 만들어 변수에만 담아 둡니다. 화면에 찍지 않으니 터미널 기록에도 값이 남지 않습니다.


```bash
DB_PASSWORD=$(openssl rand -hex 16)
kubectl create secret generic app-env \
  --from-literal=DB_HOST=db \
  --from-literal=DB_NAME=app \
  --from-literal=DB_USERNAME=app \
  --from-literal=DB_PASSWORD="$DB_PASSWORD"
```


`secret/app-env created`가 나오면 됩니다. `DB_HOST`의 `db`는 곧 만들 데이터베이스 Service의 이름이고, 클러스터 안에서는 이 이름이 곧 주소입니다. 임시 데이터베이스는 같은 Secret에서 계정과 비밀번호를 받아 그 값으로 처음 초기화됩니다.


```yaml
# k8s/db-temp.yaml
apiVersion: v1
kind: Pod
metadata:
  name: db
  labels:
    app: db
spec:
  containers:
    - name: postgres
      image: postgres:17-alpine
      env:
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef: { name: app-env, key: DB_NAME }
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef: { name: app-env, key: DB_USERNAME }
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef: { name: app-env, key: DB_PASSWORD }
      ports:
        - containerPort: 5432
      resources:
        requests:
          cpu: 100m
          memory: 128Mi
        limits:
          memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: db
spec:
  selector:
    app: db
  ports:
    - port: 5432
```


앱 쪽에는 이 Secret을 통째로 환경변수로 받는 세 줄을 더합니다. `k8s/app.yaml`의 컨테이너에서 `ports:` 바로 위에 넣습니다. 키를 하나씩 적지 않으니, 나중에 Secret에 키를 더해도 매니페스트는 그대로 둡니다.


```yaml
envFrom:
            - secretRef:
                name: app-env # 이 Secret 의 키가 전부 환경변수가 됩니다
```


데이터베이스가 먼저 떠야 하니 `kubectl wait`로 기다린 뒤 앱을 다시 적용합니다. `REPO`와 `SHA`는 앞에서 만든 변수를 그대로 쓰니, 터미널을 새로 열었다면 그 두 줄을 먼저 다시 칩니다.


```bash
kubectl apply -f k8s/db-temp.yaml
kubectl wait --for=condition=Ready pod/db --timeout=180s
kubectl logs db | grep "init process complete"
sed "s|IMAGE_PLACEHOLDER|$REPO:$SHA|" k8s/app.yaml | kubectl apply -f -
```


임시 데이터베이스에는 준비됐는지 묻는 장치가 없어서, 파드가 Ready여도 초기화 중일 수 있습니다. 그래서 로그에 `PostgreSQL init process complete`가 보인 뒤에 앱을 적용합니다. 비어 있으면 몇 초 뒤 다시 칩니다. `ready to accept connections`는 초기화 중에도 한 번 찍혀서 기준으로 삼기 어렵습니다.


40초쯤 기다리면 앱이 두어 번 죽은 뒤입니다. 그때 다시 `Caused by`를 셉니다. 매니페스트가 바뀌어 파드가 새로 만들어졌으니, 이름 대신 `deploy/app`으로 부르는 습관이 여기서 쓸모가 있습니다.


```bash
kubectl get pods
kubectl logs deploy/app --previous | grep "Caused by"
```


`kubectl get pods`에서 `db`는 `1/1 Running`이고, `app`은 `Error`나 `CrashLoopBackOff`에 RESTARTS가 1이나 2쯤이면 됩니다. 그리고 `Caused by`는 이번에는 한 줄만 나옵니다.


```plain text
Caused by: org.springframework.util.PlaceholderResolutionException: Could not resolve placeholder 'TOKEN_SECRET' in value "${TOKEN_SECRET}"
```


데이터베이스는 통과했고, 이번에는 토큰 키에서 죽었습니다. 설정 파일이 아니라 코드에서 받은 값이라 `application.yml`만 뒤진 검색에는 걸리지 않았던 것입니다. 그날 제가 놓친 세 개와 모양은 다르지만, 검색한 곳 밖에 있었다는 점은 같습니다. 그러니 검색은 설정 파일이 아니라 소스 전체에 겁니다.


```bash
grep -rohE '\$\{[A-Z_]+\}' app/src/main | sort -u
```


이번에는 `${TOKEN_SECRET}`까지 다섯 개가 나옵니다. 다만 이것도 `${...}` 형식만 찾는다는 한계는 그대로입니다. 그날의 로그 설정처럼 다른 형식으로 값을 부르는 곳이 있으면 여전히 놓치니, 검색 결과는 출발점으로만 쓰고 마지막 확인은 실제로 띄워서 합니다.


---


## 다섯 값이 다 들어가면 같은 파드가 스스로 일어납니다


그러면 빠진 키를 넣은 뒤에는 파드를 다시 만들어야 할까요? 일단 키부터 Secret에 더합니다. 이 키도 무작위로 만들어 화면에 찍지 않고 바로 넣고, 파드가 어떻게 되는지 지켜봅니다.


```bash
kubectl patch secret app-env -p "{\"stringData\":{\"TOKEN_SECRET\":\"$(openssl rand -hex 32)\"}}"
kubectl get pods -l app=app -w
```


흔히 Secret을 바꾸면 파드를 다시 만들어야 한다고 합니다. 이미 떠 있는 컨테이너는 시작할 때 받은 환경변수를 계속 쓰기 때문인데, 재시작을 기다리던 파드는 이야기가 다릅니다. 다음 재시작에서 컨테이너를 새로 만들 때 바뀐 Secret을 다시 읽기 때문입니다.


실제로 연습용 클러스터에서 해 보니, RESTARTS가 3에서 멈추고 같은 파드가 `Running`으로 남았습니다. 다만 기다리는 시간이 길어진 뒤라면 몇 분을 더 기다려야 하니, 바로 보고 싶으면 `kubectl rollout restart deployment/app`으로 새 파드를 띄우면 됩니다. 이제 ⑥편처럼 포트를 이어 응답을 봅니다.


```bash
kubectl port-forward svc/app 8080:8080
```


다른 터미널에서 두 주소를 부릅니다. 첫 줄은 ⑥편과 같은 인사말이고, 둘째 줄이 이번 편에서 달라진 곳입니다.


```bash
curl -s localhost:8080/hello
curl -s localhost:8080/actuator/health
```


```plain text
hello from eks-lab
{"groups":["liveness","readiness"],"status":"UP"}
```


`/actuator/health`가 `UP`이라는 것은 이번에는 데이터베이스까지 확인한 결과입니다. ⑥편의 `UP`은 앱이 살아 있다는 뜻뿐이었지만, 지금은 데이터베이스 연결도 함께 묻습니다. 로그에 `Started AppApplication`이 한 번 찍히고 RESTARTS가 더 오르지 않으면 이번 편은 합격입니다.


---


## 종료 코드가 1이 아니면 앱 로그 말고 다른 곳을 봅니다


이번 편의 앱은 종료 코드 1로 죽었습니다. 앱이 스스로 오류를 내고 나간 경우라서 로그에 답이 있었습니다. 하지만 `Last State`의 종료 코드가 다르면 앱의 로그에 아무 단서가 없을 수 있는데, 아래 두 경우는 제가 이 실습에서 겪은 것이 아니라 알아 둘 만한 것으로 적습니다.


종료 코드가 137이고 `Reason`이 `OOMKilled`라면, 앱이 매니페스트에 적은 메모리 상한인 512Mi를 넘겨서 커널이 죽인 것입니다. 앱은 오류를 남길 틈도 없이 죽으니 로그가 갑자기 끊깁니다. 이때는 앱 설정이 아니라 상한과 JVM의 메모리 설정을 봅니다.


로그에 `exec format error` 한 줄만 있다면 ⑥편에서 본 아키텍처 문제입니다. arm64 노드에 x86용 이미지가 올라온 것이라, 고칠 곳은 앱이 아니라 이미지를 굽는 러너입니다. 이 경우 JVM은 아예 시작하지 못하니 자바 로그도 한 줄 없습니다.


---


## 정리할 때 임시 데이터베이스와 Secret도 함께 지웁니다


이번 편에서 손으로 만든 것은 매니페스트 둘과 Secret 하나입니다. 셋 다 OpenTofu의 state 밖에 있으니 `tofu destroy` 전에 지웁니다. 클러스터를 부수면 함께 사라지기는 하지만, 쿠버네티스 쪽부터 지우는 순서를 ⑥편에 이어 손에 익혀 둡니다.


```bash
kubectl delete -f k8s/db-temp.yaml
kubectl delete -f k8s/app.yaml
kubectl delete secret app-env
cd 2-cluster && tofu destroy && cd ..
```


`Destroy complete! Resources: 14 destroyed.`가 나오면 ⑥편처럼 ⑤편의 확인 명령 일곱 개를 돌립니다. `tofu state list` 줄만 `tofu -chdir=2-cluster state list`로 바꿉니다. ECR에는 이번 편의 이미지가 하나 더 남아 있어야 합니다.


`k8s/db-temp.yaml`과 고친 `k8s/app.yaml`은 커밋해 둡니다. 파일 안에는 비밀값이 없고 Secret의 이름만 있으니 공개 레포에 올려도 괜찮습니다. 비밀번호와 토큰 키는 클러스터와 함께 사라졌고, 다음에 띄울 때 새로 만들면 됩니다.


---


## 이 방식은 비밀값을 손으로 다루는 값을 치릅니다


이번 편의 Secret은 그 자리에서 손으로 만들었습니다. 쿠버네티스의 Secret은 암호화가 아니라 base64로 적어 둔 것이라서, 읽을 권한이 있는 사람은 바로 풀어 봅니다. 지금 클러스터는 실습하는 한 사람만 관리자 권한을 쓰지만, 사람이 늘면 이 권한부터 따져야 합니다.


```bash
kubectl get secret app-env -o jsonpath='{.data.DB_NAME}' | base64 -d   # app
```


게다가 값의 원본이 어디에도 없습니다. 클러스터를 부수면 사라지고, 다시 세우면 새로 만들어야 합니다. 이번에는 무작위 값을 새로 만들면 그만이었지만, 실제 서비스의 비밀값은 그렇게 버릴 수 없습니다.


임시 데이터베이스도 같은 문제를 안고 있습니다. 파드가 지워지면 데이터가 사라지고, 노드가 바뀌어도 사라집니다. 그리고 검색으로 필요한 값을 세는 방법은 형식이 다른 곳을 놓칩니다. 그러니 마지막 판단은 언제나 실제로 띄운 로그가 합니다.


---


## 정리


| 볼 것           | 명령                                        | 알려 주는 것             |
| ------------- | ----------------------------------------- | ------------------- |
| 지금 상태와 재시작 횟수 | `kubectl get pods -w`                     | 죽고 있는지, 기다리는 중인지    |
| 직전 죽음의 기록     | `kubectl describe pod`                    | `Last State`의 종료 코드 |
| 직전 컨테이너의 로그   | `kubectl logs deploy/app --previous`      | 앱이 남긴 오류 전체         |
| 예외 사슬 전부      | `... | grep "Caused by"`                  | 결과가 아닌 원인이 어느 줄인지   |
| 필요한 값 목록      | `grep -rohE '\$\{[A-Z_]+\}' app/src/main` | 띄우기 전에 채울 값         |


`CrashLoopBackOff`는 무엇이 고장 났는지 말해 주지 않습니다. 쿠버네티스는 다시 띄우며 기다릴 뿐이고, 원인은 직전에 죽은 컨테이너의 로그 안에서 사람이 읽어 내야 합니다. 그리고 그 로그에서도 맨 아래 한 줄이 아니라 사슬 전체를 봐야 합니다.


다음 편에서는 이번에 손으로 만든 Secret을 AWS Secrets Manager에서 받아 오게 바꿉니다. 비밀값의 원본을 클러스터 밖에 두고, 파드가 자기 신원으로 그 값을 받아 오는 길을 만듭니다. ⑤편에서 만들어 두고 쓰지 않았던 OIDC 공급자가 거기서 쓰입니다.


---


## 참고

- [Kubernetes Docs, Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Kubernetes Docs, Debug Running Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/)
- [kubectl logs 레퍼런스](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_logs/)
- [Kubernetes Docs, Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [postgres 공식 이미지](https://hub.docker.com/_/postgres)
- 제 원본 작업 일지와 전체 코드는 [switch-job-quest](https://github.com/bangddong/switch-job-quest) 레포에 있습니다. 서비스를 닫으면서 보관(archive)해 두었습니다.
> 이 편의 앱 변경과 매니페스트는 이 글을 위해 새로 쓴 것입니다. 2026년 11월 10일에 ⑥편의 앱에 위 변경을 더해 Apple Silicon 노트북의 Docker로 구웠습니다. 그리고 노트북의 연습용 쿠버네티스(kind, v1.37)에서 세 단계를 그대로 재현했습니다. 값 없이 띄운 `CrashLoopBackOff`, 네 값만 넣었을 때의 `TOKEN_SECRET` 오류, 다섯 값을 넣은 뒤의 응답입니다. 위의 출력은 전부 그때 받은 것입니다. EKS에서는 이 앱으로 돌려 보지 못했습니다. 그래서 이벤트 문구나 시간은 조금 다를 수 있고, 노드가 Docker Hub에서 `postgres` 이미지를 받는 것도 EKS에서는 확인하지 못했습니다. 비용은 ⑤편의 시간당 \$0.13쯤으로 한 시간 안쪽을 어림한 값입니다. 제 서비스가 세 번 죽은 이야기와 일곱 개가 열 개였던 이야기는 7월 27일과 28일 제 일지의 기록입니다. 막히는 곳이 있으면 알려 주시기 바랍니다.
>
> 이 글의 그림은 AI가 코드 블록 안 글자로 그렸습니다.
>
>
