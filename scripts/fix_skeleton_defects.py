"""
fix_skeleton_defects.py — skeleton 양식 결함 보정 (v3.6.6 / 3.6.10)
────────────────────────────────────────────────────────────────────────
양식 빈 골격(skeleton.hwpx) 자체의 결함을 fill_skeleton 호출 *전* 에 메모리에서
보정. skeleton 파일은 변경하지 않음 (사용자 원칙 "스켈레톤 유지" 보존).

발견된 결함 목록:

  ① 풀버전 목차 Ⅳ장 들여쓰기 run 누락 (INDENT_FIXES)
     placeholder {{목차_항목_021}} 직전에 다른 로마자 단락(001/003/013/033/043)
     처럼 들여쓰기용 공백 run 이 있어야 하는데 Ⅳ장 단락에만 누락돼 있음.

  ② 공문 수신자 라벨/입력 셀 분리 결함 (v3.6.10)
     양식이 원래 [셀0: '수신자' 라벨] | [셀1: 입력 자리] 디자인이었으나, 빈
     골격 만들면서 셀0 의 '수신자' 라벨까지 placeholder({{text_004}}) 로
     변환되어 사용자가 입력 시 라벨 자체가 사라짐. 셀1 은 빈 hp:p 만 있고
     placeholder 가 없어서 정상 입력 경로 없음.
     해결: 셀1 의 빈 hp:p 안에 {{수신자}} placeholder 동적 삽입,
     {{text_004}} 는 fill_skeleton 의 DEFAULT_VALUES 로 '수신' 라벨 자동 부여.
"""

import re


# placeholder 직전에 들여쓰기 run 보충이 필요한 토큰 목록
INDENT_FIXES = [
    ("목차_항목_021", "12"),
]


def fix_missing_indent_runs(xml: str) -> tuple:
    """INDENT_FIXES 토큰 직전 hp:run 이 들여쓰기 run 이 아니면 보충."""
    n_fixed = 0
    for token, indent_char_pr in INDENT_FIXES:
        idx = xml.find(f"{{{{{token}}}}}")
        if idx == -1:
            continue
        run_start = xml.rfind("<hp:run", 0, idx)
        if run_start == -1:
            continue
        p_start = xml.rfind("<hp:p ", 0, run_start)
        if p_start == -1:
            continue
        before_token_run = xml[p_start:run_start]
        if "<hp:run" in before_token_run:
            continue
        indent_run = (
            f'<hp:run charPrIDRef="{indent_char_pr}">'
            f'<hp:t> </hp:t>'
            f'</hp:run>'
        )
        xml = xml[:run_start] + indent_run + xml[run_start:]
        n_fixed += 1
    return xml, n_fixed


def add_receiver_input_slot(xml: str) -> tuple:
    """공문 양식 수신자 행: 셀[1] (라벨 옆 빈 셀) 의 빈 hp:p 안에
    `{{수신자}}` placeholder 를 동적 삽입.

    text_004 셀 = 라벨 셀, 그 다음 hp:tc = 입력 셀.
    Returns (new_xml, applied: bool)
    """
    idx = xml.find('{{text_004}}')
    if idx == -1:
        return xml, False
    # text_004 셀(hp:tc) 닫는 위치
    tc_close_idx = xml.find('</hp:tc>', idx)
    if tc_close_idx == -1:
        return xml, False
    tc_end = tc_close_idx + len('</hp:tc>')
    # 다음 hp:tc 시작
    next_tc_start = xml.find('<hp:tc', tc_end)
    if next_tc_start == -1:
        return xml, False
    next_tc_close = xml.find('</hp:tc>', next_tc_start)
    if next_tc_close == -1:
        return xml, False
    # 그 셀 안의 hp:p 닫는 태그 직전에 hp:run 삽입
    next_cell_xml = xml[next_tc_start:next_tc_close]
    # 셀 안 마지막 </hp:p> 직전 위치 (가장 안쪽 hp:p)
    p_close_rel = next_cell_xml.rfind('</hp:p>')
    if p_close_rel == -1:
        return xml, False
    # 이미 {{수신자}} placeholder 가 있으면 중복 삽입 안 함
    if '{{수신자}}' in next_cell_xml:
        return xml, False
    # text_004 라벨 셀의 charPr 가져오기 (시각적 일치)
    label_cell_start = xml.rfind('<hp:tc', 0, idx)
    label_cell_xml = xml[label_cell_start:tc_end]
    char_pr_m = re.search(r'<hp:run\s+charPrIDRef="(\d+)"', label_cell_xml)
    char_pr = char_pr_m.group(1) if char_pr_m else "12"

    new_run = (
        f'<hp:run charPrIDRef="{char_pr}">'
        f'<hp:t>{{{{수신자}}}}</hp:t>'
        f'</hp:run>'
    )
    abs_p_close = next_tc_start + p_close_rel
    xml = xml[:abs_p_close] + new_run + xml[abs_p_close:]
    return xml, True


def apply_skeleton_fixes(xml: str) -> tuple:
    """모든 결함 보정 적용."""
    summary = {}
    xml, n_indent = fix_missing_indent_runs(xml)
    summary["indent_fixes"] = n_indent
    xml, recv_added = add_receiver_input_slot(xml)
    summary["receiver_slot_added"] = recv_added
    return xml, summary


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("사용법: python3 fix_skeleton_defects.py <input.xml> <output.xml>")
        sys.exit(1)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        xml = f.read()
    new_xml, summary = apply_skeleton_fixes(xml)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(new_xml)
    print(f"✅ 결함 보정 완료: {summary}")
