#!/usr/bin/env python3
"""문장 리듬 측정기 — study-log 발행분을 기준선으로 초안을 채점한다.

왜 이 스크립트가 있나 (2026-10-01):
  writing-style.md 가 "문장 평균 34.7~39.0자"만 적고 **분산을 적지 않아서**,
  평균에 수렴한 단조로운 초안이 규칙을 전부 통과했다. 평균은 리듬을 구분하지 못한다.
  → 기준선을 발행분에서 직접 뽑아 **표준편차까지** 본다.

  ⚠️ 기준은 '공백 포함' 이다. writing-style.md 의 34.7~39.0 은 '공백 제외' 기준이라
     같은 글을 재면 7자쯤 차이가 난다. 기준을 섞어 읽으면 멀쩡한 글을 짧다고 판정한다.

사용:
  python3 check-prose.py <초안.md> [...]                    초안 채점
  python3 check-prose.py --baseline 'contents/posts/**/*.md'  기준선 재계산
  python3 check-prose.py --flow <초안.md> [...]             흐름 프로파일 (문단 기준, EKS 실습기부터)
"""
import io, re, sys, glob, statistics as st, collections

# 발행분 4~7장 실측 (2026-10-01, 공백 포함, 산문만)
# 발행분 Agentic Design Patterns 4~7장, 641문장 (2026-10-01 실측)
BASE = {"mean": 41.1, "sd": 28.0, "conj": 3.3, "top_end": 6.3, "short": 13.6, "long": 9.0}
TOL = {"mean": (36.0, 48.0), "sd": (22.0, None), "conj": (None, 4.0), "top_end": (None, 9.0),
       "short": (6.0, 24.0), "long": (5.0, None)}


def prose(path):
    """산문만 남긴다. frontmatter·코드블록·표·불릿·인용·제목 제외."""
    t = io.open(path, encoding="utf-8").read()
    t = re.sub(r"^---\n.*?\n---\n", "", t, flags=re.S)
    out, inblock = [], False
    for line in t.split("\n"):
        if line.strip().startswith("```"):
            inblock = not inblock
            continue
        if inblock:
            continue
        s = line.strip()
        if not s or s[0] in "#|>" or s.startswith("- ") or s.startswith("* "):
            continue
        out.append(s)
    return re.sub(r"[*`\[\]]", "", "\n".join(out))


def measure(text):
    sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", text) if len(x.strip()) > 3]
    if not sents:
        return None
    ln = [len(x) for x in sents]
    ends = collections.Counter()
    for s in sents:
        m = re.search(r"([가-힣]{2,5})[.!?]$", s)
        ends[m.group(1) if m else "기타"] += 1
    conj = len(re.findall(r"(?:^|[.\n]\s*)(그런데|그래서|그러나|다만|하지만|즉|따라서)", text))
    return {
        "n": len(sents),
        "mean": st.mean(ln),
        "sd": st.pstdev(ln),
        "conj": conj / len(sents) * 100,
        "top_end": ends.most_common(1)[0][1] / len(sents) * 100,
        "short": len([x for x in ln if x <= 20]) / len(sents) * 100,
        "long": len([x for x in ln if x >= 70]) / len(sents) * 100,
        "ends": ends,
        "sents": sents,
    }


def verdict(key, val):
    lo, hi = TOL[key]
    if lo is not None and val < lo:
        return "🔴 낮음"
    if hi is not None and val > hi:
        return "🔴 높음"
    return "✅"


