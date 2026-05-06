"""
hwpx_helpers.py
────────────────────────────────────────────────────────────
HWPX 문서 생성 헬퍼 라이브러리

출처: jkf87/hwpx-skill 구조 + 공공기관 콘텐츠 매핑 로직 통합
업데이트: 2026-04-05
────────────────────────────────────────────────────────────
"""

import re
import zipfile
from pathlib import Path
from itertools import count

# ── 네임스페이스 선언 (section0.xml 루트에 반드시 포함) ──────
NS_DECL = (
    'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
    'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
    'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" '
    'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"'
)

# ── HWPUNIT 변환 상수 ─────────────────────────────────────
# 1pt = 100, 1mm = 283.5, A4폭 = 59528, A4높이 = 84186
# 좌우여백(30mm) = 8504, 본문폭 = 42520
CONTENT_WIDTH = 42520   # 본문 폭 (HWPUNIT)

# ── 전역 ID 카운터 ────────────────────────────────────────
_id_counter = count(1)

def next_id() -> int:
    """문서 내 고유 ID 생성"""
    return next(_id_counter)

def reset_id():
    """새 문서 생성 시 카운터 초기화"""
    global _id_counter
    _id_counter = count(1)

# ── XML 이스케이프 ────────────────────────────────────────
def xml_escape(text: str) -> str:
    """XML 특수문자 이스케이프 (필수)"""
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;'))

# ═══════════════════════════════════════════════════════════
# [1] secPr 추출 (레퍼런스 HWPX에서)
# ═══════════════════════════════════════════════════════════

def extract_secpr_and_colpr(hwpx_path: str) -> tuple[str, str]:
    """
    레퍼런스 HWPX에서 secPr + colPr 추출
    ⚠️ 첫 문단 첫 run에 반드시 포함 필요 — 없으면 한글이 문서를 열지 못함
    """
    with zipfile.ZipFile(hwpx_path, 'r') as z:
        data = z.read('Contents/section0.xml').decode('utf-8')

    secpr_match = re.search(r'<hp:secPr.*?</hp:secPr>', data, re.DOTALL)
    if not secpr_match:
        raise ValueError(f"secPr을 찾을 수 없음: {hwpx_path}")
    secpr = secpr_match.group()

    end = secpr_match.end()
    colpr_match = re.search(r'<hp:ctrl>.*?</hp:ctrl>', data[end:end+1000], re.DOTALL)
    colpr = colpr_match.group() if colpr_match else '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" sameSz="1" sameGap="0"/></hp:ctrl>'

    return secpr, colpr


# ═══════════════════════════════════════════════════════════
# [2] 기본 단락 생성 함수
# ═══════════════════════════════════════════════════════════

def make_first_para(secpr: str, colpr: str) -> str:
    """
    첫 문단 생성 — secPr + colPr 포함 (필수!)
    ⚠️ 이 함수 없이 생성된 문서는 한글에서 열리지 않음
    """
    pid = next_id()
    return (
        f'<hp:p id="{pid}" paraPrIDRef="0" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">\n'
        f'  <hp:run charPrIDRef="0">\n'
        f'    {secpr}\n'
        f'    {colpr}\n'
        f'  </hp:run>\n'
        f'</hp:p>'
    )

def make_empty_line(para_pr=0, char_pr=0) -> str:
    """빈 줄"""
    pid = next_id()
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{char_pr}"><hp:t/></hp:run>'
        f'</hp:p>'
    )

def make_page_break(para_pr=18, char_pr=0) -> str:
    """페이지 넘김"""
    pid = next_id()
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="1" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{char_pr}"><hp:t/></hp:run>'
        f'</hp:p>'
    )

def make_text_para(text: str, char_pr: int = 0, para_pr: int = 0,
                   page_break: int = 0) -> str:
    """일반 텍스트 단락"""
    pid = next_id()
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="{page_break}" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{char_pr}">'
        f'<hp:t>{xml_escape(text)}</hp:t>'
        f'</hp:run>'
        f'</hp:p>'
    )

