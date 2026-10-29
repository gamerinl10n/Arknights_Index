let initialized = false;
let opener;
export function openDialog(dialog, trigger) {
  initDialogs();
  if (dialog.open) return;
  opener = trigger || document.activeElement;
  dialog.showModal();
  document.documentElement.classList.add("modal-open");
}
export function initDialogs() {
  if (initialized) return;
  initialized = true;
  const dialogs = [...document.querySelectorAll("dialog.modal")];
  dialogs.forEach((dialog) => {
    dialog
      .querySelector("[data-close-dialog]")
      .addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => {
      const r = dialog.getBoundingClientRect();
      if (
        event.target === dialog &&
        (event.clientX < r.left ||
          event.clientX > r.right ||
          event.clientY < r.top ||
          event.clientY > r.bottom)
      )
        dialog.close();
    });
    dialog.addEventListener("close", () => {
      document.documentElement.classList.remove("modal-open");
      if (opener?.isConnected) opener.focus({ preventScroll: true });
    });
  });
  const help = document.getElementById("help-dialog"),
    button = document.getElementById("help-button");
  button.addEventListener("click", (event) => {
    // Keep native link behavior for new tabs and browsers without dialogs.
    if (
      event.button !== 0 ||
      event.ctrlKey ||
      event.metaKey ||
      event.shiftKey ||
      event.altKey ||
      typeof help.showModal !== "function"
    )
      return;
    event.preventDefault();
    openDialog(help, button);
  });
  if (new URLSearchParams(location.search).get("help") === "1")
    openDialog(help, button);
}
