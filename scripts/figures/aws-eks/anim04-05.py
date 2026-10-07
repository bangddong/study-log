# -*- coding: utf-8 -*-
"""AWS EKS 실습기 ②편 Anim.4 · ③편 Anim.5.

Anim.4  버튼 하나가 크레딧까지 이어집니다        (②편. Identity Center → 조직 → 유료 플랜 → 크레딧 만료)
Anim.5  크레딧을 빼고 재면 알림은 울리지 않습니다  (③편. 같은 지출을 두 가지 방식으로 잰 예산)

움직이는 방식과 제약은 anim01-cost-states.py 의 머리말과 같다.

실행:
  python3 scripts/figures/aws-eks/anim04-05.py             # 본편
  python3 scripts/figures/aws-eks/anim04-05.py --frames D  # 다 그려진 상태의 정지 PNG

🔴 Anim.5 의 곡선은 **설명용 예시**다. 실제 청구 기록이 아니다(그림 안에 그렇게 적는다).
   고정된 사실은 둘뿐이다: 첫 알림 선이 $10 이라는 것, 크레딧이 남아 있는 동안 순액은 $0 이라는 것.
   Anim.4 의 인과는 콘솔 확인 화면의 경고문(sjq docs/eks-migration-log.md 07-16)에 근거한다.
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


STEPS = [  # (큰 글씨, 작은 글씨, 색)
    ("Identity Center를 켭니다", "AWS가 권하는 로그인 방식입니다", INK),
    ("조직이 함께 만들어집니다", "Identity Center가 조직을 필요로 합니다", INK),
    ("유료 플랜으로 바뀝니다", "조직을 만들면 무료 플랜에서 벗어납니다", "#e07a10"),
    ("크레딧이 만료됩니다", "확인 화면의 경고문에 그렇게 적혀 있습니다", HOT),
]


def anim4(static=False):
    H = 400
    n = len(STEPS)
    css = "".join(
        f".s{i}{{opacity:0;animation:st{i} 14s ease-out infinite}}"
        f"@keyframes st{i}{{0%,{4 + i * 16}%{{opacity:0}}{10 + i * 16}%,94%{{opacity:1}}100%{{opacity:0}}}}"
        for i in range(n)
    ) + "@media (prefers-reduced-motion:reduce){" + "".join(f".s{i}{{animation:none;opacity:1}}" for i in range(n)) + "}"
    o = head(H, "Identity Center를 켜면 조직이 만들어지고, 유료 플랜으로 바뀌고, 크레딧이 만료됩니다",
             "버튼 하나가 크레딧까지 이어집니다",
             "로그인 방식을 고른 것뿐인데, 세 단계 뒤에 크레딧이 걸려 있습니다", css, static)
    bw, gap, y, bh = 232, 34, 150, 130
    x = 44
    for i, (big, small, col) in enumerate(STEPS):
        cls = "" if static else f' class="s{i}"'
        fill = "#fff5f3" if col == HOT else "#fafbfc"
        o.append(f'<g{cls}>')
        if i:
            ax = x - gap
            o.append(f'<path d="M{ax + 6},{y + bh / 2} L{ax + gap - 10},{y + bh / 2}" stroke="{SUB}" stroke-width="2.5"/>'
                     f'<path d="M{ax + gap - 10},{y + bh / 2 - 7} L{ax + gap - 1},{y + bh / 2} L{ax + gap - 10},{y + bh / 2 + 7} z" fill="{SUB}"/>')
        o.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="12" fill="{fill}" stroke="{col}" stroke-width="2"/>'
                 f'<text x="{x + 18}" y="{y + 34}" font-size="13" font-weight="700" fill="{col}">{i + 1}</text>'
                 f'<text x="{x + 18}" y="{y + 68}" font-size="16.5" font-weight="700" fill="{INK}">{big}</text>')
        words, line, lines = small.split(" "), "", []
        for w_ in words:
            if line and len(line) + 1 + len(w_) > 17:
                lines.append(line); line = w_
            else:
                line = (line + " " + w_).strip()
        lines.append(line)
        for k, ln in enumerate(lines):
            o.append(f'<text x="{x + 18}" y="{y + 94 + k * 19}" font-size="13" fill="{SUB}">{ln}</text>')
        o.append("</g>")
        x += bw + gap
    o.append(f'<text x="44" y="{y + bh + 44}" font-size="14.5" fill="{INK}">첫 번째 칸의 버튼에는 크레딧 이야기가 없습니다. 경고는 확인 화면까지 가야 보입니다.</text>')
    return foot(o, H, "그림은 AI가 코드로 그렸습니다")


def anim5(static=False):
    H = 540
    x0, x1, y0, y1, ymax = 110, 860, 440, 140, 16.0
    X = lambda t: x0 + (x1 - x0) * t
    Y = lambda usd: y0 - (y0 - y1) * usd / ymax
    css = """
