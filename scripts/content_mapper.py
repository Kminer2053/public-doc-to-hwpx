"""
content_mapper.py
────────────────────────────────────────────────────────────
AI 리서치 결과물(MD/DOCX/PDF) → 공공기관 문서 구조 변환
우리 스킬 고유 로직: jkf87/hwpx-skill에 없는 차별점
────────────────────────────────────────────────────────────
"""

import re
import sys
from pathlib import Path


# ═══════════════════════════════════════════════════════════
# [1] 입력 파일 파싱
# ═══════════════════════════════════════════════════════════

def parse_input(file_path: str) -> dict:
    """
    입력 파일 파싱 → 구조화 딕셔너리 반환
    Returns: {'title': str, 'sections': [{'heading': str, 'level': int, 'content': str}]}
    """
    ext = Path(file_path).suffix.lower()
    if ext == '.md':
        return _parse_markdown(file_path)
    elif ext == '.docx':
        return _parse_docx(file_path)
    elif ext == '.pdf':
        return _parse_pdf(file_path)
    elif ext in ('.txt', ''):
        return _parse_text(file_path)
    else:
        raise ValueError(f'지원하지 않는 포맷: {ext} (md/docx/pdf/txt 지원)')


def _parse_markdown(path: str) -> dict:
    content = Path(path).read_text(encoding='utf-8')
    sections, current = [], None
    for line in content.split('\n'):
        m = re.match(r'^(#{1,6})\s+(.+)', line)
        if m:
            if current:
                sections.append(current)
            current = {'heading': m.group(2).strip(),
                       'level': len(m.group(1)), 'content': ''}
        elif current:
            current['content'] += line + '\n'
    if current:
        sections.append(current)
    title = sections[0]['heading'] if sections else Path(path).stem
    return {'title': title, 'sections': sections[1:] if len(sections) > 1 else sections}


def _parse_docx(path: str) -> dict:
    try:
        from docx import Document
    except ImportError:
        raise ImportError('python-docx 필요: pip install python-docx --break-system-packages')
    doc = Document(path)
    sections, current = [], None
    for para in doc.paragraphs:
        if para.style.name.startswith('Heading'):
            if current:
                sections.append(current)
            try:
                level = int(para.style.name.split()[-1])
            except (ValueError, IndexError):
                level = 1
            current = {'heading': para.text.strip(), 'level': level, 'content': ''}
        elif current and para.text.strip():
            current['content'] += para.text + '\n'
    if current:
        sections.append(current)
    title = doc.core_properties.title or (sections[0]['heading'] if sections else '문서')
    return {'title': title, 'sections': sections[1:] if len(sections) > 1 else sections}


def _parse_pdf(path: str) -> dict:
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            full_text = '\n'.join(p.extract_text() or '' for p in pdf.pages)
    except ImportError:
        import subprocess
        result = subprocess.run(['pdftotext', path, '-'], capture_output=True, text=True)
        full_text = result.stdout

    lines = [l.strip() for l in full_text.split('\n') if l.strip()]
    sections, current = [], None
    for i, line in enumerate(lines):
        # 짧고 이전 줄이 마침표로 안 끝나면 헤딩으로 추정
        is_heading = (len(line) < 40 and
                      (i == 0 or not lines[i-1].endswith('.')) and
                      not line.endswith(','))
        if is_heading:
            if current:
                sections.append(current)
            current = {'heading': line, 'level': 2, 'content': ''}
        elif current:
            current['content'] += line + '\n'
    if current:
        sections.append(current)
    title = lines[0] if lines else Path(path).stem
    return {'title': title, 'sections': sections}


def _parse_text(path: str) -> dict:
    lines = Path(path).read_text(encoding='utf-8').split('\n')
    sections, current = [], None
    for line in lines:
        line = line.rstrip()
        if re.match(r'^[一-龥A-Z0-9가-힣]{1,30}$', line) or re.match(r'^\d+\.\s+', line):
            if current:
                sections.append(current)
            current = {'heading': line.strip(), 'level': 2, 'content': ''}
        elif current:
            current['content'] += line + '\n'
    if current:
        sections.append(current)
    title = lines[0].strip() if lines else '문서'
    return {'title': title, 'sections': sections}


# ═══════════════════════════════════════════════════════════
# [2] 전체 변환 파이프라인 실행기
# ═══════════════════════════════════════════════════════════

