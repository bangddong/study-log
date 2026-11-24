---
title: '클러스터는 부수고 데이터는 옮겨 붙인다. EKS 실습기 ⑩, 부숴도 남는 데이터'
date: '2026-11-15'
tags:
  - AWS
  - EKS
series: AWS EKS 실습기
emoji: ''
---
> **AWS 프리티어 \$200으로 EKS 실습하기 ⑩** · 💰 클러스터를 두 번 세우는 한 시간 남짓에 약 **\$0.15**, 그리고 디스크 1GiB에 월 **\$0.09**

⑨편에서 파드를 지워도 데이터가 남게 만들었습니다. 그런데 실습이 끝날 때마다 `tofu destroy`로 클러스터를 통째로 부수면 그 데이터는 어떻게 될까요? ⑨편의 정리 순서를 그대로 따랐다면 PVC를 지우는 순간 디스크도 함께 지워졌습니다. 다시 말해 지금 구성에서 데이터의 수명은 클러스터의 수명과 같습니다.


이번 편에서는 디스크를 클러스터보다 오래 사는 층으로 옮깁니다. 그리고 클러스터를 실제로 부수고 다시 세운 뒤, 부수기 전에 넣어 둔 한 줄이 그대로 돌아오는지 확인합니다. 마지막으로 그 디스크마저 잃었을 때를 위해 백업을 뜨고 되돌려 봅니다.

> 클러스터는 부수는 것이고, 데이터는 옮겨 붙이는 것이다.

---


## 디스크는 `0-bootstrap`에 두고 쿠버네티스는 빌려 쓰기만 합니다


⑨편에서는 PVC를 내면 드라이버가 디스크를 만들었습니다. 이것을 동적 방식이라고 부르는데 만든 쪽이 쿠버네티스이니 지우는 쪽도 쿠버네티스입니다. 그래서 이번에는 반대로 갑니다. 디스크는 OpenTofu가 `0-bootstrap`에서 만들고 쿠버네티스에는 "이미 있는 이 디스크를 써라"라고 알려 주기만 합니다.


`0-bootstrap`인 이유는 ⑥편의 ECR이나 ⑧편의 시크릿과 같습니다. 이 층은 실습이 끝나도 지우지 않으니 클러스터를 몇 번 부숴도 디스크가 남습니다. 대신 이 순간부터 디스크는 클러스터를 켜지 않은 날에도 요금을 받는데 1GiB짜리 gp3라 한 달에 9센트쯤입니다.


```hcl
# db-volume.tf
# 데이터베이스 디스크는 클러스터보다 오래 삽니다
variable "db_az" {
  type    = string
  default = "ap-northeast-2a" # 디스크는 이 AZ 를 떠날 수 없습니다
}

resource "aws_ebs_volume" "db" {
  availability_zone = var.db_az
  size              = 1
  type              = "gp3"
  encrypted         = true
  tags              = { Name = "eks-lab-db" }

  lifecycle {
    prevent_destroy = true # 실수로 destroy 해도 plan 에서 멈춥니다
  }
}

output "db_volume_id" {
  value = aws_ebs_volume.db.id
}

output "db_az" {
  value = var.db_az
}
```


`prevent_destroy`는 이 디스크를 지우는 계획이 나오면 OpenTofu가 거기서 멈추게 합니다. 이 층에 `tofu destroy`를 칠 일은 시리즈 마지막의 ⑭편뿐이지만 그 전에 실수로 칠 수도 있어서 걸어 둡니다. `tofu apply`를 하면 `1 added`가 나오고 디스크는 11초 만에 생겼습니다.


```bash
tofu -chdir=0-bootstrap apply
aws ec2 describe-volumes --region ap-northeast-2 --volume-ids "$(tofu -chdir=0-bootstrap output -raw db_volume_id)" \
  --query 'Volumes[0].[State,Size,AvailabilityZone]' --output text
```


```plain text
available	1	ap-northeast-2a
```


---


## 디스크를 먼저 만들면 노드가 디스크의 AZ로 가야 합니다


