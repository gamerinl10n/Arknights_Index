import { $, reducedMotion } from "./dom.mjs";
export function createNavigation(experience) {
  let viewTransition,
    viewVersion = 0;
  function setView(view, animate = true, afterApply = () => {}) {
    const token = ++viewVersion,
      changed = experience.dataset.view !== view;
    const apply = () => {
      if (token !== viewVersion) return;
      experience.dataset.view = view;
      document.title = "Arknights Index";
      $("results-panel").hidden = view === "home";
      $("back-search").parentElement.hidden = view === "home";
      if (changed && view === "results")
        $("results-title").focus({ preventScroll: true });
      afterApply();
    };
    if (!changed || !animate || reducedMotion()) {
      viewTransition?.skipTransition();
      apply();
      return;
    }
    if (document.startViewTransition) {
      try {
        viewTransition?.skipTransition();
        viewTransition = document.startViewTransition(apply);
        // Skipping before the first frame rejects ready even when apply succeeds.
        viewTransition.ready.catch(() => {});
        viewTransition.finished.catch(() => {});
        return;
      } catch {
        /* Use the CSS entry transition on unsupported surfaces. */
      }
    }
    apply();
    experience.classList.remove("view-enter");
    void experience.offsetWidth;
    experience.classList.add("view-enter");
  }
  experience.addEventListener("animationend", () =>
    experience.classList.remove("view-enter"),
  );
  return setView;
}
