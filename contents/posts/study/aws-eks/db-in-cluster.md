---
title: '파드는 바뀌어도 디스크는 남아야 한다. EKS 실습기 ⑨, 데이터베이스를 클러스터 안으로'
date: '2026-11-14'
tags:
  - AWS
  - EKS
series: AWS EKS 실습기
emoji: ''
---
> **AWS 프리티어 \$200으로 EKS 실습하기 ⑨** · 💰 클러스터를 켜는 한 시간 안쪽에 약 **\$0.1**, 디스크는 켜 둔 동안 1GiB에 월 \$0.09 꼴이라 거의 \$0

데이터베이스에 넣은 데이터가 파드를 한 번 지웠다고 통째로 사라진 적이 있으신가요? ⑦편과 ⑧편의 임시 데이터베이스가 바로 그렇습니다. 이 글을 쓰며 `memo`라는 표를 만들고 한 줄을 넣은 뒤 파드를 지웠다가 다시 띄웠더니 표가 아예 없다는 답이 돌아왔습니다.


```plain text
ERROR:  relation "memo" does not exist
```


임시 데이터베이스는 데이터를 컨테이너 안에 적기 때문입니다. 컨테이너가 사라지면 그 안의 파일도 함께 사라집니다. 이번 편에서는 데이터를 컨테이너 밖, AWS의 EBS 디스크에 적게 바꿉니다. 그리고 그 디스크는 사람이 미리 만들어 두지 않고 쿠버네티스가 필요할 때 직접 만들게 합니다.

> 파드는 몇 번이고 바뀌어도 되지만, 디스크는 바뀌지 않아야 한다.

---


## 디스크를 요청하는 쪽과 만드는 쪽은 서로 다른 객체입니다


쿠버네티스에서 디스크를 다룰 때는 이름이 비슷한 객체 셋이 나옵니다. PVC(PersistentVolumeClaim)는 "1GiB짜리 디스크를 주세요"라는 요청서입니다. PV(PersistentVolume)는 그 요청에 실제로 배정된 디스크입니다. 요청이 들어왔을 때 어떤 디스크를 어떻게 만들지는 StorageClass라는 규칙이 정합니다.


그런데 쿠버네티스는 EBS가 무엇인지 모릅니다. 규칙에 따라 실제로 AWS에 디스크를 만들어 달라고 요청하는 일은 EBS CSI 드라이버가 맡습니다. CSI는 쿠버네티스가 저장소 업체의 코드를 본체에서 떼어 내고 정해 둔 표준 접점입니다. 그래서 EBS든 다른 클라우드의 디스크든 같은 방식으로 붙습니다.


순서를 그림으로 먼저 보겠습니다. 둘째 칸과 셋째 칸의 순서가 뒤집히지 않는다는 점을 눈여겨보시기 바랍니다. 그 순서를 정하는 설정은 뒤의 StorageClass에서 나옵니다.


