// GA4 初期化（CSPでインラインスクリプトを禁止しているため外部ファイル化）
(function () {
  var script = document.currentScript;
  var id = script && script.getAttribute("data-ga-id");
  if (!id || !/^G-[A-Z0-9]+$/.test(id)) return;
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag("js", new Date());
  gtag("config", id);
})();
