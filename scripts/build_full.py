"""
build_full.py — 풀버전 보고서 통합 빌드 워크플로우 (v3.5.0 신규)
────────────────────────────────────────────────────────────────
풀버전 보고서(format_full) 빌드 시 발생했던 4가지 함정을 자동 처리:

  ① 목차 슬롯 위계 위반 검사
     - 양식의 대제목 슬롯 위치(001,003,013,021,033,043) 에 Ⅰ~Ⅵ 매핑 여부 확인
     - 소제목 슬롯에 "1.~5." 형태 매핑 여부 확인
     - 위반 시 경고 출력

  ② 빈 슬롯으로 인한 점선 끊김 점검
     - 목차 텍스트 슬롯 중 빈 값 개수 카운트
     - 일정 비율 이상 비면 양식 레이아웃 무너짐 경고

  ③ 본문 마커 중복 점검
     - 본문_항목_001~009: paraPr 자동 ○ 마커 → 콘텐츠에 ◦ 직접 표기 금지
     - 본문_항목_010~012: 양식 원본에 ◦ 마커 → 콘텐츠에도 ◦ 직접 표기 필요
     - 위반 시 경고

  ④ 페이지번호 자동 매핑 → hwpx 직접 반영 (재빌드)

워크플로우:
  1) values 입력 점검 (위 ①②③ 검사)
  2) 1차 빌드 (페이지번호는 임시값)
  3) 페이지 시뮬레이션
  4) values 에 페이지번호 병합
  5) 2차 빌드 (최종)
  6) 후처리 (fix_namespaces + ensure_body_anchor + validate)

사용법:
    python build_full.py \\
        --values my_values.json \\
        --output result.hwpx \\
        [--skeleton templates/format_full/skeleton.hwpx] \\
        [--mapping templates/format_full/skeleton_mapping.json] \\
        [--strict]   # 위반 발견 시 빌드 중단
────────────────────────────────────────────────────────────────
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


# ────────────────────────────────────────────────
# 양식 명세 (format_full 한정)
# ────────────────────────────────────────────────

# 대제목 슬롯 (Ⅰ~Ⅵ 들어가는 자리)
CHAPTER_SLOTS = ["목차_항목_001", "목차_항목_003", "목차_항목_013",
                 "목차_항목_021", "목차_항목_033", "목차_항목_043"]

# 소제목 슬롯 (장별 분포)
SUBSECTION_SLOTS_BY_CHAPTER = {
    "Ⅰ": [],
    "Ⅱ": ["목차_항목_005", "목차_항목_007", "목차_항목_009", "목차_항목_011"],
    "Ⅲ": ["목차_항목_015", "목차_항목_017", "목차_항목_019"],
    "Ⅳ": ["목차_항목_023", "목차_항목_025", "목차_항목_027",
          "목차_항목_029", "목차_항목_031"],
    "Ⅴ": ["목차_항목_035", "목차_항목_037", "목차_항목_039", "목차_항목_041"],
    "Ⅵ": ["목차_항목_045", "목차_항목_047", "목차_항목_049", "목차_항목_051"],
}

# 본문 항목 슬롯 마커 패턴
# 자동 마커(○): 콘텐츠에 ◦ 직접 표기 금지
AUTO_MARKER_ITEMS = [f"본문_항목_{i:03d}" for i in range(1, 10)]
# 직접 표기: 양식 원본에 ◦ 가 있으므로 콘텐츠에도 ◦ 표기 필요
DIRECT_MARKER_ITEMS = [f"본문_항목_{i:03d}" for i in range(10, 13)]


def check_chapter_slot_hierarchy(values: dict) -> list:
    """① 대제목 슬롯에 Ⅰ~Ⅵ 가, 소제목 슬롯에 1.~5. 가 들어갔는지 검사"""
    warnings = []

    for slot in CHAPTER_SLOTS:
        v = values.get(slot, "").strip()
        if not v:
            continue
        if not any(v.startswith(r) for r in
                   ["Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ", "Ⅵ", "Ⅶ", "Ⅷ", "Ⅸ", "Ⅹ"]):
            warnings.append(
                f"⚠️  [위계 위반] {slot} 은 대제목(Ⅰ~Ⅵ) 슬롯인데 "
                f"값={v!r} 으로 매핑됨. 양식 서식이 깨질 수 있습니다.")

    for chapter, slots in SUBSECTION_SLOTS_BY_CHAPTER.items():
        for slot in slots:
            v = values.get(slot, "").strip()
            if not v:
                continue
            # 소제목 패턴: "1.", "2." 등으로 시작
            if not re.match(r"^\d+\.\s*", v):
                warnings.append(
                    f"⚠️  [위계 위반] {slot} 은 {chapter}장 소제목 슬롯인데 "
                    f"값={v!r} 으로 매핑됨. 양식 서식이 깨질 수 있습니다.")

    return warnings


def check_empty_toc_slots(values: dict) -> list:
    """② 목차 텍스트 슬롯 빈 값 개수 점검"""
    warnings = []
    all_text_slots = CHAPTER_SLOTS[:]
    for slots in SUBSECTION_SLOTS_BY_CHAPTER.values():
        all_text_slots.extend(slots)

    empty_slots = [s for s in all_text_slots
                   if not values.get(s, "").strip()]
    if empty_slots:
        ratio = len(empty_slots) / len(all_text_slots)
        if ratio > 0.2:  # 20% 초과
            warnings.append(
                f"⚠️  [레이아웃] 목차 텍스트 슬롯 {len(empty_slots)}/"
                f"{len(all_text_slots)}개 ({ratio:.0%})가 비어 있습니다. "
                f"양식의 점선·페이지번호 정렬이 무너질 수 있습니다.\n"
                f"    빈 슬롯: {empty_slots[:5]}{'...' if len(empty_slots)>5 else ''}\n"
                f"    → 콘텐츠를 양식 슬롯 수에 맞춰 확장 권장")
    return warnings


def check_body_marker_consistency(values: dict) -> list:
    """③ 본문_항목 슬롯 마커 패턴 검사"""
    warnings = []

    for slot in AUTO_MARKER_ITEMS:
        v = values.get(slot, "")
        if v and ("◦" in v[:5] or "○" in v[:5]):
            warnings.append(
                f"⚠️  [마커 중복] {slot} 은 paraPr 자동 ○ 마커 슬롯인데 "
                f"콘텐츠에 ◦/○ 가 직접 들어있습니다 → 마커 중복 표기 발생.\n"
                f"    값={v!r}\n"
                f"    → ◦ 를 제거하고 텍스트만 남기세요.")

    for slot in DIRECT_MARKER_ITEMS:
        v = values.get(slot, "")
        if v and "◦" not in v[:5] and "○" not in v[:5]:
            warnings.append(
                f"⚠️  [마커 누락] {slot} 은 양식 원본에 ◦ 마커가 있는 슬롯입니다. "
                f"콘텐츠에도 ◦ 를 직접 넣으세요.\n"
                f"    현재값={v!r}")

    return warnings


def run_script(script_name: str, *args) -> bool:
    """scripts/ 안의 보조 스크립트 실행"""
    cmd = [sys.executable, str(SCRIPT_DIR / script_name)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ {script_name} 실패:")
        print(result.stderr)
        return False
    print(result.stdout.rstrip())
    return True


def main():
    parser = argparse.ArgumentParser(
        description="풀버전 보고서 통합 빌드 (v3.5.0)")
    parser.add_argument("--values", required=True,
                        help="사용자 values.json")
    parser.add_argument("--output", required=True,
                        help="출력 hwpx 경로")
    parser.add_argument("--skeleton",
                        default=str(SCRIPT_DIR.parent / "templates"
                                    / "format_full" / "skeleton.hwpx"),
                        help="빈 골격 hwpx (기본: format_full/skeleton.hwpx)")
    parser.add_argument("--mapping",
                        default=str(SCRIPT_DIR.parent / "templates"
                                    / "format_full" / "skeleton_mapping.json"),
                        help="skeleton_mapping.json (페이지번호 매핑용)")
    parser.add_argument("--strict", action="store_true",
                        help="위계·마커 위반 발견 시 빌드 중단")
    args = parser.parse_args()

    values_path = Path(args.values).resolve()
    skeleton_path = Path(args.skeleton).resolve()
    mapping_path = Path(args.mapping).resolve()
    output_path = Path(args.output).resolve()

    # ────────────────────────────────────────────
    # 단계 1: values 입력 점검
    # ────────────────────────────────────────────
    print("===== 단계 1: 입력 검사 =====")
    values = json.loads(values_path.read_text(encoding="utf-8"))

    all_warnings = []
    all_warnings += check_chapter_slot_hierarchy(values)
    all_warnings += check_empty_toc_slots(values)
    all_warnings += check_body_marker_consistency(values)

    if all_warnings:
        for w in all_warnings:
            print(w)
        if args.strict:
            print("\n❌ --strict 모드: 위반 사항으로 빌드 중단")
            sys.exit(1)
        print(f"\n⚠️  경고 {len(all_warnings)}건 — 계속 진행합니다 "
              f"(--strict 시 중단됨)")
    else:
        print("✅ 입력 검사 통과")

    # ────────────────────────────────────────────
    # 단계 2: 1차 빌드 (페이지번호 임시값)
    # ────────────────────────────────────────────
    print("\n===== 단계 2: 1차 빌드 =====")
    tmp_hwpx = tempfile.NamedTemporaryFile(suffix=".hwpx", delete=False).name
    if not run_script("fill_skeleton.py",
                      "--skeleton", str(skeleton_path),
                      "--values", str(values_path),
                      "--output", tmp_hwpx):
        sys.exit(1)

    if not run_script("fix_namespaces.py", tmp_hwpx):
        sys.exit(1)

    # ────────────────────────────────────────────
    # 단계 3: 페이지 시뮬레이션 + values 자동 갱신
    # ────────────────────────────────────────────
    print("\n===== 단계 3: 페이지번호 자동 계산 =====")
    # 임시 values 사본을 만들어 그것을 갱신 (원본은 보존)
    work_values = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8")
    work_values.write(json.dumps(values, ensure_ascii=False, indent=2))
    work_values.close()

    if not run_script("simulate_pages.py", tmp_hwpx,
                      "--mapping", str(mapping_path),
                      "--values", work_values.name,
                      "--apply-to-values"):
        sys.exit(1)

    # ────────────────────────────────────────────
    # 단계 4: 2차 빌드 (페이지번호 반영된 최종본)
    # ────────────────────────────────────────────
    print("\n===== 단계 4: 2차 빌드 (페이지번호 반영) =====")
    if not run_script("fill_skeleton.py",
                      "--skeleton", str(skeleton_path),
                      "--values", work_values.name,
                      "--output", str(output_path)):
        sys.exit(1)

    # ────────────────────────────────────────────
    # 단계 5: 후처리
    # ────────────────────────────────────────────
    print("\n===== 단계 5: 후처리 =====")
    if not run_script("fix_namespaces.py", str(output_path)):
        sys.exit(1)
    if not run_script("ensure_body_anchor.py", str(output_path)):
        sys.exit(1)
    # v3.6.0: 표지 큰 제목이 셀 너비 초과 시 한글2018에서 자간 압축으로 깨지는 문제 방지
    if not run_script("wrap_long_titles.py", str(output_path), "--format", "full"):
        sys.exit(1)
    # v3.6.1: 목차 점선 tab width 통일 (한글2018 폰트 보유 시 점선/페이지번호 깨짐 방지)
    if not run_script("fix_toc_dots.py", str(output_path)):
        sys.exit(1)
    if not run_script("validate.py", str(output_path)):
        sys.exit(1)

    # 임시 파일 정리
    Path(tmp_hwpx).unlink(missing_ok=True)
    Path(work_values.name).unlink(missing_ok=True)

    print(f"\n✅ 완료: {output_path}")


if __name__ == "__main__":
    main()
