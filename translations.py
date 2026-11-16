"""Shared UI copy; UI language and corpus language are independent."""
UI_LANGS = {'ko':'한국어', 'zh':'中文', 'ja':'日本語', 'en':'English'}
KEYS = 'search subtitle help privacy terms license changelog feedback speaker target expression corpus required optional swap spoilers results more context context_more line branch unnamed loading failed no_results broaden retry search_error long_query count search_pair search_solo choose empty_speaker update_ready update_later update_now update_hint back ui_language dark light'.split()
ROWS = {'ko': ['대사 검색', '명일방주 대사 검색', '사용 설명서', '개인정보', '이용안내', '라이선스', '패치 노트', '피드백 보내기', '말하는 인물', '대사에서 찾을 인물', '대사 속 표현', '대사 언어', '필수', '선택', '두 인물 바꾸기', '중국 서버 선행 스토리 포함', '검색 결과', '대사 더 보기', '앞뒤 문맥', '문맥 더 보기', '원본 {n}행', '분기', '이름 없음', '검색 중…', '요청을 처리하지 못했습니다. 다시 시도하세요.', '조건에 맞는 대사가 없습니다.', '찾을 인물이나 표현을 지워 다시 검색하세요.', '검색 버튼을 눌러 다시 시도하세요.', '말하는 인물을 입력하세요.', '검색어가 너무 깁니다.', '{n}개 대사', '{a} → {b}', '{a}의 전체 대사', '이름 검색', '말하는 인물', '새로운 버전의 웹사이트가 출시되었습니다.', '나중에 다시 알림', '지금 업데이트', '30분 후 다시 알려드립니다.', '대사 검색으로', '화면 언어', '다크 모드', '라이트 모드'], 'en': ['Dialogue search', 'Arknights dialogue search', 'User guide', 'Privacy', 'Terms', 'License', 'Changelog', 'Feedback', 'Speaker', 'Character mentioned', 'Words in dialogue', 'Dialogue language', 'Required', 'Optional', 'Swap characters', 'Include CN advance stories', 'Search results', 'Load more', 'Surrounding dialogue', 'Expand context', 'Source line {n}', 'Branch', 'Unnamed', 'Searching…', 'Request failed. Please try again.', 'No matching dialogue.', 'Clear the mentioned character or phrase and search again.', 'Press Search to try again.', 'Enter a speaker.', 'Search text is too long.', '{n} lines', '{a} → {b}', 'All dialogue by {a}', 'Search names', 'Speaker', 'A new version of the website is available.', 'Remind me later', 'Update now', 'Remind me again in 30 minutes.', 'Back to search', 'Interface language', 'Dark mode', 'Light mode'], 'zh': ['台词搜索', '明日方舟台词搜索', '使用说明', '隐私', '使用条款', '许可', '更新日志', '反馈', '说话角色', '台词中提及的角色', '台词中的词句', '台词语言', '必填', '选填', '交换角色', '包含国服先行剧情', '搜索结果', '加载更多', '前后台词', '展开更多上下文', '原文件第 {n} 行', '分支', '未署名', '搜索中…', '请求失败，请重试。', '没有匹配的台词。', '清除提及的角色或词句后重新搜索。', '点击搜索重试。', '请输入说话角色。', '搜索内容过长。', '{n} 条台词', '{a} → {b}', '{a}的全部台词', '搜索角色名', '说话角色', '网站已有新版本。', '稍后提醒', '立即更新', '30 分钟后再次提醒。', '返回搜索', '界面语言', '深色模式', '浅色模式'], 'ja': ['台詞検索', 'アークナイツ台詞検索', '使い方', 'プライバシー', '利用案内', 'ライセンス', '更新履歴', 'フィードバック', '話す人物', '台詞に登場する人物', '台詞内の語句', '台詞の言語', '必須', '任意', '人物を入れ替え', '中国サーバー先行ストーリーを含む', '検索結果', 'さらに表示', '前後の台詞', '文脈をさらに表示', '原文 {n} 行目', '分岐', '名前なし', '検索中…', 'リクエストに失敗しました。再試行してください。', '該当する台詞はありません。', '登場人物や語句を消して再検索してください。', '検索ボタンで再試行してください。', '話す人物を入力してください。', '検索語句が長すぎます。', '{n} 件の台詞', '{a} → {b}', '{a}の全台詞', '人物名を検索', '話す人物', '新しいバージョンが公開されました。', '後で通知', '今すぐ更新', '30分後に再通知します。', '検索に戻る', '表示言語', 'ダークモード', 'ライトモード']}
STRINGS = {lang:dict(zip(KEYS, row, strict=True)) for lang,row in ROWS.items()}
EXTRA = {
 'ko': {'no_parallel':'같은 줄 위치의 다른 언어 후보가 없습니다.','retry_action':'다시 시도','source_line':'원본 행','close':'닫기','source_details':'대사 정보','source_file':'원본 파일','source_revision':'원본 버전','source':'제공처','main_branch':'기본 분기','branch_hint':'앞뒤 문맥에는 서로 다른 분기의 대사가 섞일 수 있습니다. 분기 정보를 함께 확인하세요.','story_filter':'스토리 파일','all_stories':'전체 스토리','story_count':'{path} · {n}개'},
 'en': {'no_parallel':'No same-line candidates in other languages.','retry_action':'Retry','source_line':'Source line','close':'Close','source_details':'Dialogue details','source_file':'Source file','source_revision':'Source revision','source':'Provider','main_branch':'Main branch','branch_hint':'Adjacent lines may belong to different branches. Check the branch details when interpreting context.','story_filter':'Story file','all_stories':'All stories','story_count':'{path} · {n} lines'},
 'zh': {'no_parallel':'没有其他语言的同行候选。','retry_action':'重试','source_line':'原文件行号','close':'关闭','source_details':'台词信息','source_file':'原始文件','source_revision':'原始版本','source':'提供方','main_branch':'主分支','branch_hint':'相邻台词可能属于不同分支。解读上下文时请确认分支信息。','story_filter':'剧情文件','all_stories':'全部剧情','story_count':'{path} · {n} 条'},
 'ja': {'no_parallel':'同じ行位置の他言語候補はありません。','retry_action':'再試行','source_line':'原文の行番号','close':'閉じる','source_details':'台詞情報','source_file':'原文ファイル','source_revision':'原文の版','source':'提供元','main_branch':'基本分岐','branch_hint':'隣接する台詞が別の分岐に属する場合があります。文脈を読む際は分岐情報も確認してください。','story_filter':'ストーリーファイル','all_stories':'すべてのストーリー','story_count':'{path} · {n} 件'}
}
SEARCH_EXTRA = {
 'ko': {'speaker_optional':'말하는 인물 · 선택','target_optional':'대사에서 찾을 인물 · 선택','expression':'대사 속 단어나 문구','search_error':'인물이나 대사 속 표현을 입력하세요.','search_keyword':'“{q}” 포함 대사','search_mention':'{b} 이름이 포함된 대사'},
 'en': {'speaker_optional':'Speaker · optional','target_optional':'Character mentioned · optional','expression':'Word or phrase in dialogue','search_error':'Enter a character or a word in dialogue.','search_keyword':'Dialogue containing “{q}”','search_mention':'Dialogue mentioning {b}'},
 'zh': {'speaker_optional':'说话角色 · 选填','target_optional':'台词中提及的角色 · 选填','expression':'台词中的词语或句子','search_error':'请输入角色或台词中的词句。','search_keyword':'包含“{q}”的台词','search_mention':'提及{b}姓名的台词'},
 'ja': {'speaker_optional':'話す人物 · 任意','target_optional':'台詞に登場する人物 · 任意','expression':'台詞内の単語やフレーズ','search_error':'人物または台詞内の語句を入力してください。','search_keyword':'「{q}」を含む台詞','search_mention':'{b}の名前を含む台詞'}
}
for lang,values in SEARCH_EXTRA.items(): EXTRA[lang].update(values)
for lang,values in EXTRA.items(): STRINGS[lang].update(values)
def tr(lang, key, **values):
    return STRINGS[lang][key].format(**values)

