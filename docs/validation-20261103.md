# Search completion review — 2026-11-03

Base: `dc0110240aaad9741c3912e6ecb416c28e605ddd` (master).

## Changes prepared locally

- Autocomplete ignores composing keyboard events and legacy IME keyCode 229. Confirming Korean, Chinese or Japanese input must not accidentally choose a character suggestion.
- ArrowUp with no active suggestion selects the final option, rather than skipping it.
- Added a regression covering both behaviors and ordinary Enter selection.
- Existing design, search controls and data provenance are preserved.

## Validation

- Python: 79 tests passed.
- JavaScript: 57 tests passed, including the new regression.
- Prettier, changed JavaScript syntax checks and git diff whitespace checks passed.
- Build reused checksum-verified `dataset-8d8e4bc2c61e593c0ff0d514`.
- Materialized snapshot: 1,501,688 dialogue lines; SQLite quick_check: ok.
- Tested `/api/search` using all four display languages and each of `안녕`, `你好`, `こんにちは`, `hello` (16 combinations). Totals were respectively 850, 567, 315 and 94 for every display language. Every first-page row with an available verified page-language variant used that language as its main row.
- Some first pages contained one unmatched-language fallback. These rows had no verified page-language variant; they were not silently replaced or translated.
- Speaker-only M3: 810 matches. Target-only 凯尔希: 1,696 matches. Mon3tr → 凯尔希: 51 matches, ordered by nearby-turn rank descending (2, 1, 0). Context endpoint succeeded for each sampled filter result.
- Suggestions and home/help endpoints succeeded in all four languages.

## Public browser observations (existing production, not the local patch)

Using the actual English page, entered Korean `안녕` and submitted with the search button. The UI returned 850 lines and defaulted to English counterparts. The unverified Korean fallback carried an explicit notice. Enabled Korean, Chinese and Japanese display, expanded context, toggled dark mode and opened the help dialog. These interactions completed without a navigation error.

## Outstanding requirements and limitations

- Modified-source browser QA could not start: the managed preview service lacks Python (`sh: 1: python: not found`). Its launch also appends frontend-specific flags. No working application code was changed to compensate for this infrastructure limitation.
- The browser API exposes no viewport/device emulation. Mobile widths, touch scrolling and software-keyboard behavior remain unverified. Desktop production observations do not establish mobile correctness or validate the local IME fix in a real input method.
- Existing audio research has no verified story-line-to-recording mapping. No audio player, guessed sound URL or substituted character recording was introduced. Audio playback remains incomplete pending a reliable mapping/source.
- Current Vercel project `arknights_index` has SSO protection enabled for `all_except_custom_domains`. A preview must retain that protection and must not receive a production domain.
- The user subsequently approved pushing a feature branch, opening a PR and deploying an authenticated preview. Deployment results are recorded in the PR. This review is not a completion claim for mobile verification or audio playback; production promotion and access changes are outside this preview release.
