# public-doc-to-hwpx

> **AI 콘텐츠를 공공기관 표준 보고서로 다듬어 HWPX·메일 본문으로 변환하는 Claude Skill**
> 한 문장 한 줄, 개조식, 두괄식 — AI가 없던 시절 한글(hwp)을 쓰던 베테랑 보고서 작성자가 만든 것처럼.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![HWPX 5.1.3](https://img.shields.io/badge/HWPX-5.1.3-green.svg)](https://www.hancom.com/)

---

## 왜 만들었나

대부분의 AI 문서 자동화 도구는 **양식**(서식·레이아웃) 자동화에 집중합니다.
하지만 공공기관에서 평생 보고서를 써온 분들이 늘 강조하는 건 다른 부분입니다.

> "보고서는 30초 안에 핵심을 파악할 수 있어야 한다."
> "한 문장에 두 개 이상의 정보가 들어가면 다시 읽게 된다."
> "`-적`, `의`, `것`, `들` — 빼도 의미가 살아나면 빼라."

이 스킬은 **약 20여 년의 공공기관 근무 경력을 가진 직원의 보고서 작성 노하우**를
실제 강의자료와 우수예시에서 추출하여, AI가 자동으로 글을 다듬어주는 도구로 구현했습니다.

XML 빌드보다 **글쓰기 품질**을 먼저 생각하는 것이 이 스킬의 핵심입니다.

---

## 4단계 워크플로우

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│   ① 콘텐츠 정리        ②  양식 결정       ③  콘텐츠 매핑      ④ 레이아웃 최적화      │
│   ─────────         ─────────       ─────────         ─────────         │
│   md/docx/pdf/txt    참조 hwpx 우선     필수항목 매핑       적/의/것/들 정리         │
│   파싱 + 구조화      4개 양식 자동추천   누락 시 ※AI 플래그   한 문장 한 줄 점검       │
│                                                       페이지 걸침 점검         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                       ┌──────────────────┐
                       │   ⑤ HWPX 빌드      │
                       │ (이메일은 .md)     │
                       └──────────────────┘
```

각 단계가 분리되어 있어 한 단계만 따로 실행하거나, `compose_doc.py` 한 줄로 전체 파이프라인을 돌릴 수 있습니다.

---

## 4개 양식 비교

| 양식 | 분량 | 독자 | 출력 | 글머리 위계 | 핵심 특징 |
|------|------|------|------|-------------|----------|
| **`format_1p`** | A4 1쪽 강제 | 의사결정자 | `.hwpx` | □ ○ - * | 두괄식 음영 박스 + 핵심 항목만 |
| **`format_full`** | A4 5–30쪽 | 상급자·관계부서 | `.hwpx` | Ⅰ. 1. 가. (1) | 표지 + 목차 + 보고요약 + 본문 + 별첨 |
| **`format_gongmun`** | A4 1–3쪽 | 외부기관·일반국민 | `.hwpx` | 1. 가. 1) (1) | 수신·제목·본문·발신명의 형식 엄수 |
| **`format_email`** | 200–500자 | 협업자 | `.md`/`.txt` | □ - * | 두괄식 결론 + 기한 명시 (메일 본문 복붙용) |

---

## 가장 빠른 사용법 (one-shot)

```bash
git clone https://github.com/<your-username>/public-doc-to-hwpx.git
cd public-doc-to-hwpx

# 1페이지 보고서 빌드
python3 scripts/compose_doc.py input.md output.hwpx \
  --format format_1p \
  --meta meta.json \
  --report-path /tmp/optimization_report.md
```

### `input.md` 예시

```markdown
# ○○기관 협력사업 실무협의 보고

## 추진배경
- 한국을 대표하는 공기업과 중소기업과의 상호 협력
- 판로 개척 어려운 중소기업의 전시·판매 통한 국가경제 발전

## 추진경과
- (6.15. ○○기관 유선협의)
  - ○○공사에서 중소기업 제품 판로개척 노력에 감사
  - 향후 MOU 등 적극 의사표명

## 향후계획
- MOU 체결에 따른 세부사항 협의 : '12. 6월
- MOU 체결 : '12. 7월
```

### `meta.json` 예시

```json
{
  "subtitle": "- ○○공사와 중소기업 상생협력을 위한 -",
  "author": "○○○처장 ○○○",
  "date": "'25.11.",
  "phone": "4315"
}
```

### 결과

- `output.hwpx` — 한글에서 바로 열리는 1페이지 보고서
- `optimization_report.md` — 자동 적용·검토 권장 사항 리포트

---

## 글쓰기 자동 변환 (★ 핵심 차별점)

`layout_optimizer.py` 가 다음을 **자동 적용**합니다.

### 신뢰도 높음 — 자동 적용

| 변환 전 | 변환 후 |
|---------|---------|
| `~와 관련된 ~` | `~ 관련 ~` |
| `~할 예정이었으나 이를 유예하였습니다` | `~ 예정 → 유예` |
| `여러/많은/각/모든/수많은/대부분의/다양한 ~들` | (들 제거) |

### 신뢰도 중간 — 검토 권장으로 표시

- `~할 것으로 보입니다` → `~ 예상 / ~ 전망`
- `~한 것으로 판단됩니다` → `~ 판단 / ~로 보임`
- `~하는 것이 필요합니다` → `~가 필요합니다`
- `~에 대한`, `~ 중 하나인`, `~의 ~의 ~` (의 연쇄)
- `사회적/경제적/정치적/행정적/조직적` + 명사
- 한 문장 46자 초과 (분리 후보)

### Before / After 예시

**Before** (66자, 정보 3개 혼재):
> 라마단 종료에 따라 중동항로의 거래량과 적재율 회복이 예상되며, 라마단 직전 적재율은 95% 수준이었고, 선사협의체는 성수기 할증료 부과를 유예하였습니다.

**After** (개조식 변환):
```
- 라마단 종료 → 중동항로 거래량·적재율 회복 예상
- 라마단 직전 적재율: 약 95%
- 성수기 할증료(USD 300/TEU) 부과 유예
```

---

## 디렉토리 구조

```
public-doc-to-hwpx/
├── SKILL.md                          # 4단계 워크플로우 (Claude Skill 진입점)
├── README.md                         # 이 파일
├── LICENSE                           # MIT
├── scripts/
│   ├── compose_doc.py                ★ 메인 파이프라인 (4단계 통합)
│   ├── layout_optimizer.py           ★ 글쓰기 최적화 (적/의/것/들, 한 문장 한 줄)
│   ├── format_builders.py            ★ 4개 양식 빌더
│   ├── content_mapper.py             콘텐츠 파싱 (md/docx/pdf/txt)
│   ├── hwpx_helpers.py               저수준 XML 빌더
│   ├── build_hwpx.py                 HWPX 조립
│   ├── fix_namespaces.py             ⚠️ 필수 후처리
│   └── validate.py                   구조 검증
├── templates/
│   ├── government/header.xml         관공서 charPr/paraPr 정의
│   └── format_*/                     양식별 참조 hwpx 위치
└── references/                       Claude가 작업 중 참조하는 가이드 7개
    ├── writing-principles.md         ★ 보고서 작성 원칙 (강의자료 + 사례 통합)
    ├── layout-rules.md               ★ 레이아웃 최적화 규칙
    ├── format-selection.md           양식 선택 결정트리
    ├── format-1p.md                  1p 보고서 가이드
    ├── format-full.md                풀버전 보고서 가이드
    ├── format-gongmun.md             시행문 가이드
    └── format-email.md               이메일 가이드
```

---

## Claude Skill로 설치

이 리포지토리는 [Claude Skill](https://docs.claude.com/) 형식을 따르며, Claude·Cursor·Codex 등에서 사용 가능합니다.

### Claude Desktop / Web

```bash
# 1. 사용자 스킬 디렉토리에 복사
cp -r public-doc-to-hwpx ~/.claude/skills/

# 2. Claude 재시작 후, 자연어로 호출
"매출 실적 보고서 1페이지로 작성해줘"
"이 내용을 시행문 양식으로 hwpx 만들어줘"
```

### Cursor / Codex

`.cursor/rules` 또는 `AGENTS.md` 에 다음 추가:

```yaml
description: HWPX 보고서 작성 시 public-doc-to-hwpx v3 사용
globs: ["*.hwpx", "*.md", "*.docx"]
---
1. SKILL.md 의 4단계 워크플로우를 따른다
2. compose_doc.py 한 번으로 빌드 + 후처리 + 검증 자동
3. layout_optimizer 의 검토 권장 사항을 사용자에게 항상 표시
4. 1p 양식 1쪽 초과 시 풀버전 변경 권고 (자동 변경 금지)
```

---

## 작성 원칙 (요약)

자세한 내용은 [`references/writing-principles.md`](references/writing-principles.md) 참조.

1. **두괄식** — 결론·요약을 첫 3줄 안에. 1p 보고서는 음영 박스로 압축.
2. **개조식** — 키워드 중심, 글머리·번호로 짧게. 서술식은 시행문 본문 도입부에서만.
3. **한 문장 한 핵심** — 한 문장에 두 개 정보 = 분리. 한 줄(약 40자) 초과 = 분리.
4. **명사형 제목** — `~와 관련된 ~` → `~ 관련 ~` 또는 단순화.
5. **적의를 보이는 것들 4종 점검** — `-적`, `의`, `것`, `들`. 빼도 의미 유지되면 빼라.

---

## 출처와 학습 자료

이 스킬은 **약 20여 년의 공공기관 근무 경력을 가진 직원의 보고서 작성 강의자료(전 25페이지)와
우수예시 모음**을 학습하여 만들어졌습니다.
저작권 보호를 위해 원문은 리포지토리에 포함하지 않으며, 핵심 원칙·패턴만 코드와 가이드에 반영했습니다.

학습 자료에서 추출한 주요 내용:

- 보고서 논리 패턴 (Why → How → What)
- 개조식 ↔ 서술식 변환 사례
- 1페이지 보고서 표준 골격 3가지 패턴 (결과보고형 / 진행보고형 / 동향보고형)
- 시행문 = 서술식 + 개조식 혼용 원칙
- 이메일 5원칙 (제목·결론·기한·파일명·참조)
- 「적의를 보이는 것들」 4종 (-적 / 의 / 것 / 들) 자동 점검

---

## 관련 도구

- [chrisryugj/kordoc](https://github.com/chrisryugj/kordoc) — HWP/HWPX → Markdown 파서. 사용자 참조 hwpx 분석 시 활용.
- [Hancom HWPX 공식 문서](https://www.hancom.com/) — HWPX 5.1.3 스펙
- [Anthropic Claude Skills](https://docs.claude.com/) — 이 스킬의 진입점 형식

---

## 변경 이력

| 날짜 | 버전 | 변경사항 |
|------|------|----------|
| 2026-04-05 | 1.0.0 | 최초 생성 (python-hwpx 직접 API) |
| 2026-04-05 | 2.0.0 | jkf87/hwpx-skill 구조 흡수, fix_namespaces 추가 |
| 2026-05-05 | **3.0.0** | **글쓰기 품질 강화** — 4단계 워크플로우 + 4개 양식 빌더 + layout_optimizer + 통합 파이프라인 |
| 2026-05-06 | **3.0.1** | **한글 호환성 핫픽스** — Skeleton.hwpx 기반 빌드로 전면 전환 (메타파일 6개 한컴 표준 준수), `paraPrIDRef="20"` 오류 정정 |
| 2026-05-08 | **3.4.0** | **스켈레톤 기반 파이프라인** — 빈 골격에 값만 채우는 방식으로 양식 100% 보존, simulate_pages + ensure_body_anchor 추가 |
| 2026-05-13 | **3.5.0** | **풀버전 4대 함정 자동 검사** — build_full.py 신규 (위계 위반·빈 슬롯·마커 중복·페이지번호 미반영 해결), simulate_pages --values 인자 추가 |

---

## 라이선스

MIT License — [LICENSE](LICENSE) 참조.

> 이 스킬은 공공기관 보고서 작성 노하우를 누구나 자유롭게 활용·개선할 수 있도록 공유합니다.
> 개선 제안·이슈는 GitHub Issues 환영합니다.