.ln{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 12s linear infinite}
.bell{opacity:0;animation:ring 12s linear infinite}
.end{opacity:0;animation:pop 12s linear infinite}
@keyframes draw{0%{stroke-dashoffset:1}60%,94%{stroke-dashoffset:0}100%{stroke-dashoffset:1}}
@keyframes ring{0%,44%{opacity:0}48%,94%{opacity:1}100%{opacity:0}}
@keyframes pop{0%,58%{opacity:0}64%,94%{opacity:1}100%{opacity:0}}
@media (prefers-reduced-motion:reduce){.ln{animation:none;stroke-dashoffset:0}.bell,.end{animation:none;opacity:1}}"""
    o = head(H, "같은 지출도 크레딧을 빼고 재면 0에 붙어 있고, 크레딧 전 금액으로 재면 10달러 선을 넘어 알림이 울립니다",
             "크레딧을 빼고 재면 알림은 울리지 않습니다",
             "같은 지출을 두 가지 방식으로 잰 예산입니다. 곡선은 설명을 위한 예시이고 실제 기록이 아닙니다", css, static)
    for usd in (0, 5, 10, 15):
        o.append(f'<line x1="{x0}" y1="{Y(usd):.1f}" x2="{x1}" y2="{Y(usd):.1f}" stroke="{LINE}"/>')
        o.append(f'<text x="{x0 - 14}" y="{Y(usd) + 5:.1f}" font-size="13" fill="{SUB}" text-anchor="end" font-family="{M}">${usd}</text>')
    o.append(f'<line x1="{x0}" y1="{Y(10):.1f}" x2="{x1}" y2="{Y(10):.1f}" stroke="{INK}" stroke-width="1.5" stroke-dasharray="6 5"/>')
    o.append(f'<text x="{x0 + 8}" y="{Y(10) - 8:.1f}" font-size="13" font-weight="700" fill="{INK}">첫 알림 선 $10</text>')
    o.append(f'<text x="{(x0 + x1) / 2}" y="{y0 + 30}" font-size="13" fill="{SUB}" text-anchor="middle">시간이 지나며 쓴 돈이 쌓입니다 →</text>')
    ln = "" if static else ' class="ln" pathLength="1"'
    end_usd = 14.0
    o.append(f'<path d="M{X(0):.1f},{Y(0):.1f} L{X(1):.1f},{Y(end_usd):.1f}"{ln} fill="none" stroke="{OK}" stroke-width="4" stroke-linecap="round"/>')
    o.append(f'<path d="M{X(0):.1f},{Y(0.12):.1f} L{X(1):.1f},{Y(0.12):.1f}"{ln} fill="none" stroke="{HOT}" stroke-width="4" stroke-linecap="round"/>')
    cross = 10 / end_usd
    bell = "" if static else ' class="bell"'
    o.append(f'<g{bell}><circle cx="{X(cross):.1f}" cy="{Y(10):.1f}" r="9" fill="#fff" stroke="{OK}" stroke-width="3"/>'
             f'<rect x="{X(cross) - 62:.1f}" y="{Y(10) - 58:.1f}" width="124" height="34" rx="17" fill="{OK}"/>'
             f'<text x="{X(cross):.1f}" y="{Y(10) - 36:.1f}" font-size="14.5" font-weight="700" fill="#fff" text-anchor="middle">알림이 옵니다</text></g>')
    end = "" if static else ' class="end"'
    lx = x1 + 22
    o.append(f'<g{end}><text x="{lx}" y="{Y(end_usd) + 2:.1f}" font-size="15" font-weight="700" fill="{OK}">크레딧 전 금액으로 잼</text>'
             f'<text x="{lx}" y="{Y(end_usd) + 23:.1f}" font-size="13" fill="{SUB}" font-family="{M}">include_credit = false</text>'
             f'<text x="{lx}" y="{Y(end_usd) + 43:.1f}" font-size="13" fill="{SUB}">쓴 만큼 올라갑니다</text></g>')
    o.append(f'<g{end}><text x="{lx}" y="{Y(0.12) - 44:.1f}" font-size="15" font-weight="700" fill="{HOT}">크레딧을 빼고 잼</text>'
             f'<text x="{lx}" y="{Y(0.12) - 23:.1f}" font-size="13" fill="{SUB}">크레딧이 지출을 지웁니다</text>'
             f'<text x="{lx}" y="{Y(0.12) - 3:.1f}" font-size="13" fill="{SUB}">크레딧이 남은 동안 $0</text></g>')
    return foot(o, H, "곡선은 예시입니다. 그림은 AI가 코드로 그렸습니다")


if __name__ == "__main__":
    base = "static/images/aws-eks/"
    jobs = (("anim04-credit-chain", anim4), ("anim05-budget-credit", anim5))
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
