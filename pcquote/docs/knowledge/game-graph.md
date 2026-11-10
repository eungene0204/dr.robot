# 게임 지식 그래프

2026-11-11 최초 버전 `2026-11-11.1`. 견적 시 외부 검색이나 LLM 사실 생성 없이 버전 관리된 로컬 property graph를 조회한다. 그래프 JSON은 backend Python 패키지에 포함한다.

## 수집 범위와 근거

8게임: Overwatch, VALORANT, League of Legends, PUBG, Counter-Strike 2, Fortnite, Apex Legends, Cyberpunk 2077.

- 공식 요구 사양: 17개 프로필, 각 퍼블리셔 공식 지원 문서 또는 퍼블리셔가 관리하는 Steam 상품 페이지. [조사 및 정규화 JSON](../research/2026-11-11-game-requirements-sources.md).
- 원본 실측: ComputerBase의 자체 측정 4개(오버워치·사이버펑크, RTX 4060/5060 8GB). [원문·방법론·설정·한계](../research/2026-11-11-game-benchmark-sources.md).
- 107노드 / 121관계. `game → HAS_REQUIREMENT → requirement → REQUIRES_CPU/GPU → hardware`, `game → HAS_MEASUREMENT → measurement → TESTED_CPU/GPU → hardware`, 두 근거 종류에서 `SUPPORTED_BY → source`로 순회한다.
- 공식 하드웨어 대안은 `operator=any`인 대안 그룹이다. GTX 1060 3GB/6GB 등 VRAM이 다른 기록과 CPU 제품군/정확 모델을 구별한다. 공식 권장 사양을 FPS 측정으로 취급하지 않는다.

## 추천 적용

1. 서버가 제공하는 별칭을 UI에서 확인하고, 서버도 동일 그래프로 게임을 식별한다. 게임명이 확인된 요구는 EXAONE 호출을 생략한다. 명시된 편집·AI 등 용도는 기존 해석 규칙을 따른다.
2. 해상도 미지정임을 `resolutionExplicit=false`로 표시한 게임 견적만 FHD 기본값을 쓴다. 기존 API의 명시 해상도는 보존한다. 정규화된 `requirement`를 응답하여 화면 제목·저장·후속 견적 조건도 일치시킨다.
3. 공식 사양 RAM/설치 용량을 일반 최소 사양과 합쳐 하한으로 사용한다. 공식 CPU/GPU 이름과 원문은 조회 API에 보존한다. 오래된 모델과 현재 제품의 성능 동등성을 임의 생성하지 않는다.
4. FHD에서 특정 옵션·렌더링 모드를 지정하지 않은 경우 원문의 사용자 설정 High/Ultra 혼합 실측을 GPU 선택 참고로 쓴다. GPU 모델 및 VRAM이 일치하는 카탈로그 후보만 남긴다. 서로 다른 게임을 요청하면 공통 후보를 사용하며, 한 게임이라도 근거가 부족하면 제한을 적용하지 않는다.
5. 사용자 FPS가 있으면 **원문 평균 FPS**가 그 수치 이상인 GPU 후보를 조회한다. 미지정 기본 조회 기준은 오버워치 평균144, 나머지 평균60으로, 이는 서비스 정책이다. 목표 달성 판정이나 PC 성능 보장이 아니다. CPU9800X3D·RAM64GB인 실측 시스템과 실제 조립 견적을 구별한다.
6. 실측이 없는 QHD/4K, 명명된 옵션, 안정/방어 FPS, RT/업스케일/프레임 생성 요청은 `coverage_gap`으로 처리한다. 다른 해상도나 Blender 점수를 게임 FPS로 환산하지 않는다. 오버워치 원문 프레임 생성 여부는 미확인이므로 네이티브 모드 보장에도 사용하지 않는다.
7. 실측 후보 제한이 적용되면 예산은 상한이며 예산의 일정 비율을 소진하도록 강제하지 않는다. 실측 GPU 재고/가격이 확보되지 않으면 상위 미측정 GPU로 자동 대체하지 않는다. 직접 GPU 모델/브랜드 지정·VRAM 8GB 초과·최고 성능 요청은 후보 제한을 해제하며 `selectionApplied=false`와 이유를 표시한다. 호환성·예산·요청 VRAM 하한은 계속 검사한다.
8. 6게임 및 미측정 조건은 일반 추천 규칙으로 돌아가고 근거 부족을 표시한다. 이것을 게임별 FPS 검증이 완료된 견적으로 표현하지 않는다. 현재 그래프는 모든 게임·해상도를 커버하지 않는다.

## 조회와 유지보수

저장: `backend/src/pcquote/knowledge/games.json`. 각 출처에는 URL·확인일·검토 상태·재검토 기한이 있다. 현재 재검토 기한은 2027-02-11이며, 미검토·미래 확인일·기한 초과 근거는 선택 근거에서 제외한다. 영구 캐시로 오래된 자료를 확정하지 않는다.

```sh
# 저장소 루트: 검토한 조사 문서의 JSON으로 재생성
python pcquote/backend/scripts/build_game_graph.py
# backend 디렉터리
uv run python -m pcquote.knowledge validate
uv run python -m pcquote.knowledge resolve '오버워치 200fps'
uv run pytest -q
```

읽기 API: `GET /api/knowledge/graph`, `GET /api/knowledge/resolve?text=오버워치&resolution=FHD`. 견적 응답에는 `gameEvidence`(버전·게임·공식 프로필·측정 컨텍스트·출처·적용 상태·한계)가 포함된다. UI에서 출처와 조건 부족을 보여준다. FPS 보장 플래그는 항상 false다.

갱신할 때 원문을 직접 확인하고 조사 문서의 데이터·확인일을 수정한 후, 생성 스크립트의 버전·재검토 기한도 갱신한다. 생성 스크립트는 검토한 입력을 변환하는 도구이며 인터넷 내용을 자동 승인하지 않는다. 검증기는 중복 노드/관계·끊긴 연결·관계 종류·근거 출처·측정 하드웨어/컨텍스트를 검사한다. 정기 자동 수집은 이 기능 범위에 포함하지 않았다.
