from itertools import chain
import base64
import csv
import os

import supervision as sv
import cv2
from tqdm import tqdm
import numpy as np

from config import *
from sports.annotators.soccer import draw_pitch, draw_points_on_pitch
from sports.common.view import ViewTransformer
from sports.configs.soccer import SoccerPitchConfiguration
from team_assigner import Assigner
from utils import get_number_of_frames, annotate_frames, get_frames


CONFIG = SoccerPitchConfiguration()
TEAM1_RADAR_COLOR = sv.Color.from_hex("#00BFFF")
TEAM2_RADAR_COLOR = sv.Color.from_hex("#FF1493")
REFEREE_RADAR_COLOR = sv.Color.from_hex("#FFD700")
BALL_RADAR_COLOR = sv.Color.WHITE


try:
    import requests
except ImportError:
    requests = None


CLASS_NAME_TO_PROJECT_ID = {
    "ball": MODEL_CLASSES["ball"],
    "goalkeeper": MODEL_CLASSES["goalkepper"],
    "goal keeper": MODEL_CLASSES["goalkepper"],
    "goalkepper": MODEL_CLASSES["goalkepper"],
    "keeper": MODEL_CLASSES["goalkepper"],
    "player": MODEL_CLASSES["player"],
    "person": MODEL_CLASSES["player"],
    "referee": MODEL_CLASSES["referee"],
    "official": MODEL_CLASSES["referee"],
    "sports ball": MODEL_CLASSES["ball"],
    "soccer ball": MODEL_CLASSES["ball"],
}


def empty_detections():
    return sv.Detections(
        xyxy=np.empty((0, 4), dtype=np.float32),
        confidence=np.empty((0,), dtype=np.float32),
        class_id=np.empty((0,), dtype=np.int32),
    )


