"""
wrap_long_titles.py — 풀버전 표지 제목·공문 제목 자동 줄바꿈 후처리 (v3.6.0 신규)
────────────────────────────────────────────────────────────────────────
근본 원인:
  HWPX 양식의 결재제목 셀에 놓인 큰 제목 단락이 *단일* `<hp:linesegarray>` 로
  정의되어 있어서, HY헤드라인M(풀버전) 또는 맑은고딕(공문) 같은 시스템 보유
  폰트로 렌더링될 때 한글2018이 셀 너비에 맞추려고 자간을 음수로 강제 축소함
  (글자 겹침, 가독성 급락). 폰트 미보유 환경(한컴뷰어)에서는 대체 폰트의 넓은
  글자 폭으로 자연 줄바꿈되어 2줄로 정상 표시됨.
  → "한컴뷰어 2줄 = 정상 동작, 한글2018 1줄 압축 = 비정상" 임을 의미.

해결:
  fill_skeleton 으로 토큰을 채운 *후*, section0.xml 안에서
   ① 풀버전 표지 큰 제목 단락 (charPrIDRef="44", 28pt HY헤드라인M)
   ② 공문 제목 단락 (`결재제목` 셀 안의 charPrIDRef="21", 14pt)
  의 텍스트 길이가 임계 글자수를 초과하면 단락을 두 개로 자동 분리해서
  HWPX 단계에서 강제로 2줄 레이아웃을 부여.

사용법:
  python3 wrap_long_titles.py <hwpx_path> [--format full|gongmun|auto]
    --format auto  자동 감지 (기본)
    --dry-run     변경 없이 어떤 단락이 어떻게 분리될지만 출력
"""

import argparse
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


# ──────────────────────────────────────────────────────────────
# 양식별 단락 매칭 규칙
# ──────────────────────────────────────────────────────────────
# 각 규칙은 다음 정보를 가진다:
#   - name: 사람이 읽을 식별자
#   - charpr_id: 매칭할 charPrIDRef (해당 셀의 큰 제목 단락만 잡기 위한 필터)
#   - parapr_id: 매칭할 paraPrIDRef (결재제목 셀 안의 단락 패턴)
#   - max_chars: 이 길이 초과 시 분리 시도 (공백 포함)
#   - font_label: 로그용 폰트 라벨
#
# format_full   text_002 단락은 charPrIDRef="44" + paraPrIDRef="19"
# format_gongmun text_006 단락은 charPrIDRef="21" + paraPrIDRef="17"
RULES = {
    "full": {
        "name": "풀버전 표지 큰 제목",
        "charpr_id": "44",
        "parapr_id": "19",
        "max_chars": 14,        # 28pt × 폰트폭 ≈ 14자 한 줄 한계
        "font_label": "HY헤드라인M 28pt",
    },
    "gongmun": {
        "name": "공문 제목",
        "charpr_id": "21",
        "parapr_id": "17",
        "max_chars": 25,        # 14pt 결재제목 셀 한 줄 한계
        "font_label": "맑은고딕 14pt",
    },
}


# ──────────────────────────────────────────────────────────────
# 분할 알고리즘
# ──────────────────────────────────────────────────────────────
def find_split_point(text: str, max_chars: int) -> int:
    """텍스트를 두 줄로 나눌 공백 인덱스 반환. -1 이면 분할 불필요/불가."""
    text = text.strip()
    if len(text) <= max_chars:
        return -1
    # 공백 위치
    spaces = [i for i, c in enumerate(text) if c == " "]
    if not spaces:
        return -1  # 공백 없으면 분할 불가
    mid = len(text) / 2
    # 1순위: 두 부분 모두 max_chars 이하 + 중앙 근접
    balanced = []
    for s in spaces:
        left_len = s
        right_len = len(text) - s - 1
        if left_len <= max_chars and right_len <= max_chars:
            balanced.append((abs(s - mid), s))
    if balanced:
        balanced.sort()
        return balanced[0][1]
    # 2순위: 그냥 중앙에 가장 가까운 공백 (한쪽이 max_chars 초과해도 차선)
    fallback = [(abs(s - mid), s) for s in spaces]
    fallback.sort()
    return fallback[0][1]


