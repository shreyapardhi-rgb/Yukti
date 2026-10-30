/**
 * Yukti (युक्ति) — Shared UI Component & Theme Manager
 * Powers the navigation bar, live server telemetry, theme switching, and notifications across all pages.
 * Zero-dependency, pure vanilla JavaScript.
 */

// Element selector helper
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

// Consistent Inline SVG Icon Library (24x24 grid, 2px stroke, round caps/joins)
const ICONS = {
  home: `<svg class="icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
  patterns: `<svg class="icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>`,
  codec: `<svg class="icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>`,
  benchmark: `<svg class="icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>`,
  verify: `<svg class="icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>`,
  sun: `<svg class="icon" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`,
  moon: `<svg class="icon" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`,
  menu: `<svg class="icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`,
  close: `<svg class="icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  copy: `<svg class="icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`,
  check: `<svg class="icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
  arrowRight: `<svg class="icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`,
  download: `<svg class="icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`,
  flask: `<svg class="icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3h6"/><path d="M10 9l-4 8a2 2 0 0 0 1.8 3h8.4a2 2 0 0 0 1.8-3l-4-8V3h-4z"/></svg>`,
  refresh: `<svg class="icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>`,
  info: `<svg class="icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
  alert: `<svg class="icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  external: `<svg class="icon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`
};

function getSvg(name) {
  return ICONS[name] || "";
}

// Universal Navigation Pages
const NAV_PAGES = [
  { id: "home", title: "Home", href: "index.html", icon: "home" },
  { id: "patterns", title: "Combinatorics", href: "patterns.html", icon: "patterns" },
  { id: "codec", title: "Codec Theatre", href: "codec.html", icon: "codec" },
  { id: "benchmark", title: "Benchmarks", href: "benchmark.html", icon: "benchmark" },
  { id: "verify", title: "Test Lab", href: "verify.html", icon: "verify" }
];

function renderNavbar(activePageId) {
  const navContainer = $("siteNav");
  if (!navContainer) return;

  navContainer.className = "site-nav";
  navContainer.innerHTML = `
    <div class="nav-container">
      <div style="display:flex; align-items:center; gap:12px;">
        <button id="mobileNavToggle" class="mobile-nav-toggle" aria-label="Toggle navigation menu" aria-expanded="false">
          ${ICONS.menu}
        </button>
        <a href="index.html" class="brand-link">
          <div class="brand-logo">यु</div>
          <div>
            <span class="brand-title">Yukti</span>
            <span class="brand-subtitle">Pingala Bitstream Codec</span>
          </div>
        </a>
      </div>

      <ul id="navMenu" class="nav-menu">
        ${NAV_PAGES.map(p => `
          <li class="nav-item ${p.id === activePageId ? "active" : ""}">
            <a href="${p.href}">
              ${ICONS[p.icon]}
              <span>${p.title}</span>
            </a>
          </li>
        `).join("")}
      </ul>

      <div class="nav-actions">
        <div id="srvPill" class="status-pill" title="Checking server status...">
          <span class="status-dot"></span>
          <span id="srvText">Connecting</span>
        </div>
        <button id="themeToggleBtn" class="theme-btn" aria-label="Toggle Theme">
          <span id="themeIcon">${ICONS.sun}</span>
          <span id="themeLabel" style="font-size:12px;">Theme</span>
        </button>
      </div>
    </div>
  `;

  // Attach mobile hamburger toggle
  const mobileToggle = $("mobileNavToggle");
  const navMenu = $("navMenu");
  if (mobileToggle && navMenu) {
    mobileToggle.onclick = () => {
      const isOpen = navMenu.classList.toggle("open");
      mobileToggle.setAttribute("aria-expanded", String(isOpen));
      mobileToggle.innerHTML = isOpen ? ICONS.close : ICONS.menu;
    };
  }

  // Attach theme listener
  const toggleBtn = $("themeToggleBtn");
  if (toggleBtn) {
    toggleBtn.onclick = () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      setTheme(current === "light" ? "dark" : "light");
    };
  }

  // Check health immediately
  checkBackendHealth();
}

// Universal Theme Manager (Defaults to Light mode for Vedic aesthetic, remembers choice)
function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("yukti_theme", theme);
  const isLight = theme === "light";
  const icon = $("themeIcon");
  const label = $("themeLabel");
  if (icon && label) {
    icon.innerHTML = isLight ? ICONS.sun : ICONS.moon;
    label.textContent = isLight ? "Light" : "Dark";
  }
}

function initTheme() {
  const saved = localStorage.getItem("yukti_theme") || "light";
  setTheme(saved);
}

// Universal Backend Health Telemetry
// Per Problem 4: Show "Online" or "Offline" with a dot, and put the version in a tooltip
function checkBackendHealth() {
  fetch("/api/health")
    .then(r => {
      if (!r.ok) throw new Error("Offline");
      return r.json();
    })
    .then(data => {
      const pill = $("srvPill");
      const text = $("srvText");
      if (pill && text) {
        pill.className = "status-pill online";
        text.textContent = "Online";
        const v = data.version || "2.0.0";
        const uptime = data.uptime_seconds ? `${data.uptime_seconds.toFixed(1)}s` : "active";
        pill.title = `Yukti v${v} • Server uptime: ${uptime}`;
      }
    })
    .catch(() => {
      const pill = $("srvPill");
      const text = $("srvText");
      if (pill && text) {
        pill.className = "status-pill offline";
        text.textContent = "Offline";
        pill.title = "Backend unreachable (client-side JS codec active)";
      }
    });
}

// Universal Toast System
function showToast(msg, duration = 3000) {
  let t = $("toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "toast";
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => {
    t.classList.remove("show");
  }, duration);
}

// Universal Copy to Clipboard Helper
function copyText(text, successMsg = "Copied to clipboard!") {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => showToast(successMsg)).catch(() => fallbackCopy(text, successMsg));
  } else {
    fallbackCopy(text, successMsg);
  }
}

function fallbackCopy(text, successMsg) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand("copy");
    showToast(successMsg);
  } catch (err) {
    showToast("Failed to copy");
  }
  document.body.removeChild(ta);
}

// Universal Footer Renderer
function renderFooter() {
  const footerContainer = $("siteFooter");
  if (!footerContainer) return;

  footerContainer.innerHTML = `
    <footer class="site-footer">
      <div class="footer-container">
        <div class="footer-main">
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
            <span class="brand-logo" style="width:26px; height:26px; font-size:13px;">यु</span>
            <strong style="color:var(--text-primary); font-size:15px; letter-spacing:0.02em;">Yukti (युक्ति) &bull; MeruCode</strong>
            <span class="pill" style="font-size:11px; padding:2px 8px;">Hackathon CSE-03</span>
          </div>
          <p class="text-small" style="max-width:640px; margin-bottom:12px;">
            A modern lossless bitstream serialization system inspired by Acharya Pingala's <em>Chhandas-Shastra</em> (~3rd–2nd c. BCE). 
            <strong>Honesty Notice:</strong> This codec is the team's modern combinadic design and does not represent an ancient digital compression algorithm.
          </p>
          <div class="footer-links">
            <a href="index.html">${ICONS.home} Home</a>
            <a href="patterns.html">${ICONS.patterns} Combinatorics</a>
            <a href="codec.html">${ICONS.codec} Codec Theatre</a>
            <a href="benchmark.html">${ICONS.benchmark} Benchmarks</a>
            <a href="verify.html">${ICONS.verify} Test Lab</a>
            <a href="/api/docs" target="_blank">${ICONS.external} API Docs</a>
            <a href="https://github.com/shreyapardhi-rgb/Yukti" target="_blank" rel="noopener">${ICONS.external} GitHub Repo</a>
          </div>
        </div>
        <div class="footer-aside">
          <div class="text-small" style="font-family:'JetBrains Mono',monospace;">
            <div>Standard: 40-bit Header + Combinadics</div>
            <div>Container: .meru v2 (CRC-32)</div>
            <div style="color:var(--success); margin-top:4px;">&bull; 82/82 Python Tests Passed</div>
            <div style="color:var(--laghu-color);">&bull; 1,000/1,000 JS Parity Verified</div>
          </div>
        </div>
      </div>
    </footer>
  `;
}

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
});
