document.addEventListener("DOMContentLoaded", () => {
    const app = document.querySelector("#face-attendance-app");
    if (!app) return;
    const video = document.querySelector("#attendance-camera");
    const canvas = document.querySelector("#attendance-canvas");
    const toggle = document.querySelector("#toggle-attendance-camera");
    const message = document.querySelector("#attendance-camera-message");
    const result = document.querySelector("#recognition-result");
    const modeButtons = document.querySelectorAll("[data-attendance-mode]");
    const modeHelp = document.querySelector("#attendance-mode-help");
    const csrf = document.querySelector("#face-attendance-csrf").value;
    let stream = null;
    let running = false;
    let processing = false;
    let scanTimer = null;
    let attendanceMode = "ENTRY";

    const modeLabel = () => attendanceMode === "ENTRY" ? "Entry Mode" : "Exit Mode";

    const formatDuration = (seconds) => {
        const safeSeconds = Math.max(0, Number(seconds) || 0);
        const minutes = Math.floor(safeSeconds / 60);
        const remainder = safeSeconds % 60;
        return `${minutes}m ${remainder}s`;
    };

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
        form.append("mode", attendanceMode);
        let nextDelay = 1800;
        try {
            const response = await fetch(app.dataset.recognitionUrl, {
                method: "POST",
                body: form,
                headers: {"Accept": "application/json"},
            });
            const data = await response.json();
            if (data.result === "entry_recorded") {
                const status = data.status === "LATE" ? " · Marked late" : "";
                showResult("Entry recorded ✓", `${data.student.full_name} · ${data.student.register_number}${status}. Next student may approach.`, "success");
                message.textContent = "Entry recorded. Please move away for the next student.";
                nextDelay = 3500;
            } else if (data.result === "exit_recorded") {
                showResult("Exit recorded ✓", `${data.student.full_name} · ${data.student.register_number} · Present for ${formatDuration(data.duration_seconds)}.`, "success");
                message.textContent = "Exit recorded. Please move away for the next student.";
                nextDelay = 3500;
            } else if (data.result === "duplicate_entry") {
                showResult("Entry already recorded", `${data.student.full_name} · ${data.student.register_number}. Please allow the next student.`, "warning");
                nextDelay = 2500;
            } else if (data.result === "duplicate_exit") {
                showResult("Exit already recorded", `${data.student.full_name} · ${data.student.register_number} · Recorded duration ${formatDuration(data.duration_seconds)}.`, "warning");
                nextDelay = 2500;
            } else if (data.result === "entry_required") {
                showResult("No entry found", `${data.student.full_name} must record an entry before recording an exit.`, "warning");
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

    modeButtons.forEach((button) => {
        button.addEventListener("click", () => {
            attendanceMode = button.dataset.attendanceMode;
            modeButtons.forEach((item) => item.classList.toggle("active", item === button));
            modeHelp.textContent = attendanceMode === "ENTRY"
                ? "Entry Mode records each recognized student's arrival time."
                : "Exit Mode records departure time and calculates presence duration.";
            message.textContent = running
                ? `${modeLabel()} active. Students may approach one by one.`
                : `${modeLabel()} selected. Start the camera when ready.`;
            showResult(modeLabel(), attendanceMode === "ENTRY"
                ? "Waiting to record student arrivals."
                : "Waiting to record student departures.", "pending");
        });
    });

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
            message.textContent = `${modeLabel()} active. Students may approach one by one.`;
            showResult(`${modeLabel()} started`, "Waiting for the first student…", "pending");
            scheduleScan(800);
        } catch (error) {
            message.textContent = "Camera access failed. Allow camera permission and try again.";
            showResult("Camera unavailable", "The lecturer must allow browser camera access.", "error");
        }
    });

    window.addEventListener("beforeunload", stopCamera);
});
