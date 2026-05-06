"""
compose_doc.py
────────────────────────────────────────────────────────────
4단계 통합 워크플로우 실행 스크립트

워크플로우
  ① 콘텐츠 기초데이터 정리       — parse_input
  ② 작성목적 및 서식결정         — pick_format (참조 hwpx 우선)
  ③ 콘텐츠 매핑                 — map_to_format (필수항목 자동 매핑)
  ④ 레이아웃 최적화 편집         — layout_optimizer 적용
  ⑤ HWPX 빌드 + 후처리          — format_builders 호출

사용법:
  python3 compose_doc.py input.md output.hwpx \\
    --format format_1p --reference templates/format_1p/reference.hwpx \\
    --report-path /tmp/optimization_report.md
────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import sys
import json
import argparse
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from layout_optimizer import optimize, render_report
from format_builders import build_by_format
from content_mapper import parse_input
from hwpx_helpers import detect_doc_type


# ═══════════════════════════════════════════════════════════
# 양식 ↔ legacy doc_type 매핑
# ═══════════════════════════════════════════════════════════

LEGACY_TO_FORMAT = {
    'gihoekseo': 'format_full',
    'bogoseo': 'format_1p',
    'gongmun': 'format_gongmun',
    'geomto': 'format_full',
}

# 양식별 콘텐츠 키워드 자동 추천
FORMAT_KEYWORDS = {
    'format_gongmun': ['시행', '공지', '통보', '알림', '협조 요청', '발송', '수신'],
    'format_email': ['메일', '이메일', '회신', '답변', '~님께', '안녕하세요'],
    'format_1p': ['보고', '결과보고', '검토결과', '동향', '한 장으로', '간략'],
    'format_full': ['기획서', '추진계획', '검토보고서', '사업계획', '백서', '분석보고'],
}


def pick_format(parsed: dict, user_hint: str = '', force: str = '') -> str:
    """
    양식 자동 추천.

    우선순위:
      1) force 파라미터 (사용자 명시)
      2) user_hint (자연어 힌트)
      3) 콘텐츠 분량 + 키워드
    """
    if force:
        return force if force.startswith('format_') else LEGACY_TO_FORMAT.get(force, 'format_1p')

    text_all = (parsed.get('title', '') + '\n' +
                '\n'.join(s.get('content', '') for s in parsed.get('sections', [])) +
                '\n' + user_hint).lower()

    # 키워드 매칭
    scores = {}
    for fmt, kws in FORMAT_KEYWORDS.items():
        scores[fmt] = sum(1 for kw in kws if kw in text_all)

    # 가장 점수가 높은 양식
    best = max(scores, key=scores.get)
    if scores[best] >= 2:
        return best

    # 분량 기반 (라인 수 추정)
    line_estimate = sum(s.get('content', '').count('\n') for s in parsed.get('sections', []))
    if line_estimate <= 25:
        return 'format_1p'
    return 'format_full'


# ═══════════════════════════════════════════════════════════
# 콘텐츠 → 양식별 payload 매핑
# ═══════════════════════════════════════════════════════════

def map_to_format(parsed: dict, format_type: str,
                  user_meta: dict = None) -> dict:
    """
    parse_input 결과를 양식별 payload 스키마로 변환.

    누락된 필수 항목은 _missing 리스트로 플래그.
    """
    user_meta = user_meta or {}

    if format_type == 'format_1p':
        return _map_to_1p(parsed, user_meta)
    elif format_type == 'format_full':
        return _map_to_full(parsed, user_meta)
    elif format_type == 'format_gongmun':
        return _map_to_gongmun(parsed, user_meta)
    elif format_type == 'format_email':
        return _map_to_email(parsed, user_meta)
    else:
        raise ValueError(f'알 수 없는 양식: {format_type}')


def _map_to_1p(parsed: dict, meta: dict) -> dict:
    """1페이지 보고서 매핑."""
    sections = parsed.get('sections', [])
    title = parsed.get('title', meta.get('title', '제목 미정 ※AI'))

    # 첫 번째 섹션을 요약문 후보로 사용
    summary = ''
    if sections:
        first_content = sections[0].get('content', '').strip().split('\n')
        for line in first_content:
            line = line.strip().lstrip('-*•').strip()
            if line and len(line) > 15:
                summary = line[:120]
                break

    if not summary:
        summary = f'{title} 관련 내용을 보고드림. ※AI 보완 필요'

    # 섹션을 □ 단위로 변환
    out_sections = []
    for sec in sections[:5]:  # 최대 5개 섹션
        items = []
        for raw in sec.get('content', '').split('\n'):
            raw = raw.strip()
            if not raw:
                continue
            # `-` 또는 `*` 마커 제거
            text = raw.lstrip('-*•○◦').strip()
            if text:
                items.append({'text': text, 'sub': []})
        if items:
            out_sections.append({
                'heading': sec.get('heading', '미정'),
                'items': items,
            })

    # 누락 항목 점검
    missing = []
    headings_str = ' '.join(s['heading'] for s in out_sections)
    if not any(kw in headings_str for kw in ['배경', '계기', '필요']):
        missing.append('추진배경')
    if not any(kw in headings_str for kw in ['계획', '향후', '조치']):
        missing.append('향후계획')

    return {
        'subtitle': meta.get('subtitle', ''),
        'title': title,
        'author': meta.get('author', ''),
        'date': meta.get('date', ''),
        'phone': meta.get('phone', ''),
        'summary': summary,
        'sections': out_sections,
        '_missing': missing,
    }


def _map_to_full(parsed: dict, meta: dict) -> dict:
    """풀버전 보고서 매핑."""
    sections = parsed.get('sections', [])
    title = parsed.get('title', meta.get('title', '제목 미정 ※AI'))

    # 표지
    cover = {
        'subtitle': meta.get('subtitle', ''),
        'title': title,
        'date': meta.get('date', ''),
        'department': meta.get('department', ''),
        'doc_meta': meta.get('doc_meta', {}),
        'approval_line': meta.get('approval_line', []),
    }

    # 목차 - 섹션 타이틀에서 자동 생성
    toc = []
    page_estimate = 4
    roman_chars = ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ', 'Ⅵ', 'Ⅶ', 'Ⅷ']
    for i, sec in enumerate(sections):
        if i >= len(roman_chars):
            break
        toc.append((f'{roman_chars[i]}. {sec.get("heading", "")}', page_estimate))
        page_estimate += max(2, sec.get('content', '').count('\n') // 30 + 1)

    # 보고내용 요약
    summary_secs = []
    for sec in sections[:3]:
        items_raw = sec.get('content', '').split('\n')
        items = [
            line.strip().lstrip('-*•○◦').strip()
            for line in items_raw
            if line.strip() and len(line.strip()) > 5
        ][:5]
        if items:
            summary_secs.append({'heading': sec.get('heading', ''), 'items': items})

    # 본문 chapters
    chapters = []
    for i, sec in enumerate(sections):
        if i >= len(roman_chars):
            break
        ch_sections = []
        # content 를 단락별로 분리해서 절(節)·목(目) 구조 생성
        paras = [p.strip() for p in sec.get('content', '').split('\n\n') if p.strip()]
        for j, p in enumerate(paras[:5]):
            first_line = p.split('\n', 1)[0].strip().lstrip('-*•')
            rest_items = [
                ln.strip().lstrip('-*•○◦').strip()
                for ln in p.split('\n')[1:]
                if ln.strip()
            ]
            ch_sections.append({
                'title': first_line[:40],
                'subsections': [
                    {'title': '주요 내용', 'items': rest_items}
                ] if rest_items else []
            })
        chapters.append({
            'roman': roman_chars[i],
            'title': sec.get('heading', ''),
            'sections': ch_sections,
        })

    # 누락 점검
    missing = []
    headings_str = ' '.join(s.get('heading', '') for s in sections)
    for kw, label in [('배경', '추진배경'), ('계획', '추진계획'),
                       ('일정', '추진일정'), ('예산', '소요예산')]:
        if kw not in headings_str:
            missing.append(label)

    return {
        'cover': cover,
        'toc': toc,
        'toc_appendix': meta.get('toc_appendix', []),
        'summary': {
            'title': '보고내용 요약',
            'sections': summary_secs,
            'side_boxes': meta.get('side_boxes', []),
        },
        'chapters': chapters,
        'appendix': meta.get('appendix', []),
        '_missing': missing,
    }


def _map_to_gongmun(parsed: dict, meta: dict) -> dict:
    """시행문 매핑."""
    sections = parsed.get('sections', [])
    title = parsed.get('title', meta.get('title', '제목 미정 ※AI'))

    # 본문 도입 + 항목들
    main_para = ''
    items = []
    if sections:
        first_content = sections[0].get('content', '').strip().split('\n')
        # 첫 줄을 도입부로
        for line in first_content:
            if line.strip() and len(line.strip()) > 20:
                main_para = line.strip()
                break

    # 가/나/다 마커가 이미 있는 라인 또는 -/* 마커는 가/나/다 자동 부여
    kor = '가나다라마바사아자차카타파하'
    idx = 0
    for sec in sections[1:]:
        for raw in sec.get('content', '').split('\n'):
            raw = raw.strip()
            if not raw:
                continue
            # 이미 가/나/다 마커가 있으면 그대로
            if any(raw.startswith(f'{c}.') for c in kor[:5]):
                items.append(raw)
            else:
                text = raw.lstrip('-*•○◦').strip()
                if text and idx < len(kor):
                    items.append(f'{kor[idx]}. {text}')
                    idx += 1

    return {
        'sender_org': meta.get('sender_org', ''),
        'receiver': meta.get('receiver', '관계 부서장'),
        'via': meta.get('via', ''),
        'title': title,
        'related_clause': meta.get('related_clause', '※ 근거 문서 명시 필요'),
        'main_paragraph': main_para or f'{title} 관련하여 다음과 같이 알려드립니다.',
        'items': items,
        'attachments': meta.get('attachments', []),
        'signature_org': meta.get('signature_org', ''),
        'signature_title': meta.get('signature_title', ''),
        'metadata': meta.get('metadata', {}),
        '_missing': [
            x for x in ['sender_org', 'signature_title']
            if not meta.get(x)
        ],
    }


def _map_to_email(parsed: dict, meta: dict) -> dict:
    """이메일 매핑."""
    sections = parsed.get('sections', [])
    title = parsed.get('title', meta.get('subject', '제목 미정 ※AI'))

    # 첫 섹션 첫 줄을 결론으로
    conclusion = ''
    if sections:
        first_content = sections[0].get('content', '').strip().split('\n')
        for line in first_content:
            if line.strip() and len(line.strip()) > 15:
                conclusion = line.strip().lstrip('-*•').strip()
                break

    # 나머지 섹션은 □ 단위
    out_sections = []
    for sec in sections[1:3]:  # 이메일은 짧게
        items = [
            ln.strip().lstrip('-*•○◦').strip()
            for ln in sec.get('content', '').split('\n')
            if ln.strip()
        ][:4]
        if items:
            out_sections.append({'title': sec.get('heading', ''), 'items': items})

    return {
        'subject': meta.get('subject', f'[{meta.get("dept", "회신")}] {title}'),
        'to': meta.get('to', []),
        'cc': meta.get('cc', []),
        'bcc': meta.get('bcc', []),
        'greeting': meta.get('greeting', '안녕하세요.'),
        'conclusion': conclusion or f'{title} 관련 회신 부탁드립니다.',
        'sections': out_sections,
        'closing': meta.get('closing', '감사합니다.'),
        'signature': meta.get('signature', {}),
        '_missing': [x for x in ['to'] if not meta.get(x)],
    }


# ═══════════════════════════════════════════════════════════
# 메인 파이프라인
# ═══════════════════════════════════════════════════════════

def compose(input_path: str, output_path: str,
            format_type: str = '',
            reference_hwpx: str = '',
            user_meta: dict = None,
            report_path: str = '',
            no_optimize: bool = False) -> dict:
    """
    end-to-end 파이프라인.

    Returns: {'status': 'ok'|'error', 'optimization': {...}, 'missing': [...]}
    """
    user_meta = user_meta or {}
    skill_dir = SCRIPTS_DIR.parent
    summary_info = {}

    # ① 콘텐츠 파싱
    parsed = parse_input(input_path)
    summary_info['parsed_sections'] = len(parsed.get('sections', []))

    # ② 양식 결정
    if not format_type:
        format_type = pick_format(parsed, force=format_type)
    summary_info['format'] = format_type

    # ④ 레이아웃 최적화 (전체 텍스트에 대해)
    full_text = parsed.get('title', '') + '\n\n'
    for sec in parsed.get('sections', []):
        full_text += f'## {sec.get("heading", "")}\n{sec.get("content", "")}\n\n'

    if not no_optimize:
        opt_result = optimize(full_text, doc_type=format_type, auto_apply=True)
        summary_info['line_count'] = opt_result.line_count
        summary_info['page_estimate'] = opt_result.page_estimate
        summary_info['auto_applied'] = len(opt_result.auto_applied())
        summary_info['needs_review'] = len(opt_result.needs_review())

        if report_path:
            Path(report_path).write_text(render_report(opt_result), encoding='utf-8')

        # 최적화된 텍스트로 parsed 갱신 (단순 — 헤딩 구조 유지)
        # 자동 적용된 패턴만 콘텐츠 부분에 반영
        opt_text = opt_result.text
        # parsed.sections 의 content 필드를 갱신 (간이 — 전체를 그대로 못 넣음)
        # 실용적으로는 각 섹션 콘텐츠에 같은 변환을 따로 적용
        from layout_optimizer import apply_high_confidence
        for sec in parsed.get('sections', []):
            new_content, _ = apply_high_confidence(sec.get('content', ''))
            sec['content'] = new_content

    # ③ 콘텐츠 매핑
    payload = map_to_format(parsed, format_type, user_meta=user_meta)
    summary_info['missing'] = payload.get('_missing', [])

    # ⑤ 빌드
    if format_type == 'format_email':
        # 이메일은 텍스트
        from format_builders import build_email_md
        md = build_email_md(payload)
        Path(output_path).write_text(md, encoding='utf-8')
        summary_info['output_type'] = 'markdown'
    else:
        # HWPX 빌드
        section_xml = build_by_format(format_type, payload, reference_hwpx=reference_hwpx)
        section_path = Path('/tmp') / 'compose_section0.xml'
        section_path.write_text(section_xml, encoding='utf-8')

        header_path = skill_dir / 'templates' / 'government' / 'header.xml'

        # build_hwpx
        r = subprocess.run([
            'python3', str(SCRIPTS_DIR / 'build_hwpx.py'),
            '--header', str(header_path),
            '--section', str(section_path),
            '--title', payload.get('title', payload.get('cover', {}).get('title', '문서')),
            '--output', output_path,
        ], capture_output=True, text=True)
        if r.returncode != 0:
            return {'status': 'error', 'stage': 'build_hwpx', 'stderr': r.stderr}

        # fix_namespaces
        r = subprocess.run([
            'python3', str(SCRIPTS_DIR / 'fix_namespaces.py'), output_path
        ], capture_output=True, text=True)
        if r.returncode != 0:
            return {'status': 'error', 'stage': 'fix_namespaces', 'stderr': r.stderr}

        # validate
        r = subprocess.run([
            'python3', str(SCRIPTS_DIR / 'validate.py'), output_path
        ], capture_output=True, text=True)
        summary_info['validation'] = r.stdout
        summary_info['output_type'] = 'hwpx'

    summary_info['status'] = 'ok'
    summary_info['output_path'] = output_path
    return summary_info


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='4단계 통합 워크플로우')
    parser.add_argument('input', help='입력 파일 (md/docx/pdf/txt)')
    parser.add_argument('output', help='출력 파일 (.hwpx 또는 .md)')
    parser.add_argument('--format', dest='format_type', default='',
                        choices=['format_1p', 'format_full', 'format_gongmun', 'format_email', ''],
                        help='양식 (지정 안 하면 자동 추천)')
    parser.add_argument('--reference', default='', help='참조 hwpx 파일 (서식 추출용)')
    parser.add_argument('--meta', default='', help='메타데이터 JSON 파일 (선택)')
    parser.add_argument('--report-path', default='', help='최적화 리포트 저장 경로')
    parser.add_argument('--no-optimize', action='store_true', help='레이아웃 최적화 끄기')
    args = parser.parse_args()

    user_meta = {}
    if args.meta and Path(args.meta).exists():
        user_meta = json.loads(Path(args.meta).read_text(encoding='utf-8'))

    result = compose(
        input_path=args.input,
        output_path=args.output,
        format_type=args.format_type,
        reference_hwpx=args.reference,
        user_meta=user_meta,
        report_path=args.report_path,
        no_optimize=args.no_optimize,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
