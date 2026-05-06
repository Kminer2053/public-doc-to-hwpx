"""
validate.py — HWPX 구조 검증
사용법: python validate.py <파일.hwpx>
"""
import sys, zipfile
from pathlib import Path

REQUIRED_FILES = ['mimetype', 'Contents/content.hpf',
                  'Contents/header.xml', 'Contents/section0.xml']

def validate(path: str) -> bool:
    ok = True
    try:
        with zipfile.ZipFile(path, 'r') as z:
            names = z.namelist()

            # 필수 파일 존재 확인
            for f in REQUIRED_FILES:
                if f not in names:
                    print(f'[validate] ❌ 누락: {f}')
                    ok = False

            # mimetype: ZIP_STORED 확인
            if 'mimetype' in names:
                info = z.getinfo('mimetype')
                if info.compress_type != 0:
                    print('[validate] ❌ mimetype이 STORED가 아님 (DEFLATED 감지)')
                    ok = False
                else:
                    print('[validate] ✅ mimetype: STORED')

            # section0.xml: secPr 포함 확인
            if 'Contents/section0.xml' in names:
                xml = z.read('Contents/section0.xml').decode('utf-8')
                if 'secPr' not in xml:
                    print('[validate] ❌ section0.xml에 secPr 없음 (문서 열림 실패 위험)')
                    ok = False
                else:
                    print('[validate] ✅ secPr 존재')

                # 네임스페이스 확인
                for ns in ['xmlns:hp=', 'xmlns:hs=']:
                    if ns not in xml:
                        print(f'[validate] ⚠️  {ns} 네임스페이스 누락')

            # XML 파싱 가능 여부
            try:
                from lxml import etree
                for fname in ['Contents/header.xml', 'Contents/section0.xml']:
                    if fname in names:
                        data = z.read(fname)
                        etree.fromstring(data)
                print('[validate] ✅ XML 파싱 정상')
            except ImportError:
                pass
            except Exception as e:
                print(f'[validate] ❌ XML 파싱 오류: {e}')
                ok = False

    except zipfile.BadZipFile:
        print(f'[validate] ❌ 손상된 ZIP 파일: {path}')
        return False

    if ok:
        size = Path(path).stat().st_size
        print(f'[validate] ✅ 검증 통과 ({size:,} bytes)')
    return ok


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('사용법: python validate.py <파일.hwpx>')
        sys.exit(1)
    sys.exit(0 if validate(sys.argv[1]) else 1)
