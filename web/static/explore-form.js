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
  const flexibleSearchCheckbox = document.getElementById("flexible-search");
  const tripDeparture = document.getElementById("trip-departure");
  const tripReturn = document.getElementById("trip-return");
  const tripDaysInput = document.getElementById("trip-days");
  const flexibilityDaysInput = document.getElementById("flexibility-days");
  const tripDateHint = document.getElementById("trip-date-hint");
  const swapButton = document.getElementById("swap-places");
  const tabOneWay = document.getElementById("tab-one-way");
  const tabRoundTrip = document.getElementById("tab-round-trip");

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

  function syncReturnDateMinimum() {
    if (!tripDeparture || !tripReturn) return;
    const dep = tripDeparture.value;
    if (!dep) return;
    tripReturn.min = dep;
    if (!tripReturn.value || tripReturn.value < dep) {
      tripReturn.value = dep;
    }
  }

  function resetReturnDateToDeparture() {
    if (!tripDeparture || !tripReturn) return;
    const dep = tripDeparture.value;
    if (!dep) return;
    tripReturn.min = dep;
    tripReturn.value = dep;
  }

  function syncTripDatePanel() {
    syncTripTypeTabs();
    syncReturnDateMinimum();
    const isFlexibleMode = modeSelect?.value === "flexible";
    if (tripDatePanel) {
      tripDatePanel.hidden = isFlexibleMode;
      tripDatePanel.classList.toggle("field-hidden", isFlexibleMode);
    }
    if (isFlexibleMode) return;

    const useReturn = Boolean(useReturnCheckbox?.checked);
    const flexSearch = Boolean(flexibleSearchCheckbox?.checked);

    if (tripReturn) {
      tripReturn.disabled = !useReturn;
      if (!useReturn) {
        tripReturn.removeAttribute("required");
      }
    }
    if (flexibilityDaysInput) {
      flexibilityDaysInput.disabled = !flexSearch;
    }

    const dep = tripDeparture?.value;
    const ret = tripReturn?.value;
    const flexDays = parseInt(flexibilityDaysInput?.value || "3", 10) || 3;
    const span = daysBetween(dep, ret);

    if (useReturn && dep && ret && span && tripDaysInput) {
      tripDaysInput.value = String(span);
    }

    if (!tripDateHint) return;

    if (flexSearch) {
      if (useReturn && dep && ret && span) {
        tripDateHint.textContent =
          "Esnek gidiş-donus: " +
          formatDateTr(dep) +
          " ±" +
          flexDays +
          " gun; donus " +
          formatDateTr(ret) +
          " (en iyi 3).";
      } else if (dep) {
        tripDateHint.textContent =
          "Esnek tek gidiş: " + formatDateTr(dep) + " ±" + flexDays + " gun (en iyi 3).";
      } else {
        tripDateHint.textContent = "Esnek arama: gidis ±N gun, en ucuz 3 sonuc.";
      }
    } else if (useReturn && dep && ret && span) {
      tripDateHint.textContent =
        "Gidis-donus: " + formatDateTr(dep) + " → " + formatDateTr(ret) + " (" + span + " gun).";
    } else if (dep) {
      tripDateHint.textContent = "Tek gidiş: " + formatDateTr(dep) + " — donus aranmaz.";
    } else {
      tripDateHint.textContent = "Gidis tarihi secin. Donus icin 'Donus tarihi belirle' isaretleyin.";
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
        originHint.textContent = "Ülke yazınca «tüm havalimanları» seçeneğini işaretleyin.";
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
    if (destinationHint) {
      destinationHint.hidden = false;
      if (hub && hasDest) {
        destinationHint.textContent = "Hub + belirli varış: seçilen hedefe hub'lardan gidilir.";
      } else if (hub) {
        destinationHint.textContent = "Hub seçili — bölge hedefi varış ülkelerini belirler.";
      } else if (hasDest) {
        destinationHint.textContent = "Belirli varış seçildi. Bölge hedefi kapalı.";
      } else {
        destinationHint.textContent = "Boş bırakırsanız aşağıdaki bölge hedefi kullanılır.";
      }
    }
    if (tripDateHint) tripDateHint.hidden = false;
  }

  function clearDestination() {
    if (destInput) destInput.value = "";
    if (destHidden) destHidden.value = "";
    syncScopeField();
    syncHints();
  }

  function swapPlaces() {
    if (isHubMode() || !originInput || !destInput) return;
    const originText = originInput.value;
    const originId = originHidden ? originHidden.value : "";
    const destText = destInput.value;
    const destId = destHidden ? destHidden.value : "";

    originInput.value = destText;
    if (originHidden) originHidden.value = destId;
    destInput.value = originText;
    if (destHidden) destHidden.value = originId;

    originInput.dispatchEvent(new Event("place-selected"));
    destInput.dispatchEvent(new Event("input"));
    destInput.dispatchEvent(new Event("place-selected"));
  }

  function syncTripTypeTabs() {
    const useReturn = Boolean(useReturnCheckbox?.checked);
    if (tabOneWay) tabOneWay.classList.toggle("active", !useReturn);
    if (tabRoundTrip) tabRoundTrip.classList.toggle("active", useReturn);
  }

  function setTripType(useReturn) {
    if (!useReturnCheckbox) return;
    useReturnCheckbox.checked = useReturn;
    useReturnCheckbox.dispatchEvent(new Event("change"));
    syncTripTypeTabs();
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
  useReturnCheckbox?.addEventListener("change", syncTripDatePanel);
  flexibleSearchCheckbox?.addEventListener("change", syncTripDatePanel);
  tripDeparture?.addEventListener("change", () => {
    resetReturnDateToDeparture();
    syncTripDatePanel();
  });
  tripReturn?.addEventListener("change", syncTripDatePanel);
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
  if (swapButton) {
    swapButton.addEventListener("click", (event) => {
      event.preventDefault();
      swapPlaces();
    });
  }
  if (tabOneWay) {
    tabOneWay.addEventListener("click", (event) => {
      event.preventDefault();
      setTripType(false);
    });
  }
  if (tabRoundTrip) {
    tabRoundTrip.addEventListener("click", (event) => {
      event.preventDefault();
      setTripType(true);
    });
  }

  syncModePanels();
})();
