/* ── Search filter for table rows ── */
function filterRows(inputId, rowSelector) {
    const input = document.getElementById(inputId);
    if (!input) return;
    input.addEventListener('input', () => {
        const query = input.value.toLowerCase().trim();
        document.querySelectorAll(rowSelector).forEach((row) => {
            const text = row.textContent.toLowerCase();
            row.style.display = query && !text.includes(query) ? 'none' : '';
        });
    });
}

/* ── Notification type filter ── */
function initNotificationFilters() {
    const buttons = document.querySelectorAll('.notif-filter-btn');
    const items = document.querySelectorAll('.notification-item');
    if (!buttons.length || !items.length) return;
    buttons.forEach((button) => {
        button.addEventListener('click', () => {
            buttons.forEach((btn) => btn.classList.remove('active'));
            button.classList.add('active');
            const filter = button.dataset.filter;
            items.forEach((item) => {
                const type = item.dataset.type || 'all';
                item.style.display = filter === 'all' || type === filter ? '' : 'none';
            });
        });
    });
}

/* ── Active nav highlighting ── */
function highlightActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('.ea-nav-links a').forEach((link) => {
        const href = link.getAttribute('href');
        if (!href) return;
        if (
            (href === '/' && path === '/') ||
            (href !== '/' && path.startsWith(href))
        ) {
            link.classList.add('active-nav');
        } else {
            link.classList.remove('active-nav');
        }
    });
}

/* ── Mobile navbar toggle ── */
function initMobileNav() {
    const btn = document.getElementById('eaMobileNavBtn');
    const links = document.getElementById('eaNavLinks');
    if (!btn || !links) return;
    btn.addEventListener('click', () => {
        links.classList.toggle('open');
    });
}

/* ── Fade-in on scroll (Intersection Observer) ── */
function initFadeObserver() {
    const items = document.querySelectorAll('.fade-up');
    if (!('IntersectionObserver' in window)) {
        items.forEach(el => el.style.opacity = '1');
        return;
    }
    const obs = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.animationPlayState = 'running';
                obs.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12 });
    items.forEach(el => {
        el.style.animationPlayState = 'paused';
        obs.observe(el);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    filterRows('receiptSearchInput', '.receipt-row');
    filterRows('policySearchInput', '.policy-card');
    filterRows('auditSearchInput', '.audit-row');
    initNotificationFilters();
    highlightActiveNav();
    initMobileNav();
    initFadeObserver();
});
