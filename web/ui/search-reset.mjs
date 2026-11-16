import { $ } from "./dom.mjs";
import { readForm } from "./form-state.mjs";

export function bindSearchReset({
  autocomplete,
  stopSearch,
  onReset = () => {},
}) {
  $("reset-search").addEventListener("click", () => {
    stopSearch();
    for (const id of ["query", "speaker", "target", "interlocutor"]) {
      $(id).value = "";
      $(id).setCustomValidity("");
    }
    $("third-party").checked = false;
    $("third-party").dispatchEvent(new Event("change"));
    autocomplete.close();
    autocomplete.hydrate();
    const draft = readForm();
    const url = new URL("/", location.href);
    url.searchParams.set("ui", window.ASI.ui);
    for (const key of ["lang", "spoilers", "all_languages", "show"])
      url.searchParams.set(key, draft[key]);
    history.replaceState({ draft }, "", url);
    onReset();
  });
}
