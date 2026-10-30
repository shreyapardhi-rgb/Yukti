// ==NAV & GLOBAL SHELL==
// Universal navigation, theme switching, Web Audio toggle, and responsive mobile menu for Yukti

(function () {
  // 1. Theme Management (Default to DARK, store in localStorage)
  let currentTheme = localStorage.getItem("yukti-theme") || "dark";
  document.documentElement.dataset.theme = currentTheme;

  function applyTheme(theme) {
    currentTheme = theme;
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("yukti-theme", theme);
    const lbl = document.getElementById("themeLabel");
    if (lbl) lbl.textContent = theme === "dark" ? "Light" : "Dark";
    const icon = document.getElementById("themeIcon");
    if (icon) {
      icon.innerHTML = theme === "dark"
        ? `<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>`
        : `<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>`;
    }
  }

  // 2. Navigation items
  const PAGES = [
    { href: "index.html", label: "Overview", icon: "⌂" },
    { href: "patterns.html", label: "Combinatorics", icon: "❖" },
    { href: "codec.html", label: "Codec Theatre", icon: "⟨⟩" },
    { href: "benchmark.html", label: "Benchmarks", icon: "≈" },
    { href: "verify.html", label: "Test Lab", icon: "✓" }
  ];

  function buildNav() {
    const nav = document.getElementById("siteNav");
    if (!nav) return;

    const curPage = location.pathname.split("/").pop() || "index.html";

    nav.className = "site-nav";
    nav.innerHTML = `
      <div class="nav-container">
        <a href="index.html" class="brand-link" title="Yukti — Pingala's Bitstream Codec">
          <div class="brand-logo">Y</div>
          <div>
            <div class="brand-title">Yukti</div>
            <span class="brand-subtitle">CSE-03 &middot; MeruCode</span>
          </div>
        </a>

        <button class="mobile-nav-toggle" id="mobileNavToggle" aria-label="Toggle navigation menu" aria-expanded="false">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>

        <ul class="nav-menu" id="navMenu">
          ${PAGES.map(p => {
            const isActive = (p.href === curPage) || (curPage === "" && p.href === "index.html");
            return `<li class="nav-item ${isActive ? "active" : ""}">
              <a href="${p.href}">${p.icon} ${p.label}</a>
            </li>`;
          }).join("")}
        </ul>

        <div class="nav-actions">
          <button class="sound-toggle-btn" id="navSoundBtn" title="Toggle audio feedback">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
            <span>Sound</span>
          </button>
          <button class="theme-btn" id="navThemeBtn" title="Toggle color scheme">
            <svg id="themeIcon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
            </svg>
            <span id="themeLabel">${currentTheme === "dark" ? "Light" : "Dark"}</span>
          </button>
        </div>
      </div>
    `;

    // Event listeners
    const mobBtn = document.getElementById("mobileNavToggle");
    const menu = document.getElementById("navMenu");
    if (mobBtn && menu) {
      mobBtn.addEventListener("click", () => {
        const isOpen = menu.classList.toggle("open");
        mobBtn.setAttribute("aria-expanded", String(isOpen));
      });
    }

    const themeBtn = document.getElementById("navThemeBtn");
    if (themeBtn) {
      themeBtn.addEventListener("click", () => {
        applyTheme(currentTheme === "dark" ? "light" : "dark");
        if (window.YuktiAudio) window.YuktiAudio.click(800, 0.03);
      });
    }

    const soundBtn = document.getElementById("navSoundBtn");
    if (soundBtn && window.YuktiAudio) {
      function syncSoundBtn() {
        const en = window.YuktiAudio.isEnabled();
        soundBtn.innerHTML = en
          ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg> <span>Sound: ON</span>`
          : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg> <span>Sound: OFF</span>`;
      }
      syncSoundBtn();
      soundBtn.addEventListener("click", () => {
        window.YuktiAudio.toggle();
        syncSoundBtn();
      });
    }

    applyTheme(currentTheme);
  }

  // 3. Toast helper
  window.toast = function (msg, ok = true) {
    let t = document.getElementById("toast");
    if (!t) {
      t = document.createElement("div");
      t.id = "toast";
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.style.borderColor = ok ? "var(--success)" : "var(--danger)";
    t.classList.add("show");
    setTimeout(() => { t.classList.remove("show"); }, 2500);
  };

  // 4. Cursor glow on cards
  function initCardEffects() {
    document.querySelectorAll(".card, .bento-card, .proof-card").forEach(el => {
      el.addEventListener("pointermove", e => {
        const r = el.getBoundingClientRect();
        el.style.setProperty("--mx", (e.clientX - r.left) + "px");
        el.style.setProperty("--my", (e.clientY - r.top) + "px");
      });
    });
  }

  // 5. Scroll reveal
  function initScrollReveal() {
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.08 });
      document.querySelectorAll(".rv").forEach(el => observer.observe(el));
    } else {
      document.querySelectorAll(".rv").forEach(el => el.classList.add("in"));
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      buildNav();
      initCardEffects();
      initScrollReveal();
    });
  } else {
    buildNav();
    initCardEffects();
    initScrollReveal();
  }
})();
