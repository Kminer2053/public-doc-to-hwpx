"""
split_gongmun_paragraphs.py — placeholder 강제 단락 분리 (v3.6.4 신규, v3.6.6 롤백)
────────────────────────────────────────────────────────────────────────
⚠️ v3.6.6 결정: SPLIT_PAIRS 빈 상태로 변경 (실질 비활성화).

이유: v3.6.4 에서 공문 본문 text_008/text_009 가 같은 hp:p 에 있는 걸 결함으로
판단하고 강제 분리했으나, 사용자와 함께 양식 매핑(skeleton_mapping.json) 을
정밀 분석한 결과 그것이 **양식 의도** 임을 확인.

공문 양식 본문 슬롯 의도:
  text_007 (paraPr=17) — 1번 항목 (단독 단락)
  text_008 (paraPr=29) — "2. " 마커
  text_009 (paraPr=29) — 2번 항목 본문 (text_008 과 같은 단락, 의도적)
    가. (목차_항목_001), 나. (목차_항목_002), 1)/가)/(1)/① (text_010~013)
  목차_항목_003/004 — 붙임 1, 2

즉 공문 본문은 1번/2번 두 단락 구조이며, text_008/text_009 를 분리하면 양식
의도를 깬다. 사용자의 3번 이상 항목이 필요하면 text_009 안에 통합하는 것이
양식 친화적 사용법.

이 스크립트는 향후 *다른* 양식 결함 (실제 양식 의도와 다른 placeholder 묶음)
을 처리할 가능성을 위해 구조만 유지하고, 현재 SPLIT_PAIRS 는 비어 있음.
"""

import re
import sys


# v3.6.6: 빈 리스트. 양식 결함이 추가로 발견되면 여기에 등록.
SPLIT_PAIRS = []


def split_combined_placeholders(xml: str) -> tuple:
    """SPLIT_PAIRS 가 비어있으면 변경 없이 그대로 반환."""
    n_splits = 0
    for first_token, second_token, para_pr, char_pr in SPLIT_PAIRS:
        idx_first = xml.find(f"{{{{{first_token}}}}}")
        if idx_first == -1:
            continue
        end_first_run = xml.find("</hp:t></hp:run>", idx_first)
        if end_first_run == -1:
            continue
        end_first_run += len("</hp:t></hp:run>")
        end_p = xml.find("</hp:p>", end_first_run)
        if end_p == -1:
            continue
        idx_second = xml.find(f"{{{{{second_token}}}}}", end_first_run)
        if idx_second == -1 or idx_second > end_p:
            continue
        start_p = xml.rfind("<hp:p ", 0, idx_first)
        if start_p == -1:
            continue
        end_start_tag = xml.find(">", start_p) + 1
        opening_tag = xml[start_p:end_start_tag]
        new_p_open = re.sub(
            r'paraPrIDRef="\d+"',
            f'paraPrIDRef="{para_pr}"',
            opening_tag
        )
        insertion = f'</hp:p>{new_p_open}'
        xml = xml[:end_first_run] + insertion + xml[end_first_run:]
        n_splits += 1
    return xml, n_splits


def main():
    if len(sys.argv) < 3:
        print("사용법: python3 split_gongmun_paragraphs.py <input.xml> <output.xml>")
        sys.exit(1)
    inp, out = sys.argv[1], sys.argv[2]
    with open(inp, "r", encoding="utf-8") as f:
        xml = f.read()
    new_xml, n = split_combined_placeholders(xml)
    with open(out, "w", encoding="utf-8") as f:
        f.write(new_xml)
    print(f"✅ {n} 쌍 분리 적용: {out}")


if __name__ == "__main__":
    main()
