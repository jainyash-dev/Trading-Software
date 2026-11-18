/* Applies the saved GTF theme before the first paint (P10-2). No network, no data. */
(function () {
  var theme = "dark";
  try {
    if (window.localStorage.getItem("gtf-theme") === "light") theme = "light";
  } catch (error) {
    theme = "dark";
  }
  document.documentElement.setAttribute("data-theme", theme);
})();
