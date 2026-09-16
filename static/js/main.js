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
    initAgentViewDetailsButtons();
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
 * Includes loading state, error handling, and graceful null value display.
 * Now uses unified /api/ticket/<ticketno> endpoint.
 */
function loadAgentTicketDetails(ticketId) {
    // Show loading state in modal
    let modal = document.getElementById('agentTicketDetailsModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'agentTicketDetailsModal';
        modal.className = 'custom-modal-backdrop';
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
        <div style="max-width: 400px; width: 90%; margin: 100px auto; background: #16171A; border: 1px solid rgba(255,255,255,0.12); border-radius: 14px; box-shadow: 0 25px 60px rgba(0,0,0,0.75); padding: 40px; text-align: center;">
            <div style="color: #9CA3AF; font-size: 1rem; margin-bottom: 16px;">
                <i class="bi bi-hourglass-split" style="font-size: 2rem; display: block; margin-bottom: 12px;"></i>
                Loading ticket details...
            </div>
        </div>
    `;
    openModal(modal);

    // Use unified API endpoint
    fetch(`/api/ticket/${encodeURIComponent(ticketId)}`, {
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
        // Show user-friendly error in modal
        modal.innerHTML = `
            <div style="max-width: 400px; width: 90%; margin: 100px auto; background: #16171A; border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 14px; box-shadow: 0 25px 60px rgba(0,0,0,0.75); padding: 30px; text-align: center;">
                <div style="color: #EF4444; font-size: 1.1rem; margin-bottom: 12px;">
                    <i class="bi bi-exclamation-triangle" style="font-size: 2rem; display: block; margin-bottom: 12px;"></i>
                    Unable to load ticket details
                </div>
                <div style="color: #9CA3AF; font-size: 0.9rem; margin-bottom: 20px;">
                    ${escapeHtml(err.message || 'Please try again later')}
                </div>
                <button type="button" onclick="closeModal('#agentTicketDetailsModal')" class="btn btn-secondary" style="padding: 8px 24px;">
                    Close
                </button>
            </div>
        `;
    });
}

/**
 * Renders agent ticket details inside an interactive modal.
 * Shows all ticket fields: assigned agent, predicted category ("Not classified" for null),
 * resolved date, CSAT, customer feedback, replies, and AI similar matches.
 */
function renderDetailsModal(data) {
    if (!data || !(data.status === 'success' || data.success === true)) {
        const errMsg = data ? (data.message || data.error || 'Unknown server error') : 'No response received';
        console.error('Ticket details fetch error:', data);
        showCustomAlert('Error', 'Error loading ticket details: ' + errMsg, 'danger');
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

    // Display "Not classified" when predicted_category is null/empty
    const rawCat = ticket.predicted_category;
    const isUnclassified = !rawCat || rawCat === 'null' || rawCat === 'None';
    const catKey = isUnclassified ? (ticket.department_name || 'GeneralInquiry') : rawCat;
    const catDisplay = isUnclassified ? 'Not classified' : rawCat;

    const assignedAgent = ticket.assigned_agent_name || 'Unassigned';
    const resolvedDate = ticket.resolveddate || ticket.resolved_at || null;

    // Build similar matches section
    let similarHtml;
    if (similar.length > 0) {
        similarHtml = `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px;">
            ${similar.map(m => `
                <div style="background: #1C1D21; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 10px; font-size: 0.82rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="color: #10b981; font-family: monospace; font-size: 0.78rem;">${escapeHtml(m.similar_ticket_ref_id || 'HIST-REF')}</span>
                        <span style="color: #93C5FD; font-size: 0.78rem;">${Math.round((m.similarity_score || 0.8) * 100)}% match</span>
                    </div>
                    <div style="font-weight: 500; color: #FFF; margin-bottom: 4px; font-size: 0.83rem; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;">${escapeHtml(m.similar_subject || 'Similar Historical Ticket')}</div>
                    <div style="color: #9CA3AF; font-size: 0.78rem; line-height: 1.4; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">${escapeHtml(m.similar_description || 'No resolution details recorded.')}</div>
                    <div style="color: #6B7280; font-size: 0.75rem; margin-top: 6px;"><i class="bi bi-clock"></i> Resolved in ${m.historical_resolution_hours || 12}h</div>
                </div>`
            ).join('')}
        </div>`;
    } else {
        similarHtml = `<p style="color: #9CA3AF; font-size: 0.84rem; margin: 0; padding: 8px 0; font-style: italic;">
            <i class="bi bi-info-circle me-1"></i>No historically similar tickets found for this issue.
        </p>`;
    }

    // Build conversation replies section
    let repliesHtml;
    if (replies.length === 0) {
        repliesHtml = '<p style="color: #6B7280; text-align: center; margin: 10px 0; font-size: 0.85rem; font-style: italic;">No conversation messages yet for this ticket.</p>';
    } else {
        repliesHtml = replies.map(r => {
            const isAgent = (r.sender_role === 'agent' || r.sender_role === 'admin');
            return `<div style="margin-bottom: 10px; padding: 10px 13px; border-radius: 6px; background: ${isAgent ? '#22344D' : '#26272B'}; border: 1px solid rgba(255,255,255,0.06);">
                <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #9CA3AF; margin-bottom: 5px;">
                    <strong>${escapeHtml(r.sender_name || 'User')} <span style="font-weight:400;">(${escapeHtml(r.sender_role || 'agent')})</span></strong>
                    <span>${r.created_at ? escapeHtml(r.created_at) : ''}</span>
                </div>
                <div style="color: #F3F4F6; font-size: 0.9rem; white-space: pre-wrap; line-height: 1.5;">${escapeHtml(r.message || '')}</div>
            </div>`;
        }).join('');
    }

    modal.innerHTML = `
        <div style="max-width: 860px; width: 94%; margin: 24px auto; background: #16171A; border: 1px solid rgba(255,255,255,0.12); border-radius: 14px; box-shadow: 0 25px 60px rgba(0,0,0,0.75); overflow: hidden; display: flex; flex-direction: column; max-height: 92vh;">

            <!-- Header -->
            <div style="padding: 16px 24px; border-bottom: 1px solid rgba(255,255,255,0.08); display: flex; justify-content: space-between; align-items: center; background: #1C1D21; flex-shrink: 0;">
                <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                    <span style="font-family: 'Courier New', monospace; font-size: 1.1rem; font-weight: 700; color: #10b981;">${escapeHtml(tktNo)}</span>
                    <span class="badge badge-priority-${escapeHtml(prio)}">${escapeHtml(prio)}</span>
                    <span class="badge badge-category-${escapeHtml(catKey.replace(/\s+/g,'').replace(/&/g,''))}">${escapeHtml(catDisplay)}</span>
                    <span class="badge badge-status-${escapeHtml(st.replace(/\s+/g,''))}">${escapeHtml(st)}</span>
                </div>
                <button type="button" onclick="closeModal('#agentTicketDetailsModal')" title="Close" style="background:none;border:none;color:#9CA3AF;font-size:1.6rem;cursor:pointer;line-height:1;padding:0 4px;">&times;</button>
            </div>

            <!-- Scrollable Body -->
            <div style="padding: 22px 24px; overflow-y: auto; flex: 1;">

                <h3 style="font-size:1.15rem;margin:0 0 16px 0;color:#FFF;line-height:1.4;">${escapeHtml(ticket.subject || 'No Subject')}</h3>

                <!-- Metadata Grid -->
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:20px;background:rgba(0,0,0,0.25);padding:14px 16px;border-radius:8px;border:1px solid rgba(255,255,255,0.06);font-size:0.83rem;">
                    <div><span style="color:#6B7280;display:block;font-size:0.72rem;margin-bottom:2px;">CUSTOMER</span><strong style="color:#FFF;">${escapeHtml(ticket.customer_name || '—')}</strong></div>
                    <div><span style="color:#6B7280;display:block;font-size:0.72rem;margin-bottom:2px;">EMAIL</span><span style="color:#93C5FD;">${escapeHtml(ticket.customer_email || '—')}</span></div>
                    <div><span style="color:#6B7280;display:block;font-size:0.72rem;margin-bottom:2px;">DEPARTMENT</span><span style="color:#E5E7EB;">${escapeHtml(ticket.department_name || ticket.assigned_department || '—')}</span></div>
                    <div><span style="color:#6B7280;display:block;font-size:0.72rem;margin-bottom:2px;">ASSIGNED AGENT</span><span style="color:#E5E7EB;">${escapeHtml(assignedAgent)}</span></div>
                    <div><span style="color:#6B7280;display:block;font-size:0.72rem;margin-bottom:2px;">PREDICTED CATEGORY</span><span style="color:${isUnclassified ? '#9CA3AF' : '#E5E7EB'};font-style:${isUnclassified ? 'italic' : 'normal'}">${escapeHtml(catDisplay)}</span></div>
                    <div><span style="color:#6B7280;display:block;font-size:0.72rem;margin-bottom:2px;">SUBMITTED</span><span style="color:#9CA3AF;">${escapeHtml((ticket.submitdate || '—').substring(0,19))}</span></div>
                    ${resolvedDate ? `<div><span style="color:#6B7280;display:block;font-size:0.72rem;margin-bottom:2px;">RESOLVED</span><span style="color:#9CA3AF;">${escapeHtml(resolvedDate.substring(0,19))}</span></div>` : ''}
                    ${ticket.satisfaction_score ? `<div><span style="color:#6B7280;display:block;font-size:0.72rem;margin-bottom:2px;">SATISFACTION</span><span style="color:#facc15;font-weight:700;">★ ${escapeHtml(String(ticket.satisfaction_score))} / 5.0</span></div>` : ''}
                </div>

                <!-- Description -->
                <div style="margin-bottom:20px;">
                    <div style="font-size:0.72rem;color:#6B7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:7px;">ISSUE DESCRIPTION</div>
                    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:13px;color:#E5E7EB;line-height:1.6;font-size:0.91rem;white-space:pre-wrap;">${escapeHtml(ticket.description || 'No description provided.')}</div>
                </div>

                ${ticket.resolution_notes ? `
                <div style="margin-bottom:20px;">
                    <div style="font-size:0.72rem;color:#10b981;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:7px;"><i class="bi bi-check-circle me-1"></i>RESOLUTION NOTES</div>
                    <div style="background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.22);border-radius:8px;padding:12px 16px;color:#A7F3D0;font-size:0.9rem;line-height:1.5;white-space:pre-wrap;">${escapeHtml(ticket.resolution_notes)}</div>
                </div>` : ''}

                ${ticket.satisfaction_score ? `
                <div style="margin-bottom:20px;background:rgba(234,179,8,0.07);border:1px solid rgba(234,179,8,0.22);border-radius:8px;padding:12px 16px;">
                    <div style="font-size:0.72rem;color:#facc15;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;"><i class="bi bi-star-fill me-1"></i>CUSTOMER FEEDBACK (CSAT)</div>
                    <div style="color:#facc15;font-size:1.05rem;font-weight:700;margin-bottom:4px;">★ ${escapeHtml(String(ticket.satisfaction_score))} / 5.0</div>
                    ${ticket.customer_feedback ? `<div style="color:#E2E8F0;font-size:0.88rem;font-style:italic;">&ldquo;${escapeHtml(ticket.customer_feedback)}&rdquo;</div>` : ''}
                </div>` : ''}

                <!-- AI Similar Recommendations -->
                <div style="margin-bottom:20px;">
                    <div style="font-size:0.72rem;color:#3B82F6;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;display:flex;align-items:center;gap:6px;"><i class="bi bi-robot"></i>AI SIMILAR RECOMMENDATIONS</div>
                    ${similarHtml}
                </div>

                <!-- Conversation History -->
                <div style="margin-bottom:20px;">
                    <div style="font-size:0.72rem;color:#6B7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;"><i class="bi bi-chat-left-text me-1"></i>CONVERSATION HISTORY (${replies.length})</div>
                    <div style="background:#0E0F12;border-radius:8px;padding:12px;max-height:240px;overflow-y:auto;border:1px solid rgba(255,255,255,0.06);">
                        ${repliesHtml}
                    </div>
                </div>

                <!-- Agent Reply & Status Update Form -->
                <div>
                    <div style="font-size:0.72rem;color:#6B7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px;"><i class="bi bi-send me-1"></i>SEND RESPONSE &amp; UPDATE STATUS</div>
                    <form method="POST" action="/agent/tickets/${encodeURIComponent(tktNo)}/reply">
                        <div style="margin-bottom:10px;">
                            <label style="font-size:0.82rem;font-weight:500;color:#D5D5D5;display:block;margin-bottom:4px;">Message to Customer</label>
                            <textarea name="message" class="form-control" rows="3" placeholder="Compose message to customer..." style="width:100%;background:#1C1D21;color:white;border:1px solid rgba(255,255,255,0.12);border-radius:6px;padding:8px;font-family:inherit;font-size:0.9rem;"></textarea>
                        </div>
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;">
                            <div>
                                <label style="font-size:0.82rem;font-weight:500;color:#D5D5D5;display:block;margin-bottom:4px;">Update Status</label>
                                <select name="status" class="form-select" style="width:100%;height:38px;background:#1C1D21;color:white;border:1px solid rgba(255,255,255,0.12);border-radius:6px;padding:0 8px;">
                                    <option value="" selected>Keep Current (${escapeHtml(st)})</option>
                                    <option value="Under Review">Under Review</option>
                                    <option value="In Progress">In Progress</option>
                                    <option value="Resolved">Resolved</option>
                                    <option value="Closed">Closed</option>
                                </select>
                            </div>
                            <div>
                                <label style="font-size:0.82rem;font-weight:500;color:#D5D5D5;display:block;margin-bottom:4px;">Resolution Notes</label>
                                <input type="text" name="resolution_notes" class="form-control" placeholder="Brief fix explanation..." value="${escapeHtml(ticket.resolution_notes || '')}" style="width:100%;height:38px;background:#1C1D21;color:white;border:1px solid rgba(255,255,255,0.12);border-radius:6px;padding:0 8px;">
                            </div>
                        </div>
                        <div style="display:flex;justify-content:flex-end;gap:10px;">
                            <button type="button" class="btn btn-secondary btn-sm" onclick="closeModal('#agentTicketDetailsModal')">Close</button>
                            <button type="submit" class="btn btn-primary btn-sm" style="padding:8px 18px;font-weight:600;"><i class="bi bi-send me-1"></i>Submit &amp; Update</button>
                        </div>
                    </form>
                </div>

            </div>
        </div>
    `;

    modal.addEventListener('click', function(e) {
        if (e.target === modal) closeModal(modal);
    }, { once: true });

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

/* ==========================================================================
   8. UNIFIED TICKET DETAILS HANDLER (All Dashboards)
   ========================================================================== */

function initAgentViewDetailsButtons() {
    // Attach event listeners to all View Details buttons using event delegation
    document.body.addEventListener('click', function(e) {
        const button = e.target.closest('.btn-view-details');
        if (button) {
            e.preventDefault();
            const ticketno = button.getAttribute('data-ticketno');
            if (ticketno) {
                console.log('View Details clicked for ticket:', ticketno);
                loadUnifiedTicketDetails(ticketno);
            } else {
                console.error('No ticketno found on button');
                showCustomAlert('Error', 'Ticket ID not found on button', 'danger');
            }
        }
    });
}

function loadUnifiedTicketDetails(ticketno) {
    const modalBackdrop = document.getElementById('agentTicketDetailsModal');
    if (!modalBackdrop) {
        console.error('Modal container not found');
        showCustomAlert('Error', 'Modal container not found', 'danger');
        return;
    }

    // Show loading state
    modalBackdrop.innerHTML = `
        <div class="custom-modal-overlay" style="display: flex; align-items: center; justify-content: center; min-height: 400px;">
            <div style="text-align: center; color: #9CA3AF;">
                <i class="bi bi-hourglass-split" style="font-size: 3rem; margin-bottom: 1rem; display: block;"></i>
                <p style="font-size: 1.1rem;">Loading ticket details...</p>
            </div>
        </div>
    `;
    modalBackdrop.style.display = 'flex';

    // Fetch ticket details from unified API endpoint
    const apiUrl = `/api/ticket/${encodeURIComponent(ticketno)}`;

    fetch(apiUrl, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success && data.status === 'success') {
            renderDetailsModal(data);
        } else {
            throw new Error(data.message || 'Failed to load ticket details');
        }
    })
    .catch(err => {
        console.error('Error loading ticket details:', err);
        modalBackdrop.innerHTML = `
            <div class="custom-modal-overlay" style="display: flex; align-items: center; justify-content: center; min-height: 400px;">
                <div style="text-align: center; color: #EF4444; max-width: 400px; padding: 20px;">
                    <i class="bi bi-exclamation-triangle" style="font-size: 3rem; margin-bottom: 1rem; display: block;"></i>
                    <p style="font-size: 1.1rem; margin-bottom: 1rem;">Failed to load ticket details</p>
                    <p style="font-size: 0.9rem; color: #9CA3AF; margin-bottom: 1.5rem;">${escapeHtml(err.message)}</p>
                    <button type="button" class="btn btn-secondary" onclick="closeTicketDetailsModal()">
                        Close
                    </button>
                </div>
            </div>
        `;
    });
}

function closeTicketDetailsModal() {
    const modalBackdrop = document.getElementById('agentTicketDetailsModal');
    if (modalBackdrop) {
        modalBackdrop.style.display = 'none';
        modalBackdrop.innerHTML = '';
    }
}
