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
    fetch(`/customer/tickets/${encodeURIComponent(ticketId)}`, {
        headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(async res => {
            if (!res.ok) {
                let errDetail = `Server returned HTTP ${res.status}`;
                try {
                    const errData = await res.json();
                    errDetail = errData.message || errData.error || errDetail;
                } catch(e) {}
                throw new Error(errDetail);
            }
            return res.json();
        })
        .then(data => {
            if (data.status === 'success' || data.success === true) {
                const ticket = data.ticket || {};
                const replies = data.replies || [];

                // Update ticket information
                const subjEl = document.getElementById('custModalSubject');
                if (subjEl) subjEl.textContent = ticket.subject || 'No Subject';
                const catEl = document.getElementById('custModalCategory');
                if (catEl) catEl.textContent = ticket.predicted_category || ticket.department_name || 'General Inquiry';
                const statusEl = document.getElementById('custModalStatus');
                if (statusEl) {
                    const st = ticket.status || 'Submitted';
                    statusEl.textContent = st;
                    statusEl.className = `badge-status badge-status-${st.replace(/\s+/g, '')}`;
                }

                // Update step progress tracker
                updateStepTrackerUI('custStepTracker', ticket.status || 'Submitted');

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
                                ${escapeHtml(r.sender_name || 'User')} ${isCustomer ? '(You)' : '(Support Agent)'}
                            </div>
                            <div style="white-space: pre-wrap;">${escapeHtml(r.message || '')}</div>
                            <div class="chat-meta">
                                <span>${r.created_at ? new Date(r.created_at).toLocaleString() : ''}</span>
                            </div>
                        `;
                        threadContainer.appendChild(bubble);
                    });
                    threadContainer.scrollTop = threadContainer.scrollHeight;
                }

                // Show feedback section if ticket is resolved
                const feedbackSection = document.getElementById('custFeedbackSection');
                if (feedbackSection) {
                    if ((ticket.status === 'Resolved' || ticket.status === 'Closed') && !ticket.satisfaction_score) {
                        feedbackSection.style.display = 'block';
                        const fbInput = document.getElementById('feedbackTicketIdInput');
                        if (fbInput) fbInput.value = ticket.ticket_id || ticket.ticketno || ticketId;
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
                console.error('Failed to load customer ticket details:', data);
                showCustomAlert('Error', data.message || data.error || 'Failed to load ticket details.', 'danger');
            }
        })
        .catch(err => {
            console.error('Error loading customer ticket details:', err);
            showCustomAlert('Connection Error', err.message || 'Could not retrieve ticket conversation.', 'danger');
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
    fetch(`/agent/tickets/${encodeURIComponent(ticketId)}/details`, {
        headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(async res => {
            if (!res.ok) {
                let errDetail = `Server returned HTTP ${res.status}`;
                try {
                    const errData = await res.json();
                    errDetail = errData.message || errData.error || errDetail;
                } catch(e) {}
                throw new Error(errDetail);
            }
            return res.json();
        })
        .then(data => {
            if (data.status === 'success' || data.success === true) {
                const ticket = data.ticket || {};
                const replies = data.replies || [];
                const tktNo = ticket.ticket_id || ticket.ticketno || ticketId;

                // Update ticket information
                const idHeading = document.getElementById('agentTicketIdHeading');
                if (idHeading) idHeading.textContent = tktNo;
                const subjEl = document.getElementById('agentTicketSubject');
                if (subjEl) subjEl.textContent = ticket.subject || 'No Subject';
                const custName = document.getElementById('agentCustomerName');
                if (custName) custName.textContent = ticket.customer_name || 'Customer';
                const custEmail = document.getElementById('agentCustomerEmail');
                if (custEmail) custEmail.textContent = ticket.customer_email || '—';

                // Update status and resolution notes
                const statusSelect = document.getElementById('agentStatusSelect');
                if (statusSelect) statusSelect.value = ticket.status || 'Submitted';
                const notesInput = document.getElementById('agentResolutionNotes');
                if (notesInput) notesInput.value = ticket.resolution_notes || '';

                const replyForm = document.getElementById('agentReplyForm');
                if (replyForm) replyForm.action = `/agent/tickets/${tktNo}/reply`;

                // Render conversation thread
                const threadContainer = document.getElementById('agentThreadContainer');
                if (threadContainer) {
                    threadContainer.innerHTML = '';
                    replies.forEach(r => {
                        const isCustomer = r.sender_role === 'customer';
                        const bubble = document.createElement('div');
                        bubble.className = `chat-bubble ${isCustomer ? 'chat-bubble-customer' : 'chat-bubble-agent'}`;
                        bubble.innerHTML = `
                            <div class="fw-bold mb-1" style="font-size: 0.8rem; color: ${isCustomer ? '#FFF' : '#D5D5D5'};">
                                ${escapeHtml(r.sender_name || 'Sender')} ${isCustomer ? '(Customer)' : '(Agent)'}
                            </div>
                            <div style="white-space: pre-wrap;">${escapeHtml(r.message || '')}</div>
                            <div class="chat-meta">
                                <span>${r.created_at ? new Date(r.created_at).toLocaleString() : ''}</span>
                            </div>
                        `;
                        threadContainer.appendChild(bubble);
                    });
                    threadContainer.scrollTop = threadContainer.scrollHeight;
                }

                // Update AI predictions display
                const catBadge = document.getElementById('agentAiCategoryBadge');
                if (catBadge) {
                    catBadge.textContent = ticket.predicted_category || ticket.department_name || 'General Inquiry';
                }

                const prioPill = document.getElementById('agentAiPriorityPill');
                if (prioPill) {
                    const prio = ticket.predicted_priority || 'Medium';
                    prioPill.textContent = prio;
                    prioPill.className = `badge-priority badge-priority-${prio}`;
                }

            } else {
                console.error('Failed to load agent ticket workspace:', data);
                showCustomAlert('Error', data.message || data.error || 'Failed to load ticket workspace.', 'danger');
            }
        })
        .catch(err => {
            console.error("Ticket details fetch error:", err);
            alert("Error loading ticket details: " + err.message);
        });
}

/**
 * Loads agent ticket details via AJAX fetch with exact error diagnostics.
 * Invoked from department queue "View Details" action.
 */
function loadAgentTicketDetails(ticketId) {
    fetch(`/agent/tickets/${encodeURIComponent(ticketId)}/details`, {
        headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(res => {
        if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
        return res.json();
    })
    .then(data => renderDetailsModal(data))
    .catch(err => {
        console.error("Ticket details fetch error:", err);
        alert("Error loading ticket details: " + err.message);
    });
}

/**
 * Renders agent ticket details inside an interactive modal.
 */
function renderDetailsModal(data) {
    if (!data || !(data.status === 'success' || data.success === true)) {
        const errMsg = data ? (data.message || data.error || 'Unknown server error') : 'No response received';
        console.error("Ticket details fetch error:", data);
        alert("Error loading ticket details: " + errMsg);
        return;
    }

    const ticket = data.ticket || {};
    const replies = data.replies || [];
    const similar = data.similar_matches || [];
    const tktNo = ticket.ticket_id || ticket.ticketno || 'N/A';

    let modal = document.getElementById('agentTicketDetailsModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'agentTicketDetailsModal';
        modal.className = 'custom-modal-backdrop';
        document.body.appendChild(modal);
    }

    const st = ticket.status || 'Submitted';
    const prio = ticket.predicted_priority || 'Medium';
    const cat = ticket.predicted_category || ticket.department_name || 'General Inquiry';

    modal.innerHTML = `
        <div class="custom-modal-dialog" style="max-width: 840px; width: 92%; margin: 30px auto; background: #16171A; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; box-shadow: 0 25px 50px rgba(0, 0, 0, 0.7); overflow: hidden; display: flex; flex-direction: column; max-height: 90vh;">
            <div style="padding: 16px 24px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); display: flex; justify-content: space-between; align-items: center; background: #1C1D21;">
                <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                    <span style="font-family: 'Courier New', monospace; font-size: 1.15rem; font-weight: 700; color: #10b981;">${escapeHtml(tktNo)}</span>
                    <span class="badge badge-priority-${escapeHtml(prio)}">${escapeHtml(prio)}</span>
                    <span class="badge badge-category-${escapeHtml(cat.replace(/\s+/g, '').replace(/&/g, ''))}">${escapeHtml(cat)}</span>
                    <span class="badge badge-status-${escapeHtml(st.replace(/\s+/g, ''))}">${escapeHtml(st)}</span>
                </div>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <a href="/agent/tickets/${encodeURIComponent(tktNo)}/details" class="btn btn-secondary btn-sm" style="font-size: 0.8rem; padding: 4px 10px; display: inline-flex; align-items: center; gap: 4px;">
                        <i class="bi bi-box-arrow-up-right"></i> Full Page
                    </a>
                    <button type="button" class="modal-close-btn" onclick="closeModal('#agentTicketDetailsModal')" style="background: none; border: none; color: #9CA3AF; font-size: 1.5rem; cursor: pointer; line-height: 1;">&times;</button>
                </div>
            </div>
            
            <div style="padding: 24px; overflow-y: auto; flex: 1;">
                <h3 style="font-size: 1.2rem; margin-top: 0; margin-bottom: 12px; color: #FFF;">${escapeHtml(ticket.subject || 'No Subject')}</h3>
                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px; color: #E5E7EB; line-height: 1.5; font-size: 0.92rem; margin-bottom: 20px; white-space: pre-wrap;">${escapeHtml(ticket.description || '')}</div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 20px; font-size: 0.85rem; background: rgba(0, 0, 0, 0.25); padding: 12px 16px; border-radius: 8px;">
                    <div><span style="color: #9CA3AF;">Customer:</span> <strong style="color: #FFF;">${escapeHtml(ticket.customer_name || 'Customer')}</strong></div>
                    <div><span style="color: #9CA3AF;">Email:</span> <span style="color: #93C5FD;">${escapeHtml(ticket.customer_email || '—')}</span></div>
                    <div><span style="color: #9CA3AF;">Department:</span> <span style="color: #FFF;">${escapeHtml(ticket.department_name || ticket.assigned_department || 'General Inquiry')}</span></div>
                    <div><span style="color: #9CA3AF;">Submitted:</span> <span style="color: #9CA3AF;">${escapeHtml((ticket.submitdate || '').substring(0, 19))}</span></div>
                </div>

                ${ticket.satisfaction_score ? `
                    <div style="background: rgba(234, 179, 8, 0.08); border: 1px solid rgba(234, 179, 8, 0.25); border-radius: 8px; padding: 12px 16px; margin-bottom: 20px;">
                        <span style="color: #facc15; font-weight: 700; font-size: 1.05rem;">★ ${ticket.satisfaction_score} / 5.0</span>
                        <span style="color: #9CA3AF; font-size: 0.8rem; margin-left: 8px;">Customer CSAT Rating</span>
                        ${ticket.customer_feedback ? `<div style="color: #E2E8F0; font-size: 0.88rem; font-style: italic; margin-top: 4px;">"${escapeHtml(ticket.customer_feedback)}"</div>` : ''}
                    </div>
                ` : ''}

                ${similar.length > 0 ? `
                    <div style="margin-bottom: 20px;">
                        <div style="font-size: 0.9rem; font-weight: 600; color: #10b981; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                            <i class="bi bi-robot"></i> AI Similar Recommendations
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 10px;">
                            ${similar.map(m => `
                                <div style="background: #1C1D21; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 10px; font-size: 0.82rem;">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                        <span style="color: #10b981; font-family: monospace;">${escapeHtml(m.similar_ticket_ref_id || '')}</span>
                                        <span style="color: #93C5FD;">${Math.round((m.similarity_score || 0.8) * 100)}%</span>
                                    </div>
                                    <div style="font-weight: 500; color: #FFF; margin-bottom: 4px;">${escapeHtml(m.similar_subject || '')}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                <h4 style="font-size: 0.95rem; margin-bottom: 10px; color: #FFF;">Conversation History (${replies.length})</h4>
                <div style="background: #121315; border-radius: 8px; padding: 12px; max-height: 200px; overflow-y: auto; margin-bottom: 20px;">
                    ${replies.length === 0 ? '<p style="color: #9CA3AF; text-align: center; margin: 10px 0; font-size: 0.85rem;">No conversation messages yet.</p>' : replies.map(r => `
                        <div style="margin-bottom: 10px; padding: 8px 12px; border-radius: 6px; background: ${r.sender_role === 'agent' ? '#22344D' : '#26272B'}; border: 1px solid rgba(255, 255, 255, 0.06);">
                            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #9CA3AF; margin-bottom: 4px;">
                                <strong>${escapeHtml(r.sender_name || 'User')} (${escapeHtml((r.sender_role || 'agent'))})</strong>
                                <span>${r.created_at ? escapeHtml(r.created_at) : ''}</span>
                            </div>
                            <div style="color: #F3F4F6; font-size: 0.9rem; white-space: pre-wrap;">${escapeHtml(r.message || '')}</div>
                        </div>
                    `).join('')}
                </div>

                <form method="POST" action="/agent/tickets/${encodeURIComponent(tktNo)}/reply">
                    <div style="margin-bottom: 12px;">
                        <label style="font-size: 0.85rem; font-weight: 500; color: #D5D5D5; display: block; margin-bottom: 4px;">Response Message</label>
                        <textarea name="message" class="form-control" rows="3" placeholder="Compose message to customer..." style="width: 100%; background: #1C1D21; color: white; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 8px; font-family: inherit; font-size: 0.9rem;"></textarea>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
                        <div>
                            <label style="font-size: 0.85rem; font-weight: 500; color: #D5D5D5; display: block; margin-bottom: 4px;">Status</label>
                            <select name="status" class="form-select" style="width: 100%; height: 38px; background: #1C1D21; color: white; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 0 8px;">
                                <option value="" selected>Keep Current (${escapeHtml(st)})</option>
                                <option value="Under Review">Under Review</option>
                                <option value="In Progress">In Progress</option>
                                <option value="Resolved">Resolved</option>
                                <option value="Closed">Closed</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size: 0.85rem; font-weight: 500; color: #D5D5D5; display: block; margin-bottom: 4px;">Resolution Notes</label>
                            <input type="text" name="resolution_notes" class="form-control" placeholder="Fix details..." style="width: 100%; height: 38px; background: #1C1D21; color: white; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; padding: 0 8px;">
                        </div>
                    </div>
                    <div style="display: flex; justify-content: flex-end; gap: 10px;">
                        <button type="button" class="btn btn-secondary btn-sm" onclick="closeModal('#agentTicketDetailsModal')">Close</button>
                        <button type="submit" class="btn btn-primary btn-sm" style="padding: 8px 18px; font-weight: 600;">Update Ticket</button>
                    </div>
                </form>
            </div>
        </div>
    `;

    openModal(modal);
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
