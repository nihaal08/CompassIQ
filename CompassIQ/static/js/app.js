/* CompassIQ - Dynamic Application Interactivity & AI Hooks */

document.addEventListener('DOMContentLoaded', () => {
    initLiveAIPrediction();
    initRatingStars();
    initTableSearch();
    initDepartmentToggle();
    initNavigationAccessibility();
    initRoleChangeConfirmation();
    initNotifications();
    initSidebarToggle();
    initTicketPagination();
});

function initSidebarToggle() {
    const toggle = document.querySelector('[data-sidebar-toggle]');
    const sidebar = document.getElementById('app-sidebar');
    if (!toggle || !sidebar) return;

    toggle.addEventListener('click', () => {
        document.body.classList.toggle('sidebar-open');
        toggle.setAttribute('aria-expanded', document.body.classList.contains('sidebar-open'));
    });
}

function initNotifications() {
    const overlay = document.querySelector('[data-notification-overlay]');
    if (!overlay) return;

    const dismissNotification = notification => {
        notification.remove();
        if (!overlay.querySelector('.notification-popup')) overlay.remove();
    };

    overlay.querySelectorAll('.notification-popup').forEach(notification => {
        const closeButton = notification.querySelector('[data-notification-close]');
        if (closeButton) closeButton.addEventListener('click', () => dismissNotification(notification));
        window.setTimeout(() => {
            if (notification.isConnected) dismissNotification(notification);
        }, 5000);
    });
}

function initNavigationAccessibility() {
    const toggler = document.querySelector('.navbar-toggler');
    const navigation = document.getElementById('navbarNav');
    if (!toggler || !navigation) return;

    navigation.addEventListener('shown.bs.collapse', () => toggler.setAttribute('aria-expanded', 'true'));
    navigation.addEventListener('hidden.bs.collapse', () => toggler.setAttribute('aria-expanded', 'false'));
}

function initRoleChangeConfirmation() {
    document.querySelectorAll('.role-select').forEach(select => {
        select.addEventListener('change', () => {
            const previousRole = select.dataset.currentRole;
            const message = `Change this user's role from ${previousRole} to ${select.value}?`;
            if (window.confirm(message)) {
                select.form.submit();
            } else {
                select.value = previousRole;
            }
        });
    });
}

// Dynamic Department Selector toggle on Registration Form
function initDepartmentToggle() {
    const roleSelect = document.getElementById('role-select');
    const deptWrapper = document.getElementById('department-wrapper');

    if (roleSelect && deptWrapper) {
        roleSelect.addEventListener('change', () => {
            if (roleSelect.value === 'agent') {
                deptWrapper.style.display = 'block';
            } else {
                deptWrapper.style.display = 'none';
            }
        });
    }
}

// Live AI Analysis on Ticket Creation Form
function initLiveAIPrediction() {
    const subjectInput = document.getElementById('ticket-subject');
    const descInput = document.getElementById('ticket-description');
    const aiPreviewBox = document.getElementById('ai-live-preview');

    if (!subjectInput || !descInput || !aiPreviewBox) return;

    let debounceTimer;

    function triggerPrediction() {
        const subject = subjectInput.value.trim();
        const description = descInput.value.trim();

        if (subject.length < 3 && description.length < 5) {
            aiPreviewBox.style.display = 'none';
            return;
        }

        aiPreviewBox.style.display = 'block';
        aiPreviewBox.setAttribute('aria-busy', 'true');

        fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subject, description })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                renderAIResults(data.predictions, data.recommendation, data.similar_tickets);
            }
            aiPreviewBox.setAttribute('aria-busy', 'false');
        })
        .catch(err => {
            aiPreviewBox.setAttribute('aria-busy', 'false');
            aiPreviewBox.setAttribute('data-error', 'true');
            console.error('AI Prediction error:', err);
        });
    }

    const handler = () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(triggerPrediction, 400);
    };

    subjectInput.addEventListener('input', handler);
    descInput.addEventListener('input', handler);
}

function renderAIResults(predictions, recommendation, similarTickets) {
    const catBadge = document.getElementById('ai-cat-badge');
    const catConf = document.getElementById('ai-cat-conf');
    const catBar = document.getElementById('ai-cat-bar');

    const prioBadge = document.getElementById('ai-prio-badge');
    const prioConf = document.getElementById('ai-prio-conf');
    const prioBar = document.getElementById('ai-prio-bar');

    const recText = document.getElementById('ai-rec-text');
    const recSteps = document.getElementById('ai-rec-steps');
    const simCount = document.getElementById('ai-sim-count');

    if (catBadge) catBadge.textContent = predictions.category;
    if (catConf) catConf.textContent = `${predictions.category_confidence}%`;
    if (catBar) catBar.style.width = `${predictions.category_confidence}%`;

    if (prioBadge) {
        prioBadge.textContent = predictions.priority;
        prioBadge.className = `badge badge-priority badge-priority-${predictions.priority.toLowerCase()}`;
    }
    if (prioConf) prioConf.textContent = `${predictions.priority_confidence}%`;
    if (prioBar) prioBar.style.width = `${predictions.priority_confidence}%`;

    if (recText) recText.textContent = recommendation.primary_solution;

    if (recSteps) {
        recSteps.innerHTML = recommendation.steps.map(step => `
            <li class="mb-1"><i class="fas fa-check-circle text-warning me-2"></i>${step}</li>
        `).join('');
    }

    if (simCount) {
        simCount.textContent = similarTickets ? similarTickets.length : 0;
    }
}