def make_body_para(marker: str, text: str,
                   marker_pr: int = 0, text_pr: int = 0,
                   para_pr: int = 1) -> str:
    """
    본문 단락 (마커 + 내용 혼합 서식)
    예: make_body_para("가.", "내용 텍스트")
    """
    pid = next_id()
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{marker_pr}"><hp:t>{xml_escape(marker)} </hp:t></hp:run>'
        f'<hp:run charPrIDRef="{text_pr}"><hp:t>{xml_escape(text)}</hp:t></hp:run>'
        f'</hp:p>'
    )


# ═══════════════════════════════════════════════════════════
# [3] 관공서 전용 — 컬러 배너 & 섹션 바
# ═══════════════════════════════════════════════════════════

def make_cover_banner(title: str) -> str:
    """
    표지/본문 상단 컬러 배너 (3×2 테이블)
    government 템플릿 전용 charPr/borderFill ID 사용
    ⚠️ 다른 템플릿에 사용하면 서식 깨짐
    """
    tid = next_id()
    rows = []

    # 1행: 좌(파랑 bf=10) + 우(노랑 bf=8), 높이=382
    r1_cells = _banner_color_cell(tid, col=0, row=0, bf=10, w=21260, h=382, text='')
    r1_cells += _banner_color_cell(tid, col=1, row=0, bf=8,  w=21260, h=382, text='')
    rows.append(f'<hp:tr>{r1_cells}</hp:tr>')

    # 2행: 제목 셀 병합(colspan=2, bf=15 회색배경), 높이=7410
    rows.append(f'<hp:tr>{_banner_title_cell(tid, title)}</hp:tr>')

    # 3행: 좌(초록 bf=9) + 우(빨강 bf=11), 높이=382
    r3_cells = _banner_color_cell(tid, col=0, row=2, bf=9,  w=21260, h=382, text='')
    r3_cells += _banner_color_cell(tid, col=1, row=2, bf=11, w=21260, h=382, text='')
    rows.append(f'<hp:tr>{r3_cells}</hp:tr>')

    tbl_id = next_id()
    total_h = 382 + 7410 + 382
    return (
        f'<hp:p id="{next_id()}" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="0">'
        f'<hp:tbl id="{tbl_id}" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" '
        f'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" '
        f'repeatHeader="0" rowCnt="3" colCnt="2" cellSpacing="0" borderFillIDRef="3" noAdjust="0">'
        f'<hp:sz width="{CONTENT_WIDTH}" widthRelTo="ABSOLUTE" height="{total_h}" heightRelTo="ABSOLUTE" protect="0"/>'
        f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
        f'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" '
        f'vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        f'<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        f'<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        f'{"".join(rows)}'
        f'</hp:tbl>'
        f'<hp:t/>'
        f'</hp:run>'
        f'</hp:p>'
    )

def _banner_color_cell(tid, col, row, bf, w, h, text=''):
    pid = next_id()
    return (
        f'<hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="1" borderFillIDRef="{bf}">'
        f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" '
        f'linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
        f'<hp:p paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0" id="{pid}">'
        f'<hp:run charPrIDRef="0"><hp:t>{xml_escape(text)}</hp:t></hp:run>'
        f'</hp:p>'
        f'</hp:subList>'
        f'<hp:cellAddr colAddr="{col}" rowAddr="{row}"/>'
        f'<hp:cellSpan colSpan="1" rowSpan="1"/>'
        f'<hp:cellSz width="{w}" height="{h}"/>'
        f'<hp:cellMargin left="170" right="170" top="0" bottom="0"/>'
        f'</hp:tc>'
    )

def _banner_title_cell(tid, title):
    pid = next_id()
    return (
        f'<hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="1" borderFillIDRef="15">'
        f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" '
        f'linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
        f'<hp:p paraPrIDRef="21" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0" id="{pid}">'
        f'<hp:run charPrIDRef="9"><hp:t>{xml_escape(title)}</hp:t></hp:run>'
        f'</hp:p>'
        f'</hp:subList>'
        f'<hp:cellAddr colAddr="0" rowAddr="1"/>'
        f'<hp:cellSpan colSpan="2" rowSpan="1"/>'
        f'<hp:cellSz width="{CONTENT_WIDTH}" height="7410"/>'
        f'<hp:cellMargin left="170" right="170" top="0" bottom="0"/>'
        f'</hp:tc>'
    )

