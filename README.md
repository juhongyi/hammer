# System One-native AI 프레젠테이션 PoC

한국어 텍스트로 발표자료를 만드는 앱과 디자인 데이터 온톨로지 관리 앱입니다.
제품 요구사항은 [PRD.md](PRD.md), 검증 결과는 [docs/verification.md](docs/verification.md)에 있습니다.

## 실행

Node.js 24 LTS, pnpm 12.6.0, uv, Docker Compose가 필요합니다.

1. `.env.local.example`을 루트 `.env.local`로 복사합니다.
2. 아래 세 값을 설정합니다. 키는 서버에서만 사용하며 Git에 포함되지 않습니다.
   - `CLOUDFLARE_ACCOUNT_ID`
   - `CLOUDFLARE_API_TOKEN` — Workers AI 호출 권한이 있는 토큰
   - `TYPESAFE_API_KEY`
3. 실행합니다.

```sh
docker compose --env-file .env.local up --build -d --wait
```

| 제품 | 주소 |
|---|---|
| AI 프레젠테이션 | http://localhost:3000 |
| 디자인 데이터 온톨로지 | http://localhost:3001 |
| FastAPI OpenAPI | http://localhost:8000/docs |

모델 키 없이도 두 앱과 온톨로지는 실행됩니다. 생성 요청에는 누락된 설정 오류가 표시됩니다.
온톨로지, 개요, 생성 상태·결과는 PostgreSQL 볼륨에 저장됩니다.

```sh
docker compose --env-file .env.local logs api
docker compose --env-file .env.local down
```

`.env.local` 변경 후에는 `docker compose --env-file .env.local up -d --force-recreate api`로
API 컨테이너에 새 설정을 적용합니다. Compose의 서비스별 DB 설정이 로컬 개발용 `DATABASE_URL`을
컨테이너 내부 주소로 덮어씁니다.

## 사용자 흐름

1. 한국어 주제·요청·원고 입력 → Workers AI가 6~30장 개요 자동 생성
2. 페이지별 제목·핵심 메시지·주요 내용 수정 → 확정
3. Jev가 확정 개요의 표현 유형을 예상 → 해당 유형을 지원하는 최신 디자인의 슬롯 제약으로 LLM 출력 스키마 구성
4. LLM이 페이지 순서대로 문구 생성 → 수치 누락·변경·추가 검사 → Jev가 확정 개요와 문구의 **내용 보존 여부 검수** → **최종 문구**의 대표 표현 유형 하나 분류
5. 사용 여부·최종 지원 유형·슬롯·용량으로 후보 제한 → Jev Choice로 선택·확률순 표시
6. 전체 슬라이드의 한국어 폰트 로딩·잘림·슬롯 겹침 검사 → 모두 통과하면 완료

개요 사전 판단은 구현 중 사용자 승인을 받아 추가했다. 예를 들어 도입으로 예상되면 본문 0~1개,
최대 120자로 LLM 출력 스키마를 제한한다. 사전 판단은 디자인 선택을 확정하지 않는다.
최종 분류가 달라지면 그 최종 유형으로 후보를 다시 제한하며, 유효 후보가 없으면 오류를 표시한다.
내용 보존 검수도 실제 문구에서 목표를 달성 결과로 바꾸거나 새 사실을 추가한 사례를 확인한 후
사용자 승인을 받아 추가했다. Jev의 적합/부적합 Choice가 부적합이면 디자인을 선택하지 않고
실패 처리한다. 자동 문구 재작성은 수행하지 않는다. 숫자는 출력 스키마와 서버에서 함께 제한한다.
초기 ‘도입’·‘강조’ 설명도 승인한 의미 경계를 반영했다. 목록의 도입 지원은 추가하지 않았다.

Jev의 사전 판단·최종 유형 분류, LLM 출력 스키마, 후보별 선택 확률, 사용한 온톨로지 버전,
실제 평가 요청·응답은 페이지별
**Jev 판단 근거**에서 확인합니다. 확률은 제공된 후보 사이의 상대적 선택 확률입니다.

실패하면 이유를 표시하고 개요를 보존합니다. 개요를 수정·확정하여 수동 재생성할 수 있습니다.
잘못된 모델 출력을 자동으로 재작성하거나 다른 모델로 대체하지 않습니다.
수치의 보존과 새 수치 추가를 코드로 검사하고, 의미·고유명사·목표와 결과의 구분·근거 없는
추가 사실은 Jev로 검수합니다. 실제 모델 검증 기록에는 사람이 확인한 문구 결과도 포함합니다.

온톨로지에서는 표현 유형의 의미, 디자인 용도, 다중 지원 관계, 슬롯 설명·용량을 수정합니다.
변경 전·후 검수 후 저장·사용 전환하면 **이후 시작한 생성**부터 반영됩니다. 생성마다 스냅샷을
저장하므로 이미 생성된 결과와 진행 중인 작업은 변경되지 않습니다.

## 확정한 기술 구성

- FE: 별도 Next.js 16 App Router 앱 2개, React 19, TypeScript, Tailwind CSS 4,
  shadcn/ui **Base UI**, TanStack Query, React Hook Form, Zod
- UI 컴포넌트는 앱별 관리. FastAPI OpenAPI에서 `openapi-typescript`로 API 타입 생성
- BE: Python 3.13, `fastapi[standard-no-fastapi-cloud-cli]`, Uvicorn,
  SQLModel 비동기 세션, Psycopg 3, PostgreSQL 18, `httpx2`, Pydantic Settings
