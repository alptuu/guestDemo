(function () {
  const form = document.getElementById("run-form");
  if (!form) return;

  const button = document.getElementById("run-btn");
  const label = button.querySelector("[data-label]");
  const errorBox = document.getElementById("run-error");
  const results = document.getElementById("results");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    button.disabled = true;
    button.classList.add("is-loading");
    label.textContent = "Çalışıyor…";

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Çalıştırma başarısız oldu.");

      const placeholder = document.getElementById("results-placeholder");
      if (placeholder) placeholder.remove();

      const holder = document.createElement("div");
      holder.className = "stack";
      holder.innerHTML = data.html;
      results.prepend(...holder.children);
      results.firstElementChild.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    } finally {
      button.disabled = false;
      button.classList.remove("is-loading");
      label.textContent = "Graph’ı çalıştır";
    }
  });
})();
