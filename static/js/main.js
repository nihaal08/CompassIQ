/**
 * CompassIQ — Frontend JavaScript Controller
 * =========================================
 * Handles:
 * - Modal alert system with "OK" buttons
 * - Customer ticket workspace and conversation threads
 * - Agent split workspace with ticket details
 * - Sidebar navigation (3 links + Sign Out per role)
 * - Admin analytics chart initialization
 * - Star rating feedback system
 */

document.addEventListener('DOMContentLoaded', () => {
    initAlertModals();
    initStarRatings();
    initSidebarNavigation();
});

/* ==========================================================================
   1. MODAL ALERT SYSTEM (Centered alerts with "OK" button)
   ========================================================================== */

function initAlertModals() {
    // Close button handlers (top-left X)
    const closeBtns = document.querySelectorAll('.modal-close-btn');
    closeBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const modalBackdrop = btn.closest('.alert-modal-backdrop') || 
                                   btn.closest('.custom-modal-backdrop') || 
                                   btn.closest('.ticket-modal-backdrop');
            if (modalBackdrop) {
                closeModal(modalBackdrop);
            }
        });
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const openModals = document.querySelectorAll('.alert-modal-backdrop.show, .custom-modal-backdrop.show');
            openModals.forEach(m => closeModal(m));
        }
    });

    // Close when clicking outside modal
    const backdrops = document.querySelectorAll('.alert-modal-backdrop, .custom-modal-backdrop');
    backdrops.forEach(backdrop => {
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) {
                closeModal(backdrop);
            }
        });
    });
}

function openModal(modalEl) {
    if (typeof modalEl === 'string') {
        modalEl = document.querySelector(modalEl);
    }
    if (modalEl) {
        modalEl.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalEl) {
    if (typeof modalEl === 'string') {
        modalEl = document.querySelector(modalEl);
    }
    if (modalEl) {
        modalEl.classList.remove('show');
        document.body.style.overflow = '';
    }
}

/**
 * Shows a centered modal alert with title, message, and "OK" button.
 * Used for notifications, errors, and confirmations.
 */
function showCustomAlert(title, message, type = 'info') {
    let modal = document.getElementById('dynamicAlertModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'dynamicAlertModal';
        modal.className = 'alert-modal-backdrop';
        modal.innerHTML = `
            <div class="alert-modal-box">
                <button type="button" class="modal-close-btn" title="Close">
                    &times;
                </button>
                <div class="alert-icon-wrap alert-icon-${type}">
                    <i class="bi ${getIconForType(type)}"></i>
                </div>
                <h4 class="mb-2" id="dynamicAlertTitle">${title}</h4>
                <p class="text-muted mb-4" id="dynamicAlertMessage">${message}</p>
                <button type="button" class="btn btn-cyber px-4" onclick="closeModal('#dynamicAlertModal')">
                    OK
                </button>
            </div>
        `;
        document.body.appendChild(modal);
        initAlertModals();
    } else {
        document.getElementById('dynamicAlertTitle').textContent = title;
        document.getElementById('dynamicAlertMessage').textContent = message;
        const iconWrap = modal.querySelector('.alert-icon-wrap');
        iconWrap.className = `alert-icon-wrap alert-icon-${type}`;
        iconWrap.innerHTML = `<i class="bi ${getIconForType(type)}"></i>`;
    }
    openModal(modal);
}

function getIconForType(type) {
    switch (type) {
        case 'warning':
            return 'bi-exclamation-triangle';
        case 'danger':
            return 'bi-shield-x';
        case 'success':
            return 'bi-check2-circle';
        default:
            return 'bi-info-circle';
    }
}

/* ==========================================================================
   2. STAR RATING FEEDBACK SYSTEM
   ========================================================================== */

function initStarRatings() {
    const starContainers = document.querySelectorAll('.star-rating');
    starContainers.forEach(container => {
        const inputs = container.querySelectorAll('input[type="radio"]');
        inputs.forEach(input => {
            input.addEventListener('change', () => {
                const label = container.querySelector(`label[for="${input.id}"]`);
                if (label) {
                    label.style.transform = 'scale(1.2)';
                    setTimeout(() => label.style.transform = 'scale(1)', 200);
                }
            });
        });
    });
}

/* ==========================================================================
   3. CUSTOMER PORTAL - TICKET WORKSPACE
   ========================================================================== */

function openCustomerTicketModal(ticketId) {
    const modal = document.getElementById('customerTicketModal');
    if (!modal) return;

    // Reset thread with loading indicator
    const threadContainer = document.getElementById('custChatThread');
    threadContainer.innerHTML = '<div class="text-center py-4"><div class="spinner-border" role="status"></div></div>';
    
    document.getElementById('custModalTicketId').textContent = ticketId;
    document.getElementById('custReplyForm').action = `/customer/tickets/${ticketId}/reply`;

    // Fetch ticket details via AJAX
    fetch(`/customer/tickets/${ticketId}`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                const ticket = data.ticket;
                const replies = data.replies;

                // Update ticket information
                document.getElementById('custModalSubject').textContent = ticket.subject;
                document.getElementById('custModalCategory').textContent = ticket.predicted_category;
                document.getElementById('custModalStatus').textContent = ticket.status;
                document.getElementById('custModalStatus').className = `badge-status badge-status-${ticket.status.replace(/\s+/g, '')}`;

                // Update step progress tracker
                updateStepTrackerUI('custStepTracker', ticket.status);

                // Render conversation thread
                threadContainer.innerHTML = '';
                if (replies.length === 0) {
                    threadContainer.innerHTML = '<p class="text-muted text-center my-3">No messages yet.</p>';
                } else {
                    replies.forEach(r => {
                        const isCustomer = r.sender_role === 'customer';
                        const bubble = document.createElement('div');
                        bubble.className = `chat-bubble ${isCustomer ? 'chat-bubble-customer' : 'chat-bubble-agent'}`;
                        bubble.innerHTML = `
                            <div class="fw-bold mb-1" style="font-size: 0.8rem; color: ${isCustomer ? '#FFF' : '#D5D5D5'};">
                                ${escapeHtml(r.sender_name)} ${isCustomer ? '(You)' : '(Support Agent)'}
                            </div>
                            <div style="white-space: pre-wrap;">${escapeHtml(r.message)}</div>
                            <div class="chat-meta">
                                <span>${new Date(r.created_at).toLocaleString()}</span>
                            </div>
                        `;
                        threadContainer.appendChild(bubble);
                    });
                    threadContainer.scrollTop = threadContainer.scrollHeight;
                }

                // Show feedback section if ticket is resolved
                const feedbackSection = document.getElementById('custFeedbackSection');
                if (feedbackSection) {
                    if (ticket.status === 'Resolved' && !ticket.satisfaction_score) {
                        feedbackSection.style.display = 'block';
                        document.getElementById('feedbackTicketIdInput').value = ticket.ticket_id;
                    } else if (ticket.satisfaction_score) {
                        feedbackSection.style.display = 'block';
                        feedbackSection.innerHTML = `
                            <div class="alert alert-info py-2 px-3 mb-0" style="background: #202126; border: 1px solid rgba(255, 255, 255, 0.12); color: #FFF;">
                                <i class="bi bi-star-fill text-warning me-2"></i> You rated this ticket <strong>${ticket.satisfaction_score} / 5 Stars</strong>.
                            </div>
                        `;
                    } else {
                        feedbackSection.style.display = 'none';
                    }
                }

                openModal(modal);
            } else {
                showCustomAlert('Error', data.message || 'Failed to load ticket details.', 'danger');
            }
        })
        .catch(err => {
            showCustomAlert('Connection Error', 'Could not retrieve ticket conversation.', 'danger');
        });
}

