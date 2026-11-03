# Notification Worker

**Module:** `services/notification-worker`  
**Purpose:** Dispatches verified advisories to farmer notification channels (Telegram Bot, PWA push).  
**Scheduled Stage:** Stage 19  

## Responsibilities
- Consumes from Kafka topic `agent-actions`.
- Deduplicates alerts via alert-ID keying to prevent repeated farmer notifications on stream replay.
- Formats messages in English and Kannada.
- Delivers action cards with interactive Approve and Reject buttons.
- Forwards farmer decisions to Kafka topic `feedback`.
