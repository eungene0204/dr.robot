# dr.robot

PC 매장 직원용 조립 상담 MVP. 한국어 요청 입력 → 3안 비교 → 부품 교체 및 규칙 재검증 → 견적서 인쇄/PDF·링크 공유 흐름을 제공합니다.

**현재 기본 카탈로그의 가격·스펙·성능 지수는 시연 데이터입니다. 실제 시세·실측 FPS·조립 가능성을 보증하지 않습니다.** 비공개 Sites 배포는 정적 데모이며 API 및 고객 정보 서버 저장을 포함하지 않습니다.

## 실행

Node.js 24 이상이 필요합니다.

```sh
npm install
npm run dev
```

http://127.0.0.1:5173 에서 사용합니다. 정적 데모는 API 없이도 작동하며 상담 이력과 설정을 현재 브라우저 localStorage에 저장합니다.

서버 영구 저장과 선택적인 OpenRouter 요구 분석을 켜려면 별도 터미널에서 실행합니다.

```sh
cp .env.example .env
# .env에 키와 JSON Schema 지원 모델 ID 설정 (선택)
node --env-file=.env backend/server.mjs
```

키가 없으면 로컬 규칙으로 요구를 분석합니다. API 키는 서버에서만 사용합니다. 로컬 서버는 127.0.0.1에만 바인딩합니다. Vite가 `/api`를 8000 포트로 프록시합니다. OpenRouter 구조화 출력의 로컬 타입·범위 검증과 1회 재시도, 선택적인 모델 폴백, 토큰·비용 로그를 포함합니다. UI에서 고른 조건이 자연어 해석보다 우선합니다.

## 구현한 동작

- 한국어 예산·용도·해상도·색상 분석, 직접 수정 가능한 필수 조건
- 게임·편집·사무·로컬 AI별 후보 필터링 및 유효 조합 전수 탐색
- 균형안 95~100%, 강화안 최대 110%(직접 허용 시), 절약안 80~90% 목표
- 목표 예산 구간에 조합이 없으면 대체안 표시; 강화안은 균형안보다 높은 성능 지수일 때만 제공
- 동일 조합 중복 방지. 부품 공유율 50% 강제 조건은 성능과 무관한 교체를 유발하므로 적용하지 않음
- 소켓·BIOS 목록·RAM·보드·GPU 공간/전원·쿨러·SSD·전력 및 고객 필수 조건 검사
- 부품별 교체, 가격·성능 지수·호환성 재계산, 오류/예산 초과 시 발행 차단
- 견적서 인쇄/PDF 저장, 발행·만료 시각, 시연 기준·가상 가격 고지
- URL에 선택한 부품 ID·요구·매장명·고객명을 넣는 공유 링크. 민감 정보 입력 금지
- 브라우저 상담 이력, 매장명·조립비·유효기간, 부품 라이브러리·상세 스펙
- 로컬 Node HTTP API 및 SQLite 견적/LLM 사용량 영구 저장

고객 보기에서는 직원용 입력과 내비게이션을 숨깁니다. 인증이나 보안 경계가 아닙니다. 매입가·마진은 저장/표시하지 않습니다.

## API

| 경로 | 동작 |
| --- | --- |
| GET /api/health | 연결, LLM 구성 및 데이터 모드 |
| POST /api/requirements | `{text}` → 구조화 요구 및 최대 3개 질문 |
| GET /api/catalog | 카탈로그 조회 |
| POST /api/recommend | `{requirement, settings:{assembly}}` → 3안 |
| POST /api/quotes | `{plan, req, settings, customerName}` → 서버 재검증 후 저장 |
| GET /api/quotes | 저장된 최근 100건 |

서버는 클라이언트 가격을 신뢰하지 않고 카탈로그 ID로 가격과 스펙을 다시 조회합니다. 서버 저장과 브라우저 이력은 별도로 유지됩니다. 다중 사용자·다중 매장 운영 전 인증, 테넌트 분리, 권한, 저장/삭제 정책을 추가해야 합니다.

## 거래처 데이터 반입

허가받은 거래처 데이터를 `src/catalog.mjs`의 부품 형식과 같은 JSON 배열로 변환해 사용합니다. 각 부품에는 `id`, `category`, `name`, `price`, `inStock`, `verified: true`, `sourceUrl`(HTTPS), `observedAt` 및 카테고리 필수 스펙이 있어야 합니다.

```sh
node backend/import-catalog.mjs /absolute/path/supplier.json
CATALOG_PATH=backend/data/catalog.json node --env-file=.env backend/server.mjs
```

검수/필수 속성 누락 및 기존 가격 대비 30% 이상 변동은 `.quarantine.json`으로 분리합니다. 담당자가 확인한 가격 변동에는 `priceChangeApproved: true`를 지정합니다. 검수 상품이 0개이면 이전 정상 파일을 유지합니다. 파일은 원자적으로 교체됩니다.

**반입 카탈로그는 현재 서버 API 전용입니다. 배포된 화면과 브라우저 추천은 기본 시연 카탈로그를 사용합니다.** 내장 `g0`, `o0`, `o1` ID는 각각 내장 그래픽, OS 미포함, Windows 포함용입니다. 실제 카탈로그 전환 전 제품별 소켓/BIOS와 규칙 입력값 검수가 필요합니다.

## 검증

```sh
npm test
npm run build
```

엔진 테스트와 HTTP API 통합 테스트가 포함됩니다. 부품 교체 오류, 예산 범위, 미검수 상품 제외, 중복 방지, 강화안 성능, 요구 파싱, API 저장 및 변조 요청 거부를 확인합니다. 현재 환경에는 연결된 브라우저가 없어 실제 브라우저 렌더링과 인쇄 레이아웃은 검증하지 못했습니다.

## 아직 필요한 운영 기능

- 다나와/쇼핑몰 자동 수집: 약관·접근 허용 확인 및 실제 공급 소스 확보 후 어댑터 연결
- 실측 벤치마크와 SKU별 제조사 원문 근거, QVL·슬롯 공유·수랭 간섭 등 세부 규칙
- 출고 BIOS가 불명인 상품의 미확인 상태 처리와 검수 운영
- 실제 시세 DB, 발행 직전 재고·가격 확인, 데이터 신선도 차단 정책
- 기획서의 Next.js/FastAPI/PostgreSQL 기반 다중 매장 서비스로 전환
- PDF 파일 서버 생성, 접근 권한이 있는 짧은 공유 링크, 로고 업로드, 카카오톡 발송
- 대화형 부분 수정, 매입가·마진·재고, 가격 이력, 기존 부품 재사용, CRM·결제

현재 구현은 React/Vite + Node/SQLite로 첫 상담 사이클을 검증하는 MVP입니다. 실제 수집·실사용 준비가 끝난 서비스로 오인하지 않도록 모든 결과에 시연 상태를 표시합니다.

OpenRouter 연동 참고: https://github.com/OpenRouterTeam/docs/blob/main/guides/features/structured-outputs.mdx
