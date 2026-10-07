# -*- coding: utf-8 -*-
"""AWS EKS 실습기 ①편 Anim.2 · Anim.3.

Anim.2  켜 두기만 해도 열 배가 나갑니다   (일주일, 하루 2시간 실습)
Anim.3  실습에 쓴 돈은 여섯 중 하나였습니다 (실제 청구 $5.87 의 구성)

움직이는 방식과 제약은 anim01-cost-states.py 의 머리말과 같다(SVG 안의 CSS 만 쓴다).

실행:
  python3 scripts/figures/aws-eks/anim02-03-cost.py             # 본편 2장
  python3 scripts/figures/aws-eks/anim02-03-cost.py --frames D  # 다 그려진 상태의 정지 PNG

🔴 숫자의 출처
  Anim.2  ①편 단가표의 합계 $0.1663/h, 다시 만드는 값 $0.07 (sjq docs/eks-cost-model.md)
          켜 둠    168h × 0.1663           = $27.94
          쓸 때만  7일 × (2h × 0.1663 + 0.07) = $2.82
  Anim.3  2026-10-06 Cost Explorer 실측 (sjq docs/eks-migration-log.md 10-06 엔트리)
          컨트롤플레인 2.5750 (25.75h) = 실습 9.95h 0.99 + 잊은 하룻밤 15.8h 1.58 (0.995 는 합이 5.87 이 되도록 0.99 로 적는다) / EC2-Other 2.14 /
          🔴 초판은 0.84 + 1.73 이었다. 09-16 세션의 컨트롤플레인 17.34h 를 통째로 '잊은 시간'으로 셌는데,
             그 세션에는 실습 1.5h 가 들어 있고 방치된 구간은 15.8h 다(일지 09-16 공백표). 발행 전 QA 가 잡았다.
          VPC·ECR·RDS·ELB·시크릿·S3 0.90 / Cost Explorer 0.26 → 합 5.87
"""
import io, subprocess, sys

W = 1120
F = "-apple-system,'Apple SD Gothic Neo','Pretendard','Noto Sans KR',system-ui,sans-serif"
M = "ui-monospace,SFMono-Regular,Menlo,monospace"
INK, SUB, LINE, HOT, OK = "#16202b", "#5a6b7b", "#d9dfe5", "#d13212", "#1d8102"
RATE, REBUILD = 0.1663, 0.07


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


