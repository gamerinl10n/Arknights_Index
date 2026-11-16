import { $, t, reducedMotion } from "./ui/dom.mjs";
import { api } from "./ui/api.mjs";
import { bindSearchReset } from "./ui/search-reset.mjs";
import { readForm, searchIdentity } from "./ui/form-state.mjs";
import { createNavigation } from "./ui/navigation.mjs";
import { createComparisonControl } from "./ui/comparison-control.mjs";
import { createAutocomplete } from "./ui/autocomplete.mjs";
import { renderBatch } from "./ui/results.mjs";
import { createResultState } from "./ui/result-state.mjs";
import { setResultTitle } from "./ui/portraits.mjs";

let offset = 0,
  last = null,
  requestVersion = 0,
  controller,
  renderedKey = null;
const setView = createNavigation($("search-experience"));
const comparisonControl = createComparisonControl();
const autocomplete = createAutocomplete();
const resultState = createResultState();
if ("scrollRestoration" in history) history.scrollRestoration = "manual";
function rememberResults() {
  resultState.save(renderedKey, { offset, search: last });
}
function resumeResults(scroll) {
  comparisonControl.refresh();
  window.scrollTo?.({ top: scroll, behavior: "instant" });
  for (const panel of $("results").querySelectorAll("details[open]"))
    panel.dispatchEvent(new Event("toggle"));
}
function stopSearch() {
  ++requestVersion;
  controller?.abort();
  $("more").disabled = false;
  $("submit-search").disabled = false;
  $("submit-search").textContent = t("search");
  $("results").setAttribute("aria-busy", "false");
  $("search-loading").hidden = true;
}
function goHome(event, focusSearch = true) {
  event?.preventDefault();
  const draft = readForm();
  rememberResults();
  history.pushState(
    { draft },
    "",
    "/?" + new URLSearchParams({ ui: window.ASI.ui }),
  );
  stopSearch();
  autocomplete.close();
  setView("home");
  if (focusSearch)
    $(
      $("third-party").value === "reference_candidates" ? "target" : "speaker",
    ).focus({ preventScroll: true });
  else document.querySelector(".brand").focus({ preventScroll: true });
  window.scrollTo?.({
    top: 0,
    behavior: reducedMotion() ? "instant" : "smooth",
  });
}
$("back-search").onclick = goHome;
document.querySelector(".brand").addEventListener("click", (event) => {
  if (
    event.button === 0 &&
    !event.ctrlKey &&
    !event.metaKey &&
    !event.shiftKey &&
    !event.altKey
  )
    goHome(event, false);
});
bindSearchReset({
  autocomplete,
  stopSearch,
  onReset: () => {
    resultState.clear();
    offset = 0;
    last = null;
    renderedKey = null;
    $("results").replaceChildren();
    $("result-count").textContent = "";
    $("notice").textContent = "";
    $("empty-state").hidden = true;
    $("relax-interlocutor").hidden = true;
    $("more").hidden = true;
    setView("home");
  },
});
function empty(title, description) {
  $("empty-state").hidden = false;
  $("empty-state").querySelector("h3").textContent = title;
  $("empty-state").querySelector("p").textContent = description;
}
async function run(append = false) {
  const version = ++requestVersion,
    search = { ...last };
  controller?.abort();
  controller = new AbortController();
  $("more").disabled = true;
  $("submit-search").disabled = true;
  $("submit-search").textContent = t("loading");
  $("results").setAttribute("aria-busy", "true");
  if (!append) {
    $("results").replaceChildren();
    $("more").hidden = true;
    $("result-count").textContent = "";
    $("empty-state").hidden = true;
    $("relax-interlocutor").hidden = true;
  }
  $("notice").textContent = t("loading");
  $("search-loading").hidden = false;
  $("search-loading").dataset.append = String(append);
  if (!append) renderedKey = null;
  try {
    const params = new URLSearchParams(search);
    params.delete("show");
    params.set("offset", offset);
    params.set("details", "0");
    const data = await api("/api/search?" + params, {
      signal: controller.signal,
    });
    if (version !== requestVersion) return;
    renderBatch(data.items, search.q, {
      ...search,
      targetNames: data.highlights || {},
    });
    // The comparison observer applies visibility only to newly attached rows.
    offset += data.items.length;
    renderedKey = searchIdentity(search);
    $("more").hidden = offset >= data.total;
    const title =
      search.mention_mode === "reference_candidates"
        ? t("reference_title", { b: search.target })
        : search.speaker
          ? search.target
            ? t("search_pair", { a: search.speaker, b: search.target })
            : t("search_solo", { a: search.speaker })
          : search.q
            ? t("search_keyword", { q: search.q })
            : t("search_mention", { b: search.target });
    setResultTitle(title, data.participants, search);
    $("result-count").textContent = t("count", {
      n: data.total.toLocaleString(),
    });
    $("notice").textContent =
      search.mention_mode === "reference_candidates"
        ? t("reference_hint")
        : search.mention_mode === "third_party_candidate"
          ? t("mention_hint")
          : "";
    if (!data.total) {
      const canRelax =
        search.mention_mode === "third_party_candidate" &&
        Boolean(search.interlocutor);
      empty(
        t("no_results"),
        t(
          search.mention_mode === "reference_candidates"
            ? "reference_empty"
            : canRelax
              ? "surrounding_empty"
              : "broaden",
        ),
      );
      $("relax-interlocutor").hidden = !canRelax;
    }
  } catch (error) {
    if (version !== requestVersion || error.name === "AbortError") return;
    $("notice").textContent = t("failed");
    if (!append) empty(t("failed"), t("retry"));
  } finally {
    if (version === requestVersion) {
      $("more").disabled = false;
      $("submit-search").disabled = false;
      $("submit-search").textContent = t("search");
      $("results").setAttribute("aria-busy", "false");
      $("search-loading").hidden = true;
    }
  }
}
function clearFormErrors() {
  for (const id of ["query", "speaker", "target", "interlocutor"])
    $(id).setCustomValidity("");
}
function invalidField(id, key) {
  $(id).setCustomValidity(t(key));
  $(id).reportValidity();
}
function syncMentionMode() {
  const mode = $("third-party").value;
  const active = mode === "third_party_candidate";
  const references = mode === "reference_candidates";
  $("search").dataset.references = String(references);
  $("swap").hidden = references;
  $("speaker").placeholder = t(
    references ? "reference_speaker" : "speaker_placeholder",
  );
  const targetField = $("target").closest(".field");
  const speakerField = $("speaker").closest(".field");
  if (references) speakerField.before(targetField);
  else speakerField.after(targetField);
  $("third-party").closest(".search-bottom").dataset.mentionExpanded =
    references ? "references" : String(active);
  $("target").placeholder = t(
    references
      ? "reference_target"
      : active
        ? "mentioned_placeholder"
        : "target_placeholder",
  );
  $("interlocutor-field").hidden = !active;
  $("mention-hint").hidden = !active && !references;
  $("mention-hint").textContent = t(
    references ? "reference_hint" : "mention_hint",
  );
  document.querySelector('label[for="target"]').textContent = t(
    references ? "reference_target" : "target",
  );
  document.querySelector('label[for="speaker"]').textContent = t(
    references ? "reference_speaker" : "speaker",
  );
  clearFormErrors();
  autocomplete.close();
}
$("third-party").addEventListener("change", syncMentionMode);
function submit(updateUrl = true) {
  clearFormErrors();
  if ($("third-party").value === "reference_candidates") {
    if (!$("target").value.trim())
      return invalidField("target", "reference_required");
    if (
      $("speaker").value.trim() &&
      autocomplete.identity($("speaker").value) ===
        autocomplete.identity($("target").value)
    )
      return invalidField("speaker", "mention_error");
  }
  if ($("third-party").value === "third_party_candidate") {
    if (!$("speaker").value.trim())
      return invalidField("speaker", "speaker_required");
    if (!$("target").value.trim())
      return invalidField("target", "mentioned_required");
    const a = autocomplete.identity($("speaker").value);
    const b = autocomplete.identity($("target").value);
    const c = $("interlocutor").value.trim()
      ? autocomplete.identity($("interlocutor").value)
      : null;
    if (a === b) return invalidField("target", "mention_error");
    if (c !== null && (c === a || c === b))
      return invalidField("interlocutor", "partner_distinct");
  }
  if (!["speaker", "target", "query"].some((id) => $(id).value.trim()))
    return invalidField("query", "search_error");
  autocomplete.hydrate();
  const draft = readForm();
  rememberResults();
  if (updateUrl) {
    history.replaceState({ ...history.state, draft }, "", location.href);
    const params = new URLSearchParams(draft);
    params.set("ui", window.ASI.ui);
    history.pushState({ draft }, "", "/search?" + params);
  }
  offset = 0;
  last = draft;
  autocomplete.close();
  setView("results", true, () =>
    window.scrollTo?.({ top: 0, behavior: "instant" }),
  );
  run();
}
function restore(initial = false) {
  if (!initial) rememberResults();
  clearFormErrors();
  const params = new URLSearchParams(location.search),
    draft = history.state?.draft || {};
  $("third-party").value =
    params.get("mention_mode") ?? draft.mention_mode ?? "all";
  if (!$("third-party").value) $("third-party").value = "all";
  syncMentionMode();
  for (const key of ["speaker", "target", "interlocutor"])
    $(key).value = (params.get(key) ?? draft[key] ?? "").slice(0, 300);
  $("query").value = (params.get("q") ?? draft.q ?? "").slice(0, 300);
  $("lang").value = { ko: "ko_KR", zh: "zh_CN", ja: "ja_JP", en: "en_US" }[
    window.ASI.ui
  ];
  $("spoilers").checked = (params.get("spoilers") ?? draft.spoilers) === "1";
  comparisonControl.restore(params.get("show") ?? draft.show ?? "");
  autocomplete.load();
  const showResults =
    ["speaker", "target", "query"].some((id) => $(id).value.trim()) &&
    params.get("view") !== "home" &&
    (location.pathname === "/search" ||
      ["speaker", "target", "q"].some((key) => params.get(key)));
  if (showResults) {
    const search = readForm();
    const key = searchIdentity(search);
    const saved = resultState.restore(key);
    if (saved) {
      stopSearch();
      offset = saved.offset;
      last = search;
      renderedKey = key;
      setView("results", !initial, () => resumeResults(saved.scroll));
    } else {
      setView("results", !initial, () =>
        window.scrollTo?.({ top: 0, behavior: "instant" }),
      );
      if (renderedKey !== key) {
        offset = 0;
        last = search;
        run();
      }
    }
  } else {
    stopSearch();
    setView("home", !initial, () =>
      window.scrollTo?.({ top: 0, behavior: "instant" }),
    );
  }
}
for (const id of ["speaker", "target", "query", "interlocutor"])
  $(id).addEventListener("input", clearFormErrors);
$("search").onsubmit = (event) => {
  event.preventDefault();
  submit();
};
$("relax-interlocutor").onclick = () => {
  $("interlocutor").value = "";
  $("interlocutor").dispatchEvent(new Event("input", { bubbles: true }));
  submit();
};
$("more").onclick = () => run(true);
window.addEventListener("popstate", () => restore(false));
restore(true);
