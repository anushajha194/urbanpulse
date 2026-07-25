# UrbanPulse Repair Verification Service

FastAPI service exposing `POST /api/v1/verify` to validate municipal repair completion before closing civic complaints.

## Verification Lifecycle

The service performs three automated validation steps:
1. **EXIF Metadata Extraction**: Extracts capture GPS and DateTime timestamps from the uploaded "after" image.
2. **GPS Geodesic Distance Check**: Computes distance (via Haversine formula) between the original complaint coordinates and the EXIF coordinates. Raises `GPSMismatchError` if distance exceeds **50 meters**.
3. **Timestamp Sequence Check**: Compares the EXIF photo timestamp against the original complaint created date. Raises `TimestampInvalidError` if the photo was captured before the complaint was submitted.
4. **Visual Structural Check (SSIM Proxy)**: Computes a structural similarity index proxy using pixel-level image correlation.
   * If similarity exceeds `0.98`, raises `NoVisibleChangeError` (indicating the worker uploaded the same photo - fraud detection).
   * If similarity drops below `0.10`, raises `NoVisibleChangeError` (indicating the photo represents an entirely different street context).

## Lifecycle Status Mapping

* **Passed Checks**: Updates parent complaint status to `verified` and sets the closure timestamp (`closed_at = NOW()`). Logs details to `repair_verifications` with `verified=TRUE`.
* **Failed Checks**: Logs details to `repair_verifications` with `verified=FALSE` along with the validation error. Reverts the parent complaint status to `under_review` (flagged for review).

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/urbanpulse` | Postgres DB connection |
| `S3_ENDPOINT` | `http://localhost:9000` | S3 image storage endpoint |

## Running Tests

To run the tests:
```bash
pip install -r requirements.txt
pytest tests/ -v
```
The test suite generates in-memory JPEG buffers with custom EXIF rational metadata to test geolocation and time offsets locally without external dependencies.
