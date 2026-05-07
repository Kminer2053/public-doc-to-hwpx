"""
build_hwpx.py
────────────────────────────────────────────────────────────
Skeleton.hwpx 기반 HWPX 조립

전략:
  - templates/_skeleton.hwpx 의 모든 메타파일(검증된 한컴 표준 포맷)을 그대로 사용
  - 사용자가 제공한 header.xml 과 section0.xml 만 교체
  - Contents/content.hpf 의 dc:title 만 동적 갱신

이전 v2 의 문제:
  - container.xml media-type 오타 (application/hwp+zip → hwpml-package+xml)
  - manifest.xml 네임스페이스 누락
  - version.xml 태그명 오류 (hv:version → hv:HCFVersion)
  - settings.xml 네임스페이스 오류
  - content.hpf href 경로 누락 (header.xml → Contents/header.xml)
  - META-INF/container.rdf, Preview/* 누락
  → 이 모든 오류로 한글에서 "파일 손상" 메시지

v3.0.1 수정 (2026.5.6.):
  Skeleton.hwpx 를 베이스로 사용해 위 6가지 문제를 일거에 해결.

사용법:
  python build_hwpx.py \\
    --header templates/government/header.xml \\
    --section /tmp/section0.xml \\
    --title "문서 제목" \\
    --output result.hwpx
────────────────────────────────────────────────────────────
"""

import re
import shutil
import sys
import tempfile
import zipfile
import argparse
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_SKELETON = SKILL_DIR / 'templates' / '_skeleton.hwpx'


def build_hwpx(header_path: str, section_path: str,
               output_path: str, title: str = '',
               skeleton_path: str = '') -> str:
    """
    Skeleton.hwpx 를 베이스로 한 HWPX 조립.

    Parameters
    ----------
    header_path : str
        교체할 header.xml 경로
    section_path : str
        교체할 section0.xml 경로
    output_path : str
        출력 .hwpx 경로
    title : str
        문서 제목 (content.hpf 의 dc:title 에 삽입)
    skeleton_path : str
        Skeleton.hwpx 경로 (비워두면 templates/_skeleton.hwpx 사용)
    """
    skel = Path(skeleton_path) if skeleton_path else DEFAULT_SKELETON
    if not skel.exists():
        raise FileNotFoundError(
            f'Skeleton.hwpx 없음: {skel}\n'
            'templates/_skeleton.hwpx 가 누락됐습니다. '
            'GitHub 리포에서 다시 받거나 python-hwpx 패키지의 '
            'data/Skeleton.hwpx 를 복사하세요.'
        )

    header_xml = Path(header_path).read_text(encoding='utf-8')
    section_xml = Path(section_path).read_text(encoding='utf-8')

    # XML 안전 처리 (제목)
    safe_title = (
        title.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;')
             .replace('"', '&quot;')
    )

    # Skeleton 을 임시 디렉토리에 풀기
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        with zipfile.ZipFile(skel, 'r') as zf:
            zf.extractall(tmp)

        # Contents/header.xml 교체
        (tmp / 'Contents' / 'header.xml').write_text(header_xml, encoding='utf-8')

        # Contents/section0.xml 교체
        (tmp / 'Contents' / 'section0.xml').write_text(section_xml, encoding='utf-8')

        # Contents/content.hpf 의 dc:title 갱신 (있을 때만)
        hpf_path = tmp / 'Contents' / 'content.hpf'
        if hpf_path.exists() and safe_title:
            hpf = hpf_path.read_text(encoding='utf-8')
            # <opf:title/> 또는 <opf:title>...</opf:title> 모두 처리
            new_hpf = re.sub(
                r'<opf:title\s*/\s*>',
                f'<opf:title>{safe_title}</opf:title>',
                hpf,
                count=1,
            )
            new_hpf = re.sub(
                r'<opf:title>[^<]*</opf:title>',
                f'<opf:title>{safe_title}</opf:title>',
                new_hpf,
                count=1,
            )
            hpf_path.write_text(new_hpf, encoding='utf-8')

        # 새 ZIP 으로 다시 묶기
        # mimetype 은 반드시 첫 번째 + ZIP_STORED
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            mimetype_path = tmp / 'mimetype'
            if mimetype_path.exists():
                zf.write(mimetype_path, 'mimetype',
                         compress_type=zipfile.ZIP_STORED)

            # 나머지 파일들 (mimetype 제외)
            for f in sorted(tmp.rglob('*')):
                if f.is_file() and f.name != 'mimetype':
                    arc = f.relative_to(tmp).as_posix()
                    zf.write(f, arc, compress_type=zipfile.ZIP_DEFLATED)

    print(f'[build_hwpx] ✅ 조립 완료: {output_path} (Skeleton 베이스)')
    return output_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HWPX 파일 조립 (Skeleton 기반)')
    parser.add_argument('--header',   required=True, help='header.xml 경로')
    parser.add_argument('--section',  required=True, help='section0.xml 경로')
    parser.add_argument('--output',   required=True, help='출력 .hwpx 경로')
    parser.add_argument('--title',    default='',    help='문서 제목')
    parser.add_argument('--skeleton', default='',
                        help='Skeleton.hwpx 경로 (기본: templates/_skeleton.hwpx)')
    args = parser.parse_args()
    build_hwpx(args.header, args.section, args.output, args.title, args.skeleton)
