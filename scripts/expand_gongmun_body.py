"""
expand_gongmun_body.py — 공문 본문 동적 확장 + 빈 단락 제거 (v3.6.7/3.6.8)
────────────────────────────────────────────────────────────────────────
공문 양식 skeleton 의 본문 슬롯은 각 위계마다 1~2개로 고정되어 있다. 이 모듈은
사용자가 입력한 콘텐츠 양에 따라 모든 위계의 단락을 동적으로 확장하고,
콘텐츠가 없는 placeholder 는 단락 자체를 출력에서 제거한다.

## 지원 위계 (EXPANSION_RULES)

| 입력 키 | 양식 슬롯 | 동적 추가 paraPr/charPr | 들여쓰기 |
|---|---|---|---|
| 본문 | text_007 + text_008/text_009 | 29 / 24 | 없음 |
| 본문_가나 | 목차_항목_001 / 002 | 26 / 22 | 없음 |
| 본문_1) | text_010 | 26 / 27 | 4-space |
| 본문_가) | text_011 | 26 / 27 | 6-space |
| 본문_(1) | text_012 | 26 / 27 | 8-space |
| 본문_① | text_013 | 26 / 27 | 10-space |
| 붙임 | 목차_항목_003 / 004 | 27 / 22 | 없음 |

## 빈 단락 제거
values 에 없거나 빈 값인 placeholder 는 EMPTY_MARKER 로 치환되고, 후처리에서
EMPTY_MARKER 만 있는 hp:p 통째 제거 (한글에서 빈 줄로 안 보임).
"""

import re


EXPANSION_RULES = [
    {
        "key": "본문",
        "slots": ["text_007", ("text_008", "text_009")],
        "para_pr": "29", "char_pr": "24",
        "anchor": "text_009",
        "slot_indent": "",       # 양식 슬롯 텍스트 prefix
        "dynamic_indent": "",    # 동적 단락 텍스트 prefix
    },
    {
        # 본문_가나: 양식 슬롯에 이미 "  <hp:fwSpace/>" 자동 들여쓰기 → slot_indent="" 유지
        # 동적 추가에도 동일한 raw XML element 사용 (시각적으로 정확히 동일)
        "key": "본문_가나",
        "slots": ["목차_항목_001", "목차_항목_002"],
        "para_pr": "26", "char_pr": "22",
        "anchor": "목차_항목_002",
        "slot_indent": "",
        "dynamic_indent": "",
        "dynamic_indent_xml": "  <hp:fwSpace/>",  # 양식과 동일한 raw XML
    },
    {
        # 본문_1)~①: 양식 슬롯 placeholder 앞 들여쓰기 없음 → 양식 슬롯에도 prefix 적용 필요
        # 양식 원본 텍스트의 들여쓰기 폭(4/6/8/10 space)과 동일하게 통일
        "key": "본문_1)",
        "slots": ["text_010"],
        "para_pr": "26", "char_pr": "27",
        "anchor": "text_010",
        "slot_indent": "    ",
        "dynamic_indent": "    ",
    },
    {
        "key": "본문_가)",
        "slots": ["text_011"],
        "para_pr": "26", "char_pr": "27",
        "anchor": "text_011",
        "slot_indent": "      ",
        "dynamic_indent": "      ",
    },
    {
        "key": "본문_(1)",
        "slots": ["text_012"],
        "para_pr": "26", "char_pr": "27",
        "anchor": "text_012",
        "slot_indent": "        ",
        "dynamic_indent": "        ",
    },
    {
        "key": "본문_①",
        "slots": ["text_013"],
        "para_pr": "26", "char_pr": "27",
        "anchor": "text_013",
        "slot_indent": "          ",
        "dynamic_indent": "          ",
    },
    {
        # 붙임은 사용자가 텍스트 안에 들여쓰기 직접 입력 (관습)
        "key": "붙임",
        "slots": ["목차_항목_003"],
        "para_pr": "27", "char_pr": "22",
        "anchor": "목차_항목_003",
        "slot_indent": "",
        "dynamic_indent": "",
    },
]


