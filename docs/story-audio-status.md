# 스토리 대사 음원 조사 · 2026-10-24

현재 검색 원본 SHA `db6f9ef8046ad17dbebe3ff1d0dd88844a5bc78c`의 네 지역 story 폴더를 직접 확인했다. 전체 21,451개 텍스트 파일의 명령과 속성을 조사했으며 개발 예제 avg_segment_report.txt는 제외했다. 집계와 명령 속성 예시는 story-audio-audit.json에 보존한다. 이 조사는 음성 파형 분석·전사 대조가 아니므로 모든 예외 콘텐츠에 음성이 없다고 단정하지 않는다.

| 지역 | 파일 | 텍스트 명령 | PlaySound | Video | 텍스트 명령의 voice/audio/sound 속성 |
| --- | ---: | ---: | ---: | ---: | ---: |
| cn | 5,674 | 390,420 | 41,082 | 28 | 0 |
| kr | 5,259 | 372,350 | 38,654 | 27 | 0 |
| jp | 5,259 | 372,350 | 38,654 | 27 | 0 |
| en | 5,259 | 372,350 | 38,654 | 27 | 0 |

관찰된 PlayMusic/PlaySound 등은 장면 단위 오디오 큐이며, 인접한 대사 한 줄의 성우 녹음이라는 근거가 아니다. VoiceWithin은 head/delay 속성과 직접 텍스트를 가진 명령으로, 조사된 예시에는 재생 파일 참조가 없었다. Video는 mp4 리소스를 가리키지만 영상의 특정 발화를 검색 대사와 연결하는 타임코드가 없다.

[ArknightsGamedata 원본](https://github.com/ArknightsAssets/ArknightsGamedata/tree/db6f9ef8046ad17dbebe3ff1d0dd88844a5bc78c)과 [PseudoMon/arknights-audio](https://github.com/PseudoMon/arknights-audio)의 자료 구조도 확인했다. 후자는 캐릭터 voice 언어 폴더와 avg/battle/music 등을 별도로 보유하며, README는 정기 갱신 범위를 voice로 설명한다. 해당 저장소의 캐릭터 녹음을 스토리 대사에 대신 붙이지 않는다. 음원 재배포 허용이나 안정적인 서비스 제공을 이 조사만으로 보증하지 않는다.

결론: 현재 확보한 자료에서는 검색 대사와 일대일 대응을 검증한 재생 음원 연결을 만들지 못했다. 따라서 재생 버튼이나 임의 연결을 운영에 추가하지 않는다. 실제 스토리 대사 ID·언어·출처 버전·재생 파일·필요시 타임코드가 확인되는 자료가 확보되면, 별도 검색 메뉴 없이 기존 결과의 해당 언어 대사에 재생을 추가한다.
