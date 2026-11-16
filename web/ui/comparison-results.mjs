import { el, t, isChoiceRow, speakerLabel } from "./dom.mjs";

const LABELS = {
  zh_CN: "中文",
  ko_KR: "한국어",
  ja_JP: "日本語",
  en_US: "English",
};

export function pairedQuote(item, needle, quote, infoButton, targetNames = {}) {
  const comparison = item.comparison;
  const box = el("div", "", "paired-quote");
  const matched = comparison.status === "matched";
  const rows = matched
    ? [item, ...comparison.items].sort((a, b) =>
        a.lang === "zh_CN" ? -1 : b.lang === "zh_CN" ? 1 : 0,
      )
    : [item];
  for (const row of rows) {
    const section = el("div", "", "paired-line");
    section.lang = row.lang.replace("_", "-");
    const heading = el("div", "", "paired-heading");
    const suffix =
      row.lang === "zh_CN"
        ? t("original_text") +
          (isChoiceRow(row) ? " · " + speakerLabel(row) : "")
        : speakerLabel(row);
    heading.append(el("span", `${LABELS[row.lang]} · ${suffix}`));
    if (row !== item) heading.append(infoButton(row));
    section.append(
      heading,
      quote(row.text, row === item ? needle : "", targetNames[row.lang]),
    );
    box.append(section);
  }
  if (!matched)
    box.append(
      el(
        "p",
        t(
          comparison.status === "unavailable"
            ? comparison.lang === "zh_CN"
              ? "original_unavailable"
              : "translation_unavailable"
            : "translation_unverified",
        ),
        "pair-status",
      ),
    );
  return box;
}

export function multilingualQuote(
  item,
  needle,
  quote,
  infoButton,
  targetNames = {},
) {
  const box = el("div", "", "multilingual-quote");
  const variants = item.variants || { [item.lang]: item };
  for (const lang of [
    item.lang,
    ...Object.keys(LABELS).filter((lang) => lang !== item.lang),
  ]) {
    const row = variants[lang];
    const section = el(
      "div",
      "",
      "paired-line" +
        (lang === item.lang ? " primary-language" : " secondary-language"),
    );
    section.dataset.variantLang = lang;
    section.dataset.primary = String(lang === item.lang);
    section.hidden = lang !== item.lang;
    section.lang = lang.replace("_", "-");
    const heading = el("div", "", "paired-heading");
    heading.append(el("span", LABELS[lang]));
    if (row && lang !== item.lang)
      heading.append(el("span", speakerLabel(row)), infoButton(row));
    section.append(heading);
    if (row) section.append(quote(row.text, needle, targetNames[row.lang]));
    else section.append(el("p", t("translation_unverified"), "pair-status"));
    if (lang === item.lang && item.main_language_missing)
      section.append(el("p", t("main_language_missing"), "pair-status"));
    box.append(section);
  }
  return box;
}