for lang, label in {"ko":"상대 발화가 가까운 결과", "en":"Nearby turn by the other character", "ja":"相手の発言が近くにある結果", "zh":"附近有对方发言的结果"}.items():
    STRINGS[lang]["nearby_turns"] = label

for lang, label in {"ko":"검색 입력 초기화", "en":"Clear search inputs", "ja":"検索入力をクリア", "zh":"清空搜索内容"}.items():
    STRINGS[lang]["reset_search"] = label

for lang, placeholders in {
    "ko": ("검색할 대사 혹은 단어를 입력하세요.", "화자를 입력하세요.", "청자를 입력하세요."),
    "en": ("Enter dialogue or a word to search.", "Enter the speaker.", "Enter the listener."),
    "ja": ("検索する台詞や単語を入力してください。", "話し手を入力してください。", "聞き手を入力してください。"),
    "zh": ("请输入要搜索的台词或词语。", "请输入说话者。", "请输入听话者。"),
}.items():
    STRINGS[lang].update(zip(("query_placeholder", "speaker_placeholder", "target_placeholder"), placeholders, strict=True))

for lang, label in {"ko":"입력 지우기", "en":"Clear inputs", "ja":"入力をクリア", "zh":"清空输入"}.items():
    STRINGS[lang]["clear_inputs"] = label