function updateStepTrackerUI(trackerId, status) {
    const tracker = document.getElementById(trackerId);
    if (!tracker) return;

    const steps = ['Submitted', 'Under Review', 'In Progress', 'Resolved', 'Closed'];
    let activeIdx = steps.indexOf(status);
    if (activeIdx === -1) activeIdx = 0;

    const items = tracker.querySelectorAll('.step-item');
    items.forEach((item, idx) => {
        item.classList.remove('active', 'completed');
        if (idx < activeIdx) {
            item.classList.add('completed');
        } else if (idx === activeIdx) {
            item.classList.add('active');
        }
    });

    const progressBar = tracker.querySelector('.step-tracker-progress');
    if (progressBar) {
        const percentage = (activeIdx / (steps.length - 1)) * 100;
        progressBar.style.width = `calc(${percentage}% - 60px)`;
    }
}

/* ==========================================================================
   4. AGENT PORTAL - SPLIT WORKSPACE
   ========================================================================== */

function selectAgentTicket(ticketId, clickedElement) {
    // Highlight active ticket row
    document.querySelectorAll('.agent-ticket-row').forEach(el => el.classList.remove('active-ticket-row'));
    if (clickedElement) clickedElement.classList.add('active-ticket-row');

    // Show workspace, hide empty state
    const workspace = document.getElementById('agentTicketWorkspace');
    const emptyState = document.getElementById('agentEmptyState');
    if (emptyState) emptyState.style.display = 'none';
    if (workspace) workspace.style.display = 'flex';

    // Show loading indicator
    document.getElementById('agentThreadContainer').innerHTML = '<div class="text-center py-5"><div class="spinner-border"></div></div>';

    // Fetch ticket details via AJAX
    fetch(`/agent/tickets/${ticketId}/details`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                const ticket = data.ticket;
                const replies = data.replies;

                // Update ticket information
                document.getElementById('agentTicketIdHeading').textContent = ticket.ticket_id;
                document.getElementById('agentTicketSubject').textContent = ticket.subject;
                document.getElementById('agentCustomerName').textContent = ticket.customer_name;
                document.getElementById('agentCustomerEmail').textContent = ticket.customer_email;

                // Update status and resolution notes
                const statusSelect = document.getElementById('agentStatusSelect');
                if (statusSelect) statusSelect.value = ticket.status;
                const notesInput = document.getElementById('agentResolutionNotes');
                if (notesInput) notesInput.value = ticket.resolution_notes || '';

                document.getElementById('agentReplyForm').action = `/agent/tickets/${ticket.ticket_id}/reply`;

                // Render conversation thread
                const threadContainer = document.getElementById('agentThreadContainer');
                threadContainer.innerHTML = '';
                replies.forEach(r => {
                    const isCustomer = r.sender_role === 'customer';
                    const bubble = document.createElement('div');
                    bubble.className = `chat-bubble ${isCustomer ? 'chat-bubble-customer' : 'chat-bubble-agent'}`;
                    bubble.innerHTML = `
                        <div class="fw-bold mb-1" style="font-size: 0.8rem; color: ${isCustomer ? '#FFF' : '#D5D5D5'};">
                            ${escapeHtml(r.sender_name)} ${isCustomer ? '(Customer)' : '(Agent)'}
                        </div>
                        <div style="white-space: pre-wrap;">${escapeHtml(r.message)}</div>
                        <div class="chat-meta">
                            <span>${new Date(r.created_at).toLocaleString()}</span>
                        </div>
                    `;
                    threadContainer.appendChild(bubble);
                });
                threadContainer.scrollTop = threadContainer.scrollHeight;

                // Update AI predictions display
                const catBadge = document.getElementById('agentAiCategoryBadge');
                if (catBadge) {
                    catBadge.textContent = ticket.predicted_category;
                }

                const prioPill = document.getElementById('agentAiPriorityPill');
                if (prioPill) {
                    prioPill.textContent = ticket.predicted_priority;
                    prioPill.className = `badge-priority badge-priority-${ticket.predicted_priority}`;
                }

            } else {
                showCustomAlert('Error', data.message || 'Failed to load ticket workspace.', 'danger');
            }
        })
        .catch(err => {
            showCustomAlert('Error', 'Unable to connect to support server.', 'danger');
        });
}

