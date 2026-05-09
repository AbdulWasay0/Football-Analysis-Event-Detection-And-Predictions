from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from pathlib import Path
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest


IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
EVENT_COUNTS = {
    "Goals": 0,
    "Yellow Cards": 0,
    "Red Cards": 0,
    "Cards": 0,
    "Shots": 0,
    "Passes": 0,
    "Tackles": 0,
    "Possession Changes": 0,
}
CLIP_EVENT_TYPES = {"Goals", "Yellow Cards", "Red Cards", "Cards", "Tackles"}
DEFAULT_WORKFLOW_TARGET = "weird-gamer/yolo-world-large-demo"
DEFAULT_EVENT_CLASSES = [
    "soccer goal",
    "ball in goal",
    "goal celebration",
    "player shooting at goal",
    "yellow card",
    "red card",
    "referee card",
    "shot",
    "pass",
    "sliding tackle",
    "player tackling opponent",
    "football tackle",
    "possession change",
]
LEGACY_EVENT_CLASSES = "goal,yellow card,red card,card,shot,pass,tackle,possession change"
CONFIG_FILE = Path(__file__).with_name("event_api_config.json")


def is_configured(config: dict[str, object] | None = None) -> bool:
    return bool(_api_key(config) and (_model_id(config) or _workflow_parts(config)[0]))


def config_status(config: dict[str, object] | None = None) -> dict[str, str | bool | int | float]:
    return {
        "configured": is_configured(config),
        "api_key": bool(_api_key(config)),
        "model_id": _model_id(config),
        "mode": _api_mode(config),
        "api_url": _api_url(config),
        "confidence": _confidence(config),
        "classes": ", ".join(_classes(config)),
        "sample_step_seconds": _sample_step_seconds(config),
        "max_frames": _max_frames(config),
    }


def _stored_config() -> dict[str, object]:
    try:
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def save_config(config: dict[str, object] | None = None) -> None:
    if not config:
        return
    stored = _stored_config()
    for key in (
        "api_key",
        "model_id",
        "workspace",
        "workflow_id",
        "api_url",
        "confidence",
        "classes",
        "sample_step_seconds",
        "max_frames",
    ):
        value = str(config.get(key, "")).strip()
        if value:
            stored[key] = value
    if stored:
        CONFIG_FILE.write_text(json.dumps(stored, indent=2), encoding="utf-8")


def _config_value(config: dict[str, object] | None, key: str, env_key: str, default: str = "") -> str:
    if config and str(config.get(key, "")).strip():
        return str(config[key]).strip()
    env_value = os.environ.get(env_key, "").strip()
    if env_value:
        return env_value
    stored_value = _stored_config().get(key, "")
    if str(stored_value).strip():
        return str(stored_value).strip()
    return default.strip()


def _api_key(config: dict[str, object] | None = None) -> str:
    if config and str(config.get("api_key", "")).strip():
        return str(config["api_key"]).strip()
    return (
        os.environ.get("EVENT_DETECTION_API_KEY", "").strip()
        or os.environ.get("ROBOFLOW_API_KEY", "").strip()
        or str(_stored_config().get("api_key", "")).strip()
    )


def _model_id(config: dict[str, object] | None = None) -> str:
    return _config_value(config, "model_id", "EVENT_DETECTION_MODEL_ID", DEFAULT_WORKFLOW_TARGET)


def _uses_yolo_world_direct(config: dict[str, object] | None = None) -> bool:
    return _model_id(config).strip().lower() == DEFAULT_WORKFLOW_TARGET


def _api_mode(config: dict[str, object] | None = None) -> str:
    if _uses_yolo_world_direct(config):
        return "YOLO-World Direct"
    return "Workflow" if _workflow_parts(config)[0] else "Hosted model"


