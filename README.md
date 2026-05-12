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

## 스킬 작동 구조 (v3.4.0 — 6단계 빈 골격 채우기)

![public-doc-to-hwpx 스킬 작동 구조](assets/public_doc_to_hwpx_skill_pipeline.svg)

### 핵심 변화 (v3.4.0)

이전의 4단계 워크플로우는 v3.4.0에서 **빈 골격(skeleton) 기반의 6단계 파이프라인**으로 개선되었습니다.

| 단계 | v3.0.1까지 | v3.4.0+ (개선사항) |
|------|-----------|------------------|
| 1. 입력 | 마크다운/PDF 파싱 | (동일) |
| 2. 양식 | 4개 양식 중 선택 | (동일) |
| 3. 콘텐츠 다듬기 | 글쓰기 최적화 규칙 적용 | **Author 가이드 참조** (원칙·구조·규칙 명확화) |
| 4. 값매핑 | 콘텐츠 → 슬롯 직접 매핑 | **skeleton_mapping.json** (표준 매핑 문서화) |
| 5. 빌드 파이프라인 | 처음부터 XML 생성 | **빈 골격 토큰 치환** (디자인 100% 보존) |
| 6. 출력 | (동일) | (동일) |

### 빈 골격 채우기의 장점

- ✅ **양식 디자인 100% 보존** — 한글(hwp)의 테이블, 테두리, 음영, 페이지헤더 무결성 보장
- ✅ **외부 의존성 제거** — templates/_skeleton.hwpx 를 스킬에 동봉 (python-hwpx 라이브러리 불필요)
- ✅ **메타파일 자동 보정** — Skeleton의 한컴 표준 준수 메타파일 7종을 그대로 사용
- ✅ **회귀 테스트 완료** — 4개 양식 빌드 + 메타파일 일치 + HWP 식별 모두 검증

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

## 디렉토리 구조 (v3.4.0)

