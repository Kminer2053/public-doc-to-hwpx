---
name: public-doc-to-hwpx
description: "AI가 생성한 콘텐츠를 공공기관 표준 보고서로 다듬어 HWPX 또는 메일 본문으로 변환하는 스킬. 보고서 작성 원칙(개조식 문체·한 문장 한 줄·적/의/것/들 정리·두괄식 요약)을 자동 적용하여 의사결정자가 30초 안에 읽고 5분 안에 판단할 수 있는 가독성 높은 문서를 만든다. 4개 양식(1페이지 보고서/풀버전 보고서/시행문/이메일)을 지원하며, 1p·풀버전·시행문 세 양식은 내장 표준 hwpx 의 빈 골격(skeleton)에 콘텐츠만 채우는 방식으로 빌드되어 양식의 표·테두리·음영·페이지헤더 등 시각 디자인이 100% 보존된다. 사용자가 참조 hwpx 파일을 주면 그 양식을 우선 적용하며, 내용·구성까지 반영할지 추가로 묻는다. 트리거: hwpx, HWP, 한글파일, 한글로 작성, 공문, 시행문, 보고서, 1페이지 보고서, 1p 보고, 기획서, 검토보고서, 추진계획, 결과보고, 검토결과, 공공기관 문서, 메일 작성, 이메일 본문, 회신 요청, 보고드림"
allowed-tools: "Bash(python3*), Read, Write, Glob"
---

# 공공기관 보고서 작성 + HWPX 변환 스킬 (v3.6.10)

> **이 스킬의 목표**: AI가 없던 시절 한글(hwp)을 쓰던 베테랑 보고서 작성자가 만든 것처럼,
> 독자 입장에서 가독성이 높고 핵심이 빠르게 읽히는 공공기관 보고서를 자동 생성한다.

---

## 디렉토리 구조

```
public-doc-to-hwpx/
├── SKILL.md                          ← 이 파일 (4단계 워크플로우)
├── scripts/                          ★ v3.5.0 — 4대 함정 자동 검사 + 통합 빌드
│   ├── make_skeleton.py              양식 hwpx → 빈 골격 변환 (새 양식 등록 시)
│   ├── fill_skeleton.py              메인 빌더 — 빈 골격 토큰을 값으로 치환
│   ├── fix_namespaces.py             ⚠️ 필수 후처리 (빠뜨리면 한글에서 안 열림)
│   ├── simulate_pages.py             ★ v3.5.0 갱신 — --values + --apply-to-values
│   ├── ensure_body_anchor.py         본문 시작 pageBreak="1" 강제 (풀버전)
│   ├── wrap_long_titles.py           ★ v3.6.0/3.6.4 — 표지 큰 제목 자간 압축 자동 해소
│   ├── fix_toc_dots.py               ★ v3.6.1/3.6.2/3.6.5 — 목차 점선 width 42000 통일 + lineseg 캐시 제거
│   ├── fix_gongmun_body.py           ★ v3.6.3 — 공문 본문 단락 자간 압축 자동 해소
│   ├── split_gongmun_paragraphs.py   ★ v3.6.4/3.6.6 — placeholder 강제 분리 (현재 비활성)
│   ├── fix_skeleton_defects.py       ★ v3.6.6/3.6.10 — Skeleton 양식 결함 자동 보정 (Ⅳ장 들여쓰기 + 수신자 라벨/입력 분리)
│   ├── expand_gongmun_body.py        ★ v3.6.7/3.6.8/3.6.9/3.6.10 — 공문 본문 모든 위계 동적 확장 + 빈 단락 제거 + 들여쓰기 통일
│   ├── build_full.py                 ★ v3.5.0 — 풀버전 통합 빌드 워크플로우
│   └── validate.py                   구조 검증
├── templates/
│   ├── _skeleton.hwpx                폴백 베이스
│   ├── charpr_mapping.json           양식별 charPr 역할 → id 매핑표
│   ├── government/header.xml         관공서 charPr/paraPr/borderFill 정의
│   ├── format_1p/
│   │   ├── standard.hwpx             1p 보고서 표준 양식 (맑은 고딕)
│   │   ├── skeleton.hwpx             ★ 빈 골격 (35개 토큰)
│   │   ├── skeleton_mapping.json     ★ 토큰 ↔ 원본 매핑표
│   │   └── outline_guide.md          ★ v3.3.1 보고 목적별 11가지 표준 목차 가이드
│   ├── format_full/
│   │   ├── standard.hwpx             풀버전 보고서 표준 양식 (맑은 고딕, 표 10개)
│   │   ├── skeleton.hwpx             ★ 빈 골격 (127개 토큰 — 페이지번호 포함)
│   │   └── skeleton_mapping.json     ★ 토큰 ↔ 원본 매핑표
│   ├── format_gongmun/
│   │   ├── standard.hwpx             시행문 표준 양식 (굴림체, 표 셀 66개)
│   │   ├── skeleton.hwpx             ★ 빈 골격 (27개 토큰 — fwSpace 포함)
│   │   └── skeleton_mapping.json     ★ 토큰 ↔ 원본 매핑표
│   └── format_email/                 이메일 (텍스트 출력이라 골격 불필요)
└── references/
    ├── writing-principles.md         ★ 보고서 작성 원칙 (강의자료 + 사례 통합)
    ├── layout-rules.md               ★ 레이아웃 최적화 규칙
    ├── format-selection.md           양식 선택 결정트리
    ├── format-1p.md                  1p 보고서 가이드
    ├── format-full.md                풀버전 보고서 가이드
    ├── format-gongmun.md             시행문 가이드
    └── format-email.md               이메일 가이드

examples/                             ★ v3.6.10 — values.json 예시
├── example_values_gongmun.json       시행문 예시 (모든 위계 활용)
└── example_values_full.json          풀버전 보고서 예시 (127슬롯)
```

> **v3.4.0 변경**: v3.3.x 까지의 "모드 1 (자동 빌드, `compose_doc.py`)" 는 양식 시각 디자인을 보존하지 못해 deprecated 되었고, v3.4.0 부터는 **빈 골격 채우기 단일 워크플로우** 만 지원합니다. 관련 스크립트(`compose_doc.py`, `layout_optimizer.py`, `format_builders.py`, `content_mapper.py`, `build_hwpx.py`, `hwpx_helpers.py`) 는 모두 제거되었습니다.

---

## ★ 4단계 워크플로우 (반드시 이 순서로 진행)

### ① 콘텐츠 기초데이터 정리

사용자 요청을 AI가 이해하기 쉬운 구조로 정돈한다.

- Claude가 사용자 메시지 또는 입력 파일(.md/.docx/.pdf/.txt)에서 핵심 정보(제목 후보·배경·현황·해결안·일정·예산 등) 를 직접 추출
- 마크다운 헤딩(`#`, `##`)을 섹션 구조로 변환
- 필요 시 `kordoc` MCP 도구로 입력 파일 파싱 가능

### ② 작성목적 및 서식 결정

**Claude는 반드시 이 순서로 양식을 결정한다.**

#### 2-1. 사용자에게 참조 HWPX 파일이 있는지 먼저 묻는다

```
사용자에게 줄 메시지 (예시):
"보고서 양식을 결정하기 전에 한 가지 확인할게요.
이번에 따로 참고하실 .hwpx 파일이 있으신가요?

(없으셔도 됩니다. 1p 보고서·풀버전 보고서·시행문 모두 회사 표준
서식이 내장되어 있어 폰트·서식이 그대로 적용됩니다.)"
```

> ⚠️ HWTX 형식은 묻지 않는다. 내부적으로 어차피 HWPX 로 변환되므로,
> 사용자가 HWTX 를 가지고 있더라도 HWPX 로 저장해서 줄 것을 안내한다.

**참조 파일이 있다고 답하면** → 사용자 파일 경로 수령 후 **추가 질문** 한 번 더:

```
사용자에게 줄 추가 질문 (예시):
"이 참조 파일을 어떻게 활용할까요?
  ① 서식만 적용 (폰트·문단·테두리 등) - 기본 권장
  ② 서식 + 내용·섹션 구성도 반영 (참조파일의 챕터/소제목 구조를 따라 콘텐츠를 재정렬)"
```

