"""
ensure_body_anchor.py
────────────────────────────────────────────────────────────
빌드된 hwpx 의 본문 시작 단락에 명시적 페이지나눔(pageBreak="1") 을 보장.

원리:
- Ⅰ장 제목 토큰(또는 그 텍스트)을 찾음
- 그 토큰을 포함하는 표(hp:tbl) 의 외부 단락(hp:p)을 식별
- 그 단락의 pageBreak 속성을 "0" → "1" 로 변경

CLI:
    python ensure_body_anchor.py <hwpx>
"""

import re
import shutil
import sys
import zipfile
from pathlib import Path


CHAPTER_PATTERNS = [
    r'Ⅰ\b',          # 로마 숫자 1 단독 (표 셀의 장 헤더)
    r'추진배경',
    r'사업\s*개요',
]


def ensure_body_anchor(hwpx_path: Path) -> dict:
    workdir = Path("/tmp") / f"anchor_{hwpx_path.stem}"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    with zipfile.ZipFile(hwpx_path, "r") as zf:
        zf.extractall(workdir)

    sec_path = workdir / "Contents" / "section0.xml"
    sec = sec_path.read_text(encoding="utf-8")

    # 본문의 Ⅰ장 위치 찾기 (페이지 1 영역인 표지·목차 이후)
    # 양식 기본: 첫 페이지나눔 이후 영역에서 단독 "Ⅰ" 표 셀
    first_break = re.search(r'pageBreak="1"', sec)
    body_search_start = first_break.end() if first_break else 0

    chapter_pos = -1
    for pattern in CHAPTER_PATTERNS:
        m = re.search(rf'<hp:t>{pattern}[^<]*</hp:t>', sec[body_search_start:])
        if m:
            chapter_pos = body_search_start + m.start()
            break
    if chapter_pos < 0:
        return {"applied": False, "reason": "Ⅰ장 토큰 못 찾음"}

    # 감싸는 표 찾기
    tbl_starts = [m.start() for m in re.finditer(r'<hp:tbl\b', sec)]
    enclosing_tbl = None
    for ts in reversed(tbl_starts):
        te_m = re.search(r'</hp:tbl>', sec[ts:])
        if te_m and ts + te_m.end() > chapter_pos and ts <= chapter_pos:
            enclosing_tbl = ts
            break
    if enclosing_tbl is None:
        return {"applied": False, "reason": "감싸는 표 못 찾음"}

    # 그 표를 담는 단락 찾기 (가장 가까운 직전 <hp:p ...>)
    para_pattern = re.compile(r'<hp:p\s+([^>]+)>')
    para_matches = list(para_pattern.finditer(sec[:enclosing_tbl]))
    if not para_matches:
        return {"applied": False, "reason": "감싸는 단락 못 찾음"}

    last_para = para_matches[-1]
    attrs = last_para.group(1)
    if 'pageBreak="1"' in attrs:
        return {"applied": True, "reason": "이미 pageBreak='1' 있음"}

    # pageBreak="0" → pageBreak="1" 치환
    new_attrs = re.sub(r'pageBreak="0"', 'pageBreak="1"', attrs)
    if new_attrs == attrs:
        # pageBreak 속성이 없으면 추가
        new_attrs = attrs + ' pageBreak="1"'

    new_sec = (
        sec[:last_para.start()]
        + f'<hp:p {new_attrs}>'
        + sec[last_para.end():]
    )
    sec_path.write_text(new_sec, encoding="utf-8")

    # 재패키징
    with zipfile.ZipFile(hwpx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        mt = workdir / "mimetype"
        zf.write(mt, "mimetype", compress_type=zipfile.ZIP_STORED)
        for f in sorted(workdir.rglob("*")):
            if f.is_file() and f.name != "mimetype":
                zf.write(f, f.relative_to(workdir).as_posix())

    return {"applied": True, "reason": "본문 시작 단락에 pageBreak='1' 추가"}


if __name__ == "__main__":
    result = ensure_body_anchor(Path(sys.argv[1]))
    print(result)
