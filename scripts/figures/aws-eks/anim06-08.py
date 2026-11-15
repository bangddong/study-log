# -*- coding: utf-8 -*-
"""AWS EKS 실습기 ⑧편 Anim.6 · ⑨편 Anim.7 · ⑩편 Anim.8.

Anim.6  비밀값은 다섯 칸을 지나 앱에 닿습니다  (⑧편. 서비스 계정 토큰 → 역할 → Secrets Manager → Secret → 환경변수)
Anim.7  디스크는 파드가 자리를 잡은 뒤에 생깁니다  (⑨편. PVC → 스케줄 → 디스크 생성 → Bound → 파드 교체)
Anim.8  클러스터만 부서지고 디스크는 남습니다      (⑩편. 디스크 → 클러스터 → 값 심기 → destroy → 다시 세워 붙이기)

움직이는 방식과 제약은 anim01-cost-states.py 의 머리말과 같다.

실행:
  python3 scripts/figures/aws-eks/anim06-08.py             # 본편
  python3 scripts/figures/aws-eks/anim06-08.py --frames D  # 다 그려진 상태의 정지 PNG

그림의 사실은 2026-11-17 EKS 1.36 클러스터에서 잰 것이다.
Anim.7 의 순서는 PVC 이벤트 네 줄(WaitForFirstConsumer → Provisioning → ExternalProvisioning → ProvisioningSucceeded)과
db-0 을 지운 뒤 UID 만 바뀌고 volumeName 은 같았던 실측에 근거한다.
Anim.8 의 값 9283ed75 는 2026-11-17 왕복에서 실제로 심고 다시 찾은 값이다.
마지막 칸(환경변수는 시작할 때 한 번만 읽는다)은 Secret 값을 바꾼 뒤 앱 안의 값이
rollout restart 전까지 그대로였던 실측에 근거한다.
"""
import io, subprocess, sys

W = 1120
F = "-apple-system,'Apple SD Gothic Neo','Pretendard','Noto Sans KR',system-ui,sans-serif"
M = "ui-monospace,SFMono-Regular,Menlo,monospace"
INK, SUB, LINE, HOT, OK = "#16202b", "#5a6b7b", "#d9dfe5", "#d13212", "#1d8102"


def head(h, label, title, sub, css, static):
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" '
         f'font-family="{F}" role="img" aria-label="{label}">']
    o.append("<style>" + ("" if static else css) + "</style>")
    o.append(f'<rect width="{W}" height="{h}" rx="14" fill="#fff"/>')
    o.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="14" fill="none" stroke="{LINE}"/>')
    o.append(f'<text x="44" y="62" font-size="25" font-weight="700" fill="{INK}">{title}</text>')
    o.append(f'<text x="44" y="92" font-size="14" fill="{SUB}">{sub}</text>')
    return o


def foot(o, h, note):
    o.append(f'<text x="44" y="{h - 28}" font-size="12.5" fill="{SUB}">{note}</text>')
    o.append("</svg>")
    return "\n".join(o)


def wrap(text, width):
    words, line, lines = text.split(" "), "", []
    for w_ in words:
        if line and len(line) + 1 + len(w_) > width:
            lines.append(line)
            line = w_
        else:
            line = (line + " " + w_).strip()
    lines.append(line)
    return lines


def chain(steps, label, title, sub, bottom, static, period=15):
    """상자가 왼쪽부터 하나씩 켜지는 사슬. steps = [(큰 글씨, 작은 글씨, 색)]"""
    H = 420
    n = len(steps)
    step = 80 // n
    css = "".join(
        f".s{i}{{opacity:0;animation:st{i} {period}s ease-out infinite}}"
        f"@keyframes st{i}{{0%,{4 + i * step}%{{opacity:0}}{9 + i * step}%,94%{{opacity:1}}100%{{opacity:0}}}}"
        for i in range(n)
    ) + "@media (prefers-reduced-motion:reduce){" + "".join(f".s{i}{{animation:none;opacity:1}}" for i in range(n)) + "}"
    o = head(H, label, title, sub, css, static)
    gap, y, bh = 26, 140, 160
    bw = (W - 88 - gap * (n - 1)) / n
    x = 44
    for i, (big, small, col) in enumerate(steps):
        cls = "" if static else f' class="s{i}"'
        fill = "#fff5f3" if col == HOT else "#fafbfc"
        o.append(f'<g{cls}>')
        if i:
            ax = x - gap
            o.append(f'<path d="M{ax + 4:.1f},{y + bh / 2} L{ax + gap - 9:.1f},{y + bh / 2}" stroke="{SUB}" stroke-width="2.5"/>'
                     f'<path d="M{ax + gap - 9:.1f},{y + bh / 2 - 6} L{ax + gap - 1:.1f},{y + bh / 2} L{ax + gap - 9:.1f},{y + bh / 2 + 6} z" fill="{SUB}"/>')
        o.append(f'<rect x="{x:.1f}" y="{y}" width="{bw:.1f}" height="{bh}" rx="12" fill="{fill}" stroke="{col}" stroke-width="2"/>'
                 f'<text x="{x + 16:.1f}" y="{y + 32}" font-size="13" font-weight="700" fill="{col}">{i + 1}</text>'
                 f'<text x="{x + 16:.1f}" y="{y + 64}" font-size="16.5" font-weight="700" fill="{INK}">{big}</text>')
        for k, ln in enumerate(wrap(small, 14)):
            o.append(f'<text x="{x + 16:.1f}" y="{y + 92 + k * 19}" font-size="13" fill="{SUB}">{ln}</text>')
        o.append("</g>")
        x += bw + gap
    o.append(f'<text x="44" y="{y + bh + 46}" font-size="14.5" fill="{INK}">{bottom}</text>')
    return foot(o, H, "그림은 AI가 코드로 그렸습니다")