def make_section_bar(number: str, title: str) -> str:
    """
    섹션 구분 바 (1×3 테이블) — government 템플릿 전용
    예: make_section_bar("1", "추진배경")
    """
    tbl_id = next_id()
    w0, w1, w2 = 3422, 565, CONTENT_WIDTH - 3422 - 565

    def _cell(col, bf, char_pr, w, h, text, para_pr=21):
        pid = next_id()
        return (
            f'<hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="1" borderFillIDRef="{bf}">'
            f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" '
            f'linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
            f'<hp:p paraPrIDRef="{para_pr}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0" id="{pid}">'
            f'<hp:run charPrIDRef="{char_pr}"><hp:t>{xml_escape(text)}</hp:t></hp:run>'
            f'</hp:p>'
            f'</hp:subList>'
            f'<hp:cellAddr colAddr="{col}" rowAddr="0"/>'
            f'<hp:cellSpan colSpan="1" rowSpan="1"/>'
            f'<hp:cellSz width="{w}" height="{h}"/>'
            f'<hp:cellMargin left="170" right="170" top="0" bottom="0"/>'
            f'</hp:tc>'
        )

    row = (
        _cell(0, 14, 81, w0, 2835, number)   # 번호: 파랑bg, 흰볼드
        + _cell(1, 13, 0,  w1, 2835, '')     # 간격: 회색
        + _cell(2, 12, 83, w2, 2835, title)  # 제목: 하늘색bg, 볼드
    )

    return (
        f'<hp:p id="{next_id()}" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="0">'
        f'<hp:tbl id="{tbl_id}" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" '
        f'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" '
        f'repeatHeader="0" rowCnt="1" colCnt="3" cellSpacing="0" borderFillIDRef="3" noAdjust="0">'
        f'<hp:sz width="{CONTENT_WIDTH}" widthRelTo="ABSOLUTE" height="2835" heightRelTo="ABSOLUTE" protect="0"/>'
        f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
        f'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" '
        f'vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        f'<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        f'<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        f'<hp:tr>{row}</hp:tr>'
        f'</hp:tbl>'
        f'<hp:t/>'
        f'</hp:run>'
        f'</hp:p>'
    )

def make_cover_page(title: str, subtitle: str = '', date: str = '') -> list[str]:
    """
    표지 전체 생성 (빈줄×6 → 배너 → 부제 → 날짜 → pageBreak)
    Returns: list of XML paragraph strings
    """
    parts = []
    for _ in range(6):
        parts.append(make_empty_line())
    parts.append(make_cover_banner(title))
    parts.append(make_empty_line())
    if subtitle:
        parts.append(make_text_para(subtitle, char_pr=0, para_pr=0))
    for _ in range(8):
        parts.append(make_empty_line())
    if date:
        parts.append(make_text_para(date, char_pr=0, para_pr=0))
    for _ in range(4):
        parts.append(make_empty_line())
    parts.append(make_page_break())
    return parts


# ═══════════════════════════════════════════════════════════
# [4] 이미지 삽입
# ═══════════════════════════════════════════════════════════

def add_images_to_hwpx(hwpx_path: str, images: list[dict]):
    """
    images: [{"file": "img1.png", "src_path": "/path/to/img.png", "id": "img1"}]
    ⚠️ content.hpf에도 등록 필요 → update_content_hpf() 함께 호출
    """
    import os
    tmp = hwpx_path + '.tmp'
    with zipfile.ZipFile(hwpx_path, 'r') as zin:
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                ct = zipfile.ZIP_STORED if item.filename == 'mimetype' else zipfile.ZIP_DEFLATED
                zout.writestr(item, data, compress_type=ct)
            for img in images:
                zout.write(img['src_path'], f'BinData/{img["file"]}')
    os.replace(tmp, hwpx_path)