```
public-doc-to-hwpx/
├── SKILL.md                                   # 6단계 워크플로우 (Claude Skill 진입점)
├── README.md                                  # 이 파일
├── LICENSE                                    # MIT
│
├── scripts/                                   ★ v3.4.0 — 빈 골격 채우기 단일 빌드 워크플로우
│   ├── fill_skeleton.py                       ★ 메인 빌더 — 토큰을 값으로 치환
│   ├── make_skeleton.py                       새 양식 등록 시 hwpx → 빈 골격 변환
│   ├── fix_namespaces.py                      ⚠️ 필수 후처리 (빠뜨리면 한글에서 안 열림)
│   ├── simulate_pages.py                      ★ v3.3.0 페이지 시뮬레이션 + 목차 페이지번호
│   ├── ensure_body_anchor.py                  ★ v3.3.0 풀버전 본문 시작 pageBreak 강제
│   ├── validate.py                            구조 검증
│   │
│   ├── [이전 버전] compose_doc.py             v3.0.1 4단계 파이프라인 (참고용)
│   ├── [이전 버전] layout_optimizer.py        v3.0.1 글쓰기 최적화
│   ├── [이전 버전] format_builders.py         v3.0.1 양식 빌더
│   └── [이전 버전] build_hwpx.py              v3.0.1 HWPX 조립
│
├── templates/
│   ├── _skeleton.hwpx                         ★ v3.4.0 폴백 베이스 (7.4KB, 한컴 표준 준수)
│   ├── charpr_mapping.json                    ★ v3.4.0 양식별 charPr 역할 → id 매핑표
│   ├── government/header.xml                  관공서 charPr/paraPr/borderFill 정의
│   │
│   ├── format_1p/
│   │   ├── standard.hwpx                      1p 보고서 표준 양식 (맑은 고딕, 35개 슬롯)
│   │   ├── skeleton.hwpx                      ★ v3.4.0 빈 골격 (35개 토큰)
│   │   ├── skeleton_mapping.json              ★ v3.4.0 토큰 ↔ 원본 텍스트 매핑
│   │   └── outline_guide.md                   ★ v3.3.1 보고 목적별 11가지 표준 목차
│   │
│   ├── format_full/
│   │   ├── standard.hwpx                      풀버전 보고서 표준 양식 (표 10개, 127개 슬롯)
│   │   ├── skeleton.hwpx                      ★ v3.4.0 빈 골격 (127개 토큰 + 페이지번호)
│   │   └── skeleton_mapping.json              ★ v3.4.0 토큰 ↔ 원본 텍스트 매핑
│   │
│   ├── format_gongmun/
│   │   ├── standard.hwpx                      시행문 표준 양식 (27개 슬롯)
│   │   ├── skeleton.hwpx                      ★ v3.4.0 빈 골격 (27개 토큰)
│   │   └── skeleton_mapping.json              ★ v3.4.0 토큰 ↔ 원본 텍스트 매핑
│   │
│   └── format_email/                          (이메일은 텍스트만, 양식 불필요)
│
├── references/                                Claude가 작업 중 참조하는 Author 가이드 7개
│   ├── writing-principles.md                  ★ 보고서 작성 원칙 (강의자료 + 사례 통합)
│   ├── layout-rules.md                        ★ 레이아웃 최적화 규칙
│   ├── format-selection.md                    양식 선택 결정트리
│   ├── format-1p.md                           1p 보고서 가이드
│   ├── format-full.md                         풀버전 보고서 가이드
│   ├── format-gongmun.md                      시행문 가이드
│   └── format-email.md                        이메일 가이드
│
└── assets/
    └── public_doc_to_hwpx_skill_pipeline.svg  작동 구조 설명 다이어그램
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

## 작성 원칙 (완전 가이드)

### 📖 전체 원칙 (5가지)

자세한 내용은 [`references/writing-principles.md`](references/writing-principles.md) 참조.

1. **두괄식** — 결론·요약을 첫 3줄 안에. 1p 보고서는 음영 박스로 압축.
2. **개조식** — 키워드 중심, 글머리·번호로 짧게. 서술식은 시행문 본문 도입부에서만.
3. **한 문장 한 핵심** — 한 문장에 두 개 정보 = 분리. 한 줄(약 40자) 초과 = 분리.
4. **명사형 제목** — `~와 관련된 ~` → `~ 관련 ~` 또는 단순화.
5. **적의를 보이는 것들 4종 점검** — `-적`, `의`, `것`, `들`. 빼도 의미 유지되면 빼라.

---

### 📋 보고 목적별 표준 구조

양식마다 다릅니다. 더 자세한 내용은 각 양식 가이드에서 확인하세요.

#### **1️⃣ 1페이지 보고서** (format_1p)
📖 가이드: [`templates/format_1p/outline_guide.md`](templates/format_1p/outline_guide.md) · [`references/format-1p.md`](references/format-1p.md)

| 특징 | 설명 |
|------|------|
| **핵심 철학** | 의사결정자가 30초 안에 읽고, 5분 안에 결정할 수 있도록 |
| **표준 구조** | 제목 + 부제(보고배경) + **음영 박스(두괄식 요지)** + 본문 4절 |
| **글머리 위계** | □ 대제목 → ○ 항목 → - 세부 → * 주석 (4단계) |
| **4절 표준 목차** | ① 보고요지 ② 배경·현황 ③ 주요내용·검토 ④ 향후계획·요청 |
| **보고 유형** | <br>• **현황·동향** — 핵심 변화 + 수치 + 비교<br>• **검토·의사결정** — 현황 + 검토사항 + 결론<br>• **계획·사업** — 배경 + 목표 + 추진방안 + 일정<br>• **결과·성과** — 추진내용 + 성과 + 시사점<br>• **회의결과·이슈** — 의제 + 결정사항 + 향후조치 |
| **압축 옵션** | 3절 형식(개요 + 주요내용 + 계획) 또는 5절 형식(배경/현황 분리) |
| **우수예시** | `협력사업 실무협의 보고`, `신규 사업 제휴 검토`, `시설 언론보도 현황` |

#### **2️⃣ 풀버전 보고서** (format_full)
📖 가이드: [`references/format-full.md`](references/format-full.md)

| 특징 | 설명 |
|------|------|
| **구성** | 표지 + 목차 + 보고요약(1쪽) + 본문(다중쪽) + 별첨 |
| **글머리 위계** | Ⅰ. 1. 가. (1) (4단계) |
| **보고 대상** | 상급자, 관계 부서, 제출 문서용 |
| **본문 구조** | 배경·현황 → 주요내용·검토 → 결론·향후계획 (기본 3부 구성) |
| **필수 요소** | 페이지번호 자동 계산, 목차의 쪽번호 자동 매핑 |
| **표 활용** | 최대 10개 테이블 지원 (요약표, 비교표, 일정표 등) |

#### **3️⃣ 공문·시행문** (format_gongmun)
📖 가이드: [`references/format-gongmun.md`](references/format-gongmun.md)

| 특징 | 설명 |
|------|------|
| **구성** | 수신 + 발신 + 제목 + 본문(서술식) + 서명 |
| **글머리 위계** | 1. 가. 1) (1) (4단계, 글머리로 강조 지양) |
| **보고 대상** | 외부 기관, 일반 국민 |
| **본문 문체** | 서술식 도입부 → 개조식 본론 → 마무리(경어) |
| **형식 엄수** | 관공서 문서 형식 규칙 준수 필수 |
| **세로쓰기** | 기관에 따라 세로쓰기(한글 전용) 옵션 지원 |

#### **4️⃣ 메일 본문** (format_email)
📖 가이드: [`references/format-email.md`](references/format-email.md)

| 특징 | 설명 |
|------|------|
| **분량** | 200–500자 (동료 협업용) |
| **구성** | 제목 요약 + 결론(굵게) + 기한 명시 + 파일명 |
| **출력** | 마크다운(.md) 또는 순문본(.txt) — 복붙용 |
| **5원칙** | ① 제목 명확히 ② 결론부터 ③ 기한 명시 ④ 파일명 명시 ⑤ 참조자 포함 |
| **글머리** | □ - * (3단계, 단순) |

---

### 🎓 더 배우기

| 자료 | 위치 | 내용 |
|------|------|------|
| **보고서 작성 원칙** | `references/writing-principles.md` | 개조식↔서술식 변환, 패턴, 사례 |
| **레이아웃 최적화** | `references/layout-rules.md` | 한 문장 길이, 페이지 걸침, 글머리 정렬 |
| **양식 선택** | `references/format-selection.md` | 4개 양식 선택 결정트리 |
| **1p 보고서 목차** | `templates/format_1p/outline_guide.md` | 11가지 보고 유형별 표준 목차 |
| **각 양식 가이드** | `references/format-*.md` | 각 양식의 구성·글머리·우수예시 |

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
| 2026-05-05 | 3.0.0 | 글쓰기 품질 강화 — 4단계 워크플로우 + 4개 양식 빌더 + layout_optimizer + 통합 파이프라인 |
| 2026-05-06 | 3.0.1 | 한글 호환성 핫픽스 — Skeleton.hwpx 기반 빌드로 전면 전환 (메타파일 6개 한컴 표준 준수) |
| 2026-05-07 | 3.3.0 | 페이지 시뮬레이션 추가 (simulate_pages.py + ensure_body_anchor.py) |
| 2026-05-07 | 3.3.1 | 풀버전 목차 표준화 (outline_guide.md, 11가지 보고 유형) |
| 2026-05-13 | **3.4.0** | **빈 골격 채우기 통합** — 6단계 파이프라인으로 전환, skeleton_mapping.json 도입, templates 구조 재정리, 내장 skeleton 추가 |

---

## 라이선스

MIT License — [LICENSE](LICENSE) 참조.

> 이 스킬은 공공기관 보고서 작성 노하우를 누구나 자유롭게 활용·개선할 수 있도록 공유합니다.
> 개선 제안·이슈는 GitHub Issues 환영합니다.
