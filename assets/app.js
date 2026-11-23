// 一覧の絞り込み・相対時刻表示・GA4イベント送信
(function () {
  "use strict";

  var PAGE_SIZE = 48;
  var DAY = 86400000;

  function track(name, params) {
    if (typeof window.gtag === "function") window.gtag("event", name, params || {});
  }

  // ---- 相対時刻（「3時間前」など）と NEW バッジ ----
  function relTime(ms) {
    var diff = Date.now() - ms;
    if (diff < 0) diff = 0;
    var h = Math.floor(diff / 3600000);
    if (h < 1) return "1時間以内";
    if (h < 24) return h + "時間前";
    var d = Math.floor(h / 24);
    if (d < 30) return d + "日前";
    return Math.floor(d / 30) + "か月前";
  }

  var cards = Array.prototype.slice.call(document.querySelectorAll(".card"));
  cards.forEach(function (card) {
    var ms = Date.parse(card.getAttribute("data-published"));
    card._ms = isNaN(ms) ? 0 : ms;
    card._search = card.getAttribute("data-search") || "";
    var t = card.querySelector(".meta time");
    if (t && card._ms) {
      var rel = document.createElement("span");
      rel.className = "rel";
      rel.textContent = relTime(card._ms);
      t.appendChild(rel);
      if (Date.now() - card._ms < DAY) card.classList.add("is-fresh");
    }
  });

  var grid = document.getElementById("grid");
  if (!grid) return;

  // ---- 絞り込み状態（URLの ?kind=sale&cat=tent に保存・共有可能） ----
  var params = new URLSearchParams(location.search);
  var state = {
    kind: params.get("kind") || "all",
    cat: params.get("cat") || "all",
    brand: params.get("brand") || "all",
    period: params.get("period") || "all",
    q: params.get("q") || ""
  };
  var limit = PAGE_SIZE;

  var countEl = document.getElementById("result-count");
  var moreBtn = document.getElementById("more");
  var emptyEl = document.getElementById("empty");
  var periodSel = document.getElementById("f-period");
  var brandSel = document.getElementById("f-brand");
  var searchInput = document.getElementById("f-search");

  function setActive(selector, attr, value) {
    document.querySelectorAll(selector).forEach(function (el) {
      var on = el.getAttribute(attr) === value;
      el.classList.toggle("active", on);
      if (el.getAttribute("role") === "tab") el.setAttribute("aria-selected", on ? "true" : "false");
    });
  }

  function syncUrl() {
    var p = new URLSearchParams();
    Object.keys(state).forEach(function (k) {
      if (state[k] && state[k] !== "all") p.set(k, state[k]);
    });
    var qs = p.toString();
    history.replaceState(null, "", location.pathname + (qs ? "?" + qs : ""));
  }

  function matches(card) {
    if (state.kind !== "all" && card.getAttribute("data-kind") !== state.kind) return false;
    if (state.cat !== "all" && card.getAttribute("data-category") !== state.cat) return false;
    if (state.brand !== "all" && card.getAttribute("data-brand") !== state.brand) return false;
    if (state.period !== "all" && Date.now() - card._ms > Number(state.period) * DAY) return false;
    if (state.q) {
      var words = state.q.toLowerCase().split(/\s+/).filter(Boolean);
      for (var i = 0; i < words.length; i++) if (card._search.indexOf(words[i]) === -1) return false;
    }
    return true;
  }

  function apply() {
    var shown = 0, total = 0;
    cards.forEach(function (card) {
      var ok = matches(card);
      if (ok) total++;
      var visible = ok && shown < limit;
      if (visible) shown++;
      card.hidden = !visible;
    });
    if (countEl) countEl.textContent = String(total);
    if (moreBtn) moreBtn.hidden = total <= shown;
    if (emptyEl) emptyEl.hidden = total !== 0;
    setActive(".tab", "data-kind", state.kind);
    setActive(".chip", "data-cat", state.cat);
    syncUrl();
  }

  function change(key, value, eventType) {
    state[key] = value;
    limit = PAGE_SIZE;
    apply();
    track("filter_change", { filter_type: eventType || key, filter_value: value });
  }

  document.querySelectorAll(".tab").forEach(function (btn) {
    btn.addEventListener("click", function () { change("kind", btn.getAttribute("data-kind")); });
  });
  document.querySelectorAll(".chip").forEach(function (btn) {
    btn.addEventListener("click", function () { change("cat", btn.getAttribute("data-cat"), "category"); });
  });
  if (periodSel) {
    periodSel.value = state.period;
    periodSel.addEventListener("change", function () { change("period", periodSel.value); });
  }
  if (brandSel) {
    if (brandSel.querySelector('option[value="' + CSS.escape(state.brand) + '"]')) brandSel.value = state.brand;
    else state.brand = "all";
    brandSel.addEventListener("change", function () { change("brand", brandSel.value); });
  }
  if (searchInput) {
    searchInput.value = state.q;
    var typing, reporting;
    searchInput.addEventListener("input", function () {
      clearTimeout(typing);
      clearTimeout(reporting);
      typing = setTimeout(function () {
        state.q = searchInput.value.trim().slice(0, 50);
        limit = PAGE_SIZE;
        apply();
      }, 200);
      reporting = setTimeout(function () {
        var q = searchInput.value.trim();
        if (q.length >= 2) track("search", { search_term: q.slice(0, 50) });
      }, 1500);
    });
  }
  if (moreBtn) {
    moreBtn.addEventListener("click", function () {
      limit += PAGE_SIZE;
      apply();
      track("load_more", { shown: limit });
    });
  }

  // ---- クリック計測（記事 / アフィリエイト） ----
  document.addEventListener("click", function (ev) {
    var link = ev.target.closest && ev.target.closest("a[data-ev]");
    if (!link) return;
    var card = link.closest(".card");
    var info = card ? {
      kind: card.getAttribute("data-kind"),
      category: card.getAttribute("data-category"),
      brand: card.getAttribute("data-brand") || "(none)"
    } : {};
    var host = "";
    try { host = new URL(link.href).hostname; } catch (e) { /* ignore */ }
    if (link.getAttribute("data-ev") === "affiliate") {
      info.shop = link.getAttribute("data-shop");
      info.placement = link.getAttribute("data-placement") || "card";
      track("click_affiliate", info);
    } else {
      info.source = card ? (card.querySelector(".source") || {}).textContent : "";
      info.link_domain = host;
      track("click_article", info);
    }
  });

  apply();
})();
