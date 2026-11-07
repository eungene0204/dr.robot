---
name: quote-eval
description: 고객 예상 요청 시나리오로 견적 파이프라인(요구 해석 → 추천 엔진)을 평가한다. "견적 테스트", "견적 정확도 확인", "시나리오 평가", 엔진·해석·카탈로그를 바꾼 뒤 회귀 확인에 사용.
---

# 견적 시나리오 평가

`cases.json`의 고객 문장을 상담 화면과 같은 경로(LLM 요구 해석 → 화면 요구 병합 → `screen.recommend_fresh`)로 돌리고, 결과를 케이스 기대값과 매장 규칙으로 판정한다. 다나와 가격 갱신은 하지 않으므로 저장된 가격 스냅샷 기준이다.

## 판정 등급

- **FAIL**: 명세된 동작이 깨짐. 해석 불일치(용도·예산·해상도·화이트·와이파이·OS), 예산 초과, 합계 불일치, 호환성 실패, 용도별 최소 사양(RAM·SSD·GPU 하한·AI VRAM) 미달, 옵션 미반영, 제외 브랜드 포함, 3안 누락·순서 역전.
- **GAP**: 고객이 요구했지만 시스템에 기능이 없음. 모델·브랜드 지정, 고객이 직접 말한 RAM·SSD·VRAM 하한, 화이트 통일.
- **WARN**: 허용되지만 의심스러움. 같은 사양 30% 이상 저렴한 제품 존재, 고사양 GPU에 3만 원 미만 파워, 오래된 가격, 예산 55% 미만 활용, 중복 안.

## 절차

1. 서버 DB가 살아 있는지 확인한다: `curl -s localhost:8001/api/health`가 `"storage":"postgresql"`. 꺼져 있어도 스크립트는 DB만 있으면 돈다.
2. 실행한다(케이스당 약 5~15초, 전체 수 분이라 백그라운드로):
   ```bash
   cd pcquote/backend && uv run python ../.claude/skills/quote-eval/run_eval.py          # LLM 해석
   uv run python ../.claude/skills/quote-eval/run_eval.py --local                        # 규칙 해석만
   uv run python ../.claude/skills/quote-eval/run_eval.py --only G03,X04                 # 일부만
   ```
   보고서는 `pcquote/reports/quote-eval/<시각>.md`와 `.json`에 남는다.
3. FAIL·GAP·WARN 각각을 **원인 분류**한다. 끝난 기준: 모든 FAIL과 GAP에 다음 중 하나가 붙어 있다.
   - **해석 결함**: `consult.py` 규칙이나 LLM 병합이 고객 말을 놓침(예: 한글 숫자 예산).
   - **엔진 결함**: `engine/` 규칙 위반.
   - **데이터 결함**: 카탈로그 가격·사양 오류(예: 비정상 저가 파워). 해당 부품 id와 다나와 링크를 적는다.
   - **기능 부재**: 요구를 받을 필드가 `Request`에 없음.
   - **케이스 기대값 오류**: 기대값이 매장 정책과 다름. 기대값을 고치기 전에 근거(srs·plan 문서 조항 또는 사용자 확인)를 적는다.
   의심 항목은 `.json`의 `plans`·`requirement`를 보고, 필요하면 `--only`로 재실행해 재현한다.
4. 사용자에게 요약을 보고한다: 등급별 개수, 원인 분류별 묶음, 고객 영향이 큰 순서의 수정 제안. 코드 수정은 사용자가 고른 뒤에 한다.

## 케이스 추가

새 고객 표현·버그 재현은 `cases.json`에 추가한다(형식은 파일 상단 `_schema`). 추가 요청 흐름은 `turns`에 문장을 이어 적는다. 화면의 요구 병합 로직(`buildmate/src/main.jsx`의 `send`·`applyText`·`isNewTopic`)이 바뀌면 `run_eval.py`의 `screen_requirement`도 맞춘다.
