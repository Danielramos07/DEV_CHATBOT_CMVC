document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn = document.getElementById("asideToggleBtn");
  if (!toggleBtn) return;

  const root = document.documentElement;
  const storageKey = "ai4ap_sidebar_collapsed";

  const readPreference = () => {
    try {
      return window.localStorage.getItem(storageKey);
    } catch {
      return null;
    }
  };

  const writePreference = (isCollapsed) => {
    try {
      window.localStorage.setItem(storageKey, isCollapsed ? "1" : "0");
    } catch {
      // ignore (private mode / blocked storage)
    }
  };

  const applyCollapsed = (isCollapsed) => {
    root.classList.toggle("sidebar-collapsed", Boolean(isCollapsed));
    // Backward-compat: if any pages relied on body selector.
    document.body?.classList.toggle("sidebar-collapsed", Boolean(isCollapsed));
  };

  const updateA11y = () => {
    const isCollapsed = root.classList.contains("sidebar-collapsed");
    toggleBtn.setAttribute("aria-expanded", (!isCollapsed).toString());
    toggleBtn.setAttribute(
      "aria-label",
      isCollapsed ? "Expandir menu" : "Colapsar menu"
    );
    toggleBtn.setAttribute(
      "title",
      isCollapsed ? "Expandir menu" : "Colapsar menu"
    );
  };

  // Apply persisted preference (default: expanded)
  const saved = readPreference();
  if (saved === "1") {
    applyCollapsed(true);
  } else if (saved === "0") {
    applyCollapsed(false);
  }

  toggleBtn.addEventListener("click", () => {
    root.classList.toggle("sidebar-collapsed");
    document.body?.classList.toggle("sidebar-collapsed");
    writePreference(root.classList.contains("sidebar-collapsed"));
    updateA11y();
  });

  updateA11y();
});
