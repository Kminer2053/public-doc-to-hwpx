"""
layout_optimizer.py
────────────────────────────────────────────────────────────
콘텐츠 텍스트의 레이아웃 최적화 처리

기능
  1) 적/의/것/들 등 군더더기 표현 자동 정리 (writing-principles.md 기반)
  2) 한 문장 한 줄 원칙 점검 (45자 초과 분리 후보 식별)
  3) 페이지 라인 수 추정 (페이지 걸침 위험 사전 감지)
  4) 글머리 위계 일관성 점검 (체계 A: □○-* / 체계 B: 1.가.(1)(가))
  5) 보고서 구성 항목 누락 점검 (배경/현황/해결방안/기대효과)
  6) Before/After 비교 리포트 생성

설계 원칙
  - "신뢰도 높음" 변환만 자동 적용
  - "신뢰도 중간"은 후보로 표시만 (사용자 확인용)
  - 모든 변환은 trace 가능 (어떤 규칙이 어떤 곳에 적용되었는지)
────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional

# ═══════════════════════════════════════════════════════════
# 상수
# ═══════════════════════════════════════════════════════════

# 한 줄 기준 (한글 11pt, 본문폭 42,520 HWPUNIT 기준)
LINE_THRESHOLD_OK = 35      # 안전
LINE_THRESHOLD_WARN = 45    # 검토 권장
LINE_THRESHOLD_FORCE = 46   # 자동 분리 후보

# 페이지 라인 수 (양식별)
LINES_PER_PAGE = {
    'format_1p': 38,         # 1p 보고서 (강제 1쪽)
    'format_full': 40,       # 풀버전 본문
    'format_gongmun': 35,    # 시행문 (여백이 더 큼)
    'format_email': 9999,    # 이메일은 페이지 개념 없음
}

# 양식별 글머리 위계
HIERARCHY_TOKENS = {
    'A': ['□', '○', '-', '*', '※'],
    'B': ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ', '1', '가', '1)', '가)', '(1)', '(가)', '①', '㉮'],
}


# ═══════════════════════════════════════════════════════════
# 데이터 클래스
# ═══════════════════════════════════════════════════════════

@dataclass
class Issue:
    kind: str           # 'long_sentence' | 'jeok' | 'ui' | 'geot' | 'deul' | ...
    location: str       # 라인 인덱스 또는 섹션
    severity: str       # 'auto' | 'review' | 'warn' | 'block'
    before: str
    after: Optional[str] = None  # 자동 변환된 경우
    note: str = ''


@dataclass
class OptimizationResult:
    text: str                              # 최적화된 텍스트
    issues: list[Issue] = field(default_factory=list)
    page_estimate: int = 0
    line_count: int = 0
    missing_sections: list[str] = field(default_factory=list)
    hierarchy_system: Optional[str] = None  # 'A' | 'B' | None | 'mixed'

    def auto_applied(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == 'auto']

    def needs_review(self) -> list[Issue]:
        return [i for i in self.issues if i.severity in ('review', 'warn', 'block')]


# ═══════════════════════════════════════════════════════════
# [1] 군더더기 표현 자동 정리
# ═══════════════════════════════════════════════════════════

# 신뢰도 "높음" — 자동 적용 (문맥 안정적인 패턴만)
HIGH_CONFIDENCE_RULES = [
    # (regex, replacement, kind, note)
    (r'와\s*관련된\s+', '와 관련 ', 'wakwallyeon', '~와 관련된 → ~와 관련'),
    (r'과\s*관련된\s+', '과 관련 ', 'gwagwallyeon', '~과 관련된 → ~과 관련'),
    # 할 예정이었으나 이를 유예/연기/보류 — 안정적
    (r'할\s*예정이었으나\s*이를\s*유예하였습니다', ' 예정 → 유예', 'yeyu', '~할 예정이었으나 이를 유예하였습니다 → ~ 예정 → 유예'),
    (r'할\s*예정이었으나\s*이를\s*연기하였습니다', ' 예정 → 연기', 'yeyu', '~할 예정이었으나 이를 연기하였습니다 → ~ 예정 → 연기'),
    (r'할\s*예정이었으나\s*이를\s*보류하였습니다', ' 예정 → 보류', 'yeyu', '~할 예정이었으나 이를 보류하였습니다 → ~ 예정 → 보류'),
    # 복수 표현 들 — 안정적
    (r'여러\s+([가-힣]+)들', r'여러 \1', 'deul', '여러 ~들 → 여러 ~'),
    (r'많은\s+([가-힣]+)들', r'많은 \1', 'deul', '많은 ~들 → 많은 ~'),
    (r'각\s+([가-힣]+)들', r'각 \1', 'deul', '각 ~들 → 각 ~'),
    (r'모든\s+([가-힣]+)들', r'모든 \1', 'deul', '모든 ~들 → 모든 ~'),
    (r'수많은\s+([가-힣]+)들', r'수많은 \1', 'deul', '수많은 ~들 → 수많은 ~'),
    (r'대부분의\s+([가-힣]+)들', r'대부분의 \1', 'deul', '대부분의 ~들 → 대부분의 ~'),
    (r'다양한\s+([가-힣]+)들', r'다양한 \1', 'deul', '다양한 ~들 → 다양한 ~'),
]

# 신뢰도 "중" — 후보로 표시만 (자동 적용 안 함, 사용자 검토 필요)
MEDIUM_CONFIDENCE_PATTERNS = [
    # ~할 것으로 보입니다 등 - 동사 어미와 연결되어 있어 단순 치환 위험
    (r'할\s*것으로\s*보입니다', 'geotseuro_a', '~할 것으로 보입니다 → ~ 예상 / ~ 전망 (동사 변형 필요)'),
    (r'한\s*것으로\s*판단됩니다', 'geotseuro_b', '~한 것으로 판단됩니다 → ~ 판단 / ~로 보임 (앞 어미 변형 필요)'),
    (r'한\s*것으로\s*확인됩니다', 'geotseuro_c', '~한 것으로 확인됩니다 → ~ 확인 (어미 변형 필요)'),
    (r'될\s*것으로\s*예상됩니다', 'geotseuro_d', '~될 것으로 예상됩니다 → ~ 예상'),
    (r'하는\s*것이\s*필요합니다', 'haneun_geot_a', '~하는 것이 필요합니다 → ~가 필요합니다 (앞 어미 변형 필요)'),
    (r'하는\s*것이\s*중요합니다', 'haneun_geot_b', '~하는 것이 중요합니다 → ~가 중요합니다 (앞 어미 변형 필요)'),
    # 일반 ~에 대한
    (r'에\s+대한\s+', 'edaehan', '~에 대한 → 생략 또는 동사형 검토'),
    # 중 하나인
    (r'중\s+하나인\s+', 'jung_hanain', '~ 중 하나인 → 대표적인 또는 생략'),
    # 한 문장에 의 2번 이상
    (r'(?:[가-힣]+의\s+){2,}', 'multi_ui', '의 연쇄 (2회 이상) - 압축 검토'),
    # 적 (명사 직전, 강조 의도가 아닌 경우)
    (r'(사회|경제|정치|행정|조직|기술|사업|업무|제도)적\s+([가-힣]+)', 'jeok', '~적 ~ → 빼도 의미 유지되는지 검토'),
]


def apply_high_confidence(text: str) -> tuple[str, list[Issue]]:
    """신뢰도 높은 변환 자동 적용. (변환 후 텍스트, 이슈 리스트) 반환."""
    issues: list[Issue] = []
    out = text
    for pattern, repl, kind, note in HIGH_CONFIDENCE_RULES:
        for m in re.finditer(pattern, out):
            issues.append(Issue(
                kind=kind, location=f'pos:{m.start()}', severity='auto',
                before=m.group(), after=re.sub(pattern, repl, m.group()),
                note=note
            ))
        out = re.sub(pattern, repl, out)
    return out, issues


def detect_medium_confidence(text: str) -> list[Issue]:
    """신뢰도 중간 패턴은 검토 후보로만 표시."""
    issues: list[Issue] = []
    for pattern, kind, note in MEDIUM_CONFIDENCE_PATTERNS:
        for m in re.finditer(pattern, text):
            issues.append(Issue(
                kind=kind, location=f'pos:{m.start()}', severity='review',
                before=m.group(), note=note
            ))
    return issues


# ═══════════════════════════════════════════════════════════
# [2] 한 문장 한 줄 점검
# ═══════════════════════════════════════════════════════════

def estimate_line_count(text: str) -> int:
    """
    한글 11pt 본문 기준, 한 줄 ~38자 가정.
    줄바꿈 + 긴 줄의 자동 줄바꿈을 합산.
    """
    if not text:
        return 0
    total = 0
    for line in text.split('\n'):
        if not line.strip():
            total += 1  # 빈 줄도 1줄
        else:
            # 긴 줄은 38자 단위로 줄바꿈
            # 한글 1자 = 1단위, 영문/숫자는 0.5단위로 가산
            visual_len = sum(1.0 if ord(c) > 0x7F else 0.5 for c in line)
            total += max(1, int(visual_len / 38) + (1 if visual_len % 38 else 0))
    return total


def check_long_sentences(text: str) -> list[Issue]:
    """문장이 LINE_THRESHOLD_FORCE 이상이면 분리 후보로 표시."""
    issues: list[Issue] = []
    # 문장 분리: 마침표·물음표·느낌표 + 공백 또는 줄바꿈
    sentences = re.split(r'(?<=[.?!])\s+|\n', text)
    for i, s in enumerate(sentences):
        s = s.strip()
        if not s:
            continue
        visual_len = sum(1.0 if ord(c) > 0x7F else 0.5 for c in s)
        if visual_len > LINE_THRESHOLD_FORCE:
            issues.append(Issue(
                kind='long_sentence', location=f'sentence:{i}',
                severity='review' if visual_len < 60 else 'warn',
                before=s,
                note=f'{visual_len:.0f}자 — 분리 권장'
            ))
        elif visual_len > LINE_THRESHOLD_WARN:
            issues.append(Issue(
                kind='long_sentence_warn', location=f'sentence:{i}',
                severity='review',
                before=s,
                note=f'{visual_len:.0f}자 — 검토 권장'
            ))
    return issues


# ═══════════════════════════════════════════════════════════
# [3] 글머리 위계 점검
# ═══════════════════════════════════════════════════════════

def detect_hierarchy_system(text: str) -> str:
    """'A' (□○-*) / 'B' (1.가.(1)(가)) / 'mixed' / 'none' 반환."""
    has_a = bool(re.search(r'^[\s]*[□○*※]\s|^\s*-\s', text, re.MULTILINE))
    has_b = bool(re.search(r'^\s*(?:Ⅰ|Ⅱ|Ⅲ|Ⅳ|Ⅴ)\.\s|^\s*\d+\.\s|^\s*[가나다라마]\.\s|^\s*\(\d+\)\s|^\s*\([가나다]\)\s', text, re.MULTILINE))
    if has_a and has_b:
        return 'mixed'
    if has_a:
        return 'A'
    if has_b:
        return 'B'
    return 'none'


def check_hierarchy(text: str, expected: Optional[str] = None) -> list[Issue]:
    """글머리 위계 일관성 점검."""
    issues: list[Issue] = []
    detected = detect_hierarchy_system(text)
    if detected == 'mixed':
        issues.append(Issue(
            kind='hierarchy_mixed', location='document', severity='warn',
            before='', note='체계 A(□○-*)와 체계 B(1.가.(1))가 혼용됨 — 한 체계로 통일 필요'
        ))
    if expected and detected not in ('none', expected):
        issues.append(Issue(
            kind='hierarchy_wrong', location='document', severity='review',
            before=detected, note=f'양식은 체계 {expected}을 권장하나 체계 {detected}이 사용됨'
        ))
    return issues


# ═══════════════════════════════════════════════════════════
# [4] 필수 항목 누락 점검
# ═══════════════════════════════════════════════════════════

REQUIRED_SECTIONS = {
    'format_1p': ['배경', '내용', '계획'],            # 추진배경/주요내용/향후계획 (느슨한 매칭)
    'format_full': ['배경', '계획', '일정', '예산'],
    'format_gongmun': ['수신', '제목', '본문', '발신'],
    'format_email': ['제목', '받는사람', '본문'],
    'gihoekseo': ['추진배경', '현황', '추진방향', '세부', '기대효과'],
    'bogoseo': ['개요', '추진현황', '세부내용', '문제점', '향후'],
    'geomto': ['검토배경', '관련', '검토 내용', '쟁점', '검토 의견'],
}


def check_missing_sections(text: str, doc_type: str) -> list[str]:
    """필수 섹션 누락 검출. 누락된 키워드 리스트 반환."""
    required = REQUIRED_SECTIONS.get(doc_type, [])
    missing = []
    text_lower = text.lower()
    for kw in required:
        # 느슨한 부분 일치 (한글이라 lower는 의미 없음)
        if kw not in text:
            missing.append(kw)
    return missing


# ═══════════════════════════════════════════════════════════
# [5] 페이지 걸침 위험 점검
# ═══════════════════════════════════════════════════════════

def estimate_page_count(text: str, doc_type: str) -> tuple[int, int]:
    """(추정 페이지 수, 추정 라인 수) 반환."""
    lines = estimate_line_count(text)
    per_page = LINES_PER_PAGE.get(doc_type, 38)
    pages = max(1, (lines + per_page - 1) // per_page)
    return pages, lines


def check_page_overflow(text: str, doc_type: str) -> list[Issue]:
    """양식 분량 초과 점검."""
    issues: list[Issue] = []
    pages, lines = estimate_page_count(text, doc_type)

    if doc_type == 'format_1p' and pages > 1:
        issues.append(Issue(
            kind='overflow_1p', location='document', severity='block',
            before=f'{lines} 줄 (약 {pages} 쪽)',
            note=f'1p 보고서가 1쪽({LINES_PER_PAGE["format_1p"]}줄)을 초과합니다. 압축 또는 풀버전 변경 권고.'
        ))
    elif doc_type == 'format_email' and lines > 25:
        issues.append(Issue(
            kind='overflow_email', location='document', severity='warn',
            before=f'{lines} 줄',
            note='이메일이 25줄을 초과합니다. 1p 보고서 + 안내 메일로 분리 권고.'
        ))
    elif doc_type == 'format_gongmun' and pages > 1:
        issues.append(Issue(
            kind='overflow_gongmun', location='document', severity='warn',
            before=f'{lines} 줄 (약 {pages} 쪽)',
            note='시행문은 1쪽 안에 끝나는 것이 표준입니다. 별첨으로 분리 권고.'
        ))
    return issues


# ═══════════════════════════════════════════════════════════
# [6] 통합 최적화 함수
# ═══════════════════════════════════════════════════════════

def optimize(text: str, doc_type: str = 'format_1p',
             auto_apply: bool = True) -> OptimizationResult:
    """
    통합 최적화 처리.

    Parameters
    ----------
    text : str
        원본 콘텐츠 텍스트 (마크다운/플레인텍스트)
    doc_type : str
        'format_1p' | 'format_full' | 'format_gongmun' | 'format_email'
        혹은 'gihoekseo' | 'bogoseo' | 'geomto' (legacy)
    auto_apply : bool
        True이면 신뢰도 높음 규칙 자동 적용. False이면 검출만.

    Returns
    -------
    OptimizationResult
    """
    out = text
    all_issues: list[Issue] = []

    # 1. 신뢰도 높음 자동 적용
    if auto_apply:
        out, auto_issues = apply_high_confidence(out)
        all_issues.extend(auto_issues)

    # 2. 신뢰도 중간 검토 후보 검출
    all_issues.extend(detect_medium_confidence(out))

    # 3. 한 문장 한 줄 점검
    all_issues.extend(check_long_sentences(out))

    # 4. 글머리 위계 점검
    expected_system = {
        'format_1p': 'A',
        'format_full': 'B',
        'format_gongmun': 'B',
        'format_email': 'A',
    }.get(doc_type)
    all_issues.extend(check_hierarchy(out, expected_system))

    # 5. 필수 항목 누락 점검
    missing = check_missing_sections(out, doc_type)

    # 6. 페이지 걸침 점검
    all_issues.extend(check_page_overflow(out, doc_type))

    pages, lines = estimate_page_count(out, doc_type)

    return OptimizationResult(
        text=out,
        issues=all_issues,
        page_estimate=pages,
        line_count=lines,
        missing_sections=missing,
        hierarchy_system=detect_hierarchy_system(out),
    )


# ═══════════════════════════════════════════════════════════
# [7] 리포트 생성 (사용자에게 보여줄 Before/After)
# ═══════════════════════════════════════════════════════════

def render_report(result: OptimizationResult) -> str:
    """최적화 결과를 사람이 읽기 좋은 마크다운 리포트로."""
    lines = []
    lines.append('# 레이아웃 최적화 리포트')
    lines.append('')
    lines.append(f'- **추정 분량**: {result.line_count} 줄 (약 {result.page_estimate} 쪽)')
    lines.append(f'- **글머리 위계**: 체계 {result.hierarchy_system}')
    lines.append(f'- **자동 적용**: {len(result.auto_applied())} 건')
    lines.append(f'- **검토 권장**: {len(result.needs_review())} 건')
    if result.missing_sections:
        lines.append(f'- **누락 항목**: {", ".join(result.missing_sections)} ※ AI 보완 필요')
    lines.append('')

    auto = result.auto_applied()
    if auto:
        lines.append('## 자동 적용된 변환')
        lines.append('')
        lines.append('| # | 변환 전 | 변환 후 | 규칙 |')
        lines.append('|---|---------|---------|------|')
        for i, issue in enumerate(auto[:20], 1):  # 너무 많으면 20개만
            before = (issue.before or '').replace('|', '\\|')[:30]
            after = (issue.after or '').replace('|', '\\|')[:30]
            lines.append(f'| {i} | {before} | {after} | {issue.note} |')
        if len(auto) > 20:
            lines.append(f'| ... | ... | ... | (총 {len(auto)} 건 중 20건만 표시) |')
        lines.append('')

    review = result.needs_review()
    if review:
        lines.append('## 검토 권장 사항')
        lines.append('')
        for issue in review[:15]:
            sev = {'review': '🔍', 'warn': '⚠️', 'block': '🚫'}.get(issue.severity, '•')
            before_short = (issue.before or '')[:60]
            lines.append(f'- {sev} **[{issue.kind}]** {issue.note}')
            if before_short:
                lines.append(f'  - "_{before_short}_"')
        if len(review) > 15:
            lines.append(f'- ... (총 {len(review)} 건 중 15건만 표시)')
        lines.append('')

    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    import json
    from pathlib import Path

    if len(sys.argv) < 2:
        print('Usage: python layout_optimizer.py <input> [--doc-type TYPE] [--no-auto] [--output FILE]')
        print('  --doc-type: format_1p (default) | format_full | format_gongmun | format_email')
        print('  --no-auto: 자동 변환 끄기 (검출만)')
        print('  --output: 결과 저장 경로 (기본: stdout)')
        sys.exit(1)

    args = sys.argv[1:]
    input_path = args[0]
    doc_type = 'format_1p'
    auto = True
    output_path = None

    i = 1
    while i < len(args):
        if args[i] == '--doc-type' and i + 1 < len(args):
            doc_type = args[i + 1]
            i += 2
        elif args[i] == '--no-auto':
            auto = False
            i += 1
        elif args[i] == '--output' and i + 1 < len(args):
            output_path = args[i + 1]
            i += 2
        else:
            i += 1

    text = Path(input_path).read_text(encoding='utf-8')
    result = optimize(text, doc_type=doc_type, auto_apply=auto)
    report = render_report(result)

    print(report)
    print()
    print('---')
    print('## 최적화된 텍스트')
    print()
    print(result.text)

    if output_path:
        Path(output_path).write_text(result.text, encoding='utf-8')
        json_meta = {
            'doc_type': doc_type,
            'page_estimate': result.page_estimate,
            'line_count': result.line_count,
            'auto_applied_count': len(result.auto_applied()),
            'review_count': len(result.needs_review()),
            'missing_sections': result.missing_sections,
            'hierarchy_system': result.hierarchy_system,
        }
        Path(output_path + '.meta.json').write_text(
            json.dumps(json_meta, ensure_ascii=False, indent=2), encoding='utf-8'
        )
