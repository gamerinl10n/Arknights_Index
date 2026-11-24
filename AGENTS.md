# Project rules

## Required pstack workflow

Before implementing, fixing, refactoring, or reviewing code, read and apply the [pstack poteto-mode instructions](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/SKILL.md) and the relevant playbook. If the plugin is unavailable, read the upstream files directly and use the tools available here. Report any source you could not read. Follow this repository's rules and the user's authorization for external actions.

Read README.md, docs/architecture.md, docs/development.md, and CONTRIBUTING.md before changes. Preserve Korean/Chinese/Japanese/English text and provenance. Never infer addressees from co-occurrence alone or label name matches as confirmed forms of address. Let users judge using context. Do not add administrator review, login, review records, or external review-storage dependencies. Never present synthetic dialogue as official. Never commit secrets, raw game dumps, or runtime databases. Run unit tests and JavaScript syntax checks. Ship changes via a feature branch and PR; report missing live-data verification explicitly.

Keep UI behavior in web/ui native ES modules and retrieval logic in search_queries.py/search_service.py/catalog.py. Reuse form-state.mjs for URL preservation. Do not reintroduce eager per-result context fetching or count scans. Retain legacy detailed API compatibility and mutable-archive freshness. Use the formatting and benchmark commands in docs/development.md for refactors; report local timings separately from deployed performance.

Treat 1.0.0 (2026-10-22) as the public baseline. Changelogs include only substantial user-facing features, compatibility changes or important fixes. Do not publish routine refactors, layout tweaks, internal milestones or a running development diary. Keep service notices self-contained; preserve rights, attribution and font notices without unnecessary outbound navigation.