⑨편의 `WaitForFirstConsumer`는 파드가 노드를 고른 뒤에 그 AZ에 디스크를 만들었습니다. 덕분에 AZ가 어긋날 일이 없었습니다. 이번에는 디스크가 먼저 `ap-northeast-2a`에 있으니 노드가 그 AZ에 떠야 합니다. 그런데 ⑤편의 노드 그룹은 두 AZ의 서브넷을 다 받아서 어디에 뜰지 모릅니다.


### 일부러 깨 보기 ①: 디스크와 노드가 다른 AZ에 있을 때


실제로 ⑨편을 마친 클러스터의 노드는 `ap-northeast-2c`에 떠 있었습니다. 그 상태로 아래 절의 매니페스트를 적용해 보면 PVC는 `Bound`가 되는데 파드는 `Pending`에서 움직이지 않습니다.


```plain text
NAME                            STATUS   VOLUME    CAPACITY   ...
persistentvolumeclaim/db-data   Bound    db-data   1Gi        ...
NAME   READY   STATUS    RESTARTS   AGE
db-0   0/1     Pending   0          21s
```


```plain text
0/1 nodes are available: 1 node(s) didn't match PersistentVolume's node affinity. ...
```


PVC가 `Bound`라서 디스크 쪽은 끝난 것처럼 보여도 실제로는 파드를 올릴 노드가 디스크의 AZ에 없습니다. 이 실패는 제 원본에서는 겪지 않았고 이 글을 쓰며 일부러 만들었습니다. 원본은 처음부터 노드를 디스크의 AZ로 묶어 두었습니다.


그래서 노드 그룹의 서브넷을 디스크가 있는 AZ 하나로 좁힙니다. 먼저 `1-network/outputs.tf`에 AZ별 서브넷을 꺼내는 출력을 하나 더합니다. 그러면 `2-cluster`가 AZ 이름으로 서브넷을 고를 수 있습니다.


```hcl
# 1-network/outputs.tf 에 더합니다
output "public_subnet_ids_by_az" {
  value = zipmap(var.azs, aws_subnet.public[*].id)
}
```


```hcl
# 2-cluster/nodes.tf 의 subnet_ids 를 이렇게 바꿉니다
  # 데이터베이스 디스크가 있는 AZ 의 서브넷 하나에만 노드를 띄웁니다
  subnet_ids = [
    data.terraform_remote_state.network.outputs.public_subnet_ids_by_az[
      data.terraform_remote_state.bootstrap.outputs.db_az
    ]
  ]
```


AZ 이름은 `0-bootstrap`의 `db_az` 한 곳에만 적고 `2-cluster`는 그 값을 읽기만 합니다. 같은 값을 두 곳에 적어 두면 언젠가는 한쪽만 고치는 날이 옵니다. `1-network`도 반드시 `tofu apply`합니다. 바뀌는 리소스는 0개지만 새 출력이 state에 적혀야 `2-cluster`가 읽을 수 있습니다.


```bash
tofu -chdir=1-network apply    # 0 added, Outputs 에 public_subnet_ids_by_az
```


클러스터가 이미 떠 있다면 `2-cluster`의 `plan`이 노드 그룹을 지우고 새로 만든다고 알려 줍니다. 노드 그룹의 서브넷은 바꿀 수 없는 속성이라서 통째로 갈아야 합니다. 이 글을 쓰며 해 보니 옛 노드 그룹을 지우는 데 8분 10초, 새로 만드는 데 1분 48초가 걸렸습니다. 클러스터를 막 부순 상태라면 뒤에서 다시 세울 때 처음부터 그 AZ에 뜹니다. 아래는 클러스터가 떠 있을 때 확인한 결과입니다.


```bash
kubectl get nodes -L topology.kubernetes.io/zone
```


```plain text
NAME                                           STATUS   ROLES    AGE   VERSION               ZONE
ip-10-0-8-81.ap-northeast-2.compute.internal   Ready    <none>   59s   v1.36.5-eks-9adbfea   ap-northeast-2a
```


---


## PV는 사람이 쓰는 창고증이고 지우는 규칙이 ⑨편과 반대입니다


