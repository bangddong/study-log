# -*- coding: utf-8 -*-
"""AWS EKS 실습기 ⑪편 Anim.9.

Anim.9   주문서가 로드밸런서가 되기까지      (⑪편. Ingress → 컨트롤러 → ALB → 파드 IP 타겟 → 443 인증서)

상자 사슬은 anim06-08.py 의 chain() 을 그대로 쓴다. 움직이는 방식과 제약은 anim01-cost-states.py 의 머리말과 같다.

실행:
  python3 scripts/figures/aws-eks/anim09.py             # 본편
  python3 scripts/figures/aws-eks/anim09.py --frames D  # 다 그려진 상태의 정지 PNG

그림의 사실은 제 원본 서비스의 2026-09-11(ALB), 2026-09-16(HTTPS), 2026-10-16(재현) 일지에 근거한다.
ADDRESS 가 20초 만에 채워지고, 타겟이 파드 IP 로 등록되고, HTTP 가 301 로 돌아간 것이 그날의 실측이다.
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


if __name__ == "__main__":
    base = "static/images/aws-eks/"
    jobs = (("anim09-ingress", anim9),)
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
