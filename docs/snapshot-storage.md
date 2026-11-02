# 검색 스냅샷 저장 최적화 (2026-11-02)

원본 리비전 `3c3ab1ffe979c186f5dfd76c1750ee73d4c3f900`, PR #50의 공개 검색 묶음과 같은 원본을 재적재한 새 스냅샷을 비교했다. 게임 원문이나 DB는 이 문서에 포함하지 않는다.

## 구조와 선택

기존 SQLite의 `lines`는 322.18MiB, `story_idx`는 83.01MiB, `speaker_idx`는 27.95MiB였다. 각 대사의 SHA-256을 64자리 16진 문자열로 저장해 해시 본문만 91.66MiB를 사용했다. 이를 32바이트 BLOB으로 저장하고 가상 `hash` 열에서 원래 소문자 16진 문자열을 복원한다. 공개 조회는 기존 7개 대사 열을 명시해 내부 BLOB을 JSON으로 내보내지 않는다. 구버전 검색 DB와 변경 가능한 아카이브도 동일한 공개 열로 읽는다.

이 변경으로 `lines`는 272.03MiB가 된다. 대사·분기·물리 행·출처·해시 값과 다국어 ordinal map은 모두 유지한다. 입력 해시가 비정규 형식이면 빌드를 실패시키고 기존 출력은 교체하지 않는다. 기존 450MiB 제한과 모든 검색 인덱스는 유지한다. 빌드 입력 fingerprint가 달라지므로 예전 Release를 새 스키마의 결과로 재사용하지 않는다.

동일 해시는 61,604행(약 4.1%)에서 반복된다. 같은 문장도 파일·분기·등장 위치가 다르므로 행을 합치지 않는다. 스토리 ID 문자열은 대사 테이블에서 합계 약 65.29MiB이고 위치 인덱스에도 반복된다. 정수 사전으로 정규화하면 추가 절감 여지가 있지만, 공개 story ID를 복원하는 JOIN과 검색 계획·호환성 변경이 필요하다. 이번의 손실 없는 해시 표현 변경만으로 제한 여유를 50MiB 이상 확보하여 이 추가 마이그레이션은 포함하지 않았다. 대응표는 이미 zlib 압축된 ordinal map을 사용하며 전체 5.20MiB여서 우선순위가 낮다.

## 용량과 동일성

| 항목 | 변경 전 | 변경 후 |
| --- | ---: | ---: |
| SQLite | 446.891MiB | 396.742MiB |
| gzip (level 6) | 약 149.3MiB | 135.563MiB |
| 450MiB까지 여유 | 3.109MiB | 53.258MiB |
| 대사 | 1,501,688행 | 동일 |
| 스토리 | 21,954개 | 동일 |
| 다국어 파일 대응표 | 6,544개 | 동일 |
| 자동완성 집계 | 52,852행 | 동일 |

`compare_snapshots.py`가 전체 공개 대사 열·스토리 메타데이터·압축된 대응표·자동완성 집계·수집 상태를 정렬 후 스트리밍 비교하며, 두 DB의 `integrity_check`를 실행한다. 네 언어·공개 범위·페이지·기존 상세/대조 API를 포함한 60개 API 응답 및 결과의 문맥도 비교했다. 화자 조회는 `speaker_idx`, 파일 내 문맥 조회는 `story_idx`를 계속 사용한다.

## 재현

```sh
# 기존 dataset Release의 검증된 search.sqlite를 before.sqlite로 보존한다.
python sync.py --database data/build.sqlite --ephemeral --ref 3c3ab1ffe979c186f5dfd76c1750ee73d4c3f900
python build.py --source-db data/build.sqlite
python scripts/compare_snapshots.py before.sqlite generated/search.sqlite
python scripts/verify_alignment_snapshot.py data/build.sqlite generated/search.sqlite --output generated/alignment-validation.json
python scripts/benchmark.py before.sqlite --rounds 7 --unified
python scripts/benchmark.py generated/search.sqlite --rounds 7 --unified
```

벤치마크는 다른 빌드·검증 작업이 종료된 뒤 순차 실행한다. 로컬 CPU·파일 캐시의 영향이 있으며 네트워크, 배포 환경의 기동 시간 및 최초 gzip 해제 시간은 포함하지 않는다.

## 전송 압축

새 DB에서 gzip 압축 수준도 비교했다. CPU 시간은 `time.process_time()`으로 측정했으며 I/O 대기와 다른 프로세스의 CPU 시간을 제외한다.

| gzip 수준 | 크기 | 압축 CPU 시간 |
| --- | ---: | ---: |
| 1 | 146.35MiB | 12.94초 |
| 6 | 135.56MiB | 49.92초 |
| 9 | 133.50MiB | 73.27초 |

수준 9는 6보다 약 2.07MiB(1.5%) 작지만 CPU 시간이 약 47% 증가했다. 빌드 비용과 전송량을 고려해 기존 수준 6을 유지한다. Runtime의 gzip 해제·잠금·immutable 읽기 전용 연결 방식도 유지한다. SQLite 자체의 절감이므로 압축 해제 후 `/tmp` 점유량과 전체 검색 스캔에 필요한 페이지 수도 줄어든다.
