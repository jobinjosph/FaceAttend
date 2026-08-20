document.addEventListener("DOMContentLoaded", () => {
    const app = document.querySelector("#face-attendance-app");
    if (!app) return;
    const video = document.querySelector("#attendance-camera");
    const canvas = document.querySelector("#attendance-canvas");
    const toggle = document.querySelector("#toggle-attendance-camera");
    const message = document.querySelector("#attendance-camera-message");
    const result = document.querySelector("#recognition-result");
    const csrf = document.querySelector("#face-attendance-csrf").value;
    let stream = null;
    let running = false;
    let processing = false;
    let scanTimer = null;

    const showResult = (title, detail, state) => {
        result.className = `recognition-result ${state || ""}`;
        result.replaceChildren();
        const strong = document.createElement("strong");
        const span = document.createElement("span");
        strong.textContent = title;
        span.textContent = detail;
        result.append(strong, span);
    };

    const scheduleScan = (delay = 1800) => {
        window.clearTimeout(scanTimer);
        if (running) scanTimer = window.setTimeout(scan, delay);
    };

    const stopCamera = () => {
        running = false;
        processing = false;
        window.clearTimeout(scanTimer);
        if (stream) stream.getTracks().forEach((track) => track.stop());
        stream = null;
        video.srcObject = null;
        toggle.textContent = "Start attendance camera";
        toggle.classList.add("primary");
        message.textContent = "Camera stopped by the lecturer.";
    };

    const scan = async () => {
        if (!running || processing) return;
        if (video.videoWidth === 0) {
            scheduleScan(500);
            return;
        }
        processing = true;
        message.textContent = "Scanning automatically — keep one face centred.";
        showResult("Checking face…", "Please hold still.", "pending");
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
        const form = new FormData();
        form.append("csrf_token", csrf);
        form.append("sample", canvas.toDataURL("image/jpeg", 0.88));
        let nextDelay = 1800;
        try {
            const response = await fetch(app.dataset.recognitionUrl, {
                method: "POST",
                body: form,
                headers: {"Accept": "application/json"},
            });
            const data = await response.json();
            if (data.result === "matched") {
                showResult("Attendance marked ✓", `${data.student.full_name} · ${data.student.register_number}. Next student may approach.`, "success");
                message.textContent = "Attendance recorded. Please move away for the next student.";
                nextDelay = 3500;
            } else if (data.result === "duplicate") {
                showResult("Attendance already marked", `${data.student.full_name} · ${data.student.register_number}. Please allow the next student.`, "warning");
                nextDelay = 2500;
            } else if (data.result === "unknown") {
                showResult("Face not recognized", "Try again in better lighting or ask the lecturer to mark attendance manually.", "error");
            } else if (data.result === "ambiguous") {
                showResult("Match unclear", "More than one registration is too similar. Ask the lecturer for help.", "error");
                nextDelay = 2500;
            } else if (data.result === "no_registered") {
                showResult("No registered students", "Register student faces before using automatic attendance.", "error");
                stopCamera();
                return;
            } else if (data.result === "locked") {
                showResult("Session is no longer active", "Return to the attendance roster.", "error");
                stopCamera();
                return;
            } else {
                showResult("Face not ready", data.message || "Keep one clear face inside the guide.", "error");
            }
        } catch (error) {
            showResult("Recognition failed", "The server could not process this frame. Retrying automatically.", "error");
            nextDelay = 3000;
        } finally {
            processing = false;
            scheduleScan(nextDelay);
        }
    };

    toggle.addEventListener("click", async () => {
        if (running) {
            stopCamera();
            showResult("Camera stopped", "Attendance scanning has ended on this device.", "");
            return;
        }
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: {facingMode: "user", width: {ideal: 640}, height: {ideal: 480}},
                audio: false,
            });
            video.srcObject = stream;
            await video.play();
            running = true;
            toggle.textContent = "Stop attendance camera";
            toggle.classList.remove("primary");
            message.textContent = "Camera active. Students may approach one by one.";
            showResult("Continuous attendance started", "Waiting for the first student…", "pending");
            scheduleScan(800);
        } catch (error) {
            message.textContent = "Camera access failed. Allow camera permission and try again.";
            showResult("Camera unavailable", "The lecturer must allow browser camera access.", "error");
        }
    });

    window.addEventListener("beforeunload", stopCamera);
});
