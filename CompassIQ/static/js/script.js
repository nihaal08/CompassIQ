/**
 * CompassIQ - AI Powered Ticket Management System
 * Phase 1 Client-Side Script
 */

document.addEventListener('DOMContentLoaded', () => {
    // Dynamically update the current year in the footer
    const yearSpan = document.getElementById('current-year');
    if (yearSpan) {
        yearSpan.textContent = new Date().getFullYear();
    }

    console.log('CompassIQ System Initialized - Phase 1 (Database & Flask Setup)');
});
