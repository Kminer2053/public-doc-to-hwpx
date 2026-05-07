---
name: public-doc-to-hwpx
description: "AI가 생성한 콘텐츠를 공공기관 표준 보고서로 다듬어 HWPX 또는 메일 본문으로 변환하는 스킬. 보고서 작성 원칙(개조식 문체·한 문장 한 줄·적/의/것/들 정리·두괄식 요약)을 자동 적용하여 의사결정자가 30초 안에 읽고 5분 안에 판단할 수 있는 가독성 높은 문서를 만든다. 4개 양식(1페이지 보고서/풀버전 보고서/시행문/이메일)을 지원하고, 사용자가 참조 hwpx·hwtx 파일을 주면 그 서식을 자동 추출해 일치시킨다. 트리거: hwpx, HWP, 한글파일, 한글로 작성, 공문, 시행문, 보고서, 1페이지 보고서, 1p 보고, 기획서, 검토보고서, 추진계획, 결과보고, 검토결과, 공공기관 문서, 메일 작성, 이메일 본문, 회신 요청, 보고드림"
allowed-tools: "Bash(python3*), Read, Write, Glob"
---

# 공공기관 보고서 작성 + HWPX 변환 스킬 (v3.0)

> **이 스킬의 목표**: AI가 없던 시절 한글(hwp)을 쓰던 베테랑 보고서 작성자가 만든 것처럼,
> 독자 입장에서 가독성이 높고 핵심이 빠르게 읽히는 공공기관 보고서를 자동 생성한다.

---

## 디렉토리 구조

```
public-doc-to-hwpx/
├── SKILL.md                          ← 이 파일 (4단계 워크플로우)
├── scripts/
│   ├── compose_doc.py                ★ 메인 파이프라인 (4단계 통합 실행)
│   ├── layout_optimizer.py           ★ 레이아웃 최적화 (적/의/것/들, 한 문장 한 줄)
│   ├── format_builders.py            ★ 4개 양식 빌더 (1p / full / gongmun / email)
│   ├── content_mapper.py             콘텐츠 파싱 (md/docx/pdf/txt)
│   ├── hwpx_helpers.py               저수준 XML 빌더
│   ├── build_hwpx.py                 HWPX 조립
│   ├── fix_namespaces.py             ⚠️ 필수 후처리 (빠뜨리면 한글에서 안 열림)
│   └── validate.py                   구조 검증
├── templates/
│   ├── government/header.xml         관공서 charPr/paraPr/borderFill 정의
│   ├── format_1p/                    1p 보고서 참조 (사용자 hwpx 넣을 위치)
│   ├── format_full/                  풀버전 보고서 참조
│   ├── format_gongmun/                시행문 참조
│   └── format_email/                  이메일 (참조 불필요)
└── references/
    ├── writing-principles.md         ★ 보고서 작성 원칙 (강의자료 + 사례 통합)
    ├── layout-rules.md               ★ 레이아웃 최적화 규칙
    ├── format-selection.md           양식 선택 결정트리
    ├── format-1p.md                  1p 보고서 가이드
    ├── format-full.md                풀버전 보고서 가이드
    ├── format-gongmun.md             시행문 가이드
    └── format-email.md               이메일 가이드
```

---

## ★ 4단계 워크플로우 (반드시 이 순서로 진행)

### ① 콘텐츠 기초데이터 정리

사용자 요청을 AI가 이해하기 쉬운 구조로 정돈한다.

- 입력 파일(.md/.docx/.pdf/.txt)을 `content_mapper.parse_input()` 으로 파싱
- 또는 사용자 메시지에서 핵심 정보(제목 후보·배경·현황·해결안·일정·예산 등)를 추출
- 마크다운 헤딩(`#`, `##`)을 섹션 구조로 변환

### ② 작성목적 및 서식 결정

**Claude는 반드시 이 순서로 양식을 결정한다.**

#### 2-1. 사용자에게 참조 hwpx/hwtx 파일이 있는지 먼저 묻는다

```
사용자에게 줄 메시지 (예시):
"보고서 양식을 결정하기 전에, 회사·부서에서 평소에 쓰는
참조용 .hwpx 또는 .hwtx 파일이 있으신가요?

(있으면 그 서식을 그대로 적용하고, 없으면 공공기관 표준에
가까운 무채색·중립 스타일로 작성하겠습니다.)"
```

