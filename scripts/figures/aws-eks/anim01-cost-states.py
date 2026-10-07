# -*- coding: utf-8 -*-
"""AWS EKS 실습기 ①편 Anim.1 — 무엇을 꺼야 요금이 멈추는가.

움직이는 SVG 다. 스크립트 없이 SVG 안의 CSS @keyframes 만으로 12초를 반복한다.
그래서 마크다운의 평범한 이미지(![](...svg))로 넣어도 재생된다. <img> 로 불러온 SVG 는
스크립트는 막히지만 CSS 애니메이션은 돈다. 빌드 의존성이 0 이다(mermaid 를 기각한 이유와 반대).

실행:
  python3 scripts/figures/aws-eks/anim01-cost-states.py            # 움직이는 본편
  python3 scripts/figures/aws-eks/anim01-cost-states.py --frames   # 장면별 정지 PNG (검수용)

🔴 숫자의 출처는 ①편 본문의 단가표 한 곳이다. 여기서 따로 계산하지 않는다.
   컨트롤플레인 0.1000 + ALB 세트 0.0405 + 노드 1대(0.0208)와 퍼블릭 IP(0.005) 0.0258 = 0.1663
"""
import io, subprocess, sys

W, H = 1120, 510
F = "-apple-system,'Apple SD Gothic Neo','Pretendard','Noto Sans KR',system-ui,sans-serif"
M = "ui-monospace,SFMono-Regular,Menlo,monospace"
INK, SUB, LINE = "#16202b", "#5a6b7b", "#d9dfe5"
HOT, OFF, OK = "#d13212", "#c3cad2", "#1d8102"

ROWS = [  # (key, 이름, 설명, 시간당, 어느 장면부터 꺼지나)
    ("cp",   "EKS 컨트롤플레인", "클러스터를 지워야만 멈춥니다", 0.1000, 3),
    ("alb",  "로드밸런서 (ALB)", "Ingress 를 지우면 멈춥니다",   0.0405, 3),
    ("node", "노드 1대 + 퍼블릭 IP", "대수를 0으로 줄이면 멈춥니다", 0.0258, 2),
]
TOTAL = sum(r[3] for r in ROWS)                      # 0.1663
SCENES = [
    (1, "실습 중",            f"${TOTAL:.4f}",                       "전부 켜져 있습니다"),
    (2, "노드를 0대로 줄임",   f"${TOTAL - ROWS[2][3]:.4f}",          f"요금의 {round((TOTAL - ROWS[2][3]) / TOTAL * 100)}%가 그대로 나갑니다"),
    (3, "클러스터를 destroy", "$0",                                  "여기서야 멈춥니다"),
]
BAR_X, BAR_MAX, ROW_Y0, ROW_H = 330, 420, 150, 96