/* ==========================================================================
   5. SIDEBAR NAVIGATION (3 links + Sign Out per role)
   ========================================================================== */

function initSidebarNavigation() {
    // Find scroll container
    const scrollContainer = document.querySelector('.main-content') ||
                            document.querySelector('.page-wrapper') ||
                            document.documentElement;

    // Attach click handlers to sidebar links
    const sidebarLinks = document.querySelectorAll('.sidebar-nav-item, .nav-link, [data-nav-action]');

    sidebarLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            const action = this.getAttribute('data-nav-action');

            // Handle logout - let it proceed normally
            if (action === 'logout') {
                return;
            }

            // Get target section ID
            let targetId = getTargetSectionId(action);
            if (!targetId) return;

            const targetEl = document.getElementById(targetId);
            if (!targetEl) return;

            e.preventDefault();

            // Update active menu styling
            sidebarLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');

            // Apply queue filters for agent dashboard
            if (action === 'assigned-queue' && typeof triggerQueueFilter === 'function') {
                triggerQueueFilter('all');
            }
            if (action === 'pending-submitted' && typeof triggerQueueFilter === 'function') {
                triggerQueueFilter('Submitted');
            }
            if (action === 'in-progress' && typeof triggerQueueFilter === 'function') {
                triggerQueueFilter('In Progress');
            }
            if (action === 'resolved-tickets' && typeof triggerQueueFilter === 'function') {
                triggerQueueFilter('Resolved');
            }

            // Apply filters for customer dashboard
            if (action === 'ticket-history' && typeof filterTicketHistory === 'function') {
                filterTicketHistory();
            }
            if (action === 'my-tickets' && typeof resetTicketFilter === 'function') {
                resetTicketFilter();
            }

            // Refresh admin charts
            if (action === 'analytics' && typeof refreshAdminCharts === 'function') {
                refreshAdminCharts();
            }

            // Scroll to target section
            scrollToSection(targetId, scrollContainer);

            // Focus subject input for create ticket
            if (action === 'create-ticket') {
                setTimeout(() => {
                    const subjectInput = document.getElementById('subject');
                    if (subjectInput) {
                        subjectInput.focus();
                    }
                }, 500);
            }
        });
    });
}

