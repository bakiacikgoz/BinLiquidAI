(() => {
  "use strict";

  const header = document.querySelector("[data-header]");
  const navToggle = document.querySelector("[data-nav-toggle]");
  const mobileNav = document.querySelector("[data-mobile-nav]");
  const yearEl = document.querySelector("[data-year]");
  const form = document.getElementById("pilot-form");
  const formStatus = document.querySelector("[data-form-status]");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (yearEl) {
    yearEl.textContent = String(new Date().getFullYear());
  }

  /* Sticky header elevation */
  const onScroll = () => {
    if (!header) return;
    header.classList.toggle("is-scrolled", window.scrollY > 8);
  };
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  /* Mobile nav */
  const setNavOpen = (open) => {
    if (!navToggle || !mobileNav) return;
    navToggle.setAttribute("aria-expanded", open ? "true" : "false");
    mobileNav.hidden = !open;
    document.body.style.overflow = open ? "hidden" : "";
  };

  if (navToggle && mobileNav) {
    navToggle.addEventListener("click", () => {
      const open = navToggle.getAttribute("aria-expanded") !== "true";
      setNavOpen(open);
    });

    mobileNav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => setNavOpen(false));
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") setNavOpen(false);
    });
  }

  /* Active section in nav */
  const sectionIds = ["platform", "surfaces", "governance", "principles", "readiness", "contact"];
  const navLinks = document.querySelectorAll('.nav-desktop a[href^="#"]');

  const setActiveNav = () => {
    const offset = (header?.offsetHeight || 72) + 24;
    let current = "";
    for (const id of sectionIds) {
      const el = document.getElementById(id);
      if (!el) continue;
      const top = el.getBoundingClientRect().top;
      if (top - offset <= 0) current = id;
    }
    navLinks.forEach((link) => {
      const href = link.getAttribute("href") || "";
      const match = href === `#${current}`;
      if (match) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    });
  };

  window.addEventListener("scroll", setActiveNav, { passive: true });
  setActiveNav();

  /* Reveal on scroll */
  const revealEls = document.querySelectorAll("[data-reveal], .lifecycle-step, .principle");
  if (reduceMotion) {
    revealEls.forEach((el) => el.classList.add("is-visible"));
  } else if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.12 }
    );
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add("is-visible"));
  }

  /* Pilot form — client-side only mailto handoff */
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const data = new FormData(form);
      const name = String(data.get("name") || "").trim();
      const email = String(data.get("email") || "").trim();
      const org = String(data.get("org") || "").trim();
      const role = String(data.get("role") || "").trim();
      const message = String(data.get("message") || "").trim();

      if (!name || !email || !org || !role) {
        if (formStatus) {
          formStatus.textContent = "Lütfen zorunlu alanları doldurun.";
          formStatus.classList.add("is-error");
          formStatus.classList.remove("is-success");
        }
        return;
      }

      const subject = encodeURIComponent(`ImperaOS pilot talebi — ${org}`);
      const body = encodeURIComponent(
        [
          `Ad: ${name}`,
          `E-posta: ${email}`,
          `Kurum: ${org}`,
          `Rol: ${role}`,
          "",
          "Bağlam:",
          message || "(belirtilmedi)",
        ].join("\n")
      );

      /* Prefer local storage + success state for static hosting */
      try {
        const payload = { name, email, org, role, message, at: new Date().toISOString() };
        const prev = JSON.parse(localStorage.getItem("imperaos-pilot-requests") || "[]");
        prev.push(payload);
        localStorage.setItem("imperaos-pilot-requests", JSON.stringify(prev));
      } catch {
        /* ignore storage errors */
      }

      if (formStatus) {
        formStatus.textContent =
          "Talep kaydedildi. Ekibe göndermek için e-posta istemciniz açılıyor…";
        formStatus.classList.add("is-success");
        formStatus.classList.remove("is-error");
      }

      window.location.href = `mailto:pilot@imperaos.com?subject=${subject}&body=${body}`;
      form.reset();
    });
  }

  /* Soft gate-rail pulse on hero load */
  if (!reduceMotion) {
    const activeGate = document.querySelector(".gate-step.is-active");
    if (activeGate) {
      activeGate.animate(
        [
          { boxShadow: "0 0 0 0 rgba(251, 191, 36, 0)" },
          { boxShadow: "0 0 0 6px rgba(251, 191, 36, 0.18)" },
          { boxShadow: "0 0 0 0 rgba(251, 191, 36, 0)" },
        ],
        { duration: 2200, iterations: 2, easing: "ease-in-out" }
      );
    }
  }
})();