COMPARISON_COPY = {
    'ko': {'compare_mode':'원문·번역 대조','translation_language':'함께 볼 번역 언어','original_text':'원문','translation_unavailable':'이 언어의 번역 파일이 없습니다.','translation_unverified':'대응 대사를 확인하지 못했습니다.','alignment_method':'번역 대응 기준','alignment_structure':'명령·분기 구조와 대사 순서 일치','search_original':'중국어 원문에서 검색'},
    'en': {'compare_mode':'Original & translation','translation_language':'Translation language','original_text':'Original','translation_unavailable':'No translation file is available in this language.','translation_unverified':'Corresponding dialogue could not be verified.','alignment_method':'Alignment method','alignment_structure':'Matching command/branch structure and dialogue order','search_original':'Search the Chinese original'},
    'ja': {'compare_mode':'原文・訳文を比較','translation_language':'一緒に表示する翻訳言語','original_text':'原文','translation_unavailable':'この言語の翻訳ファイルはありません。','translation_unverified':'対応する台詞を確認できませんでした。','alignment_method':'訳文の対応基準','alignment_structure':'命令・分岐構造と台詞順序の一致','search_original':'中国語の原文で検索'},
    'zh': {'compare_mode':'原文与译文对照','translation_language':'对照译文语言','original_text':'原文','translation_unavailable':'暂无该语言的翻译文件。','translation_unverified':'无法确认对应台词。','alignment_method':'译文对应依据','alignment_structure':'命令、分支结构及台词顺序一致','search_original':'搜索中文原文'},
}
for lang, values in COMPARISON_COPY.items():
    STRINGS[lang].update(values)

for lang, text in {"ko":"중국어 원문 파일이 없습니다.", "en":"No Chinese original file is available.", "ja":"中国語原文のファイルはありません。", "zh":"缺少中文原文文件。"}.items():
    STRINGS[lang]["original_unavailable"] = text


for _ui, _copy in {
    "ko": "페이지 언어의 대응 대사를 확인하지 못해 검색된 언어로 표시합니다.",
    "en": "No verified line in the page language; showing the matched language.",
    "ja": "ページ言語の対応を確認できないため、検索で見つかった言語を表示しています。",
    "zh": "未能确认页面语言的对应台词，现显示匹配语言。",
}.items():
    STRINGS[_ui]["main_language_missing"] = _copy

for _ui, _text in {
    "ko": "검색한 인물의 이름·별칭 일치",
    "en": "Matching character name or registered alias",
    "ja": "検索した人物名・登録別名の一致",
    "zh": "匹配搜索角色的姓名或已登记别名",
}.items():
    STRINGS[_ui]["name_match"] = _text


