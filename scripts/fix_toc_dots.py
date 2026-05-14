"""
fix_toc_dots.py — 풀버전 목차 점선(leader=3) width 통일 + lineseg 제거 후처리
                  (v3.6.1 신규, v3.6.5 lineseg 제거 추가)
────────────────────────────────────────────────────────────────────────
근본 원인 (두 가지가 결합):

  ① 양식 원본 텍스트(예: "Ⅰ. 사업 개요") 기준으로 박힌 `<hp:tab width="..." leader="3"/>`
     의 width 가 사용자 콘텐츠 텍스트 길이와 무관하게 11404~35444 사이 무작위.
     → 한글2018 (실제 폰트 메트릭 환경) 이 정합성 검증 시 점선 끊김·번호 누락.

  ② 목차 단락의 `<hp:linesegarray>` 에 저장된 lineseg 캐시 정보가 원본 양식 기준이라,
     한글2018 이 첫 렌더링 시 이 캐시를 따라가 점선이 단락 너비를 넘어 길게 표시되거나
     페이지번호가 잘리는 현상 발생. 사용자 보고: "점선 지웠다가 Ctrl+Z 로 되돌리면
     정확한 위치로 그려진다" → 한글 재계산 동작은 정상, 저장된 캐시가 문제.

해결 (2단계):
  단계 A (v3.6.1~): 모든 `leader="3"` tab 의 width 를 단락 너비보다 약간 작은
    값(42000) 으로 통일. type="2" right-align tab 에서 width 는 점선이 끝나고
    페이지번호가 right-align 으로 그려질 위치. 단락 너비(43000) 보다 작아야
    페이지번호가 단락 안에 표시됨.

  단계 B (v3.6.5): 점선 tab 을 포함하는 단락의 `<hp:linesegarray>` 통째 제거.
    한글이 파일 열 때 폰트 메트릭으로 lineseg 자동 재계산 → Ctrl+Z 후 정상화되는
    동작을 처음부터 강제. fix_gongmun_body 와 동일한 lineseg 캐시 무효화 접근.

사용법:
  python3 fix_toc_dots.py <hwpx_path>
  python3 fix_toc_dots.py <hwpx_path> --dry-run
"""

import argparse
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# 모든 width 를 이 값으로 통일. 양식의 목차 단락 horzsize=43000 보다 약간 작게.
UNIFIED_WIDTH = 42000


def fix_toc_dot_widths(xml: str, target_width: int = UNIFIED_WIDTH) -> tuple:
    """
    `<hp:tab width="..." leader="3" type="2"/>` 들의 width 를 target_width 로 통일.
    Returns (new_xml, count_changed, originals)
    """
    pattern = re.compile(
        r'<hp:tab\s+width="(\d+)"\s+leader="3"\s+type="2"\s*/>'
    )
    originals = []
    def _sub(m):
        original_w = int(m.group(1))
        originals.append(original_w)
        return f'<hp:tab width="{target_width}" leader="3" type="2"/>'
    new_xml, n = pattern.subn(_sub, xml)
    return new_xml, n, originals


def remove_linesegarray_from_dotted_paragraphs(xml: str) -> tuple:
    """
    `<hp:tab leader="3"/>` 를 포함한 hp:p 블록 안의 `<hp:linesegarray>` 제거.

    한글이 파일 열 때 폰트 메트릭으로 lineseg 자동 재계산 → 점선 길이·페이지번호
    위치가 처음부터 정확하게 그려짐.

    Returns (new_xml, n_removed)
    """
    n_removed = 0
    out_parts = []
    pos = 0
    while pos < len(xml):
        p_start = xml.find('<hp:p ', pos)
        if p_start == -1:
            out_parts.append(xml[pos:])
            break
        p_close = xml.find('</hp:p>', p_start)
        if p_close == -1:
            out_parts.append(xml[pos:])
            break
        p_end = p_close + len('</hp:p>')
        block = xml[p_start:p_end]
        # 이 hp:p 안에 점선 tab 이 있는지
        if 'leader="3"' in block:
            # linesegarray 제거
            new_block = re.sub(
                r'<hp:linesegarray\b[^>]*>.*?</hp:linesegarray>',
                '', block, flags=re.DOTALL
            )
            if new_block != block:
                n_removed += 1
            block = new_block
        out_parts.append(xml[pos:p_start])
        out_parts.append(block)
        pos = p_end
    return ''.join(out_parts), n_removed