- **있다고 답하면** → 사용자가 업로드한 파일 경로를 받아 `--reference` 인자로 전달
  - `kordoc:detect_format` 으로 포맷 검증
  - 빈칸·플레이스홀더가 있으면 `kordoc:fill_form` 활용도 가능
  - 없으면 `hwpx_helpers.extract_secpr_and_colpr` 로 서식 추출
- **없다고 답하면** → 다음 단계로 (스킬 내장 기본 양식 사용)

#### 2-2. 4개 양식 중 자동 추천 + 최종 확인

`compose_doc.pick_format()` 이 콘텐츠를 분석해 양식을 자동 추천한다.

| 양식 | 분량 | 독자 | 출력 |
|------|------|------|------|
| `format_1p` | A4 1쪽 강제 | 의사결정자 | .hwpx |
| `format_full` | A4 5–30쪽 (표지+목차+요약+본문) | 상급자·관계부서 | .hwpx |
| `format_gongmun` | A4 1–3쪽 (수신·제목·본문·발신) | 외부기관·일반국민 | .hwpx |
| `format_email` | 200–500자 | 협업자 | **.md/.txt 텍스트** (메일 복붙용) |

자세한 결정 트리는 `references/format-selection.md` 참조.

추천 결과를 사용자에게 1줄로 알리고 확인받는다:

```
"콘텐츠를 보니 1페이지 보고서가 적합해 보입니다.
이대로 진행할까요? (다른 양식: 풀버전 / 시행문 / 이메일)"
```

### ③ 지정 용도의 서식에 맞춰 콘텐츠 텍스트 수정

`compose_doc.map_to_format()` 가 양식별 필수 항목에 자동 매핑한다.

- 1p 보고서 → 부제·제목·작성자·요약문·□섹션 으로 매핑
- 풀버전 → 표지·목차·요약페이지·본문 chapters 로 매핑
- 시행문 → 수신·제목·본문(서술식+개조식)·붙임·발신명의·메타데이터로 매핑
- 이메일 → 제목·받는사람·결론·□섹션·서명 으로 매핑

**필수항목 누락 시** `_missing` 리스트에 담아 `※ AI 보완 필요` 플래그를 붙인다.

### ④ 레이아웃 최적화 편집 (★ 가장 차별화된 부분)

`layout_optimizer.optimize()` 가 다음을 자동 적용한다.

#### 4-1. 자동 적용 (신뢰도 높음)
- `~와 관련된` → `~ 관련`
- `~할 예정이었으나 이를 유예하였습니다` → `~ 예정 → 유예`
- `여러/많은/각/모든/수많은/대부분의/다양한 ~들` → 동일 단어에서 `들` 제거

#### 4-2. 검토 권장 표시 (사용자 확인용)
- `~할 것으로 보입니다` → `~ 예상 / ~ 전망`
- `~한 것으로 판단됩니다` → `~ 판단 / ~로 보임`
- `~하는 것이 필요합니다` → `~가 필요합니다`
- `~에 대한`, `~ 중 하나인`, `~의 ~의 ~` (의 연쇄)
- `사회적/경제적/정치적/행정적/조직적/기술적/사업적/업무적/제도적` + 명사
- 한 문장 46자 초과 (분리 후보)

#### 4-3. 페이지 걸침 점검
- 양식별 페이지당 라인 수 추정(`format_1p` = 38줄)
- 1p 보고서가 1쪽 초과하면 빌드 거부 + 압축 또는 양식 변경 권고
- 시행문이 1쪽 초과하면 별첨 분리 권고

#### 4-4. 글머리 위계 일관성
- 양식별 권장 체계 (1p·이메일=A 체계 □○-*, 풀버전·시행문=B 체계 1.가.(1))
- 두 체계 혼용 시 경고

전체 작성 원칙은 `references/writing-principles.md`, 자동 적용 규칙은 `references/layout-rules.md` 에 정리되어 있다.

---

## 가장 빠른 실행 (one-shot)

```bash
cd <skill_dir>

# (참조 파일 있을 때)
python3 scripts/compose_doc.py input.md output.hwpx \
  --format format_1p \
  --reference user_reference.hwpx \
  --meta meta.json \
  --report-path /tmp/optimization_report.md

# (참조 파일 없을 때 - 무채색 중립 스타일 폴백)
python3 scripts/compose_doc.py input.md output.hwpx \
  --format format_1p \
  --meta meta.json \
  --report-path /tmp/optimization_report.md
```

`meta.json` 예시 (1p 보고서):
```json
{
  "subtitle": "- ○○공사와 중소기업 상생협력을 위한 -",
  "author": "○○○처장 ○○○",
  "date": "'25.11.",
  "phone": "4315"
}
```

