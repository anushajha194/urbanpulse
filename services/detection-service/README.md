# UrbanPulse Detection Service

A Python background worker that consumes complaint metadata and image paths from a Redis queue, downloads the images from S3-compatible storage, runs two CV detectors (a multi-class YOLOv8 model for objects and a segmentation model for area-based issues), and updates the database with results.

## Model Mapping

The system supports two model families to cover all 11 issue classes:

### YOLOv8 Detector (Object Detection)
* `pothole`
* `streetlight`
* `manhole`
* `dead_animal`
* `tree`
* `damaged_public_property`

### Segmentation Detector (Semantic Segmentation)
* `waterlogging`
* `mud_road`
* `erosion`
* `footpath_damage`
* `encroachment`

## Pipeline Flow

1. Reads jobs from Redis list `detection_jobs` (blocking pop via BRPOP).
2. Downloads original image from S3 storage.
3. Runs detectors (YOLOv8 + Segmentation).
4. Picks the detection with the highest confidence score.
5. If confidence is below the threshold (default: `0.4`), sets the complaint's status to `under_review` (routing it to the human verification queue). If confidence is high, sets status to `assigned`.
6. Updates the database `complaints` table row with the detected class, confidence score, and status.
7. Publishes a job to `scoring_jobs` to compute severity.
8. Publishes a job to `dedup_jobs` to execute duplicate checks.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MODEL_MODE` | `stub` | `model` for actual ML inference, `stub` for dummy deterministic classifier |
| `YOLO_MODEL_PATH` | `models/yolov8n-civic.pt` | Path to YOLO model weights |
| `SEG_MODEL_PATH` | `models/seg-civic.pt` | Path to Segmentation model weights |
| `CONFIDENCE_THRESHOLD` | `0.4` | Low confidence complaints go to human review |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/urbanpulse` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis queue endpoint |
| `S3_ENDPOINT` | `http://localhost:9000` | S3-compatible object storage endpoint |

## Running Tests

To run the automated tests:
```bash
pip install -r requirements.txt
pytest tests/ -v
```
