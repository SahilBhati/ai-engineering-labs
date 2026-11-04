// Site chrome: theme toggle, collapsible side nav, header that hides on long pages.
// Preferences live in localStorage (a convenience only; everything works without it).
(function(){
  "use strict";
  const root = document.documentElement;
  const get = k => { try{ return localStorage.getItem(k); }catch(e){ return null; } };
  const set = (k, v) => { try{ localStorage.setItem(k, v); }catch(e){} };
  const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  // Animate a DOM change as a crossfade where supported; plain change otherwise.
  // A newer transition can skip an older one; that's expected, so swallow the rejection instead of logging an error.
  const smooth = fn => { if(!(document.startViewTransition && !reduce)) return fn();
    const t = document.startViewTransition(fn); t.ready.catch(()=>{}); t.finished.catch(()=>{}); t.updateCallbackDone.catch(()=>{}); return t; };

  // Theme: light by default (dark text on light reads better); the choice is remembered.
  const themeBtn = document.getElementById("themeBtn");
  const isDark = () => root.dataset.theme === "dark";
  function syncTheme(){
    if(!themeBtn) return;
    themeBtn.textContent = isDark() ? "Light mode" : "Dark mode";
    themeBtn.setAttribute("aria-pressed", String(isDark()));
  }
  if(themeBtn){
    themeBtn.addEventListener("click", ()=>smooth(()=>{ root.dataset.theme = isDark() ? "light" : "dark"; set("ael-theme", root.dataset.theme); syncTheme(); }));
    syncTheme();
  }

  // Side nav: expanded by default, collapsible, remembered.
  const navBtn = document.getElementById("navBtn");
  function syncNav(){
    if(!navBtn) return;
    const collapsed = root.classList.contains("nav-collapsed");
    navBtn.setAttribute("aria-expanded", String(!collapsed));
    navBtn.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
    navBtn.title = collapsed ? "Expand sidebar" : "Collapse sidebar";
  }
  if(navBtn){
    navBtn.addEventListener("click", ()=>smooth(()=>{ root.classList.toggle("nav-collapsed"); set("ael-nav", root.classList.contains("nav-collapsed") ? "0" : "1"); syncNav(); }));
    syncNav();
  }

  // Header: on long pages only, hide while scrolling down, show again on scroll up.
  const header = document.querySelector("header.site");
  let lastY = window.scrollY, ticking = false;
  function onScroll(){
    // Only in reading mode (side nav collapsed): with the nav open, header and nav stay locked together.
    const y = window.scrollY, long = root.classList.contains("nav-collapsed") && document.documentElement.scrollHeight > window.innerHeight * 2.2;
    if(!long || y < 80 || y < lastY - 4){ root.classList.remove("hdr-hidden"); }
    else if(y > lastY + 4 && !header.contains(document.activeElement)){ root.classList.add("hdr-hidden"); }
    lastY = y; ticking = false;
  }
  if(header) window.addEventListener("scroll", ()=>{ if(!ticking){ ticking = true; requestAnimationFrame(onScroll); } }, {passive:true});
  // Keyboard users: tabbing into the header always brings it back.
  if(header) header.addEventListener("focusin", ()=>root.classList.remove("hdr-hidden"));
  window.__aelReduceMotion = reduce;
})();
