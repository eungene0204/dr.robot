# Dr.Robot 실제 데이터 파이프라인

등록된 실제 SKU → 수집 → 정규화 → 검증/격리 → SQLite 이력 → 원자적 스냅샷 → API/화면/추천 엔진.

가상 가격을 실제 가격으로 바꾸어 표시하는 방식이 아닙니다. 실제 원문에서 확보한 값만 가격·성능의 근거로 사용합니다. 누락·오류·만료 데이터를 가상값으로 대체하지 않습니다.

## 소스와 최초 수집

- 가격/스펙: 다나와 공개 상품 상세 페이지의 Product JSON-LD. `/info/?pcode=...`만 접근하고 robots.txt에서 제한한 API/AJAX 경로는 사용하지 않습니다.
- 보조 가격: 네이버 쇼핑 검색 공식 API. `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`와 상품별 고정 `naverProductId`/`naverQuery`를 설정해야 합니다. 중고·렌탈·해외직구를 제외하고 등록된 상품 ID만 비교합니다. 현재 실행 환경에는 키가 없어 이 소스의 실호출은 하지 않았습니다.
- 벤치마크: Blender 공식 `opendata-latest.zip`, CC0-1.0. 최초 실행에서 약 100MB ZIP을 받고 약 1.9GB의 JSONL을 메모리에 올리거나 디스크에 압축 해제하지 않고 스트리밍 집계합니다. 실제 규모는 이후 변경됩니다. Python 3이 필요합니다.
- 초기 카탈로그는 실제 상품 23개로 시작했습니다. 현재는 CPU·GPU·메모리·SSD·메인보드·파워·케이스·쿨러의 공개 검색 페이지를 순회해 자동 확장합니다. 검색어·유통 지역·공개 판매 상태에 따른 범위이며 전 세계 모든 상품을 보장하지 않습니다.