class RoboflowHttpClient:
    def __init__(self):
        if requests is None:
            raise RuntimeError("The requests package is required for Roboflow HTTP detection.")
        if not ROBOFLOW_API_KEY:
            raise RuntimeError("ROBOFLOW_API_KEY is required for Roboflow HTTP detection.")

        self.session = requests.Session()

    def infer(self, frame, model_id):
        ok, encoded = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), ROBOFLOW_JPEG_QUALITY],
        )
        if not ok:
            raise RuntimeError("Could not encode frame for Roboflow HTTP detection.")

        image_b64 = base64.b64encode(encoded).decode("ascii")
        response = self.session.post(
            f"{ROBOFLOW_API_URL.rstrip('/')}/{model_id}",
            params={"api_key": ROBOFLOW_API_KEY},
            data=image_b64,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=ROBOFLOW_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()


class RoboflowHttpObjectDetector:
    def __init__(self):
        self.client = RoboflowHttpClient()
        print(f"Using Roboflow HTTP detector: {PLAYER_DETECTION_MODEL_ID}")

    def _to_detections(self, data):
        xyxy = []
        confidences = []
        class_ids = []

        for prediction in data.get("predictions", []):
            confidence = float(prediction.get("confidence", 0))
            if confidence < PLAYER_DETECTION_CONFIDENCE:
                continue

            class_name = str(prediction.get("class", "")).strip().lower().replace("-", " ")
            project_class_id = CLASS_NAME_TO_PROJECT_ID.get(class_name)
            if project_class_id is None:
                raw_class_id = prediction.get("class_id")
                if raw_class_id in MODEL_CLASSES.values():
                    project_class_id = int(raw_class_id)
                else:
                    continue

            x = float(prediction["x"])
            y = float(prediction["y"])
            width = float(prediction["width"])
            height = float(prediction["height"])

            xyxy.append([
                x - width / 2,
                y - height / 2,
                x + width / 2,
                y + height / 2,
            ])
            confidences.append(confidence)
            class_ids.append(project_class_id)

        if not xyxy:
            return empty_detections()

        return sv.Detections(
            xyxy=np.array(xyxy, dtype=np.float32),
            confidence=np.array(confidences, dtype=np.float32),
            class_id=np.array(class_ids, dtype=np.int32),
        )

    def predict(self, frame):
        return self._to_detections(self.client.infer(frame, PLAYER_DETECTION_MODEL_ID))


def create_object_detector():
    if DETECTION_BACKEND not in {"auto", "roboflow", "roboflow_http", "http"}:
        raise RuntimeError(
            "Part A now uses the Roboflow HTTP backend only. "
            "Set FOOTBALL_DETECTION_BACKEND=roboflow or leave it as auto."
        )

    return RoboflowHttpObjectDetector()


class PitchProjector:
    def __init__(self, frame_width, frame_height, field_client=None):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.field_client = field_client
        self.fallback_transformer = self._build_transformer()
        self.last_transformer = None
        self.frame_index = -1
        self._warning_printed = False

        if self.field_client is None:
            print("Using approximate pitch projection.")
        else:
            print(f"Using Roboflow HTTP field keypoints every {FIELD_REFRESH_FRAMES} frame(s).")

    def _build_transformer(self):
        w = self.frame_width
        h = self.frame_height
        source = np.array(
            [
                [w * 0.06, h * 0.98],
                [w * 0.18, h * 0.22],
                [w * 0.82, h * 0.22],
                [w * 0.94, h * 0.98],
            ],
            dtype=np.float32,
        )
        target = np.array(
            [
                [0, CONFIG.width],
                [0, 0],
                [CONFIG.length, 0],
                [CONFIG.length, CONFIG.width],
            ],
            dtype=np.float32,
        )
        return ViewTransformer(source=source, target=target)

    def _build_field_transformer(self, data):
        predictions = data.get("predictions", [])
        if not predictions:
            return None

        keypoints = predictions[0].get("keypoints", [])
        pitch_vertices = np.array(CONFIG.vertices, dtype=np.float32)
        frame_points = np.full((len(pitch_vertices), 2), np.nan, dtype=np.float32)
        confidences = np.zeros((len(pitch_vertices),), dtype=np.float32)

        for keypoint in keypoints:
            class_id = int(keypoint.get("class_id", -1))
            if class_id < 0 or class_id >= len(pitch_vertices):
                continue
            frame_points[class_id] = [
                float(keypoint.get("x", 0)),
                float(keypoint.get("y", 0)),
            ]
            confidences[class_id] = float(keypoint.get("confidence", 0))

        visible = confidences > FIELD_KEYPOINT_CONFIDENCE
        visible &= np.isfinite(frame_points).all(axis=1)

        if np.count_nonzero(visible) < 4:
            return None

        return ViewTransformer(
            source=frame_points[visible],
            target=pitch_vertices[visible],
        )

    def get_transformer(self, frame):
        self.frame_index += 1

        if self.field_client is None:
            return self.fallback_transformer

        if self.last_transformer is not None and self.frame_index % FIELD_REFRESH_FRAMES != 0:
            return self.last_transformer

        try:
            data = self.field_client.infer(frame, FIELD_DETECTION_MODEL_ID)
            transformer = self._build_field_transformer(data)
            if transformer is not None:
                self.last_transformer = transformer
                return transformer
        except Exception as exc:
            if not self._warning_printed:
                print(f"Field keypoint HTTP detection failed; using last/approximate projection. ({exc})")
                self._warning_printed = True

        return self.last_transformer or self.fallback_transformer

    def transform_detections(self, frame, detections):
        if len(detections) == 0:
            return np.empty((0, 2), dtype=np.float32)

        points = detections.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
        return self.get_transformer(frame).transform_points(points=points)


def empty_like(detections):
    return detections[np.zeros(len(detections), dtype=bool)]


def labels_for(detections, default=""):
    tracker_ids = getattr(detections, "tracker_id", None)
    if tracker_ids is None:
        return [default] * len(detections)
    return [str(int(tracker_id)) for tracker_id in tracker_ids]


def pitch_scale_for_frame(frame_width):
    max_pitch_width = max(100, frame_width - 20)
    return min(PITCH_SCALE, max_pitch_width / (CONFIG.length + 2 * PITCH_PADDING))


def fit_to_panel(image, panel_width, panel_height):
    image_height, image_width = image.shape[:2]
    scale = min(panel_width / image_width, panel_height / image_height)
    resized_width = max(1, int(image_width * scale))
    resized_height = max(1, int(image_height * scale))
    resized = cv2.resize(image, (resized_width, resized_height))

    panel = np.zeros((panel_height, panel_width, 3), dtype=np.uint8)
    x_offset = (panel_width - resized_width) // 2
    y_offset = (panel_height - resized_height) // 2
    panel[y_offset:y_offset + resized_height, x_offset:x_offset + resized_width] = resized
    return panel


class BallPossessionTracker:
    def __init__(self):
        self.last_team = None
        self.last_ball_center = None
        self.frames_without_owner = 0

    def _select_ball(self, ball_detections):
        if len(ball_detections) <= 1:
            return ball_detections

        centers = ball_detections.get_anchors_coordinates(sv.Position.CENTER)
        confidences = ball_detections.confidence
        if confidences is None:
            confidences = np.ones((len(ball_detections),), dtype=np.float32)

        if self.last_ball_center is None:
            index = int(np.argmax(confidences))
        else:
            distances = np.linalg.norm(centers - self.last_ball_center, axis=1)
            score = confidences - (distances / 1200)
            index = int(np.argmax(score))

        return ball_detections[index:index + 1]

    def _assign_to_player(self, players_detections, ball_detections):
        if len(ball_detections) == 0 or len(players_detections) == 0:
            return -1

        ball_center = ball_detections.get_anchors_coordinates(sv.Position.CENTER)[0]
        self.last_ball_center = ball_center
        best_index = -1
        best_distance = float("inf")

        for index, player_bbox in enumerate(players_detections.xyxy):
            x1, y1, x2, y2 = player_bbox
            width = max(1.0, x2 - x1)
            height = max(1.0, y2 - y1)
            foot_y = y2
            center_x = (x1 + x2) / 2
            candidate_points = np.array(
                [
                    [center_x, foot_y],
                    [x1, foot_y],
                    [x2, foot_y],
                    [center_x, y2 - height * 0.18],
                ],
                dtype=np.float32,
            )
            distance = float(np.min(np.linalg.norm(candidate_points - ball_center, axis=1)))
            dynamic_limit = max(55.0, min(BALL_ASSIGNMENT_MAX_DISTANCE, height * 0.9, width * 3.2))

            if distance < dynamic_limit and distance < best_distance:
                best_distance = distance
                best_index = index

        return best_index

    def update(self, players_detections, ball_detections):
        ball_detections = self._select_ball(ball_detections)
        player_index = self._assign_to_player(players_detections, ball_detections)

        if player_index != -1:
            team_id = int(players_detections.class_id[player_index])
            if team_id in {MODEL_CLASSES["team1"], MODEL_CLASSES["team2"]}:
                self.last_team = team_id
                self.frames_without_owner = 0
                return player_index, team_id, ball_detections

        if self.last_team is not None and self.frames_without_owner < BALL_POSSESSION_CARRY_FRAMES:
            self.frames_without_owner += 1
            return -1, self.last_team, ball_detections

        self.frames_without_owner += 1
        return -1, None, ball_detections


def build_pitch_radar_frame(frame, projector, team1_detections, team2_detections,
                            referee_detections, ball_detections, frame_width,
                            transformer=None):
    scale = pitch_scale_for_frame(frame_width)
    pitch = draw_pitch(
        config=CONFIG,
        padding=PITCH_PADDING,
        scale=scale,
        line_thickness=4,
        point_radius=7,
    )

    transformer = transformer or projector.get_transformer(frame)

    def transform(detections):
        if len(detections) == 0:
            return np.empty((0, 2), dtype=np.float32)
        points = detections.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
        return transformer.transform_points(points=points)

    pitch_ball_xy = transform(ball_detections)
    pitch_team1_xy = transform(team1_detections)
    pitch_team2_xy = transform(team2_detections)
    pitch_referee_xy = transform(referee_detections)

    pitch = draw_points_on_pitch(
        config=CONFIG,
        xy=pitch_ball_xy,
        face_color=BALL_RADAR_COLOR,
        edge_color=sv.Color.BLACK,
        radius=10,
        padding=PITCH_PADDING,
        scale=scale,
        pitch=pitch,
    )
    pitch = draw_points_on_pitch(
        config=CONFIG,
        xy=pitch_team1_xy,
        face_color=TEAM1_RADAR_COLOR,
        edge_color=sv.Color.BLACK,
        radius=16,
        padding=PITCH_PADDING,
        scale=scale,
        pitch=pitch,
    )
    pitch = draw_points_on_pitch(
        config=CONFIG,
        xy=pitch_team2_xy,
        face_color=TEAM2_RADAR_COLOR,
        edge_color=sv.Color.BLACK,
        radius=16,
        padding=PITCH_PADDING,
        scale=scale,
        pitch=pitch,
    )
    pitch = draw_points_on_pitch(
        config=CONFIG,
        xy=pitch_referee_xy,
        face_color=REFEREE_RADAR_COLOR,
        edge_color=sv.Color.BLACK,
        radius=16,
        padding=PITCH_PADDING,
        scale=scale,
        pitch=pitch,
    )

    return fit_to_panel(pitch, frame_width, PITCH_PANEL_HEIGHT)


def team_label(team_id):
    if team_id == MODEL_CLASSES["team1"]:
        return "Team 1"
    if team_id == MODEL_CLASSES["team2"]:
        return "Team 2"
    return "Referee"


def record_tracking(frame_index, fps, transformer, detections, team_id, rows, last_positions, motion_stats):
    if len(detections) == 0:
        return

    points = detections.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
    pitch_points = transformer.transform_points(points=points)
    tracker_ids = getattr(detections, "tracker_id", None)

    for index, point in enumerate(pitch_points):
        if not np.isfinite(point).all():
            continue
        tracker_id = int(tracker_ids[index]) if tracker_ids is not None else index
        key = f"{team_id}_{tracker_id}"
        x = float(np.clip(point[0], 0, CONFIG.length))
        y = float(np.clip(point[1], 0, CONFIG.width))
        distance = 0.0
        speed = 0.0
        stats = motion_stats.setdefault(key, {
            "team": team_label(team_id),
            "distance": 0.0,
            "max_speed": 0.0,
            "speed_sum": 0.0,
            "speed_count": 0,
        })
        if key in last_positions:
            previous = last_positions[key]
            distance = float(np.linalg.norm(np.array([x, y]) - np.array(previous)))
            speed = distance * float(fps or 0)
            stats["distance"] += distance
            stats["max_speed"] = max(stats["max_speed"], speed)
            stats["speed_sum"] += speed
            stats["speed_count"] += 1
        stats["team"] = team_label(team_id)
        last_positions[key] = (x, y)
        rows.append({
            "frame": frame_index,
            "team": team_label(team_id),
            "tracker_id": tracker_id,
            "pitch_x": round(x, 2),
            "pitch_y": round(y, 2),
            "distance_units": round(distance, 2),
            "speed_units_per_second": round(speed, 2),
        })


def write_tracking_csv(rows):
    path = globals().get("OUT_TRACKING_CSV")
    if not path:
        return
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "frame", "team", "tracker_id", "pitch_x", "pitch_y",
            "distance_units", "speed_units_per_second",
        ])
        writer.writeheader()
        writer.writerows(rows)