이제 쿠버네티스에 디스크를 소개합니다. 동적 방식에서는 드라이버가 PV를 만들어 줬지만 이번에는 PV를 사람이 직접 씁니다. PV에 디스크 ID를 적어 두면 그 PV가 "이 디스크는 여기 있다"는 창고증이 되고 PVC는 아무 PV나 받지 않고 그 창고증을 이름으로 지목합니다.


```yaml
# k8s/db-static.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: static
provisioner: kubernetes.io/no-provisioner # 아무것도 만들지 않습니다. 이름만 필요합니다
volumeBindingMode: WaitForFirstConsumer
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: db-data
spec:
  capacity:
    storage: 1Gi
  accessModes: ["ReadWriteOnce"]
  storageClassName: static
  persistentVolumeReclaimPolicy: Retain # PVC 를 지워도 디스크는 남깁니다
  csi:
    driver: ebs.csi.aws.com
    volumeHandle: VOLUME_ID_PLACEHOLDER # 0-bootstrap 이 만든 디스크
    fsType: ext4
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - key: topology.kubernetes.io/zone
              operator: In
              values: [AZ_PLACEHOLDER]
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: db-data
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: static
  volumeName: db-data # 아무 PV 나 받지 않고 이것 하나를 지목합니다
  resources:
    requests:
      storage: 1Gi
```


가장 중요한 한 줄은 `persistentVolumeReclaimPolicy: Retain`입니다. ⑨편의 StorageClass는 `Delete`였는데 실습이 끝나면 디스크도 지워야 요금이 남지 않으니 거기서는 그 설정이 맞았습니다. 하지만 같은 `Delete`를 여기에 두면 PVC를 정리하는 순간 몇 달치 데이터를 담은 디스크까지 함께 지워집니다. 같은 설정이 목적에 따라 옳기도 하고 사고가 되기도 합니다.


디스크 ID는 계정마다 다르니 매니페스트에 적지 않고 적용할 때 `0-bootstrap`의 출력으로 바꿔 넣습니다. ⑥편의 `IMAGE_PLACEHOLDER`와 같은 방식입니다. 그런데 ⑧편에서 본 것처럼 `tofu output`은 실패해도 종료 코드가 0일 수 있으니 바꿔 넣기 전에 값이 비어 있지 않은지 먼저 봅니다.


```bash
VOL=$(tofu -chdir=0-bootstrap output -raw db_volume_id)
AZ=$(tofu -chdir=0-bootstrap output -raw db_az)
case "$VOL" in vol-*) echo "OK $VOL $AZ" ;; *) echo "디스크 ID가 아닙니다. 여기서 멈춥니다" ;; esac
```


`OK`로 시작하는 줄이 나왔을 때만 뒤의 적용으로 넘어갑니다.


`k8s/db.yaml`도 고쳐서 ⑨편의 `gp3` StorageClass 문서와 StatefulSet의 `volumeClaimTemplates` 블록을 지웁니다. 사람이 만든 PVC는 이름으로 붙입니다. `volumeClaimTemplates`는 PVC를 새로 만들어 버리니 지목한 PVC와 함께 둘 수 없습니다. 컨테이너의 `resources` 블록 아래, `containers`와 같은 깊이에 네 줄을 더합니다.


```yaml
volumes:
        - name: data
          persistentVolumeClaim:
            claimName: db-data # 사람이 만든 PVC 를 씁니다
```


`volumeClaimTemplates`는 바꿀 수 없는 필드입니다. ⑨편의 StatefulSet이 떠 있다면 `kubectl delete sts db`로 먼저 지웁니다.


⑨편을 마치며 PVC `data-db-0`을 지우지 않았다면 그 디스크가 2c에 남아 요금을 받으니 `kubectl delete pvc data-db-0`도 함께 합니다. 클러스터를 이미 부순 뒤라면 ⑨편의 태그 필터로 그 디스크를 찾아 `aws ec2 delete-volume`으로 지웁니다.


⑨편 끝에서 클러스터를 부쉈다면 여기서 다시 세웁니다. 같은 이름이라도 새 클러스터는 주소와 인증서가 달라서 `aws eks update-kubeconfig`로 접속 정보도 새로 받습니다. 노드는 이미 디스크의 AZ에 뜹니다.


