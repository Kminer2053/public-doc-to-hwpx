# v3.5.0 변경 사항 (2026-05-13)

## 풀버전 보고서 4대 함정 자동 검사 + 통합 빌드 도입

### 추가/변경된 파일

| 파일 | 상태 | 내용 |
|------|------|------|
| `scripts/build_full.py` | **신규** | 풀버전 통합 빌더 (4대 함정 검사 + 5단계 빌드 자동화) |
| `scripts/simulate_pages.py` | 수정 | `--values` / `--apply-to-values` 인자 추가 |
| `templates/format_full/skeleton_mapping.json` | 수정 | 슬롯별 `hierarchy`·`marker_type`·`hint` 메타 추가 |
| `references/format-full.md` | 수정 | 4대 함정 명세 + 권장 분포 + 워크플로우 |
| `SKILL.md` | 수정 | 버전·워크플로우·Critical Rules 12~15 추가 |

### 해결된 풀버전 빌드 문제

1. **목차 슬롯 위계 위반**: 대제목/소제목 슬롯 위치가 고정인데 임의 매핑 → 서식 깨짐
2. **빈 슬롯으로 인한 점선 끊김**: 양식 슬롯 수보다 콘텐츠가 적으면 정렬 무너짐
3. **본문 마커 중복**: `본문_항목_001~009` 는 자동 ○ 마커인데 ◦ 직접 표기 시 중복
4. **페이지번호 미반영**: `simulate_pages.py` 가 계산만 하고 hwpx 에 적용 안 함

### 새 빌드 명령

```bash
# Before (v3.4.0): 7단계 수동
fill_skeleton → fix_namespaces → simulate_pages(출력만)
→ 수동 갱신 → fill_skeleton → fix_namespaces
→ ensure_body_anchor → validate

# After (v3.5.0): 1단계 자동
python3 scripts/build_full.py --values my_values.json --output result.hwpx
```

### 호환성

- 1p/시행문/이메일 빌드 흐름 변경 없음
- 기존 스크립트 호출 방식 모두 하위 호환 (인자 추가만 됨)
- skeleton_mapping.json 메타 추가는 기존 키 유지 + 신규 키 추가 (하위 호환)
