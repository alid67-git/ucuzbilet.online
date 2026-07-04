(function () {
  const filtersPanel = document.getElementById("results-filters");
  if (!filtersPanel) return;

  const offerCards = Array.from(document.querySelectorAll(".offer[data-price]"));
  const countryGroups = Array.from(document.querySelectorAll(".country-group"));
  const stopsCheckboxes = Array.from(document.querySelectorAll(".filter-stops"));
  const airlinesContainer = document.getElementById("filter-airlines");
  const countriesContainer = document.getElementById("filter-countries");
  const priceInput = document.getElementById("filter-price");
  const priceValue = document.getElementById("filter-price-value");
  const durationInput = document.getElementById("filter-duration");
  const durationValue = document.getElementById("filter-duration-value");
  const resetBtn = document.getElementById("filter-reset");
  const summary = document.getElementById("filter-summary");

  function numAttr(el, name) {
    const raw = el.dataset[name];
    if (raw === undefined || raw === "") return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  }

  function formatPrice(v) {
    return Math.round(v).toLocaleString("tr-TR") + " TRY";
  }

  function formatDuration(mins) {
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return h + "sa " + m + "dk";
  }

  function uniqueSorted(values) {
    return Array.from(new Set(values.filter((v) => v))).sort((a, b) => a.localeCompare(b, "tr"));
  }

  function buildChipRow(container, values, className) {
    container.innerHTML = "";
    values.forEach((value) => {
      const label = document.createElement("label");
      label.className = "filter-chip";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.className = className;
      input.value = value;
      input.checked = true;
      label.appendChild(input);
      label.appendChild(document.createTextNode(" " + value));
      container.appendChild(label);
    });
  }

  const airlines = uniqueSorted(offerCards.map((c) => c.dataset.airline));
  buildChipRow(airlinesContainer, airlines, "filter-airline");

  const countries = uniqueSorted(offerCards.map((c) => c.dataset.country));
  buildChipRow(countriesContainer, countries, "filter-country");

  const prices = offerCards.map((c) => numAttr(c, "price")).filter((v) => v !== null);
  const durations = offerCards.map((c) => numAttr(c, "duration")).filter((v) => v !== null);

  const priceMin = prices.length ? Math.min(...prices) : 0;
  const priceMax = prices.length ? Math.max(...prices) : 0;
  const durationMin = durations.length ? Math.min(...durations) : 0;
  const durationMax = durations.length ? Math.max(...durations) : 0;

  priceInput.min = String(priceMin);
  priceInput.max = String(priceMax);
  priceInput.value = String(priceMax);
  priceInput.disabled = prices.length === 0;

  durationInput.min = String(durationMin);
  durationInput.max = String(durationMax);
  durationInput.value = String(durationMax);
  durationInput.disabled = durations.length === 0;

  function updatePriceLabel() {
    priceValue.textContent = prices.length ? formatPrice(Number(priceInput.value)) : "-";
  }
  function updateDurationLabel() {
    durationValue.textContent = durations.length ? formatDuration(Number(durationInput.value)) : "-";
  }
  updatePriceLabel();
  updateDurationLabel();

  function activeValues(selector) {
    return Array.from(document.querySelectorAll(selector))
      .filter((el) => el.checked)
      .map((el) => el.value);
  }

  function stopsMatches(stopsCount, activeStops) {
    if (stopsCount === null) return true;
    if (stopsCount === 0) return activeStops.includes("0");
    if (stopsCount === 1) return activeStops.includes("1");
    return activeStops.includes("2plus");
  }

  function applyFilters() {
    const activeStops = activeValues(".filter-stops");
    const activeAirlines = activeValues(".filter-airline");
    const activeCountries = activeValues(".filter-country");
    const maxPrice = Number(priceInput.value);
    const maxDuration = Number(durationInput.value);

    let visibleCount = 0;

    countryGroups.forEach((group) => {
      let groupHasVisible = false;
      const cards = group.querySelectorAll(".offer");
      cards.forEach((card) => {
        const stopsCount = numAttr(card, "stops");
        const airline = card.dataset.airline;
        const country = card.dataset.country;
        const price = numAttr(card, "price");
        const duration = numAttr(card, "duration");

        const stopsOk = stopsMatches(stopsCount, activeStops);
        const airlineOk = !airline || activeAirlines.includes(airline);
        const countryOk = !country || activeCountries.includes(country);
        const priceOk = price === null || price <= maxPrice;
        const durationOk = duration === null || duration <= maxDuration;

        const visible = stopsOk && airlineOk && countryOk && priceOk && durationOk;
        card.hidden = !visible;
        if (visible) {
          groupHasVisible = true;
          visibleCount += 1;
        }
      });
      group.hidden = !groupHasVisible;
    });

    if (summary) {
      summary.textContent = visibleCount + " sonuc gosteriliyor.";
    }
  }

  stopsCheckboxes.forEach((cb) => cb.addEventListener("change", applyFilters));
  airlinesContainer.addEventListener("change", applyFilters);
  countriesContainer.addEventListener("change", applyFilters);
  priceInput.addEventListener("input", () => {
    updatePriceLabel();
    applyFilters();
  });
  durationInput.addEventListener("input", () => {
    updateDurationLabel();
    applyFilters();
  });

  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      stopsCheckboxes.forEach((cb) => (cb.checked = true));
      document.querySelectorAll(".filter-airline, .filter-country").forEach((cb) => (cb.checked = true));
      priceInput.value = String(priceMax);
      durationInput.value = String(durationMax);
      updatePriceLabel();
      updateDurationLabel();
      applyFilters();
    });
  }

  applyFilters();
})();
