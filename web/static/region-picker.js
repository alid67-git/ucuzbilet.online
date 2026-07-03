(function () {
  const continentSelect = document.getElementById("target-continent");
  const countryGrid = document.getElementById("country-grid");
  const selectionHint = document.getElementById("country-selection-hint");
  const savedCountries = window.__savedTargetCountries || [];

  let continents = [];

  function selectedCountryIds() {
    if (!countryGrid) return [];
    return Array.from(countryGrid.querySelectorAll('input[name="target_countries"]:checked')).map(
      (input) => input.value
    );
  }

  function renderCountries(continentId) {
    if (!countryGrid) return;
    countryGrid.innerHTML = "";
    const continent = continents.find((item) => item.id === continentId);
    if (!continent || continentId === "anywhere") {
      countryGrid.hidden = true;
      if (selectionHint) {
        selectionHint.textContent = "Her yer secili — tum bolgeler taranir.";
      }
      return;
    }

    countryGrid.hidden = false;
    continent.countries.forEach((country) => {
      const label = document.createElement("label");
      label.className = "country-chip";
      const checked = savedCountries.includes(country.id) ? " checked" : "";
      label.innerHTML =
        '<input type="checkbox" name="target_countries" value="' +
        country.id +
        '"' +
        checked +
        ">" +
        '<span class="flag">' +
        (country.flag || "") +
        "</span>" +
        "<span>" +
        country.name +
        "</span>";
      countryGrid.appendChild(label);
    });

    countryGrid.querySelectorAll('input[name="target_countries"]').forEach((input) => {
      input.addEventListener("change", updateHint);
    });
    updateHint();
  }

  function updateHint() {
    if (!selectionHint) return;
    const selected = selectedCountryIds();
    if (selected.length === 0) {
      selectionHint.textContent = "Hic ulke secilmezse secili kitadaki tum ulkeler taranir.";
    } else {
      selectionHint.textContent = selected.length + " ulke secildi.";
    }
    document.dispatchEvent(new CustomEvent("region-selection-changed"));
  }

  async function init() {
    if (!continentSelect || !countryGrid) return;
    const response = await fetch("/api/regions");
    if (!response.ok) return;
    continents = await response.json();
    renderCountries(continentSelect.value);
    continentSelect.addEventListener("change", () => {
      savedCountries.length = 0;
      renderCountries(continentSelect.value);
    });
  }

  init();
})();
