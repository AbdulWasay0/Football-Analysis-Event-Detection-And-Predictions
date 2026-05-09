# ============================================================================
# COMPLEXITY NOTES FOR TWO SPECIFIC FEATURES ONLY
# ============================================================================
#
# This file is NOT used by the application.
# It only contains commented code snippets and short explanations for:
#
# 1. Heat map generation
# 2. Event detection
#
# The real working code lives inside:
# - Part A: Part a Player Tracking And Mapping/.../main_test.py
# - Part C: Part c Event Detection/event_detector.py
#


# ============================================================================
# 1. HEAT MAP FEATURE
# ============================================================================
#
# Purpose:
# The heat map shows where players spent the most time on the pitch.
# It uses tracked player positions, converts them into pitch coordinates,
# then draws stronger color intensity where movement happens repeatedly.
#


# ----------------------------------------------------------------------------
# Step 1: Store tracked player pitch positions
# ----------------------------------------------------------------------------
#
# def record_tracking(frame_index, fps, transformer, detections, team_id,
#                     rows, last_positions, motion_stats):
#     if len(detections) == 0:
#         return
#
#     # Use bottom-center of each player bounding box because it represents
#     # the player's foot position on the ground.
#     points = detections.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
#
#     # Convert camera/image coordinates into top-down pitch coordinates.
#     pitch_points = transformer.transform_points(points=points)
#
#     for index, point in enumerate(pitch_points):
#         if not np.isfinite(point).all():
#             continue
#
#         tracker_id = int(detections.tracker_id[index])
#         key = f"{team_id}_{tracker_id}"
#
#         # Keep the position inside the pitch boundaries.
#         x = float(np.clip(point[0], 0, CONFIG.length))
#         y = float(np.clip(point[1], 0, CONFIG.width))
#
#         # Compare with the previous position of the same player to estimate
#         # distance and speed.
#         distance = 0.0
#         speed = 0.0
#         if key in last_positions:
#             previous = last_positions[key]
#             distance = float(np.linalg.norm(np.array([x, y]) - np.array(previous)))
#             speed = distance * float(fps or 0)
#
#         last_positions[key] = (x, y)
#
#         # These rows become the input for the heat map.
#         rows.append({
#             "frame": frame_index,
#             "team": team_id,
#             "tracker_id": tracker_id,
#             "pitch_x": round(x, 2),
#             "pitch_y": round(y, 2),
#             "distance_units": round(distance, 2),
#             "speed_units_per_second": round(speed, 2),
#         })
#


# ----------------------------------------------------------------------------
# Step 2: Convert pitch positions into a heat map image
# ----------------------------------------------------------------------------
#
# def write_heatmap(rows):
#     path = globals().get("OUT_HEATMAP")
#     if not path or not rows:
#         return
#
#     width, height = 900, 560
#
#     # Start with a blank heat layer.
#     heat = np.zeros((height, width), dtype=np.float32)
#
#     for row in rows:
#         # Convert pitch coordinates into image pixels.
#         x = int((float(row["pitch_x"]) / max(1, CONFIG.length)) * (width - 1))
#         y = int((float(row["pitch_y"]) / max(1, CONFIG.width)) * (height - 1))
#
#         # Draw a small heat point for every tracked player location.
#         cv2.circle(heat, (x, y), 18, 1, -1)
#
#     # Blur makes nearby player positions merge into smooth hotspots.
#     heat = cv2.GaussianBlur(heat, (0, 0), 18)
#
#     # Normalize so the strongest area becomes maximum intensity.
#     if heat.max() > 0:
#         heat = heat / heat.max()
#
#     # Convert grayscale intensity into colored heat.
#     colored = cv2.applyColorMap((heat * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
#
#     # Draw a simple pitch background.
#     pitch = np.zeros((height, width, 3), dtype=np.uint8)
#     pitch[:] = (44, 119, 72)
#     line = (235, 245, 238)
#     cv2.rectangle(pitch, (20, 20), (width - 20, height - 20), line, 2)
#     cv2.line(pitch, (width // 2, 20), (width // 2, height - 20), line, 2)
#     cv2.circle(pitch, (width // 2, height // 2), 65, line, 2)
#
#     # Blend heat colors with the pitch drawing.
#     overlay = cv2.addWeighted(pitch, 0.62, colored, 0.55, 0)
#     cv2.imwrite(path, overlay)
#


# ============================================================================
# 2. EVENT DETECTION FEATURE
# ============================================================================
#
# Purpose:
# Event detection samples frames from a match video, sends those frames to
# Roboflow YOLO-World, then converts returned labels into football events such
# as goals, cards, shots, passes, tackles, and possession changes.
#


# ----------------------------------------------------------------------------
# Step 1: Define event prompts for YOLO-World
# ----------------------------------------------------------------------------
#
# DEFAULT_EVENT_CLASSES = [
#     "soccer goal",
#     "ball in goal",
#     "goal celebration",
#     "player shooting at goal",
#     "yellow card",
#     "red card",
#     "referee card",
#     "shot",
#     "pass",
#     "sliding tackle",
#     "player tackling opponent",
#     "football tackle",
#     "possession change",
# ]
#
# Explanation:
# YOLO-World is prompt-based, so better football-specific text prompts improve
# the chance of detecting the real event instead of only detecting "person".
#