def _workflow_parts(config: dict[str, object] | None = None) -> tuple[str, str]:
    workspace = _config_value(config, "workspace", "EVENT_DETECTION_WORKSPACE")
    workflow_id = _config_value(config, "workflow_id", "EVENT_DETECTION_WORKFLOW_ID")
    model_id = _model_id(config)
    if (not workspace or not workflow_id) and model_id.count("/") == 1:
        workspace, workflow_id = [part.strip() for part in model_id.split("/", 1)]
    return workspace, workflow_id


def _api_url(config: dict[str, object] | None = None) -> str:
    return _config_value(config, "api_url", "EVENT_DETECTION_API_URL", "https://serverless.roboflow.com").rstrip("/")


def _confidence(config: dict[str, object] | None = None) -> int:
    default = "3" if _uses_yolo_world_direct(config) else "25"
    value = _config_value(config, "confidence", "EVENT_DETECTION_CONFIDENCE", default)
    try:
        confidence = max(1, min(100, int(float(value))))
        if _uses_yolo_world_direct(config) and confidence == 25:
            return 3
        return confidence
    except ValueError:
        return int(default)


def _classes(config: dict[str, object] | None = None) -> list[str]:
    raw = _config_value(config, "classes", "EVENT_DETECTION_CLASSES", ",".join(DEFAULT_EVENT_CLASSES))
    if raw.replace(" ", "").lower() == LEGACY_EVENT_CLASSES.replace(" ", ""):
        raw = ",".join(DEFAULT_EVENT_CLASSES)
    classes = [
        item.strip()
        for item in raw.replace("\n", ",").replace(";", ",").split(",")
        if item.strip()
    ]
    return classes or DEFAULT_EVENT_CLASSES


def _sample_step_seconds(config: dict[str, object] | None = None) -> float:
    default = "0.5" if _uses_yolo_world_direct(config) else "2"
    value = _config_value(config, "sample_step_seconds", "EVENT_DETECTION_SAMPLE_STEP_SECONDS", default)
    try:
        seconds = max(0.25, min(20.0, float(value)))
        if _uses_yolo_world_direct(config) and seconds == 2.0:
            return 0.5
        return seconds
    except ValueError:
        return float(default)


def _max_frames(config: dict[str, object] | None = None) -> int:
    value = _config_value(config, "max_frames", "EVENT_DETECTION_MAX_FRAMES", "120")
    try:
        return max(1, min(600, int(value)))
    except ValueError:
        return 120


def _clip_seconds(config: dict[str, object] | None, key: str, env_key: str, default: str) -> float:
    value = _config_value(config, key, env_key, default)
    try:
        return max(0.5, min(30.0, float(value)))
    except ValueError:
        return float(default)


def _event_group(label: str) -> str | None:
    label_key = label.lower().replace("_", " ").replace("-", " ")
    if "goal" in label_key:
        return "Goals"
    if "yellow" in label_key:
        return "Yellow Cards"
    if "red" in label_key:
        return "Red Cards"
    if "card" in label_key:
        return "Cards"
    if "shot" in label_key:
        return "Shots"
    if "pass" in label_key:
        return "Passes"
    if "tackl" in label_key or "challenge" in label_key:
        return "Tackles"
    if "possession" in label_key:
        return "Possession Changes"
    return None


def _where(prediction: dict[str, object], width: int | None, height: int | None) -> str:
    if not width or not height:
        return "location unavailable"
    x = float(prediction.get("x", 0) or 0)
    y = float(prediction.get("y", 0) or 0)
    horizontal = "left" if x < width / 3 else "right" if x > width * 2 / 3 else "center"
    vertical = "top" if y < height / 3 else "bottom" if y > height * 2 / 3 else "middle"
    return f"{vertical}-{horizontal} area of the frame"


def _what_happened(event: str, label: str, confidence: float, where: str, time_value: object) -> str:
    time_text = f" at {time_value}s" if isinstance(time_value, (int, float)) else ""
    return f"{event} detected{time_text} in the {where} from API label '{label}' ({confidence * 100:.1f}% confidence)."