def report(path):
    m = measure(prose(path))
    if not m:
        print(f"{path}: 산문 없음")
        return False
    print(f"\n── {path}  (산문 {m['n']}문장)")
    # 🔴 비율 지표는 표본이 작으면 요동친다. 토막글에 글 전체 기준을 대면 과신이다
    #    (16문장 발췌에서 '70자 이상 37.5%' 가 나왔다. 문장 6개로 만들어진 값이다).
    if m["n"] < 40:
        print(f"   ⚠️ 표본 {m['n']}문장. 비율 지표(짧은/긴/접속부사/최빈어미)는 **참고용**이다.")
        print("      판정은 글 전체(40문장 이상)로 한다. 지금은 평균·표준편차만 신뢰한다.")
    rows = [
        ("문장 평균(공백포함)", m["mean"], BASE["mean"], "자"),
        ("문장 길이 표준편차", m["sd"], BASE["sd"], ""),
        ("접속부사 비율", m["conj"], BASE["conj"], "%"),
        ("최빈 종결어미 비율", m["top_end"], BASE["top_end"], "%"),
    ]
    ok = True
    for label, val, base, unit in rows:
        key = {"문장 평균(공백포함)": "mean", "문장 길이 표준편차": "sd",
               "접속부사 비율": "conj", "최빈 종결어미 비율": "top_end"}[label]
        v = verdict(key, val)
        ok = ok and v == "✅"
        print(f"   {label:<20}{val:>7.1f}{unit:<2}  발행분 {base:>5.1f}{unit:<2} {v}")
    for label, key in (("20자 이하 문장", "short"), ("70자 이상 문장", "long")):
        v = verdict(key, m[key])
        ok = ok and v == "✅"
        print(f"   {label:<20}{m[key]:>7.1f}%   발행분 {BASE[key]:>5.1f}%  {v}")

    # 🔴 처방은 데이터에서 뽑는다. 어느 꼬리가 비었는지 보지 않고 조언하면 틀린다
    #    (첫 구현이 그랬다: 짧은 문장이 이미 많은 초안에 "짧은 문장을 넣어라"를 냈다).
    if m["sd"] < TOL["sd"][0]:
        print("\n   🔴 표준편차가 낮다 = 문장 길이가 한 군데로 몰려 있다.")
        short_short = m["short"] < TOL["short"][0]
        no_long = m["long"] < TOL["long"][0]
        if no_long and not short_short:
            print(f"      빈 쪽은 **긴 문장**이다. 70자 이상이 {m['long']:.1f}% "
                  f"(발행분 {BASE['long']:.1f}%).")
            print("      짧은 문장은 이미 충분하다. 고치는 법은 짧은 문장을 더 넣는 게 아니라,")
            print("      **인접한 짧은 문장 둘을 연결어미로 이어 70자급 한 문장을 만드는 것**이다.")
            print("      `~는데`, `~이고`, `~므로`, `~기 때문에`로 잇고 쉼표·괄호를 함께 쓴다.")
        elif short_short and not no_long:
            print(f"      빈 쪽은 **짧은 문장**이다. 20자 이하가 {m['short']:.1f}% "
                  f"(발행분 {BASE['short']:.1f}%).")
            print("      긴 문장을 쪼개지 말고, 단정하는 한 줄을 문단마다 하나 심는다.")
        else:
            print(f"      양쪽 꼬리가 다 얇다. 짧은 문장 {m['short']:.1f}% / 긴 문장 {m['long']:.1f}%")
            print("      문단마다 '아주 짧은 한 줄 + 길게 흐르는 한 문장'을 짝으로 넣는다.")
        uni = [x for x in m["sents"] if 28 <= len(x) <= 44]
        print(f"      28~44자 구간에 {len(uni)}문장({len(uni)/m['n']*100:.0f}%)이 몰려 있다. 예시 2개:")
        for x in uni[:2]:
            print(f"        [{len(x):>2}] {x[:62]}")
    if m["conj"] > TOL["conj"][1]:
        print("\n   🔴 접속부사가 많다. '그런데/그래서/다만' 을 지우고 문장 자체로 이어라.")
    return ok


def baseline(pattern):
    allsent, alltext = [], ""
    for p in sorted(glob.glob(pattern, recursive=True)):
        t = prose(p)
        alltext += t + "\n"
        allsent += [x for x in re.split(r"(?<=[.!?])\s+", t) if len(x.strip()) > 3]
    m = measure(alltext)
    print(f"기준선 재계산 ({pattern}) — 문장 {m['n']}")
    print(f"  mean {m['mean']:.1f} · sd {m['sd']:.1f} · conj {m['conj']:.1f}% · top_end {m['top_end']:.1f}%")
    print("  → 이 값을 BASE 딕셔너리에 반영할 것")


# ── 흐름 프로파일 (2026-10-07) ─────────────────────────────────────────────
# 위 기준은 **문장** 길이의 분산을 리듬으로 본다. 그 기준을 다 통과한 글이 여전히 딱딱했다.
# 원인은 문장이 아니라 **문단**이었다. 참고 글(kciter.so, 서버 모니터링 분석 가이드, 414문장)과
# 재서 비교하니 문장 표준편차는 참고 글이 오히려 낮고(21.3), 다른 것은 이쪽이었다.
#
#                       참고 글   EKS ①②③ 초판
#   문단당 문장 수        3.9       2.1~2.4      ← 생각 하나를 두 문장 하고 끊었다
#   문단 평균 길이        179자     84~95자
#   20자 이하 문장        7.2%      19~33%       ← 분산을 맞추려고 심은 단정문이 과했다
#   접속어로 시작         14.0%     0~3%         ← 4% 상한이 문장 사이의 논리를 지웠다
#
# 그래서 이 프로파일은 분산을 보지 않고 문단을 본다. 코드나 표를 소개하는 한 줄
# ("확인합니다." 같은 안내문)은 튜토리얼에 꼭 필요하므로 문단 통계에서 뺀다.
FLOW_BASE = {"spp": 3.9, "plen": 179, "short": 7.2, "conj": 14.0, "mean": 45.4}
FLOW_TOL = {"spp": (3.0, None), "plen": (130, None), "short": (None, 12.0), "conj": (5.0, 18.0),
            "mean": (38.0, 52.0), "top_end": (None, 14.0), "mark": (None, 3)}
