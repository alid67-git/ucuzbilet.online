(function () {
  const LANG_CURRENCY = { tr: "TRY", en: "USD", de: "EUR", fr: "EUR" };
  const RATES = { TRY: 1, EUR: 37, USD: 34, GBP: 43 };
  const SYMBOLS = { TRY: "₺", EUR: "€", USD: "$", GBP: "£" };

  function getStored(key, fallback) {
    try {
      return localStorage.getItem(key) || fallback;
    } catch {
      return fallback;
    }
  }

  function setStored(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* ignore */
    }
  }

  const serverLocale = window.__LOCALE || {};
  let lang = getStored("lang", serverLocale.lang || "tr");
  let strings = serverLocale.strings || {};
  let currencyAuto = getStored("currencyAuto", "1") !== "0";
  let currency = getStored("currency", LANG_CURRENCY[lang] || "TRY");

  function t(key) {
    return strings[key] || key;
  }

  function effectiveCurrency() {
    if (currencyAuto) {
      return LANG_CURRENCY[lang] || "TRY";
    }
    return currency;
  }

  function tryToDisplay(amountTry) {
    const cur = effectiveCurrency();
    const rate = RATES[cur] || 1;
    const converted = amountTry / rate;
    const sym = SYMBOLS[cur] || cur;
    const formatted = Math.round(converted).toLocaleString(lang === "tr" ? "tr-TR" : lang === "de" ? "de-DE" : lang === "fr" ? "fr-FR" : "en-US");
    return sym + formatted + " " + cur;
  }

  function applyI18n() {
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (key && strings[key]) {
        el.textContent = strings[key];
      }
    });
    document.querySelectorAll(".lang-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lang === lang);
    });
    const autoLabel = document.querySelector("#currency-auto + span[data-i18n]");
    if (autoLabel && strings.currency_auto) autoLabel.textContent = strings.currency_auto;
  }

  function syncCurrencySelect() {
    const sel = document.getElementById("currency-select");
    const auto = document.getElementById("currency-auto");
    if (sel) {
      sel.value = currencyAuto ? effectiveCurrency() : currency;
      sel.disabled = currencyAuto;
    }
    if (auto) auto.checked = currencyAuto;
  }

  async function setLang(next) {
    lang = next;
    setStored("lang", lang);
    document.cookie = "lang=" + lang + ";path=/;max-age=31536000";
    try {
      const res = await fetch("/api/locale?lang=" + encodeURIComponent(lang));
      if (res.ok) {
        const data = await res.json();
        strings = data.strings || strings;
      }
    } catch {
      /* keep existing */
    }
    if (currencyAuto) {
      currency = LANG_CURRENCY[lang] || "TRY";
      setStored("currency", currency);
    }
    applyI18n();
    syncCurrencySelect();
    document.dispatchEvent(new CustomEvent("localechange", { detail: { lang, currency: effectiveCurrency() } }));
  }

  function initTopBar() {
    document.querySelectorAll(".lang-btn").forEach((btn) => {
      btn.addEventListener("click", () => setLang(btn.dataset.lang));
    });
    const sel = document.getElementById("currency-select");
    const auto = document.getElementById("currency-auto");
    if (auto) {
      auto.addEventListener("change", () => {
        currencyAuto = auto.checked;
        setStored("currencyAuto", currencyAuto ? "1" : "0");
        syncCurrencySelect();
        document.dispatchEvent(new CustomEvent("localechange", { detail: { lang, currency: effectiveCurrency() } }));
      });
    }
    if (sel) {
      sel.addEventListener("change", () => {
        currency = sel.value;
        currencyAuto = false;
        setStored("currency", currency);
        setStored("currencyAuto", "0");
        if (auto) auto.checked = false;
        sel.disabled = false;
        document.dispatchEvent(new CustomEvent("localechange", { detail: { lang, currency: effectiveCurrency() } }));
      });
    }
    const helpOpen = document.getElementById("help-open");
    const helpClose = document.getElementById("help-close");
    const dialog = document.getElementById("help-dialog");
    if (helpOpen && dialog) {
      helpOpen.addEventListener("click", () => {
        if (typeof dialog.showModal === "function") dialog.showModal();
        else dialog.setAttribute("open", "");
      });
    }
    if (helpClose && dialog) {
      helpClose.addEventListener("click", () => dialog.close());
    }
  }

  window.SiteLocale = {
    t,
    lang: () => lang,
    currency: effectiveCurrency,
    formatFromTry: tryToDisplay,
    rates: RATES,
    symbols: SYMBOLS,
  };

  applyI18n();
  syncCurrencySelect();
  initTopBar();
})();