def _prediction_label(prediction: dict[str, object]) -> str:
    for key in ("class", "class_name", "label", "name"):
        value = str(prediction.get(key, "")).strip()
        if value:
            return value
    return "unknown"


def _looks_like_prediction(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    has_label = any(str(value.get(key, "")).strip() for key in ("class", "class_name", "label", "name"))
    has_box = any(key in value for key in ("x", "y", "width", "height", "bbox", "bounding_box"))
    return has_label and ("confidence" in value or "score" in value or has_box)


def _normalise_prediction(prediction: dict[str, object]) -> dict[str, object]:
    normalised = dict(prediction)
    normalised["class"] = _prediction_label(prediction)
    if "confidence" not in normalised and "score" in normalised:
        normalised["confidence"] = normalised["score"]

    box = prediction.get("bbox") or prediction.get("bounding_box")
    if isinstance(box, dict):
        for key in ("x", "y", "width", "height"):
            if key not in normalised and key in box:
                normalised[key] = box[key]
    elif isinstance(box, (list, tuple)) and len(box) >= 4:
        x1, y1, x2, y2 = [float(value or 0) for value in box[:4]]
        normalised.setdefault("x", (x1 + x2) / 2)
        normalised.setdefault("y", (y1 + y2) / 2)
        normalised.setdefault("width", abs(x2 - x1))
        normalised.setdefault("height", abs(y2 - y1))
    return normalised


def extract_predictions(data: object) -> list[dict[str, object]]:
    if isinstance(data, list):
        if all(_looks_like_prediction(item) for item in data):
            return [_normalise_prediction(item) for item in data if isinstance(item, dict)]
        predictions: list[dict[str, object]] = []
        for item in data:
            predictions.extend(extract_predictions(item))
        return predictions

    if not isinstance(data, dict):
        return []

    direct = data.get("predictions")
    if isinstance(direct, list) and all(_looks_like_prediction(item) for item in direct):
        return [_normalise_prediction(item) for item in direct if isinstance(item, dict)]

    predictions = []
    for key, value in data.items():
        if key in {"visualization", "image", "output_image"}:
            continue
        predictions.extend(extract_predictions(value))
    return predictions


def _image_size(path: Path) -> tuple[int | None, int | None]:
    try:
        import cv2

        image = cv2.imread(str(path))
        if image is None:
            return None, None
        height, width = image.shape[:2]
        return int(width), int(height)
    except Exception:
        return None, None


def sample_frames(upload_path: Path, output_dir: Path, config: dict[str, object] | None = None) -> list[dict[str, object]]:
    suffix = upload_path.suffix.lower().lstrip(".")
    if suffix in IMAGE_EXTENSIONS:
        width, height = _image_size(upload_path)
        return [{"path": upload_path, "frame": "image", "time": "N/A", "width": width, "height": height}]

    try:
        import cv2
    except Exception as exc:
        raise RuntimeError("OpenCV is required to sample video frames before calling the event API.") from exc

    capture = cv2.VideoCapture(str(upload_path))
    if not capture.isOpened():
        raise RuntimeError("Could not read the uploaded video for event detection.")

    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0) or None
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0) or None
    if total_frames <= 0:
        indices = [0]
    else:
        step_frames = max(1, int((fps or 25) * _sample_step_seconds(config)))
        indices = list(range(0, total_frames, step_frames))[:_max_frames(config)]
        if total_frames - 1 not in indices and len(indices) < _max_frames(config):
            indices.append(total_frames - 1)

    sampled: list[dict[str, object]] = []
    for index in indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = capture.read()
        if not ok:
            continue
        frame_path = output_dir / f"{upload_path.stem}_event_frame_{index}.jpg"
        cv2.imwrite(str(frame_path), frame)
        sampled.append({
            "path": frame_path,
            "frame": index,
            "time": round(index / fps, 2) if fps else "N/A",
            "width": width,
            "height": height,
        })

    capture.release()
    if not sampled:
        raise RuntimeError("Could not extract any frames from the uploaded video.")
    return sampled


