import { el, t } from "./dom.mjs";

/** Literal intervals preserve source text; overlaps never nest markup. */
export function highlightedQuote(
  text,
  query = "",
  names = [],
  references = [],
) {
  const node = el("p", "", "quote");
  const events = new Map();
  function event(position, kind, delta) {
    if (!events.has(position)) events.set(position, [0, 0, 0]);
    events.get(position)[kind] += delta;
  }
  for (const [terms, kind] of [
    [[query], 0],
    [names || [], 1],
    [references || [], 2],
  ]) {
    for (const term of new Set(terms)) {
      if (!term) continue;
      let at = text.indexOf(term);
      while (at !== -1) {
        event(at, kind, 1);
        event(at + term.length, kind, -1);
        at = text.indexOf(term, at + 1);
      }
    }
  }
  if (!events.size) {
    node.textContent = text;
    return node;
  }
  event(0, 0, 0);
  event(text.length, 0, 0);
  const positions = [...events.keys()].sort((a, b) => a - b);
  let words = 0,
    people = 0,
    referring = 0;
  for (let i = 0; i < positions.length - 1; i++) {
    const start = positions[i],
      end = positions[i + 1];
    words += events.get(start)[0];
    people += events.get(start)[1];
    referring += events.get(start)[2];
    const content = text.slice(start, end);
    if (!words && !people && !referring)
      node.append(document.createTextNode(content));
    else {
      const mark = el("mark", content);
      if (words) mark.classList.add("query-highlight");
      if (people) {
        mark.classList.add("name-highlight");
        mark.title = t("name_match");
      }
      if (referring) {
        mark.classList.add("reference-highlight");
        mark.title = t("reference_span");
      }
      node.append(mark);
    }
  }
  return node;
}
