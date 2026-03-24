'use strict';

// PrintManager — router and status bar controller.
// Always loaded on scanner/kiosk pages.
// Reads data-print-backend from #webusb-page-root to decide which backend to use.
(function () {

    // --- Status bar ---

    function getStatusBar() {
        return document.getElementById('webusb-status-bar');
    }

    function setStatus(state, printerName, detail) {
        const bar = getStatusBar();
        if (!bar) return;

        const icons = {
            ready:          '🖨️',
            unpaired:       '⚠️',
            disconnected:   '⚠️',
            error:          '❌',
            driver_conflict:'❌',
        };
        const messages = {
            ready:          `${icons.ready} ${printerName} ✅`,
            unpaired:       `${icons.unpaired} Tiskárna není párována`,
            disconnected:   `${icons.disconnected} Tiskárna ${printerName} — odpojená`,
            error:          `${icons.error} Tisk selhal: ${detail || ''}`,
            driver_conflict:`${icons.driver_conflict} Tiskárna blokována Windows ovladačem`,
        };
        const actions = {
            unpaired:        `<button class="btn btn-sm btn-warning ms-2" onclick="PrintManager.showPairButton()">Spárovat</button>`,
            disconnected:    `<button class="btn btn-sm btn-outline-secondary ms-2" onclick="PrintManager.retryPrint()">Zkusit znovu</button>`,
            error:           `<button class="btn btn-sm btn-outline-secondary ms-2" onclick="PrintManager.retryPrint()">Zkusit znovu</button>`,
            driver_conflict: `<a href="#webusb-zadig-section" class="btn btn-sm btn-outline-secondary ms-2">Zadig návod</a>`,
        };

        const msg = messages[state] || state;
        const action = actions[state] || '';
        bar.innerHTML = `<span>${msg}</span>${action}
            <button class="btn btn-sm btn-link ms-auto p-0" onclick="PrintManager.toggleGearPanel()" title="Nastavení tiskárny">⚙️</button>`;
    }

    // --- Gear panel (inline, non-blocking) ---

    let _gearOpen = false;
    function toggleGearPanel() {
        const panel = document.getElementById('webusb-gear-panel');
        if (!panel) return;
        _gearOpen = !_gearOpen;
        panel.style.display = _gearOpen ? '' : 'none';
    }

    function showPairButton() {
        const queue = _getQueue();
        window.WebUSBBackend.pairDevice(queue).then(device => {
            setStatus('ready', device.productName);
            if (_pending) retryPrint();
        }).catch(e => {
            console.warn('Pairing cancelled or failed:', e);
        });
    }

    // --- Pending print (saved for retry after pairing) ---

    let _pending = null;

    function savePending(payload) {
        _pending = payload;
    }

    function retryPrint() {
        if (!_pending) return;
        const { base64Data, printerName, queue, ticketId, eventPk, attempt } = _pending;
        const nextAttempt = (attempt || 0) + 1;
        if (nextAttempt > 3) {
            _pending = null;
            return;
        }
        _pending = { ..._pending, attempt: nextAttempt };
        window.WebUSBBackend.print(base64Data, printerName, queue, ticketId, eventPk);
    }

    // --- Page attributes ---

    function _getQueue() {
        const el = document.getElementById('printer_queue');
        return el ? el.value : '1';
    }

    function _getBackend() {
        const root = document.getElementById('webusb-page-root');
        return root ? root.dataset.printBackend : '';
    }

    function _getEventPk() {
        const root = document.getElementById('webusb-page-root');
        return root ? root.dataset.eventPk : '';
    }

    // --- Response handler (called from verifyTicket) ---

    async function handle(data) {
        if (!data || data.print_backend !== 'webusb') return;
        const base64Data = data.print_data;
        const printerName = data.print_printer;
        const queue = _getQueue();
        const ticketId = data.ticket ? data.ticket.id : null;
        const eventPk = _getEventPk();

        savePending({ base64Data, printerName, queue, ticketId, eventPk, attempt: 0 });
        await window.WebUSBBackend.print(base64Data, printerName, queue, ticketId, eventPk);
    }

    // --- Init on page load ---

    document.addEventListener('DOMContentLoaded', function () {
        const backend = _getBackend();
        const bar = getStatusBar();
        if (bar) {
            bar.style.display = backend === 'webusb' ? '' : 'none';
        }
        const gearPanel = document.getElementById('webusb-gear-panel');
        if (gearPanel) {
            gearPanel.style.display = 'none';
        }
        if (backend === 'webusb') {
            window.WebUSBBackend.initStatusCheck(_getQueue()).then(({ state, printerName }) => {
                setStatus(state, printerName);
            });
        }
    });

    // Expose public API
    window.PrintManager = {
        handle,
        setStatus,
        savePending,
        retryPrint,
        toggleGearPanel,
        showPairButton,
    };
}());
