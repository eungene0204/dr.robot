# Intent: 수집 파이프라인을 Python(pcquote)으로 옮기기

- 작성일: 2026-11-07
- 요청자: 매장 운영자
- 작성자: Claude
- 상태: 진행 중 (전환 전 섀도 대조 단계)
- 요청자/제품 책임자 검토: 미검토

## 문제와 이유

[서버 통합](2026-11-06-single-server.md) 뒤에도 매일 밤 수집은 Node 배치(`pipeline/`)로 남아 Node와 documents.db가 필요했다. 요청자는 "pcquote 4단계는 지금 할 수 없는 일인가?"라고 물었고, 진행 방식(파서 대조 → 섀도 실행 → 전환)을 듣고 "응 진행 해줘"라고 답했다.

## 기대 결과

매일 0시 수집(신제품 발견, 가격·사양, Blender 벤치마크, 인기 순위)을 Python 수집기가 한다. 결과는 PostgreSQL에 바로 들어가고 서버가 그대로 쓴다. 수집 규칙과 결과는 Node 수집기와 같다.

## 영향받는 사용자와 시스템

매장 직원(견적에 쓰이는 카탈로그), buildmate `pipeline/`(전환 후 미사용), pcquote `collector`(신규), PostgreSQL(수집 테이블 추가), LaunchAgent `com.drrobot.daily-components`(전환 시 실행 명령 변경).

## 범위

- 포함: 다나와 상품·검색·카테고리 파서, 인기 순위, 사양 파싱, 등록월, 신제품 발견(재개 가능), 가격 수집과 30% 변동 검수, Blender 다운로드·집계·정규화, 스냅샷 생성·발행, 일일 작업·보고서, 수동 실행, 원문 캐시와 조건부 요청, Node 상태 가져오기, 섀도 대조, 전환 명령.
- 제외: 네이버 교차 가격(키가 없어 Node에서도 실행되지 않음, 미이식), 일회성 정비 스크립트(`scripts/enrich-cooling-types.mjs`, `refresh-popularity.mjs`, `refresh-current-quote-prices.mjs`, `compare-recommendation-basis.mjs`: 각각 파서·일일 발견·서버 가격 갱신이 대신함), 상주 스케줄러(`scheduler.mjs`: LaunchAgent가 대신함).

## 제약

- 수집 규칙 유지: robots.txt(와일드카드·Crawl-delay), 출처당 2초 이상, 허용 호스트, 리디렉션 금지, 재시도 3회와 Retry-After 60초 초과 시 보류, 8MB 제한, 자기 식별 User-Agent.
- 섀도 대조는 Node가 받은 원문을 재생해서 한다. 다나와에 같은 요청을 두 번 보내지 않는다.
- 전환 전에는 수집기가 서버 카탈로그(parts)를 바꾸지 않는다.
- 전환(LaunchAgent 변경)은 실행 중인 시스템 설정 변경이므로 요청자 확인 후 한다.

## 수용 기준

- [x] 같은 원문에서 Python 파서 결과가 JS와 같다(원문 캐시 전체).
- [x] 같은 원문을 재생한 Python 수집 결과(카탈로그)가 Node 결과와 같다(섀도). 남은 차이는 모두 Node 쪽 원인으로 설명됨(아래)
- [x] 전환 전 수집기는 서버 카탈로그를 바꾸지 않고, 전환 후에는 서버가 수집기 결과만 쓴다(테스트).
- [x] 전환 후 LaunchAgent가 Python 일일 작업을 실행하도록 등록됨(요청자 지시 "바로 전환 하자"). 실제 0시 실행은 미확인

## 가정과 열린 질문

- 가정: 원문 캐시는 PostgreSQL에 zlib 압축으로 둔다(조건부 요청·재파싱용).
- 가정: 프로세스 잠금은 PostgreSQL advisory lock으로 바꾼다(프로세스가 죽으면 자동 해제).
- 질문: 없음(전환 시점은 요청자가 "바로 전환 하자"로 결정).

## 구현 및 검증 결과