def write_heatmap(rows):
    path = globals().get("OUT_HEATMAP")
    if not path or not rows:
        return

    width, height = 900, 560
    heat = np.zeros((height, width), dtype=np.float32)
    for row in rows:
        x = int((float(row["pitch_x"]) / max(1, CONFIG.length)) * (width - 1))
        y = int((float(row["pitch_y"]) / max(1, CONFIG.width)) * (height - 1))
        cv2.circle(heat, (x, y), 18, 1, -1)

    heat = cv2.GaussianBlur(heat, (0, 0), 18)
    if heat.max() > 0:
        heat = heat / heat.max()
    colored = cv2.applyColorMap((heat * 255).astype(np.uint8), cv2.COLORMAP_TURBO)

    pitch = np.zeros((height, width, 3), dtype=np.uint8)
    pitch[:] = (44, 119, 72)
    line = (235, 245, 238)
    cv2.rectangle(pitch, (20, 20), (width - 20, height - 20), line, 2)
    cv2.line(pitch, (width // 2, 20), (width // 2, height - 20), line, 2)
    cv2.circle(pitch, (width // 2, height // 2), 65, line, 2)
    overlay = cv2.addWeighted(pitch, 0.62, colored, 0.55, 0)
    cv2.imwrite(path, overlay)


def write_stats(ball_possession, analyzed_frames, motion_stats):
    team1_poss = ball_possession.get(MODEL_CLASSES["team1"], 0)
    team2_poss = ball_possession.get(MODEL_CLASSES["team2"], 0)
    total = team1_poss + team2_poss

    if total > 0:
        team1_percent = (team1_poss / total) * 100
        team2_percent = (team2_poss / total) * 100
    else:
        team1_percent = team2_percent = 0

    total_distance = sum(item["distance"] for item in motion_stats.values())
    avg_speed_values = [
        item["speed_sum"] / item["speed_count"]
        for item in motion_stats.values()
        if item["speed_count"] > 0
    ]
    avg_speed = sum(avg_speed_values) / len(avg_speed_values) if avg_speed_values else 0
    max_speed = max((item["max_speed"] for item in motion_stats.values()), default=0)

    with open(OUT_STATS, "w") as f:
        f.write("Ball Possession Statistics\n")
        f.write("=" * 30 + "\n")
        f.write(f"Team 1 Possession: {team1_percent:.2f}% ({team1_poss} frames)\n")
        f.write(f"Team 2 Possession: {team2_percent:.2f}% ({team2_poss} frames)\n")
        f.write(f"Frames Written: {analyzed_frames}\n")
        f.write(f"Tracked Players: {len(motion_stats)}\n")
        f.write(f"Estimated Total Distance: {total_distance:.2f} pitch units\n")
        f.write(f"Average Speed: {avg_speed:.2f} pitch units/sec\n")
        f.write(f"Max Speed: {max_speed:.2f} pitch units/sec\n")


def main():
    os.makedirs(os.path.dirname(OUT_VIDEO), exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    object_detector = create_object_detector()
    field_client = None
    if ROBOFLOW_API_KEY and requests is not None:
        try:
            field_client = RoboflowHttpClient()
        except Exception as exc:
            print(f"Field keypoint HTTP client unavailable; using approximate projection. ({exc})")

    total_frames, fps = get_number_of_frames(VIDEO_SRC)
    frame_generator = get_frames(VIDEO_SRC)
    progress_callback = globals().get("PROGRESS_CALLBACK")

    if frame_generator is None:
        raise RuntimeError(f"Could not read frames from {VIDEO_SRC}")

    first_frame = next(frame_generator)
    height, width, _ = first_frame.shape

    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter(OUT_VIDEO, fourcc, fps, (width, height + PITCH_PANEL_HEIGHT))
    pitch_out = cv2.VideoWriter(OUT_PITCH_VIDEO, fourcc, fps, (width, PITCH_PANEL_HEIGHT))

    tracker_team1 = sv.ByteTrack()
    tracker_team2 = sv.ByteTrack()
    tracker_team1.reset()
    tracker_team2.reset()

    team_assigner = Assigner()
    kmeans = None
    team_colors = {}
    ball_possession = {MODEL_CLASSES["team1"]: 0, MODEL_CLASSES["team2"]: 0}
    possession_tracker = BallPossessionTracker()
    projector = PitchProjector(width, height, field_client=field_client)
    last_pitch_frame = None
    frames_written = 0
    tracking_rows = []
    last_positions = {}
    motion_stats = {}
    if callable(progress_callback):
        progress_callback(0, total_frames, "processing")

    for frame in tqdm(chain([first_frame], frame_generator), total=total_frames):
        detections = object_detector.predict(frame)

        goalkeepers_detections = detections[detections.class_id == MODEL_CLASSES["goalkepper"]]
        ball_detections = detections[detections.class_id == MODEL_CLASSES["ball"]]
        players_detections = detections[detections.class_id == MODEL_CLASSES["player"]]
        referee_detections = detections[detections.class_id == MODEL_CLASSES["referee"]]

        if len(players_detections) > 0:
            players_detections = players_detections.with_nms(threshold=0.5)

        if kmeans is None:
            kmeans = team_assigner.assign_team_color(frame, players_detections)
            if kmeans is not None:
                team_colors = team_assigner.team_colors

        if kmeans is not None:
            for object_ind, _ in enumerate(players_detections.class_id):
                team_id = team_assigner.get_player_team(
                    frame,
                    players_detections.xyxy[object_ind],
                    kmeans,
                )
                if team_id == 0:
                    players_detections.class_id[object_ind] = MODEL_CLASSES["team1"]
                elif team_id == 1:
                    players_detections.class_id[object_ind] = MODEL_CLASSES["team2"]
        else:
            players_detections.class_id[:] = MODEL_CLASSES["team1"]

        team1_detections = players_detections[players_detections.class_id == MODEL_CLASSES["team1"]]
        team2_detections = players_detections[players_detections.class_id == MODEL_CLASSES["team2"]]
        field_players_detections = players_detections[
            players_detections.class_id != MODEL_CLASSES["goalkepper"]
        ]

        player_ind, possession_team, ball_detections = possession_tracker.update(
            field_players_detections,
            ball_detections,
        )
        active_player_detection = empty_like(field_players_detections)

        if player_ind != -1:
            active_player_detection = field_players_detections[player_ind:player_ind + 1]
        if possession_team is not None:
            ball_possession[possession_team] += 1

        team1_detections = tracker_team1.update_with_detections(detections=team1_detections)
        team2_detections = tracker_team2.update_with_detections(detections=team2_detections)
        frame_transformer = projector.get_transformer(frame)

        record_tracking(
            frame_index=frames_written,
            fps=fps,
            transformer=frame_transformer,
            detections=team1_detections,
            team_id=MODEL_CLASSES["team1"],
            rows=tracking_rows,
            last_positions=last_positions,
            motion_stats=motion_stats,
        )
        record_tracking(
            frame_index=frames_written,
            fps=fps,
            transformer=frame_transformer,
            detections=team2_detections,
            team_id=MODEL_CLASSES["team2"],
            rows=tracking_rows,
            last_positions=last_positions,
            motion_stats=motion_stats,
        )

        pitch_frame = build_pitch_radar_frame(
            frame=frame,
            projector=projector,
            team1_detections=team1_detections,
            team2_detections=team2_detections,
            referee_detections=referee_detections,
            ball_detections=ball_detections,
            frame_width=width,
            transformer=frame_transformer,
        )
        last_pitch_frame = pitch_frame

        ball_detections.xyxy = sv.pad_boxes(xyxy=ball_detections.xyxy, px=10)
        active_player_detection.xyxy = sv.pad_boxes(xyxy=active_player_detection.xyxy, px=10)

        labels = {
            "labels_team1": labels_for(team1_detections),
            "labels_team2": labels_for(team2_detections),
            "labels_referee": ["ref"] * len(referee_detections),
            "labels_gk": ["GK"] * len(goalkeepers_detections),
        }

        all_detection = {
            "goalkeepers": goalkeepers_detections,
            "ball": ball_detections,
            "palyers": field_players_detections,
            "referee": referee_detections,
            "team1": team1_detections,
            "team2": team2_detections,
            "active_player": active_player_detection,
        }

        annotated_frame = annotate_frames(frame, all_detection, labels, ball_possession)
        combined_frame = np.vstack((annotated_frame, pitch_frame))
        out.write(combined_frame)
        pitch_out.write(pitch_frame)
        frames_written += 1
        if callable(progress_callback):
            progress_callback(frames_written, total_frames, "processing")

    out.release()
    pitch_out.release()
    if callable(progress_callback):
        progress_callback(frames_written, total_frames, "finalizing")

    if last_pitch_frame is not None:
        cv2.imwrite(OUT_PITCH_MAP, last_pitch_frame)

    write_tracking_csv(tracking_rows)
    write_heatmap(tracking_rows)
    write_stats(ball_possession, frames_written, motion_stats)
    if callable(progress_callback):
        progress_callback(frames_written, total_frames, "complete")

    print(f"Video saved as {OUT_VIDEO}")
    print(f"Pitch movement video saved as {OUT_PITCH_VIDEO}")
    print(f"Last pitch frame saved as {OUT_PITCH_MAP}")
    if globals().get("OUT_HEATMAP"):
        print(f"Heatmap saved as {OUT_HEATMAP}")
    if globals().get("OUT_TRACKING_CSV"):
        print(f"Tracking CSV saved as {OUT_TRACKING_CSV}")
    print(f"Statistics saved as {OUT_STATS}")


if __name__ == "__main__":
    main()