def update_content_hpf(hwpx_path: str, images: list[dict]):
    """이미지를 content.hpf manifest에 등록"""
    import os
    tmp = hwpx_path + '.tmp'
    mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'png': 'image/png', 'bmp': 'image/bmp', 'gif': 'image/gif'}
    with zipfile.ZipFile(hwpx_path, 'r') as zin:
        hpf = zin.read('Contents/content.hpf').decode('utf-8')
        items = ''
        for img in images:
            ext = img['file'].rsplit('.', 1)[-1].lower()
            mime = mime_map.get(ext, 'image/png')
            items += f'<opf:item id="{img["id"]}" href="BinData/{img["file"]}" media-type="{mime}" isEmbeded="1"/>\n'
        hpf = hpf.replace('</opf:manifest>', items + '</opf:manifest>')
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == 'Contents/content.hpf':
                    ct = zipfile.ZIP_STORED if item.filename == 'mimetype' else zipfile.ZIP_DEFLATED
                    zout.writestr(item, hpf.encode('utf-8'), compress_type=ct)
                else:
                    data = zin.read(item.filename)
                    ct = zipfile.ZIP_STORED if item.filename == 'mimetype' else zipfile.ZIP_DEFLATED
                    zout.writestr(item, data, compress_type=ct)
    os.replace(tmp, hwpx_path)


# ═══════════════════════════════════════════════════════════
# [5] 공공기관 문서 콘텐츠 매핑 (우리 고유 로직)
# ═══════════════════════════════════════════════════════════

DOC_TYPES = {
    'gihoekseo': {
        'name': '기획서',
        'required_fields': ['추진배경', '현황 및 문제점', '추진방향', '세부 추진계획', '기대효과', '소요예산'],
        'numbering': ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ', 'Ⅵ', 'Ⅶ'],
        'trigger_keywords': ['기획', '사업계획', '추진계획', '제안'],
    },
    'bogoseo': {
        'name': '보고서',
        'required_fields': ['개요', '추진현황', '세부내용', '문제점 및 개선방안', '향후 추진계획'],
        'numbering': ['□', '○', '―', '※'],
        'trigger_keywords': ['보고', '현황보고', '결과보고', '추진현황'],
    },
    'gongmun': {
        'name': '공문',
        'required_fields': ['수신', '제목', '본문', '붙임'],
        'numbering': ['1.', '가.', '1)', '가)', '(1)', '(가)', '①'],
        'trigger_keywords': ['공문', '공식문서', '발신', '수신'],
    },
    'geomto': {
        'name': '검토보고서',
        'required_fields': ['검토배경', '관련 법령 및 규정', '검토 내용', '문제점 및 쟁점', '검토 의견'],
        'numbering': ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ'],
        'trigger_keywords': ['검토', '법령검토', '법률검토', '의견'],
    },
}

FIELD_KEYWORDS = {
    '추진배경':       ['배경', '필요성', '목적', '경위', '취지'],
    '현황 및 문제점': ['현황', '문제점', '실태', '이슈', '분석'],
    '추진방향':       ['방향', '전략', '목표', '기본방향'],
    '세부 추진계획':  ['계획', '세부', '일정', '방법', '내용'],
    '기대효과':       ['효과', '기대', '성과', '편익'],
    '소요예산':       ['예산', '비용', '소요', '재원'],
    '개요':           ['개요', '요약', '핵심', 'summary'],
    '추진현황':       ['현황', '경과', '추진', '진행'],
    '세부내용':       ['내용', '상세', '세부'],
    '문제점 및 개선방안': ['문제점', '개선', '개선방안'],
    '향후 추진계획':  ['향후', '계획', '일정'],
    '수신':           ['수신', '받는곳'],
    '제목':           ['제목', '건명'],
    '본문':           ['본문', '내용'],
    '붙임':           ['붙임', '첨부'],
    '검토배경':       ['배경', '경위', '목적'],
    '관련 법령 및 규정': ['법령', '규정', '법률', '조항', '근거'],
    '검토 내용':      ['내용', '분석', '검토'],
    '문제점 및 쟁점': ['문제점', '쟁점', '한계'],
    '검토 의견':      ['의견', '결론', '제언', '권고'],
}


