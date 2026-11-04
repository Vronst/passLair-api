// Shows the one-time backup phrase modal. It must only close via the OK
// button, so Escape (the dialog "cancel" event) is suppressed.
const dialog = document.getElementById("backup-phrase-dialog");

if (dialog) {
  dialog.addEventListener("cancel", (event) => event.preventDefault());
  dialog.showModal();
}
