"""
fix_gongmun_body.py — 공문 본문 단락 자간 압축 깨짐 자동 해소 (v3.6.3)
────────────────────────────────────────────────────────────────────────
근본 원인:
  공문 양식의 본문 단락들 (표 셀 밖) 은 단일 `<hp:lineseg horzsize="49108" .../>`
  로 저장되어 있다. 텍스트가 단락 너비(49108 HwpUnit ≈ 49mm) 를 초과하면
  한글2018 (실제 폰트 메트릭 보유 환경) 이 한 줄에 끼워넣으려 자간을 음수로
  강제 압축 → 글자 겹침·가독성 급락. 표지 제목 깨짐과 동일 메커니즘.

  반면 표 셀 안 단락 (제목·수신·발신명의 등) 의 lineseg 는 horzsize 가
  셀 너비(44380, 6004, 42676 등) 라서 식별이 명확히 구분 가능.

전략:
  단락 구조 파싱은 hp:p 안에 hp:tbl → hp:tc → hp:subList → hp:p 가 중첩될 수
  있어 복잡하므로, `<hp:linesegarray>` 안에 단일 `<hp:lineseg horzsize="49108"/>`
  가 들어있는 패턴을 정규식으로 직접 매칭하여 그 linesegarray 통째 제거.
  한글이 파일 열 때 폰트 메트릭으로 lineseg 자동 재계산 → 자연 줄바꿈 정상화.

  표 셀 안 단락 lineseg 는 horzsize 가 49108 이 아니므로 자동으로 제외됨.
  다중 lineseg(이미 정상) linesegarray 도 매칭 안 됨.
"""

import argparse
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# 공문 본문 단락 너비 (표 셀 밖 일반 단락). 양식 분석으로 확인된 값.
DEFAULT_BODY_HORZSIZE = 49108


def remove_single_lineseg_at_body_width(xml: str, body_horzsize: int) -> tuple:
    """
    `<hp:linesegarray><hp:lineseg ... horzsize="{body_horzsize}" .../></hp:linesegarray>`
    패턴(공백 허용, 단일 lineseg) 을 매칭하여 통째 제거.

    Returns (new_xml, count_removed, removed_samples)
    """
    pattern = re.compile(
        r'<hp:linesegarray\b[^>]*>'
        r'\s*'
        r'<hp:lineseg\b[^/]*'
        r'horzsize="' + str(body_horzsize) + r'"'
        r'[^/]*/>'
        r'\s*'
        r'</hp:linesegarray>'
    )
    removed = []
    def _sub(m):
        removed.append(m.group(0))
        return ''
    new_xml = pattern.sub(_sub, xml)
    return new_xml, len(removed), removed


def process_hwpx(hwpx_path: Path,
                 body_horzsize: int = DEFAULT_BODY_HORZSIZE,
                 dry_run: bool = False, verbose: bool = True) -> dict:
    workdir = Path(tempfile.mkdtemp(prefix="fix_gongmun_"))
    try:
        with zipfile.ZipFile(hwpx_path, "r") as zf:
            zf.extractall(workdir)
        sec_path = workdir / "Contents" / "section0.xml"
        if not sec_path.exists():
            return {"ok": False, "error": "section0.xml 없음"}
        xml = sec_path.read_text(encoding="utf-8")

        if verbose:
            print(f"===== 공문 본문 단락 lineseg 깨짐 후처리 (v3.6.3) =====")
            print(f"  대상: {hwpx_path}")
            print(f"  본문 폭(horzsize): {body_horzsize}")

        new_xml, n_removed, samples = \
            remove_single_lineseg_at_body_width(xml, body_horzsize)

        if verbose:
            print(f"  ✂ 단일 lineseg 본문 단락 linesegarray 제거: {n_removed} 건")
            print(f"     (한글이 파일 열 때 폰트 메트릭으로 lineseg 자동 재계산)")

        if dry_run:
            if verbose:
                print("  (dry-run: 파일 변경 안 함)")
            return {"ok": True, "removed": n_removed, "dry_run": True}

        if n_removed == 0:
            return {"ok": True, "removed": 0}

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
        return {"ok": True, "removed": n_removed}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main():
    p = argparse.ArgumentParser(
        description="공문 본문 단락 자간 압축 깨짐 자동 해소 (v3.6.3)")
    p.add_argument("hwpx", help="처리할 hwpx 파일")
    p.add_argument("--horzsize", type=int, default=DEFAULT_BODY_HORZSIZE,
                   help=f"본문 단락 너비 (기본 {DEFAULT_BODY_HORZSIZE})")
    p.add_argument("--dry-run", action="store_true",
                   help="실제 변경 없이 어떤 단락이 처리될지만 출력")
    args = p.parse_args()
    hwpx = Path(args.hwpx).resolve()
    if not hwpx.exists():
        print(f"❌ 파일 없음: {hwpx}", file=sys.stderr)
        sys.exit(1)
    result = process_hwpx(hwpx, body_horzsize=args.horzsize, dry_run=args.dry_run)
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
