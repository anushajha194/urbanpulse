# UrbanPulse Notification Service

A background worker service that consumes job payloads from `notification_jobs` queue, renders SMS and WhatsApp alerts utilizing dynamic, file-based text templates, and dispatches updates.

## Notification Events

The service handles three types of events:
1. **`assigned`**: Sent when a complaint gets assigned to a department. Alerts the citizen and the assigned team contact.
2. **`escalated`**: Sent when a complaint breaches its SLA deadline. Dispatches SMS + WhatsApp alerts directly to the department supervisor.
3. **`closed`**: Sent when a complaint repair has been verified and marked closed. Notifies the citizen.

## Template Files

All notifications use text template files located under `app/templates/` folder:
* `assigned.txt`
* `escalated.txt`
* `closed.txt`

These templates are read from disk, cached, and rendered dynamically injecting payload variables.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis queue connection string |
| `INPUT_QUEUE` | `notification_jobs` | Queue to consume notification jobs from |
| `TEMPLATES_DIR` | `app/templates` | Path to text templates folder |
| `TWILIO_ACCOUNT_SID` | `""` | Twilio Account SID (If blank, runs in STUB mode printing alerts to stdout) |
| `TWILIO_AUTH_TOKEN` | `""` | Twilio Authentication Token |
| `TWILIO_FROM_NUMBER` | `+12345678901` | Number of sender |

## Running Tests

To run the tests:
```bash
pip install -r requirements.txt
pytest tests/ -v
```
All tests use a mocked SMS/WhatsApp provider and locally resolved template files; no active Twilio account or external queues are required to execute.
