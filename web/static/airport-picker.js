(function () {
  const activePickers = [];

  function closeAllDropdowns(exceptDropdown) {
    activePickers.forEach((picker) => {
      if (picker.dropdown !== exceptDropdown) {
        picker.closeDropdown();
      }
    });
  }

  function typeLabel(type) {
    if (type === "country") return "Ulke";
    if (type === "city") return "Sehir";
    if (type === "hub") return "Hub";
    return "Havalimani";
  }

  function escapeHtml(text) {
    return text
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function setupPicker(inputId, hiddenId, dropdownId) {
    const input = document.getElementById(inputId);
    const hidden = document.getElementById(hiddenId);
    const dropdown = document.getElementById(dropdownId);
    if (!input || !hidden || !dropdown) return null;

    let timer = null;

    function closeDropdown() {
      dropdown.classList.remove("open");
      dropdown.innerHTML = "";
    }

    function appendPlaceOption(place, depth, onSelect) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "place-option" + (depth > 0 ? " place-option-child" : "");
      button.style.paddingLeft = 0.75 + depth * 1.1 + "rem";
      button.innerHTML =
        '<span class="place-type">' +
        typeLabel(place.type) +
        "</span><strong>" +
        escapeHtml(place.label) +
        "</strong>";
      button.addEventListener("mousedown", (event) => {
        event.preventDefault();
      });
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        onSelect(place);
      });
      dropdown.appendChild(button);

      if (place.children && place.children.length) {
        place.children.forEach((child) => appendPlaceOption(child, depth + 1, onSelect));
      }
    }

    function selectPlace(place) {
      input.value = place.label;
      hidden.value = place.id;
      closeDropdown();
      closeAllDropdowns(null);
      input.dispatchEvent(new CustomEvent("place-selected", { detail: place, bubbles: false }));
    }

    function renderItems(results) {
      dropdown.innerHTML = "";
      if (!results.length) {
        dropdown.innerHTML = '<div class="place-empty">Sonuc bulunamadi</div>';
        dropdown.classList.add("open");
        return;
      }
      closeAllDropdowns(dropdown);
      results.forEach((place) => appendPlaceOption(place, 0, selectPlace));
      dropdown.classList.add("open");
    }

    async function fetchWithTimeout(url, ms) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), ms);
      try {
        return await fetch(url, { signal: controller.signal });
      } finally {
        clearTimeout(timer);
      }
    }

    async function search(query) {
      try {
        const response = await fetchWithTimeout("/api/places/search?q=" + encodeURIComponent(query), 8000);
        if (!response.ok) return;
        const data = await response.json();
        renderItems(data);
      } catch {
        /* mobil ag hatasi/zaman asimi: sonuc listesi guncellenmez */
      }
    }

    async function resolveQuery() {
      const query = input.value.trim();
      if (!query || hidden.value) return Boolean(hidden.value);
      try {
        const response = await fetchWithTimeout("/api/places/resolve?q=" + encodeURIComponent(query), 8000);
        if (!response.ok) return false;
        const data = await response.json();
        if (!data.id) return false;
        hidden.value = data.id;
        input.value = data.label;
        input.dispatchEvent(new CustomEvent("place-selected", { detail: data, bubbles: false }));
        return true;
      } catch {
        return false;
      }
    }

    input.addEventListener("input", () => {
      if (input.disabled || input.readOnly) return;
      hidden.value = "";
      clearTimeout(timer);
      const query = input.value.trim();
      if (query.length < 2) {
        closeDropdown();
        return;
      }
      timer = setTimeout(() => search(query), 180);
    });

    input.addEventListener("focus", () => {
      closeAllDropdowns(dropdown);
      if (input.disabled || input.readOnly) return;
      const query = input.value.trim();
      if (query.length >= 2 && !hidden.value) {
        search(query);
      }
    });

    const picker = { dropdown, closeDropdown, input, hidden, resolveQuery };
    activePickers.push(picker);

    document.addEventListener("click", (event) => {
      if (!dropdown.contains(event.target) && event.target !== input) {
        closeDropdown();
      }
    });

    return picker;
  }

  const originPicker = setupPicker("origin-input", "origin-place-id", "origin-dropdown");
  const destPicker = setupPicker("destination-input", "destination-place-id", "destination-dropdown");
  const hubCheckbox = document.getElementById("use-european-hubs");
  const form = document.getElementById("search-form");
  const modeSelect = document.getElementById("mode-select");

  function isHubMode() {
    return Boolean(hubCheckbox?.checked);
  }

  function syncFormFieldsBeforeSubmit() {
    const mode = modeSelect?.value;
    const useReturn = document.getElementById("use-return-date");
    const flexSearch = document.getElementById("flexible-search");
    const tripReturn = document.getElementById("trip-return");
    const tripDays = document.getElementById("trip-days");
    const tripDeparture = document.getElementById("trip-departure");
    const tripDatePanel = document.getElementById("trip-date-panel");
    const flexibilityDaysInput = document.getElementById("flexibility-days");

    if (tripDatePanel) {
      tripDatePanel.querySelectorAll("input, select").forEach((el) => {
        el.disabled = false;
      });
    }
    if (useReturn) useReturn.disabled = false;
    if (flexSearch) flexSearch.disabled = false;

    if (mode === "flexible" && tripDatePanel) {
      tripDatePanel.querySelectorAll("input, select").forEach((el) => {
        if (el.type !== "checkbox") {
          el.disabled = true;
        }
      });
      return;
    }

    if (useReturn?.checked) {
      if (tripReturn) tripReturn.disabled = false;
      if (tripReturn?.value && tripDeparture?.value && tripDays) {
        const from = new Date(tripDeparture.value + "T00:00:00");
        const to = new Date(tripReturn.value + "T00:00:00");
        const span = Math.round((to - from) / (1000 * 60 * 60 * 24));
        if (span > 0) {
          tripDays.value = String(span);
        }
      }
    } else {
      if (tripReturn) {
        tripReturn.value = "";
      }
    }

    if (!flexSearch?.checked && flexibilityDaysInput) {
      flexibilityDaysInput.disabled = true;
    }
  }

  if (form) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      window.SiteLoading?.show();

      function abort(message, focusEl) {
        window.SiteLoading?.hide();
        alert(message);
        if (focusEl) focusEl.focus();
      }

      try {
        const destInput = document.getElementById("destination-input");
        const destHidden = document.getElementById("destination-place-id");
        const originHidden = document.getElementById("origin-place-id");
        const destText = destInput ? destInput.value.trim() : "";
        const hub = isHubMode();

        if (hub) {
          if (originHidden) {
            originHidden.value = "HUB_EU";
          }
          if (modeSelect?.value === "flexible") {
            abort("Hub modu esnek taramayla kullanilamaz. Ucus fiyat taramasi secin.");
            return;
          }
        } else if (originPicker) {
          await originPicker.resolveQuery();
          if (!originHidden.value) {
            abort(
              "Lutfen listeden bir kalkis noktasi secin (ornek: Italya — Tum havalimanlari).",
              document.getElementById("origin-input")
            );
            return;
          }
        }

        if (destText && destPicker) {
          await destPicker.resolveQuery();
          if (!destHidden.value) {
            abort("Varis cozulemedi. Listeden secin veya alani bos birakin (bolge hedefi kullanilir).", destInput);
            return;
          }
        } else if (destHidden) {
          destHidden.value = "";
          if (destInput) {
            destInput.value = "";
          }
        }

        syncFormFieldsBeforeSubmit();

        const submitter = event.submitter;
        const targetAction =
          (submitter && submitter.getAttribute("formaction")) || form.getAttribute("action") || form.action;
        form.action = targetAction;
        form.submit();
      } catch {
        abort("Beklenmeyen bir hata olustu. Lutfen tekrar deneyin.");
      }
    });
  }
})();
