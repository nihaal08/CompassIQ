/**
 * CompassIQ — Frontend Controller & Glassmorphism Interactivity
 * =============================================================
 * Handles centered modal alert dismissal (Top-Left 'X'), dynamic ticket
 * workspace loading, live conversations, star rating, and Chart.js analytics.
 */

document.addEventListener('DOMContentLoaded', () => {
    initAlertModals();
    initStarRatings();
    initSidebarNavigation();
});

/* ==========================================================================
   1. CENTERED MODAL ALERT SYSTEM (TOP-LEFT CLOSE BUTTON)
   ========================================================================== */

function initAlertModals() {
    // Top-right close buttons (updated class)
    const closeBtns = document.querySelectorAll('.modal-close-btn');
    closeBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const modalBackdrop = btn.closest('.alert-modal-backdrop') || btn.closest('.custom-modal-backdrop') || btn.closest('.ticket-modal-backdrop');
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

    // Close when clicking outside modal box
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
 * Dynamically trigger a centered modal alert with top-left 'X' button
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
                    Understood
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
        case 'pending_approval':
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
   2. STAR RATING WIDGET
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
   3. CUSTOMER PORTAL INTERACTION
   ========================================================================== */

function openCustomerTicketModal(ticketId) {
    const modal = document.getElementById('customerTicketModal');
    if (!modal) return;

    // Reset thread
    const threadContainer = document.getElementById('custChatThread');
    threadContainer.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-cyan" role="status"></div></div>';
    
    document.getElementById('custModalTicketId').textContent = ticketId;
    document.getElementById('custReplyForm').action = `/customer/tickets/${ticketId}/reply`;

    fetch(`/customer/tickets/${ticketId}`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                const ticket = data.ticket;
                const replies = data.replies;

                document.getElementById('custModalSubject').textContent = ticket.subject;
                document.getElementById('custModalCategory').textContent = ticket.predicted_category;
                document.getElementById('custModalStatus').textContent = ticket.status;
                document.getElementById('custModalStatus').className = `badge-status badge-status-${ticket.status.replace(/\s+/g, '')}`;

                // Update Visual Step Progress
                updateStepTrackerUI('custStepTracker', ticket.status);

                // Render Thread
                threadContainer.innerHTML = '';
                if (replies.length === 0) {
                    threadContainer.innerHTML = '<p class="text-muted text-center my-3">No messages yet.</p>';
                } else {
                    replies.forEach(r => {
                        const isCustomer = r.sender_role === 'customer';
                        const bubble = document.createElement('div');
                        bubble.className = `chat-bubble ${isCustomer ? 'chat-bubble-customer' : 'chat-bubble-agent'}`;
                        bubble.innerHTML = `
                            <div class="fw-bold mb-1" style="font-size: 0.8rem; color: ${isCustomer ? '#FFF' : '#00D2FF'};">
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

                // Show Feedback CTA if resolved
                const feedbackSection = document.getElementById('custFeedbackSection');
                if (feedbackSection) {
                    if (ticket.status === 'Resolved' && !ticket.satisfaction_score) {
                        feedbackSection.style.display = 'block';
                        document.getElementById('feedbackTicketIdInput').value = ticket.ticket_id;
                    } else if (ticket.satisfaction_score) {
                        feedbackSection.style.display = 'block';
                        feedbackSection.innerHTML = `
                            <div class="alert alert-info py-2 px-3 mb-0" style="background: rgba(0, 210, 255, 0.1); border: 1px solid #00D2FF; color: #FFF;">
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
   4. DEPARTMENT AGENT SPLIT WORKSPACE INTERACTION
   ========================================================================== */

function selectAgentTicket(ticketId, clickedElement) {
    // Highlight active card
    document.querySelectorAll('.agent-ticket-row').forEach(el => el.classList.remove('active-ticket-row'));
    if (clickedElement) clickedElement.classList.add('active-ticket-row');

    const workspace = document.getElementById('agentTicketWorkspace');
    const emptyState = document.getElementById('agentEmptyState');
    if (emptyState) emptyState.style.display = 'none';
    if (workspace) workspace.style.display = 'flex';

    // Show loading indicators
    document.getElementById('agentThreadContainer').innerHTML = '<div class="text-center py-5"><div class="spinner-border text-cyan"></div></div>';
    document.getElementById('aiSimilarTicketsContainer').innerHTML = '<div class="text-center py-5"><div class="spinner-border text-cyan"></div></div>';

    fetch(`/agent/tickets/${ticketId}/details`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                const ticket = data.ticket;
                const replies = data.replies;
                const matches = data.similar_matches;

                // Left Panel Header & Details
                document.getElementById('agentTicketIdHeading').textContent = ticket.ticket_id;
                document.getElementById('agentTicketSubject').textContent = ticket.subject;
                document.getElementById('agentCustomerName').textContent = ticket.customer_name;
                document.getElementById('agentCustomerEmail').textContent = ticket.customer_email;
                document.getElementById('agentCustomerProduct').textContent = ticket.customer_product_id || 'N/A';

                // Status & Resolution Notes Form
                const statusSelect = document.getElementById('agentStatusSelect');
                if (statusSelect) statusSelect.value = ticket.status;
                const notesInput = document.getElementById('agentResolutionNotes');
                if (notesInput) notesInput.value = ticket.resolution_notes || '';

                document.getElementById('agentReplyForm').action = `/agent/tickets/${ticket.ticket_id}/reply`;

                // Render Left Conversation Thread
                const threadContainer = document.getElementById('agentThreadContainer');
                threadContainer.innerHTML = '';
                replies.forEach(r => {
                    const isCustomer = r.sender_role === 'customer';
                    const bubble = document.createElement('div');
                    bubble.className = `chat-bubble ${isCustomer ? 'chat-bubble-customer' : 'chat-bubble-agent'}`;
                    bubble.innerHTML = `
                        <div class="fw-bold mb-1" style="font-size: 0.8rem; color: ${isCustomer ? '#FFF' : '#00D2FF'};">
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

                // Right Panel: AI Intelligence
                const catBadge = document.getElementById('agentAiCategoryBadge');
                if (catBadge) {
                    catBadge.textContent = ticket.predicted_category;
                }

                const prioPill = document.getElementById('agentAiPriorityPill');
                if (prioPill) {
                    prioPill.textContent = ticket.predicted_priority;
                    prioPill.className = `badge-priority badge-priority-${ticket.predicted_priority}`;
                }

                // Render Top-3 Similar Matches
                const matchesContainer = document.getElementById('aiSimilarTicketsContainer');
                matchesContainer.innerHTML = '';
                
                if (!matches || matches.length === 0) {
                    matchesContainer.innerHTML = '<p class="text-muted text-center py-4">No matching historical tickets computed.</p>';
                } else {
                    matches.forEach((m, idx) => {
                        const card = document.createElement('div');
                        card.className = 'ai-recommendation-card';
                        card.innerHTML = `
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span class="similarity-pill">
                                    <i class="bi bi-cpu me-1"></i> ${m.similarity_score}% Match
                                </span>
                                <span class="text-dim font-monospace small">${escapeHtml(m.similar_ticket_ref_id)}</span>
                            </div>
                            <h6 class="text-white mb-1" style="font-size: 0.92rem;">${escapeHtml(m.similar_subject)}</h6>
                            <p class="text-muted small mb-2" style="line-height: 1.35;">${escapeHtml(m.similar_description)}</p>
                            <div class="d-flex justify-content-between align-items-center pt-2 border-top border-secondary border-opacity-25" style="font-size: 0.75rem;">
                                <span class="text-cyan"><i class="bi bi-clock-history me-1"></i> Avg Resolution: ${m.historical_resolution_hours || 'N/A'} hrs</span>
                                <button type="button" class="btn btn-sm btn-cyber-outline py-0 px-2" onclick="copyHistoricalContext('${escapeHtml(m.similar_description).replace(/'/g, "\\'")}')">
                                    Use Solution
                                </button>
                            </div>
                        `;
                        matchesContainer.appendChild(card);
                    });
                }

            } else {
                showCustomAlert('Error', data.message || 'Failed to load ticket workspace.', 'danger');
            }
        })
        .catch(err => {
            showCustomAlert('Error', 'Unable to connect to support server.', 'danger');
        });
}

function copyHistoricalContext(text) {
    const replyBox = document.getElementById('agentReplyMessage');
    if (replyBox) {
        replyBox.value = `Referencing solution:\n${text}\n\n`;
        replyBox.focus();
    }
}

/* ==========================================================================
   5. SIDEBAR NAVIGATION HANDLERS
   ========================================================================== */

function initSidebarNavigation() {
  // 1. Locate the true scroll container
  const scrollContainer = document.querySelector('.main-content') ||
                          document.querySelector('.page-wrapper') ||
                          document.documentElement;

  // 2. Attach click handlers to all sidebar navigation links
  const sidebarLinks = document.querySelectorAll('.sidebar-nav-item, .nav-link, [data-nav-action]');

  sidebarLinks.forEach(link => {
    link.addEventListener('click', function (e) {
      const action = this.getAttribute('data-nav-action');

      // Handle logout action - let it proceed normally
      if (action === 'logout') {
        return;
      }

      // Get target section ID based on action
      let targetId = getTargetSectionId(action);
      if (!targetId) return;

      const targetEl = document.getElementById(targetId);
      if (!targetEl) return;

      e.preventDefault();

      // Update active menu link styling
      sidebarLinks.forEach(l => l.classList.remove('active'));
      this.classList.add('active');

      // Handle special actions that don't require scrolling
      if (action === 'profile' && typeof openProfileModal === 'function') {
        openProfileModal();
        return;
      }

      if (action === 'ai-insights') {
        const modal = document.getElementById('ticketModal');
        if (modal && modal.classList.contains('show')) {
          scrollToSection('ai-insights-section', scrollContainer);
        } else {
          showCustomAlert('AI Insights', 'Open a ticket to view AI-powered similarity recommendations and confidence scores.', 'info');
        }
        return;
      }

      // Apply queue filters before scrolling
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

      if (action === 'ticket-history' && typeof filterTicketHistory === 'function') {
        filterTicketHistory();
      }

      if (action === 'my-tickets' && typeof resetTicketFilter === 'function') {
        resetTicketFilter();
      }

      if (action === 'analytics' && typeof refreshAdminCharts === 'function') {
        refreshAdminCharts();
      }

      // Perform scrolling
      scrollToSection(targetId, scrollContainer);

      // Special focus for create ticket
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
    'ai-insights': 'ai-insights-section',
    'all-tickets': 'admin-all-tickets-section',
    'user-approvals': 'user-verification-card',
    'fraud-center': 'fraud-escalation-center',
    'analytics': 'admin-analytics-section'
  };

  // Determine which dashboard we're on
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

// Add missing triggerQueueFilter function for sidebar navigation
function triggerQueueFilter(status) {
    const filterButtons = document.querySelectorAll('.queue-status-tabs a');
    filterButtons.forEach(btn => {
        const btnStatus = btn.getAttribute('href').split('status=')[1];
        if (btnStatus === status) {
            window.location.href = btn.getAttribute('href');
        }
    });
}

// Add missing filterTicketHistory function for customer dashboard
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

// Add missing resetTicketFilter function for customer dashboard
function resetTicketFilter() {
    const table = document.querySelector('#customer-tickets-table table tbody');
    if (!table) return;

    const rows = table.querySelectorAll('tr');
    rows.forEach(row => {
        row.style.display = '';
    });
}

// Add missing refreshAdminCharts function for admin dashboard
function refreshAdminCharts() {
    // Trigger chart update animation
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

  // Top padding/offset so the card is not flush against the top edge
  const DESIRED_TOP_OFFSET = 24;

  // If scrolling is inside .main-content
  if (scrollContainer && scrollContainer !== document.documentElement && scrollContainer !== document.body) {
    const containerRect = scrollContainer.getBoundingClientRect();
    const targetRect = section.getBoundingClientRect();

    // Calculate position relative to container's current scroll position
    const targetPosition = targetRect.top - containerRect.top + scrollContainer.scrollTop - DESIRED_TOP_OFFSET;

    scrollContainer.scrollTo({
      top: Math.max(0, targetPosition),
      behavior: 'smooth'
    });
  } else {
    // Fallback for standard document window scrolling (no fixed header offset needed)
    const targetTop = section.getBoundingClientRect().top + window.pageYOffset - DESIRED_TOP_OFFSET;
    window.scrollTo({
      top: Math.max(0, targetTop),
      behavior: 'smooth'
    });
  }

  // Visual focus ring to highlight the targeted card
  section.classList.remove('section-focus-highlight');
  void section.offsetWidth; // Force reflow
  section.classList.add('section-focus-highlight');
  setTimeout(() => section.classList.remove('section-focus-highlight'), 1200);
}

/* ==========================================================================
   6. ADMIN ANALYTICS CHART INITIALIZATION (Chart.js)
   ========================================================================== */

function initAdminCharts(deptLabels, deptData, prioLabels, prioData, satLabels, satData) {
    // Chart.js Dark Mode Global Defaults
    Chart.defaults.color = '#8E9CAE';
    Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.08)';
    Chart.defaults.font.family = "'Inter', sans-serif";

    // 1. Department Volume Bar Chart
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
                        'rgba(0, 210, 255, 0.65)',
                        'rgba(0, 102, 255, 0.65)',
                        'rgba(121, 40, 202, 0.65)',
                        'rgba(0, 230, 118, 0.65)',
                        'rgba(255, 51, 102, 0.65)'
                    ],
                    borderColor: [
                        '#00D2FF',
                        '#0066FF',
                        '#7928CA',
                        '#00E676',
                        '#FF3366'
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

    // 2. Priority Distribution Doughnut Chart
    const prioCtx = document.getElementById('priorityDoughnutChart');
    if (prioCtx) {
        new Chart(prioCtx, {
            type: 'doughnut',
            data: {
                labels: prioLabels,
                datasets: [{
                    data: prioData,
                    backgroundColor: [
                        '#FF3366', // Critical
                        '#FF9900', // High
                        '#FFCC00', // Medium
                        '#00E676'  // Low
                    ],
                    borderWidth: 2,
                    borderColor: '#121824'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { boxWidth: 12, padding: 15 }
                    }
                },
                cutout: '70%'
            }
        });
    }

    // 3. Satisfaction Score Chart
    const satCtx = document.getElementById('satisfactionChart');
    if (satCtx) {
        new Chart(satCtx, {
            type: 'bar',
            data: {
                labels: satLabels,
                datasets: [{
                    label: 'Reviews',
                    data: satData,
                    backgroundColor: 'rgba(255, 204, 0, 0.6)',
                    borderColor: '#FFCC00',
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

/* Helper to escape HTML tags */
function escapeHtml(string) {
    if (!string) return '';
    const div = document.createElement('div');
    div.innerText = string;
    return div.innerHTML;
}
