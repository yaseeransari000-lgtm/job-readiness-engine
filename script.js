// script.js
// Sirf ek kaam: score number ko 0 se target value tak smoothly count karna

document.addEventListener("DOMContentLoaded", () => {
    const scoreEl = document.querySelector(".score-number");
    if (!scoreEl) return;

    const target = parseInt(scoreEl.getAttribute("data-target"), 10) || 0;
    let current = 0;
    const duration = 1400; // ms
    const stepTime = 16;
    const totalSteps = duration / stepTime;
    const increment = target / totalSteps;

    const counter = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(counter);
        }
        scoreEl.textContent = Math.round(current);
    }, stepTime);

    // Flash messages ko thodi der baad hata dena (CSS animation already fade karta hai,
    // ye unhe DOM se bhi remove kar deta hai taaki clutter na ho)
    setTimeout(() => {
        document.querySelectorAll(".flash").forEach(el => el.remove());
    }, 3500);
});