for lang, values in {
    "ko": ("제삼자 언급 후보만", "주변 대화 인물 · 선택", "주변 발화를 기준으로 찾은 후보입니다. 실제 청자와 지칭은 앞뒤 문맥에서 확인하세요.", "제삼자 검색에는 서로 다른 화자와 언급 인물이 필요합니다."),
    "en": ("Third-party mention candidates", "Surrounding speaker · optional", "Candidates based on nearby turns. Check context to establish the addressee and reference.", "Third-party search requires distinct speaker and mentioned character."),
    "ja": ("第三者への言及候補のみ", "周辺の発言者・任意", "周辺の発言に基づく候補です。実際の聞き手と言及先は文脈で確認してください。", "異なる話し手と言及対象を指定してください。"),
    "zh": ("仅第三方提及候选", "附近发言角色·选填", "候选基于附近发言。请结合上下文确认实际听话者和指代。", "请指定不同的说话角色和提及角色。"),
}.items():
    STRINGS[lang].update(zip(("third_party", "interlocutor", "mention_hint", "mention_error"), values, strict=True))


for lang, values in {
    "ko": ("선택지 · 화자 미확인", "원문 유형", "여러 선택지는 서로 다른 선택 항목입니다. 한 인물이 연달아 말한 대사나 박사의 발화로 확정하지 않습니다.", "주변 인물 조건 없이 검색", "현재 조건에 맞는 용례를 찾지 못했습니다. 주변 인물은 가까운 명시적 발화만 확인하므로 선택지나 더 먼 대화는 빠질 수 있습니다. 주변 인물 조건만 풀고 앞뒤 문맥을 확인할 수 있습니다."),
    "en": ("Choice · speaker unverified", "Source row type", "Multiple options are alternatives, not consecutive speech. They are not automatically attributed to the Doctor.", "Search without surrounding speaker", "No lines match these conditions. The surrounding-speaker condition checks nearby explicit turns, so choices and more distant turns may be missed. Remove only this condition to inspect the surrounding context."),
    "ja": ("選択肢・話者未確認", "原文の種類", "複数の選択肢は別々の候補であり、連続した発言ではありません。ドクターの発言とは自動判定しません。", "周辺の発言者の条件を外して検索", "現在の条件に一致する用例がありません。周辺の発言者は近くの明示的な発言で確認するため、選択肢や離れた発言は漏れる場合があります。この条件だけを外して文脈を確認できます。"),
    "zh": ("选项·说话者未确认", "原文类型", "多个选项是不同的选择，不是连续发言，也不会自动归为博士的台词。", "移除附近发言角色条件后搜索", "未找到符合当前条件的用例。附近发言角色条件仅核对附近的明确发言，因此可能遗漏选项或较远的发言。可仅移除此条件后查看上下文。"),
}.items():
    STRINGS[lang].update(zip(("choice_unknown", "row_kind", "choice_hint", "relax_interlocutor", "surrounding_empty"), values, strict=True))


# Describe the user's task rather than the internal candidate classification.
for lang, values in {
    "ko": ("다른 사람에게 언급", "대화 상대 · 선택", "가까운 발화를 기준으로 찾습니다. 정확한 대화 관계는 앞뒤 문맥에서 확인하세요.", "말하는 인물과 언급되는 인물을 다르게 입력하세요.", "언급되는 인물 (예: Mon3tr)", "대화 상대 · 선택 (예: 박사)"),
    "en": ("Mentioned to someone else", "Conversation partner · optional", "Matches use nearby turns. Check the surrounding context to confirm who is speaking to whom.", "Enter different speaking and mentioned characters.", "Character mentioned (e.g. Mon3tr)", "Conversation partner · optional (e.g. Doctor)"),
    "ja": ("別の相手に言及", "会話相手・任意", "近くの発言をもとに探します。実際の会話関係は前後の文脈で確認してください。", "話し手と言及される人物は別々に指定してください。", "言及される人物（例：Mon3tr）", "会話相手・任意（例：ドクター）"),
    "zh": ("向其他人提及", "对话对象·选填", "根据附近发言查找。请结合前后文确认实际对话关系。", "请分别填写不同的说话角色和提及角色。", "提及的角色（如 Mon3tr）", "对话对象·选填（如 博士）"),
}.items():
    STRINGS[lang].update(zip(("third_party", "interlocutor", "mention_hint", "mention_error", "mentioned_placeholder", "interlocutor_placeholder"), values, strict=True))
