// SecureNet website: theme switch, mobile menu, highlight the section in view.
(function () {
  var root = document.documentElement;
  var body = document.body;

  // ── Theme (dark / peach), remembered on this device ──
  var themeButton = document.querySelector('.theme-toggle');
  var themeLabel = document.querySelector('.theme-label');
  var themeColor = document.querySelector('meta[name="theme-color"]');
  function applyTheme(theme) {
    root.dataset.theme = theme;
    themeLabel.textContent = theme === 'light' ? 'Dark theme' : 'Peach theme';
    if (themeColor) themeColor.setAttribute('content', theme === 'light' ? '#fbeee4' : '#0a1020');
  }
  applyTheme(root.dataset.theme === 'light' ? 'light' : 'dark');
  themeButton.addEventListener('click', function () {
    var next = root.dataset.theme === 'light' ? 'dark' : 'light';
    applyTheme(next);
    try { localStorage.setItem('sn_site_theme', next); } catch (e) { /* storage blocked */ }
  });

  // ── Mobile menu ──
  var menuButton = document.querySelector('.menu-button');
  var scrim = document.querySelector('.scrim');
  function setMenu(open) {
    body.classList.toggle('menu-open', open);
    menuButton.setAttribute('aria-expanded', String(open));
    scrim.hidden = !open;
  }
  menuButton.addEventListener('click', function () { setMenu(!body.classList.contains('menu-open')); });
  scrim.addEventListener('click', function () { setMenu(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setMenu(false); });
  document.querySelectorAll('.sidebar a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function () { setMenu(false); });
  });

  // ── Highlight the sidebar link of the section in view ──
  var links = {};
  document.querySelectorAll('.nav-link').forEach(function (a) { links[a.getAttribute('href').slice(1)] = a; });
  function activate(id) {
    Object.keys(links).forEach(function (key) {
      var on = key === id;
      links[key].classList.toggle('active', on);
      if (on) links[key].setAttribute('aria-current', 'true'); else links[key].removeAttribute('aria-current');
    });
  }
  if ('IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) { if (entry.isIntersecting && links[entry.target.id]) activate(entry.target.id); });
    }, { rootMargin: '-45% 0px -50% 0px' });
    document.querySelectorAll('main section[id]').forEach(function (s) { observer.observe(s); });
  }
  activate((location.hash || '#home').slice(1));

  document.getElementById('year').textContent = String(new Date().getFullYear());
})();
