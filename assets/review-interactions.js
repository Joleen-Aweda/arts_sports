(function () {
  function addStyles() {
    var style = document.createElement("style");
    style.textContent = ".review-control{margin-top:.5rem;border:2px solid #84cc16;border-radius:.65rem;background:#fff;padding:.55rem .75rem;font:inherit;color:#1f2937}.review-radio{width:1.25rem;height:1.25rem;margin:.3rem .75rem 0 0;accent-color:#65a30d;flex:none}.review-select{min-width:8rem}.review-answer{display:block;width:100%;min-height:5rem;resize:vertical}";
    document.head.appendChild(style);
  }

  function makeChoicesInteractive(root, prefix) {
    root.querySelectorAll(".questions > div").forEach(function (question, questionIndex) {
      question.querySelectorAll("label.activity-option").forEach(function (label, optionIndex) {
        if (label.querySelector("input")) return;
        var input = document.createElement("input");
        input.type = "radio";
        input.name = prefix + "-" + questionIndex;
        input.value = String(optionIndex + 1);
        input.className = "review-radio";
        var text = label.querySelector("[data-id]");
        if (text) input.setAttribute("aria-label", text.textContent.trim());
        label.insertBefore(input, label.firstChild);
      });
    });
  }

  function addTextInput(container, label) {
    if (container.querySelector(".review-control")) return;
    var input = document.createElement("input");
    input.type = "text";
    input.className = "review-control";
    input.setAttribute("aria-label", label);
    container.appendChild(input);
  }

  function addTrueFalse(container, label) {
    if (container.querySelector(".review-control")) return;
    var select = document.createElement("select");
    select.className = "review-control review-select";
    select.setAttribute("aria-label", label);
    ["Choose an answer", "TRUE", "FALSE"].forEach(function (text, index) {
      var option = document.createElement("option");
      option.value = index ? text : "";
      option.textContent = text;
      select.appendChild(option);
    });
    container.appendChild(select);
  }

  function setup() {
    addStyles();
    var page = document.querySelector('meta[name="title-id"]');
    page = page ? page.content : "";
    if (page === "pg076_sec001") {
      makeChoicesInteractive(document.querySelector('[data-section-id="pg076_sec001"]'), "test-one");
    }
    if (page === "pg077_sec001") {
      makeChoicesInteractive(document.querySelector('[data-section-id="pg077_sec001"]'), "test-one");
      document.querySelectorAll('[data-section-id="pg077_sec002"] [data-id="pg077_n0028"], [data-section-id="pg077_sec002"] [data-id="pg077_n0033"], [data-section-id="pg077_sec002"] [data-id="pg077_n0038"], [data-section-id="pg077_sec002"] [data-id="pg077_n0043"]').forEach(function (item) {
        addTrueFalse(item, "Choose the matching item from List B");
        var select = item.querySelector("select");
        select.firstElementChild.textContent = "Choose A to D";
        select.innerHTML = '<option value="">Choose A to D</option><option>A</option><option>B</option><option>C</option><option>D</option>';
      });
    }
    if (page === "pg078_sec001") {
      document.querySelectorAll('[data-section-id="pg078_sec001"] .fitb-sentence').forEach(function (item, index) {
        addTextInput(item, "Answer for question 3 item " + (index + 1));
      });
      document.querySelectorAll('[data-section-id="pg078_sec002"] .fitb-sentence').forEach(function (item, index) {
        addTrueFalse(item, "True or false for question 4 item " + (index + 1));
      });
    }
    if (page === "pg079_sec001") {
      document.querySelectorAll('[data-section-id="pg079_sec001"] .fitb-sentence').forEach(function (item, index) {
        addTrueFalse(item, "True or false continuation item " + (index + 3));
      });
      document.querySelectorAll('[data-section-id="pg079_sec002"] > div > div').forEach(function (item, index) {
        if (item.querySelector("textarea")) return;
        var answer = document.createElement("textarea");
        answer.className = "review-control review-answer";
        answer.setAttribute("aria-label", "Written answer for question " + (index + 5));
        item.appendChild(answer);
      });
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", setup);
  else setup();
})();
