(function () {
  const modeSelect = document.getElementById("mode-select");
  const tripDatePanel = document.getElementById("trip-date-panel");
  const scopeField = document.getElementById("scope-field");
  const allianceField = document.getElementById("alliance-field");
  const preferThyCheckbox = document.querySelector('input[name="prefer_thy"]');
  const hubCheckbox = document.getElementById("use-european-hubs");
  const hubHint = document.getElementById("hub-hint");
  const destinationHint = document.getElementById("destination-hint");
  const destinationLabel = document.getElementById("destination-label");
  const originField = document.getElementById("origin-field");
  const originHint = document.getElementById("origin-hint");
  const originHubNote = document.getElementById("origin-hub-note");
  const originInput = document.getElementById("origin-input");
  const originHidden = document.getElementById("origin-place-id");
  const destInput = document.getElementById("destination-input");
  const destHidden = document.getElementById("destination-place-id");
  const flexibleOption = document.getElementById("mode-flexible");
  const clearDestBtn = document.getElementById("clear-destination");
  const useReturnCheckbox = document.getElementById("use-return-date");
  const oneWayCheckbox = document.getElementById("one-way-trip");
  const flexibleSearchCheckbox = document.getElementById("flexible-search");
  const tripDeparture = document.getElementById("trip-departure");
  const tripReturn = document.getElementById("trip-return");
  const tripDaysInput = document.getElementById("trip-days");
  const flexibilityDaysInput = document.getElementById("flexibility-days");
  const tripDateHint = document.getElementById("trip-date-hint");

  function hasResolvedDestination() {
    return Boolean(destHidden?.value);
  }

  function isHubMode() {
    return Boolean(hubCheckbox?.checked);
  }

  function formatDateTr(iso) {
    if (!iso) return "";
    const parts = iso.split("-");
    if (parts.length !== 3) return iso;
    return parts[2] + "." + parts[1] + "." + parts[0];
  }

  function daysBetween(fromIso, toIso) {
    if (!fromIso || !toIso) return null;
    const from = new Date(fromIso + "T00:00:00");
    const to = new Date(toIso + "T00:00:00");
    const diff = Math.round((to - from) / (1000 * 60 * 60 * 24));
    return diff > 0 ? diff : null;
  }

  function syncTripDatePanel() {
    const isFlexibleMode = modeSelect?.value === "flexible";
    if (tripDatePanel) {
      tripDatePanel.hidden = isFlexibleMode;
      tripDatePanel.classList.toggle("field-hidden", isFlexibleMode);
    }
    if (isFlexibleMode) return;

    const useReturn = Boolean(useReturnCheckbox?.checked);
    const oneWay = Boolean(oneWayCheckbox?.checked);
    const flexSearch = Boolean(flexibleSearchCheckbox?.checked);

    if (tripReturn) {
      tripReturn.disabled = !useReturn || oneWay;
      if (!useReturn || oneWay) {
        tripReturn.removeAttribute("required");
      }
    }
    if (tripDaysInput) {
      tripDaysInput.disabled = useReturn || oneWay;
    }
    if (flexibilityDaysInput) {
      flexibilityDaysInput.disabled = !flexSearch;
    }

    const dep = tripDeparture?.value;
    const ret = tripReturn?.value;
    const days = parseInt(tripDaysInput?.value || "5", 10) || 5;
    const flexDays = parseInt(flexibilityDaysInput?.value || "3", 10) || 3;
    const span = daysBetween(dep, ret);

    if (!tripDateHint) return;

    if (flexSearch) {
      if (useReturn && dep && ret && span) {
        tripDateHint.textContent =
          "Esnek: " +
          formatDateTr(dep) +
          " ±" +
          flexDays +
          " gun icinde en ucuz gidis aranir; donus " +
          formatDateTr(ret) +
          " (en iyi 3 sonuc).";
      } else if (dep) {
        tripDateHint.textContent =
          "Esnek: " +
          formatDateTr(dep) +
          " ±" +
          flexDays +
          " gun icinde en ucuz gidis; " +
          days +
          " gun kalis (en iyi 3 sonuc).";
      } else {
        tripDateHint.textContent = "Esnek arama: gidis ±N gun, en ucuz 3 sonuc listelenir.";
      }
    } else if (useReturn && dep && ret && span) {
      tripDateHint.textContent =
        "Gidis-donus: " + formatDateTr(dep) + " gidis → " + formatDateTr(ret) + " donus (" + span + " gun).";
    } else if (oneWay && dep) {
      tripDateHint.textContent = "Tek gidiş: " + formatDateTr(dep) + " — sadece gidiş fiyati aranir.";
    } else if (dep) {
      tripDateHint.textContent =
        "Gidis-donus: " + formatDateTr(dep) + " gidis, " + days + " gun kalis (donus otomatik hesaplanir).";
    } else {
      tripDateHint.textContent = "Gidis tarihi secin. Tek gidiş, donus tarihi veya kalis suresi seceneklerinden birini kullanin.";
    }
  }

  function syncScopeField() {
    const showScope = !hasResolvedDestination();
    if (scopeField) {
      scopeField.hidden = !showScope;
      scopeField.classList.toggle("field-hidden", !showScope);
      scopeField.querySelectorAll("select, input").forEach((el) => {
        el.disabled = !showScope;
      });
    }
  }

  function syncAllianceField() {
    const thyOnly = Boolean(preferThyCheckbox?.checked);
    if (allianceField) {
      allianceField.hidden = thyOnly;
      allianceField.classList.toggle("field-hidden", thyOnly);
      const select = allianceField.querySelector("select");
      if (select) {
        select.disabled = thyOnly;
        if (thyOnly) {
          select.value = "any";
        }
      }
    }
  }

  function syncOriginField() {
    const hub = isHubMode();
    if (hub) {
      if (originInput) {
        originInput.value = "";
        originInput.disabled = true;
        originInput.readOnly = true;
        originInput.removeAttribute("required");
      }
      if (originHidden) originHidden.value = "";
      if (originField) originField.classList.add("field-passive");
      if (originHint) originHint.hidden = true;
      if (originHubNote) originHubNote.hidden = false;
    } else {
      if (originInput) {
        originInput.disabled = false;
        originInput.readOnly = false;
        originInput.setAttribute("required", "required");
      }
      if (originField) originField.classList.remove("field-passive");
      if (originHint) {
        originHint.hidden = false;
        originHint.textContent =
          'Italya yazinca "Italya — Tum havalimanlari" secin; altinda Roma, Milano, Venedik listelenir.';
      }
      if (originHubNote) originHubNote.hidden = true;
    }
  }

  function syncFlexibleOption() {
    const hub = isHubMode();
    if (flexibleOption) {
      flexibleOption.disabled = hub;
      if (hub && modeSelect.value === "flexible") {
        modeSelect.value = "fixed_trip";
      }
    }
  }

  function syncHints() {
    const hub = isHubMode();
    const hasDest = hasResolvedDestination();
    if (hubHint) hubHint.hidden = !hub;
    if (clearDestBtn) clearDestBtn.hidden = !hasDest;
    if (destinationLabel) {
      destinationLabel.textContent = "Varis (ulke / sehir / havalimani) — opsiyonel";
    }
    if (destinationHint) {
      if (hub && hasDest) {
        destinationHint.textContent =
          "Hub + belirli varis: Avrupa hub'larindan secilen varise gidilir.";
      } else if (hub) {
        destinationHint.textContent =
          "Hub secili: Avrupa hub'larindan taranir. Asagidaki bolge hedefi varis ulkelerini belirler.";
      } else if (hasDest) {
        destinationHint.textContent =
          "Belirli varis secildi. Bolge hedefi devre disi — temizlemek icin 'Varisi temizle'.";
      } else {
        destinationHint.textContent =
          "Bos birakirsaniz asagidaki bolge hedefiyle en ucuz destinasyonlar aranir.";
      }
    }
  }

  function clearDestination() {
    if (destInput) destInput.value = "";
    if (destHidden) destHidden.value = "";
    syncScopeField();
    syncHints();
  }

  function syncModePanels() {
    syncFlexibleOption();
    syncOriginField();
    syncScopeField();
    syncAllianceField();
    syncHints();
    syncTripDatePanel();
  }

  modeSelect?.addEventListener("change", syncModePanels);
  useReturnCheckbox?.addEventListener("change", () => {
    if (useReturnCheckbox.checked && oneWayCheckbox) {
      oneWayCheckbox.checked = false;
    }
    syncTripDatePanel();
  });
  oneWayCheckbox?.addEventListener("change", () => {
    if (oneWayCheckbox.checked) {
      if (useReturnCheckbox) useReturnCheckbox.checked = false;
    }
    syncTripDatePanel();
  });
  flexibleSearchCheckbox?.addEventListener("change", syncTripDatePanel);
  tripDeparture?.addEventListener("change", syncTripDatePanel);
  tripReturn?.addEventListener("change", syncTripDatePanel);
  tripDaysInput?.addEventListener("input", syncTripDatePanel);
  flexibilityDaysInput?.addEventListener("input", syncTripDatePanel);

  if (hubCheckbox) hubCheckbox.addEventListener("change", syncModePanels);
  if (preferThyCheckbox) preferThyCheckbox.addEventListener("change", syncAllianceField);
  if (clearDestBtn) {
    clearDestBtn.addEventListener("click", (event) => {
      event.preventDefault();
      clearDestination();
      if (destInput) destInput.focus();
    });
  }
  if (destInput) {
    destInput.addEventListener("input", () => {
      if (!destInput.value.trim() && destHidden) destHidden.value = "";
      syncScopeField();
      syncHints();
    });
    destInput.addEventListener("place-selected", () => {
      syncScopeField();
      syncHints();
    });
  }
  if (originInput) {
    originInput.addEventListener("place-selected", () => syncOriginField());
  }

  syncModePanels();
})();