이 명령 한 줄이 4단계를 모두 실행한다. 결과:
- `output.hwpx` — 한글에서 바로 열리는 문서
- `/tmp/optimization_report.md` — 자동 적용·검토 권장 사항 리포트

---

## 양식별 빠른 가이드

자세한 내용은 각 references 파일 참조. 여기서는 핵심만.

### format_1p (1페이지 보고서)
- 구성: 부제 → 제목 → 음영 박스(요약) → □ 대제목(3–4개) → ○ 본문 → - 세부
- 분량: 1쪽 강제 (38줄 이내)
- 우수예시: `○○기관 협력사업 실무협의 보고`, `신규 사업 제휴 검토결과 보고`
- 가이드: `references/format-1p.md`

### format_full (풀버전 보고서)
- 구성: 표지 → 목차 → 보고내용 요약(1쪽) → 본문(Ⅰ.1.가.(1)(가)) → 별첨
- 분량: 5–30쪽
- 우수예시: `스마트 편의점 개발 추진계획`(2020.7., 25p)
- 가이드: `references/format-full.md`

### format_gongmun (시행문)
- 구성: 발신기관 → 수신·경유·제목 → 본문(서술식+개조식) → 붙임 → 발신명의 → 메타데이터
- 분량: 1–3쪽 (1쪽이 표준)
- 글머리: 반드시 1. → 가. → 1) → 가) → (1) → (가) → ① → ㉮
- 결문: `~하기 바랍니다`, `~하여 주시기 바랍니다`
- 가이드: `references/format-gongmun.md`

### format_email (이메일 — 텍스트 출력)
- 구성: 제목 → 받는사람·참조 → 인사 → 결론(두괄식) → □ 섹션 → 마무리 → 서명
- 분량: 본문 200–500자
- 출력: **.md 또는 .txt** (HWPX 빌드 안 함, 메일 본문 복붙용)
- 가이드: `references/format-email.md`

---

## 작성 원칙 (writing-principles.md 요약)

> 자세한 내용은 `references/writing-principles.md` 를 읽을 것.

**핵심 5원칙**:
1. **두괄식** — 결론·요약을 첫 3줄 안에. 1p 보고서는 음영 박스로 압축.
2. **개조식** — 키워드 중심, 글머리·번호로 짧게 끊기. 서술식은 시행문 본문 도입부에서만.
3. **한 문장 한 핵심** — 한 문장에 두 개 정보 = 분리. 한 문장이 한 줄(약 40자) 초과 = 분리.
4. **명사형 제목** — `~와 관련된 ~` → `~ 관련 ~` 또는 단순화.
5. **적의를 보이는 것들 4종 점검** — `-적`, `의`, `것`, `들`. 빼도 의미 유지되면 빼라.

---

## ⚠️ Critical Rules (반드시 준수)

| # | 규칙 | 위반 시 |
|---|------|---------|
| 1 | secPr 필수 (첫 문단 첫 run) | 한글에서 문서 안 열림 |
| 2 | `fix_namespaces.py` 필수 (모든 빌드 후) | 빈 페이지 표시 |
| 3 | `mimetype` = `ZIP_STORED` | 손상된 파일 |
| 4 | XML 이스케이프 (`< > & "`) | XML 파싱 오류 |
| 5 | ID 고유성 (모든 문단 id 정수) | 렌더링 오류 |
| 6 | 템플릿 ID 비혼용 (government charPr를 다른 템플릿에 사용 금지) | 서식 깨짐 |
| 7 | 1p 양식 분량 초과 시 빌드 거부 | 페이지 걸침 |
| 8 | 사용자에게 참조 파일 여부 먼저 질문 | 양식 미스매치 |

위 1–6은 기존 v2 의 규칙 그대로, 7–8은 v3 추가 규칙.

---

## 참조 파일이 있을 때 워크플로우 (kordoc 활용)

사용자가 hwpx/hwtx 참조 파일을 주면:

