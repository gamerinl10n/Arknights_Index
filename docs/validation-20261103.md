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

## Chromium follow-up — 2026-11-06

The earlier modified-source browser limitation was overcome with a read-only GitHub Actions browser job. [Run 42163675675](https://github.com/gamerinl10n/Arknights_Index/actions/runs/42163675675) passed the existing Python/JavaScript, syntax and formatting checks and all **30 Chromium browser cases** at `5ab5433a665ef79844042a8c7175dd4102df2f5b`. The browser job checked out that exact PR head and restored checksum-verified `dataset-8d8e4bc2c61e593c0ff0d514` before serving the unmodified Flask application locally on the runner. No production URL, deployment setting or access protection was changed.

Coverage:

- Desktop 1280×800; emulated touch viewports 320×568, 375×667, 390×844, 430×932 and landscape 844×390.
- Both character fields: initial ArrowUp chooses the last of 12 suggestions; ArrowDown/ArrowUp wrapping, ordinary Enter selection and Escape dismissal. Synthetic composing and legacy keyCode 229 events leave the value, active option and open list unchanged for Enter, Escape and both arrows.
- Korean `아미야`, Chinese `阿米娅` and Japanese `アーミヤ` composition/commit through Chromium's CDP input protocol. Composition start and composing input events were browser-trusted; the protocol's compositionend event was not trusted. Values and selection behavior were checked, and composition did not submit a search. This is protocol-driven coverage, not an operating-system IME test.
- Pointer/touch autocomplete selection, Korean phrase search on the English UI, three additional display languages, expanded context, source dialog, repeated help open/close, theme, settled Back/Forward navigation and footer visibility. Horizontal page overflow checks passed at the tested stages.
- Explicit touch start/move/end events changed the actual page scroll offset in every emulated touch viewport. Each context also verified scrolling on an isolated synthetic control page. The higher-level CDP scroll-gesture helper did not move the page reliably and is not used as evidence of scrolling.

Reproduce with Python dependencies installed, `npm ci --ignore-scripts`, `npx playwright install --with-deps chromium`, `python -c 'import dataset; assert dataset.reuse()'`, then `npm run test:browser`. The job has read-only repository permissions and retains its HTML test report and failure traces/screenshots for seven days. It does not publish a dataset or deploy the application.

Remaining limits and separate diagnostic:

- Emulation does not validate physical Android/iOS devices, mobile Safari, real Korean/Chinese/Japanese candidate windows, software-keyboard resizing or keyboard confirmation sequences. Those remain unverified; the browser tests must not be presented as real-device or real-IME QA.
- Rapid Back→Forward before a view transition was ready produced an unhandled `AbortError: Transition was skipped. skipTransition() called`. Results remained present in the recorded run. The unchanged `web/ui/navigation.mjs` handles the transition's `finished` promise but not `ready`; this separate diagnostic was not fixed in this autocomplete/testing change. Passing UI flows wait for real animation completion before the next navigation/gesture, rather than asserting that interrupted transitions are error-free.
- Story audio mapping/playback and the preview-only publication restriction remain unchanged. No merge or production promotion is covered by these checks.
