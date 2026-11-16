import { $, t, el, isChoiceRow, speakerLabel } from "./dom.mjs";
import { api } from "./api.mjs";
import { portrait } from "./portraits.mjs";
import { pairedQuote, multilingualQuote } from "./comparison-results.mjs";
import { highlightedQuote } from "./highlight.mjs";
import { openDialog } from "./dialogs.mjs";

function infoButton(item, row = item) {
  const button = el("button", "?", "info-button");
  button.type = "button";
  button.title = t("source_details");
  button.setAttribute("aria-label", t("source_details"));
  button.setAttribute("aria-haspopup", "dialog");
  button.onclick = () => {
    const list = el("dl", "", "source-list");
    const fields = [
      ["source_file", item.path],
      ["source_line", String(row.ordinal + 1)],
      [
        "branch",
        !row.branch || row.branch === "main" ? t("main_branch") : row.branch,
      ],
      ["source_revision", item.revision],
      ["source", item.source],
      ["corpus", item.lang],
    ];
    if (item.reference_evidence) {
      fields.push(
        ["reference_portrait", item.reference_evidence.asset],
        [
          "reference_evidence_line",
          String(item.reference_evidence.ordinal + 1),
        ],
      );
    }
    if (isChoiceRow(row)) fields.push(["row_kind", t("choice_unknown")]);
    if (
      row.comparison?.method ||
      row.alignment_method ||
      item.comparison?.method
    )
      fields.push(["alignment_method", t("alignment_structure")]);
    for (const [key, value] of fields)
      list.append(el("dt", t(key)), el("dd", value));
    $("info-content").replaceChildren(
      list,
      el("p", t("branch_hint"), "source-hint"),
      ...(isChoiceRow(row) ? [el("p", t("choice_hint"), "source-hint")] : []),
    );
    openDialog($("info-dialog"), button);
  };
  return button;
}

function contextRows(
  rows,
  item,
  needle,
  matches = [item],
  options = {},
  cache = new Map(),
) {
  const fragment = document.createDocumentFragment();
  const retained = new Set();
  for (const row of rows) {
    retained.add(row.ordinal);
    const signature = JSON.stringify(row);
    const cached = cache.get(row.ordinal);
    if (cached?.signature === signature) {
      fragment.append(cached.node);
      continue;
    }
    const line = el(
      "div",
      "",
      "context-line" +
        (matches.some((match) => match.ordinal === row.ordinal)
          ? " current-line"
          : ""),
    );
    const heading = el("div", "", "context-heading");
    heading.append(
      portrait(row),
      el("strong", speakerLabel(row)),
      infoButton(item, row),
    );
    line.append(
      heading,
      row.variants
        ? multilingualQuote(
            row,
            needle,
            highlightedQuote,
            infoButton,
            options.targetNames,
          )
        : row.comparison
          ? pairedQuote(
              row,
              needle,
              highlightedQuote,
              infoButton,
              options.targetNames,
            )
          : highlightedQuote(
              row.text,
              needle,
              options.targetNames?.[row.lang || item.lang],
            ),
    );
    cache.set(row.ordinal, { signature, node: line });
    fragment.append(line);
  }
  for (const key of cache.keys()) if (!retained.has(key)) cache.delete(key);
  return fragment;
}

