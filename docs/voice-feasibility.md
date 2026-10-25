# 캐릭터 음성 대사 조사 · 2026-10-24

이 문서는 선행 조사 기록입니다. 별도 음성 대사 검색은 제거했으며, 현재 범위와 연결 한계는 [스토리 음원 조사](story-audio-status.md)를 따릅니다.

고정 원본 `db6f9ef8046ad17dbebe3ff1d0dd88844a5bc78c`의 [ArknightsGamedata](https://github.com/ArknightsAssets/ArknightsGamedata/tree/db6f9ef8046ad17dbebe3ff1d0dd88844a5bc78c) 네 지역 `gamedata/excel/charword_table.json`을 확인했다. 스토리 대사와 다른 데이터이며 이번 작업에서 검색 DB나 재생 UI에 추가하지 않았다.

| 지역 | charWords 항목 | 고유 charId | 중국어와 공통 키 | 중국어에만 있는 키 |
| --- | ---: | ---: | ---: | ---: |
| cn | 18,351 | 438 | 18,351 | 0 |
| kr | 17,675 | 421 | 17,675 | 676 |
| jp | 17,675 | 421 | 17,675 | 676 |
| en | 17,675 | 421 | 17,675 | 676 |

각 항목에 `charWordId`, `wordKey`, `charId`, `voiceId`, `voiceText`, `voiceTitle`, `voiceIndex`, `voiceType`, 해금 조건과 `voiceAsset`이 있다. 조사한 네 표에서 빈 voiceText/voiceAsset은 없었다. 음성 식별자는 예를 들어 `char_102_texas/CN_001` 형태의 상대 리소스 키이며 재생 가능한 HTTPS URL이 아니다. 표에 값이 있다는 사실만으로 실제 음성 파일의 존재나 접근 가능성을 입증하지 않는다.

조사 당시 캐릭터 ID와 대사 키로 지역별 항목을 연결하는 방식을 검토했으나, 별도 검색 화면은 현재 범위에서 제외했다. 공통 키는 구조상 연결 가능성만 의미하므로 charId/voiceId/해금 조건도 비교해야 한다. 중국 선행 676개 키를 임의 번역으로 채우지 않는다. 화면의 텍스트 언어와 성우 음성의 언어는 별도 설정으로 취급한다. voiceLangDict 등 언어별 음성 메타데이터의 세부 연결은 추가 검증이 필요하다.

음원 재생 전에는 파일 출처·배포/임베드 조건·실제 자산 경로·언어별 누락·브라우저 CORS/Range 지원·트래픽 규모를 확인해야 한다. PRTS의 화면을 참고해도 그 사이트의 음원 URL이나 대사 대응을 그대로 재사용할 수 있다고 가정하지 않는다. 이번에는 음원을 다운로드하거나 외부 음원에 연결하지 않았다.
