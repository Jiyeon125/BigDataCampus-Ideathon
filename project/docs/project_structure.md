# 프로젝트 구조 정리

## 1. 목적
Meet-Mid & Hip-Catcher 프로젝트의 코드, 데이터, 문서를 일관된 구조로 관리하기 위한 기본 폴더 구조 정의.

## 2. 폴더 구조

project/
  data/
    raw/
    interim/
    processed/
  docs/
  notebooks/
  src/
    preprocessing/
    features/
    modeling/
    visualization/
    utils/
  outputs/

## 3. 폴더별 역할

### data/
- raw/: 원본 데이터 보관
- interim/: 전처리 중간 산출물
- processed/: 모델 입력/최종 결과용 데이터

### docs/
- 기획 문서
- 분원 방문 체크리스트
- 데이터 딕셔너리
- 발표 스토리라인 메모

### notebooks/
- 데이터 확인
- EDA
- 시각화
- 실험용 분석 노트북

### src/
- preprocessing/: 데이터 로딩 및 전처리
- features/: Meet-Mid, H3 매핑, 피처 엔지니어링
- modeling/: rule-based, Isolation Forest 등 모델 코드
- visualization/: 지도/차트 생성 코드
- utils/: 공통 입출력, 좌표 계산, 텍스트 처리 유틸

### outputs/
- figure, table, 지도 이미지, 발표용 결과물 저장

## 4. 운영 원칙
- 폐쇄망 실행을 고려해 경로 하드코딩 최소화
- 파일경로, 컬럼명 매핑, 날짜 범위는 config로 분리
- 방문 전날에는 실행 스크립트와 실행 순서 문서를 함께 정리
- 원본 데이터는 raw 폴더에 보존하고 가공 데이터는 별도 저장