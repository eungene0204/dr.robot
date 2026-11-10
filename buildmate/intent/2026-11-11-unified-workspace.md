# Intent: Dr.Robot 저장소 통합

- 작성일: 2026-11-11
- 작성자: Codex
- 요청자: 사용자
- 상태: 완료
- 요청자/제품 책임자 검토: 미검토

## 문제와 기대 결과
화면과 백엔드가 같은 GitHub 저장소의 서로 다른 브랜치로 분리되어 있었다. 한 브랜치를 체크아웃하면 두 구성요소를 함께 받을 수 있게 한다.

## 범위와 제약
루트 아래 buildmate/와 pcquote/를 함께 관리한다. 기존 두 커밋 이력과 형제 경로, 로컬 키·운영 데이터·설치 파일을 보존한다. 기존 Git 메타데이터는 작업 폴더 밖에 백업한다. 루트 실행 안내와 npm 명령을 제공한다.

## 수용 기준
- [x] 루트 Git 한 개가 두 폴더를 일반 파일로 추적한다(서브모듈 아님).
- [x] 기존 두 HEAD가 통합 이력의 조상이다.
- [x] 백엔드·화면 테스트 및 빌드가 통과한다.
- [x] 새 브랜치를 GitHub에 푸시하고 원격 브랜치의 커밋과 두 폴더의 트리를 확인한다.

## 가정과 열린 질문
- 기존 main은 유지하고 unified-workspace 브랜치에 통합한다.
- 질문: 없음.

## 구현 및 검증 결과
- 기존 Git 메타데이터 백업: /Users/eugene/nullSpace/drobot-git-backup-3njtgxk8. 로컬 키·운영 파일·node_modules·가상환경 보존.
- 루트·화면·백엔드에서 rev-parse --show-toplevel 모두 /Users/eugene/nullSpace/drobot 확인. 서브모듈 엔트리 없음, 추적 파일 키 검사 통과.
- npm run test:backend 270개, npm test 화면 88개, npm run build 통과. 실행 API health 정상.
- 루트 npm 명령과 README 추가, 구조 문서 갱신. srs.md는 사용자 기능 변경 없어 유지.
- 원격 unified-workspace가 통합 커밋 efcfd67과 일치함을 ls-remote로 확인. 해당 커밋의 루트 트리에 buildmate/와 pcquote/ 존재. 두 기존 HEAD(0bb838b, eade044)가 조상임을 merge-base로 확인. 기존 main 유지. 브라우저 수동 조작·새 환경 DB 초기화 미실행.
