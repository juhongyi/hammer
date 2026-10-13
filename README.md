# AI 프레젠테이션 PoC

`PRD.md`의 핵심 파이프라인을 Next.js + FastAPI로 구현합니다. 판단은 TypeSafe 공식 Jev API, 텍스트 생성은 Cloudflare Workers AI의 `@cf/openai/gpt-oss-120b`를 사용합니다.

## 실행

1. `.env.example`을 루트 `.env`로 복사하고 다음 값을 설정합니다.
   - `TYPESAFE_API_KEY`: TypeSafe API 키
   - `CLOUDFLARE_ACCOUNT_ID`: Cloudflare 계정 ID
   - `CLOUDFLARE_API_TOKEN`: 해당 계정의 Workers AI 호출 권한이 있는 API 토큰
   - `JEV_MODEL`, `WORKERS_AI_MODEL`, `MODEL_TIMEOUT_SECONDS`: 필요할 때 변경
2. Docker 데몬을 실행합니다.
3. 저장소 루트에서 실행합니다.

```sh
docker compose up --build
```

- 웹: <http://localhost:3000>
- 백엔드 API 문서: <http://localhost:8000/docs>

`.env`는 Git과 Docker 빌드 컨텍스트에서 제외합니다. 키는 백엔드 컨테이너에만 전달하며 브라우저에 전달하지 않습니다. 온톨로지와 실행 결과는 `poc-data` 볼륨의 SQLite에 저장합니다. 소스 변경은 마운트와 개발 서버의 reload로 반영합니다. 의존성 변경 시 이미 생성된 `web-modules` 볼륨에도 `docker compose exec web npm ci`를 실행합니다.

## 사용 흐름

1. **프레젠테이션** 화면에 한국어 주제·요청·원고를 입력합니다.
2. Jev가 표지 포함 6~30장과 챕터 수를 선택합니다. Workers AI가 개요를 작성하고, Jev가 챕터 경계를 선택합니다. 일반 로직이 페이지를 묶고 Workers AI가 챕터 제목을 작성합니다.
3. 구조·의미 검수를 통과하면 표지·챕터·페이지 제목, 핵심 메시지, 항목 제목·설명을 편집합니다. 장수·페이지 순서·챕터 소속은 유지합니다.
4. **개요 확정 및 슬라이드 생성**을 누릅니다. Jev가 확정 개요의 표현 유형을 분류하고, 일반 로직이 사용 여부와 구조 제약으로 제한한 후보 중 레이아웃을 선택합니다.
5. Workers AI가 슬롯 문구를 작성합니다. 개요·챕터 제목·문구 생성에 장수와 필드·항목 수·용량을 지정한 JSON Schema를 전달합니다. 일반 로직의 필드·항목 수·용량·수치와 단위 검사, Jev의 의미 검수, Chromium의 실제 배치 검사를 모두 통과하면 전체 슬라이드를 열람합니다.
6. **Jev 후보·판단 결과 및 검사 기록**에서 판단 입력·후보·확률·선택 결과·검수 판정·재생성 기록을 확인합니다.

생성 문구 검사 실패는 해당 개요 또는 페이지를 1회 재생성한 뒤 재검사합니다. 장수·챕터 수·결정된 경계 또는 확정 개요·유형·레이아웃은 유지합니다. HTTP 실패·시간 초과·유효하지 않은 Jev 판단·후보 부재는 텍스트 재생성 없이 실패합니다. 완료 상태와 슬라이드 열람은 모든 페이지 검사 후에만 허용합니다. 실패한 실행에도 확정 개요가 보존됩니다.

### 온톨로지 관리

**온톨로지 관리** 화면에서 JSON 정의를 편집하고 **수정 내용 검수 → 변경 내용 확인 → 검수한 정의·사용 여부 적용** 순서로 적용합니다.

- `types`: 표현 목적, 의미적 적합·부적합 조건
- `layouts`: 용도, 지원 표현 유형, `enabled` 사용 여부
- `slots`: ID, 역할, 형태, 필수 여부, 항목 수와 텍스트 용량

