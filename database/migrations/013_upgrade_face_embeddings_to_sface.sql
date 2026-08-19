-- Keep legacy descriptors for recovery, but only current SFace registrations
-- should appear ready for recognition.
UPDATE students AS s
SET s.face_registered = EXISTS (
    SELECT 1
    FROM face_embeddings AS fe
    WHERE fe.student_id = s.id
      AND fe.model_name = 'opencv-yunet-sface-v1'
);
