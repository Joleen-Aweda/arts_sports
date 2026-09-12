// Display the reader index (1-82) while preserving internal media page IDs (0-81).
(function () {
  var meta = document.querySelector('meta[name="page-section-id"]');
  var internal = meta ? Number.parseInt(meta.content, 10) : NaN;
  if (!Number.isFinite(internal)) return;
  var displayed = String(internal + 1);
  function update() {
    document.querySelectorAll("#nav-container div").forEach(function (node) {
      var spans = node.children;
      if (spans.length === 3 && spans[0].tagName === "SPAN" &&
          spans[1].textContent.trim() === "/" &&
          spans[0].textContent.trim() !== displayed) {
        spans[0].textContent = displayed;
      }
    });
  }
  update();
  new MutationObserver(update).observe(document.getElementById("nav-container"), {
    childList: true, subtree: true
  });
})();