- 관리·검증: pnpm workspace, uv, Biome·TypeScript, Ruff, pytest·pytest-asyncio, Playwright
- Workers AI: `@cf/ibm-granite/granite-4.0-h-micro`
- Jev: `jev-1.13.0` 고정. 모델명은 `.env.local`에서 변경 가능
- 로컬 전용·인증 없음. 웹 앱은 같은 출처의 `/api` 프록시로 FastAPI에 연결
- 단일 Uvicorn 프로세스에서 생성 작업 실행. 서버 종료·재시작으로 중단된 생성은 실패 처리
- DB는 초기 테이블 자동 생성 방식. 스키마 변경 시 기존 DB 갱신은 별도 처리 필요

## 초기 온톨로지

고정 스타일: 16:9 / 흰 배경 / 남색 글자 / 청록 강조 / 앱에 포함한 Noto Sans KR.
제목 최대 48자, 핵심 메시지 96자, 본문 소제목 32자. 글자 수는 공백·문장부호를 포함한
Unicode 코드 포인트 수입니다. 운영자는 고정 레이아웃의 최대 수용 범위 안에서 제약을 조정합니다.

| 디자인 | 지원 유형 | 본문 블록 수 | 블록 내용 상한 |
|---|---|---:|---:|
| 표지 | 도입 | 0~1 | 120자 |
| 핵심 메시지 | 강조, 요약·행동 제안 | 0~2 | 160자 |
| 목록 | 나열, 비교, 요약·행동 제안 | 2~6 | 100자 |
| 비교 | 비교 | 2 | 180자 |
| 과정 | 순서·과정, 나열 | 3~5 | 80자 |
| 마무리 | 요약·행동 제안, 강조 | 0~2 | 120자 |

후보 제한과 웹 배치 검증은 같은 슬롯 정의를 사용합니다. 렌더러는 1280×720 기준에서 배치하고,
열람 화면만 화면 폭에 맞춰 비율을 조정합니다. 완료 판정은 폰트를 로딩한 브라우저에서
원본 크기의 **모든 페이지**를 실제 측정한 후 서버에 제출합니다. 브라우저를 닫아도 생성은
진행되며, 다시 열면 배치 검사를 이어갑니다.

## 로컬 개발

```sh
pnpm install --frozen-lockfile
uv sync --project services/api --frozen
docker compose --env-file .env.local up -d db
```

각 명령을 별도 터미널에서 실행합니다. 백엔드 명령은 `services/api`에서 실행합니다.

```sh
# services/api
uv run uvicorn app.main:app --reload --port 8000
```

```sh
# 저장소 루트
pnpm dev:presentation
pnpm dev:ontology
```

API 명세·타입 갱신:

```sh
# services/api
uv run export_openapi.py
```

```sh
# 저장소 루트
pnpm api:types
```

## 자동 검증

테스트 전용 Compose는 별도 프로젝트·볼륨·포트에서 실제 PostgreSQL·두 웹 앱·FastAPI를
연결합니다. 외부 모델 HTTP 응답만 테스트 픽스처로 대체합니다. 운영 실행 경로에는 모의 모델이나
자동 대체 경로가 없습니다.

```sh
pnpm install --frozen-lockfile
docker compose -p poc-test -f compose.yaml -f compose.test.yaml up --build -d --wait
pnpm exec playwright install chromium
pnpm test:e2e
pnpm check
pnpm typecheck
pnpm build
```

BE 검증은 `services/api`에서 실행합니다. 테스트 DB 기본 주소는 `localhost:55432`이고,
각 테스트가 별도 임시 PostgreSQL 스키마를 만들고 정리합니다.

```sh
uv run pytest
uv run ruff check app tests export_openapi.py
uv run ruff format --check app tests export_openapi.py
```

`TEST_DATABASE_URL`로 다른 테스트 DB를 지정할 수 있습니다.

## 실제 모델 E2E

API 키 설정 및 모델 호출 승인을 받은 뒤 일반 Compose 환경에서 실행합니다.
개요와 슬라이드를 **두 번 생성**하므로 모델 API 사용량이 발생합니다. 자동 재시도하지 않습니다.
온톨로지를 웹에서 검수·변경하고 다음 생성에 전달되는지 확인한 뒤 기존 설정을 복원합니다.

```sh
REAL_MODELS=1 \
PRESENTATION_URL=http://127.0.0.1:3000 \
ONTOLOGY_URL=http://127.0.0.1:3001 \
API_URL=http://127.0.0.1:8000 \
pnpm exec playwright test e2e/real-models.spec.ts
```

실제 모델 사용 여부는 테스트 픽스처 검증과 별도로 기록합니다. `playwright-report`에서 실행 결과와
`real-model-evidence` 첨부를 확인할 수 있습니다.

### 공식 자료

- [Workers AI 가격](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- [Granite 모델](https://developers.cloudflare.com/workers-ai/models/granite-4.0-h-micro/)
- [TypeSafe 공식 API](https://docs.typesafe.ai/api)
- [Jev Choice](https://docs.typesafe.ai/primitives/choice)
- [FastAPI Cloud CLI 제외 설치](https://pypi.org/project/fastapi/#without-fastapi-cloud-cli)
