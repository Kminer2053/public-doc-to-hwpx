"""
format_builders.py
────────────────────────────────────────────────────────────
4개 양식 (1p / full / gongmun / email) 별 고수준 빌더

설계 원칙
  - hwpx_helpers.py 의 저수준 함수(make_text_para, make_body_para 등) 를 조합
  - 양식별 secPr 추출은 templates/format_*/reference.hwpx 사용 (없으면 government로 폴백)
  - 이메일은 HWPX 빌드 안 함 → build_email_md() 만 제공

────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional

# scripts/ 디렉토리를 import 경로에 추가 (CLI 실행 대비)
sys.path.insert(0, str(Path(__file__).parent))

from hwpx_helpers import (
    NS_DECL, CONTENT_WIDTH,
    next_id, reset_id, xml_escape,
    extract_secpr_and_colpr,
    make_first_para, make_text_para, make_body_para,
    make_empty_line, make_page_break,
)


# ═══════════════════════════════════════════════════════════
# 공통 — 신규 단락 빌더 (기존 hwpx_helpers 보강)
# ═══════════════════════════════════════════════════════════

def make_centered_para(text: str, char_pr: int = 0, para_pr: int = 4) -> str:
    """가운데 정렬 단락 (paraPrIDRef=4 가 일반적으로 가운데 정렬 — 템플릿에 따라 변경)"""
    pid = next_id()
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{char_pr}">'
        f'<hp:t>{xml_escape(text)}</hp:t>'
        f'</hp:run>'
        f'</hp:p>'
    )


def make_right_para(text: str, char_pr: int = 0, para_pr: int = 5) -> str:
    """우측 정렬 단락 (paraPrIDRef=5 가 일반적으로 우측 정렬)"""
    pid = next_id()
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{char_pr}">'
        f'<hp:t>{xml_escape(text)}</hp:t>'
        f'</hp:run>'
        f'</hp:p>'
    )


def make_underlined_title(text: str, char_pr: int = 0, para_pr: int = 4) -> str:
    """
    제목 + 밑줄 (1p 보고서 메인 타이틀용).
    실제 밑줄은 charPr 정의에 따라 다르므로, 별도 가로선 단락으로 구현.
    """
    parts = [
        make_centered_para(text, char_pr=char_pr, para_pr=para_pr),
        make_horizontal_rule(),
    ]
    return '\n'.join(parts)


def make_horizontal_rule() -> str:
    """가로 구분선 (테이블로 1행 1열 borderFill 적용 - 단순 구현)."""
    pid = next_id()
    return (
        f'<hp:p id="{pid}" paraPrIDRef="20" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="0">'
        f'<hp:t>{"_" * 60}</hp:t>'
        f'</hp:run>'
        f'</hp:p>'
    )


def make_summary_box(text: str, char_pr: int = 0) -> str:
    """
    음영 박스 (1p 보고서 두괄식 요약문용).

    실제 음영 효과는 borderFillIDRef + 셀 배경으로 처리해야 하지만,
    참조 hwpx 가 없는 폴백 모드에서는 들여쓰기 + 가로선으로 시각 분리.
    """
    parts = [
        make_horizontal_rule(),
        make_text_para(f'  {text}', char_pr=char_pr, para_pr=2),
        make_horizontal_rule(),
    ]
    return '\n'.join(parts)


def make_marker_para(marker: str, text: str, indent_level: int = 0,
                     marker_pr: int = 0, text_pr: int = 0) -> str:
    """
    들여쓰기 레벨별 글머리 단락. indent_level 에 따라 paraPrIDRef 가 달라짐.

    indent_level 0: □ ○ Ⅰ. 1.   (paraPrIDRef=1)
    indent_level 1: - 가. 1)      (paraPrIDRef=2)
    indent_level 2: * (1) 가)     (paraPrIDRef=3)
    indent_level 3: ※ (가) ①     (paraPrIDRef=3)
    """
    para_pr_map = {0: 1, 1: 2, 2: 3, 3: 3}
    para_pr = para_pr_map.get(indent_level, 1)
    return make_body_para(marker, text, marker_pr=marker_pr,
                          text_pr=text_pr, para_pr=para_pr)


# ═══════════════════════════════════════════════════════════
# 양식 1: 1페이지 보고서 (format_1p)
# ═══════════════════════════════════════════════════════════

def build_1p_report(payload: dict, secpr: str = '', colpr: str = '') -> str:
    """
    1페이지 보고서 빌더.

    payload schema:
    {
        'subtitle': '- 부제 -',                      # optional
        'title': '대제목 (보고서 제목)',
        'author': '○○○처장 ○○○',
        'date': "'12.6.",
        'phone': '4315',
        'summary': '두괄식 요약문 (1-2줄)',
        'sections': [
            {
                'heading': '추진배경',                  # □ 마커 자동 부착
                'items': [                              # ○ 본문 항목들
                    {'text': '본문 내용 1', 'sub': []},
                    {'text': '본문 내용 2', 'sub': [
                        '세부항목 1',                   # - 마커 자동
                        '세부항목 2',
                    ]},
                ],
            },
            ...
        ],
        '_missing': ['배경', '계획'],                  # AI 보완 플래그 (optional)
    }

    Returns: section0.xml 문자열 (전체 <hs:sec> 포함)
    """
    reset_id()
    parts = [
        "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>",
        f'<hs:sec {NS_DECL}>',
        make_first_para(secpr, colpr) if secpr else _make_first_para_minimal(),
    ]

    # 부제 (선택)
    if payload.get('subtitle'):
        parts.append(make_centered_para(payload['subtitle'], char_pr=4))

    # 제목 + 밑줄
    parts.append(make_centered_para(payload['title'], char_pr=2))
    parts.append(make_horizontal_rule())

    # 작성자 정보 (우측 정렬)
    author_line = _format_author_line(
        payload.get('author', ''),
        payload.get('date', ''),
        payload.get('phone', '')
    )
    if author_line:
        parts.append(make_right_para(author_line, char_pr=3))

    parts.append(make_empty_line())

    # 음영 박스 (요약문)
    if payload.get('summary'):
        parts.append(make_summary_box(payload['summary'], char_pr=2))
        parts.append(make_empty_line())

    # AI 보완 필요 경고
    if payload.get('_missing'):
        warning = f'※ AI 보완 필요: {", ".join(payload["_missing"])}'
        parts.append(make_text_para(warning, char_pr=5))
        parts.append(make_empty_line())

    # 본문 섹션들
    for sec in payload.get('sections', []):
        parts.append(make_marker_para('□', sec['heading'], indent_level=0, marker_pr=2))
        for item in sec.get('items', []):
            parts.append(make_marker_para('○', item['text'], indent_level=0))
            for sub in item.get('sub', []):
                parts.append(make_marker_para('-', sub, indent_level=1))
        parts.append(make_empty_line())

    parts.append('</hs:sec>')
    return '\n'.join(parts)


def _format_author_line(name: str, date: str, phone: str) -> str:
    """`○○○처장 ○○○('12.6., ☎4315)` 형식"""
    if not name:
        return ''
    paren_parts = []
    if date:
        paren_parts.append(date)
    if phone:
        paren_parts.append(f'☎{phone}')
    if paren_parts:
        return f'{name}({", ".join(paren_parts)})'
    return name


def _make_first_para_minimal() -> str:
    """
    secPr 없는 폴백용 최소 first para.
    A4, 여백 30/25/30/25mm, 1단 레이아웃.
    """
    pid = next_id()
    secpr = (
        '<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" tabStop="8000" '
        'tabStopVal="4000" tabStopUnit="HWPUNIT" outlineShapeIDRef="1" memoShapeIDRef="0" '
        'textVerticalWidthHead="0" masterPageCnt="0">'
        '<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0"/>'
        '<hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0"/>'
        '<hp:visibility hideFirstHeader="0" hideFirstFooter="0" hideFirstMasterPage="0" '
        'border="SHOW_ALL" fill="SHOW_ALL" hideFirstPageNum="0" hideFirstEmptyLine="0" showLineNumber="0"/>'
        '<hp:lineNumberShape restartType="0" countBy="0" distance="0" startNumber="0"/>'
        '<hp:pagePr landscape="WIDELY" width="59528" height="84186" gutterType="LEFT_ONLY">'
        '<hp:margin header="4252" footer="4252" gutter="0" left="8504" right="8504" top="8504" bottom="7087"/>'
        '</hp:pagePr>'
        '<hp:footNotePr>'
        '<hp:autoNumFormat type="DIGIT" userChar="*" prefixChar="" suffixChar=")" supscript="0"/>'
        '<hp:noteLine length="-1" type="SOLID" width="0.12 mm" color="#000000"/>'
        '<hp:noteSpacing betweenNotes="0" belowLine="567" aboveLine="850"/>'
        '<hp:numbering type="CONTINUOUS" newNum="1"/>'
        '<hp:placement place="EACH_COLUMN" beneathText="0"/>'
        '</hp:footNotePr>'
        '<hp:endNotePr>'
        '<hp:autoNumFormat type="DIGIT" userChar="*" prefixChar="" suffixChar=")" supscript="0"/>'
        '<hp:noteLine length="14692344" type="SOLID" width="0.12 mm" color="#000000"/>'
        '<hp:noteSpacing betweenNotes="0" belowLine="567" aboveLine="850"/>'
        '<hp:numbering type="CONTINUOUS" newNum="1"/>'
        '<hp:placement place="END_OF_DOCUMENT" beneathText="0"/>'
        '</hp:endNotePr>'
        '<hp:pageBorderFill type="BOTH" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER"/>'
        '<hp:pageBorderFill type="EVEN" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER"/>'
        '<hp:pageBorderFill type="ODD" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER"/>'
        '</hp:secPr>'
    )
    colpr = '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" sameSz="1" sameGap="0"/></hp:ctrl>'
    return (
        f'<hp:p id="{pid}" paraPrIDRef="0" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="0">'
        f'{secpr}'
        f'{colpr}'
        f'</hp:run>'
        f'</hp:p>'
    )


# ═══════════════════════════════════════════════════════════
# 양식 2: 풀버전 보고서 (format_full)
# ═══════════════════════════════════════════════════════════

def build_full_report(payload: dict, secpr: str = '', colpr: str = '') -> str:
    """
    풀버전 보고서 빌더.

    payload schema:
    {
        'cover': {
            'subtitle': '- 역구내 환경에 적합한 -',
            'title': '스마트 편의점 개발 추진계획',
            'date': '2025. 11.',
            'department': 'AI혁신처',
            'doc_meta': {'문서번호': 'AI혁신처-001', '보존기간': '...', '보고일자': '...'},
            'approval_line': [('과장', '박○○'), ('처장', '박○○'), ...],
        },
        'toc': [
            ('Ⅰ. 추진배경 및 목적', 4),
            ('Ⅱ. 추진계획(안)', 6),
            ...
        ],
        'toc_appendix': [
            ('1. 개발 산출물 예시사례', 15),
            ...
        ],
        'summary': {
            'title': '보고내용 요약',
            'sections': [
                {'heading': '추진배경 및 목적', 'items': ['..', '..']},
                {'heading': '추진계획 주요내용', 'items': ['..', '..']},
            ],
            'side_boxes': [
                {'title': '추진일정/기간', 'items': ['..']},
                {'title': '소요예산', 'items': ['..']},
                {'title': '부서별 협조사항', 'items': ['..']},
            ],
        },
        'chapters': [
            {
                'roman': 'Ⅰ',
                'title': '추진배경 및 목적',
                'sections': [...],
            },
            ...
        ],
        'appendix': [...],
    }
    """
    reset_id()
    parts = [
        "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>",
        f'<hs:sec {NS_DECL}>',
        make_first_para(secpr, colpr) if secpr else _make_first_para_minimal(),
    ]

    # ─── 표지 ───
    cover = payload.get('cover', {})
    parts.extend(_build_cover_page(cover))
    parts.append(make_page_break())

    # ─── 목차 ───
    parts.extend(_build_toc_page(
        payload.get('toc', []),
        payload.get('toc_appendix', [])
    ))
    parts.append(make_page_break())

    # ─── 보고내용 요약 ───
    summary = payload.get('summary', {})
    if summary:
        parts.extend(_build_summary_page(summary))
        parts.append(make_page_break())

    # ─── 본문 (각 장 시작은 새 페이지) ───
    for ch_idx, ch in enumerate(payload.get('chapters', [])):
        if ch_idx > 0:
            parts.append(make_page_break())
        parts.extend(_build_chapter(ch))

    # ─── 별첨 ───
    for ap in payload.get('appendix', []):
        parts.append(make_page_break())
        parts.extend(_build_appendix(ap))

    parts.append('</hs:sec>')
    return '\n'.join(parts)


def _build_cover_page(cover: dict) -> list[str]:
    """풀버전 표지 빌드. 결재선·문서메타·부제·제목·일자·부서."""
    parts = []
    # 빈 줄 (위 여백)
    for _ in range(3):
        parts.append(make_empty_line())

    # (간이 표지 — 결재선 표는 복잡한 테이블이라 생략하고 텍스트로)
    if cover.get('doc_meta'):
        for k, v in cover['doc_meta'].items():
            parts.append(make_text_para(f'{k}: {v}', char_pr=3))
        parts.append(make_empty_line())

    if cover.get('approval_line'):
        line = '결재: ' + ' | '.join(f'{role} {name}' for role, name in cover['approval_line'])
        parts.append(make_text_para(line, char_pr=3))
        parts.append(make_empty_line())

    for _ in range(5):
        parts.append(make_empty_line())

    if cover.get('subtitle'):
        parts.append(make_centered_para(cover['subtitle'], char_pr=4))
    parts.append(make_centered_para(cover.get('title', ''), char_pr=2))
    parts.append(make_empty_line())
    parts.append(make_empty_line())

    if cover.get('date'):
        parts.append(make_centered_para(cover['date'], char_pr=2))
    parts.append(make_empty_line())
    parts.append(make_empty_line())
    if cover.get('department'):
        parts.append(make_centered_para(cover['department'], char_pr=2))

    return parts


def _build_toc_page(entries: list, appendix: list) -> list[str]:
    """목차 페이지."""
    parts = []
    for _ in range(2):
        parts.append(make_empty_line())
    parts.append(make_centered_para('목  차', char_pr=2))
    parts.append(make_empty_line())
    parts.append(make_empty_line())

    for entry, page in entries:
        line = f'{entry} {"·" * max(2, 40 - len(entry))} {page}'
        parts.append(make_text_para(line, char_pr=0, para_pr=1))
        parts.append(make_empty_line())

    if appendix:
        parts.append(make_empty_line())
        parts.append(make_text_para('【참고자료】', char_pr=2, para_pr=1))
        for entry, page in appendix:
            line = f'  {entry} {"·" * max(2, 38 - len(entry))} {page}'
            parts.append(make_text_para(line, char_pr=0, para_pr=1))

    return parts


def _build_summary_page(summary: dict) -> list[str]:
    """보고내용 요약 페이지."""
    parts = []
    parts.append(make_centered_para(summary.get('title', '보고내용 요약'), char_pr=2))
    parts.append(make_empty_line())
    parts.append(make_horizontal_rule())
    parts.append(make_empty_line())

    for sec in summary.get('sections', []):
        parts.append(make_marker_para('▦', sec['heading'], indent_level=0, marker_pr=2))
        for i, item in enumerate(sec.get('items', []), 1):
            parts.append(make_marker_para(f'{i}.', item, indent_level=1))
        parts.append(make_empty_line())

    if summary.get('side_boxes'):
        parts.append(make_horizontal_rule())
        parts.append(make_empty_line())
        for box in summary['side_boxes']:
            parts.append(make_marker_para('▣', box['title'], indent_level=0, marker_pr=2))
            for item in box.get('items', []):
                parts.append(make_marker_para('-', item, indent_level=1))
            parts.append(make_empty_line())

    return parts


def _build_chapter(ch: dict) -> list[str]:
    """본문 장(章) 빌드 (Ⅰ. 1. 가. (1) (가) 위계)."""
    parts = []
    parts.append(make_marker_para(
        f'{ch.get("roman", "")}.',
        ch.get('title', ''),
        indent_level=0, marker_pr=2
    ))
    parts.append(make_empty_line())

    for sec_idx, sec in enumerate(ch.get('sections', []), 1):
        parts.append(make_marker_para(f'  {sec_idx}.', sec.get('title', ''), indent_level=0))
        for sub_idx, sub in enumerate(sec.get('subsections', []), 0):
            kor = '가나다라마바사아자차'[sub_idx % 10]
            parts.append(make_marker_para(f'    {kor}.', sub.get('title', ''), indent_level=1))
            for item in sub.get('items', []):
                parts.append(make_marker_para('      -', item, indent_level=2))
        parts.append(make_empty_line())
    return parts


def _build_appendix(ap: dict) -> list[str]:
    """별첨 페이지."""
    parts = []
    parts.append(make_centered_para(f'[별첨] {ap.get("title", "")}', char_pr=2))
    parts.append(make_empty_line())
    for line in ap.get('content', []):
        parts.append(make_text_para(line, char_pr=0))
    return parts


# ═══════════════════════════════════════════════════════════
# 양식 3: 시행문 (format_gongmun)
# ═══════════════════════════════════════════════════════════

def build_gongmun(payload: dict, secpr: str = '', colpr: str = '') -> str:
    """
    시행문 빌더.

    payload schema:
    {
        'sender_org': '○○주식회사',          # 상단 발신기관
        'receiver': '각 부서장',
        'via': '',                                # 경유 (선택)
        'title': '제목',
        'related_clause': '근거 (1줄)',
        'main_paragraph': '본문 도입 (서술식)',
        'items': ['가. ~~~', '나. ~~~', ...],
        'attachments': ['1. ~~~ 1부.', '2. ~~~ 1부.'],
        'signature_org': '○○주식회사',
        'signature_title': 'AI혁신처장',
        'metadata': {
            'drafter': ('AI혁신처 ○○과장', '박○○'),
            'reviewer': ('AI혁신처장', '박○○'),
            'cooperator': ('', ''),
            'serial': 'AI혁신처-1234',
            'date': '2025. 11. 5.',
            'address': '...',
            'tel': '02-0000-0000',
            'fax': '02-0000-0001',
            'email': 'example@○○공사.com',
            'disclosure': '대국민공개',
        }
    }
    """
    reset_id()
    parts = [
        "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>",
        f'<hs:sec {NS_DECL}>',
        make_first_para(secpr, colpr) if secpr else _make_first_para_minimal(),
    ]

    # 발신기관 (상단)
    if payload.get('sender_org'):
        parts.append(make_centered_para(payload['sender_org'], char_pr=2))
    parts.append(make_horizontal_rule())
    parts.append(make_empty_line())

    # 수신·경유·제목
    parts.append(make_text_para(f'수    신: {payload.get("receiver", "")}', char_pr=0))
    via = payload.get('via', '')
    parts.append(make_text_para(f'(경    유){"  " + via if via else ""}', char_pr=0))
    parts.append(make_text_para(f'제    목: {payload.get("title", "")}', char_pr=2))
    parts.append(make_empty_line())
    parts.append(make_empty_line())

    # 본문
    if payload.get('related_clause'):
        parts.append(make_marker_para('1.', f'관련: {payload["related_clause"]}', indent_level=0))
    if payload.get('main_paragraph'):
        parts.append(make_marker_para('2.', payload['main_paragraph'], indent_level=0))
    for item in payload.get('items', []):
        # 가./나. 등 마커가 이미 포함된 텍스트로 가정
        parts.append(make_text_para(f'    {item}', char_pr=0, para_pr=1))

    # 붙임
    attachments = payload.get('attachments', [])
    parts.append(make_empty_line())
    if attachments:
        parts.append(make_text_para(f'붙임  {attachments[0]}', char_pr=0))
        for att in attachments[1:-1]:
            parts.append(make_text_para(f'      {att}', char_pr=0))
        if len(attachments) >= 2:
            parts.append(make_text_para(f'      {attachments[-1]}   끝.', char_pr=0))
        else:
            # 붙임 1건만
            parts[-1] = make_text_para(f'붙임  {attachments[0]}   끝.', char_pr=0)
    else:
        # 붙임 없으면 본문 마지막에 끝.
        parts.append(make_text_para('끝.', char_pr=0))

    # 발신명의
    parts.append(make_empty_line())
    parts.append(make_empty_line())
    parts.append(make_centered_para(payload.get('signature_org', ''), char_pr=2))
    parts.append(make_centered_para(
        f'{payload.get("signature_title", "")}    (직인)', char_pr=2
    ))
    parts.append(make_empty_line())
    parts.append(make_empty_line())

    # 메타데이터 (하단 3줄)
    md = payload.get('metadata', {})
    if md:
        parts.append(make_horizontal_rule())
        # 1줄: 기안·검토·협조
        line1_parts = []
        if md.get('drafter'):
            line1_parts.append(f'기안자  {md["drafter"][0]} {md["drafter"][1]}')
        if md.get('reviewer'):
            line1_parts.append(f'검토자  {md["reviewer"][0]} {md["reviewer"][1]}')
        if md.get('cooperator') and md['cooperator'][0]:
            line1_parts.append(f'협조자  {md["cooperator"][0]} {md["cooperator"][1]}')
        if line1_parts:
            parts.append(make_text_para('   '.join(line1_parts), char_pr=3))
        # 2줄: 시행 + 접수
        if md.get('serial'):
            parts.append(make_text_para(f'시행  {md["serial"]} ({md.get("date", "")})         접수', char_pr=3))
        # 3줄: 주소·연락처
        contact_parts = []
        if md.get('address'):
            contact_parts.append(md['address'])
        if md.get('tel'):
            contact_parts.append(md['tel'])
        if md.get('fax'):
            contact_parts.append(f'fax {md["fax"]}')
        if md.get('email'):
            contact_parts.append(md['email'])
        if md.get('disclosure'):
            contact_parts.append(md['disclosure'])
        if contact_parts:
            parts.append(make_text_para('  /  '.join(contact_parts), char_pr=3))

    parts.append('</hs:sec>')
    return '\n'.join(parts)


# ═══════════════════════════════════════════════════════════
# 양식 4: 이메일 (format_email) - 텍스트 출력만
# ═══════════════════════════════════════════════════════════

def build_email_md(payload: dict) -> str:
    """
    이메일 본문 빌더 (마크다운/텍스트 출력).

    payload schema:
    {
        'subject': '[AI혁신처] AX포털 1차 검토 회신 요청 (~11.12)',
        'to': ['kimproduct@○○공사.com'],
        'cc': ['leemanager@○○공사.com'],
        'bcc': [],                                    # optional
        'greeting': '○○○님 안녕하세요. ...',
        'conclusion': '~~~을 요청드립니다.',           # 두괄식 결론
        'sections': [
            {'title': '회신 요청 사항', 'items': ['...', '...']},
            {'title': '기한 및 방법', 'items': ['...']},
        ],
        'closing': '빠른 회신 부탁드립니다. 감사합니다.',
        'signature': {
            'name': '박○○',
            'org': '○○ ○○○처',
            'tel': '02-0000-0000',
            'mobile': '010-0000-0000',
            'email': 'example@○○공사.com',
        }
    }
    """
    lines: list[str] = []
    lines.append('# 이메일 본문')
    lines.append('')
    lines.append(f"**제목**: {payload.get('subject', '')}")
    lines.append('')
    if payload.get('to'):
        lines.append(f"**받는사람**: {', '.join(payload['to'])}")
    if payload.get('cc'):
        lines.append(f"**참조**: {', '.join(payload['cc'])}")
    if payload.get('bcc'):
        lines.append(f"**숨은참조**: {', '.join(payload['bcc'])}")
    lines.append('')
    lines.append('---')
    lines.append('')

    if payload.get('greeting'):
        lines.append(payload['greeting'])
        lines.append('')

    if payload.get('conclusion'):
        lines.append(payload['conclusion'])
        lines.append('')

    for sec in payload.get('sections', []):
        lines.append(f"□ {sec.get('title', '')}")
        for item in sec.get('items', []):
            lines.append(f' - {item}')
        lines.append('')

    if payload.get('closing'):
        lines.append(payload['closing'])
        lines.append('')

    lines.append('---')
    sig = payload.get('signature', {})
    if sig.get('name') or sig.get('org'):
        lines.append(f"{sig.get('name', '')} ({sig.get('org', '')})".strip())
    if sig.get('tel') or sig.get('mobile'):
        tel_parts = []
        if sig.get('tel'):
            tel_parts.append(sig['tel'])
        if sig.get('mobile'):
            tel_parts.append(f"mobile {sig['mobile']}")
        lines.append(' / '.join(tel_parts))
    if sig.get('email'):
        lines.append(sig['email'])

    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
# 양식 디스패치
# ═══════════════════════════════════════════════════════════

def build_by_format(format_type: str, payload: dict,
                    reference_hwpx: Optional[str] = None) -> str:
    """
    양식 타입에 따라 적절한 빌더 호출.

    format_type: 'format_1p' | 'format_full' | 'format_gongmun' | 'format_email'
    reference_hwpx: 참조 hwpx 경로 (None 이면 폴백 secPr 사용)

    Returns: format_email 은 마크다운 텍스트, 그 외는 section0.xml 문자열.
    """
    if format_type == 'format_email':
        return build_email_md(payload)

    secpr, colpr = '', ''
    if reference_hwpx and Path(reference_hwpx).exists():
        try:
            secpr, colpr = extract_secpr_and_colpr(reference_hwpx)
        except Exception:
            pass  # 폴백

    if format_type == 'format_1p':
        return build_1p_report(payload, secpr=secpr, colpr=colpr)
    elif format_type == 'format_full':
        return build_full_report(payload, secpr=secpr, colpr=colpr)
    elif format_type == 'format_gongmun':
        return build_gongmun(payload, secpr=secpr, colpr=colpr)
    else:
        raise ValueError(f'알 수 없는 양식: {format_type}')