- 관련 코드: pcquote `backend/src/pcquote/collector/`(parse, jsre, client, store, expand, blender, run, daily, bootstrap, shadow, `__main__`), `danawa.py`(수집기 클라이언트·파서 사용), `service.py`(가격 갱신을 `price_observations`·`review_queue`에도 기록), `importer.py`·`pipeline.py`·`main.py`(전환 후 동작), `db.py`(수집 테이블), `scripts/{dump_js_parsers.mjs,compare_parsers.py,run_collector_daily.sh}`, `tests/test_collector.py`.
- 파서 대조(2026-11-07): buildmate 원문 캐시 14,349건을 지금 JS 파서와 Python 파서에 같이 넣음. 상품 13,553건(사양·가격·등록월·오류), 벤치마크 이름·신제품 판정 12,271건, 검색 576건, 인기 순위 10건 모두 차이 0건. 대조 중 실행 중이던 수집이 원문을 바꾼 220건은 제외. Python 56초, JS 6분 24초.
- 섀도 실행(2026-11-07 00:3x, Node 11-06 일일 수집 종료 직후): Node 상태를 가져와 Node가 받은 원문을 재생(누락 0, 네트워크 없음, 53초). 상품 6,847개 목록 일치. 차이와 원인:
  - 사양 약 400건(슬롯 276·내장 그래픽 78·전력 21·TDP 19·소켓 6·코어 2): Node 프로세스가 19:49에 시작해 22:03에 고친 파서 이전 코드로 돌았음. 지금 JS 파서는 같은 원문에서 Python과 같은 값(dw-111134015: LGA1700·14코어·181W, dw-100383200: 슬롯 4).
  - 사양 출처 시각·인기 순위·출처 카테고리·냉각 근거 6건: 이전 Node 서버의 견적 시 가격 갱신이 오래된 카탈로그 레코드로 `product_facts`를 덮어씀([기록](../troubleshooting.md#2026-11-07-stale-facts-from-live-refresh)). Python은 원문을 다시 파싱한 값.
  - 벤치마크 176건: 소수점 끝자리(상대 2×10⁻¹⁶)만 다름. 집계 Python 버전 차이. 정규화 점수 676개 모두 같음.
- 테스트: pcquote `uv run pytest` 118개 통과(수집기 23개 추가). 서버 재시작 후 5588 경유 견적·교체·저장 확인, 실시간 가격 갱신 실제 요청 2회(688,990원, 두 번째는 2초 간격 대기) 확인.
- 전환(2026-11-07 00:4x KST):
  1. `bootstrap --with-cache`: Node 수집 상태(제품 6,845·가격 관측 13,728·벤치마크 676·검수 67·작업 36)와 원문 캐시 14,349건(PostgreSQL 820MB) 이전, 2분.
  2. `cutover`: 카탈로그 소유자를 수집기로 변경.
  3. `run --reparse-cache --prices-only`: 24시간 안 원문으로 재파싱해 첫 발행(1분, 부분 성공. 가격 6,779, 오류 55건은 Node 실행 때와 같은 상품 페이지 구조 불일치). 사용 가능 부품 4,705 → 4,968(옛 파서로 빠졌던 사양 복구, 예: dw-111134015 LGA1700·14코어·181W).
  4. 서버 확인: catalog-source가 collector, 문서 동기화 `imported: null`(buildmate 미참조), 수집 현황이 PostgreSQL 문서에서 나옴, 5588 경유 견적·저장 정상.
  5. LaunchAgent `com.drrobot.daily-components`: 실행 명령을 `pcquote/backend/scripts/run_collector_daily.sh`로, 로그를 `pcquote/backend/data/daily.launchd*.log`로 변경 후 재등록. 원래 plist는 `pcquote/backend/data/com.drrobot.daily-components.node.plist.bak`. 환경 변수 없는 셸에서 스크립트 `--check` 정상.
  6. buildmate `npm run pipeline*`가 Python 수집기를 실행하도록 변경(`pipeline:schedule`·`pipeline:popularity` 제거, `pipeline:publish` 추가). `npm test` 79개 통과.
- 되돌리기: 백업 plist로 LaunchAgent 복원 후 PostgreSQL `documents`에서 `catalog-owner` 행 삭제. Node `pipeline/` 코드는 그대로 남아 있다.
- 남은 항목: 첫 야간 실행(2026-11-08 00:00) 결과 미확인. 네이버 교차 가격 미이식. Node `pipeline/` 코드·테스트 삭제는 하지 않음(복구 경로).
