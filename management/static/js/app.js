document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.querySelector(".sidebar");
  const toggle = document.querySelector("[data-menu-toggle]");
  if (sidebar && toggle) {
    toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
  }

  document.querySelectorAll(".message button").forEach((btn) =>
    btn.addEventListener("click", () => btn.closest(".message").remove())
  );
  document.querySelectorAll(".message.success").forEach((msg) =>
    setTimeout(() => msg.remove(), 6000)
  );
});
