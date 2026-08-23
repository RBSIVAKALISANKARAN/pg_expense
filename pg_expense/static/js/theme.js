const root = document.documentElement;
const toggle = document.getElementById('theme-toggle');

if (toggle) {
  const currentTheme = localStorage.getItem('expense-theme') || 'dark';
  root.setAttribute('data-theme', currentTheme);
  toggle.textContent = currentTheme === 'dark' ? '🌙' : '☀️';

  toggle.addEventListener('click', () => {
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    localStorage.setItem('expense-theme', next);
    toggle.textContent = next === 'dark' ? '🌙' : '☀️';
  });
}