def anim2(static=False):
    H = 540
    always = 168 * RATE
    per_day = 2 * RATE + REBUILD
    ondemand = 7 * per_day
    x0, x1, y0, y1, ymax = 110, 860, 440, 140, 30.0
    X = lambda hours: x0 + (x1 - x0) * hours / 168
    Y = lambda usd: y0 - (y0 - y1) * usd / ymax
    css = """
.ln{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 12s linear infinite}
.end{opacity:0;animation:pop 12s linear infinite}
@keyframes draw{0%{stroke-dashoffset:1}58%,94%{stroke-dashoffset:0}100%{stroke-dashoffset:1}}
@keyframes pop{0%,56%{opacity:0}62%,94%{opacity:1}100%{opacity:0}}
@media (prefers-reduced-motion:reduce){.ln{animation:none;stroke-dashoffset:0}.end{animation:none;opacity:1}}"""
    o = head(H, "일주일 동안 켜 두면 27.94달러, 쓸 때만 켜면 2.82달러가 나갑니다",
             "켜 두기만 해도 열 배가 나갑니다",
             "하루 2시간씩 일주일 동안 실습한다고 해 보겠습니다. 노드 1대 기준이고 클러스터 요금만 셌습니다", css, static)
    for usd in (0, 10, 20, 30):
        o.append(f'<line x1="{x0}" y1="{Y(usd):.1f}" x2="{x1}" y2="{Y(usd):.1f}" stroke="{LINE}"/>')
        o.append(f'<text x="{x0 - 14}" y="{Y(usd) + 5:.1f}" font-size="13" fill="{SUB}" text-anchor="end" font-family="{M}">${usd}</text>')
    for d in range(1, 8):
        o.append(f'<text x="{X(d * 24 - 12):.1f}" y="{y0 + 28}" font-size="13" fill="{SUB}" text-anchor="middle">{d}일째</text>')
    # 쓸 때만 켬: 매일 저녁 2시간 동안만 오른다 (만들고 지우는 값은 그 구간에 얹었다)
    pts, cost = [(X(0), Y(0))], 0.0
    for d in range(7):
        start = d * 24 + 20
        pts.append((X(start), Y(cost)))
        cost += per_day
        pts.append((X(start + 2), Y(cost)))
    pts.append((X(168), Y(cost)))
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    ln = "" if static else ' class="ln" pathLength="1"'
    o.append(f'<path d="M{X(0):.1f},{Y(0):.1f} L{X(168):.1f},{Y(always):.1f}"{ln} fill="none" stroke="{HOT}" stroke-width="4" stroke-linecap="round"/>')
    o.append(f'<path d="{path}"{ln} fill="none" stroke="{OK}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    end = "" if static else ' class="end"'
    lx = x1 + 22
    o.append(f'<g{end}><circle cx="{x1}" cy="{Y(always):.1f}" r="6" fill="{HOT}"/>'
             f'<text x="{lx}" y="{Y(always) - 2:.1f}" font-size="26" font-weight="800" font-family="{M}" fill="{HOT}">${always:.2f}</text>'
             f'<text x="{lx}" y="{Y(always) + 22:.1f}" font-size="14" font-weight="700" fill="{INK}">계속 켜 둔 경우</text>'
             f'<text x="{lx}" y="{Y(always) + 42:.1f}" font-size="13" fill="{SUB}">자는 동안에도 나갑니다</text></g>')
    o.append(f'<g{end}><circle cx="{x1}" cy="{Y(ondemand):.1f}" r="6" fill="{OK}"/>'
             f'<text x="{lx}" y="{Y(ondemand) - 44:.1f}" font-size="26" font-weight="800" font-family="{M}" fill="{OK}">${ondemand:.2f}</text>'
             f'<text x="{lx}" y="{Y(ondemand) - 20:.1f}" font-size="14" font-weight="700" fill="{INK}">쓸 때만 켠 경우</text>'
             f'<text x="{lx}" y="{Y(ondemand):.1f}" font-size="13" fill="{SUB}">매일 만들고 지웁니다</text></g>')
    return foot(o, H, "숫자는 본문의 단가로 계산했습니다. 그림은 AI가 코드로 그렸습니다")


SEG = [  # (이름, 금액, 색, 한 줄 설명)
    ("실습하려고 켠 시간", 0.99, OK, "약 10시간 동안의 컨트롤플레인 요금입니다"),
    ("끄는 걸 잊은 하룻밤", 1.58, HOT, "15.8시간 동안의 컨트롤플레인 요금입니다. 지우는 명령이 멈춘 줄 몰랐습니다"),
    ("세워 둔 볼륨", 2.14, "#e07a10", "대부분 두 달 넘게 보관한 값입니다. 기간이 길수록 늘어납니다"),
    ("그 밖의 리소스", 0.90, "#7d8a97", "IP, 이미지 보관, 로드밸런서, 초반에 잠깐 쓴 RDS"),
    ("청구서를 조회한 값", 0.26, "#3b6fb6", "비용을 확인하는 명령도 한 번에 1센트씩 받습니다"),
]


def anim3(static=False):
    H = 560
    total = sum(s[1] for s in SEG)
    bx, bw, by, bh = 44, W - 88, 130, 56
    css = "".join(
        f".g{i}{{opacity:0;animation:in{i} 14s ease-out infinite}}"
        f"@keyframes in{i}{{0%,{6 + i * 12}%{{opacity:0}}{12 + i * 12}%,95%{{opacity:1}}100%{{opacity:0}}}}"
        for i in range(len(SEG))
    ) + "@media (prefers-reduced-motion:reduce){" + "".join(f".g{i}{{animation:none;opacity:1}}" for i in range(len(SEG))) + "}"
    o = head(H, "총 5.87달러 가운데 실습하는 동안의 컨트롤플레인 요금은 0.99달러입니다",
             "실습에 쓴 돈은 여섯 중 하나였습니다",
             f"제 청구서 ${total:.2f}을 무엇에 썼는지 순서대로 쌓아 보겠습니다", css, static)
    o.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="8" fill="#f1f3f5"/>')
    x = bx
    for i, (name, usd, col, note) in enumerate(SEG):
        w = bw * usd / total
        cls = "" if static else f' class="g{i}"'
        ry = 236 + i * 56
        o.append(f'<g{cls}><rect x="{x:.1f}" y="{by}" width="{w:.1f}" height="{bh}" fill="{col}"/>'
                 f'<text x="{x + w / 2:.1f}" y="{by + 35}" font-size="{15 if w > 70 else 11.5}" font-weight="800" fill="#fff" text-anchor="middle" font-family="{M}">${usd:.2f}</text>'
                 f'<rect x="{bx}" y="{ry - 15}" width="18" height="18" rx="4" fill="{col}"/>'
                 f'<text x="{bx + 32}" y="{ry}" font-size="16.5" font-weight="700" fill="{INK}">{name}</text>'
                 f'<text x="{bx + 250}" y="{ry}" font-size="16.5" font-weight="700" fill="{INK}" font-family="{M}">${usd:.2f}</text>'
                 f'<text x="{bx + 340}" y="{ry}" font-size="14" fill="{SUB}">{note}</text></g>')
        x += w
    return foot(o, H, "2026년 10월 6일에 조회한 실제 청구 내역입니다. 그림은 AI가 코드로 그렸습니다")


if __name__ == "__main__":
    base = "static/images/aws-eks/"
    jobs = (("anim02-always-on", anim2), ("anim03-bill", anim3))
    if "--frames" in sys.argv:
        out = sys.argv[sys.argv.index("--frames") + 1]
        for name, fn in jobs:
            p = f"{out}/{name}.svg"
            io.open(p, "w", encoding="utf-8").write(fn(static=True))
            subprocess.run(["rsvg-convert", "-w", str(W), p, "-o", p.replace(".svg", ".png")], check=True)
            print("wrote", p.replace(".svg", ".png"))
    else:
        for name, fn in jobs:
            io.open(base + name + ".svg", "w", encoding="utf-8").write(fn())
            print("wrote", base + name + ".svg")
