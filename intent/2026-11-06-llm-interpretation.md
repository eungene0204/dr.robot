# Intent: OpenRouter LLM 요구 해석 활성화

- 작성일: 2026-11-06
- 요청자: 사용자
- 작성자: Claude Code
- 상태: 완료
- 요청자/제품 책임자 검토: 미검토

## 문제와 이유

LLM 설정이 비어 있어 상담 문장을 규칙으로만 해석했다. 요청자가 OpenRouter 키와 모델(nvidia/nemotron-3.5-super-vl:free, 대체 nvidia/nemotron-3-ultra-550b-a55b:free)을 제공했다.

## 기대 결과

서버가 .env를 읽어 LLM 요구 해석을 사용한다. LLM 해석이 문장에 명시된 용도·예산·해상도·옵션을 바꾸지 않는다.

## 범위

- 포함: .env 저장(.gitignore 대상), npm run server의 .env 로드, 추론 모델의 reasoning 비활성화, 대체 모델 허용을 위한 require_parameters 제거(출력은 스키마 검증 유지), 해석 병합 규칙(mergeInterpretation).
- 제외: LLM으로 질문에 답하기, 부품·가격·FPS 제안.

## 제약

키는 브라우저 변수(VITE_)나 문서에 넣지 않는다. LLM 결과는 검증 후에만 쓴다.

## 수용 기준

- [x] /api/health가 llm:true를 반환한다.
- [x] '200만원 이하 adobe용 견적'이 LLM 사용 시에도 editing, 2,000,000원이다.
- [x] 규칙이 용도를 못 찾는 문장은 LLM 용도를 쓰고, 예산을 묻는 질문은 제외한다.

## 가정과 열린 질문

- 가정: 해상도·화이트·Wi-Fi·OS는 문장 규칙 값을 쓴다. LLM은 문장에 없는 해상도를 임의로 고르는 경향이 확인되었다.
- 질문: LLM 기반 질문 답변 도입 여부는 미정.

## 구현 및 검증 결과

- 관련 코드·문서: backend/server.mjs, src/engine.mjs(mergeInterpretation), package.json, .env, tests/engine.test.mjs
- 수용 기준별 검증: 실제 OpenRouter 호출에서 기본 모델은 reasoning 활성 시 content가 null(토큰을 추론에 소진), 비활성 시 약 1초 응답. 대체 모델은 require_parameters에서 404, 제거 시 응답. 재시작한 API에서 adobe → editing·200만원, '5060ti 게임 4K 견적' → gaming·4K·예산 없음·models 5060ti, '스타크래프트 할 PC 150만원' → gaming. 전체 테스트 88개 통과.
- 남은 항목: 무료 모델의 가용성·속도 제한은 미확인. 브라우저 화면의 확인 질문 표시는 미확인.
