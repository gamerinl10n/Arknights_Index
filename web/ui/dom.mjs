export const $ = (id) => document.getElementById(id);
export const t = (key, values = {}) =>
  Object.entries(values).reduce(
    (text, [key, value]) => text.replaceAll("{" + key + "}", String(value)),
    window.ASI.strings[key] || key,
  );
export const el = (tag, text = "", className = "") => {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
};
export const reducedMotion = () =>
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// The parser records the command's physical ordinal in branch provenance.
// Only that exact row is a choice; following dialogue inherits the branch.
export function isChoiceRow(row) {
  return (
    Number.isInteger(row.ordinal) &&
    typeof row.branch === "string" &&
    row.branch.startsWith(`decision@${row.ordinal}:`)
  );
}
export function speakerLabel(row) {
  return row.speaker || t(isChoiceRow(row) ? "choice_unknown" : "unnamed");
}
