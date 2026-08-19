document.addEventListener("DOMContentLoaded", () => {
    const app = document.querySelector("#face-attendance-app");
    if (!app) return;
    const video = document.querySelector("#attendance-camera");
    const canvas = document.querySelector("#attendance-canvas");
    const start = document.querySelector("#start-attendance-camera");
    const recognize = document.querySelector("#recognize-student");
    const message = document.querySelector("#attendance-camera-message");
    const result = document.querySelector("#recognition-result");
    const csrf = document.querySelector("#face-attendance-csrf").value;
    let stream = null;

    const showResult = (title, detail, state) => {
        result.className = `recognition-result ${state || ""}`;
        result.replaceChildren();
        const strong = document.createElement("strong");
        const span = document.createElement("span");
        strong.textContent = title; span.textContent = detail;
        result.append(strong, span);
    };
    const stopCamera = () => {
        if (stream) stream.getTracks().forEach((track) => track.stop());
        stream = null;
    };
    start.addEventListener("click", async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({video: {facingMode: "user", width: {ideal: 640}, height: {ideal: 480}}, audio: false});
            video.srcObject = stream; start.disabled = true; recognize.disabled = false;
            message.textContent = "Camera ready. Keep one face centred and hold still.";
        } catch (error) {
            message.textContent = "Camera access failed. Allow camera permission and try again.";
        }
    });
    recognize.addEventListener("click", async () => {
        if (!stream || video.videoWidth === 0) return;
        recognize.disabled = true;
        showResult("Checking face…", "Please hold still.", "pending");
        canvas.width = video.videoWidth; canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
        const form = new FormData();
        form.append("csrf_token", csrf);
        form.append("sample", canvas.toDataURL("image/jpeg", 0.88));
        try {
            const response = await fetch(app.dataset.recognitionUrl, {method: "POST", body: form, headers: {"Accept": "application/json"}});
            const data = await response.json();
            if (data.result === "matched") showResult("Attendance marked", `${data.student.full_name} · ${data.student.register_number}`, "success");
            else if (data.result === "duplicate") showResult("Already marked", `${data.student.full_name} already has an entry for this session.`, "warning");
            else if (data.result === "unknown") showResult("Face not recognized", "Register this student or try again in better lighting.", "error");
            else if (data.result === "ambiguous") showResult("Match unclear", "More than one registration is too similar. Mark manually.", "error");
            else if (data.result === "no_registered") showResult("No registered students", "Register faces for students in this semester first.", "error");
            else if (data.result === "locked") showResult("Session is not active", "Return to the roster and check the session status.", "error");
            else showResult("Could not recognize face", data.message || "Check the face and try again.", "error");
        } catch (error) {
            showResult("Recognition failed", "The server could not process this request.", "error");
        } finally {
            recognize.disabled = false;
        }
    });
    window.addEventListener("beforeunload", stopCamera);
});
