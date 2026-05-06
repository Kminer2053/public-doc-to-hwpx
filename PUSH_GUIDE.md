# GitHub 푸시 가이드 (5분)

> 이 파일은 푸시 후 삭제하시면 됩니다.

## 사전 준비

GitHub 계정에 로그인 + Git이 로컬에 설치되어 있어야 합니다.

```bash
git --version  # 2.x 이상
```

## 1. GitHub에서 빈 리포 생성

브라우저에서 https://github.com/new 접속 → 다음과 같이 입력:

- **Repository name**: `public-doc-to-hwpx`
- **Description** (복사해서 붙여넣기):
  ```
  AI 콘텐츠를 공공기관 표준 보고서(HWPX)로 다듬는 Claude Skill — 한 문장 한 줄, 개조식, 두괄식. 4단계 워크플로우 + 4개 양식(1p/풀버전/시행문/이메일).
  ```
- **Public** 선택
- **Initialize this repository with**: 모두 **체크 해제** (README, .gitignore, license 모두 생성하지 않음 — 이 패키지에 이미 들어있음)
- **Create repository** 클릭

## 2. 로컬에서 푸시

리포 페이지에 표시된 URL (예: `https://github.com/지식광부/public-doc-to-hwpx.git`)을 복사한 뒤:

```bash
# 압축 푼 디렉토리로 이동
cd public-doc-to-hwpx-v3

# Git 초기화
git init -b main
git add .
git commit -m "Initial commit: v3.0 — 4-stage workflow + writing principles"

# 본인의 GitHub URL로 변경 (위에서 복사한 것)
git remote add origin https://github.com/<your-username>/public-doc-to-hwpx.git

# 푸시
git push -u origin main
```

## 3. 인증 (처음 푸시 시)

GitHub은 비밀번호 대신 **Personal Access Token (PAT)** 또는 **SSH 키**를 사용합니다.

### 가장 간단한 방법: PAT

1. https://github.com/settings/tokens/new 에서 토큰 생성
2. **scope**: `repo` 만 체크
3. 생성된 토큰을 복사 (한 번만 표시됨!)
4. `git push` 시 password 입력 자리에 토큰을 붙여넣기

### 더 편한 방법: GitHub CLI

```bash
# macOS
brew install gh
gh auth login          # 한 번만 인증

# 그 다음부터는 자동
git push -u origin main
```

## 4. 푸시 후 점검

브라우저에서 리포 URL 접속 → 다음이 보이면 성공:

- README.md가 메인에 렌더링됨 (한국어 4단계 워크플로우 도식 포함)
- 디렉토리 구조: `scripts/`, `references/`, `templates/`, `SKILL.md` 보임
- 우측 About에 LICENSE: MIT, 언어 분포에 Python 표시

## 5. 마무리 (선택)

리포 설정 (Settings) 에서:

- **Topics 추가**: `claude-skill`, `hwpx`, `korean`, `report-generator`, `public-doc`, `government-document`
- **Description** 위에 한 줄 추가 (이미 입력했다면 패스)
- **Social preview image**: 직접 만든 이미지 업로드 (선택)

Issues / Discussions 탭은 켜두면 다른 분들의 피드백을 받기 좋습니다.

---

푸시 완료 후 이 PUSH_GUIDE.md는 다음 명령으로 삭제 가능:

```bash
git rm PUSH_GUIDE.md
git commit -m "remove push guide"
git push
```
