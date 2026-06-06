document.addEventListener('DOMContentLoaded', () => {
    // --- Employee Upload Logic ---
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('reportFile');
            const statusMsg = document.getElementById('uploadStatus');
            const submitBtn = uploadForm.querySelector('button[type="submit"]');

            if (fileInput.files.length === 0) {
                alert("Please select a file.");
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            // Show loading state
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner"></span> Uploading...';
            statusMsg.innerHTML = '<div class="alert alert-info" style="margin-bottom:0">Processing & Uploading to Blockchain...</div>';

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();

                if (result.success) {
                    statusMsg.innerHTML = `
                        <div class="alert alert-success" style="margin-bottom:0">
                            <strong>✓ Success!</strong> Report securely hashed & stored.<br>
                            <span style="font-size:0.85em">Tx: ${result.hash}</span>
                        </div>
                    `;
                    setTimeout(() => location.reload(), 2500);
                } else {
                    statusMsg.innerHTML = `<div class="alert alert-danger" style="margin-bottom:0">${result.error || 'Upload failed'}</div>`;
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                }
            } catch (err) {
                statusMsg.innerHTML = '<div class="alert alert-danger" style="margin-bottom:0">Network Error. Please try again.</div>';
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
                console.error(err);
            }
        });
    }

    // --- Admin Verify Logic ---
    const verifyButtons = document.querySelectorAll('.verify-btn');
    verifyButtons.forEach(btn => {
        btn.addEventListener('click', async () => {
            const hash = btn.getAttribute('data-hash');
            const rowId = btn.getAttribute('data-id');
            const statusCell = document.getElementById(`status-${rowId}`);

            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Checking...';

            try {
                const response = await fetch('/verify_report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ hash: hash })
                });
                const result = await response.json();

                // statusCell.innerText = result.status; // Set inside logic blocks for precision

                // Update Badge Class
                statusCell.className = "status-badge"; // Reset
                if (result.status === "Verified (On-Chain)") {
                    statusCell.innerText = "Verified (On-Chain)";
                    statusCell.classList.add("status-verified");
                } else if (result.status === "Tampered / Mismatch") {
                    statusCell.innerText = "Tampered / Mismatch";
                    statusCell.classList.add("status-tampered");
                } else if (result.status === "QUARANTINED") {
                    statusCell.innerText = "QUARANTINED";
                    statusCell.classList.add("status-tampered");
                    // Reload to update buttons (Download -> Blocked)
                    setTimeout(() => location.reload(), 1000);
                } else if (result.status === "error" && result.message && result.message.includes("DECRYPTION_FAILED")) {
                    statusCell.innerText = "Decryption Failed (Check Key)";
                    statusCell.classList.add("status-warning");
                } else if (result.status === "Not Found on Chain") {
                    statusCell.innerText = "Not Found on Chain";
                    statusCell.classList.add("status-pending");
                } else {
                    statusCell.innerText = result.status || "Unknown Error";
                    statusCell.classList.add("status-error");
                }

                btn.innerHTML = '<span style="color:white">✓ Done</span>';

                // Re-enable after short delay
                setTimeout(() => {
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                }, 2000);

            } catch (err) {
                console.error(err);
                btn.innerHTML = 'Error';
                btn.disabled = false;
            }
        });
    });





    // --- Dual Attack Simulation Logic ---

    // 1. Local Attack Function
    document.addEventListener("click", async function (e) {
        if (e.target.classList.contains("local-attack-btn")) {
            if (!confirm("⚠️ WARNING: This will corrupt the LOCAL file storage.\n\nThis simulates a server breach where an attacker modifies files on disk.\nProceed?")) return;

            const hash = e.target.dataset.hash;
            const originalText = e.target.innerHTML;
            e.target.innerHTML = "Corrupting...";
            e.target.disabled = true;

            try {
                const res = await fetch("/simulate_local_attack", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ hash: hash })
                });
                const data = await res.json();

                if (data.success) {
                    alert("⚔️ LOCAL FILE COMPROMISED! \nNow run 'Verify Integrity' to see the hash mismatch.");
                    location.reload();
                } else {
                    alert("Error: " + data.error);
                }
            } catch (err) {
                alert("Network Error");
            } finally {
                e.target.innerHTML = originalText;
                e.target.disabled = false;
            }
        }
    });

    // 2. CID Attack Function
    document.addEventListener("click", async function (e) {
        if (e.target.classList.contains("cid-attack-btn")) {
            if (!confirm("⚠️ WARNING: This will tamper with the IPFS CID reference.\n\nThis simulates a database manipulation where the file pointer is changed to a malicious location.\nProceed?")) return;

            const hash = e.target.dataset.hash;
            const originalText = e.target.innerHTML;
            e.target.innerHTML = "Tampering...";
            e.target.disabled = true;

            try {
                const res = await fetch("/simulate_cid_attack", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ hash: hash })
                });
                const data = await res.json();

                if (data.success) {
                    alert("🌐 CID REFERENCE TAMPERED! \nNow run 'Verify Integrity' to see the fetch failure/mismatch.");
                    location.reload();
                } else {
                    alert("Error: " + data.error);
                }
            } catch (err) {
                alert("Network Error");
            } finally {
                e.target.innerHTML = originalText;
                e.target.disabled = false;
            }
        }
    });

    // 3. Smart Content Attack Function
    document.addEventListener("click", async function (e) {
        if (e.target.classList.contains("smart-attack-btn")) {
            if (!confirm("⚠️ WARNING: This will tamper with the ACTUAL PDF TEXT content.\n\nThis simulates an attacker decrypting, modifying text, and re-encrypting the file cleanly.\nProceed?")) return;

            const hash = e.target.dataset.hash;
            const originalText = e.target.innerHTML;
            e.target.innerHTML = "Tampering Text...";
            e.target.disabled = true;

            try {
                const res = await fetch("/simulate_content_tamper", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ hash: hash })
                });
                const data = await res.json();

                if (data.success) {
                    alert("📝 TEXT TAMPERED SUCCESSFULLY! \nNow run 'Verify Integrity' to trigger the Document-Level Tamper Localization Engine.");
                    location.reload();
                } else {
                    alert("Error: " + data.error);
                }
            } catch (err) {
                alert("Network Error");
            } finally {
                e.target.innerHTML = originalText;
                e.target.disabled = false;
            }
        }
    });

    // --- Admin Unblock Logic ---
    document.addEventListener("click", async function (e) {
        if (e.target.classList.contains("unblock-btn")) {
            const hash = e.target.dataset.hash;
            const originalText = e.target.innerHTML;

            e.target.disabled = true;
            e.target.innerHTML = "Unblocking...";

            try {
                const res = await fetch("/admin_unblock", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ hash: hash })
                });

                const data = await res.json();

                if (data.success) {
                    alert("File Unblocked Successfully");
                    location.reload();
                } else {
                    alert("Error unblocking file: " + (data.error || "Unknown Error"));
                    e.target.disabled = false;
                    e.target.innerHTML = originalText;
                }
            } catch (err) {
                console.error("Unblock Error:", err);
                alert("Network Error during unblock.");
                e.target.disabled = false;
                e.target.innerHTML = originalText;
            }
        }
    });

});

