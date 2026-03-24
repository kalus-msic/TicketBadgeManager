'use strict';

// WebUSBBackend — handles device pairing, USB transfer, and print-confirm POST.
// Always loaded on scanner/kiosk pages.
// Depends on PrintManager (loaded first).
(function () {

    // Cache bulk OUT endpoint number per device serial number (session only)
    const _endpointCache = {};

    // --- localStorage helpers ---

    function _storageKey(queue) {
        return `webusb_device_q${queue}`;
    }

    function getPairedInfo(queue) {
        try {
            const raw = localStorage.getItem(_storageKey(queue));
            return raw ? JSON.parse(raw) : null;
        } catch { return null; }
    }

    function _savePairedInfo(queue, device) {
        localStorage.setItem(_storageKey(queue), JSON.stringify({
            name: device.productName,
            serialNumber: device.serialNumber,
        }));
    }

    function clearPairedInfo(queue) {
        localStorage.removeItem(_storageKey(queue));
    }

    // --- Device matching ---

    async function _findDevice(queue) {
        const info = getPairedInfo(queue);
        if (!info) return null;
        const devices = await navigator.usb.getDevices();
        return devices.find(d =>
            (info.serialNumber && d.serialNumber === info.serialNumber) ||
            d.productName === info.name
        ) || null;
    }

    // --- Bulk OUT endpoint detection (interface 0, configuration 1) ---

    function _getBulkOutEndpoint(device) {
        const key = device.serialNumber || device.productName;
        if (_endpointCache[key] !== undefined) return _endpointCache[key];

        let found = null;
        try {
            const ifaces = device.configuration.interfaces;
            for (const iface of ifaces) {
                for (const alt of iface.alternates) {
                    for (const ep of alt.endpoints) {
                        if (ep.direction === 'out' && ep.type === 'bulk') {
                            found = ep.endpointNumber;
                            break;
                        }
                    }
                    if (found !== null) break;
                }
                if (found !== null) break;
            }
        } catch (e) {
            console.warn('WebUSB: failed to iterate endpoints', e);
        }

        if (found === null) {
            console.warn('WebUSB: no bulk OUT endpoint found on interface 0');
        }
        _endpointCache[key] = found;
        return found;
    }

    // --- Pairing (must be called from user gesture) ---

    async function pairDevice(queue) {
        const device = await navigator.usb.requestDevice({
            filters: [{ vendorId: 0x1203 }]  // TSC printers only
        });
        _savePairedInfo(queue, device);
        console.log(`WebUSB: paired ${device.productName} (S/N: ${device.serialNumber}) for queue ${queue}`);
        return device;
    }

    // --- Init: check pairing state for status bar ---

    async function initStatusCheck(queue) {
        const info = getPairedInfo(queue);
        if (!info) return { state: 'unpaired', printerName: '' };

        const device = await _findDevice(queue);
        if (!device) return { state: 'unpaired', printerName: info.name };

        // Try open to verify it's still connected
        try {
            await device.open();
            await device.close();
            return { state: 'ready', printerName: device.productName };
        } catch (e) {
            if (e.name === 'NotFoundError') {
                return { state: 'disconnected', printerName: info.name };
            }
            // open may fail if device is already open — treat as ready
            return { state: 'ready', printerName: info.name };
        }
    }

    // --- Base64 → Uint8Array ---

    function _base64ToBytes(base64) {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return bytes;
    }

    // --- print_confirm POST ---

    async function _postPrintConfirm(eventPk, ticketId, queue, success, error) {
        if (!ticketId || !eventPk) return;
        const csrfMatch = document.cookie.match(/csrftoken=([^;]+)/);
        const csrftoken = csrfMatch ? csrfMatch[1] : '';
        try {
            await fetch(`/events/${eventPk}/print-confirm/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ticket_id: ticketId,
                    printer_queue: queue,
                    success: success,
                    ...(error ? { error: error } : {}),
                }),
            });
        } catch (e) {
            console.warn('WebUSB: print-confirm POST failed', e);
        }
    }

    // --- Main print function ---

    async function print(base64Data, printerName, queue, ticketId, eventPk) {
        const bytes = _base64ToBytes(base64Data);
        const info = getPairedInfo(queue);

        // No pairing info — show unpaired state
        if (!info) {
            window.PrintManager.setStatus('unpaired', printerName);
            return;
        }

        const device = await _findDevice(queue);
        if (!device) {
            window.PrintManager.setStatus('unpaired', info.name || printerName);
            return;
        }

        try {
            await device.open();

            // usbprint.sys conflict: SecurityError on open (rare) or NetworkError on claimInterface
            try {
                await device.selectConfiguration(1);
                await device.claimInterface(0);
            } catch (claimErr) {
                if (claimErr.name === 'NetworkError' || claimErr.name === 'SecurityError') {
                    window.PrintManager.setStatus('driver_conflict', device.productName);
                    try { await device.close(); } catch {}
                    return;
                }
                throw claimErr;
            }

            const endpointNumber = _getBulkOutEndpoint(device);
            if (endpointNumber === null) {
                console.error('WebUSB: cannot print — no bulk OUT endpoint');
                try { await device.close(); } catch {}
                return;
            }

            await device.transferOut(endpointNumber, bytes);
            await device.close();

            window.PrintManager.setStatus('ready', device.productName);
            window.PrintManager.savePending(null);  // clear pending on success
            await _postPrintConfirm(eventPk, ticketId, queue, true, null);

        } catch (e) {
            try { await device.close(); } catch {}

            if (e.name === 'NotFoundError') {
                // Device was unplugged mid-session — preserve localStorage entry
                window.PrintManager.setStatus('disconnected', info.name || printerName);
            } else {
                window.PrintManager.setStatus('error', info.name || printerName, e.message);
                await _postPrintConfirm(eventPk, ticketId, queue, false, e.message);
            }
        }
    }

    // Expose public API
    window.WebUSBBackend = {
        print,
        pairDevice,
        initStatusCheck,
        getPairedInfo,
        clearPairedInfo,
    };
}());