function renderCard(group, needle, index, options) {
  const compareParams =
    options.all_languages === "1"
      ? { all_languages: "1" }
      : options.compare === "1"
        ? { compare: "1", translation_lang: options.translation_lang }
        : {};
  const item = group[Math.floor((group.length - 1) / 2)];
  const initialRadius = Math.max(
    3,
    group[group.length - 1].ordinal - group[0].ordinal,
  );
  const card = el("article", "", "result-card");
  card.lang = item.lang.replace("_", "-");
  card.style.setProperty("--enter-delay", Math.min(index, 5) * 35 + "ms");
  if (
    options.mention_mode !== "reference_candidates" &&
    group.some((row) => row.nearby_turns > 0)
  )
    card.append(el("span", t("nearby_turns"), "evidence-label"));
  for (const row of group) {
    const referenceTerms = {};
    for (const ref of row.references || [])
      (referenceTerms[ref.lang] ||= []).push(...ref.expressions);
    const heading = el("div", "", "card-heading");
    heading.append(portrait(row), el("h2", speakerLabel(row)), infoButton(row));
    card.append(
      heading,
      row.variants
        ? multilingualQuote(
            row,
            needle,
            highlightedQuote,
            infoButton,
            options.targetNames,
            referenceTerms,
          )
        : row.comparison
          ? pairedQuote(
              row,
              needle,
              highlightedQuote,
              infoButton,
              options.targetNames,
              referenceTerms,
            )
          : highlightedQuote(
              row.text,
              needle,
              options.targetNames?.[row.lang || item.lang],
              referenceTerms[row.lang || item.lang],
            ),
    );
    for (const reference of row.references || []) {
      const evidence = el("div", "", "reference-evidence");
      evidence.append(
        el(
          "span",
          t(
            reference.status === "source_checked"
              ? "reference_documented"
              : "reference_candidate",
          ),
          "evidence-label",
        ),
      );
      evidence.append(
        el("p", reference.expressions.join(" · "), "reference-terms"),
      );
      const anchor = reference.anchor;
      evidence.append(
        el(
          "p",
          t("reference_evidence", {
            basis: t(reference.basis),
            n: anchor.ordinal + 1,
          }),
        ),
      );
      evidence.append(
        el("p", `${anchor.speaker || t("unnamed")}: ${anchor.text}`),
        infoButton({
          ...anchor,
          reference_evidence: reference.source_evidence,
        }),
      );
      card.append(evidence);
    }
  }

  // Network, line DOM and event handlers are created only when a section is opened.
  let detailRequest;
  const details = () => {
    if (!detailRequest) {
      detailRequest = item.context
        ? Promise.resolve({
            items: item.context,
            has_more: true,
          })
        : api(
            "/api/context?" +
              new URLSearchParams({
                story: item.story,
                ordinal: item.ordinal,
                radius: initialRadius,
                ...compareParams,
              }),
          );
      detailRequest = detailRequest.catch((error) => {
        detailRequest = null;
        throw error;
      });
    }
    return detailRequest;
  };
  function section(label, build) {
    const panel = el("details"),
      content = el("div");
    panel.append(el("summary", t(label)), content);
    let ready = false,
      loading = false;
    const load = async () => {
      if (ready || loading) return;
      loading = true;
      const status = el("p", t("loading"));
      status.setAttribute("role", "status");
      content.replaceChildren(status);
      try {
        const data = await details();
        if (!card.isConnected) return;
        build(content, data);
        ready = true;
      } catch {
        const retry = el("button", t("retry_action"));
        retry.type = "button";
        retry.onclick = load;
        content.replaceChildren(el("p", t("failed")), retry);
      } finally {
        loading = false;
      }
    };
    panel.addEventListener("toggle", () => {
      if (panel.open) load();
    });
    card.append(panel);
  }
  section("context", (content, data) => {
    const lines = el("div", "", "context-lines");
    const rowCache = new Map();
    lines.append(
      contextRows(data.items, item, needle, group, options, rowCache),
    );
    const expand = el("button", t("context_more"));
    expand.type = "button";
    let radius = initialRadius;
    expand.hidden = !data.has_more;
    expand.onclick = async () => {
      expand.disabled = true;
      try {
        const next = Math.min(radius + 15, 100);
        const data = await api(
          "/api/context?" +
            new URLSearchParams({
              story: item.story,
              ordinal: item.ordinal,
              radius: next,
              ...compareParams,
            }),
        );
        if (!card.isConnected) return;
        lines.replaceChildren(
          contextRows(data.items, item, needle, group, options, rowCache),
        );
        radius = next;
        expand.hidden = !data.has_more || radius >= 100;
        expand.textContent = t("context_more");
      } catch {
        expand.textContent = t("retry_action");
      } finally {
        expand.disabled = false;
      }
    };
    content.replaceChildren(lines, expand);
  });

  return card;
}

export function renderBatch(items, needle = "", options = {}) {
  const fragment = document.createDocumentFragment(),
    offset = $("results").children.length;
  const groups = [];
  for (const item of items) {
    const group = groups[groups.length - 1];
    const first = group?.[0];
    const previous = group?.[group.length - 1];
    // Only combine overlapping windows on this page; retain every matched quote.
    if (
      first &&
      first.story === item.story &&
      first.branch === item.branch &&
      item.ordinal > previous.ordinal &&
      item.ordinal - first.ordinal <= 6
    )
      group.push(item);
    else groups.push([item]);
  }
  groups.forEach((group, index) =>
    fragment.append(renderCard(group, needle, offset + index, options)),
  );
  $("results").append(fragment);
}
