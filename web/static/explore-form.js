(function () {
  const modeSelect = document.getElementById("mode-select");
  const tripDatePanel = document.getElementById("trip-date-panel");
  const scopeField = document.getElementById("scope-field");
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

  const tripTypeDropdown = document.getElementById("trip-type-dropdown");
  const tripTypeToggle = document.getElementById("trip-type-toggle");
  const tripTypeMenu = document.getElementById("trip-type-menu");
  const tripTypeLabel = document.getElementById("trip-type-label");

  const passengerDropdown = document.getElementById("passenger-dropdown");
  const passengerToggle = document.getElementById("passenger-toggle");
  const passengerMenu = document.getElementById("passenger-menu");
  const passengerCountLabel = document.getElementById("passenger-count-label");
  const adultsCount = document.getElementById("adults-count");
  const childrenCount = document.getElementById("children-count");
  const adultsInput = document.getElementById("adults-input");
  const childrenInput = document.getElementById("children-input");
  const passengerCancel = document.getElementById("passenger-cancel");
  const passengerDone = document.getElementById("passenger-done");

  function t(key) {
    return window.SiteLocale ? window.SiteLocale.t(key) : key;
  }

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

    const dayUnit = t("date_hint_day_unit");
    if (flexSearch) {
      if (useReturn && dep && ret && span) {
        tripDateHint.textContent =
          t("date_hint_flex_prefix") +
          ": " +
          formatDateTr(dep) +
          " ±" +
          flexDays +
          " " +
          dayUnit +
          "; " +
          t("date_hint_return_prefix") +
          " " +
          formatDateTr(ret) +
          ".";
      } else if (dep) {
        tripDateHint.textContent =
          t("date_hint_flex_prefix") + ": " + formatDateTr(dep) + " ±" + flexDays + " " + dayUnit + ".";
      } else {
        tripDateHint.textContent = t("date_hint_default");
      }
    } else if (useReturn && dep && ret && span) {
      tripDateHint.textContent =
        t("date_hint_return_prefix") + ": " + formatDateTr(dep) + " → " + formatDateTr(ret) + " (" + span + " " + dayUnit + ").";
    } else if (dep) {
      tripDateHint.textContent = t("date_hint_oneway_prefix") + ": " + formatDateTr(dep) + " " + t("date_hint_no_return");
    } else {
      tripDateHint.textContent = t("date_hint_pick");
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
        originHint.textContent = t("origin_hint_default");
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
        destinationHint.textContent = t("dest_hint_hub_dest");
      } else if (hub) {
        destinationHint.textContent = t("dest_hint_hub_only");
      } else if (hasDest) {
        destinationHint.textContent = t("dest_hint_has_dest");
      } else {
        destinationHint.textContent = t("dest_hint_empty");
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
    if (!tripTypeMenu) return;
    tripTypeMenu.querySelectorAll(".trip-type-option[data-return]").forEach((option) => {
      const active = (option.dataset.return === "1") === useReturn;
      option.classList.toggle("active", active);
      option.setAttribute("aria-checked", active ? "true" : "false");
      if (active && tripTypeLabel) {
        const key = option.dataset.return === "1" ? "trip_round_trip" : "trip_one_way";
        tripTypeLabel.setAttribute("data-i18n", key);
        tripTypeLabel.textContent = t(key);
      }
    });
  }

  function setTripType(useReturn) {
    if (!useReturnCheckbox) return;
    useReturnCheckbox.checked = useReturn;
    useReturnCheckbox.dispatchEvent(new Event("change"));
    syncTripTypeTabs();
  }

  function closeTripTypeMenu() {
    if (!tripTypeMenu || !tripTypeToggle) return;
    tripTypeMenu.hidden = true;
    tripTypeToggle.setAttribute("aria-expanded", "false");
  }

  function openTripTypeMenu() {
    if (!tripTypeMenu || !tripTypeToggle) return;
    closePassengerMenu();
    tripTypeMenu.hidden = false;
    tripTypeToggle.setAttribute("aria-expanded", "true");
  }

  function initTripTypeDropdown() {
    if (!tripTypeDropdown || !tripTypeToggle || !tripTypeMenu) return;
    tripTypeToggle.addEventListener("click", (event) => {
      event.stopPropagation();
      if (tripTypeMenu.hidden) openTripTypeMenu();
      else closeTripTypeMenu();
    });
    tripTypeMenu.querySelectorAll(".trip-type-option[data-return]").forEach((option) => {
      option.addEventListener("click", () => {
        setTripType(option.dataset.return === "1");
        closeTripTypeMenu();
      });
    });
    document.addEventListener("click", (event) => {
      if (!tripTypeDropdown.contains(event.target)) closeTripTypeMenu();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeTripTypeMenu();
    });
  }

  function passengerTotal() {
    const adults = parseInt(adultsInput?.value || "1", 10) || 1;
    const children = parseInt(childrenInput?.value || "0", 10) || 0;
    return adults + children;
  }

  function updatePassengerLabel() {
    if (passengerCountLabel) passengerCountLabel.textContent = String(passengerTotal());
  }

  function clampPassengerCount(target, value) {
    if (target === "adults") return Math.min(9, Math.max(1, value));
    return Math.min(8, Math.max(0, value));
  }

  function adjustPassengerCount(target, delta) {
    const input = target === "adults" ? adultsInput : childrenInput;
    const display = target === "adults" ? adultsCount : childrenCount;
    if (!input) return;
    const next = clampPassengerCount(target, (parseInt(input.value || "0", 10) || 0) + delta);
    input.value = String(next);
    if (display) display.textContent = String(next);
    updatePassengerLabel();
  }

  let passengerSnapshot = null;

  function closePassengerMenu() {
    if (!passengerMenu || !passengerToggle) return;
    passengerMenu.hidden = true;
    passengerToggle.setAttribute("aria-expanded", "false");
  }

  function openPassengerMenu() {
    if (!passengerMenu || !passengerToggle) return;
    closeTripTypeMenu();
    passengerSnapshot = { adults: adultsInput?.value, children: childrenInput?.value };
    passengerMenu.hidden = false;
    passengerToggle.setAttribute("aria-expanded", "true");
  }

  function restorePassengerSnapshot() {
    if (!passengerSnapshot) return;
    if (adultsInput) adultsInput.value = passengerSnapshot.adults;
    if (childrenInput) childrenInput.value = passengerSnapshot.children;
    if (adultsCount) adultsCount.textContent = passengerSnapshot.adults;
    if (childrenCount) childrenCount.textContent = passengerSnapshot.children;
    updatePassengerLabel();
  }

  function initPassengerDropdown() {
    if (!passengerDropdown || !passengerToggle || !passengerMenu) return;
    passengerToggle.addEventListener("click", (event) => {
      event.stopPropagation();
      if (passengerMenu.hidden) openPassengerMenu();
      else closePassengerMenu();
    });
    passengerDropdown.querySelectorAll(".stepper-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        adjustPassengerCount(btn.dataset.target, parseInt(btn.dataset.delta, 10));
      });
    });
    if (passengerCancel) {
      passengerCancel.addEventListener("click", () => {
        restorePassengerSnapshot();
        closePassengerMenu();
      });
    }
    if (passengerDone) {
      passengerDone.addEventListener("click", () => {
        closePassengerMenu();
      });
    }
    document.addEventListener("click", (event) => {
      if (!passengerDropdown.contains(event.target)) closePassengerMenu();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closePassengerMenu();
    });
  }

  function shiftDateInput(input, delta) {
    if (!input || input.disabled) return;
    const base = input.value ? new Date(input.value + "T00:00:00") : new Date();
    base.setDate(base.getDate() + delta);
    const iso =
      base.getFullYear() +
      "-" +
      String(base.getMonth() + 1).padStart(2, "0") +
      "-" +
      String(base.getDate()).padStart(2, "0");
    if (input.min && iso < input.min) return;
    input.value = iso;
    input.dispatchEvent(new Event("change"));
  }

  function initDateShiftButtons() {
    document.querySelectorAll(".date-shift").forEach((btn) => {
      btn.addEventListener("click", () => {
        const input = document.getElementById(btn.dataset.target);
        shiftDateInput(input, parseInt(btn.dataset.delta, 10));
      });
    });
  }

  function syncModePanels() {
    syncFlexibleOption();
    syncOriginField();
    syncScopeField();
    syncHints();
    syncTripDatePanel();
  }

  modeSelect?.addEventListener("change", syncModePanels);
  useReturnCheckbox?.addEventListener("change", syncTripDatePanel);
  flexibleSearchCheckbox?.addEventListener("change", syncTripDatePanel);
  tripDeparture?.addEventListener("change", () => {
    syncReturnDateMinimum();
    syncTripDatePanel();
  });
  tripReturn?.addEventListener("change", syncTripDatePanel);
  flexibilityDaysInput?.addEventListener("input", syncTripDatePanel);

  if (hubCheckbox) hubCheckbox.addEventListener("change", syncModePanels);
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
  initTripTypeDropdown();
  initPassengerDropdown();
  initDateShiftButtons();
  updatePassengerLabel();

  document.addEventListener("localechange", () => {
    syncOriginField();
    syncHints();
    syncTripDatePanel();
  });

  syncModePanels();
})();