- **① 서식만** → 사용자 hwpx 를 `make_skeleton.py` 로 빈 골격(skeleton.hwpx) 으로 변환한 후, 그 골격에 콘텐츠를 매핑·빌드.
  양식의 폰트·charPr·표·테두리·페이지헤더가 모두 보존됨.
- **② 서식+내용** → 위와 동일하게 빈 골격을 만들되, 참조파일의 섹션 헤딩·소제목·문구 패턴을 학습하여
  사용자 콘텐츠를 그 구조에 맞춰 재정렬한 후 매핑.
  (예: 참조가 "추진배경 → 현황 → 개선안 → 일정" 구조라면 사용자 콘텐츠도 그 4단으로 매핑)

**참조 파일이 없다고 답하면** → 별도 인자 없이 진행.
양식이 결정되는 즉시 해당 `templates/<format>/standard.hwpx` 가
자동으로 빌드 베이스가 된다.

> 💡 **내장 표준 서식의 효과**: 한 번 양식이 결정되면 그 양식의 폰트(맑은 고딕/굴림체 등),
> 글자속성 21~74개, 문단속성, 테두리채움 정의가 모두 보존된다. 즉 결과 hwpx 를
> 한글에서 열면 사용자가 정리해 둔 회사 표준 서식이 그대로 보인다.

#### 2-2. 4개 양식 중 자동 추천 + 최종 확인

Claude 가 콘텐츠 분량·청자·목적을 분석해 양식을 자동 추천한다.

| 양식 | 분량 | 독자 | 출력 | 베이스 (내장) |
|------|------|------|------|--------------|
| `format_1p` | A4 1쪽 강제 | 의사결정자 | .hwpx | 맑은 고딕, charPr 21개 |
| `format_full` | A4 5–30쪽 (표지+목차+요약+본문) | 상급자·관계부서 | .hwpx | 맑은 고딕, charPr 74개 |
| `format_gongmun` | A4 1–3쪽 (수신·제목·본문·발신) | 외부기관·일반국민 | .hwpx | 굴림체, charPr 28개 |
| `format_email` | 200–500자 | 협업자 | **.md/.txt 텍스트** | (텍스트 출력이라 베이스 불필요) |

자세한 결정 트리는 `references/format-selection.md` 참조.

추천 결과를 사용자에게 1줄로 알리고 확인받는다:

```
"콘텐츠를 보니 1페이지 보고서가 적합해 보입니다.
이대로 진행할까요? (다른 양식: 풀버전 / 시행문 / 이메일)"
```

### ③ 지정 용도의 서식에 맞춰 콘텐츠 텍스트 수정

Claude 가 양식의 `skeleton_mapping.json` 을 참조하여 사용자 콘텐츠를 양식 슬롯에 매핑한다.

- 1p 보고서 → 부제·제목·작성자·요약문·□ 섹션(4개) 슬롯에 매핑
- 풀버전 → 표지·목차·요약페이지·본문 chapters(127 슬롯) 에 매핑
- 시행문 → 수신·제목·본문(서술식+개조식)·붙임·발신명의 슬롯(27개) 에 매핑
  - **본문-메타 분리 원칙**: 수신자·발신자·결재선·시행번호·날짜·전화 같은 메타 정보는 빈 값으로 두고 한글에서 직접 채울 자리로 남김
- 이메일 → 제목·받는사람·결론·□ 섹션·서명 (텍스트 출력)

**필수항목 누락 시** Claude 가 사용자에게 알리고 추가 정보를 요청한다.

**마커 일관성 원칙**: 양식 원본 텍스트(`skeleton_mapping.json` 의 `original_text`) 의 마커 패턴(◦, -, * 등) 을 그대로 따라 값을 채운다. 원본에 ◦ 가 있으면 우리 값에도 ◦ 를 직접 적고, 원본에 마커가 없으면 (paraPr 자동 들여쓰기) 마커 없이 텍스트만 넣는다.

### ④ 레이아웃 최적화 편집 (★ 가장 차별화된 부분)

Claude 가 슬롯에 값을 매핑하기 *전*에 다음을 직접 적용한다 (참고: `references/layout-rules.md`).

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

## 표준 빌드 워크플로우 (v3.4.0)

v3.4.0 부터는 **빈 골격 채우기 단일 워크플로우** 만 지원한다. v3.3.x 까지 존재하던 자동 빌드 모드(`compose_doc.py`) 는 양식 시각 디자인을 보존하지 못해 deprecated 되었다.

### 작동 원리
양식 hwpx 를 사전에 빈 골격(`skeleton.hwpx`) 으로 변환해 두고, 빌드 시 토큰 자리에 콘텐츠를 채워 넣는다.

- ✅ **양식의 표·테두리·음영·페이지헤더 등 모든 시각 구조 100% 보존**
- ✅ 한글에서 열었을 때 양식 파일과 시각적으로 거의 동일한 결과
- ✅ 콘텐츠와 양식 디자인이 완전히 분리되어 양식만 교체하는 작업도 단순

### 표준 명령 시퀀스

#### 풀버전 보고서 (권장: v3.5.0 통합 빌더)

```bash
cd <skill_dir>

# 한 줄로 4대 함정 검사 + 페이지번호 자동 매핑 + 후처리까지 완료
python3 scripts/build_full.py \
  --values my_values.json \
  --output result.hwpx
# 옵션: --strict (위반 발견 시 빌드 중단)
```

`build_full.py` 가 자동 수행하는 작업:
1. **입력 검사** — 목차 슬롯 위계, 빈 슬롯 비율, 본문 마커 중복 점검
2. **1차 빌드** (페이지번호 임시값)
3. **페이지 시뮬레이션** + values 자동 갱신
4. **2차 빌드** (페이지번호 반영된 최종본)
5. **후처리** (fix_namespaces + ensure_body_anchor + **wrap_long_titles** + **fix_toc_dots** + validate)
   - v3.6.0 `wrap_long_titles`: 표지 큰 제목이 14자 초과 시 자동으로 2단락 분리
   - v3.6.1/3.6.2/3.6.5 `fix_toc_dots`: 목차 점선(`<hp:tab leader="3"/>`) width 를 42000 으로 통일 +
     점선이 든 단락의 `<hp:linesegarray>` 캐시 제거하여 한글2018 이 폰트 메트릭으로 재계산하도록 위임
   - 한글2018·한컴뷰어 양 환경에서 표지 제목·목차 점선이 동일하게 렌더링됨

#### 1p 보고서·시행문 (기존 방식)

```bash
# 단계 ① 매핑 JSON 확인 → 슬롯이 몇 개 있고 어떤 의미인지 파악
cat templates/format_1p/skeleton_mapping.json

# 단계 ② 콘텐츠를 양식 슬롯에 맞게 매핑한 values.json 작성

# 단계 ③ 빈 골격에 값 채우기
python3 scripts/fill_skeleton.py \
  --skeleton templates/format_1p/skeleton.hwpx \
  --values my_values.json \
  --output result.hwpx

# 단계 ④ 후처리 + 검증
python3 scripts/fix_namespaces.py result.hwpx
python3 scripts/fix_gongmun_body.py result.hwpx   # ★ v3.6.3 (시행문만 — 본문 자간 압축 해소)
python3 scripts/validate.py result.hwpx
```

> 💡 **v3.6.3 권장**: 시행문(공문) 빌드 시 `fix_gongmun_body.py` 후처리를 항상 실행합니다.
> 공문 양식 본문 단락은 단일 lineseg(`horzsize=49108`) 로 저장되어 한글2018 의 자간 압축
> 동작을 유발하므로, 이 후처리가 단일 lineseg 단락의 linesegarray 를 제거하여 한글이
> 폰트 메트릭으로 자동 재계산하도록 위임합니다.
>
> 1p 보고서는 본문 셀 구조가 다르므로 영향 없음 (호출해도 매칭 0건으로 무영향).

#### 풀버전 보고서 (구식 — 수동 분리 모드, 권장하지 않음)

