"""
fix_namespaces.py
────────────────────────────────────────────────────────────
⚠️ HWPX 생성 후 반드시 실행해야 하는 필수 후처리 스크립트

누락 시: 한글 Viewer에서 빈 페이지로 표시되거나 문서가 열리지 않음
출처: jkf87/hwpx-skill 구조 참조
────────────────────────────────────────────────────────────

네임스페이스 URI → 프리픽스 매핑:
  http://www.hancom.co.kr/hwpml/2011/head      → hh
  http://www.hancom.co.kr/hwpml/2011/core      → hc
  http://www.hancom.co.kr/hwpml/2011/paragraph → hp
  http://www.hancom.co.kr/hwpml/2011/section   → hs
"""

import sys
import re
import zipfile
import os

NS_MAP = {
    'http://www.hancom.co.kr/hwpml/2011/head':      'hh',
    'http://www.hancom.co.kr/hwpml/2011/core':      'hc',
    'http://www.hancom.co.kr/hwpml/2011/paragraph': 'hp',
    'http://www.hancom.co.kr/hwpml/2011/section':   'hs',
}

def fix_namespaces_in_xml(xml_text: str) -> str:
    """XML 텍스트의 네임스페이스 프리픽스를 표준화"""
    for uri, prefix in NS_MAP.items():
        # xmlns 선언 정규화
        xml_text = re.sub(
            rf'xmlns:[a-zA-Z0-9_]+="{re.escape(uri)}"',
            f'xmlns:{prefix}="{uri}"',
            xml_text
        )
        # 태그 내 URI 참조 → 프리픽스 교체
        xml_text = re.sub(
            rf'\{{{re.escape(uri)}\}}([a-zA-Z0-9_]+)',
            rf'{prefix}:\1',
            xml_text
        )
    return xml_text

def fix_hwpx(hwpx_path: str) -> bool:
    """
    HWPX 파일 내 모든 XML의 네임스페이스를 후처리
    Returns: True(성공) / False(실패)
    """
    tmp_path = hwpx_path + '.ns_fix.tmp'
    try:
        with zipfile.ZipFile(hwpx_path, 'r') as zin:
            with zipfile.ZipFile(tmp_path, 'w') as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)

                    # mimetype은 반드시 ZIP_STORED (비압축)
                    if item.filename == 'mimetype':
                        zout.writestr(item, data, compress_type=zipfile.ZIP_STORED)
                        continue

                    # XML 파일만 네임스페이스 수정
                    if item.filename.endswith('.xml') or item.filename.endswith('.hpf'):
                        try:
                            text = data.decode('utf-8')
                            text = fix_namespaces_in_xml(text)
                            data = text.encode('utf-8')
                        except UnicodeDecodeError:
                            pass  # 바이너리 파일은 그대로

                    zout.writestr(item, data, compress_type=zipfile.ZIP_DEFLATED)

        os.replace(tmp_path, hwpx_path)
        return True

    except Exception as e:
        print(f'[fix_namespaces] 오류: {e}', file=sys.stderr)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('사용법: python fix_namespaces.py <파일.hwpx>')
        sys.exit(1)
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f'파일 없음: {path}', file=sys.stderr)
        sys.exit(1)
    success = fix_hwpx(path)
    if success:
        print(f'[fix_namespaces] ✅ 완료: {path}')
    else:
        print(f'[fix_namespaces] ❌ 실패: {path}', file=sys.stderr)
        sys.exit(1)
