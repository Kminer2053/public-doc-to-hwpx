"""
빈 골격 hwpx의 {{토큰}} placeholder를 실제 값으로 채워서 완성된 hwpx 생성.

사용법:
    python fill_skeleton.py \\
        --skeleton templates/format_full/skeleton.hwpx \\
        --values values.json \\
        --output result.hwpx
        
values.json 구조:
{
    "표지_부제": "- AX 시대 인적자원 혁신을 위한 -",
    "표지_제목": "전사적 AI역량 강화 추진계획",
    "보고일": "2026. 5.",
    ...
}
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# v3.6.4: 공문 placeholder 단락 자동 분리 (v3.6.6 에서 SPLIT_PAIRS 빈 상태로 변경)
# v3.6.6: skeleton 결함 보정 (Ⅳ장 들여쓰기 누락 등)
# v3.6.7/3.6.8: 공문 본문 단락 동적 확장 (모든 위계) + 빈 placeholder 단락 자동 제거
try:
    from split_gongmun_paragraphs import split_combined_placeholders
    from fix_skeleton_defects import apply_skeleton_fixes
    from expand_gongmun_body import (
        apply_body_expansion,
        EMPTY_MARKER,
        remove_empty_marker_paragraphs,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from split_gongmun_paragraphs import split_combined_placeholders
    from fix_skeleton_defects import apply_skeleton_fixes
    from expand_gongmun_body import (
        apply_body_expansion,
        EMPTY_MARKER,
        remove_empty_marker_paragraphs,
    )


def xml_escape(text: str) -> str:
    """XML 안전 처리"""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def fill_skeleton(skeleton_path: Path, values: dict, output_path: Path,
                  split_paragraphs: bool = True,
                  fix_defects: bool = True,
                  expand_body: bool = True,
                  remove_empty: bool = True) -> dict:
    """빈 골격의 placeholder를 values 딕셔너리로 채움.

    v3.6.8: remove_empty=True (기본) 시 빈 값(values 누락 또는 빈 문자열) 인
    placeholder 가 속한 hp:p 단락을 출력에서 자동 제거. 한글에서 빈 줄로
    안 보임. 다른 의미 있는 텍스트가 같은 hp:p 에 있으면 마커만 제거하고
    단락은 보존.
    """
    workdir = Path("/tmp/fill_work")
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    with zipfile.ZipFile(skeleton_path, "r") as zf:
        zf.extractall(workdir)

    sec_path = workdir / "Contents" / "section0.xml"
    sec = sec_path.read_text(encoding="utf-8")

    # v3.6.6: skeleton 결함 보정 (Ⅳ장 들여쓰기 누락 등)
    defects_summary = {}
    if fix_defects:
        sec, defects_summary = apply_skeleton_fixes(sec)

    # v3.6.4 / 3.6.6: 공문 placeholder 단락 분리 (현재는 SPLIT_PAIRS 비어 있음)
    n_splits = 0
    if split_paragraphs:
        sec, n_splits = split_combined_placeholders(sec)

    # v3.6.7/3.6.8: 공문 본문 동적 확장 (모든 위계)
    body_summary = {"extra_paragraphs_inserted": 0, "extra_by_anchor": {}}
    if expand_body:
        values, sec, body_summary = apply_body_expansion(values, sec)

    # 모든 {{토큰}} 찾기
    tokens_found = set(re.findall(r'\{\{([^}]+)\}\}', sec))

    # v3.6.10: 양식 라벨 자동 부여 (사용자가 입력 안 해도 라벨 보존)
    DEFAULT_VALUES = {
        "text_004": "수신",  # 양식의 '수신' 라벨 자동 부여
    }

    # v3.6.8 안전화: EMPTY_MARKER 는 본문 영역 placeholder 에만 적용.
    BODY_PLACEHOLDERS = {
        "text_007", "text_008", "text_009",
        "text_010", "text_011", "text_012", "text_013",
        "목차_항목_001", "목차_항목_002", "목차_항목_003", "목차_항목_004",
    }

    # 치환
    filled_count = 0
    unfilled = []
    for token in tokens_found:
        if token in values and values[token] != "":
            replacement = xml_escape(values[token])
            sec = sec.replace(f"{{{{{token}}}}}", replacement)
            filled_count += 1
        elif token in DEFAULT_VALUES:
            # 사용자 입력 없으면 기본 라벨 자동 부여
            sec = sec.replace(f"{{{{{token}}}}}",
                              xml_escape(DEFAULT_VALUES[token]))
            filled_count += 1
        else:
            # 본문 placeholder 만 EMPTY_MARKER 처리 (단락 제거 가능)
            if remove_empty and token in BODY_PLACEHOLDERS:
                sec = sec.replace(f"{{{{{token}}}}}", EMPTY_MARKER)
            else:
                sec = sec.replace(f"{{{{{token}}}}}", "")
            unfilled.append(token)

    # v3.6.8: 빈 placeholder 단락 제거 (본문 영역 한정)
    empty_summary = {"paragraphs_removed": 0, "markers_cleaned": 0}
    if remove_empty:
        sec, n_p_removed, n_marker = remove_empty_marker_paragraphs(sec)
        empty_summary = {
            "paragraphs_removed": n_p_removed,
            "markers_cleaned": n_marker,
        }

    sec_path.write_text(sec, encoding="utf-8")

    # 제목 갱신 (content.hpf)
    hpf_path = workdir / "Contents" / "content.hpf"
    if hpf_path.exists() and values.get("표지_제목"):
        hpf = hpf_path.read_text(encoding="utf-8")
        safe = xml_escape(values["표지_제목"])
        hpf = re.sub(r'<opf:title>[^<]*</opf:title>',
                     f'<opf:title>{safe}</opf:title>', hpf, count=1)
        hpf_path.write_text(hpf, encoding="utf-8")

    # 재패키징
    if output_path.exists():
        output_path.unlink()
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        mt = workdir / "mimetype"
        zf.write(mt, "mimetype", compress_type=zipfile.ZIP_STORED)
        for f in sorted(workdir.rglob("*")):
            if f.is_file() and f.name != "mimetype":
                zf.write(f, f.relative_to(workdir).as_posix())

    return {
        "tokens_in_skeleton": len(tokens_found),
        "filled": filled_count,
        "emptied": len(unfilled),
        "emptied_tokens": unfilled,
        "paragraph_splits": n_splits,        # v3.6.4
        "defect_fixes": defects_summary,     # v3.6.6
        "body_expansion": body_summary,      # v3.6.7
        "empty_handling": empty_summary,     # v3.6.8
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skeleton", required=True)
    parser.add_argument("--values", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--no-split-paragraphs", action="store_true",
                        help="공문 placeholder 단락 분리 비활성화")
    parser.add_argument("--no-fix-defects", action="store_true",
                        help="skeleton 결함 보정 비활성화 (Ⅳ장 들여쓰기 등)")
    parser.add_argument("--no-expand-body", action="store_true",
                        help="공문 본문 동적 확장 비활성화 ('본문' 배열 처리)")
    parser.add_argument("--no-remove-empty", action="store_true",
                        help="빈 placeholder 단락 자동 제거 비활성화")
    args = parser.parse_args()

    values = json.loads(Path(args.values).read_text(encoding="utf-8"))
    result = fill_skeleton(
        Path(args.skeleton),
        values,
        Path(args.output),
        split_paragraphs=not args.no_split_paragraphs,
        fix_defects=not args.no_fix_defects,
        expand_body=not args.no_expand_body,
        remove_empty=not args.no_remove_empty,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