def run_pipeline(
    input_file: str,
    output_path: str,
    skill_dir: str,
    doc_type: str = 'auto',
    user_hint: str = '',
    use_cover: bool = True,
    date: str = '',
) -> str:
    """
    완전 자동화 파이프라인:
    입력파일 → 파싱 → 문서유형판별 → 콘텐츠매핑 → HWPX생성 → 후처리 → 검증
    """
    import subprocess
    from hwpx_helpers import (detect_doc_type, map_content,
                               build_section_xml_from_content,
                               extract_secpr_and_colpr, DOC_TYPES)

    skill = Path(skill_dir)
    scripts = skill / 'scripts'

    print(f'[1/5] 파싱 중: {input_file}')
    parsed = parse_input(input_file)
    print(f'      제목: {parsed["title"]} | 섹션 수: {len(parsed["sections"])}')

    print(f'[2/5] 문서 유형 판별...')
    if doc_type == 'auto':
        doc_type = detect_doc_type(parsed['sections'], user_hint)
    print(f'      → {DOC_TYPES[doc_type]["name"]} ({doc_type})')

    print(f'[3/5] 공공기관 필수항목 매핑...')
    result = map_content(parsed['sections'], doc_type)
    mapped, unmapped = result['mapped'], result['unmapped']
    ai_count = sum(1 for s in mapped.values() if '※ [AI 생성' in s.get('content', ''))
    print(f'      자동매핑: {len(mapped)-ai_count}개 | AI생성초안: {ai_count}개 | 붙임처리: {len(unmapped)}개')

    # 레퍼런스 HWPX에서 secPr 추출 (government 템플릿)
    ref_hwpx = skill / 'templates' / 'government' / 'reference.hwpx'
    if ref_hwpx.exists():
        print(f'[4/5] 레퍼런스 서식 추출...')
        secpr, colpr = extract_secpr_and_colpr(str(ref_hwpx))
    else:
        # 내장 빈 템플릿 사용 (폴백)
        print(f'[4/5] 내장 템플릿 사용 (레퍼런스 없음)...')
        from hwpx import HwpxDocument
        import zipfile as zf2
        tmp_blank = '/tmp/_blank.hwpx'
        doc = HwpxDocument.new()
        doc.save_to_path(tmp_blank)
        secpr, colpr = extract_secpr_and_colpr(tmp_blank)

    section_xml = build_section_xml_from_content(
        title=parsed['title'],
        mapped=mapped,
        unmapped=unmapped,
        doc_type=doc_type,
        secpr=secpr,
        colpr=colpr,
        use_cover=use_cover,
        date=date,
    )

    section_tmp = '/tmp/_section0.xml'
    Path(section_tmp).write_text(section_xml, encoding='utf-8')

    header_path = skill / 'templates' / 'government' / 'header.xml'
    if not header_path.exists():
        # 폴백: 내장 blank의 header 사용
        from hwpx import HwpxDocument
        _tmp = '/tmp/_blank2.hwpx'
        HwpxDocument.new().save_to_path(_tmp)
        import zipfile as zf3
        with zf3.ZipFile(_tmp) as z:
            Path(str(header_path)).parent.mkdir(parents=True, exist_ok=True)
            Path(str(header_path)).write_bytes(z.read('Contents/header.xml'))

    print(f'[5/5] HWPX 조립 및 후처리...')
    subprocess.run([
        'python3', str(scripts / 'build_hwpx.py'),
        '--header', str(header_path),
        '--section', section_tmp,
        '--title', parsed['title'],
        '--output', output_path,
    ], check=True)

    subprocess.run(['python3', str(scripts / 'fix_namespaces.py'), output_path], check=True)
    subprocess.run(['python3', str(scripts / 'validate.py'), output_path])

    print(f'\n✅ 완료: {output_path}')
    if ai_count > 0:
        print(f'⚠️  {ai_count}개 항목은 AI 초안입니다. 제출 전 반드시 검토·수정하세요.')
    return output_path


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='AI 리서치 → 공공기관 HWPX 변환')
    p.add_argument('input',               help='입력파일 (md/docx/pdf)')
    p.add_argument('output',              help='출력 .hwpx 경로')
    p.add_argument('--skill-dir', required=True, help='스킬 루트 디렉토리')
    p.add_argument('--doc-type',  default='auto',
                   choices=['auto', 'gihoekseo', 'bogoseo', 'gongmun', 'geomto'])
    p.add_argument('--hint',      default='', help='문서 유형 힌트')
    p.add_argument('--no-cover',  action='store_true', help='표지 없이 생성')
    p.add_argument('--date',      default='', help='작성일 (예: 2026. 04. 05.)')
    args = p.parse_args()

    sys.path.insert(0, str(Path(args.skill_dir) / 'scripts'))
    run_pipeline(
        input_file=args.input,
        output_path=args.output,
        skill_dir=args.skill_dir,
        doc_type=args.doc_type,
        user_hint=args.hint,
        use_cover=not args.no_cover,
        date=args.date,
    )
