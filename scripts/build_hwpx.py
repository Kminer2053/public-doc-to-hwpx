"""
build_hwpx.py
────────────────────────────────────────────────────────────
header.xml + section0.xml → .hwpx 파일 조립
반드시 fix_namespaces.py → validate.py 순으로 후속 실행

사용법:
  python build_hwpx.py \\
    --header templates/government/header.xml \\
    --section /tmp/section0.xml \\
    --title "문서 제목" \\
    --output result.hwpx
────────────────────────────────────────────────────────────
"""

import sys
import zipfile
import argparse
from pathlib import Path
from datetime import datetime

def build_hwpx(header_path: str, section_path: str,
               output_path: str, title: str = ''):
    header_xml = Path(header_path).read_text(encoding='utf-8')
    section_xml = Path(section_path).read_text(encoding='utf-8')
    now = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    safe_title = title.replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')

    hpf_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<opf:package xmlns:opf="http://www.idpf.org/2007/opf" version="2.0">
  <opf:metadata>
    <dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">{safe_title}</dc:title>
    <dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">공공기관 AI 문서 자동화</dc:creator>
    <dc:date xmlns:dc="http://purl.org/dc/elements/1.1/">{now}</dc:date>
  </opf:metadata>
  <opf:manifest>
    <opf:item id="header"   href="header.xml"   media-type="application/xml"/>
    <opf:item id="section0" href="section0.xml" media-type="application/xml"/>
  </opf:manifest>
  <opf:spine>
    <opf:itemref idref="section0"/>
  </opf:spine>
</opf:package>'''

    container_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<rootfiles>
  <rootfile full-path="Contents/content.hpf" media-type="application/hwp+zip"/>
</rootfiles>'''

    settings_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<hs:settings xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section">
</hs:settings>'''

    version_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<hv:version xmlns:hv="http://www.hancom.co.kr/hwpml/2012/version"
            major="5" minor="1" micro="3" buildNumber="0"/>'''

    manifest_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<manifest>
  <item href="Contents/content.hpf" id="content"/>
  <item href="Contents/header.xml" id="header"/>
  <item href="Contents/section0.xml" id="section0"/>
  <item href="settings.xml" id="settings"/>
  <item href="version.xml" id="version"/>
</manifest>'''

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # mimetype: 반드시 첫 번째, ZIP_STORED
        zf.writestr('mimetype', 'application/hwp+zip',
                    compress_type=zipfile.ZIP_STORED)
        # 나머지 파일
        zf.writestr('META-INF/container.xml', container_xml)
        zf.writestr('META-INF/manifest.xml', manifest_xml)
        zf.writestr('Contents/content.hpf', hpf_xml)
        zf.writestr('Contents/header.xml', header_xml)
        zf.writestr('Contents/section0.xml', section_xml)
        zf.writestr('settings.xml', settings_xml)
        zf.writestr('version.xml', version_xml)

    print(f'[build_hwpx] ✅ 조립 완료: {output_path}')
    return output_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HWPX 파일 조립')
    parser.add_argument('--header',  required=True, help='header.xml 경로')
    parser.add_argument('--section', required=True, help='section0.xml 경로')
    parser.add_argument('--output',  required=True, help='출력 .hwpx 경로')
    parser.add_argument('--title',   default='',    help='문서 제목')
    args = parser.parse_args()
    build_hwpx(args.header, args.section, args.output, args.title)