def _request_json(endpoint: str, payload: bytes | dict[str, object], content_type: str) -> dict[str, object] | list[object]:
    headers = {
        "Content-Type": content_type,
        "User-Agent": "inference-sdk-python-compatible/1.0",
    }
    if isinstance(payload, dict):
        try:
            import requests

            response = requests.post(endpoint, json=payload, headers=headers, timeout=45)
            response.raise_for_status()
            return response.json()
        except ImportError:
            data = json.dumps(payload).encode("utf-8")
        except requests.HTTPError as exc:
            raise urlerror.HTTPError(
                endpoint,
                response.status_code,
                response.text,
                response.headers,
                None,
            ) from exc
        except requests.RequestException as exc:
            raise urlerror.URLError(str(exc)) from exc
    else:
        data = payload

    request_obj = urlrequest.Request(
        endpoint,
        data=data,
        headers=headers,
        method="POST",
    )
    with urlrequest.urlopen(request_obj, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def _workflow_endpoints(config: dict[str, object] | None, workspace: str, workflow_id: str) -> list[str]:
    api_url = _api_url(config)
    quoted_workspace = urlparse.quote(workspace, safe="")
    quoted_workflow = urlparse.quote(workflow_id, safe="")
    endpoints = [f"{api_url}/{quoted_workspace}/workflows/{quoted_workflow}"]
    endpoints.append(f"{api_url}/infer/workflows/{quoted_workspace}/{quoted_workflow}")
    if "serverless.roboflow.com" in api_url:
        endpoints.append(f"https://detect.roboflow.com/infer/workflows/{quoted_workspace}/{quoted_workflow}")
    return list(dict.fromkeys(endpoints))


def _call_workflow_api(image_path: Path, config: dict[str, object] | None = None) -> dict[str, object] | list[object]:
    api_key = _api_key(config)
    workspace, workflow_id = _workflow_parts(config)
    if not api_key or not workspace or not workflow_id:
        raise RuntimeError(
            "Event Detection is API-only. Enter a Roboflow API key and workflow target "
            "like weird-gamer/yolo-world-large-demo, or save them once on this page."
        )

    try:
        from inference_sdk import InferenceHTTPClient

        client = InferenceHTTPClient(api_url=_api_url(config), api_key=api_key)
        return client.run_workflow(
            workspace_name=workspace,
            workflow_id=workflow_id,
            images={"image": str(image_path)},
            parameters={"classes": _classes(config)},
        )
    except ImportError:
        pass
    except Exception:
        # Fall through to the HTTP route below so self-hosted and older SDK
        # environments still get a useful direct API attempt.
        pass

    payload = {
        "api_key": api_key,
        "use_cache": True,
        "enable_profiling": False,
        "inputs": {
            "image": {
                "type": "base64",
                "value": base64.b64encode(image_path.read_bytes()).decode("ascii"),
            },
            "classes": _classes(config),
        },
    }
    errors: list[str] = []
    for endpoint in _workflow_endpoints(config, workspace, workflow_id):
        try:
            return _request_json(endpoint, payload, "application/json")
        except urlerror.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            errors.append(f"{endpoint}: {exc.code} {detail}")
        except urlerror.URLError as exc:
            errors.append(f"{endpoint}: {exc.reason}")
    raise RuntimeError("Event Workflow API request failed. " + " | ".join(errors))


def _call_yolo_world_api(image_path: Path, config: dict[str, object] | None = None) -> dict[str, object]:
    api_key = _api_key(config)
    if not api_key:
        raise RuntimeError("Event Detection needs a Roboflow API key for YOLO-World.")

    endpoint = f"https://infer.roboflow.com/yolo_world/infer?{urlparse.urlencode({'api_key': api_key})}"
    payload = {
        "image": {
            "type": "base64",
            "value": base64.b64encode(image_path.read_bytes()).decode("ascii"),
        },
        "text": _classes(config),
        "confidence": _confidence(config) / 100,
    }
    data = _request_json(endpoint, payload, "application/json")
    if isinstance(data, dict):
        return data
    return {"predictions": []}


def _call_hosted_model_api(image_path: Path, config: dict[str, object] | None = None) -> dict[str, object]:
    api_key = _api_key(config)
    model_id = _model_id(config)
    if not api_key or not model_id:
        raise RuntimeError(
            "Event Detection is API-only. Enter a Roboflow API key and hosted model ID, "
            "or set/save EVENT_DETECTION_API_KEY/ROBOFLOW_API_KEY and EVENT_DETECTION_MODEL_ID."
        )

    params = urlparse.urlencode({"api_key": api_key, "confidence": _confidence(config)})
    endpoint = f"{_api_url(config)}/{model_id}?{params}"
    payload = base64.b64encode(image_path.read_bytes())
    data = _request_json(endpoint, payload, "application/x-www-form-urlencoded")
    if isinstance(data, dict):
        return data
    return {"predictions": []}


def call_roboflow_api(image_path: Path, config: dict[str, object] | None = None) -> dict[str, object] | list[object]:
    workspace, workflow_id = _workflow_parts(config)
    try:
        if _uses_yolo_world_direct(config):
            return _call_yolo_world_api(image_path, config)
        if workspace and workflow_id:
            return _call_workflow_api(image_path, config)
        return _call_hosted_model_api(image_path, config)
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Event API request failed: {exc.code} {detail}") from exc
    except urlerror.URLError as exc:
        raise RuntimeError(f"Event API request failed: {exc.reason}") from exc


def _ffmpeg_executable() -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _write_clip_with_cv2(source: Path, target: Path, start: float, duration: float) -> bool:
    try:
        import cv2

        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            return False
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 25)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        start_frame = max(0, int(start * fps))
        end_frame = max(start_frame + 1, int((start + duration) * fps))
        capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        writer = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        frame_index = start_frame
        while frame_index <= end_frame:
            ok, frame = capture.read()
            if not ok:
                break
            writer.write(frame)
            frame_index += 1
        capture.release()
        writer.release()
        return target.exists() and target.stat().st_size > 0
    except Exception:
        return False


