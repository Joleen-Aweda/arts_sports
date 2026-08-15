// Keep every sign-language video silent, including videos inserted after boot.
(function () {
  function mute(video) {
    if (!(video instanceof HTMLVideoElement)) return;
    video.defaultMuted = true;
    video.muted = true;
    video.volume = 0;
    video.setAttribute("muted", "");
  }

  function scan(root) {
    if (root instanceof HTMLVideoElement) mute(root);
    if (root && root.querySelectorAll) root.querySelectorAll("video").forEach(mute);
  }

  scan(document);
  new MutationObserver(function (records) {
    records.forEach(function (record) {
      record.addedNodes.forEach(scan);
    });
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
