(function () {
  const tripTrigger = document.getElementById("gf-trip-trigger");
  const tripMenu = document.getElementById("gf-trip-menu");
  const paxTrigger = document.getElementById("gf-pax-trigger");
  const paxPopover = document.getElementById("gf-pax-popover");
  const cabinTrigger = document.getElementById("gf-cabin-trigger");
  const cabinMenu = document.getElementById("gf-cabin-menu");
  const datesTrigger = document.getElementById("gf-dates-trigger");
  const calendarPopover = document.getElementById("gf-calendar-popover");
  const useReturnCb = document.getElementById("use-return-date");
  const adultsInput = document.getElementById("gf-adults");
  const childrenInput = document.getElementById("gf-children");
  const infantsSeatInput = document.getElementById("gf-infants-seat");
  const infantsLapInput = document.getElementById("gf-infants-lap");
  const adultsHidden = document.querySelector('input[name="adults"]');
  const childrenHidden = document.querySelector('input[name="children"]');
  const cabinHidden = document.querySelector('input[name="cabin_class"]');
  const depInput = document.getElementById("trip-departure");
  const retInput = document.getElementById("trip-return");
  const depDay = document.getElementById("gf-dep-day");
  const depMeta = document.getElementById("gf-dep-meta");
  const retDay = document.getElementById("gf-ret-day");
  const retMeta = document.getElementById("gf-ret-meta");
  const depChip = document.getElementById("gf-dep-chip");
  const retChip = document.getElementById("gf-ret-wrap");
  const tripTypeLabel = document.getElementById("trip-type-label");
  const passengerCountLabel = document.getElementById("passenger-count-label");

  function t(key, fallback) {
    const value = window.SiteLocale?.t(key);
    return value && value !== key ? value : fallback;
  }

  const MONTHS_TR = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
  ];
  const WEEKDAYS_TR = [
    "Pazar", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi",
  ];

  const CABIN_LABELS = {
    economy: "Ekonomi",
    "premium-economy": "Premium ekonomi",
    business: "Business",
    first: "First",
  };

  function closeAll(except) {
    [tripMenu, paxPopover, cabinMenu, calendarPopover].forEach((el) => {
      if (el && el !== except) el.hidden = true;
    });
    [tripTrigger, paxTrigger, cabinTrigger, datesTrigger].forEach((btn) => {
      if (btn) btn.setAttribute("aria-expanded", btn === except ? "true" : "false");
    });
  }

  function togglePopover(panel, trigger) {
    if (!panel || !trigger) return;
    const open = panel.hidden;
    closeAll(open ? panel : null);
    panel.hidden = !open;
    trigger.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function formatDateChip(iso) {
    const d = iso ? new Date(iso + "T00:00:00") : null;
    if (!d || Number.isNaN(d.getTime())) {
      return { day: "—", meta: t("date_hint_pick", "Tarih seçin"), empty: true };
    }
    return {
      day: String(d.getDate()),
      meta: MONTHS_TR[d.getMonth()] + " · " + WEEKDAYS_TR[d.getDay()],
      empty: false,
    };
  }

  function applyDateChip(dayEl, metaEl, chipEl, iso) {
    const chip = formatDateChip(iso);
    if (dayEl) dayEl.textContent = chip.day;
    if (metaEl) metaEl.textContent = chip.meta;
    if (chipEl) chipEl.classList.toggle("is-empty", chip.empty);
  }

  function shiftDate(iso, delta) {
    const d = new Date(iso + "T00:00:00");
    if (Number.isNaN(d.getTime())) return iso;
    d.setDate(d.getDate() + delta);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return y + "-" + m + "-" + day;
  }

  function syncTripTriggerLabel() {
    if (!useReturnCb) return;
    const round = useReturnCb.checked;
    const label = t(round ? "trip_round_trip" : "trip_one_way", round ? "Gidiş-dönüş" : "Tek yön");
    if (tripTypeLabel) {
      tripTypeLabel.textContent = label;
    }
    tripMenu?.querySelectorAll("[data-trip]").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.trip === (round ? "round" : "oneway"));
    });
  }

  function passengerTotal() {
    const a = parseInt(adultsInput?.value || "1", 10) || 1;
    const c = parseInt(childrenInput?.value || "0", 10) || 0;
    return a + c;
  }

  function syncPassengerHidden() {
    if (adultsHidden && adultsInput) adultsHidden.value = adultsInput.value;
    if (childrenHidden && childrenInput) {
      childrenHidden.value = String(parseInt(childrenInput.value || "0", 10) || 0);
    }
    if (passengerCountLabel) {
      passengerCountLabel.textContent = String(passengerTotal());
    }
  }

  function syncCabinTrigger() {
    if (!cabinTrigger || !cabinHidden) return;
    const activeBtn = cabinMenu?.querySelector(`[data-cabin="${cabinHidden.value}"]`);
    const label = activeBtn?.textContent?.trim() || CABIN_LABELS[cabinHidden.value] || cabinHidden.value;
    cabinTrigger.innerHTML = label + ' <span class="caret" aria-hidden="true">▾</span>';
    cabinMenu?.querySelectorAll("[data-cabin]").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.cabin === cabinHidden.value);
    });
  }

  function syncDateDisplays() {
    const round = Boolean(useReturnCb?.checked);
    const dep = depInput?.value || "";
    const ret = retInput?.value || "";
    applyDateChip(depDay, depMeta, depChip, dep);
    if (retChip) {
      retChip.hidden = !round;
      if (round) applyDateChip(retDay, retMeta, retChip, ret);
    }
    if (datesTrigger) datesTrigger.classList.toggle("gf-dates-oneway", !round);
    window.TripDateCalendar?.refresh();
  }

  function bindCounter(minusId, plusId, input, min, max) {
    const minus = document.getElementById(minusId);
    const plus = document.getElementById(plusId);
    if (!input) return;
    minus?.addEventListener("click", () => {
      const v = Math.max(min, (parseInt(input.value, 10) || 0) - 1);
      input.value = String(v);
      syncPassengerHidden();
    });
    plus?.addEventListener("click", () => {
      const v = Math.min(max, (parseInt(input.value, 10) || 0) + 1);
      input.value = String(v);
      syncPassengerHidden();
    });
  }

  tripTrigger?.addEventListener("click", (e) => {
    e.stopPropagation();
    togglePopover(tripMenu, tripTrigger);
  });

  tripMenu?.querySelectorAll("[data-trip]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const round = btn.dataset.trip === "round";
      if (useReturnCb) {
        useReturnCb.checked = round;
        useReturnCb.dispatchEvent(new Event("change", { bubbles: true }));
      }
      syncTripTriggerLabel();
      syncDateDisplays();
      closeAll();
    });
  });

  paxTrigger?.addEventListener("click", (e) => {
    e.stopPropagation();
    togglePopover(paxPopover, paxTrigger);
  });

  document.getElementById("gf-pax-cancel")?.addEventListener("click", () => closeAll());
  document.getElementById("gf-pax-done")?.addEventListener("click", () => {
    syncPassengerHidden();
    closeAll();
  });

  cabinTrigger?.addEventListener("click", (e) => {
    e.stopPropagation();
    togglePopover(cabinMenu, cabinTrigger);
  });

  cabinMenu?.querySelectorAll("[data-cabin]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (cabinHidden) cabinHidden.value = btn.dataset.cabin || "economy";
      syncCabinTrigger();
      closeAll();
    });
  });

  datesTrigger?.addEventListener("click", (e) => {
    if (e.target.closest(".gf-date-nudge")) return;
    e.stopPropagation();
    togglePopover(calendarPopover, datesTrigger);
    window.TripDateCalendar?.refresh();
  });
  datesTrigger?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      togglePopover(calendarPopover, datesTrigger);
      window.TripDateCalendar?.refresh();
    }
  });

  document.getElementById("gf-dep-prev")?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!depInput?.value) return;
    depInput.value = shiftDate(depInput.value, -1);
    depInput.dispatchEvent(new Event("change", { bubbles: true }));
    syncDateDisplays();
  });
  document.getElementById("gf-dep-next")?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!depInput?.value) return;
    depInput.value = shiftDate(depInput.value, 1);
    depInput.dispatchEvent(new Event("change", { bubbles: true }));
    syncDateDisplays();
  });
  document.getElementById("gf-ret-prev")?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!retInput?.value || retInput.disabled) return;
    retInput.value = shiftDate(retInput.value, -1);
    retInput.dispatchEvent(new Event("change", { bubbles: true }));
    syncDateDisplays();
  });
  document.getElementById("gf-ret-next")?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!retInput?.value || retInput.disabled) return;
    retInput.value = shiftDate(retInput.value, 1);
    retInput.dispatchEvent(new Event("change", { bubbles: true }));
    syncDateDisplays();
  });

  bindCounter("gf-adults-minus", "gf-adults-plus", adultsInput, 1, 9);
  bindCounter("gf-children-minus", "gf-children-plus", childrenInput, 0, 8);

  document.addEventListener("localechange", () => {
    syncTripTriggerLabel();
    syncCabinTrigger();
    syncDateDisplays();
  });

  document.addEventListener("click", (e) => {
    if (
      e.target.closest(".gf-dropdown") ||
      e.target.closest(".gf-calendar-popover") ||
      e.target.closest("#gf-dates-trigger")
    ) {
      return;
    }
    closeAll();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAll();
  });

  useReturnCb?.addEventListener("change", syncDateDisplays);
  depInput?.addEventListener("change", syncDateDisplays);
  retInput?.addEventListener("change", syncDateDisplays);

  document.querySelectorAll(".route-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const originInput = document.getElementById("origin-input");
      const originHidden = document.getElementById("origin-place-id");
      const destInput = document.getElementById("destination-input");
      const destHidden = document.getElementById("destination-place-id");
      const hubCheckbox = document.getElementById("use-european-hubs");
      if (!originInput || !originHidden || !destInput || !destHidden) return;

      // Hub modu acikken origin alani devre disi kalir; belirli bir kalkis
      // secmek istedigimiz icin once hub modunu kapatiyoruz.
      if (hubCheckbox && hubCheckbox.checked) {
        hubCheckbox.checked = false;
        hubCheckbox.dispatchEvent(new Event("change"));
      }

      const originPlace = {
        id: chip.dataset.originCode,
        type: "airport",
        label: chip.dataset.originLabel,
      };
      const destPlace = {
        id: chip.dataset.destCode,
        type: "airport",
        label: chip.dataset.destLabel,
      };

      originInput.value = originPlace.label;
      originHidden.value = originPlace.id;
      originInput.dispatchEvent(new CustomEvent("place-selected", { detail: originPlace }));

      destInput.value = destPlace.label;
      destHidden.value = destPlace.id;
      destInput.dispatchEvent(new CustomEvent("place-selected", { detail: destPlace }));
    });
  });

  syncTripTriggerLabel();
  syncPassengerHidden();
  syncCabinTrigger();
  syncDateDisplays();

  window.GfForm = { syncDateDisplays, syncTripTriggerLabel, closeAll };
})();