def process_hwpx(hwpx_path: Path, target_width: int = UNIFIED_WIDTH,
                 dry_run: bool = False, verbose: bool = True) -> dict:
    workdir = Path(tempfile.mkdtemp(prefix="fix_toc_"))
    try:
        with zipfile.ZipFile(hwpx_path, "r") as zf:
            zf.extractall(workdir)
        sec_path = workdir / "Contents" / "section0.xml"
        if not sec_path.exists():
            return {"ok": False, "error": "section0.xml 없음"}
        xml = sec_path.read_text(encoding="utf-8")

        if verbose:
            print(f"===== 목차 점선 후처리 (v3.6.5: width 통일 + lineseg 제거) =====")
            print(f"  대상: {hwpx_path}")
            print(f"  단계 A — 점선 tab width 통일 ({target_width})")

        # 단계 A: width 통일
        new_xml, n_changed, originals = fix_toc_dot_widths(xml, target_width)
        if verbose:
            if n_changed == 0:
                print(f"    → 점선 tab 없음 (양식 미해당)")
            else:
                from collections import Counter
                wc = Counter(originals)
                print(f"    ✂ {n_changed} 개 tab width → {target_width}")
                items = sorted(wc.items())
                for w, c in items[:5]:
                    print(f"        width={w} ({c}개)")
                if len(items) > 5:
                    print(f"        ... 외 {len(items)-5} 종류")

        # 단계 B: 점선 포함 단락 linesegarray 제거
        if verbose:
            print(f"  단계 B — 점선 포함 단락의 lineseg 캐시 제거 (한글 자동 재계산)")
        new_xml, n_lsa_removed = remove_linesegarray_from_dotted_paragraphs(new_xml)
        if verbose:
            print(f"    ✂ {n_lsa_removed} 개 단락의 linesegarray 제거")

        if dry_run:
            if verbose:
                print("  (dry-run: 파일 변경 안 함)")
            return {"ok": True, "changed": n_changed, "lsa_removed": n_lsa_removed, "dry_run": True}

        if n_changed == 0 and n_lsa_removed == 0:
            return {"ok": True, "changed": 0, "lsa_removed": 0}

        sec_path.write_text(new_xml, encoding="utf-8")
        tmp_out = hwpx_path.with_suffix(".hwpx.tmp")
        if tmp_out.exists():
            tmp_out.unlink()
        with zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED) as zf:
            mt = workdir / "mimetype"
            zf.write(mt, "mimetype", compress_type=zipfile.ZIP_STORED)
            for f in sorted(workdir.rglob("*")):
                if f.is_file() and f.name != "mimetype":
                    zf.write(f, f.relative_to(workdir).as_posix())
        shutil.move(str(tmp_out), str(hwpx_path))
        if verbose:
            print(f"  → 저장 완료: {hwpx_path}")
        return {"ok": True, "changed": n_changed, "lsa_removed": n_lsa_removed}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main():
    p = argparse.ArgumentParser(
        description="풀버전 목차 점선 width 통일 + lineseg 제거 후처리 (v3.6.5)")
    p.add_argument("hwpx", help="처리할 hwpx 파일")
    p.add_argument("--width", type=int, default=UNIFIED_WIDTH,
                   help=f"통일할 width 값 (기본 {UNIFIED_WIDTH})")
    p.add_argument("--dry-run", action="store_true",
                   help="실제 변경 없이 어떤 tab/단락이 영향받는지만 출력")
    args = p.parse_args()
    hwpx = Path(args.hwpx).resolve()
    if not hwpx.exists():
        print(f"❌ 파일 없음: {hwpx}", file=sys.stderr)
        sys.exit(1)
    result = process_hwpx(hwpx, target_width=args.width, dry_run=args.dry_run)
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
