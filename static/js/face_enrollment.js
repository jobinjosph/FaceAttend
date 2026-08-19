document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("#face-enrolment-form");
    if (!form) return;
    const video = document.querySelector("#face-camera");
    const canvas = document.querySelector("#face-canvas");
    const start = document.querySelector("#start-camera");
    const capture = document.querySelector("#capture-face");
    const clear = document.querySelector("#clear-faces");
    const save = document.querySelector("#save-face");
    const input = document.querySelector("#samples_json");
    const preview = document.querySelector("#face-sample-preview");
    const message = document.querySelector("#camera-message");
    const required = Number(form.dataset.requiredSamples || 3);
    let stream = null;
    let samples = [];

    const stopCamera = () => {
        if (stream) stream.getTracks().forEach((track) => track.stop());
        stream = null;
    };
    const render = () => {
        input.value = JSON.stringify(samples);
        preview.replaceChildren(...samples.map((source, index) => {
            const image = new Image(); image.src = source; image.alt = `Face sample ${index + 1}`; return image;
        }));
        capture.disabled = !stream || samples.length >= required;
        clear.disabled = samples.length === 0;
        save.disabled = samples.length !== required;
        message.textContent = samples.length === required
            ? `${required} samples ready. Save the registration.`
            : `${samples.length} of ${required} samples captured.`;
    };
    start.addEventListener("click", async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({video: {facingMode: "user", width: {ideal: 640}, height: {ideal: 480}}, audio: false});
            video.srcObject = stream; start.disabled = true; capture.disabled = false;
            message.textContent = "Camera ready. Keep one face centred and hold still.";
        } catch (error) {
            message.textContent = "Camera access failed. Allow camera permission in the browser and try again.";
        }
    });
    capture.addEventListener("click", () => {
        if (!stream || video.videoWidth === 0) return;
        canvas.width = video.videoWidth; canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
        samples.push(canvas.toDataURL("image/jpeg", 0.82)); render();
    });
    clear.addEventListener("click", () => { samples = []; render(); });
    form.addEventListener("submit", (event) => {
        if (samples.length !== required) { event.preventDefault(); message.textContent = `Capture exactly ${required} samples first.`; }
        else stopCamera();
    });
    window.addEventListener("beforeunload", stopCamera); render();
});