def build(static=None):
    """static=None 이면 애니메이션, 1~3 이면 그 장면의 정지 화면."""
    o = []; e = o.append
    e(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
      f'font-family="{F}" role="img" aria-label="노드를 0대로 줄여도 요금의 대부분이 그대로 나가고, 클러스터를 지워야 0이 된다">')
    css = []
    if static is None:
        # 12초 한 바퀴. 장면 1: 0~30% · 장면 2: 36~63% · 장면 3: 69~96% · 나머지는 전환
        css.append("""
.s1,.s2,.s3,.bar,.rate,.chip{animation-duration:12s;animation-iteration-count:infinite;animation-timing-function:ease-in-out}
.bar{transform-box:fill-box;transform-origin:left center}
@keyframes show1{0%,30%{opacity:1}36%,96%{opacity:0}100%{opacity:1}}
@keyframes show2{0%,30%{opacity:0}36%,63%{opacity:1}69%,100%{opacity:0}}
@keyframes show3{0%,63%{opacity:0}69%,96%{opacity:1}100%{opacity:0}}
@keyframes off2{0%,30%{transform:scaleX(1)}36%,96%{transform:scaleX(0)}100%{transform:scaleX(1)}}
@keyframes off3{0%,63%{transform:scaleX(1)}69%,96%{transform:scaleX(0)}100%{transform:scaleX(1)}}
@keyframes dim2{0%,30%{opacity:1}36%,96%{opacity:.28}100%{opacity:1}}
@keyframes dim3{0%,63%{opacity:1}69%,96%{opacity:.28}100%{opacity:1}}
@keyframes tick{0%{transform:scaleX(0)}100%{transform:scaleX(1)}}
.s1{animation-name:show1}.s2{animation-name:show2;opacity:0}.s3{animation-name:show3;opacity:0}
.bar.o2{animation-name:off2}.bar.o3{animation-name:off3}
.rate.o2{animation-name:dim2}.rate.o3{animation-name:dim3}
.clock{transform-box:fill-box;transform-origin:left center;animation:tick 12s linear infinite}
/* 움직임을 줄이도록 설정한 독자에게는 이 글의 주장인 장면 2 를 정지 화면으로 보여 준다 */
@media (prefers-reduced-motion:reduce){
  .s1,.s2,.s3,.bar,.rate,.clock{animation:none}
  .s1,.s3{opacity:0}.s2{opacity:1}.bar.o2{transform:scaleX(0)}.rate.o2{opacity:.28}.clock{display:none}
}""")
    else:
        for n in (1, 2, 3):
            css.append(f".s{n}{{opacity:{1 if n == static else 0}}}")
        for n in (2, 3):
            if static >= n:
                css.append(f".bar.o{n}{{transform:scaleX(0);transform-box:fill-box;transform-origin:left center}}.rate.o{n}{{opacity:.28}}")
        css.append(".clock{display:none}")
    e("<style>" + "".join(css) + "</style>")
    e(f'<rect width="{W}" height="{H}" rx="14" fill="#fff"/>')
    e(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="none" stroke="{LINE}"/>')
    e(f'<text x="44" y="62" font-size="25" font-weight="700" fill="{INK}">무엇을 꺼야 요금이 멈추는가</text>')
    e(f'<text x="44" y="92" font-size="14" fill="{SUB}">서울 리전 시간당 요금 · 노드 1대 기준 · 세 장면이 12초마다 반복됩니다</text>')

    # 장면 표시 (오른쪽 위). 지금 장면만 진하게 보인다
    for n, label, _, _ in SCENES:
        x = 720 + (n - 1) * 0
        e(f'<g class="s{n}"><rect x="{W - 44 - 300}" y="38" width="300" height="40" rx="20" fill="{INK}"/>'
          f'<text x="{W - 44 - 150}" y="64" font-size="15.5" font-weight="700" fill="#fff" text-anchor="middle">장면 {n} / 3 · {label}</text></g>')

    # 리소스 행
    for i, (key, name, how, rate, off_at) in enumerate(ROWS):
        y = ROW_Y0 + i * ROW_H
        w = BAR_MAX * rate / ROWS[0][3]
        e(f'<text x="44" y="{y + 26}" font-size="17" font-weight="700" fill="{INK}">{name}</text>')
        e(f'<text x="44" y="{y + 50}" font-size="13" fill="{SUB}">{how}</text>')
        e(f'<rect x="{BAR_X}" y="{y + 8}" width="{BAR_MAX}" height="34" rx="6" fill="#f1f3f5"/>')
        e(f'<rect class="bar o{off_at}" x="{BAR_X}" y="{y + 8}" width="{w:.1f}" height="34" rx="6" fill="{HOT}"/>')
        e(f'<text class="rate o{off_at}" x="{BAR_X + BAR_MAX + 18}" y="{y + 32}" font-size="17" font-weight="700" '
          f'font-family="{M}" fill="{INK}">${rate:.4f}</text>')
        if i < len(ROWS) - 1:
            e(f'<line x1="44" y1="{y + ROW_H - 14}" x2="{BAR_X + BAR_MAX + 110}" y2="{y + ROW_H - 14}" stroke="{LINE}"/>')

    # 합계 (오른쪽)
    px = 900
    e(f'<rect x="{px - 20}" y="{ROW_Y0 - 14}" width="{W - px - 24}" height="{ROW_H * 3 - 6}" rx="12" fill="#fafbfc" stroke="{LINE}"/>')
    e(f'<text x="{px}" y="{ROW_Y0 + 22}" font-size="13.5" fill="{SUB}">지금 나가는 돈</text>')
    for n, _, total, note in SCENES:
        col = OK if n == 3 else HOT
        e(f'<g class="s{n}"><text x="{px}" y="{ROW_Y0 + 86}" font-size="{50 if n == 3 else 34}" font-weight="800" '
          f'font-family="{M}" fill="{col}">{total}</text>'
          f'<text x="{px}" y="{ROW_Y0 + 116}" font-size="13.5" fill="{SUB}">시간당</text>'
          + "".join(f'<text x="{px}" y="{ROW_Y0 + 168 + k * 22}" font-size="14.5" font-weight="700" fill="{INK}">{ln}</text>'
                    for k, ln in enumerate(wrap(note, 11))) + "</g>")

    # 아래: 한 바퀴 진행 막대
    e(f'<rect x="44" y="{H - 62}" width="{W - 88}" height="4" rx="2" fill="#eef1f4"/>')
    e(f'<rect class="clock" x="44" y="{H - 62}" width="{W - 88}" height="4" rx="2" fill="{INK}"/>')
    e(f'<text x="44" y="{H - 30}" font-size="12.5" fill="{SUB}">수치는 본문 단가표와 같습니다 · 작도는 AI 가 코드로 했습니다</text>')
    e("</svg>")
    return "\n".join(o)


def wrap(s, n):
    """공백 기준으로 n 글자 안팎에서 줄을 나눈다 (SVG 는 자동 줄바꿈이 없다)."""
    out, cur = [], ""
    for w in s.split(" "):
        if cur and len(cur) + 1 + len(w) > n:
            out.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    return out + [cur]


if __name__ == "__main__":
    base = "static/images/aws-eks/anim01-cost-states"
    if "--frames" in sys.argv:
        out = sys.argv[sys.argv.index("--frames") + 1]
        for n in (1, 2, 3):
            p = f"{out}/scene{n}.svg"
            io.open(p, "w", encoding="utf-8").write(build(static=n))
            subprocess.run(["rsvg-convert", "-w", str(W), p, "-o", p.replace(".svg", ".png")], check=True)
            print("wrote", p.replace(".svg", ".png"))
    else:
        io.open(base + ".svg", "w", encoding="utf-8").write(build())
        print("wrote", base + ".svg")
