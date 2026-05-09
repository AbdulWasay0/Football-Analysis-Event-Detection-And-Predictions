# Part C Event Detection

This module is API-only. It does not train or load a local event detection model.

It samples frames from an uploaded match video and sends those frames to a hosted Roboflow model. The default target is `weird-gamer/yolo-world-large-demo`; in code this is routed through Roboflow's direct YOLO-World endpoint so football class prompts such as `player tackling opponent` and `ball in goal` are honored.

The Flask page accepts API settings and saves non-empty values to `event_api_config.json` beside this file so you do not need to re-enter them every run. Environment variables still override the saved values.

## Outputs

- General report for goals, yellow cards, red cards, shots, passes, tackles, and possession changes.
- PDF, CSV, and JSON report exports.
- Downloadable clips only for goals, cards, and tackles when those labels are detected in the video.
- Each report row includes time, event type, approximate frame area, API label, confidence, and a short "what happened" sentence.

## API Configuration

- `EVENT_DETECTION_API_KEY` or `ROBOFLOW_API_KEY`
- `EVENT_DETECTION_MODEL_ID`, for example `weird-gamer/yolo-world-large-demo` for a Workflow or `workspace/project/version` for a hosted model

Workflow-specific alternatives:

- `EVENT_DETECTION_WORKSPACE`, for example `weird-gamer`
- `EVENT_DETECTION_WORKFLOW_ID`, for example `yolo-world-large-demo`

Optional:

- `EVENT_DETECTION_API_URL`, defaults to `https://serverless.roboflow.com`
- `EVENT_DETECTION_CLASSES`, defaults to goal, cards, shots, passes, tackles, and possession change labels
- `EVENT_DETECTION_SAMPLE_STEP_SECONDS`, defaults to `2`
- `EVENT_DETECTION_MAX_FRAMES`, defaults to `120`
- `EVENT_DETECTION_CONFIDENCE`, defaults to `3` for YOLO-World and `25` for classic hosted models
- `EVENT_DETECTION_CLIP_PRE_SECONDS`, defaults to `3`
- `EVENT_DETECTION_CLIP_POST_SECONDS`, defaults to `4`
- `EVENT_DETECTION_MAX_CLIPS_PER_TYPE`, defaults to `6`

If API credentials are not provided on the page, in `event_api_config.json`, or by environment variables, Part C will not run inference.
