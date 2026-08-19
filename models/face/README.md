# Face recognition models

FaceAttend uses these local OpenCV models:

- `face_detection_yunet_2023mar.onnx` for face detection and landmarks.
- `face_recognition_sface_2021dec.onnx` for 128-dimensional face embeddings.

The model files come from the official OpenCV model repositories. Their
licenses are included as `LICENSE-YUNET` and `LICENSE-SFACE`.

The application never downloads a model at runtime and does not send captured
images to an external face-recognition service.