function getTargetSectionId(action) {
    const actionMap = {
        'dashboard': 'customer-stats-section',
        'my-tickets': 'customer-tickets-table',
        'create-ticket': 'create-ticket-section',
        'ticket-history': 'customer-tickets-table',
        'assigned-queue': 'department-ticket-table',
        'pending-submitted': 'department-ticket-table',
        'in-progress': 'department-ticket-table',
        'resolved-tickets': 'department-ticket-table',
        'all-tickets': 'admin-all-tickets-section',
        'user-management': 'user-verification-card',
        'analytics': 'admin-analytics-section'
    };

    // Determine dashboard context
    const currentPath = window.location.pathname;
    if (currentPath.includes('/admin')) {
        return actionMap[action] || null;
    } else if (currentPath.includes('/agent')) {
        return actionMap[action] || null;
    } else if (currentPath.includes('/customer')) {
        return actionMap[action] || null;
    }

    return actionMap[action] || null;
}

function triggerQueueFilter(status) {
    const filterButtons = document.querySelectorAll('.queue-status-tabs a');
    filterButtons.forEach(btn => {
        const btnStatus = btn.getAttribute('href').split('status=')[1];
        if (btnStatus === status) {
            window.location.href = btn.getAttribute('href');
        }
    });
}

function filterTicketHistory() {
    const table = document.querySelector('#customer-tickets-table table tbody');
    if (!table) return;

    const rows = table.querySelectorAll('tr');
    rows.forEach(row => {
        const statusCell = row.querySelector('td:nth-child(5)');
        if (statusCell) {
            const statusText = statusCell.textContent.trim();
            if (statusText === 'Resolved' || statusText === 'Closed') {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        }
    });
}

function resetTicketFilter() {
    const table = document.querySelector('#customer-tickets-table table tbody');
    if (!table) return;

    const rows = table.querySelectorAll('tr');
    rows.forEach(row => {
        row.style.display = '';
    });
}

function refreshAdminCharts() {
    const charts = document.querySelectorAll('canvas');
    charts.forEach(canvas => {
        if (canvas.chart) {
            canvas.chart.update();
        }
    });
}

function scrollToSection(sectionId, scrollContainer) {
    const section = document.getElementById(sectionId);
    if (!section) return;

    const DESIRED_TOP_OFFSET = 24;

    if (scrollContainer && scrollContainer !== document.documentElement && scrollContainer !== document.body) {
        const containerRect = scrollContainer.getBoundingClientRect();
        const targetRect = section.getBoundingClientRect();
        const targetPosition = targetRect.top - containerRect.top + scrollContainer.scrollTop - DESIRED_TOP_OFFSET;

        scrollContainer.scrollTo({
            top: Math.max(0, targetPosition),
            behavior: 'smooth'
        });
    } else {
        const targetTop = section.getBoundingClientRect().top + window.pageYOffset - DESIRED_TOP_OFFSET;
        window.scrollTo({
            top: Math.max(0, targetTop),
            behavior: 'smooth'
        });
    }

    // Visual focus highlight
    section.classList.remove('section-focus-highlight');
    void section.offsetWidth;
    section.classList.add('section-focus-highlight');
    setTimeout(() => section.classList.remove('section-focus-highlight'), 1200);
}

/* ==========================================================================
   6. ADMIN ANALYTICS - CHART.JS INITIALIZATION
   ========================================================================== */

function initAdminCharts(deptLabels, deptData) {
    // Configure Chart.js for dark theme
    Chart.defaults.color = '#8E9CAE';
    Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.08)';
    Chart.defaults.font.family = "'Inter', sans-serif";

    // Category Distribution Bar Chart
    const deptCtx = document.getElementById('deptVolumeChart');
    if (deptCtx) {
        new Chart(deptCtx, {
            type: 'bar',
            data: {
                labels: deptLabels,
                datasets: [{
                    label: 'Tickets',
                    data: deptData,
                    backgroundColor: [
                        'rgba(232, 232, 232, 0.65)',
                        'rgba(209, 213, 219, 0.65)',
                        'rgba(156, 163, 175, 0.65)',
                        'rgba(107, 114, 128, 0.65)',
                        'rgba(75, 85, 99, 0.65)'
                    ],
                    borderColor: [
                        '#E8E8E8',
                        '#D1D5DB',
                        '#9CA3AF',
                        '#6B7280',
                        '#4B5563'
                    ],
                    borderWidth: 1.5,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }
}

/* ==========================================================================
   7. UTILITY FUNCTIONS
   ========================================================================== */

function escapeHtml(string) {
    if (!string) return '';
    const div = document.createElement('div');
    div.innerText = string;
    return div.innerHTML;
}