```bash
python3 scripts/fill_skeleton.py --skeleton templates/format_full/skeleton.hwpx --values my_values.json --output result.hwpx
python3 scripts/fix_namespaces.py result.hwpx
python3 scripts/simulate_pages.py result.hwpx --mapping templates/format_full/skeleton_mapping.json --values my_values.json --apply-to-values
python3 scripts/fill_skeleton.py --skeleton templates/format_full/skeleton.hwpx --values my_values.json --output result.hwpx
python3 scripts/fix_namespaces.py result.hwpx
python3 scripts/ensure_body_anchor.py result.hwpx
python3 scripts/validate.py result.hwpx
```

### values.json 예시 (풀버전 보고서)

```json
{
  "표지_제목": "전사적 AI역량 강화 추진계획",
  "표지_부제": "- AX 시대 인적자원 혁신을 위한 -",
  "보고일": "2026. 5. 11.",
  "기관명": "○○공사",
  "본부부서명": "AI혁신처",
  "장01_제목": " 추진배경 및 필요성",
  "본문_절_001": " □ AX 시대 도래로 전사적 AI 리터러시 확보 필수",
  "본문_항목_001": " 글로벌 기업 89% 이상이 AI 도입을 이미 진행 중",
  "본문_세부_001": "   - 4조 4천억 달러 규모 생산성 향상 잠재력 보유",
  "본문_주석_001": "       ※ 단, 성숙 단계 기업은 1~6%에 불과"
}
```

### 새 양식을 빈 골격으로 만들 때

```bash
# 사용자가 templates/format_<name>/standard.hwpx 를 두면
python3 scripts/make_skeleton.py templates/format_<name>/standard.hwpx
# → templates/format_<name>/skeleton.hwpx + skeleton_mapping.json 자동 생성
```

---

## 양식별 빠른 가이드

자세한 내용은 각 references 파일 참조. 여기서는 핵심만.

### format_1p (1페이지 보고서)
- 구성: 부제 → 제목 → 음영 박스(요약) → □ 대제목(3–4개) → ○ 본문 → - 세부
- 분량: 1쪽 강제 (38줄 이내)
- 우수예시: `○○기관 협력사업 실무협의 보고`, `신규 사업 제휴 검토결과 보고`
- 가이드: `references/format-1p.md` (양식 일반 가이드)
- **목차 구성 가이드**: `templates/format_1p/outline_guide.md` (v3.3.1 신규)
  - 보고 목적별 11가지 유형의 표준 목차 (현황·동향 / 검토·의사결정 / 계획 / 문제해결 / 이슈·리스크 / 결과·성과 / 회의 안건 / 회의 결과 / 행사 / 제휴·협력 / 예산·구매)
  - 4절 기본형 / 5절 확장형 / 3절 압축형 골격
  - 양식의 4섹션 슬롯(text_004~023) 과 목차 절의 대응표
  - 1페이지 보고서 빌드 시 **목차를 먼저 이 가이드에서 선택한 후** 슬롯에 매핑하는 것이 표준 워크플로우

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
| 6 | 템플릿 ID 비혼용 (서로 다른 양식의 charPr id 를 혼용 금지) | 서식 깨짐 |
| 7 | 1p 양식 분량 초과 시 빌드 거부 | 페이지 걸침 |
| 8 | 사용자에게 참조 파일 여부 먼저 질문 (HWPX 만; HWTX 는 묻지 말 것) | 양식 미스매치 |
| 9 | 참조 파일 있을 때 "서식만 vs 서식+내용 반영" 추가 질문 | 사용자 의도 미반영 |
| 10 | charPr id 는 매핑표(`templates/charpr_mapping.json`)를 통해 조회 | 폰트/스타일 불일치 |
| 11 | 양식 시각 디자인(표·테두리·음영) 일치가 중요하면 빈 골격 모드 사용 (자동 빌드 모드는 단락만 생성하여 표 등이 사라짐) | 양식과 시각적으로 큰 차이 |
| 12 | **풀버전 빌드 시 `build_full.py` 사용 권장 (v3.5.0)** — 수동 다단계 빌드는 페이지번호 누락 위험 | 페이지번호 미반영 |
| 13 | **풀버전 목차 슬롯 위계 준수** — `목차_항목_001/003/013/021/033/043` 에만 Ⅰ~Ⅵ 대제목 매핑 | 목차 서식 깨짐 |
| 14 | **풀버전 본문_항목 마커 구분** — `001~009` 는 자동 ○ (◦ 직접 금지) / `010~012` 는 ◦ 직접 표기 | 마커 중복 표시 |
| 15 | **풀버전 콘텐츠는 양식 슬롯 수에 맞춰 확장** — Ⅱ장 소제목 4 / Ⅲ장 3 / Ⅳ장 5 / Ⅴ장 4 / Ⅵ장 4 | 점선·페이지번호 정렬 무너짐 |
| 16 | **풀버전 표지 제목은 결재제목 셀에서 한 줄 임계 초과 시 자동 줄바꿈** (v3.6.0 후처리 `wrap_long_titles.py` 가 처리) — 14자 초과 시 공백 위치에서 단락 분리. 분리 안 되면 한글2018에서 자간 압축으로 글자 깨짐 | 표지 제목 가독성 급락 |
| 17 | **풀버전 목차 점선 width 통일** (v3.6.1 후처리 `fix_toc_dots.py` 가 처리) — 양식 원본 텍스트 기준으로 박힌 `<hp:tab width="..." leader="3"/>` 값을 단락 너비보다 약간 작은 값(42000)으로 통일. 통일 안 하면 한글2018 폰트 보유 환경에서 점선 끊김·페이지번호 누락 또는 점선이 너무 길어 페이지번호 wrap 발생 | 목차 점선·페이지번호 깨짐 |
| 18 | **공문 본문 단락 단일 lineseg 자동 정리** (v3.6.3 후처리 `fix_gongmun_body.py` 가 처리) — 공문 양식 본문 단락은 단일 `<hp:lineseg horzsize="49108"/>` 로 저장되어 한글2018 의 자간 압축을 유발. 후처리가 해당 linesegarray 를 제거해서 한글이 폰트 메트릭으로 자동 재계산하도록 위임 | 공문 본문(2번 이후) 자간 압축 깨짐 |
| 19 | **목차 점선 단락 lineseg 캐시 무효화** (v3.6.5 `fix_toc_dots.py` 단계 B) — width 통일만으로는 부족하며 점선이 든 모든 hp:p 의 `<hp:linesegarray>` 캐시도 제거해야 한글이 폰트 메트릭으로 점선 길이·페이지번호 위치를 정확히 재계산 | 목차 점선 끊김·페이지번호 누락 잔존 |
| 20 | **공문 양식 결함 자동 보정** (v3.6.6/3.6.10 `fix_skeleton_defects.py`) — ① 풀버전 Ⅳ장 들여쓰기 run 누락 자동 보충 (INDENT_FIXES) ② 공문 수신자 행: 라벨 셀에 "수신" 자동 부여 + 옆 빈 셀에 `{{수신자}}` placeholder 동적 삽입 (add_receiver_input_slot). 양식 빈 골격이 정적 라벨까지 placeholder 로 변환해 버린 결함을 빌더가 메모리에서 복구 | 수신자 라벨 사라짐 / Ⅳ장 들여쓰기 깨짐 |
| 21 | **공문 본문 모든 위계 동적 확장** (v3.6.7/3.6.8/3.6.9 `expand_gongmun_body.py`) — 양식 슬롯 수에 묶이지 않고 사용자 콘텐츠 양에 따라 7개 위계(`본문`, `본문_가나`, `본문_1)`, `본문_가)`, `본문_(1)`, `본문_①`, `붙임`) 자유 확장. 빈 placeholder 단락 자동 제거 (본문 영역 한정, hp:tbl 든 단락 보존). 양식 슬롯/동적 단락 들여쓰기 통일 (slot_indent + dynamic_indent + dynamic_indent_xml) | 단락 수 양식 슬롯 한계 / 빈 줄 잔존 |
| 22 | **본문_가나 동적 추가는 raw XML `<hp:fwSpace/>` 사용** (v3.6.10 `_build_p_block(indent_xml=)`) — 양식 슬롯의 `<hp:fwSpace/>` element 와 텍스트 전각공백(`\u3000`) 은 한글이 미세하게 다른 폰트 메트릭으로 렌더링. 동적 단락 hp:t 안에도 동일한 raw XML element 직접 삽입하여 시각 일치 보장 | 가/나/다 들여쓰기 미세 차이 |