def _split_marker(text: str) -> tuple:
    """'2. 본문' → ('2. ', '본문') 자동 분리."""
    m = re.match(r'^(\d+\.\s*)(.+)$', text, re.DOTALL)
    if m:
        return m.group(1), m.group(2)
    return "", text


def _apply_indent(text: str, indent: str) -> str:
    """텍스트가 공백(반각/전각)으로 시작하면 그대로, 아니면 indent prefix 추가."""
    if not indent:
        return text
    if text and (text[0] in (" ", "\u3000", "\t")):
        return text  # 사용자가 직접 들여쓰기 입력
    return indent + text


def normalize_body_input(values: dict) -> tuple:
    """values 위계 입력을 정규화. (new_values, dynamic_by_anchor) 반환.

    v3.6.8 변경: 양식 슬롯에 들어가는 텍스트에도 slot_indent prefix 적용,
    동적 추가에는 dynamic_indent prefix 적용 → 양식 슬롯/동적 단락 들여쓰기 통일.
    """
    new_values = dict(values)
    dynamic = {}

    for rule in EXPANSION_RULES:
        key = rule["key"]
        if key not in new_values:
            continue
        items = new_values.pop(key)
        if not isinstance(items, list):
            continue

        slots = rule["slots"]
        slot_indent = rule.get("slot_indent", "")
        dynamic_indent = rule.get("dynamic_indent", "")
        consumed = 0
        for slot in slots:
            if consumed >= len(items):
                break
            item = items[consumed]
            # 양식 슬롯에 들어가는 텍스트도 slot_indent 적용
            item = _apply_indent(item, slot_indent)
            if isinstance(slot, tuple):
                marker, body = _split_marker(item)
                marker_token, body_token = slot
                new_values.setdefault(marker_token, marker)
                new_values.setdefault(body_token, body)
            else:
                new_values.setdefault(slot, item)
            consumed += 1

        extra_items = items[consumed:]
        if extra_items:
            anchor = rule["anchor"]
            indent_xml = rule.get("dynamic_indent_xml", "")
            dynamic.setdefault(anchor, [])
            for item in extra_items:
                text = _apply_indent(item, dynamic_indent)
                dynamic[anchor].append(
                    (text, rule["para_pr"], rule["char_pr"], indent_xml))

    return new_values, dynamic


def _build_p_block(text: str, para_pr: str, char_pr: str,
                   indent_xml: str = "") -> str:
    """동적 hp:p 단락 생성.

    indent_xml: hp:t 안에 raw XML 로 들어갈 들여쓰기 prefix. 양식의
      `<hp:fwSpace/>` 같은 element 를 그대로 사용해서 양식 슬롯과 시각적으로
      정확히 동일한 들여쓰기 효과 달성. 텍스트 prefix 와 달리 폰트 메트릭 의존
      없음.
    """
    safe = (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))
    return (
        f'<hp:p id="0" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{char_pr}">'
        f'<hp:t>{indent_xml}{safe}</hp:t>'
        f'</hp:run>'
        f'</hp:p>'
    )


def _find_matching_p_close(xml: str, p_start: int) -> int:
    """hp:p 시작 위치에서 짝 맞는 </hp:p> 끝 위치 반환 (depth 추적).
    hp:p 안에 hp:tbl > hp:tc > hp:subList > hp:p 가 중첩된 경우 대응.
    Returns -1 if not found.
    """
    depth = 1
    pos = p_start + len('<hp:p ')
    while depth > 0:
        next_open = xml.find('<hp:p ', pos)
        next_close = xml.find('</hp:p>', pos)
        if next_close == -1:
            return -1
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + len('<hp:p ')
        else:
            depth -= 1
            pos = next_close + len('</hp:p>')
            if depth == 0:
                return pos
    return -1


