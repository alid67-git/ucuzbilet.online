(function () {
  const btn = document.getElementById("scroll-top-btn");
  if (!btn) return;

  function toggle() {
    btn.hidden = window.scrollY < 400;
  }

  window.addEventListener("scroll", toggle, { passive: true });
  btn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  toggle();
})();
