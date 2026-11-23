# -*- coding: utf-8 -*-
"""AWS EKS 실습기 ⑪편 Anim.9 · ⑫편 Anim.10.

Anim.9   주문서가 로드밸런서가 되기까지      (⑪편. Ingress → 컨트롤러 → ALB → 파드 IP 타겟 → 443 인증서)
Anim.10  replicas 한 칸을 둘이 고쳐 씁니다   (⑫편. HPA 가 늘림 → ArgoCD 가 git 대로 되돌림 → 반복 → 재시도 간격 → 칸을 뺌)
Anim.11  창은 세 겹으로 닫힙니다            (⑬편. 임대 → KV until → Worker 가 Fly 로 → EventBridge 감시 → destroy·off-verify)

상자 사슬은 anim06-08.py 의 chain() 을 그대로 쓴다. 움직이는 방식과 제약은 anim01-cost-states.py 의 머리말과 같다.

실행:
  python3 scripts/figures/aws-eks/anim09.py             # 본편
  python3 scripts/figures/aws-eks/anim09.py --frames D  # 다 그려진 상태의 정지 PNG

그림의 사실은 제 원본 서비스의 2026-09-11(ALB), 2026-09-16(HTTPS), 2026-10-16(재현) 일지에 근거한다.
ADDRESS 가 20초 만에 채워지고, 타겟이 파드 IP 로 등록되고, HTTP 가 301 로 돌아간 것이 그날의 실측이다.
Anim.10 은 2026-10-13 ArgoCD 세션의 실측이다. 3분 동안 둘째 파드가 4번 새로 만들어졌고,
재시도 간격이 41초에서 2분 41초로 늘었으며, git 에서 /spec/replicas 를 빼자 되돌림이 멈췄다.
Anim.11 은 2026-10-22~29 평일 창 일지에 근거한다. KV 값 {target, until}, until 경과 시 Fly,
EventBridge 첫 회차 10초·17초, off 의 240초 배수 대기와 off-verify 가 그 기록이다.
"""
import importlib.util, io, os, subprocess, sys

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("anim0608", os.path.join(_here, "anim06-08.py"))
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
chain, INK, OK, HOT, W = _base.chain, _base.INK, _base.OK, _base.HOT, _base.W


def anim9(static=False):
    steps = [
        ("Ingress를 냅니다", "주문서만 생깁니다. 아직 아무 일도 없습니다", INK),
        ("컨트롤러가 읽습니다", "빌린 역할로 AWS API 를 부릅니다", INK),
        ("ALB를 세웁니다", "elb 태그가 붙은 두 서브넷에 섭니다", INK),
        ("파드 IP를 등록합니다", "노드를 건너뛰고 파드로 바로 보냅니다", OK),
        ("HTTPS로 받습니다", "443 에서 인증서를 내고 80 은 301 로 돌려보냅니다", OK),
    ]
    return chain(steps,
                 "Ingress를 적용하면 컨트롤러가 그것을 읽고 ALB를 세운 뒤 파드 IP를 타겟으로 등록하며, 443 리스너가 인증서를 냅니다",
                 "주문서가 로드밸런서가 되기까지",
                 "첫째 칸만 사람이 하고, 나머지 네 칸은 컨트롤러가 합니다",
                 "kubectl apply 가 성공해도 ALB 가 생긴 것은 아닙니다. 둘째 칸부터의 실패는 describe ingress 에서 찾습니다.",
                 static)


def anim10(static=False):
    steps = [
        ("HPA가 2로 올립니다", "최소 파드 수를 2로 바꾼 커밋이 반영됐습니다", INK),
        ("ArgoCD가 되돌립니다", "git 에 적힌 replicas: 1 로 맞춥니다", HOT),
        ("다시 2, 다시 1", "3분 동안 둘째 파드가 4번 새로 만들어졌습니다", HOT),
        ("간격만 늘어납니다", "재시도 간격이 41초에서 2분 41초가 됩니다", INK),
        ("칸을 빼면 멈춥니다", "git 에서 replicas 를 지우자 되돌림이 사라졌습니다", OK),
    ]
    return chain(steps,
                 "HPA가 파드 수를 2로 올리면 ArgoCD가 git에 적힌 1로 되돌리고, 이것이 반복되다가 git에서 replicas 칸을 빼자 멈춥니다",
                 "replicas 한 칸을 둘이 고쳐 씁니다",
                 "HPA 는 지표를, ArgoCD 는 git 을 정답으로 봅니다. 둘 다 자기 일을 제대로 하고 있습니다",
                 "넷째 칸에서 멈춘 것처럼 보여도 끝난 것이 아닙니다. 한 칸의 주인을 하나로 정해야 끝납니다.",
                 static)


def anim11(static=False):
    steps = [
        ("임대를 적습니다", "창을 열기 전에 언제까지인지 먼저 남깁니다", INK),
        ("스위치에 until", "KV 값은 target 과 until 두 칸입니다", INK),
        ("시각이 지나면 Fly", "끄는 작업이 실패해도 사용자는 돌아옵니다", OK),
        ("매시 감시합니다", "EventBridge 가 임대가 끝난 클러스터를 찾습니다", OK),
        ("부수고 확인합니다", "240초 기다린 뒤 지우고 남은 것이 0인지 봅니다", OK),
    ]
    return chain(steps,
                 "창을 열기 전에 임대를 적고, 트래픽 스위치는 임대 시각이 지나면 스스로 Fly로 돌아가며, 매시 감시 작업이 남은 클러스터를 부숩니다",
                 "창은 세 겹으로 닫힙니다",
                 "사람이 끄는 것을 잊어도, 끄는 작업이 실패해도 닫히게 만들었습니다",
                 "셋째 칸은 사용자를, 넷째와 다섯째 칸은 요금을 지킵니다. 하나가 실패해도 다른 하나가 닫습니다.",
                 static)


if __name__ == "__main__":
    base = "static/images/aws-eks/"
    jobs = (("anim09-ingress", anim9), ("anim10-replicas-fight", anim10), ("anim11-window-close", anim11))
    if "--frames" in sys.argv:
        out = sys.argv[sys.argv.index("--frames") + 1]
        for name, fn in jobs:
            p = f"{out}/{name}.svg"
            io.open(p, "w", encoding="utf-8").write(fn(static=True))
            subprocess.run(["rsvg-convert", "-w", str(W), p, "-o", p.replace(".svg", ".png")], check=True)
    else:
        for name, fn in jobs:
            io.open(base + name + ".svg", "w", encoding="utf-8").write(fn())
    print("done")