![PVC가 기다리다가 파드가 노드를 고른 뒤에 그 AZ에 디스크가 생기고, 파드가 바뀌어도 같은 디스크가 붙습니다](https://dhbang.co.kr/images/aws-eks/anim07-pvc-binding.svg)


이 드라이버는 AWS에서 값을 읽기만 하던 ⑧편의 ESO보다 하는 일이 많습니다. 디스크를 만들고 노드에 붙이고 지우기까지 합니다. 그래서 권한이 없으면 디스크를 만들 수 없습니다. 설치하기 전에 AWS에 물어보면 이 애드온이 권한을 요구한다고 미리 알려 줍니다.


```bash
aws eks describe-addon-versions --addon-name aws-ebs-csi-driver --kubernetes-version 1.36 \
  --region ap-northeast-2 --query 'addons[0].addonVersions[0].[addonVersion,requiresIamPermissions]' \
  --output text
```


```plain text
v1.68.0-eksbuild.1	True
```


---


## 드라이버도 ⑧편과 같은 방식으로 역할을 빌립니다


역할을 만드는 방법은 ⑧편과 같습니다. 신뢰 정책의 `sub`만 드라이버의 서비스 계정인 `kube-system:ebs-csi-controller-sa`로 바꿉니다. 권한 정책은 직접 쓰지 않고 AWS가 관리하는 `AmazonEBSCSIDriverPolicy`를 붙입니다.


왜 ⑧편처럼 대상을 하나로 좁히지 않을까요? ⑧편의 시크릿은 이름이 정해져 있었지만 드라이버가 만들 디스크는 아직 존재하지 않아서 ARN을 미리 적을 수 없기 때문입니다. 그래서 이 관리형 정책은 리소스 대신 태그로 경계를 긋습니다. 드라이버가 만든 디스크에는 `ebs.csi.aws.com/cluster` 태그가 붙습니다. 지우는 권한은 그 태그가 붙은 디스크에만 듣습니다.


```hcl
# ebs-csi.tf
data "aws_iam_policy_document" "ebs_csi_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.oidc.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:sub"
      values   = ["system:serviceaccount:kube-system:ebs-csi-controller-sa"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ebs_csi" {
  name               = "${var.cluster_name}-ebs-csi"
  assume_role_policy = data.aws_iam_policy_document.ebs_csi_trust.json
}

# 아직 없는 디스크를 만들고 지우는 권한이라, AWS 가 관리하는 정책을 그대로 붙입니다
resource "aws_iam_role_policy_attachment" "ebs_csi" {
  role       = aws_iam_role.ebs_csi.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
}

resource "aws_eks_addon" "ebs_csi" {
  cluster_name             = aws_eks_cluster.main.name
  addon_name               = "aws-ebs-csi-driver"
  service_account_role_arn = aws_iam_role.ebs_csi.arn
  # 노드가 한 대라 컨트롤러 두 개는 함께 죽습니다. 하나로 줄여 파드 자리를 아낍니다
  configuration_values = jsonencode({ controller = { replicaCount = 1 } })
  depends_on           = [aws_eks_node_group.main, aws_iam_role_policy_attachment.ebs_csi]
}
```


`local.oidc_host`는 ⑧편의 `irsa-eso.tf`에서 만든 것을 그대로 씁니다. 마지막 블록의 `replicaCount = 1`에는 사연이 있는데 다음 절에서 계산으로 보겠습니다.


---


## 설치하기 전에 노드에 남은 파드 자리를 섭니다


⑤편에서 t4g.small 한 대에는 파드가 11개까지만 뜬다고 했습니다. 파드마다 VPC의 IP를 하나씩 주는데 이 인스턴스는 네트워크 카드 3장에 카드당 IP가 4개입니다. 그래서 `3 × (4 - 1) + 2 = 11`이 상한이 됩니다. 그러면 지금 노드에는 몇 자리가 남아 있을까요?


⑧편에서는 시스템 파드 넷, ESO 셋, 데이터베이스와 앱까지 아홉 자리를 썼습니다. 여기에 EBS CSI 드라이버를 기본값으로 더하면 컨트롤러 둘과 노드마다 하나씩 도는 파드 하나가 늘어, 이번 편의 것을 다 올렸을 때 모두 12개가 됩니다. 상한을 하나 넘으니 어느 파드 하나는 자리를 못 잡고 `Pending`에 갇힙니다.


기본값이 정말 2인지는 설치하기 전에 확인할 수 있습니다. `tofu plan`은 자기 코드만 보기 때문에 이런 AWS 쪽 기본값은 미리 알려 주지 않습니다.


```bash
aws eks describe-addon-configuration --addon-name aws-ebs-csi-driver \
  --addon-version v1.68.0-eksbuild.1 --region ap-northeast-2 \
  --query configurationSchema --output text | grep -o '"replicaCount"[^}]*}'
```


```plain text
"replicaCount":{"default":2,"description":"Number of replicas in the controller Deployment","minimum":1,"type":"integer"}
```


노드가 한 대뿐이라 컨트롤러 두 개는 같은 노드에 떠서 어차피 함께 죽습니다. 그래서 하나로 줄여도 잃는 것이 없고 그러면 합계가 정확히 11이 됩니다. 2026년 7월 30일 제 원본 서비스에서도 같은 계산으로 12가 나왔습니다. 그래서 설치 전에 컨트롤러를 하나로 줄여 11/11로 맞췄습니다.


⑧편을 마치며 클러스터를 부쉈으니, `2-cluster`에 `ebs-csi.tf`를 넣은 채로 다시 세웁니다. 계획은 ⑧편의 16개에 이번 셋을 더한 `19 to add`입니다. 이 글을 쓸 때는 ⑧편의 클러스터에 이어서 적용해 `3 added`가 나왔고 애드온이 뜨는 데 45초쯤 걸렸습니다.


```bash
cd 2-cluster
tofu apply    # 19 to add
aws eks update-kubeconfig --name eks-lab --region ap-northeast-2
```


클러스터가 서면 `2-cluster` 폴더에 그대로 있는 채로 ⑧편의 순서를 밟습니다. ⑧편의 역할 주소 확인은 이 폴더에서 치는 것이고 Helm 블록 끝의 `cd ..`가 맨 위 폴더로 돌려보냅니다.


역할 주소를 확인하고 ESO를 설치한 뒤, `k8s/eso/` 아래 두 장을 적용해 `app-env`가 `SecretSynced`가 되는 것까지 봅니다. 시크릿 원본은 `0-bootstrap`에 남아 있으니 같은 값이 다시 들어옵니다. 앱은 데이터베이스를 띄운 뒤에 올립니다.


---


## StorageClass의 두 줄이 디스크를 언제 어디에 만들지 정합니다


이제 데이터베이스 매니페스트를 새로 씁니다. ⑦편의 `k8s/db-temp.yaml`을 대신할 파일은 `k8s/db.yaml`입니다. 여기에 StorageClass와 Service, StatefulSet이 들어갑니다. 먼저 StorageClass입니다.


```yaml
# k8s/db.yaml (1/3)
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
reclaimPolicy: Delete                   # PVC 를 지우면 디스크도 지웁니다
volumeBindingMode: WaitForFirstConsumer # 파드가 자리를 잡은 AZ 에 디스크를 만듭니다
```


`volumeBindingMode`를 기본값인 `Immediate`로 두면 PVC가 생기자마자 디스크를 만듭니다. 그 AZ는 아무 데나 정해지는데 EBS 디스크는 만들어진 AZ의 노드에만 붙습니다. ④편에서 서브넷을 두 AZ에 나눠 두었으니, 운이 나쁘면 디스크와 노드가 서로 다른 AZ에 생겨 파드가 영영 뜨지 못합니다.


`WaitForFirstConsumer`는 파드가 노드를 고를 때까지 기다립니다. 그리고 그 노드의 AZ에 디스크를 만들어서 이 문제를 처음부터 없앱니다. 그림의 둘째 칸과 셋째 칸이 바로 이 순서입니다.


`reclaimPolicy: Delete`를 두면 PVC를 지울 때 디스크도 함께 지웁니다. 실습용 클러스터에서는 이것이 맞습니다. 남겨 두면 클러스터를 부순 뒤에도 디스크가 조용히 요금을 받습니다. 다만 ⑩편에서는 이 설정이 정반대로 작용하는데 그 이야기는 그때 합니다.


---


## 데이터베이스는 Deployment가 아니라 StatefulSet으로 띄웁니다


Deployment로 띄운 파드는 이름도 디스크도 매번 새로 받습니다. 데이터베이스는 그러면 곤란하니 StatefulSet을 씁니다. StatefulSet은 파드에 `db-0`처럼 정해진 이름을 줍니다. 그리고 `volumeClaimTemplates`로 그 이름에 묶인 PVC를 만들어, 파드가 다시 떠도 같은 디스크를 붙여 줍니다.


```yaml
# k8s/db.yaml (2/3)
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


Service 이름이 ⑦편과 같은 `db`라서 앱이 받는 `DB_HOST`는 그대로 `db`입니다. ⑧편의 시크릿도 앱의 매니페스트도 고칠 것이 없습니다.


```yaml
# k8s/db.yaml (3/3)
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: db
spec:
  serviceName: db
  replicas: 1
  selector:
    matchLabels:
      app: db
  template:
    metadata:
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
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata # 디스크 맨 위가 아니라 한 칸 아래
          ports:
            - containerPort: 5432
          readinessProbe:
            exec:
              command: ["sh", "-c", 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
            periodSeconds: 5
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 256Mi
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: gp3
        resources:
          requests:
            storage: 1Gi
```


`PGDATA`를 디스크 맨 위에서 한 칸 아래로 내린 이유는 바로 다음에 일부러 깨 보면서 확인합니다.


`readinessProbe`는 데이터베이스가 접속을 받을 수 있을 때만 파드를 `Ready`로 표시합니다. 다만 `pg_isready`는 계정을 확인하지 않습니다. 이 글을 쓰며 없는 사용자 이름 `nobody`를 넣어 봤는데도 `accepting connections`와 함께 0을 돌려줬습니다. 그러니 이 프로브가 통과했다는 것은 "포트가 열렸다"는 뜻일 뿐입니다.


### 일부러 깨 보기 ①: 디스크 맨 위에 데이터를 두면 초기화가 거절됩니다


먼저 `PGDATA` 두 줄을 빼고 적용해 봅니다. 7월 30일 제 원본에서는 처음부터 하위 디렉터리로 내려 두어서 이 오류를 보지 않았습니다. 아래는 이 글을 쓰며 일부러 만든 결과입니다.


```bash
kubectl apply -f k8s/db.yaml       # PGDATA 두 줄을 뺀 채로
kubectl get pvc,pods
```


PVC는 처음에 `Pending`이었고 41초 뒤에 다시 보니 `Bound`였습니다. 하지만 `db-0`은 `CrashLoopBackOff`로 빠졌고 ⑦편에서 배운 대로 직전 로그를 보면 이유가 적혀 있습니다.


```bash
kubectl logs db-0 --previous | tail -4
```


```plain text
initdb: error: directory "/var/lib/postgresql/data" exists but is not empty
initdb: detail: It contains a lost+found directory, perhaps due to it being a mount point.
initdb: hint: Using a mount point directly as the data directory is not recommended.
Create a subdirectory under the mount point.
```


새 EBS 디스크를 ext4로 포맷하면 맨 위에 `lost+found` 디렉터리가 생깁니다. postgres는 빈 디렉터리에서만 데이터베이스를 새로 만듭니다. 그 디렉터리 하나 때문에 비어 있지 않다고 보고 거절한 것입니다. 오류의 마지막 줄이 하위 디렉터리를 만들라고 답까지 알려 줍니다.


### 일부러 깨 보기 ②: 고친 매니페스트를 적용해도 망가진 파드는 그대로입니다


그러면 `PGDATA` 두 줄을 되살려 다시 적용하면 끝날까요? 이 글을 쓰며 그렇게 해 보니 2분이 지나도 `db-0`은 옛 설정 그대로 `CrashLoopBackOff`였습니다. StatefulSet에는 새 설정이 들어갔는데 파드는 바뀌지 않은 것입니다.


```bash
kubectl apply -f k8s/db.yaml
kubectl get sts db -o jsonpath='{.status.updateRevision} {.status.currentRevision}{"\n"}'
kubectl get pod db-0 -o jsonpath='{.metadata.labels.controller-revision-hash}{"\n"}'
```


```plain text
db-5cb66ffbdd db-79664657f7
db-79664657f7
```


StatefulSet은 파드를 하나씩 차례로 바꾸는데 바꾸기 전에 지금 파드가 `Ready`가 되기를 기다립니다. 망가진 파드는 영영 `Ready`가 되지 않으니 차례도 오지 않습니다. 이럴 때는 파드를 손으로 지웁니다. StatefulSet이 새 설정으로 `db-0`을 다시 만들고 PVC는 그대로 남아 같은 디스크가 붙습니다.


```bash
kubectl delete pod db-0
kubectl wait --for=condition=Ready pod/db-0 --timeout=180s
kubectl exec db-0 -- ls /var/lib/postgresql/data
```


```plain text
lost+found
pgdata
```


---


## 디스크가 실제로 생겼는지는 AWS에 직접 묻습니다


PVC의 이벤트에는 디스크가 만들어지기까지의 과정이 네 줄로 남습니다. 파드가 노드를 고를 때까지 기다렸고, 드라이버가 일을 받았고, 쿠버네티스가 그 결과를 기다렸고, 만들어졌다는 순서입니다.


```bash
kubectl describe pvc data-db-0 | tail -4
```


```plain text
# Age 와 From 열은 뺐습니다
Normal  WaitForFirstConsumer   waiting for first consumer to be created before binding
Normal  Provisioning           External provisioner is provisioning volume for claim "default/data-db-0"
Normal  ExternalProvisioning   Waiting for a volume to be created either by the external provisioner ...
Normal  ProvisioningSucceeded  Successfully provisioned volume pvc-2eb1025c-...
```


쿠버네티스의 말만 믿지 않고 AWS에도 물어봅니다. 크기가 1GiB, 종류가 gp3, AZ가 노드와 같고 암호화되어 있고 노드에 붙어 `in-use`여야 합니다.


```bash
kubectl get nodes -L topology.kubernetes.io/zone
aws ec2 describe-volumes --region ap-northeast-2 \
  --filters Name=tag:kubernetes.io/created-for/pvc/name,Values=data-db-0 \
  --query 'Volumes[].[Size,VolumeType,AvailabilityZone,Encrypted,State]' --output text
```


```plain text
# 노드 줄의 ZONE 도 ap-northeast-2c 였습니다. 아래는 디스크 줄입니다
1	gp3	ap-northeast-2c	True	in-use
```


---


## 파드를 지워도 데이터가 남는 것이 이번 편의 합격선입니다


이제 처음의 실험을 다시 합니다. 표를 만들고 세 줄을 넣은 뒤, 파드의 UID와 디스크 이름을 적어 두고 파드를 지웁니다.


```bash
q() { kubectl exec db-0 -- sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -tAc \"$1\""; }
q "create table memo(id int); insert into memo values (1),(2),(3);"
kubectl get pod db-0 -o jsonpath='{.metadata.uid}{"\n"}'
kubectl get pvc data-db-0 -o jsonpath='{.spec.volumeName}{"\n"}'
kubectl delete pod db-0
kubectl wait --for=condition=Ready pod/db-0 --timeout=180s
kubectl get pod db-0 -o jsonpath='{.metadata.uid}{"\n"}'
kubectl get pvc data-db-0 -o jsonpath='{.spec.volumeName}{"\n"}'
q "select count(*) from memo"
```


```plain text
# 확인할 줄만 옮겼습니다. 명령이 내는 CREATE TABLE, deleted 같은 줄은 뺐습니다
427948cd-ef60-4906-897f-fd5c932824c5
pvc-2eb1025c-9d97-4227-b84c-d20eb9025485
cd900469-e8d9-462a-bc85-456ebe7fcaba
pvc-2eb1025c-9d97-4227-b84c-d20eb9025485
3
```


파드의 UID는 바뀌었고 디스크 이름과 행 수는 그대로입니다. 파드는 새로 태어났지만 같은 디스크를 다시 받았다는 뜻입니다. 처음에 `relation "memo" does not exist`가 나왔던 자리에서 이번에는 3이 나왔으니 합격입니다. 이제 ⑧편처럼 앱을 올리고 앱이 이 데이터베이스에 붙는지 봅니다. 새 터미널이라면 `REPO`와 `SHA`부터 다시 정합니다. 노드의 파드 자리도 함께 섭니다.


```bash
REPO=$(tofu -chdir=0-bootstrap output -raw ecr_repository_url)
SHA=$(aws ecr describe-images --repository-name eks-lab/app --region ap-northeast-2 \
  --query 'sort_by(imageDetails,&imagePushedAt)[-1].imageTags[0]' --output text)
sed "s|IMAGE_PLACEHOLDER|$REPO:$SHA|" k8s/app.yaml | kubectl apply -f -
kubectl rollout status deploy/app
kubectl port-forward svc/app 8080:8080 &
sleep 3; curl -s localhost:8080/actuator/health
kill %1
kubectl get pods -A --no-headers | wc -l
```


```plain text
# 확인할 줄만 옮겼습니다
{"groups":["liveness","readiness"],"status":"UP"}
11
```


`UP`은 앱이 Service `db` 뒤의 `db-0`에 접속했다는 뜻입니다. 그리고 파드 수가 앞에서 계산한 11과 정확히 같습니다.


---


## 자리가 꽉 찬 노드에서는 앱을 새로 띄우는 일도 막힙니다


앞에서 센 대로 이제 노드의 파드 자리가 11/11입니다. 자리가 하나도 남지 않은 노드에서는 무엇이 막힐까요? 데이터베이스가 아니라 앱을 새로 띄우는 일에서 먼저 드러납니다.


### 일부러 깨 보기 ③: 꽉 찬 노드에서 `rollout restart`


파드 자리가 11/11이 된 상태에서 `kubectl rollout restart deploy/app`을 쳐 보면 어떻게 될까요? Deployment는 기본적으로 새 파드를 먼저 띄우고 옛 파드를 내립니다. 그러려면 잠깐이라도 열두 번째 자리가 필요한데 그 자리가 없으니 새 파드가 `Pending`에 걸립니다.


```plain text
0/1 nodes are available: 1 Too many pods. ...
```


7월 30일 제 원본 서비스에서도 같은 `Too many pods`로 재배포가 멈췄고 그날은 옛 파드를 손으로 지워 자리를 비웠습니다. 이 글을 쓰며 같은 상황을 만들었을 때는 다른 일도 겹쳤습니다. 마침 `db-0`을 지운 틈에 새 앱 파드가 자리를 잡았는데 첫 몇 번은 IP를 받지 못했습니다. 그다음에는 아직 일어나지 않은 데이터베이스에 접속하다가 죽었습니다.


```plain text
failed to assign an IP address to container
Caused by: org.postgresql.util.PSQLException: Connection to db:5432 refused.
```


앱은 데이터베이스가 일어나자 스스로 다시 떴지만 자리가 없는 노드에서는 이런 일이 언제든 겹칠 수 있습니다. 그래서 앱의 배포 방식을 옛 파드를 먼저 내리는 `Recreate`로 바꿉니다. 재시작하는 동안 잠깐 앱이 비지만 실습용 클러스터에서는 그편이 자리를 기다리며 멈추는 것보다 낫습니다. `k8s/app.yaml`의 `replicas: 1` 아래에 두 줄을 더합니다.


```yaml
strategy:
    type: Recreate # 노드에 남는 자리가 없어서, 옛 파드를 먼저 내립니다
```


적용은 앞의 `sed … | kubectl apply -f -` 한 줄을 그대로 다시 치면 됩니다.


옛 파드가 먼저 내려가니 `Pending`에 걸려 있던 새 파드도 자리를 잡을 것입니다. 다만 이 글을 쓸 때는 `db-0`을 지운 사이에 먼저 풀려서 이 경로는 직접 확인하지 못했습니다. 적용한 뒤 `rollout restart`를 다시 쳤더니 41초 만에 끝났습니다. 새 파드가 뜨기 전에 옛 파드가 자리를 비웠기 때문입니다. 대신 그 41초 동안은 앱에 닿을 수 없습니다.


---


## StatefulSet을 지워도 디스크는 남습니다


정리하기 전에 하나를 확인합니다. StatefulSet을 지우면 디스크도 사라질까요? 정리 순서가 이 답에 달려 있습니다.


```bash
kubectl delete sts db
kubectl get pvc
aws ec2 describe-volumes --region ap-northeast-2 \
  --filters Name=tag:kubernetes.io/created-for/pvc/name,Values=data-db-0 \
  --query 'Volumes[].State' --output text
```


```plain text
NAME        STATUS   VOLUME                                     CAPACITY   ...
data-db-0   Bound    pvc-2eb1025c-9d97-4227-b84c-d20eb9025485   1Gi        ...
available
```


PVC는 `Bound`로 남았고 디스크는 노드에서 떨어져 `available`이 됐습니다. `volumeClaimTemplates`가 만든 PVC는 데이터를 지키려고 일부러 남기기 때문입니다. 그래서 같은 매니페스트를 다시 적용하면 `db-0`이 같은 PVC를 다시 붙이고 `memo`의 3행도 그대로 돌아옵니다. 정리 순서를 그대로 따르려면 여기서 다시 적용해 둡니다.


```bash
kubectl apply -f k8s/db.yaml
kubectl wait --for=condition=Ready pod/db-0 --timeout=180s
q "select count(*) from memo"    # 3
```


정리할 때가 문제입니다. 이 디스크는 쿠버네티스가 만든 것이라 OpenTofu의 state에 없고 `tofu destroy`는 이 디스크를 모릅니다. 7월 30일 제 원본에서도 StatefulSet을 지운 직후 디스크가 `in-use`로 남아 있었습니다. PVC까지 지우고 나서야 디스크가 사라졌습니다.


---


## 정리할 때는 PVC를 지우고 디스크가 사라진 것까지 봅니다


순서는 ⑧편과 같이 소유자부터이고 이번에는 그 뒤에 PVC가 하나 더 붙습니다. PVC를 지우면 `reclaimPolicy: Delete`에 따라 드라이버가 디스크를 지웁니다.


```bash
kubectl delete -f k8s/eso/app-env.yaml -f k8s/eso/secretstore.yaml
kubectl delete -f k8s/app.yaml -f k8s/db.yaml
kubectl delete pvc data-db-0
aws ec2 describe-volumes --region ap-northeast-2 \
  --filters Name=tag:kubernetes.io/created-for/pvc/name,Values=data-db-0 \
  --query 'Volumes[].State' --output text
```


이 글을 쓰며 3~4초 간격으로 물어보니 PVC를 지우고 11초 뒤까지는 `in-use`였습니다. 노드에서 떼어 내는 데 시간이 걸려서 15초 뒤에야 `available`이 됐고 18초 뒤에는 빈 답이 돌아왔습니다. 7월 30일 원본에서는 디스크가 지워지기 시작한 때부터 사라질 때까지 7초였습니다. 그러니 조회 명령은 빈 답이 나올 때까지 몇 초 간격으로 다시 치고 빈 답을 본 뒤에 `tofu destroy`를 합니다.


```bash
cd 2-cluster && tofu destroy && cd ..
```


`Destroy complete! Resources: 19 destroyed.`가 나오면 ⑤편의 확인 명령을 돌립니다. 그중 디스크를 묻는 명령은 이번 편부터 의미가 생깁니다. `k8s/db.yaml`과 고친 `k8s/app.yaml`은 커밋하고 `k8s/db-temp.yaml`은 이제 지워도 됩니다.


---


## 이 방식은 백업과 자리 여유로 값을 치릅니다


데이터가 디스크에 남게 됐지만 그 디스크는 한 장뿐입니다. 관리형 데이터베이스라면 자동 백업과 특정 시점 복구가 체크박스 하나인데 지금 구성에는 그런 것이 하나도 없습니다. 디스크가 망가지거나 PVC를 잘못 지우면 데이터는 돌아오지 않습니다.


게다가 디스크의 수명이 아직 클러스터에 묶여 있습니다. 이번 편의 정리 순서는 실습이 끝날 때마다 데이터를 지웁니다. 클러스터를 부숴도 데이터가 남게 하려면 디스크를 클러스터보다 오래 사는 층으로 옮겨야 하고 그것이 ⑩편의 주제입니다.


그리고 노드의 파드 자리가 11/11로 꽉 찼습니다. 여기서 무엇을 하나 더 띄우려면 다른 것을 줄이거나 노드를 키워야 합니다. 이 시리즈는 비용을 지키려고 t4g.small 한 대를 유지하는데 그 대가가 이번에 본 `Too many pods`입니다.


---


## 정리


| 할 일     | 명령이나 파일                               | 확인                       |
| ------- | ------------------------------------- | ------------------------ |
| 드라이버 설치 | `2-cluster/ebs-csi.tf`                | `19 added`, 다 올리면 파드 11개 |
| 디스크 규칙  | StorageClass `gp3`                    | `WaitForFirstConsumer`   |
| 데이터베이스  | StatefulSet `db`, `PGDATA` 한 칸 아래     | `db-0` Ready             |
| 디스크 확인  | `aws ec2 describe-volumes`            | 노드와 같은 AZ, `in-use`      |
| 합격선     | `db-0` 지우고 다시 세기                      | UID만 바뀌고 행 수는 그대로        |
| 정리      | `kubectl delete pvc` 뒤 `tofu destroy` | 디스크 조회가 빈 답              |


파드를 지워도 데이터가 남게 하려면 데이터를 파드가 아니라 파드가 빌려 쓰는 디스크에 둡니다. 그 디스크를 만드는 일은 역할을 빌린 드라이버가 하고 파드가 다시 떠도 같은 디스크를 받게 하는 것은 StatefulSet입니다.


다음 편에서는 디스크를 `0-bootstrap`으로 옮겨, 클러스터를 통째로 부수고 다시 세워도 데이터가 남는지 봅니다. 이번 편에서 옳았던 `reclaimPolicy: Delete`가 거기서는 왜 사고가 되는지도 함께 봅니다.


---


## 참고

- [Amazon EKS 사용 설명서, Amazon EBS CSI 드라이버](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [Kubernetes Docs, Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Kubernetes Docs, StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [postgres 공식 이미지, PGDATA](https://hub.docker.com/_/postgres)
- 디스크 단가(gp3, GB당 월 \$0.0912)는 ⑤편에서 AWS Pricing API로 조회한 값입니다.
- 제 원본 작업 일지와 전체 코드는 [switch-job-quest](https://github.com/bangddong/switch-job-quest) 레포에 있습니다. 서비스를 닫으면서 보관(archive)해 두었습니다.
> 이 편의 코드와 매니페스트는 이 글을 위해 새로 쓴 것입니다. 2026년 11월 17일에 ⑧편의 클러스터를 부수지 않고 이 코드를 더해 제 계정에 실제로 apply했고(`3 added`), 위의 출력은 전부 그 클러스터에서 받았습니다. 다만 순서는 글과 조금 달라서, `UP`은 데이터베이스를 StatefulSet으로 바꾼 직후 그 전부터 떠 있던 앱 파드에서, 파드 수 11은 앱을 새로 띄운 뒤에 받았습니다. 원본은 이 단계에서 RDS를 클러스터 안 데이터베이스로 바꾸며 TLS 인증서까지 붙였지만, 이 시리즈의 앱은 TLS를 요구하지 않아서 그 부분을 뺐습니다. 파드 상한 계산과 `Too many pods`, StatefulSet을 지워도 디스크가 남은 일, 디스크 회수 7초는 7월 30일 제 일지의 기록입니다. 비용은 클러스터를 다시 세우는 9분쯤과 부수는 시간까지 더해 한 시간이 넘지 않는다고 보고, ⑤편의 시간당 \$0.13쯤을 곱해 어림한 값입니다. 막히는 곳이 있으면 알려 주시기 바랍니다.
>
> 이 글의 그림은 AI가 그렸습니다.
>
>
