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

function initNotificationFilters() {
    const buttons = document.querySelectorAll('.notification-filter-btn');
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

document.addEventListener('DOMContentLoaded', () => {
    filterRows('receiptSearchInput', '.receipt-row');
    filterRows('policySearchInput', '.policy-card');
    filterRows('auditSearchInput', '.audit-row');
    initNotificationFilters();
});
