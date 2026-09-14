const root = document.documentElement;
const toggle = document.getElementById('theme-toggle');

function syncThemeButton(theme) {
  if (!toggle) return;
  const dark = theme === 'dark';
  const sun = document.getElementById('theme-sun');
  const moon = document.getElementById('theme-moon');
  if (sun) sun.hidden = dark;
  if (moon) moon.hidden = !dark;
  toggle.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
}

if (toggle) {
  const currentTheme = root.getAttribute('data-theme') || 'light';
  root.setAttribute('data-theme', currentTheme);
  localStorage.setItem('theme', currentTheme);
  syncThemeButton(currentTheme);

  toggle.addEventListener('click', () => {
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    syncThemeButton(next);
  });
}