초기 레이아웃은 표지·핵심 메시지·목록·비교·과정·마무리 6종입니다. 기존 ID·순서·슬롯 형태·필수 여부와 고정 렌더러의 표현 범위를 유지하도록 검증합니다. 용량은 초기 물리적 상한 안에서 변경할 수 있습니다. `enabled: false`인 레이아웃은 다음 생성의 후보에서 제외됩니다.

최신 온톨로지는 개요 확정 시 실행에 스냅샷으로 저장합니다. 수정한 정의는 다음 슬라이드 생성의 분류·후보·문구 생성·검사에 전달되며, 이미 생성된 결과는 변경되지 않습니다.

## 코드 구성

```text
apps/web/                 Next.js 임시 UI와 백엔드 프록시
services/api/app/
  main.py                 실행·확정·온톨로지·슬라이드 API
  models.py               Jev / Workers AI HTTP 연동
  pipeline.py             판단·생성·검수·재생성·상태 제어
  ontology.py             초기 데이터·관리 검증·후보 제한
  schemas.py              입력·개요·온톨로지 데이터 모델
  validation.py           개요·슬롯·수치의 정확한 검사
  render.py               HTML 렌더러와 Chromium 배치 검사
  store.py                SQLite 저장과 확정 상태 전환
services/api/tests/       파이프라인·API·실제 렌더링·웹 흐름 테스트
compose.yaml              개발환경
```

백엔드 렌더러가 만든 동일 HTML을 웹의 iframe에 표시합니다. Compose 이미지의 한국어 폰트(NanumGothic)를 API로 제공하여 Chromium 검사와 웹 열람이 같은 폰트를 사용합니다. 로컬 실행에서는 `FONT_PATH`로 같은 TTF 폰트를 지정할 수 있습니다.

## 검증

### Compose에서 백엔드 테스트

```sh
docker compose exec api pytest -q --ignore=tests/test_ui.py
docker compose stop web
docker compose run --rm --no-deps web npm run build
docker compose run --rm --no-deps web npm run typecheck
docker compose up -d web
```

개발 서버와 빌드가 같은 `.next` 볼륨에 동시에 쓰지 않도록 웹을 멈춘 뒤 검사하고 다시 실행합니다.

### 로컬에서 전체 자동 테스트

Python 3.12+, Node.js 24+, `uv`를 사용합니다.

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r services/api/requirements.txt
.venv/bin/python -m playwright install chromium
npm --prefix apps/web ci
.venv/bin/python -m pytest -c services/api/pytest.ini services/api/tests -q
npm --prefix apps/web run build
npm --prefix apps/web run typecheck
docker compose config --no-env-resolution
```

웹 흐름 테스트는 임시 DB와 자동으로 시작한 Next.js/FastAPI 서버에서 실행합니다. 외부 모델만 테스트용 응답으로 대체하고 개요 편집, 실제 Chromium 렌더링, 온톨로지 검수·저장, 다음 생성의 후보 부재, 기존 결과 보존을 확인합니다. API 키 없이 실행할 수 있으며 실제 모델 검증을 대신하지 않습니다. 웹 의존성이 설치되지 않은 환경에서는 웹 테스트를 건너뜁니다.

### 실제 모델 E2E 확인

루트 `.env` 설정과 Compose 실행 후 웹에서 입력 → 개요 검수·수정·확정 → 슬라이드 생성·검수·열람을 수행합니다. 온톨로지 변경 후 다음 생성의 판단 입력·후보와 기존 결과 보존도 확인합니다. 실제 API 호출은 설정한 계정에 비용을 발생시킬 수 있습니다.

PoC는 단일 FastAPI 프로세스의 background task로 실행합니다. 개발 reload를 포함한 서버 재시작으로 진행 중인 호출이 중단되면 해당 실행을 실패로 표시하고 저장된 개요·결과를 보존합니다. 로컬 개발용 UI에는 인증이 없습니다.