공식 문서: [다나와 robots.txt](https://prod.danawa.com/robots.txt), [네이버 쇼핑 검색 API](https://developers.naver.com/docs/serviceapi/search/shopping/shopping.md), [Blender 데이터·라이선스](https://opendata.blender.org/download/), [공식 스냅샷](https://opendata.blender.org/snapshots/).

## 실행

```sh
npm run pipeline
npm run pipeline:prices
npm run pipeline:benchmarks
npm run pipeline:discover -- 삼성전자 990 EVO Plus 2TB
npm run pipeline:schedule
```

키가 필요한 소스의 환경변수는 명령 실행 환경에 설정하거나 Node의 `--env-file`로 불러옵니다.

```sh
node --env-file=.env pipeline/run.mjs
node --env-file=.env pipeline/scheduler.mjs
```

전체 실행은 가격과 벤치마크를 함께 갱신합니다. 가격 소스는 호스트당 기본 2초 이상 간격, 검색은 robots의 10초 간격을 따릅니다. 실패 응답은 제한적으로 재시도하며 인증 차단을 우회하지 않습니다. Blender는 공식 다운로드 페이지에서 배포하는 CC0 데이터 아카이브를 직접 다운로드합니다(HTML 크롤링/색인과 별도). robots.txt의 snapshots 디렉터리 색인 제한을 웹 페이지 수집에 사용하지 않으며, 파일 HTTP 오류·속도 제한은 그대로 따릅니다. Blender ZIP은 7일 캐시하고 `--refresh-benchmarks`로 강제 갱신합니다. 등록한 CPU/GPU 모델 목록이 바뀌면 다시 집계합니다.

옵션:

| 옵션 | 의미 |
| --- | --- |
| `--prices-only` | 가격·스펙 수집, 기존 벤치마크 유지 |
| `--benchmarks-only` | 벤치마크만 수집, 기존 가격 유지 |
| `--refresh-benchmarks` | 공식 ZIP 재다운로드 |
| `--benchmark-archive /path/file.zip` | 사전에 다운로드한 공식 ZIP 사용 |
| `--reparse-cache` | 24시간 이내 원문 캐시로 파서 재실행. 원문 수집 시각 유지 |
| `--registry /path/products.json` | 별도 상품 레지스트리 |
| `--output /path/catalog.json` | 별도 출력 경로 |
| `--data-dir /path/state` | SQLite·원문 캐시·운영 상태 저장 위치 |

프로세스 종료 코드: `0` 정상, `2` 부분 성공(누락/만료/소스 오류), `1` 실행 실패. 부분 성공은 확보한 실제 데이터만 내보내고 미확인 항목을 상태 보고서에 남깁니다.

## 스케줄과 운영 환경

`scheduler.mjs`는 한국시간 매일 00:00 슬롯을 사용합니다. 시작 시 놓친 가장 최근 슬롯을 한 번 실행하고, 슬롯별 결과를 디스크에 남겨 재시작 중복을 막습니다. 실패는 15분 간격 최대 3회 재시도합니다. 실행 중복은 잠금 파일로 차단합니다. SIGINT/SIGTERM을 처리합니다.

스케줄러는 실행 중인 Node 프로세스가 필요합니다. 개발자 컴퓨터가 꺼지면 수집하지 않습니다. 서버에서는 systemd/컨테이너 등으로 프로세스를 유지하거나 아래 cron을 사용할 수 있습니다. cron 서버 시간대가 Asia/Seoul인지 확인하세요.

```cron
0 0 * * * cd /absolute/path/buildmate && /absolute/path/node --env-file=.env pipeline/run.mjs >> backend/data/cron.log 2>&1
```

로컬 API의 `POST /api/pipeline/run`도 동일 파이프라인을 실행합니다. 네트워크에 직접 공개하지 않은 로컬 관리 기능입니다. `GET /api/pipeline/status`, `GET /api/prices/history?partId=c2`로 확인할 수 있습니다.

**현재 Sites 배포는 정적 스냅샷입니다.** 로컬 스케줄러의 실행 결과가 이미 배포된 URL에 자동 업로드되지는 않습니다. 로컬 API/개발 서버는 갱신된 파일을 읽지만, 정적 배포는 생성된 `public/data/`를 포함하여 다시 빌드/배포해야 합니다. 상시 갱신되는 운영 URL에는 이 API/스케줄러를 실행할 서버와 영구 저장소, 또는 인증된 데이터 업로드 경로가 필요합니다. 정적 사이트에서 24시간이 지난 가격은 자동으로 추천에서 제외합니다.

## 상품 ID와 검수

`config/products.json`에 실제 유통 형태까지 구분되는 고정 상품 코드를 등록합니다. 자동 확장은 검색에서 발견한 상품 코드를 상세 JSON-LD SKU와 대조하고 품목별 필수 사양과 판매가격을 검증한 뒤 등록합니다. 모델명 유사도나 LLM만으로 SKU를 매칭하지 않습니다.

```json
{
  "id": "my-gpu",
  "category": "gpu",
  "name": "실제 제조사·보드 모델·VRAM",
  "danawaPcode": "실제_숫자_상품코드",
  "benchmarkName": "NVIDIA GeForce RTX 5070",
  "registryReviewed": true
}
```

파서는 응답 Product의 `sku`가 등록한 상품 코드와 같은지 확인합니다. RAM 16GB 단품과 32GB 키트, 8GB/16GB GPU, 정품/병행수입/멀티팩을 서로 다른 상품으로 취급합니다. 내장 그래픽 사용(`g0`)과 OS 미포함(`o0`)만 실물 상품이 아닌 0원 선택 옵션입니다.

급격한 가격 변동은 `pipeline.db`의 `review_queue`에 격리합니다. 해당 원문 SHA-256을 담당자가 확인한 후 `config/reviews.json`의 `approvedPriceHashes`에 등록하면 다음 수집에서 반영합니다. 승인되지 않은 변동은 직전 정상 가격을 유지하고 수집 시각을 새로 고치지 않습니다. 기존 가격도 24시간이 지나면 사용할 수 없습니다.

제조사 검수가 끝난 규격은 `specOverrides`에 기록합니다. 출처·검수 시각이 없는 오버라이드는 적용하지 않습니다.

```json
{
  "approvedPriceHashes": [],
  "specOverrides": {
    "실제_부품_ID": {
      "reviewed": true,
      "sourceUrl": "https://제조사/실제지원페이지",
      "reviewedAt": "ISO-8601 시각",
      "specs": {"bios": ["실제로_지원목록을_확인한_CPU_ID"]}
    }
  }
}
```

BIOS 지원 목록이 없으면 `null`, GPU 두께·장착 위치나 쿨링 용량을 확정할 근거가 없으면 `null`입니다. 미확인을 통과로 바꾸지 않습니다. 그런 구성은 자동 추천에서 제외합니다. 대체 목록에서는 현재 구성의 호환 여부와 미확인 사유를 표시합니다. 가격·벤치마크 사용 조건을 충족한 제품은 수동 검토 구성에 담을 수 있으며, 관련 부품 조정과 모든 검증을 통과하기 전에는 견적서 발행을 차단합니다. 제조사 검수가 완료된 항목은 reviews.json에 출처와 조건을 남기며, 예컨대 지원 BIOS 버전으로 업데이트하는 조립 조건을 화면에 표시합니다. 실물 조립 완료를 의미하지 않습니다.

## 가격의 의미

`amount`는 가격비교 사이트에 등록된 원화 최저가입니다. 실재고와 배송비가 보장된 최종 주문금액이 아닙니다. 배송비가 없으면 `shipping: null`, `shippingKnown: false`, 재고는 `listed-unconfirmed`로 저장하고 화면에 고지합니다. 품절·가격 없음·0원·통화 불일치·SKU 불일치는 거부합니다.

DB는 상품 원문에서 파싱한 스펙, 출처 URL, 수집 시각, 원문 SHA-256, 가격 이력, 벤치마크 근거, 실행 이력, 검수 큐를 분리합니다. 전체 HTML과 ZIP 캐시는 `backend/data/`에만 두고 배포/버전 관리에서 제외합니다. 공개 스냅샷에는 필요한 숫자와 출처만 내보냅니다.

## 성능 지수의 의미

- 한 제출에 `monster`, `junkshop`, `classroom` 3장면이 모두 있고 단일 장치를 사용한 경우만 포함합니다.
- 장면별 `samples_per_minute`를 합산하고, 동일 칩·버전·백엔드·장면 체크섬 그룹의 중앙값을 사용합니다.
- 최소 3개의 완전한 제출이 있어야 합니다. CPU는 CPU 백엔드, NVIDIA GPU는 OPTIX 백엔드만 비교합니다.
- 가장 많은 등록 모델을 비교할 수 있는 공통 버전을 선택하고, 동률이면 최신 버전을 사용합니다.
- CPU 9600X=`100`, GPU RTX 5060 Ti=`100` 기준으로 각각 정규화합니다. 기준 모델은 레지스트리의 `benchmarkReferences`에서 지정합니다. 서로 다른 버전의 CPU/GPU 측정값은 합성 지수로 계산하지 않습니다.
- 실제 원본 값·단위·표본 수·버전·장면·측정 제출 시각·스냅샷 수집 시각·해시를 저장합니다.
- GPU는 칩 모델 단위이며 보드 제조사·VRAM 변형과 실행 환경 차이가 포함될 수 있습니다. 개별 판매 SKU의 실측이라고 표시하지 않습니다.
- 이 지수는 **Blender 렌더링 비교 지수**입니다. 게임 FPS나 AI 추론 속도를 예측한 값이 아닙니다. 게임·AI에 맞는 실측 데이터셋은 별도로 연결해야 합니다.
- RAM/SSD의 수집 전송속도는 제조사 공개 사양이며 실측 벤치마크라고 표시하지 않습니다. 파워/케이스/보드에는 임의의 종합 성능 점수를 주지 않습니다.

## 파일

| 경로 | 내용 |
| --- | --- |
| `pipeline/config/products.json` | 검수된 실제 SKU 매핑 |
| `pipeline/config/reviews.json` | 가격 이상치 승인 및 출처 있는 스펙 검수 |
| `backend/data/pipeline.db` | 영구 이력·검수·운영 상태 |
| `backend/data/cache/` | 원문 캐시(배포 제외) |
| `public/data/catalog.json` | 화면/API/추천이 공유하는 실제 데이터 |
| `public/data/pipeline-status.json` | 비밀정보 없는 실행/검수 상태 |
| `public/data/price-history.json` | 실제 수집 이후 누적 가격 이력 |

가격 이력이 1일뿐이면 30일 그래프를 만들어 채우지 않습니다. 실패/구조 변경/데이터 공백을 운영 화면에 그대로 표시합니다.

## 자동 상품 확장

`npm run pipeline:expand`는 `config/discovery.json`의 CPU·메인보드·RAM·GPU·SSD·파워·케이스·쿨러 검색을 순회합니다. 검색/상세 페이지의 상품 코드를 일치시키고 품목별 필수 스펙, KRW 판매가격이 확인된 상품만 레지스트리에 추가합니다. 중고·렌탈·노트북·서버 메모리와 잘못된 품목은 제외하며, 실패/누락은 `backend/data/discovery-state.json`에 이유를 저장합니다. 미확인 BIOS·쿨링 정보와 누락된 실측 벤치마크를 통과로 만들지 않습니다.

각 실행은 기본적으로 검색어별 다음 1페이지를 처리합니다. 동일 상품만 반복되거나 검색 결과가 없으면 해당 검색을 마칩니다. 페이지 커서는 영구 저장되어 이후 실행이 다음 페이지부터 이어집니다. 기본 페이지 상한은 없으며, 빈 페이지 또는 반복 페이지가 나올 때까지 진행합니다. 테스트·별도 운영에서는 maxPagesPerQuery로 명시적 상한을 설정할 수 있습니다. 전 세계 모든 상품 수집이나 전역 최적 견적을 보장하지 않습니다.

스케줄러의 자정 실행은 자동 확장 후 가격·벤치마크를 갱신합니다. CPU/GPU의 칩 모델이 동일한 여러 SKU는 같은 실측 통계를 공유합니다. 추천은 단순 가격순 12개 제한을 사용하지 않고, 동일 평가·호환성 특성을 가진 후보 중 최저가를 남기고 부분 조합의 호환성과 최소 잔여 비용으로 탐색을 줄입니다. 현재 성능 평가는 Blender 중심입니다.

수집 도중 `node pipeline/publish.mjs`로 검증된 저장 관측을 화면에 반영할 수 있습니다. 원래 관측 시각을 유지하며 가격 수집 시각을 임의로 갱신하지 않습니다. 신규 CPU/GPU의 측정값을 연결하려면 확장 후 `npm run pipeline:benchmarks`를 실행합니다.

## 자정 신제품 추가 스킬과 macOS 예약

개인 스킬 `~/.codex/skills/drobot-daily-components`의 실행 헬퍼가 `pipeline/daily.mjs`를 호출합니다. LaunchAgent `~/Library/LaunchAgents/com.drrobot.daily-components.plist`는 매일 한국시간 00:00에 이 헬퍼를 실행합니다(현재 Mac 시스템 시간대 Asia/Seoul). 중복 예약을 피하려면 LaunchAgent가 등록된 환경에서 별도 스케줄러/cron을 동시에 시작하지 않습니다.

`npm run pipeline:daily -- --check`로 읽기 전용 상태를 확인합니다. 실제 실행은 같은 한국 날짜의 완료 보고서가 있으면 건너뛰고, 필요할 때 `--force`로 재실행합니다. 매일 최신순 첫 검색 결과를 재검색하고 저장된 다음 페이지도 진행합니다. 기존 수집 잠금은 최대 3시간 기다리며, 보고서는 `backend/data/daily-YYYY-MM-DD.json`, 예약 로그는 `backend/data/daily.launchd*.log`에 저장합니다. 전원이 꺼져 있으면 실행되지 않으며, 절전 중 놓친 launchd 작업은 깨어난 뒤 실행됩니다.

## 상위 사양 대체 부품

대체 목록과 상세 비교표는 현재 구성과 호환되지 않는 제품도 교체 조건과 함께 보여줍니다. 모델명 검색, 상위 사양순/가격순 정렬, 바로 교체 가능 필터를 제공합니다. CPU/GPU는 등록된 Blender 지수, RAM·SSD는 용량과 전송속도, PSU는 정격 용량 등 품목별 사양을 사용하며 가격을 성능 점수로 사용하지 않습니다.

Intel 소켓1851은 LGA1851로 정규화하고 하이브리드 코어 수와 PBP-MTP의 최대 전력을 파싱합니다. 285K 정품 SKU 69059459를 등록했습니다. 상위 모델 검색어는 config/discovery.json에 포함되어 다음 확장 수집에서도 갱신됩니다. 확장 저장 시 디스크에 별도로 추가된 등록 상품을 병합해 수동 등록의 유실을 방지합니다.

## 최근 2년 최소 수집 범위

`config/discovery.json`의 `releaseWindowYears: 2`가 최소 목표 기간입니다. 한국 날짜 기준으로 2년 전부터 오늘까지이며, 과거 상품을 삭제하는 필터가 아닙니다. CPU·메인보드·RAM·GPU·SSD·파워·케이스·CPU 쿨러 공개 카테고리 인덱스와 검색 페이지를 함께 탐색하고, 패키지/용량별 공개 번들 SKU도 읽습니다. 일부 카테고리는 공개 HTML이 첫 목록만 제공하므로 해당 경로는 `coverageLimited`로 남기고 전체 수집 완료로 표시하지 않습니다. 제한된 AJAX API를 우회하지 않습니다.

제품 상세의 `등록월`은 `listingMonth` 및 `listingDateEvidence`에 저장합니다. 제조사에서 확인한 실제 출시일은 별도의 `releaseEvidence`로만 취급합니다. 월 단위 경계 제품과 날짜 미확인 제품도 버리지 않으며, 스냅샷 `collectionWindow`에서 최근 등록월/경계 월/과거 등록월/날짜 미확인/출시일 확인 수를 구분합니다. 사이트맵의 lastmod도 출시일로 취급하지 않습니다. 제조사 출시일과 시장 전체 커버리지가 확인되지 않은 동안 `complete`는 false입니다.

품목과 실제 SKU가 확인되지만 현재 가격이 없는 상품도 수집 기록에 보존합니다. 가격·벤치마크·호환성 정보가 없으면 추천에는 쓰지 않습니다. `node pipeline/reindex-dates.mjs`는 저장된 원문에서 등록월을 복구하며 가격 관측 시각을 갱신하지 않습니다.
