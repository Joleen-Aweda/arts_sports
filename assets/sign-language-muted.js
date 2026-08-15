// Keep every sign-language video silent, including videos inserted after boot.
(function () {
  var nativePlay = HTMLMediaElement.prototype.play;
  var nativePause = HTMLMediaElement.prototype.pause;
  var nativeAddEventListener = EventTarget.prototype.addEventListener;
  var nativeSetAttribute = Element.prototype.setAttribute;
  var autoplayDescriptor = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, "autoplay");

  function isSignVideo(media) {
    return media instanceof HTMLVideoElement &&
      /\/content\/i18n\/[^/]+\/video\/page_\d+\.mp4(?:[?#]|$)/.test(media.currentSrc || media.src || "");
  }

  function mute(video) {
    if (!(video instanceof HTMLVideoElement)) return;
    video.defaultMuted = true;
    video.muted = true;
    video.volume = 0;
    video.setAttribute("muted", "");

    if (!isSignVideo(video) || video.dataset.signLanguageClone || video.dataset.signLanguageSource) return;

    // The reader treats its React-owned video as an alternative to narration.
    // Keep that element as the lifecycle anchor, but display an independent
    // clone so signing never changes the narration player's active state.
    video.dataset.signLanguageSource = "true";
    nativePause.call(video);
    video.removeAttribute("autoplay");
    video.style.display = "none";

    var clone = video.cloneNode(true);
    delete clone.dataset.signLanguageSource;
    clone.dataset.signLanguageClone = "true";
    clone.style.removeProperty("display");
    clone.defaultMuted = true;
    clone.muted = true;
    clone.volume = 0;
    clone.setAttribute("muted", "");
    clone.setAttribute("autoplay", "");
    clone.style.width = "100%";
    clone.style.height = "calc(100% - 1.5rem)";
    clone.style.objectFit = "contain";
    clone.style.background = "black";

    // A shadow root keeps the clone's native play event outside React's
    // delegated event tree while preserving the existing player layout.
    var host = document.createElement("div");
    host.dataset.signLanguageHost = "true";
    host.style.width = "100%";
    host.style.height = "100%";
    video.insertAdjacentElement("afterend", host);
    host.attachShadow({ mode: "open" }).appendChild(clone);
    clone.load();
    clone.play().catch(function () {});
  }

  function scan(root) {
    if (root instanceof HTMLVideoElement) mute(root);
    if (root && root.querySelectorAll) root.querySelectorAll("video").forEach(mute);
  }

  Element.prototype.setAttribute = function (name, value) {
    if (name.toLowerCase() === "autoplay" && isSignVideo(this) && !this.dataset.signLanguageClone) return;
    return nativeSetAttribute.call(this, name, value);
  };

  if (autoplayDescriptor && autoplayDescriptor.set) {
    Object.defineProperty(HTMLMediaElement.prototype, "autoplay", {
      configurable: autoplayDescriptor.configurable,
      enumerable: autoplayDescriptor.enumerable,
      get: autoplayDescriptor.get,
      set: function (value) {
        if (value && isSignVideo(this) && !this.dataset.signLanguageClone) return;
        return autoplayDescriptor.set.call(this, value);
      }
    });
  }

  // Allow narration and signing to continue together. Native video controls
  // still pause normally because they do not call this JavaScript method.
  HTMLMediaElement.prototype.play = function () {
    if (isSignVideo(this) && !this.dataset.signLanguageClone) {
      mute(this);
      return Promise.resolve();
    }
    return nativePlay.call(this);
  };

  HTMLMediaElement.prototype.pause = function () {
    if (isSignVideo(this)) return;
    return nativePause.call(this);
  };

  // Prevent the reader's delegated React play handler from marking signing as
  // the sole active medium and shutting narration down. Other play events and
  // listeners continue normally.
  EventTarget.prototype.addEventListener = function (type, listener, options) {
    if (type !== "play" || !listener) {
      return nativeAddEventListener.call(this, type, listener, options);
    }
    var guarded = function (event) {
      if (isSignVideo(event.target)) return;
      if (typeof listener === "function") return listener.call(this, event);
      return listener.handleEvent(event);
    };
    return nativeAddEventListener.call(this, type, guarded, options);
  };

  // Autoplay may begin as soon as React inserts its video, before the mutation
  // observer can replace it. Intercept that first event ahead of React's event
  // system so it cannot switch the active medium away from narration.
  nativeAddEventListener.call(document, "play", function (event) {
    if (isSignVideo(event.target)) event.stopImmediatePropagation();
  }, true);

  // The runtime changes its active-medium state as the signing panel opens.
  // If narration was already running, restore it immediately within the same
  // user gesture so the browser permits both streams to continue.
  nativeAddEventListener.call(document, "click", function (event) {
    var button = event.target && event.target.closest && event.target.closest('button[aria-label="Sign language"]');
    if (!button || !document.querySelector('button[aria-label="Pause"]')) return;
    setTimeout(function () {
      var narrationToggle = document.querySelector('button[aria-label="Deactivate text to speech"]');
      if (narrationToggle && !document.querySelector('button[aria-label="Pause"]')) narrationToggle.click();
    }, 200);
  }, true);

  scan(document);
  new MutationObserver(function (records) {
    records.forEach(function (record) {
      record.addedNodes.forEach(scan);
    });
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