def insert_dynamic_paragraphs(xml: str, dynamic: dict) -> tuple:
    """anchor placeholder 가 든 hp:p 의 짝 맞는 </hp:p> 직후에 동적 단락 삽입.

    안전 원칙: hp:p 안에 hp:tbl 이 든 단락(예: 발신부 표 감싸기) 은 anchor 로
    사용하지 않는다 (EXPANSION_RULES 가 그런 anchor 를 피하도록 설계됨).
    따라서 단순 </hp:p> 다음 삽입만으로 충분 — hp:p 분리 같은 위험 로직 불필요.
    """
    n_inserted = 0
    for anchor, items in dynamic.items():
        if not items:
            continue
        token_str = "{{" + anchor + "}}"
        idx = xml.find(token_str)
        if idx == -1:
            continue
        p_start = xml.rfind('<hp:p ', 0, idx)
        if p_start == -1:
            continue
        p_end = _find_matching_p_close(xml, p_start)
        if p_end == -1:
            continue
        dyn_blocks = "".join(
            _build_p_block(t, pp, cp, ix) for t, pp, cp, ix in items)
        xml = xml[:p_end] + dyn_blocks + xml[p_end:]
        n_inserted += len(items)
    return xml, n_inserted


def apply_body_expansion(values: dict, xml: str) -> tuple:
    """공문 본문 동적 확장 통합 진입점."""
    new_values, dynamic = normalize_body_input(values)
    new_xml, n_inserted = insert_dynamic_paragraphs(xml, dynamic)
    summary = {
        "extra_paragraphs_inserted": n_inserted,
        "extra_by_anchor": {a: [item[0][:40] for item in items]
                            for a, items in dynamic.items() if items},
    }
    return new_values, new_xml, summary


# ────────────────────────────────────────────────────────────────
# 빈 placeholder 단락 제거 (v3.6.8 신규)
# ────────────────────────────────────────────────────────────────
EMPTY_MARKER = "\u200b\u200b__EMPTY_PLACEHOLDER__\u200b\u200b"


def remove_empty_marker_paragraphs(xml: str) -> tuple:
    """
    EMPTY_MARKER 가 든 *가장 안쪽* hp:p 처리:
      - **hp:tbl 또는 hp:subList 가 든 hp:p (표 감싸기) 는 무조건 단락 보존**,
        EMPTY_MARKER 만 제거. 발신부 표 같은 중요 구조 보호.
      - 그 외에 의미 있는 텍스트 있으면 마커만 제거 (단락 보존).
      - 다 비었으면 hp:p 통째 제거.

    Returns (new_xml, n_p_removed, n_marker_only_cleaned)
    """
    n_removed = 0
    n_marker_only = 0
    while True:
        idx = xml.find(EMPTY_MARKER)
        if idx == -1:
            break
        p_start = xml.rfind('<hp:p ', 0, idx)
        if p_start == -1:
            xml = xml[:idx] + xml[idx + len(EMPTY_MARKER):]
            continue
        p_end = _find_matching_p_close(xml, p_start)
        if p_end == -1:
            xml = xml[:idx] + xml[idx + len(EMPTY_MARKER):]
            continue
        block = xml[p_start:p_end]

        # 보존 예외: hp:tbl 든 단락은 표 보존을 위해 무조건 마커만 제거
        if '<hp:tbl' in block or '<hp:subList' in block:
            new_block = block.replace(EMPTY_MARKER, "")
            xml = xml[:p_start] + new_block + xml[p_end:]
            n_marker_only += 1
            continue

        # 일반 단락: 의미 있는 텍스트 검사
        texts = re.findall(r'<hp:t\b[^>]*>(.*?)</hp:t>', block, re.DOTALL)
        has_meaningful = False
        for t in texts:
            cleaned = t.replace(EMPTY_MARKER, "").strip()
            if cleaned:
                has_meaningful = True
                break
        if has_meaningful:
            new_block = block.replace(EMPTY_MARKER, "")
            xml = xml[:p_start] + new_block + xml[p_end:]
            n_marker_only += 1
        else:
            xml = xml[:p_start] + xml[p_end:]
            n_removed += 1
    return xml, n_removed, n_marker_only


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("사용법: python3 expand_gongmun_body.py <skeleton.xml> <values.json> <output.xml>")
        sys.exit(1)
    import json
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        xml = f.read()
    with open(sys.argv[2], "r", encoding="utf-8") as f:
        values = json.load(f)
    new_values, new_xml, summary = apply_body_expansion(values, xml)
    with open(sys.argv[3], "w", encoding="utf-8") as f:
        f.write(new_xml)
    print(f"✅ {summary['extra_paragraphs_inserted']} 단락 추가")
