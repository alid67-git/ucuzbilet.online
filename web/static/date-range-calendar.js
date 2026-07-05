(function () {
  const calRoot = document.getElementById("trip-date-calendar");
  const depInput = document.getElementById("trip-departure");
  const retInput = document.getElementById("trip-return");
  const useReturnCb = document.getElementById("use-return-date");
  const depChip = document.getElementById("cal-chip-dep");
  const retChip = document.getElementById("cal-chip-ret");
  const depChipValue = document.getElementById("cal-chip-dep-value");
  const retChipValue = document.getElementById("cal-chip-ret-value");
  if (!calRoot || !depInput) return;

  const MONTHS_AHEAD = 12;
  let pickPhase = "start";

  function currentLang() {
    return document.documentElement.lang || "tr";
  }

  function isoFromDate(d) {
    return (
      d.getFullYear() +
      "-" +
      String(d.getMonth() + 1).padStart(2, "0") +
      "-" +
      String(d.getDate()).padStart(2, "0")
    );
  }

  function todayIso() {
    return isoFromDate(new Date());
  }

  function parseIso(iso) {
    if (!iso) return null;
    const d = new Date(iso + "T00:00:00");
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function isRoundTrip() {
    return Boolean(useReturnCb?.checked);
  }

  function depIso() {
    return depInput.value || "";
  }

  function retIso() {
    return retInput?.value || "";
  }

  function chipText(iso) {
    const d = parseIso(iso);
    if (!d) return "—";
    return d.toLocaleDateString(currentLang(), {
      day: "numeric",
      month: "short",
      weekday: "short",
    });
  }

  function monthTitle(year, month) {
    const d = new Date(year, month, 1);
    return d.toLocaleDateString(currentLang(), { month: "long", year: "numeric" });
  }

  function weekdayNames() {
    // Pazartesi baslangicli kisa gun adlari
    const names = [];
    const monday = new Date(2024, 0, 1); // 1 Oca 2024 = Pazartesi
    for (let i = 0; i < 7; i += 1) {
      const d = new Date(monday);
      d.setDate(monday.getDate() + i);
      names.push(d.toLocaleDateString(currentLang(), { weekday: "short" }));
    }
    return names;
  }

  function syncChips() {
    if (depChipValue) depChipValue.textContent = chipText(depIso());
    if (retChipValue) retChipValue.textContent = chipText(retIso());
    if (retChip) retChip.hidden = !isRoundTrip();
    depChip?.classList.toggle("active", pickPhase === "start");
    retChip?.classList.toggle("active", pickPhase === "end" && isRoundTrip());
  }

  function cellClass(iso) {
    const classes = ["fs-cal-day"];
    const dep = depIso();
    const ret = retIso();
    if (iso === todayIso()) classes.push("fs-cal-today");
    if (!isRoundTrip()) {
      if (iso === dep) classes.push("fs-cal-selected");
      return classes.join(" ");
    }
    if (!dep) return classes.join(" ");
    const end = ret && ret >= dep ? ret : dep;
    if (iso === dep) classes.push("fs-cal-start");
    if (iso === end && end !== dep) classes.push("fs-cal-end");
    if (iso > dep && iso < end) classes.push("fs-cal-in-range");
    return classes.join(" ");
  }

  function onDayClick(iso) {
    if (iso < todayIso()) return;

    if (!isRoundTrip()) {
      depInput.value = iso;
      pickPhase = "start";
      depInput.dispatchEvent(new Event("change", { bubbles: true }));
      renderAll(false);
      return;
    }

    if (retInput) retInput.disabled = false;
    const dep = depIso();

    if (pickPhase === "start" || !dep || iso < dep) {
      depInput.value = iso;
      if (retInput) retInput.value = iso;
      pickPhase = "end";
      depInput.dispatchEvent(new Event("change", { bubbles: true }));
    } else {
      if (retInput) retInput.value = iso;
      pickPhase = "start";
      retInput?.dispatchEvent(new Event("change", { bubbles: true }));
    }
    renderAll(false);
  }

  function buildMonthSection(year, month) {
    const section = document.createElement("div");
    section.className = "fs-cal-month";
    section.dataset.year = String(year);
    section.dataset.month = String(month);

    const title = document.createElement("div");
    title.className = "fs-cal-month-title";
    title.textContent = monthTitle(year, month);
    section.appendChild(title);

    const weekdays = document.createElement("div");
    weekdays.className = "fs-cal-weekdays";
    weekdayNames().forEach((wd) => {
      const span = document.createElement("span");
      span.textContent = wd;
      weekdays.appendChild(span);
    });
    section.appendChild(weekdays);

    const grid = document.createElement("div");
    grid.className = "fs-cal-grid";

    const first = new Date(year, month, 1);
    const startPad = (first.getDay() + 6) % 7;
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const minIso = todayIso();

    for (let i = 0; i < startPad; i += 1) {
      const pad = document.createElement("span");
      pad.className = "fs-cal-pad";
      pad.setAttribute("aria-hidden", "true");
      grid.appendChild(pad);
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
      const iso =
        year + "-" + String(month + 1).padStart(2, "0") + "-" + String(day).padStart(2, "0");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = cellClass(iso);
      btn.textContent = String(day);
      btn.disabled = iso < minIso;
      btn.addEventListener("click", (event) => {
        event.stopPropagation();
        onDayClick(iso);
      });
      grid.appendChild(btn);
    }

    section.appendChild(grid);
    return section;
  }

  function renderAll(scrollToAnchor) {
    syncChips();
    const previousScrollTop = calRoot.scrollTop;

    calRoot.innerHTML = "";
    const today = new Date();
    let y = today.getFullYear();
    let m = today.getMonth();
    const anchorDate = parseIso(depIso());
    let anchorSection = null;

    for (let i = 0; i <= MONTHS_AHEAD; i += 1) {
      const section = buildMonthSection(y, m);
      if (anchorDate && anchorDate.getFullYear() === y && anchorDate.getMonth() === m) {
        anchorSection = section;
      }
      calRoot.appendChild(section);
      m += 1;
      if (m > 11) {
        m = 0;
        y += 1;
      }
    }

    if (scrollToAnchor && anchorSection) {
      anchorSection.scrollIntoView({ block: "start" });
    } else {
      calRoot.scrollTop = previousScrollTop;
    }
  }

  depChip?.addEventListener("click", () => {
    pickPhase = "start";
    syncChips();
  });

  retChip?.addEventListener("click", () => {
    if (!isRoundTrip()) return;
    pickPhase = "end";
    syncChips();
  });

  useReturnCb?.addEventListener("change", () => {
    pickPhase = "start";
    renderAll(true);
  });

  depInput.addEventListener("change", () => renderAll(false));
  retInput?.addEventListener("change", () => renderAll(false));
  document.addEventListener("localechange", () => renderAll(false));

  renderAll(true);
  window.TripDateCalendar = { refresh: () => renderAll(true) };
})();
