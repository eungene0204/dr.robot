# Intent: 서버를 pcquote(Python) 하나로 합치기

- 작성일: 2026-11-06
- 요청자: 매장 운영자
- 작성자: Claude
- 상태: 완료
- 요청자/제품 책임자 검토: 미검토

## 문제와 이유

[pcquote 엔진 연동](2026-11-06-pcquote-engine.md) 후에는 buildmate Node 서버(8001)와 pcquote 서버(8765)를 둘 다 띄워야 했다. 요청자: "왜 두 개의 서버가 필요한 거야?", "하나로 합쳐". 합치는 방향으로 "서버를 Python으로 옮김"(기획서 스택 FastAPI + PostgreSQL)을 골랐다.

## 기대 결과

`npm run server` 하나로 상담 화면이 모두 동작한다. 견적 생성·부품 교체·저장·이력·설정·요구 해석·질문 답변·수집 현황이 그대로 된다. 기존 견적·설정·상담 상태는 남아 있다.

## 영향받는 사용자와 시스템

매장 직원 상담 화면, buildmate `backend/` Node 서버(삭제), pcquote FastAPI(화면 API 추가), PostgreSQL(테이블 추가), buildmate.db(이전 후 미사용).

## 범위

- 포함: 화면이 쓰는 API 15개를 pcquote로 이전한다(응답 형식 유지). 데이터 정책·요구 해석·LLM 답변 하네스·다나와 가격 갱신(±30% 검수)을 Python으로 옮긴다. buildmate.db 데이터를 옮긴다. 발행 카탈로그를 PostgreSQL로 자동 가져온다. Node 서버와 연동 어댑터를 지운다. 빌드된 화면을 같은 서버에서 내보낸다.
- 제외: 수집 파이프라인(Node 배치, LaunchAgent 실행)과 화면 코드의 Python 이전. 화면이 쓰지 않는 `/api/recommend`(내장 엔진)·`/api/prices/history`·`/api/knowledge*`.

## 제약

- 응답 형식이 같아야 화면을 고치지 않는다.
- 데이터 정책과 요구 해석은 JS와 같은 결과를 내야 한다. 화면도 같은 규칙을 로컬에서 쓴다.
- 수집 규칙(robots.txt, 출처당 2초, 허용 호스트)과 30% 가격 변동 검수는 그대로 지킨다.

## 수용 기준

- [x] 8001 서버 하나로 5588 화면의 모든 API가 응답한다.
- [x] 사무용 100만원 요청이 실제 다나와 가격 갱신을 거쳐 3안을 내고, 견적을 저장할 수 있다(이전 연동에서는 저장이 거부됐다).
- [x] 기존 견적 4건·매장 설정·테마·진행 중 상담이 보인다.
- [x] 데이터 정책 판정과 요구 해석이 JS와 같다.
- [x] LLM 평가 7문항이 통과한다.
- [x] buildmate·pcquote 테스트가 통과한다.

## 가정과 열린 질문

- 가정: 수집 파이프라인은 서버가 아닌 배치라 이번에 옮기지 않는다. 서버는 documents.db를 읽기 전용으로 쓴다.
- 질문: 없음

## 구현 및 검증 결과

- 관련 코드·문서: pcquote `backend/src/pcquote/{main,service,screen,policy,consult,llm,danawa,importer,pipeline}.py`, `scripts/{migrate_buildmate_db,llm_eval,seed_from_buildmate}.py`, `tests/{test_api,test_ported}.py`. buildmate `package.json`, `tests/ui.test.mjs`, `tests/ontology.test.mjs`, 문서.
- 수용 기준별 검증:
  - 5588 경유: health·catalog(13MB, 0.016초)·pipeline/discovery/prices·settings·quotes·state 응답 확인.
  - 실제 흐름: 요구 해석(OpenRouter, 0.9초) → 견적(다나와 8건 갱신, 15.9초, 3안 모두 Intel·예산 +5% 이내·BIOS 확인 표시) → 대체 후보 218개 → 재계산 통과 → 견적 저장 201 → 시험 견적 삭제 → 질문 답변(LLM, 6.1초, 검사 통과).
  - 데이터 이전: 견적 4·설정 3·LLM 사용량 13건. 재실행 시 0건(중복 없음).
  - 일치 검사: 부품 6,829개 × 2개 시각에서 정책 판정 차이 0건, 문장 16개 요구 해석 차이 0건.
  - `uv run python scripts/llm_eval.py` 7/7, pcquote `uv run pytest` 95개, buildmate `npm test` 79개 통과, `npx vite build` 성공.
- 남은 항목: 실제 브라우저로 화면을 직접 조작한 확인은 하지 않았다. 수집 파이프라인은 아직 Node가 필요하다.