```bash
cd 2-cluster
tofu apply
aws eks update-kubeconfig --name eks-lab --region ap-northeast-2
```


그다음 `2-cluster` 폴더에 있는 채로 ⑧편의 순서대로 역할 주소를 확인하고 ESO를 설치합니다. Helm 블록 끝의 `cd ..`가 맨 위 폴더로 돌려보내면 `k8s/eso/` 두 장을 적용하고 `app-env`가 `SecretSynced`가 되는 것까지 본 뒤 아래를 칩니다.


```bash
REPO=$(tofu -chdir=0-bootstrap output -raw ecr_repository_url)
SHA=$(aws ecr describe-images --repository-name eks-lab/app --region ap-northeast-2 \
  --query 'sort_by(imageDetails,&imagePushedAt)[-1].imageTags[0]' --output text)
sed -e "s|VOLUME_ID_PLACEHOLDER|$VOL|" -e "s|AZ_PLACEHOLDER|$AZ|" k8s/db-static.yaml | kubectl apply -f -
kubectl apply -f k8s/db.yaml
kubectl wait --for=condition=Ready pod/db-0 --timeout=300s
sed "s|IMAGE_PLACEHOLDER|$REPO:$SHA|" k8s/app.yaml | kubectl apply -f -
kubectl rollout status deploy/app
```


---


## 클러스터를 부수기 전에 한 줄을 심어 두고 다시 세운 뒤에 찾습니다


데이터가 남았는지는 무엇으로 알 수 있을까요? 표가 있다거나 앱이 뜬다는 것만으로는 부족합니다. 빈 디스크에서 새로 만든 데이터베이스도 겉으로는 똑같아 보일 수 있습니다. 그래서 부수기 전에 무작위 값 한 줄을 넣어 두고 다시 세운 뒤 그 값이 그대로 있는지로만 판정합니다.


```bash
q() { kubectl exec db-0 -- sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -tAc \"$1\""; }
T=$(openssl rand -hex 4); echo "$T"     # 이 값을 적어 둡니다
q "create table memo(note text); insert into memo values ('$T');"
```


이 글을 쓸 때 심은 값은 `9283ed75`였습니다. 이제 클러스터를 부숩니다. 이 글을 쓸 때는 데이터베이스를 띄워 둔 채로 바로 `tofu destroy`를 했는데도 디스크는 지워지지 않았습니다. 디스크는 `0-bootstrap`의 리소스라서 `2-cluster`의 state에는 들어 있지 않습니다.


```bash
cd 2-cluster && tofu destroy && cd ..
aws ec2 describe-volumes --region ap-northeast-2 --volume-ids "$VOL" \
  --query 'Volumes[0].[State,AvailabilityZone]' --output text
```


```plain text
available	ap-northeast-2a
```


`Destroy complete! Resources: 19 destroyed.` 뒤에도 디스크는 `available`로 남았습니다.


이제 앞 절의 순서를 처음부터 다시 밟습니다. `cd 2-cluster`로 들어가 클러스터를 `apply`하고 `update-kubeconfig`를 한 뒤, 그 폴더에서 ⑧편의 ESO 단계를 밟고 매니페스트 두 장을 적용합니다. 그리고 앞 절 블록의 `REPO`부터 마지막 `app.yaml` 줄까지를 그대로 다시 칩니다. 새 터미널이라면 `VOL`과 `AZ`, `q`도 앞에서처럼 다시 정합니다. 마지막으로 `db-0`의 로그와 심어 둔 값을 봅니다.


왕복 전체를 그림으로 보면 이렇습니다. 넷째 칸에서 사라지는 것은 클러스터뿐이고 디스크는 그대로 남는다는 점을 보시기 바랍니다.


