(function () {
  const continentSelect = document.getElementById("target-continent");
  const countryGrid = document.getElementById("country-grid");
  const selectionHint = document.getElementById("country-selection-hint");
  const savedCountries = window.__savedTargetCountries || [];

  let continents = [];

  function t(key, fallback) {
    const value = window.SiteLocale?.t(key);
    return value && value !== key ? value : fallback;
  }

  function currentLang() {
    return window.SiteLocale ? window.SiteLocale.lang() : "tr";
  }

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
        selectionHint.textContent = t("region_anywhere_hint", "Her yer secili — tum bolgeler taranir.");
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
      selectionHint.textContent = t(
        "region_no_country_hint",
        "Hic ulke secilmezse secili kitadaki tum ulkeler taranir."
      );
    } else {
      selectionHint.textContent = t("region_countries_selected", "{n} ulke secildi.").replace(
        "{n}",
        String(selected.length)
      );
    }
    document.dispatchEvent(new CustomEvent("region-selection-changed"));
  }

  async function loadRegions() {
    if (!continentSelect || !countryGrid) return;
    const response = await fetch("/api/regions?lang=" + encodeURIComponent(currentLang()));
    if (!response.ok) return;
    continents = await response.json();
    renderCountries(continentSelect.value);
  }

  async function init() {
    if (!continentSelect || !countryGrid) return;
    await loadRegions();
    continentSelect.addEventListener("change", () => {
      savedCountries.length = 0;
      renderCountries(continentSelect.value);
    });
    document.addEventListener("localechange", () => {
      const previouslyChecked = selectedCountryIds();
      loadRegions().then(() => {
        if (continentSelect.value === "anywhere") return;
        countryGrid.querySelectorAll('input[name="target_countries"]').forEach((input) => {
          input.checked = previouslyChecked.includes(input.value);
        });
        updateHint();
      });
    });
  }

  init();
})();