def detect_doc_type(sections: list[dict], user_hint: str = '') -> str:
    """
    문서 유형 자동 판별
    Returns: 'gihoekseo' | 'bogoseo' | 'gongmun' | 'geomto'
    """
    hint = user_hint.lower()
    for dtype, spec in DOC_TYPES.items():
        if any(kw in hint for kw in spec['trigger_keywords']):
            return dtype

    scores = {dtype: 0 for dtype in DOC_TYPES}
    all_headings = ' '.join(s.get('heading', '') for s in sections)
    for dtype, spec in DOC_TYPES.items():
        for kw in spec['trigger_keywords']:
            if kw in all_headings:
                scores[dtype] += 1
        for field in spec['required_fields']:
            for fkw in FIELD_KEYWORDS.get(field, []):
                if fkw in all_headings:
                    scores[dtype] += 1

    return max(scores, key=scores.get) if max(scores.values()) > 0 else 'gihoekseo'


def map_content(sections: list[dict], doc_type: str) -> dict:
    """
    파싱된 섹션을 공공기관 필수항목에 매핑
    Returns: {
        'title': str,
        'mapped': {field: section_dict},
        'unmapped': [section_dict]
    }
    """
    spec = DOC_TYPES[doc_type]
    required = spec['required_fields']
    mapped = {}
    used = set()

    for field in required:
        keywords = FIELD_KEYWORDS.get(field, [field])
        best_idx, best_score = None, 0
        for i, sec in enumerate(sections):
            if i in used:
                continue
            heading = sec.get('heading', '')
            score = sum(1 for kw in keywords if kw in heading)
            if score > best_score:
                best_score, best_idx = score, i
        if best_idx is not None and best_score > 0:
            mapped[field] = sections[best_idx]
            used.add(best_idx)
        else:
            mapped[field] = {
                'heading': field,
                'content': f'※ [AI 생성 초안 - 검토 필요] {field}에 해당하는 내용을 작성하십시오.',
                'level': 1
            }

    unmapped = [s for i, s in enumerate(sections) if i not in used]
    return {'mapped': mapped, 'unmapped': unmapped}


def build_section_xml_from_content(
    title: str,
    mapped: dict,
    unmapped: list,
    doc_type: str,
    secpr: str,
    colpr: str,
    use_cover: bool = True,
    date: str = '',
) -> str:
    """
    콘텐츠 매핑 결과 → section0.xml 전체 문자열 생성
    """
    reset_id()
    spec = DOC_TYPES[doc_type]
    num_chars = spec['numbering']
    parts = [
        f"<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>",
        f'<hs:sec {NS_DECL}>',
        make_first_para(secpr, colpr),
    ]

    if use_cover:
        parts.extend(make_cover_page(title, date=date))
        parts.append(make_cover_banner(title))
        parts.append(make_empty_line())
    else:
        parts.append(make_text_para(title, char_pr=9, para_pr=21))
        parts.append(make_empty_line())

    for idx, (field, section) in enumerate(mapped.items()):
        num = num_chars[idx % len(num_chars)]
        # 섹션 바 (government 스타일)
        parts.append(make_section_bar(num, section['heading']))
        parts.append(make_empty_line())

        # 본문 내용
        content = section.get('content', '')
        for line in content.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.startswith('※'):
                parts.append(make_text_para(line, char_pr=2, para_pr=1))
            elif line.startswith('-') or line.startswith('•'):
                parts.append(make_body_para('·', line.lstrip('-•').strip(), para_pr=1))
            else:
                parts.append(make_text_para(line, char_pr=0, para_pr=1))
        parts.append(make_empty_line())

    # 매핑 안 된 섹션은 붙임으로
    if unmapped:
        parts.append(make_section_bar('붙', '붙임'))
        for sec in unmapped:
            parts.append(make_text_para(sec['heading'], char_pr=9, para_pr=0))
            for line in sec.get('content', '').strip().split('\n'):
                if line.strip():
                    parts.append(make_text_para(line.strip(), char_pr=0, para_pr=1))
        parts.append(make_empty_line())

    parts.append('</hs:sec>')
    return '\n'.join(parts)
