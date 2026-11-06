# pcquote — AI PC 견적 추천 시스템

용도와 예산을 넣으면 호환성이 검증된 1·2·3순위 조립 견적을 만든다. 기획서는 [docs/plan.md](docs/plan.md), 구현 결정은 [docs/architecture.md](docs/architecture.md), 진행 상황은 [project_plan.md](project_plan.md)에 있다.

이 서버 하나가 Dr.Robot 상담 화면(`../buildmate`)의 API, 추천 엔진, 견적 저장을 모두 맡는다.

## 서버 실행

PostgreSQL 16과 uv가 필요하다.

```bash
createdb pcquote && createdb pcquote_test
cd backend
uv sync
uv run python scripts/seed_from_buildmate.py      # 발행 카탈로그 가져오기(이후에는 서버가 자동으로 가져옴)
uv run python scripts/migrate_buildmate_db.py     # 처음 한 번: buildmate.db 견적·설정 이전
uv run python -m pcquote.collector bootstrap --with-cache && uv run python -m pcquote.collector cutover   # 처음 한 번: 수집 상태 이전
uv run uvicorn pcquote.main:app --host 127.0.0.1 --port 8001   # buildmate에서는 npm run server
```

화면: `../buildmate`에서 `npm run dev` 후 `http://127.0.0.1:5588`, 또는 `npm run build` 후 `http://127.0.0.1:8001/`.

DB 주소는 `DATABASE_URL`(기본 `postgresql+psycopg:///pcquote`)로 바꾼다. OpenRouter 키(`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`)는 `backend/.env`, 없으면 `../buildmate/.env`에서 읽는다. buildmate 위치는 `BUILDMATE_ROOT`로 바꾼다.

```bash
curl -s localhost:8001/api/recommend -H 'Content-Type: application/json' \
  -d '{"budget": 1500000, "uses": ["gaming", "editing"], "white": true}'
```

## 테스트

```bash
cd backend && uv run pytest
```

API 테스트는 `pcquote_test` DB의 테이블을 지우고 다시 만든다(`TEST_DATABASE_URL`로 변경 가능).

## 수집

```bash
cd backend
uv run python -m pcquote.collector daily          # 매일 0시 LaunchAgent가 scripts/run_collector_daily.sh로 실행
uv run python -m pcquote.collector run --expand   # 수동 수집(신제품 발견 포함)
```
