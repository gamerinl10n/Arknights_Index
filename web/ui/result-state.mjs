import { $ } from "./dom.mjs";

/** A few detached result views, kept only for this tab's lifetime. */
export function createResultState({
  limit = 3,
  maxItems = 300,
  maxNodes = 20000,
} = {}) {
  const views = new Map();
  function save(key, state) {
    if (!key || $("search-experience").dataset.view !== "results") return;
    views.delete(key);
    const nodeCount = $("results").querySelectorAll("*").length;
    if (state.offset > maxItems || nodeCount > maxNodes) return;
    views.set(key, {
      ...state,
      nodeCount,
      scroll: window.scrollY,
      nodes: [...$("results").childNodes],
      title: [...$("results-title").childNodes],
      count: $("result-count").textContent,
      notice:
        $("results").getAttribute("aria-busy") === "true"
          ? ""
          : $("notice").textContent,
      empty: $("empty-state").hidden,
      relaxHidden: $("relax-interlocutor").hidden,
      emptyTitle: $("empty-state").querySelector("h3").textContent,
      emptyDescription: $("empty-state").querySelector("p").textContent,
      more: $("more").hidden,
    });
    while (
      views.size > limit ||
      [...views.values()].reduce((n, view) => n + view.offset, 0) > maxItems ||
      [...views.values()].reduce((n, view) => n + view.nodeCount, 0) > maxNodes
    )
      views.delete(views.keys().next().value);
  }
  function restore(key) {
    const view = views.get(key);
    if (!view) return null;
    views.delete(key);
    views.set(key, view);
    $("results").replaceChildren(...view.nodes);
    $("results-title").replaceChildren(...view.title);
    $("result-count").textContent = view.count;
    $("notice").textContent = view.notice;
    $("empty-state").hidden = view.empty;
    $("relax-interlocutor").hidden = view.relaxHidden;
    $("empty-state").querySelector("h3").textContent = view.emptyTitle;
    $("empty-state").querySelector("p").textContent = view.emptyDescription;
    $("more").hidden = view.more;
    return view;
  }
  return { save, restore, clear: () => views.clear() };
}
