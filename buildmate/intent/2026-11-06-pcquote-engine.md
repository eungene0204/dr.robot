# Intent: 기존 상담 화면에서 pcquote 추천 엔진 사용

- 작성일: 2026-11-06
- 요청자: 매장 운영자
- 작성자: Claude
- 상태: 완료 (같은 날 [서버 통합](2026-11-06-single-server.md)으로 대체: 연동 어댑터와 Node 서버 삭제)
- 요청자/제품 책임자 검토: 미검토

## 문제와 이유

사무용 PC 견적을 요청해도 AMD CPU만 추천된다. buildmate 엔진은 제조사 CPU 지원 목록이 등록된 보드만 쓰는데, 등록된 보드가 MSI PRO B650M-A WIFI 1개뿐이다. 새로 만든 pcquote 엔진은 칩셋 세대 규칙과 인기도 반영으로 Intel·AMD를 모두 추천한다. 요청자: "pcquote를 쓰면 되잖아", "기존 화면에 pcquote를 사용해".

## 기대 결과

기존 buildmate 상담 화면에서 견적을 요청하면 pcquote가 고른 3안이 나온다. 사무용 요청에도 Intel CPU 견적이 나올 수 있다. 부품 교체, 호환성 표시, 견적 확정도 pcquote 규칙으로 동작한다.

## 영향받는 사용자와 시스템

매장 직원 상담 화면, buildmate 서버 `/api/recommend/fresh`·`/api/health`·새 프록시 API, pcquote FastAPI(`/api/recommend`, `/api/quotes/evaluate`, `/api/quotes/alternatives`, 새 `/api/admin/prices`).

## 범위

- 포함: live 모드 견적 생성을 pcquote로 전환한다. 선택된 부품의 오래된 가격을 buildmate의 기존 다나와 갱신 경로로 갱신해 pcquote DB에 반영하고, 다시 추천한다. 부품 교체 시 재검사와 대체 후보 호환 표시를 pcquote로 처리한다. BIOS 업데이트가 필요한 조합은 통과로 보되 "출고 전 확인"으로 표시한다. 견적 상한은 pcquote의 예산 +5%를 따른다.
- 제외: demo 모드(기존 엔진 유지), LLM 요구 해석 변경, pcquote 화면(Next.js), pcquote 수집기.

## 제약

- pcquote 서버가 꺼져 있으면 조용히 기존 엔진으로 돌아가지 않고, 연결 오류를 보여 준다. 두 엔진 결과가 섞이면 원인 추적이 어렵다.
- pcquote 부품 id가 buildmate 카탈로그에 없으면 그 안을 보여 주지 않는다.
- 가격 갱신에 실패한 부품은 다음 추천에서 제외한다.

## 수용 기준

- [x] pcquote가 켜진 live 모드에서 "조용한 사무용 PC, 엑셀과 POS, 100만 원" 요청 시 3안이 나오고, Intel CPU가 포함될 수 있다(카탈로그 상태에 따라 다름).
- [x] 견적 안의 호환성 검사는 pcquote 결과이며 BIOS 경고는 "출고 전 확인"으로 보인다.
- [x] 부품을 교체하면 pcquote 기준으로 총액·검사가 다시 계산된다.
- [x] 예산 +5% 이내 견적은 확정할 수 있다.
- [x] pcquote 서버가 꺼져 있으면 연결 오류 메시지가 나온다.
- [x] 기존 테스트가 통과한다.

## 가정과 열린 질문

- 가정: 예산 미지정 요청은 pcquote가 처리할 수 없으므로 예산을 묻는 안내를 보여 준다.
- 가정: OS 포함 요청은 OS 가격을 뺀 금액을 pcquote 예산으로 보낸다.
- 질문: 없음

## 구현 및 검증 결과

- 관련 코드·문서: `backend/pcquote-engine.mjs`, `backend/server.mjs`, `src/main.jsx`, `src/alternatives.mjs`, `tests/pcquote-engine.test.mjs`, pcquote `backend/src/pcquote/main.py`
- 수용 기준별 검증:
  - 사무 100만원: buildmate 데이터 사본(`BUILDMATE_DATA_DIR`)으로 띄운 live 서버 + 실제 pcquote에서 3안 모두 Intel(i7-14700K, i5-14600K, i7-13700 + B760M DS3H D4), 전 부품 `usablePart` 통과, 총액 ≤ 예산 +5%. 게임 QHD 250만·편집 300만·화이트 150만도 3안, 발행 차단 부품 없음, 1.1~9.2초.
  - BIOS 경고: 실제 응답에서 보드 `biosPreparation` "출고 전 확인: B760 칩셋은 인텔 14세대를 BIOS 업데이트 후 지원…" 확인. UI 테스트에서 화면 표시 확인.
  - 부품 교체: 실제 서버에서 `/api/quotes/alternatives`(보드 25개, 87ms)와 교체 후 `/api/quotes/evaluate`(85ms) 확인. UI 테스트에서 대체 후보 클릭 → evaluate 호출 → 보드 변경·BIOS 표시 해제 확인.
  - +5% 발행: UI 테스트에서 예산보다 크고 +5% 이하인 견적의 발행 버튼 활성 확인.
  - pcquote 정지: `/api/recommend/fresh` 503 "pcquote 추천 서버(http://127.0.0.1:8765)에 연결할 수 없습니다." 확인.
  - `npm test` 102개 통과, `npx vite build` 성공, pcquote `uv run pytest` 76개 통과.
- 남은 항목: 실제 5588 화면 수동 확인 미실행. 운영 중인 buildmate 서버는 재시작해야 새 엔진을 쓴다. MSI B850M 박격포 등 일부 인기 보드는 buildmate 스냅샷에 슬롯 정보가 없어 다음 수집 전까지 제외된다.
