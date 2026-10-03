# -*- coding: utf-8 -*-
"""AWS EKS 실습기 ①편 Fig.1 — 구성과 돈이 나가는 지점.

준비 (한 번만):
  mkdir -p ~/.cache/aws-architecture-icons && cd $_
  curl -sSL -o icons.zip "<https://aws.amazon.com/architecture/icons/ 의 Icon-package zip>"
  unzip -q icons.zip -d pkg && rm -rf pkg/__MACOSX     # svg 1852개

  🔴 /tmp 에 풀지 마라. 긴 세션 중에 통째로 정리돼 패키지가 사라졌다(2026-10-03 실측).

실행:
  python3 scripts/figures/aws-eks/fig01-cost-map.py
  qlmanage -t -s 1120 -o static/images/aws-eks static/images/aws-eks/fig01-cost-map.svg

아이콘: AWS Architecture Icons (https://aws.amazon.com/architecture/icons/)
  AWS 가 "아키텍처 다이어그램 작성" 용도로 배포한다. 다이어그램을 **직접 그리는 데**만 쓴다.
  AWS 문서의 완성 다이어그램을 퍼오지 않는다(그쪽은 근거가 없다).

🔴 Pod 은 AWS 서비스가 아니라 쿠버네티스 개념이다. AWS 아이콘을 붙이면 거짓말이 되므로
   라벨 박스로 그린다. 초판에서 ECS 컨테이너 아이콘을 썼다가 고쳤다.
"""
import io, os, re

P = os.environ.get("AWS_ICONS", os.path.expanduser("~/.cache/aws-architecture-icons/pkg"))
S, R, G = (f"{P}/Architecture-Service-Icons_07312026",
           f"{P}/Resource-Icons_07312026", f"{P}/Architecture-Group-Icons_07312026")
I = {
 "eks": f"{S}/Arch_Containers/64/Arch_Amazon-Elastic-Kubernetes-Service_64.svg",
 "elb": f"{S}/Arch_Networking-Content-Delivery/64/Arch_Elastic-Load-Balancing_64.svg",
 "ec2": f"{S}/Arch_Compute/64/Arch_Amazon-EC2_64.svg",
 "ebs": f"{S}/Arch_Storage/64/Arch_Amazon-Elastic-Block-Store_64.svg",
 "ecr": f"{S}/Arch_Containers/64/Arch_Amazon-Elastic-Container-Registry_64.svg",
 "s3":  f"{S}/Arch_Storage/64/Arch_Amazon-Simple-Storage-Service_64.svg",
 "acm": f"{S}/Arch_Security-Identity/64/Arch_AWS-Certificate-Manager_64.svg",
 "bud": f"{S}/Arch_Cloud-Financial-Management/64/Arch_AWS-Budgets_64.svg",
 "igw": f"{R}/Res_Networking-Content-Delivery/Res_Amazon-VPC_Internet-Gateway_48.svg",
 "cloud": f"{G}/AWS-Cloud_32.svg", "vpc": f"{G}/Virtual-private-cloud-VPC_32.svg",
}
# 🔴 qlmanage 는 정사각으로 렌더하므로 캔버스도 정사각이어야 한다.
#    아래 여백을 sips 로 잘라 보려 했으나 sips -c 는 --cropOffset 을 줘도 **가운데 기준**이라
#    제목이 날아간다. 자르지 말고 여백을 그대로 둔다.
W = H = 1120
F = "-apple-system,'Apple SD Gothic Neo','Pretendard','Noto Sans KR',system-ui,sans-serif"
M = "ui-monospace,SFMono-Regular,Menlo,monospace"
K8S = "#326ce5"          # 쿠버네티스 파랑. AWS 리소스가 아닌 것은 이 색으로 통일한다
HOT, WARM = "#d13212", "#ff9900"

# 🔴 그리기 전에 아이콘 경로를 전수 확인한다. 중간에 터지면 어디까지 그려졌는지 알 수 없고,
#    패키지가 통째로 사라진 적이 있다(/tmp 정리).
_missing = [f"{k}: {v}" for k, v in I.items() if not os.path.exists(v)]
if _missing:
    raise SystemExit("아이콘을 찾을 수 없습니다. AWS_ICONS 를 확인하세요.\n  " + "\n  ".join(_missing))

o = []; e = o.append; _c = {}

def ico(k, x, y, sz):
    """🔴 반환만 하면 호출부가 append 를 잊는다. 실제로 잊어서 아이콘 14개가 통째로 사라졌다."""
    if k not in _c:
        t = io.open(I[k], encoding="utf-8").read()
        t = re.sub(r"<\?xml.*?\?>", "", t, flags=re.S)
        t = re.sub(r"<title>.*?</title>", "", t, flags=re.S)
        m = re.search(r'viewBox="([^"]+)"', t)
        body = re.sub(r"^.*?<svg[^>]*>", "", t, flags=re.S)
        _c[k] = (m.group(1) if m else "0 0 80 80", re.sub(r"</svg>\s*$", "", body, flags=re.S))
    vb, b = _c[k]
    e(f'<svg x="{x}" y="{y}" width="{sz}" height="{sz}" viewBox="{vb}">{b}</svg>')

def txt(x, y, s, sz=14, w=400, fill="#16191f", font=F, anchor="start"):
    e(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{sz}" font-weight="{w}" '
      f'fill="{fill}" text-anchor="{anchor}">{s}</text>')

