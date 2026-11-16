import { $ } from "./dom.mjs";

export function readForm() {
  if (!$("speaker")) return null;
  return {
    speaker: $("speaker").value.trim(),
    target: $("target").value.trim(),
    q: $("query").value.trim(),
    mention_mode: $("third-party")?.value || "all",
    interlocutor:
      $("third-party")?.value === "third_party_candidate"
        ? $("interlocutor").value.trim()
        : "",
    lang: $("lang").value,
    spoilers: $("spoilers").checked ? "1" : "0",
    all_languages: "1",
    show: [
      ...document.querySelectorAll(
        "[data-translation-lang][aria-pressed=true]:not(:disabled)",
      ),
    ]
      .map((node) => node.dataset.translationLang)
      .join(","),
  };
}

export function preserveForm(url = new URL(location.href)) {
  const draft = readForm();
  if (draft) {
    for (const [key, value] of Object.entries(draft))
      url.searchParams.set(key, value);
    url.searchParams.set("view", $("search-experience").dataset.view);
  }
  return url;
}

// Display languages change neither search identity nor the API cache key.
export function searchIdentity(search) {
  return JSON.stringify(
    Object.fromEntries(
      [
        "speaker",
        "target",
        "q",
        "lang",
        "spoilers",
        "all_languages",
        "mention_mode",
        "interlocutor",
      ].map((key) => [key, search[key] || ""]),
    ),
  );
}
