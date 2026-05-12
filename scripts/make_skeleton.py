"""
make_skeleton.py
────────────────────────────────────────────────────────────
양식 hwpx 의 section0.xml 을 분석하여 빈 골격(skeleton) hwpx 와 매핑 JSON 을 생성한다.

빈 골격이란?
  - 양식의 모든 시각 구조(표·테두리·음영·페이지헤더/푸터·charPr/paraPr 사용)는 그대로 보존
  - 의미 있는 텍스트만 {{토큰}} 형태의 placeholder 로 교체
  - 라벨·마커·1글자 위계(Ⅰ, Ⅱ, ◦, □ 등)는 보존 (양식의 일부이므로)

산출물:
  - <format_dir>/skeleton.hwpx          : 빈 골격 hwpx
  - <format_dir>/skeleton_mapping.json  : 토큰 ↔ 원본 텍스트 매핑표

사용법:
    # 단일 양식 처리
    python make_skeleton.py templates/format_full/standard.hwpx
    
    # 결과는 같은 폴더에 skeleton.hwpx, skeleton_mapping.json 으로 저장
────────────────────────────────────────────────────────────
"""

import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path


# ────────────────────────────────────────────────────────────
# 보존 대상 (양식 구조의 일부 — 토큰화하지 않음)
# ────────────────────────────────────────────────────────────

PRESERVE_EXACT = {
    # 결재선 표 헤더
    "협  조", "협조", "문서번호", "보존기간", "공개", "공개여부", "보고일자",
    # 목차/참고자료 라벨
    "목    차", "목 차", "목차", "【참고자료】", "참고자료",
    # 시행문 라벨
    "수    신", "(경    유)", "제    목", "수신", "경유", "제목",
    "기안자", "검토자", "협조자", "시행", "접수",
    # 일정표/구분표 헤더
    "구분", "일정", "내용", "비고", "담당", "기간",
    # 단독 위계 표시 (로마자/마커)
    "Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ", "Ⅵ", "Ⅶ", "Ⅷ", "Ⅸ", "Ⅹ",
    "◦", "□", "○", "·", "-", "▪", "▣", "▦",
}


def should_preserve(text: str) -> bool:
    """양식 구조의 일부인 라벨·마커는 토큰화하지 않고 그대로 둠.
    단, 1글자 숫자(0~9)는 페이지번호일 가능성이 있어 토큰화 대상으로 처리."""
    stripped = text.strip()
    if not stripped:
        return True
    if stripped in PRESERVE_EXACT:
        return True
    if len(stripped) <= 1:
        # 1글자라도 숫자면 토큰화 (페이지번호 가능성)
        if stripped.isdigit():
            return False
        return True
    return False


def infer_slot_meaning(text: str, idx: int, page: int, in_table: bool,
                       prev_meanings: list) -> str:
    """양식 텍스트 단서로 슬롯 의미 자동 추정"""
    t = text.strip()
    
    # 표지 영역 (페이지 1, 표 안)
    if page == 1 and in_table:
        if "-@N" in t or t.strip("-@") == "N":
            return "문서번호"
        if t in ("1년", "3년", "5년", "10년", "준영구", "영구"):
            return "보존기간"
        if "공개" in t and len(t) < 10:
            return "공개여부"
        if "참고자료" in t and re.match(r'^\s*\d+\.', t):
            num = re.match(r'^\s*(\d+)\.', t).group(1)
            return f"참고자료_{num}"
    
    # 표지 텍스트 (페이지 1, 표 밖)
    if page == 1 and not in_table:
        if "부제" in t:
            return "표지_부제"
        if "주제목" in t or ("28pt" in t and "HY" in t):
            return "표지_제목"
        if re.match(r'^\d{4}', t):
            return "보고일"
        if "기관명" in t and "24" in t:
            return "기관명"
        if ("본부" in t and "부서" in t) or ("부서명" in t and "20" in t):
            return "본부부서명"
    
    # 시행문 영역 (보통 페이지 1)
    if page == 1 and "수신" in str(prev_meanings[-3:] if prev_meanings else "") and not in_table:
        if "수신" not in t and ":" in t[:10]:
            return "수신자"
    
    # 본문 (페이지 2 이상)
    if page >= 2:
        if in_table:
            if len(t) < 20 and "POINT" not in t and "맑은 고딕" not in t:
                return f"장{idx}_제목"
            if "맑은 고딕_12" in t:
                return "일정표_셀"
        else:
            if "□" in t or ("헤드라인" in t and "15" in t):
                return "본문_절"
            if "휴먼명조" in t and "14" in t and not t.lstrip().startswith("-"):
                return "본문_항목"
            if "휴먼명조" in t and "14" in t and t.lstrip().startswith("-"):
                return "본문_세부"
            if "맑은 고딕" in t and "11" in t:
                return "본문_주석"
    
    return "text"


