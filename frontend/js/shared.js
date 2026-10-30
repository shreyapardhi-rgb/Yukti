/**
 * Yukti (युक्ति) — Shared UI Component & Theme Manager
 * Powers the navigation bar, live server telemetry, theme switching, and notifications across all pages.
 */

// Helper to select elements
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

// Universal Navigation Pages
const NAV_PAGES = [
  { id: "home", title: "Home", href: "index.html", icon: "🏛️" },
  { id: "patterns", title: "Combinatorics", href: "patterns.html", icon: "⚡" },
  { id: "codec", title: "Codec Theatre", href: "codec.html", icon: "🎭" },
  { id: "benchmark", title: "Benchmarks", href: "benchmark.html", icon: "📊" },
  { id: "verify", title: "Test Lab", href: "verify.html", icon: "🧪" }
];

function renderNavbar(activePageId) {
  const navContainer = $("siteNav");
  if (!navContainer) return;

  navContainer.className = "site-nav";
  navContainer.innerHTML = `
    <div class="nav-container">
      <a href="index.html" class="brand-link">
        <div class="brand-logo">यु</div>
        <div>
          <span class="brand-title">Yukti</span>
          <span class="brand-subtitle">Pingala Combinadic Codec</span>
        </div>
      </a>

      <ul class="nav-links">
        ${NAV_PAGES.map(p => `
          <li class="nav-item ${p.id === activePageId ? "active" : ""}">
            <a href="${p.href}">
              <span>${p.icon}</span>
              <span>${p.title}</span>
            </a>
          </li>
        `).join("")}
      </ul>

      <div class="nav-actions">
        <div id="srvPill" class="pill">
          <span class="pill-dot"></span>
          <span id="srvText">connecting...</span>
        </div>
        <button id="themeToggleBtn" class="btn-icon" aria-label="Toggle Theme">
          <span id="themeIcon">☀️</span>
          <span id="themeLabel" style="font-size:12px;">Light</span>
        </button>
      </div>
    </div>
  `;

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

// Universal Theme Manager (Defaults to Light mode for Vedic aesthetic)
function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("yukti_theme", theme);
  const isLight = theme === "light";
  const icon = $("themeIcon");
  const label = $("themeLabel");
  if (icon && label) {
    icon.textContent = isLight ? "☀️" : "🌙";
    label.textContent = isLight ? "Light" : "Dark";
  }
}

function initTheme() {
  const saved = localStorage.getItem("yukti_theme") || "light";
  setTheme(saved);
}

// Universal Backend Health Telemetry
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
        pill.className = "pill connected";
        text.textContent = `v${data.version || "2.0"} (${data.uptime_seconds || 0}s)`;
      }
    })
    .catch(() => {
      const pill = $("srvPill");
      const text = $("srvText");
      if (pill && text) {
        pill.className = "pill offline";
        text.textContent = "offline (client ok)";
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

// Universal Footer Renderer
function renderFooter() {
  const footerContainer = $("siteFooter");
  if (!footerContainer) return;

  footerContainer.innerHTML = `
    <footer style="max-width:1200px; margin:40px auto 0; padding:24px; border-top:1px solid var(--border-gold); text-align:center; font-size:13px; color:var(--text-muted);">
      <p style="margin-bottom:8px;">
        <strong style="color:var(--text-main);">Yukti (युक्ति) &bull; MeruCode</strong> &mdash; 
        Lossless bitstream serialization inspired by Acharya Pingala's <em>Chhandas-Shastra</em> (~3rd–2nd c. BCE).
      </p>
      <p style="font-size:12px; margin-bottom:12px;">
        CSE-03 Intermediate Project &bull; Built with Flask &amp; Vanilla JavaScript &bull; Pinned, hardened &amp; verified bit-for-bit.
      </p>
      <div style="display:flex; justify-content:center; gap:16px; font-weight:600;">
        <a href="index.html" style="color:inherit; text-decoration:none;">Home</a>
        <a href="patterns.html" style="color:inherit; text-decoration:none;">Combinatorics</a>
        <a href="codec.html" style="color:inherit; text-decoration:none;">Codec Theatre</a>
        <a href="benchmark.html" style="color:inherit; text-decoration:none;">Benchmarks</a>
        <a href="verify.html" style="color:inherit; text-decoration:none;">Test Lab</a>
        <a href="/api/docs" style="color:inherit; text-decoration:none;">API Docs</a>
      </div>
    </footer>
  `;
}

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
});