def split_text_at_space(text: str, idx: int) -> tuple:
    """공백 위치 idx 에서 두 부분으로 분리. 공백 자체는 제거."""
    left = text[:idx].rstrip()
    right = text[idx + 1:].lstrip()
    return left, right


# ──────────────────────────────────────────────────────────────
# XML 처리
# ──────────────────────────────────────────────────────────────
def find_title_paragraph(xml: str, charpr_id: str, parapr_id: str):
    """
    `<hp:p ... paraPrIDRef="{parapr_id}" ...> ... <hp:run charPrIDRef="{charpr_id}">
    <hp:t>...</hp:t> ... </hp:run> ... </hp:p>` 블록을 찾아 (start, end, full_block, text)
    를 반환. 없으면 None.

    NOTE: 일반적인 HWPX 결과는 한 줄짜리(개행 없는) XML 이고, hp:p 안에는
    여러 hp:run / hp:linesegarray 가 포함될 수 있다. 가장 안전한 방법은
    paraPrIDRef 매칭 → 그 안에서 charPrIDRef 매칭 → 그 안에서 hp:t 텍스트 추출.
    """
    # paraPr 매칭되는 모든 <hp:p> 블록 찾기
    p_pattern = re.compile(
        r'<hp:p\b[^>]*\bparaPrIDRef="' + re.escape(parapr_id) + r'"[^>]*>'
    )
    for m in p_pattern.finditer(xml):
        p_start = m.start()
        # 짝 맞는 </hp:p> 찾기 (중첩 없다고 가정 — hp:p 는 중첩 불가)
        close_idx = xml.find("</hp:p>", m.end())
        if close_idx == -1:
            continue
        p_end = close_idx + len("</hp:p>")
        block = xml[p_start:p_end]

        # 이 안에 charPrIDRef 매칭되는 run 이 있는지
        run_match = re.search(
            r'<hp:run\b[^>]*\bcharPrIDRef="' + re.escape(charpr_id) + r'"[^>]*>'
            r'(.*?)</hp:run>',
            block, flags=re.DOTALL
        )
        if not run_match:
            continue
        run_inner = run_match.group(1)
        # hp:t 안의 텍스트 추출 (다중 hp:t 가능성 고려)
        text_parts = re.findall(r'<hp:t\b[^>]*>(.*?)</hp:t>', run_inner, flags=re.DOTALL)
        text = "".join(text_parts).strip()
        if text:
            return {
                "start": p_start, "end": p_end,
                "block": block, "text": text,
            }
    return None


def build_split_block(original_block: str, left_text: str, right_text: str) -> str:
    """
    원본 <hp:p> 블록을 복제해 두 개 만들고, 텍스트를 각각 left_text, right_text 로 교체.

    v3.6.4 변경: 두 번째 단락의 `<hp:linesegarray>` 통째 제거. 원본 lineseg 의
    `vertpos` 가 그대로 복사되면 두 단락이 같은 세로 위치에 그려져 한글이 파일을
    거부하는 문제 발생. linesegarray 제거 시 한글이 폰트 메트릭으로 자동 재계산.
    """
    def replace_text_in_block(block: str, new_text: str) -> str:
        replaced = {"done": False}
        def _sub(m):
            if not replaced["done"]:
                replaced["done"] = True
                return f"{m.group(1)}{new_text}{m.group(3)}"
            return f"{m.group(1)}{m.group(3)}"
        pattern = re.compile(r'(<hp:t\b[^>]*>)(.*?)(</hp:t>)', flags=re.DOTALL)
        result = pattern.sub(_sub, block, count=0)
        return result

    def remove_linesegarray(block: str) -> str:
        return re.sub(
            r'<hp:linesegarray\b[^>]*>.*?</hp:linesegarray>',
            '', block, flags=re.DOTALL
        )

    block1 = replace_text_in_block(original_block, left_text)
    # 두 번째 단락은 linesegarray 제거 (vertpos 충돌 방지)
    block2 = replace_text_in_block(original_block, right_text)
    block2 = remove_linesegarray(block2)
    return block1 + block2