# ----------------------------------------------------------------------------
# Step 2: Sample frames from the uploaded video
# ----------------------------------------------------------------------------
#
# def sample_frames(upload_path, output_dir, config=None):
#     capture = cv2.VideoCapture(str(upload_path))
#     if not capture.isOpened():
#         raise RuntimeError("Could not read the uploaded video for event detection.")
#
#     total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
#     fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
#     width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
#     height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
#
#     # Dense sampling is important because events can happen quickly.
#     # In the project, 0.5 seconds is used for YOLO-World.
#     step_frames = max(1, int((fps or 25) * 0.5))
#     indices = list(range(0, total_frames, step_frames))[:600]
#
#     sampled = []
#     for index in indices:
#         capture.set(cv2.CAP_PROP_POS_FRAMES, index)
#         ok, frame = capture.read()
#         if not ok:
#             continue
#
#         frame_path = output_dir / f"{upload_path.stem}_event_frame_{index}.jpg"
#         cv2.imwrite(str(frame_path), frame)
#
#         sampled.append({
#             "path": frame_path,
#             "frame": index,
#             "time": round(index / fps, 2) if fps else "N/A",
#             "width": width,
#             "height": height,
#         })
#
#     capture.release()
#     return sampled
#


# ----------------------------------------------------------------------------
# Step 3: Send one sampled frame to Roboflow YOLO-World
# ----------------------------------------------------------------------------
#
# def call_yolo_world_api(image_path, api_key, config=None):
#     endpoint = "https://infer.roboflow.com/yolo_world/infer?api_key=API_KEY"
#
#     payload = {
#         "image": {
#             "type": "base64",
#             "value": base64.b64encode(Path(image_path).read_bytes()).decode("ascii"),
#         },
#         "text": DEFAULT_EVENT_CLASSES,
#
#         # A low threshold is used because zero-shot event detections often
#         # return lower confidence than normal object detection.
#         "confidence": 0.03,
#     }
#
#     response = requests.post(endpoint, json=payload, timeout=45)
#     return response.json()
#


# ----------------------------------------------------------------------------
# Step 4: Convert API labels into report event groups
# ----------------------------------------------------------------------------
#
# def _event_group(label):
#     label_key = label.lower().replace("_", " ").replace("-", " ")
#
#     if "goal" in label_key:
#         return "Goals"
#     if "yellow" in label_key:
#         return "Yellow Cards"
#     if "red" in label_key:
#         return "Red Cards"
#     if "card" in label_key:
#         return "Cards"
#     if "shot" in label_key:
#         return "Shots"
#     if "pass" in label_key:
#         return "Passes"
#     if "tackl" in label_key or "challenge" in label_key:
#         return "Tackles"
#     if "possession" in label_key:
#         return "Possession Changes"
#
#     return None
#
# Explanation:
# The API may return labels like "ball in goal" or "player tackling opponent".
# This function maps those raw labels into the fixed event names shown in the UI.
#


# ----------------------------------------------------------------------------
# Step 5: Build report rows from predictions
# ----------------------------------------------------------------------------
#
# for sample in sampled_frames:
#     data = call_yolo_world_api(sample["path"], api_key, config)
#     predictions = extract_predictions(data)
#
#     for prediction in predictions:
#         label = prediction.get("class", "unknown")
#         event = _event_group(label)
#         if event is None:
#             continue
#
#         confidence = float(prediction.get("confidence", 0) or 0)
#         if confidence * 100 < confidence_threshold:
#             continue
#
#         where = _where(prediction, sample["width"], sample["height"])
#
#         rows.append({
#             "frame": sample["frame"],
#             "time_sec": sample["time"],
#             "event": event,
#             "api_label": label,
#             "confidence": f"{confidence * 100:.1f}%",
#             "where": where,
#             "what_happened": (
#                 f"{event} detected at {sample['time']}s in the {where} "
#                 f"from API label '{label}'"
#             ),
#         })
#


# ----------------------------------------------------------------------------
# Step 6: Create clips for important events
# ----------------------------------------------------------------------------
#
# def create_event_clips(upload_path, rows, output_dir):
#     clips = []
#     last_time_by_bucket = {}
#
#     for row in rows:
#         event = row["event"]
#
#         # Only these events generate clips.
#         if event == "Goals":
#             bucket = "Goals"
#         elif event in {"Yellow Cards", "Red Cards", "Cards"}:
#             bucket = "Cards"
#         elif event == "Tackles":
#             bucket = "Tackles"
#         else:
#             continue
#
#         time_value = row["time_sec"]
#
#         # Avoid duplicate clips when the same event is detected in nearby
#         # sampled frames.
#         if abs(float(time_value) - last_time_by_bucket.get(bucket, -9999.0)) < 3.5:
#             continue
#
#         last_time_by_bucket[bucket] = float(time_value)
#         start = max(0.0, float(time_value) - 3)
#         duration = 7
#
#         # FFmpeg cuts a short MP4 around the event moment.
#         # ffmpeg -ss START -i input.mp4 -t DURATION output.mp4
#
#         clips.append({
#             "type": bucket,
#             "event_time_sec": round(float(time_value), 2),
#             "what_happened": row["what_happened"],
#         })
#
#     return clips
#
