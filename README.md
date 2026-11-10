# Dr.Robot

PC 상담 화면과 Python API·추천 엔진·수집기를 함께 관리하는 단일 저장소입니다.

- `buildmate/`: React 상담 화면, 화면 테스트, 데이터 및 운영 문서
- `pcquote/`: FastAPI API, 추천 엔진, PostgreSQL 저장, 수집기

## 실행

Node.js, Python 3.12 이상, uv, PostgreSQL 16이 필요합니다.

```bash
npm run setup
npm run server   # API: http://127.0.0.1:8001
# 다른 터미널에서
npm run dev      # 화면: http://127.0.0.1:5588
```

DB 최초 생성·가져오기는 [백엔드 README](pcquote/README.md)를 따릅니다.
EXAONE 키는 `pcquote/backend/.env`에 `LLM_PROVIDER=exaone`, `EXAONE_API_KEY`, `EXAONE_MODEL=k-exaone_v2.5`로 설정합니다. `.env`는 Git에서 제외됩니다.

```bash
npm run test:backend
npm test
npm run build
```

빌드 후 API 서버가 화면도 제공합니다. 두 폴더는 형제 경로를 유지해야 합니다.
Git 작업은 이 루트에서 수행합니다. 두 프로젝트의 기존 커밋 이력은 통합 커밋의 부모 이력으로 보존되어 있습니다.