def _write_clip(source: Path, target: Path, start: float, duration: float) -> bool:
    ffmpeg = _ffmpeg_executable()
    if ffmpeg:
        command = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{start:.2f}",
            "-i",
            str(source),
            "-t",
            f"{duration:.2f}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(target),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            if target.exists() and target.stat().st_size > 0:
                return True
        except Exception:
            pass
    return _write_clip_with_cv2(source, target, start, duration)


def _clip_bucket(event: str) -> str | None:
    if event == "Goals":
        return "Goals"
    if event in {"Yellow Cards", "Red Cards", "Cards"}:
        return "Cards"
    if event == "Tackles":
        return "Tackles"
    return None


def create_event_clips(
    upload_path: Path,
    rows: list[dict[str, object]],
    output_dir: Path,
    config: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    suffix = upload_path.suffix.lower().lstrip(".")
    if suffix not in VIDEO_EXTENSIONS:
        return []

    pre_seconds = _clip_seconds(config, "clip_pre_seconds", "EVENT_DETECTION_CLIP_PRE_SECONDS", "3")
    post_seconds = _clip_seconds(config, "clip_post_seconds", "EVENT_DETECTION_CLIP_POST_SECONDS", "4")
    duration = pre_seconds + post_seconds
    try:
        max_per_type = max(1, min(20, int(_config_value(config, "max_clips_per_type", "EVENT_DETECTION_MAX_CLIPS_PER_TYPE", "6"))))
    except ValueError:
        max_per_type = 6

    clips: list[dict[str, object]] = []
    counts_by_bucket = {"Goals": 0, "Cards": 0, "Tackles": 0}
    last_time_by_bucket: dict[str, float] = {}

    for row in rows:
        bucket = _clip_bucket(str(row.get("event", "")))
        if bucket is None or counts_by_bucket[bucket] >= max_per_type:
            continue
        time_value = row.get("time_sec")
        if not isinstance(time_value, (int, float)):
            continue
        if abs(float(time_value) - last_time_by_bucket.get(bucket, -9999.0)) < max(1.5, duration / 2):
            continue

        counts_by_bucket[bucket] += 1
        last_time_by_bucket[bucket] = float(time_value)
        start = max(0.0, float(time_value) - pre_seconds)
        safe_bucket = bucket.lower().replace(" ", "_")
        target = output_dir / f"{upload_path.stem}_{safe_bucket}_{counts_by_bucket[bucket]}.mp4"
        if not _write_clip(upload_path, target, start, duration):
            continue
        clips.append({
            "type": bucket,
            "title": f"{bucket} Clip {counts_by_bucket[bucket]}",
            "file": target.name,
            "start_sec": round(start, 2),
            "end_sec": round(start + duration, 2),
            "event_time_sec": round(float(time_value), 2),
            "event": row.get("event"),
            "where": row.get("where"),
            "what_happened": row.get("what_happened"),
        })

    return clips


def run_event_detection(
    upload_path: Path,
    frame_output_dir: Path,
    clip_output_dir: Path,
    config: dict[str, object] | None = None,
) -> dict[str, object]:
    sampled_frames = sample_frames(upload_path, frame_output_dir, config)
    rows: list[dict[str, object]] = []
    counts = dict(EVENT_COUNTS)

    for sample in sampled_frames:
        frame_path = sample["path"]
        assert isinstance(frame_path, Path)
        data = call_roboflow_api(frame_path, config)
        predictions = extract_predictions(data)
        for prediction in predictions:
            if not isinstance(prediction, dict):
                continue
            label = _prediction_label(prediction)
            event = _event_group(label)
            if event is None:
                continue
            confidence = float(prediction.get("confidence", 0) or 0)
            if confidence > 1:
                confidence = confidence / 100
            if confidence * 100 < _confidence(config):
                continue
            where = _where(prediction, sample.get("width"), sample.get("height"))
            counts[event] = counts.get(event, 0) + 1
            if event in {"Yellow Cards", "Red Cards"}:
                counts["Cards"] = counts.get("Cards", 0) + 1
            rows.append({
                "frame": sample["frame"],
                "time_sec": sample["time"],
                "event": event,
                "api_label": label,
                "confidence": f"{confidence * 100:.1f}%",
                "where": where,
                "what_happened": _what_happened(event, label, confidence, where, sample["time"]),
                "x": round(float(prediction.get("x", 0) or 0), 1),
                "y": round(float(prediction.get("y", 0) or 0), 1),
                "width": round(float(prediction.get("width", 0) or 0), 1),
                "height": round(float(prediction.get("height", 0) or 0), 1),
            })

    rows.sort(key=lambda row: row["time_sec"] if isinstance(row.get("time_sec"), (int, float)) else 0)
    clips = create_event_clips(upload_path, rows, clip_output_dir, config)

    return {
        "kind": "events",
        "title": "Event Detection Report",
        "summary": {
            "Input File": upload_path.name,
            "Frames Sent To API": len(sampled_frames),
            "Events Detected": len(rows),
            "Clips Created": len(clips),
            "Configured Target": _model_id(config),
            "API Mode": _api_mode(config),
        },
        "counts": counts,
        "rows": rows,
        "clips": clips,
        "sample_frames": [Path(sample["path"]).name for sample in sampled_frames],
    }