FLOW_CONJ = ("그런데", "그래서", "하지만", "따라서", "반면", "그리고", "다만", "물론", "즉", "또한", "그러나",
             "그러면", "반대로", "여기서", "이때", "예를 들어", "그다음", "마지막으로", "먼저", "다음으로",
             "대신", "그래도", "결국", "덕분에", "문제는", "참고로")


def flow_paragraphs(path):
    """(문단 텍스트, 안내문 여부) 목록. 안내문 = 바로 뒤에 코드블록·표가 오는 한 문장짜리 문단."""
    t = io.open(path, encoding="utf-8").read()
    t = re.sub(r"^---\n.*?\n---\n", "", t, flags=re.S)
    blocks, inblock = [], False
    for raw in t.split("\n\n"):
        b = raw.strip()
        if not b:
            continue
        fence = b.count("```")
        if inblock:
            if fence % 2 == 1:
                inblock = False
            blocks.append(("other", b))
            continue
        if b.startswith("```"):
            if fence % 2 == 1:
                inblock = True
            blocks.append(("other", b))
        elif b[0] in "#|>" or b.startswith(("- ", "* ", "![", "---")):
            blocks.append(("other", b))
        else:
            blocks.append(("prose", re.sub(r"[*`\[\]]", "", b)))
    out = []
    for i, (kind, b) in enumerate(blocks):
        if kind != "prose":
            continue
        nxt = blocks[i + 1][1] if i + 1 < len(blocks) else ""
        n = len([x for x in re.split(r"(?<=[.!?])\s+", b) if len(x.strip()) > 3])
        out.append((b, n <= 1 and nxt.startswith(("```", "|"))))
    return out


def flow_report(path):
    paras = flow_paragraphs(path)
    body = [b for b, lead in paras if not lead]
    split = lambda b: [x.strip() for x in re.split(r"(?<=[.!?])\s+", b) if len(x.strip()) > 3]
    sents = [x for b, _ in paras for x in split(b)]
    if not body or not sents:
        print(f"{path}: 산문 없음")
        return False
    ends = collections.Counter()
    for x in sents:
        m = re.search(r"([가-힣]{2,5})[.!?]$", x)
        ends[m.group(1) if m else "기타"] += 1
    raw = io.open(path, encoding="utf-8").read()
    v = {
        "spp": st.mean(len(split(b)) for b in body),
        "plen": st.mean(len(b) for b in body),
        "short": len([x for x in sents if len(x) <= 20]) / len(sents) * 100,
        "conj": len([x for x in sents if re.match(r"(?:%s)[ ,]" % "|".join(FLOW_CONJ), x)]) / len(sents) * 100,
        "mean": st.mean(len(x) for x in sents),
        "top_end": ends.most_common(1)[0][1] / len(sents) * 100,
        "mark": len(re.findall("🔴|⚠️", raw)),
    }
    lead = len(paras) - len(body)
    print(f"\n── {path}  [흐름]  문단 {len(body)}개 (+안내문 {lead}) · 문장 {len(sents)}")
    labels = [("spp", "문단당 문장 수", ""), ("plen", "문단 평균 길이", "자"), ("short", "20자 이하 문장", "%"),
              ("conj", "접속어로 시작", "%"), ("mean", "문장 평균", "자"), ("top_end", "최빈 종결어미", "%"),
              ("mark", "경고 표시(🔴⚠️)", "개")]
    ok = True
    for key, label, unit in labels:
        lo, hi = FLOW_TOL[key]
        bad = (lo is not None and v[key] < lo) or (hi is not None and v[key] > hi)
        ok = ok and not bad
        base = f"참고 {FLOW_BASE[key]:>5.1f}" if key in FLOW_BASE else " " * 10
        rng = f"{'' if lo is None else lo}~{'' if hi is None else hi}"
        print(f"   {label:<16}{v[key]:>7.1f}{unit:<2} {base}  허용 {rng:<10} {'🔴' if bad else '✅'}")
    thin = sorted((b for b in body if len(split(b)) <= 2), key=len)[:3]
    if v["spp"] < FLOW_TOL["spp"][0] and thin:
        print("   🔴 문단이 얇다. 생각 하나를 서너 문장에 걸쳐 푼다. 가장 얇은 문단:")
        for b in thin:
            print(f"        [{len(b):>3}자] {b[:60]}")
    if v["short"] > FLOW_TOL["short"][1]:
        print("   🔴 짧은 단정문이 많다. 앞뒤 문장에 이어 붙인다. 예:")
        for x in [x for x in sents if len(x) <= 20][:4]:
            print(f"        {x}")
    return ok


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    if args[0] == "--flow":
        sys.exit(0 if all([flow_report(a) for a in args[1:]]) else 1)
    if args[0] == "--baseline":
        baseline(args[1])
        sys.exit(0)
    sys.exit(0 if all(report(a) for a in args) else 1)
