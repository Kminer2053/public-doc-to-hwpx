"""
normalize_1p_markers.py — 1p 보고서 양식 마커 자동 정규화 (v3.6.11 신규)
────────────────────────────────────────────────────────────────────────
1p 양식 placeholder 별 마커 규칙:

  ◦ 자리 (paraPr=31, heading=NONE): 자동 마커 없음 → ◦ 직접 텍스트 입력 필요
  - 자리 (paraPr=27, heading=BULLET): 자동 - 마커 적용 → 사용자 입력의 "-" 시작 제거
  * 자리 (paraPr=32, heading=NONE): 자동 마커 없음 → * 직접 텍스트 입력 필요

빌더가 사용자 입력 시점에 자동 정규화. 사용자가 어떤 마커로 입력하든 양식과
중복/누락 없이 통일된 결과 보장.
"""

# 1p 양식 placeholder ↔ 자동 마커 prefix 매핑
# (값은 빈 골격의 hp:p paraPr 분석으로 결정)
ONE_P_MARKER_PREFIX = {
    # ◦ 위계 자리 (paraPr=31) — ◦ 직접 추가 필요
    "text_005": "◦ ", "text_006": "◦ ",
    "text_010": "◦ ", "text_011": "◦ ",
    "text_015": "◦ ", "text_016": "◦ ",
    "text_020": "◦ ", "text_021": "◦ ",
    "text_024": "◦ ", "text_025": "◦ ",
    "text_027": "◦ ", "text_028": "◦ ",
    # * 주석 자리 (paraPr=32)
    "text_008": " * ", "text_013": " * ",
    "text_018": " * ", "text_023": " * ",
    "본문_주석_001": " * ", "본문_주석_002": " * ",
}

# 자동 BULLET 마커가 있는 placeholder (paraPr=27) — 사용자 입력의 마커 시작 제거
ONE_P_TRIM_BULLET = {
    "text_007", "text_012", "text_017", "text_022",
    "text_026", "text_029",
}

# 제거할 마커 패턴들 (다양한 입력 허용)
BULLET_PATTERNS = ["- ", "– ", "− ", "—", "-", "–", "−"]
SUBBULLET_PATTERNS = ["◦ ", "○ ", "◇ ", "◦", "○"]
ASTERISK_PATTERNS = ["* ", "※ ", " * ", "*"]


def normalize_1p_marker(token: str, val: str) -> str:
    """token 별 1p 양식 마커 규칙 적용.

    Returns: 정규화된 텍스트
    """
    if not isinstance(val, str) or not val:
        return val

    # 1. 자동 prefix 부여 위계 — 사용자가 이미 마커 입력했으면 중복 방지
    if token in ONE_P_MARKER_PREFIX:
        prefix = ONE_P_MARKER_PREFIX[token]
        prefix_char = prefix.strip()
        stripped = val.lstrip()
        # 이미 같은 마커로 시작하면 그대로
        if stripped.startswith(prefix_char):
            return val
        # 다른 비슷한 마커(◦ ○ ◇ 등) 로 시작하면 제거 후 표준 마커로
        if prefix_char == "◦":
            for m in SUBBULLET_PATTERNS:
                if stripped.startswith(m):
                    stripped = stripped[len(m):].lstrip()
                    break
        elif prefix_char == "*":
            for m in ASTERISK_PATTERNS:
                if stripped.startswith(m):
                    stripped = stripped[len(m):].lstrip()
                    break
        return prefix + stripped

    # 2. 자동 BULLET 위계 — 사용자 입력에서 "-" 마커 제거 (중복 방지)
    if token in ONE_P_TRIM_BULLET:
        stripped = val.lstrip()
        for m in BULLET_PATTERNS:
            if stripped.startswith(m):
                return stripped[len(m):].lstrip()
        return val

    return val


def normalize_1p_values(values: dict) -> tuple:
    """values dict 안의 1p 양식 placeholder 값들을 일괄 정규화.

    Returns: (new_values, summary)
    """
    new_values = {}
    summary = {"prefix_added": 0, "marker_trimmed": 0, "unchanged": 0}
    for k, v in values.items():
        if not isinstance(v, str):
            new_values[k] = v
            continue
        new_v = normalize_1p_marker(k, v)
        if new_v == v:
            summary["unchanged"] += 1
        elif k in ONE_P_MARKER_PREFIX:
            summary["prefix_added"] += 1
        elif k in ONE_P_TRIM_BULLET:
            summary["marker_trimmed"] += 1
        new_values[k] = new_v
    return new_values, summary


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 3:
        print("사용법: python3 normalize_1p_markers.py <values_in.json> <values_out.json>")
        sys.exit(1)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        values = json.load(f)
    new_values, summary = normalize_1p_values(values)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(new_values, f, ensure_ascii=False, indent=2)
    print(f"✅ 1p 마커 정규화: {summary}")