```python
# 1단계: 포맷 검증 (kordoc MCP 도구 사용)
# kordoc:detect_format → 'hwpx' 확인

# 2단계: 빈칸·플레이스홀더 점검
# kordoc:parse_document 로 마크다운 변환 후 {{제목}} 같은 패턴 탐지

# 3-A: 빈칸이 있으면 (양식형) → 워크플로우 B (템플릿 치환)
zip_replace('reference.hwpx', 'output.hwpx', {
    '{{제목}}': '...', '{{날짜}}': '...', '{{부서}}': '...'
})
subprocess.run(['python3', 'scripts/fix_namespaces.py', 'output.hwpx'])

# 3-B: 빈칸이 없으면 (서식 추출형) → secPr/colPr 추출 후 격납
secpr, colpr = extract_secpr_and_colpr('reference.hwpx')
# compose_doc.compose() 의 reference_hwpx 인자로 그대로 넘기면 됨
```

---

## 문제 발생 시 자가 진단

| 증상 | 원인 | 해결 |
|------|------|------|
| 한글에서 "문서가 손상되었습니다" | secPr 누락 또는 fix_namespaces 누락 | `make_first_para` 호출 + `fix_namespaces.py` 실행 |
| 빈 페이지로 표시 | fix_namespaces 누락 | 빌드 후 즉시 실행 |
| 1p인데 2쪽 됨 | 콘텐츠 초과 | optimization 리포트 보고 압축 또는 풀버전 변경 |
| 서식이 깨짐 | 템플릿 ID 혼용 | 한 문서 = 한 템플릿만 |
| 한글 깨짐 | XML 이스케이프 누락 | `xml_escape()` 호출 확인 |
| 글꼴이 다름 | 환경에 함초롬 없음 | 한글 환경에서 열거나 맑은 고딕으로 폴백 |

---

## Platform Notes

### Claude (이 스킬) — 권장 호출 패턴

```python
# Claude 가 사용자와 대화 중일 때:
# 1. 콘텐츠 정리 (대화 기반 또는 파일 입력)
# 2. 사용자에게 참조 hwpx 여부 질문
# 3. 양식 추천 + 확인
# 4. compose_doc.py 한 번 실행
# 5. 결과 .hwpx 와 optimization 리포트를 사용자에게 제시
```

### Cursor / Codex (.cursor/rules)
```
description: "HWPX 작성 시 public-doc-to-hwpx v3 사용"
globs: ["*.hwpx", "*.md", "*.docx"]
---
1. SKILL.md 의 4단계 워크플로우를 따른다
2. compose_doc.py 한 번으로 끝나면 그것만 사용
3. ALWAYS run fix_namespaces.py after build (compose_doc 가 이미 호출함)
4. layout_optimizer 의 검토 권장 사항을 사용자에게 항상 표시
5. 1p 양식 1쪽 초과 시 풀버전 변경 권고 (자동 변경 금지)
```

### n8n / Cowork
```
트리거: 파일 업로드 또는 텍스트 입력
노드1: Python 실행 → compose_doc.py
노드2: 결과 .hwpx + 리포트 .md 다운로드
노드3: 슬랙/메일 발송
```

---

## 변경 이력 (Changelog)

| 날짜 | 버전 | 변경사항 |
|------|------|----------|
| 2026-04-05 | 1.0.0 | 최초 생성 (python-hwpx 직접 API) |
| 2026-04-05 | 2.0.0 | jkf87/hwpx-skill 구조 흡수, fix_namespaces 추가, 5개 워크플로우 분기 |
| 2026-05-05 | **3.0.0** | **글쓰기 품질 강화** — 공공기관 보고서 작성 강의자료 + 공공기관 우수예시 학습. 4단계 워크플로우 (콘텐츠 정리 → 양식 결정 → 매핑 → 레이아웃 최적화) 도입. 4개 양식 빌더 (1p/full/gongmun/email) 분리. layout_optimizer.py 신규 (적/의/것/들, 한 문장 한 줄, 페이지 걸침 점검). compose_doc.py 통합 파이프라인. 사용자 참조 hwpx 우선 워크플로우. references/ 6개 가이드 추가. |
| 2026-05-06 | **3.0.1** | **한글 호환성 핫픽스** — v3.0.0 빌드 산출물이 한글에서 "파일 손상" 메시지로 거부되던 문제 해결. 원인은 build_hwpx.py가 만들어낸 메타파일 6개(container.xml media-type, manifest/version/settings 네임스페이스, content.hpf href 경로, container.rdf·Preview/* 누락)가 한컴 표준에서 벗어난 것. python-hwpx 라이브러리의 검증된 Skeleton.hwpx를 베이스로 사용하도록 build_hwpx.py 전면 재작성. format_builders.py의 make_horizontal_rule paraPrIDRef="20" 오류 정정 (header 정의 범위 0~19). templates/_skeleton.hwpx 신규 동봉. |