def anim6(static=False):
    steps = [
        ("토큰을 받습니다", "EKS가 ESO 파드에 서비스 계정 토큰을 넣습니다", INK),
        ("역할을 빌립니다", "STS가 토큰의 sub 를 보고 eks-lab-eso 를 빌려줍니다", INK),
        ("값을 읽습니다", "빌린 역할은 eks-lab/app 하나만 읽을 수 있습니다", INK),
        ("Secret을 씁니다", "ESO가 app-env 를 만들고 한 시간마다 맞춥니다", OK),
        ("환경변수가 됩니다", "앱은 시작할 때 한 번만 읽습니다", HOT),
    ]
    return chain(steps,
                 "ESO 파드의 토큰이 STS를 거쳐 역할이 되고, 그 역할로 읽은 값이 Secret을 지나 앱이 시작할 때 환경변수가 됩니다",
                 "비밀값은 다섯 칸을 지나 앱에 닿습니다",
                 "액세스 키는 어디에도 없습니다. 파드가 받은 토큰이 로그인을 대신합니다",
                 "넷째 칸까지는 값이 바뀌면 따라옵니다. 다섯째 칸은 앱을 재시작해야 새 값을 읽습니다.",
                 static)


def anim7(static=False):
    steps = [
        ("PVC를 냅니다", "1GiB를 요청하고 Pending 으로 기다립니다", INK),
        ("파드가 자리를 잡습니다", "노드가 정해지면 AZ 도 정해집니다", INK),
        ("디스크를 만듭니다", "드라이버가 그 AZ 에 gp3 디스크를 만듭니다", INK),
        ("노드에 붙입니다", "PVC 는 Bound, 디스크는 in-use 가 됩니다", OK),
        ("파드가 바뀌어도", "새 db-0 이 같은 PVC 와 같은 디스크를 받습니다", OK),
    ]
    return chain(steps,
                 "PVC가 기다리다가 파드가 노드를 고른 뒤에 그 AZ에 디스크가 생기고, 파드가 바뀌어도 같은 디스크가 붙습니다",
                 "디스크는 파드가 자리를 잡은 뒤에 생깁니다",
                 "StorageClass 의 WaitForFirstConsumer 가 둘째 칸과 셋째 칸의 순서를 정합니다",
                 "디스크를 먼저 만들면 노드와 다른 AZ 에 생길 수 있습니다. EBS 디스크는 다른 AZ 의 노드에 붙지 않습니다.",
                 static)


def anim8(static=False):
    steps = [
        ("디스크를 만듭니다", "0-bootstrap 이 ap-northeast-2a 에 1GiB 를 만듭니다", INK),
        ("클러스터를 세웁니다", "노드도 같은 AZ 에 뜨고 PV 가 디스크를 소개합니다", INK),
        ("값을 심습니다", "memo 표에 9283ed75 한 줄을 넣습니다", INK),
        ("클러스터를 부숩니다", "19개가 사라지고 디스크는 available 로 남습니다", HOT),
        ("다시 세워 붙입니다", "초기화를 건너뛰고 9283ed75 가 돌아옵니다", OK),
    ]
    return chain(steps,
                 "디스크는 0-bootstrap에 남고 클러스터만 부서졌다가 다시 세워지며, 같은 디스크가 다시 붙어 심어 둔 값이 돌아옵니다",
                 "클러스터만 부서지고 디스크는 남습니다",
                 "넷째 칸에서 tofu destroy 가 지우는 것은 2-cluster 의 state 에 적힌 것뿐입니다",
                 "디스크가 남아도 비밀번호가 바뀌면 앱은 붙지 못합니다. 그래서 비밀번호도 디스크와 같은 층에 둡니다.",
                 static)


if __name__ == "__main__":
    base = "static/images/aws-eks/"
    jobs = (("anim06-secret-path", anim6), ("anim07-pvc-binding", anim7), ("anim08-rebuild", anim8))
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
