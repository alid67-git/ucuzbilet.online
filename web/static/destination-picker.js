(function () {
  const destInput = document.getElementById("destination-input");
  const destHidden = document.getElementById("destination-place-id");
  const clearBtn = document.getElementById("clear-destination");
  const field = document.getElementById("destination-airports-field");
  const grid = document.getElementById("destination-airport-grid");
  const hint = document.getElementById("destination-airport-hint");
  const savedAirports = window.__savedTargetAirports || [];

  if (!destInput || !destHidden || !field || !grid) return;

  function t(key, fallback) {
    const value = window.SiteLocale?.t(key);
    return value && value !== key ? value : fallback;
  }

  function clearGrid() {
    grid.innerHTML = "";
    field.hidden = true;
  }

  function selectedAirportIds() {
    return Array.from(grid.querySelectorAll('input[name="target_airports"]:checked')).map(
      (el) => el.value
    );
  }

  function updateHint() {
    if (!hint) return;
    const selected = selectedAirportIds();
    hint.textContent = selected.length
      ? t("airports_selected", "{n} yer secildi.").replace("{n}", String(selected.length))
      : t("airports_none_selected_hint", "Hicbiri isaretlenmezse tum ulke taranir.");
  }

  function escapeHtml(text) {
    return String(text)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  async function loadChildren(placeId) {
    const response = await fetch("/api/places/" + encodeURIComponent(placeId) + "/children");
    if (!response.ok) {
      clearGrid();
      return;
    }
    const children = await response.json();
    grid.innerHTML = "";
    if (!children.length) {
      field.hidden = true;
      return;
    }
    children.forEach((child) => {
      const label = document.createElement("label");
      label.className = "country-chip";
      const checked = savedAirports.includes(child.id) ? " checked" : "";
      label.innerHTML =
        '<input type="checkbox" name="target_airports" value="' +
        escapeHtml(child.id) +
        '"' +
        checked +
        "><span>" +
        escapeHtml(child.label) +
        "</span>";
      grid.appendChild(label);
    });
    grid.querySelectorAll('input[name="target_airports"]').forEach((el) => {
      el.addEventListener("change", updateHint);
    });
    field.hidden = false;
    updateHint();
  }

  destInput.addEventListener("place-selected", (event) => {
    const place = event.detail;
    savedAirports.length = 0;
    if (place && place.type === "country") {
      loadChildren(place.id);
    } else {
      clearGrid();
    }
  });

  destInput.addEventListener("input", () => {
    if (!destHidden.value) {
      clearGrid();
    }
  });

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      clearGrid();
    });
  }

  async function init() {
    if (!destHidden.value) return;
    try {
      const res = await fetch("/api/places/resolve?q=" + encodeURIComponent(destHidden.value));
      if (!res.ok) return;
      const data = await res.json();
      if (data.type === "country") {
        await loadChildren(data.id);
      }
    } catch (err) {
      /* sessizce yoksay */
    }
  }
  init();
  document.addEventListener("localechange", updateHint);
})();