def box(x, y, w, h, stroke, dash="", fill="none", rx=8, sw=2):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    e(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
      f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

def cost(x, y, s, hot=True):
    c = HOT if hot else WARM
    e(f'<rect x="{x}" y="{y}" width="{len(s)*7.4+40}" height="22" rx="11" fill="{c}"/>')
    txt(x + 9, y + 16, f"💰 {s}", 12, 700, "#fff", font=M)

def pod(x, y, label, note=""):
    """Pod 은 쿠버네티스 개념이라 AWS 아이콘을 쓰지 않는다."""
    box(x, y, 118, 46, K8S, fill="#f2f7fe", rx=10, sw=1.8)
    txt(x + 59, y + 22, label, 13, 700, K8S, anchor="middle")
    txt(x + 59, y + 38, note or "Pod", 10.5, 400, "#6b7f99", anchor="middle", font=M)

def arrow(x1, y1, x2, y2):
    e(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#5a6b7b" stroke-width="2.5" '
      f'marker-end="url(#a)"/>')

e(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
e('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
  'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5a6b7b"/></marker></defs>')
e(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

txt(44, 50, "이 시리즈로 만드는 구성과 돈이 나가는 지점", 25, 700)
txt(44, 78, "서울 리전 · 💰 빨강은 시간당 과금, 주황은 월 과금 · 파란 상자는 쿠버네티스 개념(AWS 리소스 아님)",
    13.5, 400, "#5a6b7b")

# 사용자도 AWS 리소스가 아니므로 라벨로 그린다 (Pod 과 같은 규칙)
box(40, 298, 104, 46, "#5a6b7b", fill="#f6f7f8", rx=10, sw=1.8)
txt(92, 327, "사용자", 14, 700, "#5a6b7b", anchor="middle")
arrow(152, 321, 172, 321)

box(180, 104, 900, 712, "#232f3e")                      # AWS Cloud
ico("cloud", 196, 118, 26); txt(230, 138, "AWS 클라우드", 15, 700, "#232f3e")

box(208, 158, 840, 408, "#8c4fff", dash="7 5")          # VPC
ico("vpc", 224, 172, 24); txt(256, 190, "VPC  10.0.0.0/16", 14, 700, "#8c4fff")

# 왼쪽 열 — 트래픽 경로
ico("igw", 236, 212, 38); txt(284, 236, "인터넷 게이트웨이", 13, 500)
arrow(255, 256, 255, 282)
ico("elb", 232, 286, 48); txt(290, 306, "Application Load Balancer", 14, 600)
cost(290, 316, "$0.0405/h")
ico("acm", 560, 288, 40); txt(610, 306, "ACM 인증서", 13.5, 600)
txt(610, 324, "HTTPS · $0 · ⑪편", 11.5, 400, "#5a6b7b", font=M)
arrow(256, 346, 256, 376)

box(228, 380, 420, 164, "#00a4a6", dash="5 4")          # 퍼블릭 서브넷
txt(244, 404, "퍼블릭 서브넷 · NAT 게이트웨이를 쓰지 않습니다 (월 $32 회피)", 12, 600, "#00a4a6")
ico("ec2", 244, 414, 44); txt(298, 436, "EC2 노드  t4g.small", 13.5, 600)
cost(298, 446, "$0.0208/h")
pod(246, 484, "앱", "Pod")
arrow(370, 507, 398, 507)
pod(404, 484, "DB", "StatefulSet · ⑨편")

# 오른쪽 열 — 컨트롤플레인
box(672, 376, 356, 170, HOT, fill="#fff5f3")
ico("eks", 696, 396, 52); txt(760, 418, "EKS 컨트롤플레인", 16, 700)
txt(760, 438, "AWS 가 관리합니다", 12.5, 400, "#5a6b7b")
cost(696, 458, "$0.10/h  =  월 $73")
txt(696, 508, "노드가 0대여도 계속 나가고,", 12.5, 600, HOT)
txt(696, 528, "클러스터를 지워야만 멈춥니다.", 12.5, 700, HOT)

# 영속 레이어
box(208, 592, 840, 192, "#7aa116", dash="7 5")
txt(228, 618, "영속 레이어 · 클러스터를 부숴도 남습니다", 15, 700, "#7aa116")
ico("ebs", 232, 636, 46); txt(288, 660, "EBS 볼륨 10GB", 14, 600)
cost(288, 670, "$0.91/월", hot=False)
txt(288, 718, "⑩편. 데이터가 여기 남습니다", 12, 400, "#5a6b7b")
for key, x, name, sub in (("ecr", 560, "ECR", "이미지 보관"),
                          ("s3", 740, "S3 · DynamoDB", "tfstate"),
                          ("bud", 930, "예산 알림", "③편")):
    ico(key, x, 636, 44); txt(x + 54, 660, name, 13.5, 600); txt(x + 54, 678, sub, 11.5, 400, "#5a6b7b")
txt(560, 718, "이 셋은 사실상 $0 입니다", 12, 400, "#5a6b7b")

txt(44, 866, "실습이 끝나면 VPC 안쪽을 전부 destroy 합니다. 남는 것은 초록 상자뿐이고 월 $1 남짓입니다.",
    14.5, 500)
txt(44, 898, "시간당  합계  $0.1405/h   =   파드를 하나도 안 띄워도 나가는 돈 (전체의 60%)",
    13.5, 700, HOT, font=M)
txt(44, 952, "아이콘: AWS Architecture Icons (https://aws.amazon.com/architecture/icons/)",
    12, 400, "#879196")
txt(44, 974, "수치는 실제 청구·실행 기록 · 작도는 AI 가 코드로 했습니다", 12, 400, "#879196")
e("</svg>")

out = "static/images/aws-eks/fig01-cost-map.svg"
io.open(out, "w", encoding="utf-8").write("\n".join(o))
print("wrote", out)
