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

  let viewYear;
  let viewMonth;
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

  function monthTitle() {
    const d = new Date(viewYear, viewMonth, 1);
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

  function ensureViewDate() {
    const anchor = parseIso(depIso()) || new Date();
    if (viewYear == null || viewMonth == null) {
      viewYear = anchor.getFullYear();
      viewMonth = anchor.getMonth();
    }
  }

  function cellClass(iso, minIso) {
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
      render();
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
    render();
  }

  function render() {
    ensureViewDate();
    syncChips();

    const minIso = todayIso();
    const first = new Date(viewYear, viewMonth, 1);
    const startPad = (first.getDay() + 6) % 7;
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();

    calRoot.innerHTML = "";

    const header = document.createElement("div");
    header.className = "fs-cal-header";
    const prev = document.createElement("button");
    prev.type = "button";
    prev.className = "fs-cal-nav";
    prev.textContent = "‹";
    prev.setAttribute("aria-label", "previous month");
    prev.addEventListener("click", (event) => {
      // render() bu tikin icinde takvimi yeniden olusturup eski butonu
      // DOM'dan kaldiriyor; olay document'a kadar yukselirse "disari
      // tiklandi" saniliyor ve popover kapaniyor. stopPropagation ile
      // bunu onluyoruz.
      event.stopPropagation();
      viewMonth -= 1;
      if (viewMonth < 0) {
        viewMonth = 11;
        viewYear -= 1;
      }
      render();
    });
    const title = document.createElement("span");
    title.className = "fs-cal-title";
    title.textContent = monthTitle();
    const next = document.createElement("button");
    next.type = "button";
    next.className = "fs-cal-nav";
    next.textContent = "›";
    next.setAttribute("aria-label", "next month");
    next.addEventListener("click", (event) => {
      event.stopPropagation();
      viewMonth += 1;
      if (viewMonth > 11) {
        viewMonth = 0;
        viewYear += 1;
      }
      render();
    });
    header.append(prev, title, next);
    calRoot.appendChild(header);

    const weekdays = document.createElement("div");
    weekdays.className = "fs-cal-weekdays";
    weekdayNames().forEach((wd) => {
      const span = document.createElement("span");
      span.textContent = wd;
      weekdays.appendChild(span);
    });
    calRoot.appendChild(weekdays);

    const grid = document.createElement("div");
    grid.className = "fs-cal-grid";

    for (let i = 0; i < startPad; i += 1) {
      const pad = document.createElement("span");
      pad.className = "fs-cal-pad";
      pad.setAttribute("aria-hidden", "true");
      grid.appendChild(pad);
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
      const iso =
        viewYear +
        "-" +
        String(viewMonth + 1).padStart(2, "0") +
        "-" +
        String(day).padStart(2, "0");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = cellClass(iso, minIso);
      btn.textContent = String(day);
      btn.disabled = iso < minIso;
      btn.addEventListener("click", (event) => {
        event.stopPropagation();
        onDayClick(iso);
      });
      grid.appendChild(btn);
    }

    calRoot.appendChild(grid);
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
    render();
  });

  depInput.addEventListener("change", render);
  retInput?.addEventListener("change", render);
  document.addEventListener("localechange", render);

  render();
  window.TripDateCalendar = { refresh: render };
})();
