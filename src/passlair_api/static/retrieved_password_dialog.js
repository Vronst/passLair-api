// Shows the retrieved-password modal after a successful lookup, and lets the
// user click either value to copy it straight to the clipboard.
const dialog = document.getElementById("retrieved-password-dialog");

if (dialog) {
  dialog.showModal();

  for (const field of dialog.querySelectorAll("[data-copy]")) {
    field.addEventListener("click", () => {
      const original = field.textContent;
      navigator.clipboard.writeText(original).then(() => {
        field.textContent = "Copied!";
        setTimeout(() => {
          field.textContent = original;
        }, 1000);
      });
    });
  }
}
