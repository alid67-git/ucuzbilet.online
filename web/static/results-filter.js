(function () {
  const filtersPanel = document.getElementById("results-filters");
  if (!filtersPanel) return;

  const offerCards = Array.from(document.querySelectorAll(".offer[data-price]"));
  const countryGroups = Array.from(document.querySelectorAll(".country-group"));
  const flatContainer = document.getElementById("flat-results");
  const originalOrder = offerCards.map((el) => ({ el, parent: el.parentElement }));

  const stopsCheckboxes = Array.from(document.querySelectorAll(".filter-stops"));
  const airlinesContainer = document.getElementById("filter-airlines");
  const airlinesSummary = document.getElementById("filter-airlines-summary");
  const countriesContainer = document.getElementById("filter-countries");
  const countriesSummary = document.getElementById("filter-countries-summary");
  const originCountriesContainer = document.getElementById("filter-origin-countries");
  const originCountriesSummary = document.getElementById("filter-origin-countries-summary");
  const durationInput = document.getElementById("filter-duration");
  const durationValue = document.getElementById("filter-duration-value");
  const resetBtn = document.getElementById("filter-reset");
  const summary = document.getElementById("filter-summary");
  const priceRangeHighlight = document.getElementById("price-range-highlight");
  const sortSelect = document.getElementById("sort-select");
  const paginationControls = document.getElementById("pagination-controls");
  const pageSizeInput = document.getElementById("page-size-input");
  const pagePrevBtn = document.getElementById("page-prev");
  const pageNextBtn = document.getElementById("page-next");
  const pageIndicator = document.getElementById("page-indicator");
  const tierTabs = Array.from(document.querySelectorAll("#airline-tier-tabs .trip-type-tab"));

  let currentPage = 1;

  function numAttr(el, name) {
    const raw = el.dataset[name];
    if (raw === undefined || raw === "") return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  }

  function formatPrice(v) {
    if (window.SiteLocale && window.SiteLocale.formatFromTry) {
      return window.SiteLocale.formatFromTry(v);
    }
    return Math.round(v).toLocaleString("tr-TR") + " TRY";
  }

  function refreshOfferPrices() {
    document.querySelectorAll(".price[data-price-try]").forEach((el) => {
      const raw = el.getAttribute("data-price-try");
      if (!raw) return;
      const n = Number(raw);
      if (Number.isFinite(n)) el.textContent = formatPrice(n);
    });
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

  function buildCountryChipRow(container, cards, datasetKey, className) {
    container.innerHTML = "";
    const byCountry = new Map();
    cards.forEach((c) => {
      const country = c.dataset[datasetKey];
      if (!country) return;
      const price = numAttr(c, "price");
      if (!byCountry.has(country)) byCountry.set(country, []);
      if (price !== null) byCountry.get(country).push(price);
    });
    Array.from(byCountry.keys())
      .sort((a, b) => a.localeCompare(b, "tr"))
      .forEach((country) => {
        const prices = byCountry.get(country);
        const label = document.createElement("label");
        label.className = "filter-chip";
        const input = document.createElement("input");
        input.type = "checkbox";
        input.className = className;
        input.value = country;
        input.checked = true;
        label.appendChild(input);
        let text = " " + country;
        if (prices.length) {
          text += " (" + formatPrice(Math.min(...prices)) + " - " + formatPrice(Math.max(...prices)) + ")";
        }
        label.appendChild(document.createTextNode(text));
        container.appendChild(label);
      });
  }

  function snapshotCountryChecks(className) {
    const checks = new Map();
    document.querySelectorAll("." + className).forEach((cb) => checks.set(cb.value, cb.checked));
    return checks;
  }

  function restoreCountryChecks(className, previous) {
    if (!previous.size) return;
    const allChecked = Array.from(previous.values()).every(Boolean);
    document.querySelectorAll("." + className).forEach((cb) => {
      if (allChecked) {
        cb.checked = true;
      } else if (previous.has(cb.value)) {
        cb.checked = previous.get(cb.value);
      } else {
        cb.checked = true;
      }
    });
  }

  function rebuildCountryChipRow(container, cards, datasetKey, className) {
    const previous = snapshotCountryChecks(className);
    buildCountryChipRow(container, cards, datasetKey, className);
    restoreCountryChecks(className, previous);
  }

  const AIRLINE_GROUPS = {
    thy: ["turkish airlines"],
    star_alliance: [
      "turkish airlines", "lufthansa", "austrian", "swiss", "united", "air canada",
      "singapore airlines", "thai", "air china", "ana", "asiana airlines", "avianca",
      "brussels airlines", "copa airlines", "croatia airlines", "egyptair",
      "ethiopian airlines", "eva air", "lot polish airlines", "scandinavian airlines", "sas",
      "shenzhen airlines", "south african airways", "tap air portugal", "air india",
    ],
    oneworld: [
      "american airlines", "british airways", "cathay pacific", "finnair", "iberia",
      "japan airlines", "malaysia airlines", "qantas", "qatar airways",
      "royal air maroc", "royal jordanian", "srilankan airlines", "fiji airways", "alaska airlines",
    ],
    skyteam: [
      "air france", "klm", "delta", "aeroflot", "aerolineas argentinas",
      "aeromexico", "air europa", "china airlines", "china eastern", "china southern",
      "czech airlines", "garuda indonesia", "kenya airways", "korean air", "middle east airlines",
      "saudia", "tarom", "vietnam airlines", "xiamen airlines", "ita airways",
    ],
    ulcc: [
      "ryanair", "wizz air", "spirit airlines", "frontier", "indigo",
    ],
    lcc: [
      "pegasus", "easyjet", "wizz air", "vueling", "eurowings", "flydubai", "air arabia",
      "norwegian", "condor", "transavia", "volotea", "scoot", "jetstar", "bangkok airways",
      "airasia", "sunexpress",
    ],
  };

  function airlineComboMatchesGroup(comboValue, groupNames) {
    const lower = comboValue.toLowerCase();
    return groupNames.some((name) => lower.includes(name));
  }

  function matchesLowCostModel(comboValue) {
    return (
      airlineComboMatchesGroup(comboValue, AIRLINE_GROUPS.lcc) ||
      airlineComboMatchesGroup(comboValue, AIRLINE_GROUPS.ulcc)
    );
  }

  const airlines = uniqueSorted(offerCards.map((c) => c.dataset.airline));
  buildChipRow(airlinesContainer, airlines, "filter-airline");
  buildCountryChipRow(countriesContainer, offerCards, "country", "filter-country");
  buildCountryChipRow(originCountriesContainer, offerCards, "originCountry", "filter-origin-country");

  const prices = offerCards.map((c) => numAttr(c, "price")).filter((v) => v !== null);
  const durations = offerCards.map((c) => numAttr(c, "duration")).filter((v) => v !== null);

  const priceMin = prices.length ? Math.min(...prices) : 0;
  const priceMax = prices.length ? Math.max(...prices) : 0;
  const durationMin = durations.length ? Math.min(...durations) : 0;
  const durationMax = durations.length ? Math.max(...durations) : 0;

  if (priceRangeHighlight) {
    priceRangeHighlight.textContent = prices.length
      ? "Fiyat araligi: " + formatPrice(priceMin) + " - " + formatPrice(priceMax)
      : "";
  }

  durationInput.min = String(durationMin);
  durationInput.max = String(durationMax);
  durationInput.value = String(durationMax);
  durationInput.disabled = durations.length === 0;

  function updateDurationLabel() {
    durationValue.textContent = durations.length ? formatDuration(Number(durationInput.value)) : "-";
  }
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

  function updateAirlineSummary() {
    if (!airlinesSummary) return;
    const total = document.querySelectorAll(".filter-airline").length;
    const checked = document.querySelectorAll(".filter-airline:checked").length;
    airlinesSummary.textContent = "Havayolu (" + checked + "/" + total + " secili)";
  }

  function updateCountrySummary() {
    if (!countriesSummary) return;
    const total = document.querySelectorAll(".filter-country").length;
    const checked = document.querySelectorAll(".filter-country:checked").length;
    const label = window.SiteLocale ? window.SiteLocale.t("filter_destination_country") : "Gidis ulkesi";
    countriesSummary.textContent = label + " (" + checked + "/" + total + " secili)";
  }

  function updateOriginCountrySummary() {
    if (!originCountriesSummary) return;
    const total = document.querySelectorAll(".filter-origin-country").length;
    const checked = document.querySelectorAll(".filter-origin-country:checked").length;
    const label = window.SiteLocale ? window.SiteLocale.t("filter_departure_country") : "Cikis ulkesi";
    originCountriesSummary.textContent = label + " (" + checked + "/" + total + " secili)";
  }

  function restoreGroupedView() {
    originalOrder.forEach(({ el, parent }) => parent.appendChild(el));
  }

  function cardsForCountryPricing() {
    const activeStops = activeValues(".filter-stops");
    const activeAirlines = activeValues(".filter-airline");
    const maxDuration = Number(durationInput.value);

    return offerCards.filter((card) => {
      const stopsCount = numAttr(card, "stops");
      const airline = card.dataset.airline;
      const duration = numAttr(card, "duration");
      const stopsOk = stopsMatches(stopsCount, activeStops);
      const airlineOk = !airline || activeAirlines.includes(airline);
      const durationOk = duration === null || duration <= maxDuration;
      return stopsOk && airlineOk && durationOk;
    });
  }

  function refreshCountryPriceLabels() {
    const pricingCards = cardsForCountryPricing();
    rebuildCountryChipRow(originCountriesContainer, pricingCards, "originCountry", "filter-origin-country");
    rebuildCountryChipRow(countriesContainer, pricingCards, "country", "filter-country");

    const tierPrices = pricingCards.map((c) => numAttr(c, "price")).filter((v) => v !== null);
    if (priceRangeHighlight) {
      priceRangeHighlight.textContent = tierPrices.length
        ? "Fiyat araligi: " + formatPrice(Math.min(...tierPrices)) + " - " + formatPrice(Math.max(...tierPrices))
        : "";
    }
  }

  function computeRecommendationScores(cards) {
    const scores = new Map();
    if (!cards.length) return scores;
    const priceVals = cards.map((c) => numAttr(c, "price")).filter((v) => v !== null);
    const durationVals = cards.map((c) => numAttr(c, "duration")).filter((v) => v !== null);
    const stopsVals = cards.map((c) => numAttr(c, "stops")).filter((v) => v !== null);
    const pMin = priceVals.length ? Math.min(...priceVals) : 0;
    const pMax = priceVals.length ? Math.max(...priceVals) : 0;
    const dMin = durationVals.length ? Math.min(...durationVals) : 0;
    const dMax = durationVals.length ? Math.max(...durationVals) : 0;
    const sMin = stopsVals.length ? Math.min(...stopsVals) : 0;
    const sMax = stopsVals.length ? Math.max(...stopsVals) : 0;
    const norm = (v, min, max) => (v === null || max === min ? 0 : (v - min) / (max - min));
    cards.forEach((c) => {
      const p = numAttr(c, "price");
      const d = numAttr(c, "duration");
      const s = numAttr(c, "stops");
      const score = 0.5 * norm(p, pMin, pMax) + 0.3 * norm(d, dMin, dMax) + 0.2 * norm(s, sMin, sMax);
      scores.set(c, score);
    });
    return scores;
  }

  function sortCards(cards, mode) {
    if (mode === "price") {
      return cards.sort((a, b) => (numAttr(a, "price") ?? Infinity) - (numAttr(b, "price") ?? Infinity));
    }
    if (mode === "duration") {
      return cards.sort((a, b) => (numAttr(a, "duration") ?? Infinity) - (numAttr(b, "duration") ?? Infinity));
    }
    if (mode === "stops") {
      return cards.sort((a, b) => {
        const sa = numAttr(a, "stops") ?? Infinity;
        const sb = numAttr(b, "stops") ?? Infinity;
        if (sa !== sb) return sa - sb;
        return (numAttr(a, "price") ?? Infinity) - (numAttr(b, "price") ?? Infinity);
      });
    }
    if (mode === "recommended") {
      const scores = computeRecommendationScores(cards);
      return cards.sort((a, b) => (scores.get(a) ?? Infinity) - (scores.get(b) ?? Infinity));
    }
    return cards;
  }

  function refresh() {
    const activeStops = activeValues(".filter-stops");
    const activeAirlines = activeValues(".filter-airline");
    const activeCountries = activeValues(".filter-country");
    const activeOriginCountries = activeValues(".filter-origin-country");
    const maxDuration = Number(durationInput.value);

    const passing = [];
    offerCards.forEach((card) => {
      const stopsCount = numAttr(card, "stops");
      const airline = card.dataset.airline;
      const country = card.dataset.country;
      const originCountry = card.dataset.originCountry;
      const duration = numAttr(card, "duration");

      const stopsOk = stopsMatches(stopsCount, activeStops);
      const airlineOk = !airline || activeAirlines.includes(airline);
      const countryOk = !country || activeCountries.includes(country);
      const originCountryOk = !originCountry || activeOriginCountries.includes(originCountry);
      const durationOk = duration === null || duration <= maxDuration;

      const ok = stopsOk && airlineOk && countryOk && originCountryOk && durationOk;
      if (ok) {
        passing.push(card);
      } else {
        card.hidden = true;
      }
    });

    updateAirlineSummary();
    updateCountrySummary();
    updateOriginCountrySummary();

    const sortMode = sortSelect ? sortSelect.value : "country";

    if (sortMode === "country") {
      restoreGroupedView();
      flatContainer.hidden = true;
      if (paginationControls) paginationControls.hidden = true;

      countryGroups.forEach((group) => {
        const cards = Array.from(group.querySelectorAll(".offer"));
        let anyVisible = false;
        cards.forEach((card) => {
          const visible = passing.includes(card);
          card.hidden = !visible;
          if (visible) anyVisible = true;
        });
        group.hidden = !anyVisible;
      });

      if (summary) summary.textContent = passing.length + " sonuc gosteriliyor.";
      return;
    }

    const sorted = sortCards(passing.slice(), sortMode);
    countryGroups.forEach((g) => (g.hidden = true));
    flatContainer.hidden = false;
    sorted.forEach((card) => flatContainer.appendChild(card));

    if (paginationControls) paginationControls.hidden = false;
    const pageSize = Math.max(1, Number(pageSizeInput.value) || 20);
    const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;
    const startIdx = (currentPage - 1) * pageSize;
    const endIdx = startIdx + pageSize;

    sorted.forEach((card, idx) => {
      card.hidden = idx < startIdx || idx >= endIdx;
    });

    if (pageIndicator) pageIndicator.textContent = "Sayfa " + currentPage + " / " + totalPages;
    if (pagePrevBtn) pagePrevBtn.disabled = currentPage <= 1;
    if (pageNextBtn) pageNextBtn.disabled = currentPage >= totalPages;

    if (summary) {
      const shown = Math.max(0, Math.min(pageSize, sorted.length - startIdx));
      summary.textContent = sorted.length + " sonuctan " + shown + " tanesi gosteriliyor.";
    }
  }

  function applyAirlineTier(tier) {
    const allAirlineCheckboxes = Array.from(document.querySelectorAll(".filter-airline"));
    if (tier === "lcc") {
      allAirlineCheckboxes.forEach((cb) => {
        cb.checked = airlineComboMatchesGroup(cb.value, AIRLINE_GROUPS.lcc);
      });
    } else if (tier === "ulcc") {
      allAirlineCheckboxes.forEach((cb) => {
        cb.checked = airlineComboMatchesGroup(cb.value, AIRLINE_GROUPS.ulcc);
      });
    } else if (tier === "fsc") {
      allAirlineCheckboxes.forEach((cb) => {
        cb.checked = !matchesLowCostModel(cb.value);
      });
    } else if (tier === "thy") {
      allAirlineCheckboxes.forEach((cb) => {
        cb.checked = airlineComboMatchesGroup(cb.value, AIRLINE_GROUPS.thy);
      });
    } else {
      allAirlineCheckboxes.forEach((cb) => (cb.checked = true));
    }
  }

  function applyTierTabLabels() {
    if (!window.SiteLocale) return;
    const tips = {
      lcc: window.SiteLocale.t("tier_lcc_tip"),
      ulcc: window.SiteLocale.t("tier_ulcc_tip"),
      fsc: window.SiteLocale.t("tier_fsc_tip"),
      thy: window.SiteLocale.t("tier_thy_tip"),
    };
    tierTabs.forEach((tab) => {
      const key = "tier_" + tab.dataset.tier;
      if (tab.dataset.tier !== "all" && window.SiteLocale.t(key)) {
        tab.title = tips[tab.dataset.tier] || "";
      }
      if (window.SiteLocale.t(key)) tab.textContent = window.SiteLocale.t(key);
    });
  }

  const groupButtons = Array.from(document.querySelectorAll("[data-airline-group]"));
  groupButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const wasActive = btn.classList.contains("active");
      groupButtons.forEach((b) => b.classList.remove("active"));
      tierTabs.forEach((t) => t.classList.toggle("active", t.dataset.tier === "all"));
      const allAirlineCheckboxes = Array.from(document.querySelectorAll(".filter-airline"));

      if (wasActive) {
        allAirlineCheckboxes.forEach((cb) => (cb.checked = true));
      } else {
        const groupNames = AIRLINE_GROUPS[btn.dataset.airlineGroup] || [];
        allAirlineCheckboxes.forEach((cb) => {
          cb.checked = airlineComboMatchesGroup(cb.value, groupNames);
        });
        btn.classList.add("active");
      }
      currentPage = 1;
      refreshCountryPriceLabels();
      refresh();
    });
  });

  function setTier(tier) {
    tierTabs.forEach((t) => t.classList.toggle("active", t.dataset.tier === tier));
    groupButtons.forEach((b) => b.classList.remove("active"));
    applyAirlineTier(tier);
    currentPage = 1;
    refreshCountryPriceLabels();
    refresh();
  }
  tierTabs.forEach((tab) => tab.addEventListener("click", () => setTier(tab.dataset.tier)));

  stopsCheckboxes.forEach((cb) =>
    cb.addEventListener("change", () => {
      currentPage = 1;
      refreshCountryPriceLabels();
      refresh();
    })
  );
  airlinesContainer.addEventListener("change", () => {
    currentPage = 1;
    refreshCountryPriceLabels();
    refresh();
  });
  countriesContainer.addEventListener("change", () => {
    currentPage = 1;
    refresh();
  });
  originCountriesContainer.addEventListener("change", () => {
    currentPage = 1;
    refresh();
  });
  durationInput.addEventListener("input", () => {
    updateDurationLabel();
    currentPage = 1;
    refreshCountryPriceLabels();
    refresh();
  });
  if (sortSelect) {
    sortSelect.addEventListener("change", () => {
      currentPage = 1;
      refresh();
    });
  }
  if (pageSizeInput) {
    pageSizeInput.addEventListener("change", () => {
      currentPage = 1;
      refresh();
    });
  }
  if (pagePrevBtn) {
    pagePrevBtn.addEventListener("click", () => {
      currentPage = Math.max(1, currentPage - 1);
      refresh();
    });
  }
  if (pageNextBtn) {
    pageNextBtn.addEventListener("click", () => {
      currentPage += 1;
      refresh();
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      stopsCheckboxes.forEach((cb) => (cb.checked = true));
      document
        .querySelectorAll(".filter-airline, .filter-country, .filter-origin-country")
        .forEach((cb) => (cb.checked = true));
      groupButtons.forEach((btn) => btn.classList.remove("active"));
      tierTabs.forEach((t) => t.classList.toggle("active", t.dataset.tier === "all"));
      durationInput.value = String(durationMax);
      updateDurationLabel();
      if (sortSelect) sortSelect.value = "country";
      if (pageSizeInput) pageSizeInput.value = "20";
      currentPage = 1;
      refreshCountryPriceLabels();
      refresh();
    });
  }

  refresh();
  applyTierTabLabels();
  refreshOfferPrices();
  document.addEventListener("localechange", () => {
    applyTierTabLabels();
    refreshCountryPriceLabels();
    refreshOfferPrices();
    refresh();
  });
})();