// Interactive Star Rating
function initRatingStars() {
    const stars = document.querySelectorAll('.rating-star');
    const ratingInput = document.getElementById('satisfaction-rating');

    if (!stars.length || !ratingInput) return;

    stars.forEach(star => {
        star.addEventListener('click', () => {
            const val = star.getAttribute('data-value');
            ratingInput.value = val;

            stars.forEach(s => {
                const sVal = s.getAttribute('data-value');
                if (sVal <= val) {
                    s.classList.remove('text-muted');
                    s.classList.add('text-warning');
                } else {
                    s.classList.remove('text-warning');
                    s.classList.add('text-muted');
                }
            });
        });
    });
}

// Generic Table Search & Filter
function initTableSearch() {
    const searchInput = document.getElementById('table-search');
    const statusFilter = document.getElementById('status-filter');
    const priorityFilter = document.getElementById('priority-filter');
    const categoryFilter = document.getElementById('category-filter');
    const tableBody = document.getElementById('tickets-table-body');

    if (!tableBody || !searchInput) return;

    const isArticleGrid = tableBody.classList.contains('article-grid');
    const resultItems = [...(isArticleGrid ? tableBody.querySelectorAll('[data-searchable]') : tableBody.querySelectorAll('tr'))];
    const loadMoreButton = document.querySelector(`[data-load-more="${tableBody.id}"]`);
    let noResults = tableBody.querySelector('.search-no-results');
    if (isArticleGrid && !noResults) {
        noResults = document.createElement('p');
        noResults.className = 'search-no-results text-muted text-center py-4';
        noResults.textContent = 'No matching results found.';
        noResults.hidden = true;
        tableBody.appendChild(noResults);
    }

    function filterRows() {
        const query = searchInput ? searchInput.value.toLowerCase() : '';
        const statusVal = statusFilter ? statusFilter.value : 'all';
        const prioVal = priorityFilter ? priorityFilter.value : 'all';
        const categoryVal = categoryFilter ? categoryFilter.value : 'all';

        let visibleCount = 0;
        const matchingRows = resultItems.filter(row => {
            const text = row.textContent.toLowerCase();
            const rowStatus = row.getAttribute('data-status') || '';
            const rowPrio = row.getAttribute('data-priority') || '';
            const rowCategory = row.getAttribute('data-category') || '';

            const matchesSearch = text.includes(query);
            const matchesStatus = statusVal === 'all' || rowStatus === statusVal;
            const matchesPrio = prioVal === 'all' || rowPrio === prioVal;
            const matchesCategory = categoryVal === 'all' || rowCategory === categoryVal;

            return matchesSearch && matchesStatus && matchesPrio && matchesCategory;
        });
        const visibleLimit = Number(tableBody.dataset.visibleLimit || (loadMoreButton ? loadMoreButton.dataset.loadStep : matchingRows.length));
        tableBody.dataset.visibleLimit = visibleLimit;
        resultItems.forEach(row => { row.style.display = 'none'; });
        matchingRows.slice(0, visibleLimit).forEach(row => { row.style.display = ''; visibleCount += 1; });
        if (noResults) noResults.hidden = visibleCount !== 0;
        if (loadMoreButton) loadMoreButton.hidden = visibleCount >= matchingRows.length;
    }

    if (searchInput) searchInput.addEventListener('input', filterRows);
    if (statusFilter) statusFilter.addEventListener('change', filterRows);
    if (priorityFilter) priorityFilter.addEventListener('change', filterRows);
    if (categoryFilter) categoryFilter.addEventListener('change', filterRows);
    filterRows();
}

function initTicketPagination() {
    document.querySelectorAll('[data-load-more]').forEach(button => {
        const tableBody = document.getElementById(button.dataset.loadMore);
        if (!tableBody || tableBody.classList.contains('article-grid')) return;

        button.addEventListener('click', () => {
            button.setAttribute('aria-busy', 'true');
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Loading...';
            window.setTimeout(() => {
                const step = Number(button.dataset.loadStep || 5);
                tableBody.dataset.visibleLimit = Number(tableBody.dataset.visibleLimit || step) + step;
                const searchInput = document.getElementById('table-search');
                if (searchInput) searchInput.dispatchEvent(new Event('input'));
                button.removeAttribute('aria-busy');
                button.innerHTML = '<i class="fas fa-plus me-1"></i> Load more tickets';
            }, 120);
        });
    });
}
