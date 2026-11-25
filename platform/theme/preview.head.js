/* Preview boot screen, early part - runs in <head> before paint, only in a preview.
   On the first page of a browser session it sets html.pv-booting, whose black cover
   (preview.css) hides the page until preview.js has the boot screen up. */
(function () {
  try {
    var root = document.documentElement;
    if (!root.hasAttribute("data-ctf-preview")) return;
    if (document.cookie.split("; ").indexOf("ctf-preview-booted=1") === -1) {
      root.classList.add("pv-booting");
    }
  } catch (e) {}
})();