def wrap_long_titles_in_xml(xml: str, rules_to_apply: dict, verbose: bool = True):
    """
    xml 텍스트 안의 표지 제목·공문 제목을 분리. (수정된 xml, 적용 로그 list) 반환.
    """
    logs = []
    out = xml
    for fmt_key, rule in rules_to_apply.items():
        found = find_title_paragraph(out, rule["charpr_id"], rule["parapr_id"])
        if not found:
            logs.append(f"  - {rule['name']}: 매칭 단락 없음 (양식 미해당 또는 빈 슬롯)")
            continue
        text = found["text"]
        if len(text) <= rule["max_chars"]:
            logs.append(
                f"  - {rule['name']}: {len(text)}자 ≤ 임계 {rule['max_chars']}자 → 분리 불필요"
            )
            continue
        split_idx = find_split_point(text, rule["max_chars"])
        if split_idx == -1:
            logs.append(
                f"  - {rule['name']}: {len(text)}자, 분할 공백 없음 → 그대로 둠 "
                f"(값에 공백 추가 권장)"
            )
            continue
        left, right = split_text_at_space(text, split_idx)
        new_block = build_split_block(found["block"], left, right)
        # 텍스트 교체
        out = out[:found["start"]] + new_block + out[found["end"]:]
        logs.append(
            f"  ✂ {rule['name']} ({rule['font_label']}): {len(text)}자 → "
            f"[{len(left)}자]+[{len(right)}자]로 분리\n"
            f"      줄1: {left!r}\n"
            f"      줄2: {right!r}"
        )
    return out, logs


# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────
def detect_format(xml: str) -> str:
    """
    section0.xml 안의 charPrIDRef 분포로 양식 추정.
    - charPrIDRef="44" 가 hp:run 에 등장 → 풀버전 (표지 28pt HY헤드라인M)
    - charPrIDRef="21" 단락이 결재제목 셀에 있고 hp:run 이 charPrIDRef="44" 없음 → 공문
    auto 모드는 둘 다 시도해도 무관 (매칭 안 되면 스킵).
    """
    return "both"


def process_hwpx(hwpx_path: Path, fmt: str = "auto",
                 dry_run: bool = False, verbose: bool = True) -> dict:
    """hwpx 파일을 열어 section0.xml 의 긴 제목 단락을 자동 분리하고 다시 저장."""
    workdir = Path(tempfile.mkdtemp(prefix="wrap_titles_"))
    try:
        with zipfile.ZipFile(hwpx_path, "r") as zf:
            zf.extractall(workdir)
        sec_path = workdir / "Contents" / "section0.xml"
        if not sec_path.exists():
            return {"ok": False, "error": "section0.xml 없음"}
        xml = sec_path.read_text(encoding="utf-8")

        # 적용 규칙 결정
        if fmt == "full":
            rules = {"full": RULES["full"]}
        elif fmt == "gongmun":
            rules = {"gongmun": RULES["gongmun"]}
        else:  # auto / both
            rules = RULES

        if verbose:
            print(f"===== 긴 제목 자동 줄바꿈 후처리 =====")
            print(f"  대상: {hwpx_path}")
            print(f"  적용 양식: {fmt}")

        new_xml, logs = wrap_long_titles_in_xml(xml, rules, verbose=verbose)
        if verbose:
            for ln in logs:
                print(ln)

        if dry_run:
            if verbose:
                print("  (dry-run: 파일 변경 안 함)")
            return {"ok": True, "changed": new_xml != xml, "logs": logs, "dry_run": True}

        if new_xml == xml:
            if verbose:
                print("  → 변경사항 없음 (임계 미만이거나 매칭 단락 없음)")
            return {"ok": True, "changed": False, "logs": logs}

        # 저장
        sec_path.write_text(new_xml, encoding="utf-8")
        # 재패키징
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
        return {"ok": True, "changed": True, "logs": logs}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main():
    p = argparse.ArgumentParser(
        description="긴 표지/공문 제목 자동 줄바꿈 후처리 (v3.6.0)")
    p.add_argument("hwpx", help="처리할 hwpx 파일")
    p.add_argument("--format", choices=["full", "gongmun", "auto"], default="auto",
                   help="적용 양식 (기본: auto)")
    p.add_argument("--dry-run", action="store_true",
                   help="실제 변경 없이 어떤 단락이 어떻게 분리될지만 출력")
    args = p.parse_args()
    hwpx = Path(args.hwpx).resolve()
    if not hwpx.exists():
        print(f"❌ 파일 없음: {hwpx}", file=sys.stderr)
        sys.exit(1)
    result = process_hwpx(hwpx, fmt=args.format, dry_run=args.dry_run)
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
