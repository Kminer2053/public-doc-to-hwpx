"""
빈 골격 hwpx의 {{토큰}} placeholder를 실제 값으로 채워서 완성된 hwpx 생성.

사용법:
    python fill_skeleton.py \\
        --skeleton templates/format_full/skeleton.hwpx \\
        --values values.json \\
        --output result.hwpx
        
values.json 구조:
{
    "표지_부제": "- AX 시대 인적자원 혁신을 위한 -",
    "표지_제목": "전사적 AI역량 강화 추진계획",
    "보고일": "2026. 5.",
    ...
}
"""

import argparse
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path


def xml_escape(text: str) -> str:
    """XML 안전 처리"""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def fill_skeleton(skeleton_path: Path, values: dict, output_path: Path) -> dict:
    """빈 골격의 placeholder를 values 딕셔너리로 채움"""
    workdir = Path("/tmp/fill_work")
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)
    
    with zipfile.ZipFile(skeleton_path, "r") as zf:
        zf.extractall(workdir)
    
    sec_path = workdir / "Contents" / "section0.xml"
    sec = sec_path.read_text(encoding="utf-8")
    
    # 모든 {{토큰}} 찾기
    tokens_found = set(re.findall(r'\{\{([^}]+)\}\}', sec))
    
    # 치환
    filled_count = 0
    unfilled = []
    for token in tokens_found:
        if token in values:
            replacement = xml_escape(values[token])
            sec = sec.replace(f"{{{{{token}}}}}", replacement)
            filled_count += 1
        else:
            # 값 없으면 빈 문자열로 비움 (서식은 유지)
            sec = sec.replace(f"{{{{{token}}}}}", "")
            unfilled.append(token)
    
    sec_path.write_text(sec, encoding="utf-8")
    
    # 제목 갱신 (content.hpf)
    hpf_path = workdir / "Contents" / "content.hpf"
    if hpf_path.exists() and values.get("표지_제목"):
        hpf = hpf_path.read_text(encoding="utf-8")
        safe = xml_escape(values["표지_제목"])
        hpf = re.sub(r'<opf:title>[^<]*</opf:title>',
                     f'<opf:title>{safe}</opf:title>', hpf, count=1)
        hpf_path.write_text(hpf, encoding="utf-8")
    
    # 재패키징
    if output_path.exists():
        output_path.unlink()
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        mt = workdir / "mimetype"
        zf.write(mt, "mimetype", compress_type=zipfile.ZIP_STORED)
        for f in sorted(workdir.rglob("*")):
            if f.is_file() and f.name != "mimetype":
                zf.write(f, f.relative_to(workdir).as_posix())
    
    return {
        "tokens_in_skeleton": len(tokens_found),
        "filled": filled_count,
        "emptied": len(unfilled),
        "emptied_tokens": unfilled,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skeleton", required=True)
    parser.add_argument("--values", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    values = json.loads(Path(args.values).read_text(encoding="utf-8"))
    result = fill_skeleton(
        Path(args.skeleton),
        values,
        Path(args.output)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