def create_skeleton(src_hwpx: Path, dst_hwpx: Path,
                    mapping_json: Path) -> dict:
    """양식 hwpx 를 빈 골격으로 변환"""
    workdir = Path("/tmp") / f"skeleton_{src_hwpx.stem}"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)
    
    with zipfile.ZipFile(src_hwpx, "r") as zf:
        zf.extractall(workdir)
    
    sec_path = workdir / "Contents" / "section0.xml"
    sec = sec_path.read_text(encoding="utf-8")
    
    # 페이지 나눔 / 표 범위 (pageBreak 두 형식 모두 잡기)
    page_break_positions = (
        [m.start() for m in re.finditer(r'pageBreak="1"', sec)] +
        [m.start() for m in re.finditer(r'<hp:ctrl\s+type="PAGE_BREAK"', sec)]
    )
    page_breaks = sorted(set(page_break_positions))
    
    table_starts = [m.start() for m in re.finditer(r'<hp:tbl\b', sec)]
    table_ends = [m.end() for m in re.finditer(r'</hp:tbl>', sec)]
    table_ranges = list(zip(table_starts, table_ends))
    
    def get_page(pos): return sum(1 for pb in page_breaks if pb < pos) + 1
    def in_tbl(pos): return any(s <= pos < e for s, e in table_ranges)
    
    # ── 핵심 개선 ──
    # <hp:t>...</hp:t> 를 비탐욕 + DOTALL 로 매칭하여 자식 태그(<hp:tab/>) 포함된 것도 잡음
    # 그 안에서 텍스트 노드만 분리해 각각 토큰화하고, 자식 태그는 그대로 보존
    matches = list(re.finditer(r'<hp:t>(.*?)</hp:t>', sec, re.DOTALL))
    
    slots = []          # 각 match 별로 처리 결과 ('skip' | dict)
    slot_counter = {}
    prev_meanings = []
    
    def tokenize_text(text, idx, page, in_table):
        """단일 텍스트 조각을 토큰화. 보존이면 None 반환."""
        if should_preserve(text):
            return None
        meaning = infer_slot_meaning(text, idx, page, in_table, prev_meanings)
        prev_meanings.append(meaning)
        
        if meaning in ("본문_절", "본문_항목", "본문_세부", "본문_주석",
                       "일정표_셀", "text", "목차_항목"):
            slot_counter[meaning] = slot_counter.get(meaning, 0) + 1
            token = f"{meaning}_{slot_counter[meaning]:03d}"
        elif "장" in meaning and "_제목" in meaning:
            slot_counter["장_제목"] = slot_counter.get("장_제목", 0) + 1
            token = f"장{slot_counter['장_제목']:02d}_제목"
        else:
            token = meaning
        return {"token": token, "original": text}
    
    # ── 각 hp:t 매치를 처리 ──
    # 결과로 (match, replacement_xml) 쌍을 모으고, 역순으로 sec 에 적용
    replacements = []  # [(match.start, match.end, new_xml)]
    
    for i, m in enumerate(matches):
        content = m.group(1)
        page = get_page(m.start())
        in_table = in_tbl(m.start())
        
        # 자식 태그가 있는지 (<hp: 로 시작하는 게 있는지)
        if "<hp:" not in content:
            # 단순 텍스트 케이스 (기존 동작)
            slot = tokenize_text(content, i, page, in_table)
            if slot is None:
                slots.append(None)
                continue
            slot.update({"page": page, "in_table": in_table})
            slots.append(slot)
            new_xml = f'<hp:t>{{{{{slot["token"]}}}}}</hp:t>'
            replacements.append((m.start(), m.end(), new_xml))
        else:
            # 자식 태그 포함 (예: 목차의 <hp:tab/> 채움)
            # content 를 [텍스트, 태그, 텍스트, ...] 로 분해
            parts = []
            cursor = 0
            for child in re.finditer(r'<hp:[^/>]+/>|<hp:[^>]+>.*?</hp:[^>]+>',
                                      content, re.DOTALL):
                if child.start() > cursor:
                    parts.append(("text", content[cursor:child.start()]))
                parts.append(("tag", child.group()))
                cursor = child.end()
            if cursor < len(content):
                parts.append(("text", content[cursor:]))
            
            # 각 텍스트 파트를 토큰화 (보존되는 것은 그대로 유지)
            new_parts = []
            this_slots = []
            for kind, body in parts:
                if kind == "tag":
                    new_parts.append(body)
                else:
                    if should_preserve(body):
                        new_parts.append(body)
                    else:
                        # 자식 태그 포함 hp:t 는 목차일 가능성이 매우 높음
                        # 강제로 목차_항목 유형으로 분류
                        slot_counter["목차_항목"] = slot_counter.get("목차_항목", 0) + 1
                        token = f"목차_항목_{slot_counter['목차_항목']:03d}"
                        new_parts.append(f"{{{{{token}}}}}")
                        this_slots.append({
                            "token": token,
                            "original": body,
                            "page": page,
                            "in_table": in_table,
                        })
            
            if this_slots:
                slots.extend(this_slots)
                new_xml = "<hp:t>" + "".join(new_parts) + "</hp:t>"
                replacements.append((m.start(), m.end(), new_xml))
            else:
                slots.append(None)
    
    # 역순으로 sec 에 적용 (앞 위치가 어긋나지 않도록)
    new_sec = sec
    for start, end, new_xml in sorted(replacements, key=lambda r: -r[0]):
        new_sec = new_sec[:start] + new_xml + new_sec[end:]
    
    sec_path.write_text(new_sec, encoding="utf-8")
    
    # 재패키징
    if dst_hwpx.exists():
        dst_hwpx.unlink()
    with zipfile.ZipFile(dst_hwpx, "w", zipfile.ZIP_DEFLATED) as zf:
        mt = workdir / "mimetype"
        zf.write(mt, "mimetype", compress_type=zipfile.ZIP_STORED)
        for f in sorted(workdir.rglob("*")):
            if f.is_file() and f.name != "mimetype":
                zf.write(f, f.relative_to(workdir).as_posix())
    
    # 매핑 JSON
    used_slots = [s for s in slots if s is not None]
    mapping = {
        "_comment": "빈 골격 hwpx 의 placeholder 토큰 ↔ 원본 텍스트 매핑. fill_skeleton.py 로 채울 때 token 키에 값을 넣은 JSON 을 전달하면 됨.",
        "source_hwpx": src_hwpx.name,
        "skeleton_hwpx": dst_hwpx.name,
        "total_slots": len(used_slots),
        "slots": [
            {
                "token": s["token"],
                "original_text": s["original"],
                "page": s["page"],
                "in_table": s["in_table"],
            }
            for s in used_slots
        ],
    }
    mapping_json.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    return {
        "preserved_count": len([s for s in slots if s is None]),
        "tokenized_count": len(used_slots),
        "total_texts": len(matches),
        "source": str(src_hwpx),
        "skeleton": str(dst_hwpx),
        "mapping": str(mapping_json),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="양식 hwpx 를 빈 골격(skeleton.hwpx) + 매핑 JSON 으로 변환"
    )
    parser.add_argument("source", help="양식 hwpx 경로 (예: templates/format_full/standard.hwpx)")
    parser.add_argument("--skeleton-name", default="skeleton.hwpx",
                        help="결과 골격 파일명 (기본: skeleton.hwpx)")
    parser.add_argument("--mapping-name", default="skeleton_mapping.json",
                        help="결과 매핑 파일명 (기본: skeleton_mapping.json)")
    args = parser.parse_args()
    
    src = Path(args.source).resolve()
    if not src.exists():
        print(f"❌ 양식 파일 없음: {src}", file=sys.stderr)
        sys.exit(1)
    
    dst = src.parent / args.skeleton_name
    mapping = src.parent / args.mapping_name
    
    summary = create_skeleton(src, dst, mapping)
    print("===== 빈 골격 hwpx 생성 완료 =====")
    print(f"  원본 양식: {summary['source']}")
    print(f"  빈 골격:    {summary['skeleton']}")
    print(f"  매핑 JSON:  {summary['mapping']}")
    print()
    print(f"  전체 텍스트: {summary['total_texts']} 개")
    print(f"  보존(라벨/마커): {summary['preserved_count']} 개")
    print(f"  토큰화: {summary['tokenized_count']} 개")