위 1–6은 v2~v3.0.1 의 규칙 그대로, 7–8은 v3.0 추가, 9–10은 v3.1 추가, 11은 v3.2 신규 규칙, 12–15는 v3.5.0 신규 규칙, 16은 v3.6.0 신규 규칙, 17은 v3.6.1 신규 규칙, 18은 v3.6.3 신규 규칙, 19는 v3.6.5 신규 규칙, 20은 v3.6.6/3.6.10 신규 규칙, 21은 v3.6.7~3.6.9 신규 규칙, 22는 v3.6.10 신규 규칙.

---

## 참조 파일이 있을 때 워크플로우 (kordoc 활용)

사용자가 hwpx 참조 파일을 주면 (v3.4.0 기준 — 빈 골격 채우기 단일 방식):

```python
# 1단계: 포맷 검증 (kordoc MCP 도구 사용 — 사용 가능한 경우)
# kordoc:detect_format → 'hwpx' 확인

# 2단계: 빈칸·플레이스홀더 점검
# kordoc:parse_document 로 마크다운 변환 후 {{제목}} 같은 패턴 탐지

# 3-A: 빈칸이 있으면 (양식형) → 템플릿 치환 워크플로우
zip_replace('reference.hwpx', 'output.hwpx', {
    '{{제목}}': '...', '{{날짜}}': '...', '{{부서}}': '...'
})
subprocess.run(['python3', 'scripts/fix_namespaces.py', 'output.hwpx'])

# 3-B: 빈칸이 없으면 (서식 추출형) → 빈 골격으로 변환 후 콘텐츠 채우기
subprocess.run([
    'python3', 'scripts/make_skeleton.py',
    'reference.hwpx',                          # 사용자 양식
    '--output-dir', 'templates/format_user/',  # 빈 골격 + 매핑표 생성
])
# 그 다음 표준 빌드 워크플로우 적용 (fill_skeleton → fix_namespaces → validate)
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
| 폰트가 양식과 다름 | `standard.hwpx` 또는 `skeleton.hwpx` 누락 | `templates/<format>/skeleton.hwpx` 존재 확인, 없으면 `make_skeleton.py` 로 생성 |
| 제목·강조가 본문과 같은 크기 (v3.1+) | charpr_mapping.json 누락 또는 양식 미등록 | `templates/charpr_mapping.json` 존재 확인, 해당 format_type 키 등록 여부 확인 |

---

## Platform Notes

### Claude (이 스킬) — 권장 호출 패턴

```python
# Claude 가 사용자와 대화 중일 때:
# 1. 콘텐츠 정리 (대화 기반 또는 파일 입력)
# 2. 사용자에게 참조 hwpx 여부 질문
# 3. 양식 추천 + 확인 (1p/full/gongmun/email)
# 4. skeleton_mapping.json 참조하여 values.json 작성
# 5. fill_skeleton.py → fix_namespaces.py → validate.py 실행
# 6. (풀버전만) simulate_pages.py → ensure_body_anchor.py 적용
# 7. 결과 .hwpx 를 사용자에게 제시
```

### Cursor / Codex (.cursor/rules)
```
description: "HWPX 작성 시 public-doc-to-hwpx v3.4 사용"
globs: ["*.hwpx", "*.md", "*.docx"]
---
1. SKILL.md 의 4단계 워크플로우를 따른다
2. 표준 빌드 워크플로우는 fill_skeleton → fix_namespaces → validate
3. ALWAYS run fix_namespaces.py after fill_skeleton.py
4. 1p 보고서는 outline_guide.md 의 11가지 유형 중 매칭되는 목차 선정
5. 1p 양식 1쪽 초과 시 풀버전 변경 권고 (자동 변경 금지)
```

### n8n / Cowork
```
트리거: 파일 업로드 또는 텍스트 입력
노드1: Python 실행 → fill_skeleton.py
노드2: Python 실행 → fix_namespaces.py + validate.py
노드3: 결과 .hwpx 다운로드
노드4: 슬랙/메일 발송
```

---

## 변경 이력 (Changelog)

| 날짜 | 버전 | 변경사항 |
|------|------|----------|
| 2026-04-05 | 1.0.0 | 최초 생성 (python-hwpx 직접 API) |
| 2026-04-05 | 2.0.0 | jkf87/hwpx-skill 구조 흡수, fix_namespaces 추가, 5개 워크플로우 분기 |
| 2026-05-05 | 3.0.0 | **글쓰기 품질 강화** — 공공기관 보고서 작성 강의자료 + 공공기관 우수예시 학습. 4단계 워크플로우 (콘텐츠 정리 → 양식 결정 → 매핑 → 레이아웃 최적화) 도입. 4개 양식 빌더 (1p/full/gongmun/email) 분리. layout_optimizer.py 신규 (적/의/것/들, 한 문장 한 줄, 페이지 걸침 점검). compose_doc.py 통합 파이프라인. 사용자 참조 hwpx 우선 워크플로우. references/ 6개 가이드 추가. |
| 2026-05-06 | 3.0.1 | **한글 호환성 핫픽스** — v3.0.0 빌드 산출물이 한글에서 "파일 손상" 메시지로 거부되던 문제 해결. python-hwpx 라이브러리의 검증된 Skeleton.hwpx 를 베이스로 사용하도록 build_hwpx.py 전면 재작성. format_builders.py 의 make_horizontal_rule paraPrIDRef 오류 정정. templates/_skeleton.hwpx 신규 동봉. |
| 2026-05-11 | 3.1.0 | **양식별 표준 hwpx 내장 + 폰트·charPr 100% 보존** — 1p / 풀버전 / 시행문 세 양식의 회사 표준 hwpx 를 `templates/format_*/standard.hwpx` 로 내장. `build_hwpx.py` 에 `--base-hwpx` 모드 추가 (베이스 hwpx 통째로 사용, header.xml 보존). `templates/charpr_mapping.json` 신규 — 양식별 charPr 역할 → id 매핑표 도입. `format_builders.py` 의 모든 빌더가 양식별 cp_map 을 받아 글자 스타일을 동적으로 선택. 결과: 사용자가 별도 참조 파일을 주지 않아도 양식의 폰트(맑은 고딕/굴림체)·글자속성 21~74개·문단속성·테두리채움이 결과 hwpx 에 그대로 적용. 워크플로우 2-1 갱신: HWTX 는 묻지 않고 HWPX 만 묻기, 참조파일 있을 때 "서식만 vs 서식+내용 반영" 추가 질문. 풀버전 양식의 이미지(image1.jpg, image2.WMF) 사전 제거. |
| 2026-05-11 | 3.2.0 | **빈 골격 채우기 모드 도입 — 양식의 시각 디자인 100% 보존** — v3.1 의 base_hwpx 모드는 header.xml(폰트·charPr 정의) 만 보존하고 section0.xml 은 단락 기반으로 새로 만들었기 때문에 양식의 **표·테두리·음영·페이지헤더 등 시각 디자인이 사라지는** 본질적 한계가 있었다(풀버전 양식의 표 10개와 테두리채움 91건 → 빌드 결과 0개와 3건으로 손실). v3.2 는 양식 hwpx 의 section0.xml 도 통째로 보존하면서 텍스트만 `{{토큰}}` placeholder 로 교체한 빈 골격(skeleton.hwpx) 을 사전 생성하고, 빌드 시 토큰만 채우는 워크플로우를 추가했다. 신규 스크립트: `make_skeleton.py` (양식 → 빈 골격 자동 변환, 라벨/마커/위계는 보존), `fill_skeleton.py` (placeholder → 값 치환). 3개 양식 모두 빈 골격 사전 생성 (1p 35슬롯, 시행문 23슬롯, 풀버전 75슬롯). 결과: 양식의 표 10·테두리채움 91·charPr 58종·paraPr 27종이 빌드 결과에 100% 그대로 보존됨. SKILL.md 에 두 가지 빌드 모드(자동 / 골격 채우기) 가이드 추가. |
| 2026-05-11 | 3.2.1 | **핫픽스: 자식 태그 포함 hp:t 처리 누락 해결 (목차 보존 문제)** — v3.2.0 의 make_skeleton.py 가 `<hp:t>` 안에 자식 태그(`<hp:tab/>`, `<hp:fwSpace/>` 등) 가 끼어있는 경우를 매칭하지 못해, 양식의 **목차 페이지·풀폭 공백 영역 텍스트가 토큰화되지 않고 양식 원본 그대로 결과에 남는 문제** 발생. 사용자가 풀버전 결과에서 양식의 목차("Ⅰ. 사업 개요 ··· 1") 가 자기 보고서 목차로 안 바뀌고 그대로 남아 있어서 발견. 원인은 `<hp:t>([^<]*)</hp:t>` 정규식이 자식 태그를 만나면 매칭 종료되는 데 있었음. 해결: 비탐욕·DOTALL 정규식으로 자식 태그 포함 hp:t 도 매칭하고, 자식 태그(점선 채움 `<hp:tab leader="3"/>` 등) 는 보존하면서 텍스트 노드만 분리해 `목차_항목_NNN` 같은 새 토큰 카테고리로 토큰화. 페이지 나눔 감지도 `pageBreak="1"` 뿐 아니라 `<hp:ctrl type="PAGE_BREAK"` 도 잡도록 보완. 결과 슬롯 수: 1p 35→35, 시행문 23→27 (`<hp:fwSpace/>` 처리), 풀버전 75→112 (목차 37 슬롯 추가). 풀버전의 점선 채움 효과(`hp:tab leader="3"`) 26개 모두 보존. |
| 2026-05-11 | 3.2.2 | **목차 페이지번호 일관 처리** — v3.2.1 까지는 `should_preserve()` 가 "1글자 이하 텍스트는 보존(라벨/마커로 판단)" 규칙을 가져서 1자리 페이지번호 ("1", "3", "5" 등) 가 토큰화되지 않고 양식 원본 값 그대로 남는 문제 발생. 결과적으로 같은 목차 안에서 1자리 페이지번호는 양식 그대로, 2자리 페이지번호("10", "11" 등) 는 사용자 매핑값으로 적용되어 페이지번호가 보고서 실제 구조와 불일치. 해결: `should_preserve()` 에 "1글자라도 숫자(0-9) 면 토큰화 대상" 룰을 추가. 결과: 풀버전 양식의 목차 페이지번호 26개 전체가 일관되게 토큰화되어 우리 보고서 페이지 구조에 맞게 자유롭게 설정 가능 (목차_항목 짝수번 슬롯 = 페이지번호). 풀버전 슬롯 수: 112 → 127. AI 보고서 빌드 결과 목차가 "Ⅰ. 추진배경 ··· 1 / Ⅱ. 추진목표 ··· 2 / ..." 식으로 자연스러운 페이지번호 흐름으로 출력됨. |
| 2026-05-12 | 3.3.0 | **페이지 시뮬레이터 + 목차 페이지번호 자동 산출** — 한글의 실제 페이지 분량을 파이썬 단독 시뮬레이션으로 산출하여 목차 페이지번호를 자동 매핑하는 워크플로우 도입. 본질적으로 한국어 워드 프로세서의 페이지 레이아웃 엔진을 100% 재현하는 것은 어렵지만, 공공기관 보고서의 구조적 균일성을 활용하면 단순 카운트로도 정확도 100% 달성 가능함이 검증됨. 알고리즘 v4 (Simple Default): (1) 표지=1쪽 고정, (2) 목차=`ceil(항목수/30)` 쪽 — 양식 원본 30줄/쪽 실측 기반, (3) 본문=절(□) 단위 누적, 페이지당 3절. AI 보고서 검증 결과: Ⅰ장=3쪽, Ⅲ장=4쪽, Ⅴ장=5쪽, Ⅵ장=6쪽 모두 한글 환경과 100% 일치, 총 6쪽 일치. 신규 스크립트: `simulate_pages.py` (페이지 시뮬레이션 + 목차 페이지번호 자동 매핑), `ensure_body_anchor.py` (본문 시작 단락 pageBreak="1" 강제 보장). chapter-aware 매핑: 사용자 콘텐츠의 텍스트 슬롯에서 장 번호(Ⅰ~Ⅹ)를 감지하여 같은 장에 속한 모든 페이지번호 슬롯에 그 장의 페이지를 일관되게 할당. LibreOffice+H2Orestart PDF 변환은 폰트 대체로 페이지 분량이 달라지므로 의도적으로 채택하지 않음(파이썬 단독 시뮬레이션이 한글 환경 결과와 더 일치). |
| 2026-05-12 | 3.3.1 | **1페이지 보고서 목차 구성 가이드라인 통합** — `templates/format_1p/outline_guide.md` 신규 추가. 공공기관 1페이지 보고서의 **보고 목적별 11가지 표준 목차** (현황·동향 / 검토·의사결정 / 사업·정책 계획 / 문제해결·개선방안 / 이슈·리스크·사고 / 결과·성과 / 회의 안건 / 회의 결과 / 행사 계획 / 제휴·협력 검토 / 예산·구매·품의) 와 3가지 공통 골격(4절 기본형·5절 확장형·3절 압축형) 을 정식 등재. 양식의 4섹션 슬롯(`text_004`~`text_023`) 과 목차 절의 대응표 포함. 1p 보고서 빌드의 표준 워크플로우 확정: **(1) 보고 목적 결정 → (2) 11개 유형 중 매칭되는 표준 목차 선정 → (3) 양식 슬롯에 매핑 → (4) `fill_skeleton.py` 빌드.** 또한 매핑 작성 시 본문-메타 분리 원칙도 함께 명시 — 시행문의 수신자·발신자·결재선·시행번호·날짜·전화 같은 메타 정보는 Claude 가 가짜값(예: `02-XXX-XXXX`, `AI혁신처-368`) 으로 채우지 말고 **빈 값** 으로 두어 한글 사용자가 직접 채울 자리로 남겨두는 것이 표준. |
| 2026-05-12 | **3.4.0** | **이전 자동 빌드 모드(compose_doc.py) 완전 제거 — 빈 골격 채우기 단일 워크플로우로 단일화** — v3.2 부터 빈 골격 채우기(모드 2) 가 시각 디자인 100% 보존이라는 본질적 강점으로 표준이 됐지만, SKILL.md 에는 v3.3.x 까지 자동 빌드(모드 1, `compose_doc.py`) 가 "빠른 초안용"으로 함께 안내되어 있어 사용자 혼란 야기. 자동 빌드 모드는 단락 기반 빌더라 양식의 표·테두리·음영·페이지헤더 등 시각 구조를 유지하지 못하므로 v3.4.0 부터 deprecated 처리. **제거된 스크립트 6개 (총 116KB)**: `compose_doc.py` (메인 파이프라인), `layout_optimizer.py` (적/의/것/들·페이지 걸침 점검), `format_builders.py` (4개 양식 단락 빌더), `content_mapper.py` (입력 파싱), `build_hwpx.py` (HWPX 조립), `hwpx_helpers.py` (저수준 XML). 모드 2 표준 스크립트 6개는 그대로 유지: `make_skeleton.py`, `fill_skeleton.py`, `fix_namespaces.py`, `validate.py`, `simulate_pages.py`, `ensure_body_anchor.py`. SKILL.md 의 모든 `compose_doc`/`layout_optimizer` 참조 정리 및 워크플로우 ①~④, "두 가지 빌드 모드" 섹션, 참조파일 처리, 트러블슈팅, Claude/Cursor/n8n 호출 패턴 전면 재작성. 레이아웃 최적화(④ 단계) 는 더 이상 별도 스크립트가 아니라 Claude 가 매핑 *전*에 직접 적용하는 작성 원칙으로 변경 (`references/layout-rules.md` 참조). 표준 빌드 워크플로우: `fill_skeleton.py` → `fix_namespaces.py` → `validate.py` (+ 풀버전: `simulate_pages.py` → `ensure_body_anchor.py`). 패키지 크기 약 116KB 감소. |
| 2026-05-13 | **3.5.0** | **풀버전 보고서 4대 함정 자동 검사 + 통합 빌드 도입** — v3.4.0 까지 풀버전 보고서 빌드 시 실사용에서 4가지 결함이 반복 발생함이 확인됨. ① **목차 슬롯 위계 위반**: 양식의 대제목 슬롯(`001/003/013/021/033/043`) 과 소제목 슬롯의 서식이 고정되어 있는데 임의로 매핑하면 Ⅲ장 제목이 일반 본문 서식으로, 1.항목명이 대제목 서식으로 표시되는 현상. ② **빈 슬롯으로 인한 점선 끊김**: 양식 슬롯 수(대제목 6 + 소제목 20) 보다 콘텐츠가 적으면 빈 행 발생 → 점선·페이지번호 정렬 무너짐. ③ **본문 마커 중복**: `본문_항목_001~009` 는 paraPr 자동 ○ 마커인데 콘텐츠에 ◦ 직접 표기 시 마커 두 개 중복 표시, 반대로 `010~012` 는 양식 원본에 ◦ 가 있어 직접 표기 필수. ④ **페이지번호 미반영**: `simulate_pages.py` 가 페이지번호를 계산만 하고 hwpx 에 적용하지 않아 목차 페이지번호가 실제 본문과 불일치. **v3.5.0 변경사항**: (1) **`scripts/build_full.py` 신규** — 풀버전 통합 빌드 워크플로우. 입력 검사(①②③) + 1차 빌드 + 페이지 시뮬레이션 + values 자동 갱신 + 2차 빌드 + 후처리 3종을 한 번에 처리. `--strict` 옵션 시 위반 발견하면 빌드 중단. (2) **`simulate_pages.py` 핫픽스** — `--values` 인자 추가하여 사용자 매핑 기반 chapter 인식 정확도 향상, `--apply-to-values` 옵션으로 페이지번호를 values.json 에 직접 병합. (3) **`templates/format_full/skeleton_mapping.json` 메타데이터 보강** — 슬롯별 `hierarchy`(chapter/subsection/page_number) 와 `marker_type`(auto/direct) 필드 추가, `hint` 필드로 매핑 가이드 제공. (4) **`references/format-full.md` 보강** — 4대 함정 명세, 양식별 권장 소제목 수(Ⅰ:0/Ⅱ:4/Ⅲ:3/Ⅳ:5/Ⅴ:4/Ⅵ:4), v3.5.0 권장 워크플로우 추가. (5) **SKILL.md** Critical Rules 12–15 신규 추가. 단축 효과: 풀버전 빌드 명령 7단계 → 1단계(`build_full.py`), 4대 함정 사전 감지로 재작업 비용 제거. |
| 2026-05-13 | **3.6.0** | **표지·공문 제목 자간 압축 깨짐 자동 해소 — `wrap_long_titles.py` 후처리 도입** — 풀버전 표지 큰 제목(HY헤드라인M 28pt) 과 공문 제목(맑은고딕 14pt) 이 양식의 결재제목 셀 너비(44737/44660 HwpUnit ≈ 44.7mm) 를 초과하는 길이로 입력되면, 한글2018 (해당 폰트 보유 환경) 이 셀 안 단락의 `<hp:linesegarray>` 가 단일 lineseg 인 점을 보고 **자간을 음수로 강제 축소** 해서 한 줄에 끼워넣는 비정상 동작 발생 (글자 겹침·가독성 급락). 같은 hwpx 를 한컴뷰어(폰트 미보유) 에서 열면 대체 폰트의 넓은 글자 폭으로 인해 자연 줄바꿈되어 2줄로 정상 표시 → "한컴뷰어 2줄 = 정답, 한글2018 1줄 압축 = 비정상" 임을 의미. **v3.6.0 해결**: (1) **`scripts/wrap_long_titles.py` 신규** — fill_skeleton 후처리 단계로, section0.xml 안의 표지 제목 단락(charPrIDRef="44" + paraPrIDRef="19") 과 공문 제목 단락(charPrIDRef="21" + paraPrIDRef="17") 을 자동 감지하여 텍스트 길이가 임계(표지 14자·공문 25자) 를 초과하면 가장 균형 잡힌 공백 위치에서 단락을 둘로 분리. 한글의 두 번째 단락 lineseg 좌표 자동 재계산을 활용해 별도 vertpos 조정 없이도 정상 정렬됨. (2) **`build_full.py` 통합** — 단계 5(후처리) 에 `wrap_long_titles.py --format full` 자동 호출 추가. (3) **공문도 동일 적용** — 공문은 별도 빌드 스크립트가 없으므로 `wrap_long_titles.py <hwpx_path> --format gongmun` 또는 `--format auto` 로 수동/자동 호출. (4) **SKILL.md Critical Rule 16** 신규 추가. 결과: 표지·공문 제목이 어떤 길이로 입력되든 한글2018·한컴뷰어 양쪽 환경에서 동일하게 2줄로 균형 표시. |
| 2026-05-13 | **3.6.1** | **풀버전 목차 점선 깨짐 자동 해소 (`fix_toc_dots.py`) + 공문 후처리 임시 비활성화** — v3.6.0 으로 표지 큰 제목 깨짐은 해결됐으나, 사용자 검증 결과 두 가지 잔존 이슈 확인. ① **풀버전 목차 점선 끊김**: 한글2018(폰트 보유) 환경에서 목차 일부 항목의 점선이 페이지번호까지 닿지 않거나 페이지번호 자체가 잘림. 진단 결과 양식 원본 텍스트("Ⅰ. 사업 개요" 등) 기준으로 박힌 `<hp:tab width="..." leader="3" type="2"/>` 의 width 가 사용자 콘텐츠 텍스트 길이와 무관하게 11404~35444 사이로 무작위 분포함을 확인 (같은 12자 항목인데 width 가 11404 또는 32844 등 제각각). 한글2018 이 실제 폰트 메트릭으로 텍스트 폭을 측정해 단락 너비(43000) 와 정합성을 검증할 때, 텍스트 폭 + width + 페이지번호 폭의 합이 맞지 않으면 점선/페이지번호를 표시하지 않거나 잘라냄. 한컴뷰어는 대체 폰트로 측정이 부정확해서 오히려 자연 fallback 으로 정상 표시. ② **공문 본문 자간 압축 깨짐**: v3.5.0 부터 잔존하던 공문 본문 (2번 항목 이후) 단락의 자간 압축 깨짐이 별개 이슈로 남아 있어, v3.6.0 의 공문 제목 분리 후처리가 마치 본문을 망친 것처럼 오인되는 상황 발생. **v3.6.1 해결**: (1) **`scripts/fix_toc_dots.py` 신규** — 풀버전 빌드 결과 hwpx 의 모든 `<hp:tab width="..." leader="3" type="2"/>` 의 width 를 통일된 값(초기 45000) 으로 일괄 치환. (2) **`build_full.py` 통합** — 단계 5 후처리에 `fix_toc_dots.py` 자동 호출 추가. (3) **공문 후처리 임시 비활성화** — SKILL.md 1p/시행문 가이드에서 `wrap_long_titles.py --format gongmun` 호출 안내 제거. (4) **SKILL.md Critical Rule 17** 신규 추가. |
| 2026-05-13 | **3.6.2** | **목차 점선 width 미세 조정 (45000 → 42000)** — v3.6.1 의 width=45000 이 단락 너비(43000) 보다 컸기 때문에, type="2" right-align tab 해석상 점선이 단락 우측 끝까지 가버리고 페이지번호가 wrap 되어 다음 줄로 밀려나 보이지 않는 새 이슈 발견(사용자 검증). 단락 너비보다 살짝 작은 42000 (페이지번호 한 자리 폭 약 1000 여유) 으로 재조정. type="2" right-align tab 에서 width 는 점선이 끝나고 페이지번호가 right-align 으로 그려질 위치를 의미하므로, 페이지번호 폭만큼 여유를 두어야 페이지번호가 단락 안에 표시됨. |
| 2026-05-13 | **3.6.3** | **공문 본문 자간 압축 깨짐 자동 해소 (`fix_gongmun_body.py`)** — 사용자가 v3.5.0 공문 결과물을 첨부한 후 정밀 분석으로, 공문 본문 깨짐의 진짜 원인 확정: 공문 양식 본문 단락(표 셀 밖, paraPrIDRef=29/26/18/20 등) 의 `<hp:linesegarray>` 가 단일 `<hp:lineseg horzsize="49108" .../>` 로 저장되어 있어 한글2018 (실제 폰트 메트릭 보유 환경) 이 단락 너비 초과 텍스트를 한 줄에 끼워넣으려 자간을 강제 압축. 표지 제목 깨짐과 동일 메커니즘. **v3.6.3 해결**: (1) **`scripts/fix_gongmun_body.py` 신규** — section0.xml 안의 `<hp:linesegarray>` 중 단일 `<hp:lineseg horzsize="49108" .../>` 만 들어있는 패턴을 정규식 매칭하여 해당 linesegarray 통째 제거. 한글이 파일 열 때 폰트 메트릭으로 lineseg 자동 재계산해서 텍스트 길이에 맞춰 자연 줄바꿈. 표 셀 안 단락 lineseg 는 horzsize 가 다른 값(44380, 6004, 42676 등) 이라 자동으로 제외됨. 다중 lineseg(이미 정상) 단락도 미매칭으로 보존. (2) **SKILL.md 1p/시행문 가이드** 에 `fix_gongmun_body.py` 호출 단계 추가. 1p 보고서는 본문 셀 구조 다르므로 호출해도 매칭 0건. (3) **SKILL.md Critical Rule 18** 신규 추가. **단락 구조 파싱(hp:p 중첩) 대신 horzsize 기반 단순 매칭** 채택 사유: 공문 양식이 `<hp:p>` 안에 `<hp:tbl>` → `<hp:tc>` → `<hp:subList>` → `<hp:p>` 형태로 중첩되어 있어 단락 단위 처리가 복잡하지만, 본문 단락 폭 (49108) 이 표 셀 너비들과 명확히 구분되므로 horzsize 직접 매칭이 더 안정적. |
| 2026-05-13 | **3.6.4** | **두 가지 핵심 버그 핫픽스: 풀버전 안 열림 + 공문 단락 합쳐짐** — 사용자 검증에서 두 가지 신규 이슈 발견. ① **풀버전 hwpx 가 한글에서 안 열림**: v3.6.0 `wrap_long_titles` 가 표지 제목을 두 단락으로 분리할 때 원본 단락의 `<hp:linesegarray>` 를 그대로 복사함. 결과적으로 두 단락의 `vertpos="1820"` 이 동일해서 한글이 같은 세로 위치에 두 단락을 그리려다 충돌, 파일 열기 실패. ② **공문 "3. 보고서 주요 내용..." 단락 합쳐짐**: 공문 양식 skeleton 의 본문 영역에서 `{{text_008}}` (2번 항목) 과 `{{text_009}}` (3번 항목) placeholder 가 **같은 `<hp:p>` 안에 별도 `<hp:run>`** 으로 들어있는 양식 설계 결함 확인. placeholder 만 채우면 두 텍스트가 한 단락에 이어붙어 표시. **v3.6.4 해결**: (1) **`wrap_long_titles.py` 수정** — `build_split_block` 함수가 두 번째 단락의 `<hp:linesegarray>` 통째 제거. 한글이 파일 열 때 폰트 메트릭으로 두 번째 단락의 vertpos 자동 재계산 → 충돌 해소. 첫 번째 단락은 원본 lineseg 유지 (이미 정상 위치). (2) **`scripts/split_gongmun_paragraphs.py` 신규** — fill_skeleton 토큰 치환 *전* 에 skeleton.xml 메모리 상에서 `{{text_008}}` placeholder 직후 `</hp:p><hp:p paraPrIDRef="29" ...>` 강제 단락 분리 삽입. skeleton 파일 자체는 변경 안 됨 (사용자 원칙 "스켈레톤 유지" 보존). SPLIT_PAIRS 메타데이터로 추후 다른 placeholder 쌍 확장 가능. (3) **`fill_skeleton.py` 통합** — `split_paragraphs=True` 기본 옵션으로 자동 호출. `--no-split-paragraphs` 플래그로 비활성화 가능. 결과 dict 에 `paragraph_splits` 카운트 추가. |
| 2026-05-13 | **3.6.5** | **목차 점선 깨짐 진짜 근본 원인 발견 — lineseg 캐시 제거 추가** — 사용자 결정적 단서 제공: "한글에서 점선을 한 번 지웠다가 Ctrl+Z 로 되돌리면 정확하게 페이지 너비 맞춰서 점선 길이가 조정된다". 즉 **한글의 재계산 동작은 정상**인데 **우리 hwpx 에 저장된 lineseg 캐시가 잘못된 정보를 담고 있고, 한글이 첫 렌더링 시 이를 따라간다**는 것. v3.6.1 의 width 통일만으로는 부족했던 이유: lineseg 자체에 점선 길이·페이지번호 위치의 캐시가 들어있어서 width 값과 무관하게 lineseg 정보로 그려짐. **v3.6.5 해결**: `fix_toc_dots.py` 에 **단계 B(lineseg 제거)** 추가. 함수 `remove_linesegarray_from_dotted_paragraphs`: `<hp:tab leader="3"/>` 를 포함한 모든 hp:p 블록의 `<hp:linesegarray>` 를 통째 제거. 한글이 파일 열 때 폰트 메트릭으로 lineseg 자동 재계산 → 사용자가 Ctrl+Z 후 보던 "정확한 점선 길이" 가 처음부터 그려짐. fix_gongmun_body 와 동일한 lineseg 캐시 무효화 접근. 실측: 26개 목차 단락 모두 linesegarray 제거 적용. **교훈**: HWPX 의 `<hp:linesegarray>` 는 렌더링 캐시이며, 양식 빈 골격에서 사용자 콘텐츠로 토큰을 치환해도 캐시는 그대로라 한글이 폰트 메트릭이 들어맞지 않는 잘못된 캐시를 우선 따라간다. **lineseg 캐시 제거 = 한글 자동 재계산 강제** 가 양식 종속 깨짐 이슈의 일반적 해법임을 확인. |
| 2026-05-13 | **3.6.6** | **공문 양식 규격 정밀 진단 + 풀버전 Ⅳ장 들여쓰기 누락 보정** — 사용자 요청 "공문 양식 규격부터 차근차근 살펴보자" 에 따라 양식 매핑(skeleton_mapping.json) 과 단락 구조를 정밀 분석. ① **공문 양식 의도 확정**: 본문은 1번/2번 두 단락 구조이며, `text_008`("2. " 마커) 과 `text_009`(2번 본문) 가 **같은 hp:p 안의 별도 hp:run 인 것은 양식 의도** (paraPr=29 공유). v3.6.4 의 `split_gongmun_paragraphs` 강제 분리는 양식 의도를 깨는 잘못된 처리였음 → **SPLIT_PAIRS 빈 리스트로 변경 (실질 비활성화)**. ② **풀버전 Ⅳ장 들여쓰기 누락 발견**: skeleton.hwpx 자체에 `{{목차_항목_021}}` (Ⅳ장) 단락만 `<hp:run charPrIDRef="12"><hp:t> </hp:t></hp:run>` 들여쓰기용 공백 run 이 누락. **v3.6.6 해결**: (1) **`scripts/fix_skeleton_defects.py` 신규** — INDENT_FIXES 메타데이터에 등록된 token 들의 직전 hp:run 이 들여쓰기 run 인지 검사하고, 누락 시 자동 보충. (2) **`fill_skeleton.py` 통합** — `fix_defects=True` 기본. (3) **공문 양식 본문 슬롯 의도 명세 확정**: text_007(paraPr=17) = 1번 단독 / text_008+text_009(paraPr=29) = 2번 마커+본문 / 목차_항목_001/002(paraPr=26) = 가./나. / text_010~013 = 1)/가)/(1)/① / 목차_항목_003/004 = 붙임. |
| 2026-05-13 | **3.6.7** | **공문 본문 단락 동적 확장 — 양식 한계 돌파** — 사용자 지적: "공문은 단락이 내용에 따라서 2개 이상이 될 수도 있는데 왜 2개로 고정하는거야?". 양식 한계는 양식 디자이너의 디자인 시점 선택일 뿐, 빌더는 사용자 콘텐츠에 맞춰 단락을 동적 확장해야 함. **v3.6.7 해결**: `scripts/expand_gongmun_body.py` 신규 — fill_skeleton 토큰 치환 *전* 메모리 단계에서 `"본문"` 배열 처리. 1번째→text_007, 2번째→text_008+text_009 자동 마커 분리, 3번째 이상→동적 hp:p (paraPr=29, charPr=24) 추가. `fill_skeleton.py` 통합 (`expand_body=True` 기본). |
| 2026-05-13 | **3.6.8** | **본문 모든 위계 동적 확장 + 빈 placeholder 단락 자동 제거** — 사용자 질문: "본문 하부에 있는 항목들도 모두 들여쓰기 위계에 맞춰서 컨텐츠 양에 따라 동적으로 조절되는거지? (컨텐츠가 없으면 아예 표출되지 않는거고?)". v3.6.7 은 본문(1./2./3./...) 만 확장 지원. **v3.6.8 전면 확장**: (1) **EXPANSION_RULES 데이터 구조** — 7개 위계 키(`본문`, `본문_가나`, `본문_1)`, `본문_가)`, `본문_(1)`, `본문_①`, `붙임`) 모두 등록. 각 키마다 양식 슬롯(1~2개) + 동적 추가 paraPr/charPr + anchor token + 자동 들여쓰기 prefix(4/6/8/10-space) 정의. (2) **빈 placeholder 단락 자동 제거** — fill_skeleton 토큰 치환 시 빈 값 placeholder 를 `EMPTY_MARKER` 로 치환, 후처리에서 EMPTY_MARKER 가 든 가장 안쪽 hp:p 검사: hp:tbl/hp:subList 든 단락은 **무조건 보존** (마커만 제거, 발신부 표 등 중요 구조 보호), 그 외 의미 있는 텍스트 있으면 마커만 제거, 다 비었으면 hp:p 통째 제거. (3) **`_find_matching_p_close` 헬퍼** — hp:p 안 hp:tbl > hp:tc > hp:subList > hp:p 중첩 환경에서 짝 맞는 `</hp:p>` 정확히 매칭. (4) **BODY_PLACEHOLDERS 한정 제거** — EMPTY_MARKER 는 본문 영역 placeholder 에만 적용, 표 안(헤더/발신부) placeholder 는 빈 ""로 치환해 표 구조 단락 보존. **v3.6.8 시행착오와 안전화**: 초기 시도에서 `목차_항목_004` 가 발신부 표 전체를 감싸는 외부 hp:p 라 단순 `</hp:p>` 다음 삽입 시 동적 단락이 발신부 뒤로 밀려나는 문제 발견. hp:t 닫는 위치에서 hp:run/hp:p 강제 분리도 시도했으나 `<hp:run>` 안에 `<hp:tbl>` 이 hp:t 와 같은 레벨 자식으로 들어있는 HWPX 양식 구조 특수성으로 인해 분리 결과가 한글에서 안 열리는 잘못된 XML 생성. **최종 안전 설계**: 붙임 anchor 를 hp:tbl 포함 안 하는 `목차_항목_003` 로 변경, 슬롯 1개만 사용 (모든 추가 붙임은 동적 hp:p). `목차_항목_004` 슬롯은 사용 안 함 → 빈 마커로 치환되지만 hp:tbl 보존 예외로 외부 hp:p (발신부 표 감싸기) 통째 보존, 마커만 제거. |
| 2026-05-13 | **3.6.9** | **위계별 들여쓰기 통일 (양식 슬롯 ↔ 동적 단락)** — 사용자 보고: "레벨이 달라질때 위계에 따른 들여쓰기가 완벽하지 않네". v3.6.8 까지는 양식 슬롯에는 prefix 미적용 (양식 처리에 위임) 동적 추가에만 prefix 적용으로, 슬롯/동적 들여쓰기 불일치. 예: `text_010` (1)) 양식 슬롯에 들어간 사용자 텍스트는 들여쓰기 없음, 동적 추가는 4-space → 시각적 불일치. **진단**: 양식 빈 골격에서 가나 슬롯(목차_항목_001/002) 만 placeholder 앞에 `"  <hp:fwSpace/>"` 자동 들여쓰기 박혀있고, 1)/가)/(1)/① 슬롯은 placeholder 만 있음. **v3.6.9 해결**: (1) EXPANSION_RULES 의 `indent` 키를 `slot_indent` + `dynamic_indent` 두 키로 분리. (2) `normalize_body_input` 에서 양식 슬롯 매핑 시에도 `slot_indent` prefix 적용. (3) 위계별 설정: 본문_가나 (`slot_indent=""`, `dynamic_indent="  \u3000"`) — 양식 자동 들여쓰기 유지 + 동적 추가만 전각공백 prefix / 본문_1)~① (`slot_indent=dynamic_indent="    "/"      "/"        "/"          "`) — 슬롯/동적 동일 prefix. (4) `_apply_indent` 가 전각공백(`\u3000`) 시작도 인식해서 사용자 직접 들여쓰기 입력 보호. |
| 2026-05-13 | **3.6.10** | **수신자 라벨/입력 분리 양식 결함 보정 + 다. 들여쓰기 미세 차이 해결** — 사용자 보고 ① "상단 수신자 입력란을 착각해서 입력함 — 수신은 라벨이고 그 옆셀에 수신자를 넣어야함" ② "가/나/다 중 다 부분 들여쓰기가 미세하게 다름". **진단 ①**: 양식 빈 골격 만들면서 양식의 정적 "수신자" 라벨 셀이 `{{text_004}}` placeholder 로 변환되어 사용자가 입력하면 라벨 자체가 사라짐. 옆 셀(셀[1]) 은 빈 hp:p 만 있고 placeholder 없음. **진단 ②**: 양식 슬롯 가/나 hp:t 안의 `<hp:fwSpace/>` (XML element) 와 동적 추가의 `"  \u3000"` (텍스트 전각공백) 을 한글이 미세하게 다른 폰트 메트릭으로 렌더링. **v3.6.10 해결 ①**: (1) `fix_skeleton_defects.py` 에 `add_receiver_input_slot` 함수 신규 — 셀[1] 빈 hp:p 안에 `{{수신자}}` placeholder 동적 삽입 (라벨 셀 charPr 복사해서 시각 일치). (2) `fill_skeleton.py` 에 `DEFAULT_VALUES = {"text_004": "수신"}` 추가 — 사용자 미입력 시 자동 라벨 부여. (3) test_values 사용법 변경: `text_004` 빼고 `수신자` 키 사용. **v3.6.10 해결 ②**: (1) `_build_p_block` 에 `indent_xml` 파라미터 추가 — hp:t 안에 raw XML 그대로 삽입. (2) EXPANSION_RULES 본문_가나에 `dynamic_indent_xml="  <hp:fwSpace/>"` 추가 — 양식 슬롯과 정확히 동일한 element 사용해서 한글 메트릭 차이 원천 제거. (3) `normalize_body_input` / `insert_dynamic_paragraphs` 가 4-tuple `(text, para_pr, char_pr, indent_xml)` 로 갱신. **결과**: 수신자 행이 [수신][내부 임직원] 두 셀로 정상 분리, 가/나/다 hp:t 모두 동일 패턴 `"  <hp:fwSpace/>..."` 로 시각적 완전 일치. |