![디스크는 0-bootstrap에 남고 클러스터만 부서졌다가 다시 세워지며, 같은 디스크가 다시 붙어 심어 둔 값이 돌아옵니다](https://dhbang.co.kr/images/aws-eks/anim08-rebuild.svg)


실제로 확인한 결과는 이렇습니다.


```bash
kubectl logs db-0 | grep -i skipping
q "select * from memo"
```


```plain text
PostgreSQL Database directory appears to contain a database; Skipping initialization
9283ed75
```


`Skipping initialization`은 postgres가 디스크에서 기존 데이터베이스를 찾았다는 뜻입니다. 빈 디스크였다면 초기화부터 돌았을 것입니다. 부수기 전에 심은 `9283ed75`도 그대로 돌아왔습니다. 이 글을 쓰며 잰 시간은 destroy가 10분 37초, 다시 apply가 8분 39초였습니다. 매니페스트를 적용하고 `db-0`이 `Ready`가 되기까지는 14초였습니다.


2026년 8월 7일 제 원본 서비스에서도 같은 왕복을 했습니다. 그날은 이전 클러스터에서 넣어 둔 확인용 행이 원래 기록 시각 그대로 돌아왔고 파드와 노드는 다른 객체였습니다. 그런데 데이터가 돌아온 바로 다음에 다른 곳이 깨졌습니다.


---


## 디스크 안에 구워진 비밀번호는 디스크와 같은 층에 있어야 합니다


8월 7일 원본에서 데이터는 붙었는데 앱이 `CrashLoopBackOff`에 빠졌습니다. 로그에는 비밀번호가 틀렸다고 적혀 있었습니다. 데이터베이스 비밀번호를 클러스터 층(`2-cluster`)에서 만든 것이 원인이었습니다.


postgres 이미지는 `POSTGRES_PASSWORD`를 데이터베이스를 처음 만들 때 한 번만 씁니다. 디스크에 데이터베이스가 이미 있으면 그 변수를 읽지도 않고 처음 비밀번호를 그대로 기억합니다. 그런데 비밀번호가 클러스터 층에 있으면 `tofu destroy`가 state에서 지우고 다시 `apply`할 때 새 값을 뽑아 앱에 흘립니다. 디스크는 옛 비밀번호를, 앱은 새 비밀번호를 들고 만나는 셈입니다.


⑧편에서 시크릿을 처음부터 `0-bootstrap`에 둔 것이 이 때문입니다. 그래서 이번 왕복에서는 비밀번호가 바뀌지 않았고 앱도 바로 붙었습니다. 그렇다면 비밀번호가 바뀌면 정말 어떻게 될까요?


### 일부러 깨 보기 ②: 비밀번호만 새로 뽑기


이 글을 쓰며 원본의 상황을 재현하려고 `0-bootstrap`에서 비밀번호 하나만 다시 뽑았습니다. `-replace`는 그 리소스를 지우고 새로 만들게 하는 옵션입니다. 시크릿 버전도 따라 바뀌어 계획은 `2 to add, 0 to change, 2 to destroy`입니다. 그다음 ⑧편처럼 바로 동기화하고 앱을 재시작합니다.


```bash
tofu -chdir=0-bootstrap apply -replace=random_password.db
kubectl annotate externalsecret app-env force-sync="$(date +%s)" --overwrite
kubectl rollout restart deploy/app
sleep 20; kubectl logs deploy/app | grep "Caused by"   # 새 파드가 뜰 때까지 잠깐 기다립니다
```


```plain text
Caused by: org.postgresql.util.PSQLException: FATAL: password authentication failed for user "app"
```


원본과 같은 오류입니다. 데이터베이스 쪽 로그를 보면 앱의 접속이 `pg_hba.conf`의 `scram-sha-256` 줄에 걸려 비밀번호 검사에서 떨어진 것이 보입니다. 그러면 `db-0`도 재시작하면 새 비밀번호를 읽지 않을까요? 이 글을 쓰며 해 보니 재시작한 `db-0`의 환경변수는 새 값이 됐지만 로그에는 `Skipping initialization`이 찍혔고 오류는 그대로였습니다.


그래서 디스크 안의 비밀번호를 새 값으로 직접 바꿉니다. 컨테이너 안의 로컬 접속은 비밀번호를 묻지 않으니 옛 비밀번호를 몰라도 됩니다. 아래 명령은 `db-0` 안의 환경변수를 읽어 그 자리에서 바꾸므로 비밀번호가 노트북의 셸 기록에 남지 않습니다.


다만 그 환경변수도 컨테이너가 시작할 때 한 번 정해지므로 `db-0`을 먼저 재시작해서 새 비밀번호를 받게 해야 합니다. 이 줄을 빼면 옛 비밀번호를 다시 걸게 되고 뒤의 확인까지 옛 값으로 통과해 버립니다.


```bash
kubectl delete pod db-0
kubectl wait --for=condition=Ready pod/db-0 --timeout=180s
kubectl exec db-0 -- sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "ALTER USER \"$POSTGRES_USER\" PASSWORD '"'"'$POSTGRES_PASSWORD'"'"';"'
kubectl rollout restart deploy/app
```


`ALTER ROLE`이 나온 뒤 앱을 재시작하자 `/actuator/health`가 다시 `UP`이 됐습니다. 원본에서는 이 원인을 찾는 데 7분이 들었고 그 7분이 그대로 요금이 됐습니다. 그 뒤로 비밀번호를 `0-bootstrap`으로 옮겼습니다.


### 일부러 깨 보기 ③: 확인을 `127.0.0.1`로 하면 언제나 통과합니다


비밀번호를 맞췄는지는 어떻게 확인할까요? 8월 12일 원본에서 저는 `psql -h 127.0.0.1`로 확인했습니다. 아직 맞추기 전인데도 접속이 성공해서 하마터면 문제가 없다고 결론 낼 뻔했습니다. 이번에도 틀린 비밀번호로 해 보니 똑같이 통과했습니다.


```bash
kubectl exec db-0 -- sh -c "PGPASSWORD=wrong psql -h 127.0.0.1 -U app -d app -tAc 'select 1'"
kubectl exec db-0 -- grep -vE '^\s*(#|$)' /var/lib/postgresql/data/pgdata/pg_hba.conf
```


```plain text
1
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
...
host all all all scram-sha-256
```


postgres 이미지는 컨테이너 안의 소켓뿐 아니라 `127.0.0.1`로 오는 접속도 `trust`로 받습니다. 비밀번호를 실제로 검사하는 줄은 마지막 하나뿐이고 앱처럼 다른 파드에서 오는 접속이 그 줄을 탑니다. 그래서 확인은 파드 자신의 IP로 접속해서 합니다. 동기화 전에는 이 명령이 `password authentication failed`로 실패했고 동기화 뒤에는 심어 둔 값을 돌려줬습니다.


```bash
PODIP=$(kubectl get pod db-0 -o jsonpath='{.status.podIP}')
kubectl exec db-0 -- sh -c "PGPASSWORD=\"\$POSTGRES_PASSWORD\" psql -h $PODIP -U app -d app -tAc 'select note from memo'"
```


---


## 디스크 하나는 백업이 아니라서, 덤프를 떠서 밖에 둡니다


이제 데이터는 클러스터를 부숴도 남습니다. 하지만 디스크가 하나뿐이라 그 디스크가 망가지거나 잘못 지워지면 끝입니다. 관리형 데이터베이스라면 체크박스 하나로 끝났을 백업을 여기서는 직접 해야 합니다. 가장 단순하게는 `pg_dump`로 덤프를 떠서 노트북에 받아 둡니다.


```bash
kubectl exec db-0 -- sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > app.dump
kubectl exec -i db-0 -- pg_restore -l < app.dump | grep TABLE
```


```plain text
217; 1259 16385 TABLE public memo app
3452; 0 16385 TABLE DATA public memo app
```


`pg_dump`를 노트북 대신 파드 안에서 돌리는 것은 버전 때문입니다. `pg_dump`는 자기보다 새 버전의 서버를 덤프하지 못하는데 파드 안에 든 것은 서버와 버전이 같습니다. `-Fc`는 압축된 전용 형식이고 이번 덤프는 1,224바이트였습니다. 덤프는 레포 맨 위 폴더에 생기므로 공개 레포에 올라가지 않게 `.gitignore`에 `*.dump`를 적어 둡니다.


덤프를 검사할 때 `pg_restore -l` 뒤에 `/dev/stdin`을 적으면 안 됩니다. 9월 13일 원본에서 그렇게 했다가 `did not find magic string in file header`를 받았고 이번에도 같았습니다. 파일 이름을 주면 `pg_restore`가 파일처럼 앞뒤로 오가며 읽으려 하는데 파이프는 그럴 수 없어서 생기는 오류입니다. 덤프는 멀쩡하고 깨진 쪽은 검사인데 메시지는 정반대를 가리키는 셈입니다.


### 복구는 지운 것을 먼저 확인해야 증명됩니다


백업이 쓸모 있는지는 되돌려 봐야 압니다. 그런데 되돌린 뒤 값이 있다는 것만으로는 애초에 지워지지 않았던 경우와 구별되지 않습니다. 9월 13일 원본의 복구 연습도 이 순서로 했습니다. 심어 둔 값이 지운 뒤에는 없고 되돌린 뒤에는 있어야 합니다.


```bash
q "drop table memo"
q "select count(*) from pg_tables where tablename='memo'"     # 0
kubectl exec -i db-0 -- sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < app.dump
q "select * from memo"                                        # 9283ed75
```


가운데 줄의 0이 이 연습의 핵심입니다. 그 줄이 없으면 복구가 무엇을 되돌렸는지 아무것도 증명하지 못합니다. 이번에는 0을 본 뒤 `9283ed75`가 돌아왔습니다.


---


## 정리할 때 PVC와 PV는 지워도 디스크는 남습니다


클러스터 쪽 정리 순서는 ⑨편과 같습니다. 다만 이번에는 `Retain` 덕분에 PVC를 지워도 디스크가 지워지지 않습니다. PV는 `Released`로 바뀌어 남고 디스크는 노드에서 떨어져 `available`이 됩니다.


```bash
kubectl delete -f k8s/eso/app-env.yaml -f k8s/eso/secretstore.yaml
kubectl delete -f k8s/app.yaml -f k8s/db.yaml
kubectl delete pvc db-data
kubectl get pv db-data          # STATUS 가 Released
kubectl delete pv db-data
aws ec2 describe-volumes --region ap-northeast-2 --volume-ids "$VOL" --query 'Volumes[0].State' --output text
# available 이 나온 뒤에
cd 2-cluster && tofu destroy && cd ..
```


디스크는 10초쯤 `in-use`로 있다가 `available`이 됐습니다. 그 뒤의 `tofu destroy`는 `19 destroyed`였습니다. 노드 그룹이 지워지는 데 4분 17초가 걸렸는데 워크로드를 띄운 채로 지운 앞의 두 번은 8분이 넘었습니다. 워크로드를 먼저 지운 차이로 보이지만 원인을 따로 확인하지는 못했습니다.


이제는 ⑤편의 확인 명령에 디스크 하나가 나와야 정상입니다. 다음에 클러스터를 세우면 `db-static.yaml`부터 다시 적용해서 같은 디스크를 붙입니다.


`Released`인 PV를 고쳐 다시 쓰는 방법도 있지만 이 시리즈는 PV와 PVC를 매번 지우고 새로 만듭니다. 디스크 ID를 적는 `volumeHandle`은 바꿀 수 없는 필드라서 디스크가 바뀌는 날에는 어차피 새로 만들어야 합니다.


---


## 이 방식은 AZ 하나와 손으로 하는 동기화로 값을 치릅니다


노드가 이제 AZ 하나에만 뜹니다. ⑤편에서 서브넷을 두 AZ에 나눈 것은 한쪽이 멈춰도 다른 쪽에서 버티기 위해서였는데 디스크 하나에 묶이면서 그 여유를 내려놓았습니다. 실습용으로는 괜찮지만 실제 서비스라면 AZ를 넘나들며 복제해 주는 관리형 데이터베이스를 쓰는 편이 맞습니다.


비밀번호 동기화도 사람의 몫으로 남았습니다. 비밀번호를 `0-bootstrap`에 둬서 평소에는 바뀌지 않지만 바꾸고 싶은 날에는 `ALTER USER`를 손으로 해야 합니다. 원본에서는 이 작업을 "한 번만 하면 되는 절차"로 두면 잊는다고 보고 매 세션의 정해진 단계로 넣었습니다.


그리고 백업은 노트북에 받은 파일 하나입니다. 정해진 시간에 자동으로 뜨지도 않고 오래된 것을 지워 주지도 않습니다. 원본에서는 S3 버킷과 스크립트로 이 부분을 채웠지만 이 시리즈에서는 직접 뜨고 되돌리는 연습까지만 합니다.


---


## 정리


| 할 일        | 명령이나 파일                             | 확인                             |
| ---------- | ----------------------------------- | ------------------------------ |
| 디스크 만들기    | `0-bootstrap/db-volume.tf`          | `available`, `ap-northeast-2a` |
| 노드를 같은 AZ로 | `nodes.tf`의 `subnet_ids`            | 노드의 ZONE이 디스크와 같음              |
| 디스크 소개     | `k8s/db-static.yaml` (PV는 `Retain`) | PVC `Bound`, `db-0` Ready      |
| 남았는지 판정    | 심어 둔 값 찾기                           | 다시 세운 뒤 같은 값                   |
| 비밀번호가 다를 때 | 파드 안에서 `ALTER USER`                 | 파드 IP로 접속 성공                   |
| 백업과 복구     | `pg_dump -Fc`, `pg_restore`         | 지운 뒤 0, 되돌린 뒤 같은 값             |


클러스터를 부숴도 데이터가 남게 하려면 디스크를 클러스터 바깥 층에 두고 쿠버네티스는 빌려 쓰기만 해야 합니다. 그리고 디스크 안에 구워진 비밀번호처럼 디스크와 수명이 같아야 하는 것도 디스크와 같은 층에 둡니다.


다음 편에서는 지금까지 `port-forward`로만 들여다본 앱을 바깥에 엽니다. 도메인을 붙이고 HTTPS 인증서를 달아 노트북이 아닌 곳에서도 `hello from eks-lab`을 받아 봅니다.


---


## 참고

- [Amazon EKS 사용 설명서, 정적 프로비저닝](https://docs.aws.amazon.com/eks/latest/userguide/ebs-sample-app.html)
- [Kubernetes Docs, Persistent Volumes, Reclaiming](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#reclaiming)
- [postgres 공식 이미지, 초기화 스크립트와 POSTGRES_PASSWORD](https://hub.docker.com/_/postgres)
- [PostgreSQL Docs, pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html)
- 디스크 단가(gp3, GB당 월 \$0.0912)는 ⑤편에서 AWS Pricing API로 조회한 값입니다.
- 제 원본 작업 일지와 전체 코드는 [switch-job-quest](https://github.com/bangddong/switch-job-quest) 레포에 있습니다. 서비스를 닫으면서 보관(archive)해 두었습니다.
> 이 편의 코드와 매니페스트는 이 글을 위해 새로 쓴 것입니다. 2026년 11월 17일에 ⑨편의 클러스터에 이어 디스크를 만들고, 노드 그룹을 그 AZ로 옮긴 뒤 클러스터를 실제로 부수고 다시 세웠습니다. 위의 출력은 전부 그날 제 계정에서 받은 것입니다. 원본은 디스크 10GiB에 TLS 인증서와 S3 백업 버킷까지 두었지만, 이 시리즈는 1GiB 디스크와 노트북 덤프로 줄였습니다. 비밀번호가 어긋난 일과 7분은 8월 7일, `127.0.0.1` 확인은 8월 12일, 덤프 검사와 복구 순서는 9월 13일 제 일지의 기록입니다. 비용은 ⑨편을 마치고 부순 상태에서 클러스터를 두 번 세우고 부수는 경로를 한 시간 남짓으로 보고 ⑤편의 시간당 \$0.13쯤을 곱해 어림한 값입니다. 막히는 곳이 있으면 알려 주시기 바랍니다.
>
> 이 글의 그림은 AI가 그렸습니다.
>
>
