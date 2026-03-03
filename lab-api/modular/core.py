from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import pymysql
import os
import uuid
import io
import csv
import json
import time
import hmac
import base64
import hashlib
import re
import traceback
from collections import deque
from threading import Lock
from functools import wraps
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from flask import g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def load_local_env(env_file=".env"):
    env_path = os.path.join(BASE_DIR, env_file)
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if not key:
                    continue
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                if key not in os.environ:
                    os.environ[key] = value
    except Exception as e:
        print(f"[warn] load_local_env failed: {e}")


def env_int(key, default):
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return int(default)


load_local_env()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

DB = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": env_int("DB_PORT", 3306),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "lab_mgmt"),
    "charset": os.getenv("DB_CHARSET", "utf8mb4"),
    "cursorclass": pymysql.cursors.DictCursor,
}

LEGACY_DEFAULT_PASSWORD_MODE = os.getenv("LEGACY_DEFAULT_PASSWORD_MODE", "username")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-me")
JWT_EXPIRE_SECONDS = env_int("JWT_EXPIRE_SECONDS", 3600)
REFRESH_EXPIRE_SECONDS = env_int("REFRESH_EXPIRE_SECONDS", 86400 * 14)
if JWT_SECRET == "dev-only-change-me":
    print("[warn] JWT_SECRET not set, using insecure development default")
RATE_LIMIT_RULES = {
    "login": {"window": 60, "max": 10},
    "register": {"window": 300, "max": 5},
    "refresh": {"window": 60, "max": 20},
    "change_password": {"window": 300, "max": 10},
}
DEFAULT_RESERVATION_SLOTS = [
    "08:00-08:40",
    "08:45-09:35",
    "10:25-11:05",
    "11:10-11:50",
    "14:30-15:10",
    "15:15-15:55",
    "16:05-16:45",
    "16:50-17:30",
    "19:00-19:40",
    "19:45-20:25",
]
PERIOD_SLOT_ITEMS = [
    {"index": 1, "label": "第一节", "time": "08:00-08:40"},
    {"index": 2, "label": "第二节", "time": "08:45-09:35"},
    {"index": 3, "label": "第三节", "time": "10:25-11:05"},
    {"index": 4, "label": "第四节", "time": "11:10-11:50"},
    {"index": 5, "label": "第五节", "time": "14:30-15:10"},
    {"index": 6, "label": "第六节", "time": "15:15-15:55"},
    {"index": 7, "label": "第七节", "time": "16:05-16:45"},
    {"index": 8, "label": "第八节", "time": "16:50-17:30"},
    {"index": 9, "label": "第九节", "time": "19:00-19:40"},
    {"index": 10, "label": "第十节", "time": "19:45-20:25"},
]
PERIOD_INDEX_TO_SLOT = {int(x["index"]): str(x["time"]) for x in PERIOD_SLOT_ITEMS}
_CN_DIGIT_MAP = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
PERIOD_MAPPING_TEXT = "；".join([f"{x['label']}({x['index']})={x['time']}" for x in PERIOD_SLOT_ITEMS])
RESERVATION_MIN_DAYS_AHEAD = env_int("RESERVATION_MIN_DAYS_AHEAD", 0)
RESERVATION_MAX_DAYS_AHEAD = env_int("RESERVATION_MAX_DAYS_AHEAD", 30)
RESERVATION_MIN_TIME = os.getenv("RESERVATION_MIN_TIME", "08:00")
RESERVATION_MAX_TIME = os.getenv("RESERVATION_MAX_TIME", "22:00")
RESERVATION_LOCK_TIMEOUT_SECONDS = env_int("RESERVATION_LOCK_TIMEOUT_SECONDS", 5)
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "").strip()
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn").strip().rstrip("/")
SILICONFLOW_MODEL = os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct").strip()
SILICONFLOW_TIMEOUT_SECONDS = env_int("SILICONFLOW_TIMEOUT_SECONDS", 20)
_RATE_LIMIT_BUCKETS = {}
_RATE_LIMIT_LOCK = Lock()
AGENT_PENDING_TTL_SECONDS = max(60, env_int("AGENT_PENDING_TTL_SECONDS", 600))
_AGENT_PENDING_LOCK = Lock()
_AGENT_PENDING_CONTEXT = {}
AGENT_TOOL_WHITELIST = {
    "reservation_summary",
    "lab_reservation_list",
    "availability",
    "cancel_lab",
    "cancel_all_prepare",
    "cancel_all_confirm",
    "cancel_all_abort",
    "reschedule",
    "reserve_create",
    "update_profile",
    "general_reply",
}


def query(sql, params=None):
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def execute(sql, params=None):
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
        conn.commit()
        return True
    finally:
        conn.close()


def execute_insert(sql, params=None):
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            new_id = cur.lastrowid
        conn.commit()
        return new_id
    finally:
        conn.close()


class BizError(Exception):
    def __init__(self, msg, status=400):
        super().__init__(msg)
        self.msg = str(msg)
        self.status = int(status)


@app.errorhandler(BizError)
def handle_biz_error(e):
    return jsonify({"ok": False, "msg": e.msg}), int(e.status or 400)


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    if isinstance(e, HTTPException):
        status = int(e.code or 500)
        msg = str(e.description or "request failed")
        return jsonify({"ok": False, "msg": msg}), status
    print(f"[error] unhandled exception: {e}")
    traceback.print_exc()
    return jsonify({"ok": False, "msg": "internal server error"}), 500


def run_in_transaction(work_fn):
    conn = pymysql.connect(**DB)
    try:
        conn.begin()
        with conn.cursor() as cur:
            result = work_fn(cur)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_user_password_column():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s
                  AND TABLE_NAME='user'
                  AND COLUMN_NAME='password_hash'
                """,
                (DB["database"],),
            )
            has_column = (cur.fetchone() or {}).get("cnt", 0) > 0
            if not has_column:
                cur.execute("ALTER TABLE user ADD COLUMN password_hash VARCHAR(255) NULL")

            cur.execute("SELECT id, username, password_hash FROM user")
            users = cur.fetchall()
            for u in users:
                hashed = (u.get("password_hash") or "").strip()
                if hashed:
                    continue

                username = (u.get("username") or "").strip()
                if LEGACY_DEFAULT_PASSWORD_MODE == "username" and username:
                    raw_pwd = username
                else:
                    raw_pwd = "123456"
                cur.execute(
                    "UPDATE user SET password_hash=%s WHERE id=%s",
                    (generate_password_hash(raw_pwd), u["id"]),
                )
        conn.commit()
    finally:
        conn.close()


def ensure_auth_refresh_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_refresh_token (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT NOT NULL,
                    token_hash CHAR(64) NOT NULL UNIQUE,
                    expires_at DATETIME NOT NULL,
                    revoked_at DATETIME NULL,
                    created_at DATETIME NOT NULL,
                    replaced_by_hash CHAR(64) NULL,
                    INDEX idx_user_id (user_id),
                    INDEX idx_expires_at (expires_at),
                    INDEX idx_revoked_at (revoked_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_audit_log_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    operator_id INT NULL,
                    operator_name VARCHAR(64) NOT NULL DEFAULT '',
                    operator_role VARCHAR(32) NOT NULL DEFAULT '',
                    action VARCHAR(64) NOT NULL,
                    target_type VARCHAR(64) NOT NULL DEFAULT '',
                    target_id VARCHAR(64) NOT NULL DEFAULT '',
                    detail_json TEXT NULL,
                    ip VARCHAR(64) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL,
                    INDEX idx_operator_id (operator_id),
                    INDEX idx_action (action),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_announcement_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS announcement (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    title VARCHAR(120) NOT NULL DEFAULT '',
                    content TEXT NOT NULL,
                    publisher_id INT NULL,
                    publisher_name VARCHAR(64) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL,
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_lost_found_claim_columns():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "claim_apply_status": "VARCHAR(16) NOT NULL DEFAULT ''",
            "claim_apply_user": "VARCHAR(64) NOT NULL DEFAULT ''",
            "claim_apply_reason": "VARCHAR(255) NOT NULL DEFAULT ''",
            "claim_apply_student_id": "VARCHAR(64) NOT NULL DEFAULT ''",
            "claim_apply_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "claim_apply_class": "VARCHAR(64) NOT NULL DEFAULT ''",
            "claim_apply_at": "DATETIME NULL",
            "claim_reviewed_by": "VARCHAR(64) NOT NULL DEFAULT ''",
            "claim_reviewed_at": "DATETIME NULL",
            "claim_review_note": "VARCHAR(255) NOT NULL DEFAULT ''",
        }
        with conn.cursor() as cur:
            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='lost_found'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE lost_found ADD COLUMN {col} {ddl}")
        conn.commit()
    finally:
        conn.close()


def get_client_ip():
    x_forwarded_for = (request.headers.get("X-Forwarded-For") or "").strip()
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = (request.headers.get("X-Real-IP") or "").strip()
    if x_real_ip:
        return x_real_ip
    return (request.remote_addr or "").strip() or "unknown"


def _hit_rate_limit(scope, bucket_key):
    rule = RATE_LIMIT_RULES.get(scope) or {}
    window = int(rule.get("window") or 0)
    max_requests = int(rule.get("max") or 0)
    if window <= 0 or max_requests <= 0:
        return True, 0

    now = time.time()
    key = f"{scope}:{bucket_key}"
    with _RATE_LIMIT_LOCK:
        timestamps = _RATE_LIMIT_BUCKETS.get(key)
        if timestamps is None:
            timestamps = deque()
            _RATE_LIMIT_BUCKETS[key] = timestamps

        cutoff = now - window
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        if len(timestamps) >= max_requests:
            retry_after = max(1, int(window - (now - timestamps[0])))
            return False, retry_after

        timestamps.append(now)
    return True, 0


def enforce_rate_limit(scope, bucket_key):
    ok, retry_after = _hit_rate_limit(scope, bucket_key)
    if ok:
        return None
    return (
        jsonify({"ok": False, "msg": "too many requests"}),
        429,
        {"Retry-After": str(retry_after)},
    )


def _b64url_encode(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text):
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + pad).encode("ascii"))


def jwt_encode(payload):
    header = {"alg": "HS256", "typ": "JWT"}
    header_part = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_part = _b64url_encode(signature)
    return f"{header_part}.{payload_part}.{sig_part}"


def jwt_decode(token):
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid token")
    header_part, payload_part, sig_part = parts
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    expected_sig = _b64url_encode(hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest())
    if not hmac.compare_digest(expected_sig, sig_part):
        raise ValueError("invalid signature")
    payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    exp = int(payload.get("exp") or 0)
    if exp and int(time.time()) > exp:
        raise ValueError("token expired")
    return payload


def create_access_token(user):
    now = int(time.time())
    payload = {
        "typ": "access",
        "sub": user["username"],
        "uid": int(user["id"]),
        "role": user["role"],
        "iat": now,
        "exp": now + JWT_EXPIRE_SECONDS,
    }
    return jwt_encode(payload)


def get_bearer_token():
    auth = request.headers.get("Authorization", "").strip()
    if not auth or not auth.lower().startswith("bearer "):
        return ""
    return auth[7:].strip()


def hash_refresh_token(refresh_token):
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def create_refresh_token():
    return f"{uuid.uuid4().hex}{uuid.uuid4().hex}"


def issue_refresh_token(user_id):
    raw = create_refresh_token()
    token_hash = hash_refresh_token(raw)
    now = datetime.now()
    exp = now.timestamp() + REFRESH_EXPIRE_SECONDS
    expires_at = datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M:%S")
    created_at = now.strftime("%Y-%m-%d %H:%M:%S")
    execute_insert(
        """
        INSERT INTO auth_refresh_token (user_id, token_hash, expires_at, created_at)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, token_hash, expires_at, created_at),
    )
    return raw


def revoke_refresh_token(raw_token, replaced_by_hash=None):
    if not raw_token:
        return
    token_hash = hash_refresh_token(raw_token)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if replaced_by_hash:
        execute(
            """
            UPDATE auth_refresh_token
            SET revoked_at=%s, replaced_by_hash=%s
            WHERE token_hash=%s AND revoked_at IS NULL
            """,
            (now, replaced_by_hash, token_hash),
        )
    else:
        execute(
            """
            UPDATE auth_refresh_token
            SET revoked_at=%s
            WHERE token_hash=%s AND revoked_at IS NULL
            """,
            (now, token_hash),
        )


def get_refresh_token_row(raw_token):
    if not raw_token:
        return None
    token_hash = hash_refresh_token(raw_token)
    rows = query(
        """
        SELECT id, user_id AS userId, token_hash AS tokenHash, expires_at AS expiresAt,
               revoked_at AS revokedAt
        FROM auth_refresh_token
        WHERE token_hash=%s
        LIMIT 1
        """,
        (token_hash,),
    )
    return rows[0] if rows else None


def is_refresh_token_valid(row):
    if not row:
        return False
    if row.get("revokedAt"):
        return False
    exp = row.get("expiresAt")
    exp_dt = _to_datetime(exp)
    return exp_dt > datetime.now()


def auth_required(roles=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = get_bearer_token()
            if not token:
                return jsonify({"ok": False, "msg": "unauthorized"}), 401
            try:
                payload = jwt_decode(token)
            except Exception:
                return jsonify({"ok": False, "msg": "unauthorized"}), 401
            if payload.get("typ") != "access":
                return jsonify({"ok": False, "msg": "unauthorized"}), 401

            uid = int(payload.get("uid") or 0)
            row = query("SELECT id, username, role FROM user WHERE id=%s LIMIT 1", (uid,))
            if not row:
                return jsonify({"ok": False, "msg": "unauthorized"}), 401
            current_user = row[0]
            if roles and current_user["role"] not in roles:
                return jsonify({"ok": False, "msg": "forbidden"}), 403
            g.current_user = current_user
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def _minutes_to_hhmm(minutes):
    if minutes is None or minutes < 0:
        return ""
    hh = int(minutes // 60)
    mm = int(minutes % 60)
    return f"{hh:02d}:{mm:02d}"


def _canonicalize_slot_text(slot_text):
    start, end = _slot_to_minutes(slot_text)
    if start is None or end is None:
        return str(slot_text or "").strip()
    return f"{_minutes_to_hhmm(start)}-{_minutes_to_hhmm(end)}"


def parse_slots(time_range):
    slots = set()
    for t in (time_range or "").split(","):
        raw = t.strip()
        if not raw:
            continue
        canonical = _canonicalize_slot_text(raw)
        if canonical:
            slots.add(canonical)
    return slots


def _clock_to_minutes(text):
    raw = str(text or "").strip()
    parts = raw.split(":")
    if len(parts) != 2:
        return None
    try:
        hh = int(parts[0])
        mm = int(parts[1])
    except ValueError:
        return None
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return None
    return hh * 60 + mm


def _slot_to_minutes(slot_text):
    raw = str(slot_text or "").strip()
    parts = raw.split("-")
    if len(parts) != 2:
        return None, None
    start = _clock_to_minutes(parts[0].strip())
    end = _clock_to_minutes(parts[1].strip())
    if start is None or end is None or end <= start:
        return None, None
    return start, end


def _resolve_rule_slots(payload):
    payload = payload or {}
    rule_slots = payload.get("slots")
    if not isinstance(rule_slots, list):
        rule_slots = list(DEFAULT_RESERVATION_SLOTS)

    allowed_start = _clock_to_minutes(payload.get("minTime", RESERVATION_MIN_TIME))
    allowed_end = _clock_to_minutes(payload.get("maxTime", RESERVATION_MAX_TIME))

    resolved = []
    seen = set()
    for raw in rule_slots:
        canonical = _canonicalize_slot_text(raw)
        if not canonical or canonical in seen:
            continue
        start, end = _slot_to_minutes(canonical)
        if start is None or end is None:
            continue
        if allowed_start is not None and start < allowed_start:
            continue
        if allowed_end is not None and end > allowed_end:
            continue
        seen.add(canonical)
        resolved.append(canonical)
    return resolved


def _count_slot_frequency(rows):
    freq = {}
    for row in rows or []:
        for slot in parse_slots(row.get("time")):
            freq[slot] = int(freq.get(slot) or 0) + 1
    max_count = max(freq.values()) if freq else 0
    return freq, max_count


def _build_recommend_time_windows(rule_slots):
    normalized = []
    for slot in rule_slots or []:
        canonical = _canonicalize_slot_text(slot)
        start, end = _slot_to_minutes(canonical)
        if start is None or end is None:
            continue
        normalized.append({"slot": canonical, "start": start, "end": end})

    normalized.sort(key=lambda x: (x["start"], x["end"]))
    windows = []

    # Prefer teacher-friendly double-period windows: 1-2, 3-4, 5-6, 7-8 ...
    idx = 0
    while idx + 1 < len(normalized):
        cur = normalized[idx]
        nxt = normalized[idx + 1]
        if cur["end"] == nxt["start"]:
            windows.append(
                {
                    "time": f"{cur['slot']},{nxt['slot']}",
                    "firstStart": cur["start"],
                    "slots": [cur["slot"], nxt["slot"]],
                }
            )
        idx += 2

    if windows:
        return windows

    # Fallback to single slot windows if no valid consecutive pairs exist.
    for row in normalized:
        windows.append({"time": row["slot"], "firstStart": row["start"], "slots": [row["slot"]]})
    return windows


def get_reservation_rules_payload():
    today = datetime.now().date()
    min_days = max(0, RESERVATION_MIN_DAYS_AHEAD)
    max_days = max(min_days, RESERVATION_MAX_DAYS_AHEAD)
    min_date = (today + timedelta(days=min_days)).strftime("%Y-%m-%d")
    max_date = (today + timedelta(days=max_days)).strftime("%Y-%m-%d")
    payload = {
        "minDaysAhead": min_days,
        "maxDaysAhead": max_days,
        "minTime": RESERVATION_MIN_TIME,
        "maxTime": RESERVATION_MAX_TIME,
        "minDate": min_date,
        "maxDate": max_date,
    }
    payload["slots"] = _resolve_rule_slots(payload)
    payload["periodSlots"] = PERIOD_SLOT_ITEMS
    return payload


def validate_reservation_schedule(date_text, time_range):
    date_str = str(date_text or "").strip()
    time_str = str(time_range or "").strip()
    if not date_str or not time_str:
        return "params error"

    date_dt = _parse_date_yyyy_mm_dd(date_str)
    if not date_dt:
        return "invalid date"

    today = datetime.now().date()
    day_delta = (date_dt.date() - today).days
    min_days = max(0, RESERVATION_MIN_DAYS_AHEAD)
    max_days = max(min_days, RESERVATION_MAX_DAYS_AHEAD)
    if day_delta < min_days or day_delta > max_days:
        return f"date out of range ({min_days}-{max_days} days ahead)"

    allowed_start = _clock_to_minutes(RESERVATION_MIN_TIME)
    allowed_end = _clock_to_minutes(RESERVATION_MAX_TIME)
    if allowed_start is None or allowed_end is None or allowed_end <= allowed_start:
        return "invalid reservation time rule"

    ranges = []
    for slot in [x.strip() for x in time_str.split(",") if x.strip()]:
        start, end = _slot_to_minutes(slot)
        if start is None:
            return f"invalid time slot: {slot}"
        if start < allowed_start or end > allowed_end:
            return f"time out of range ({RESERVATION_MIN_TIME}-{RESERVATION_MAX_TIME})"
        ranges.append((start, end))

    if not ranges:
        return "time required"

    ranges.sort(key=lambda x: (x[0], x[1]))
    for i in range(1, len(ranges)):
        prev = ranges[i - 1]
        cur = ranges[i]
        if cur[0] < prev[1]:
            return "time slots overlap"

    return ""


def _reservation_lock_key(lab_name, date_text):
    return f"reservation:{str(lab_name or '').strip()}:{str(date_text or '').strip()}"


def _acquire_named_lock(cur, lock_key, timeout_seconds=RESERVATION_LOCK_TIMEOUT_SECONDS):
    cur.execute("SELECT GET_LOCK(%s, %s) AS ok", (lock_key, max(1, int(timeout_seconds))))
    row = cur.fetchone() or {}
    return int(row.get("ok") or 0) == 1


def _release_named_lock(cur, lock_key):
    try:
        cur.execute("SELECT RELEASE_LOCK(%s)", (lock_key,))
    except Exception:
        pass


def has_approved_conflict_with_cur(cur, lab_name, date, time_range, exclude_id=None):
    incoming_slots = parse_slots(time_range)
    if not incoming_slots:
        return False

    sql = """
        SELECT time
        FROM reservation
        WHERE lab_name=%s AND date=%s AND status='approved'
    """
    params = [lab_name, date]
    if exclude_id is not None:
        sql += " AND id<>%s"
        params.append(exclude_id)
    cur.execute(sql, params)
    rows = cur.fetchall()

    for row in rows:
        exist_slots = parse_slots(row.get("time"))
        if incoming_slots & exist_slots:
            return True
    return False


def has_approved_conflict(lab_name, date, time_range, exclude_id=None):
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            return has_approved_conflict_with_cur(cur, lab_name, date, time_range, exclude_id=exclude_id)
    finally:
        conn.close()


def _to_datetime(value):
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.min
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return datetime.min


def _to_text_time(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value or "")


def _parse_date_yyyy_mm_dd(text):
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return None


def _to_int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _compact_ids(raw_ids, sample_size=50):
    ids = []
    for rid in raw_ids or []:
        rid_int = _to_int_or_none(rid)
        if rid_int is not None:
            ids.append(rid_int)
    return {
        "count": len(ids),
        "sample": ids[:sample_size],
        "truncated": len(ids) > sample_size,
    }


def audit_log(action, target_type="", target_id="", detail=None, actor=None):
    actor = actor or getattr(g, "current_user", {}) or {}
    operator_id = _to_int_or_none(actor.get("id"))
    operator_name = str(actor.get("username") or "")
    operator_role = str(actor.get("role") or "")
    detail_json = json.dumps(detail or {}, ensure_ascii=False, separators=(",", ":"))
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        execute_insert(
            """
            INSERT INTO audit_log (
                operator_id, operator_name, operator_role, action,
                target_type, target_id, detail_json, ip, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                operator_id,
                operator_name,
                operator_role,
                action,
                str(target_type or ""),
                str(target_id or ""),
                detail_json,
                get_client_ip(),
                created_at,
            ),
        )
    except Exception as e:
        print(f"[warn] audit_log failed: {e}")


def fetch_audit_logs(action="", operator="", target_type="", start_date="", end_date="", limit=100, offset=0, with_total=False):
    where_sql = ""
    where_params = []

    if action:
        where_sql += " AND action=%s"
        where_params.append(action)
    if operator:
        where_sql += " AND operator_name=%s"
        where_params.append(operator)
    if target_type:
        where_sql += " AND target_type=%s"
        where_params.append(target_type)

    start_dt = _parse_date_yyyy_mm_dd(start_date)
    end_dt = _parse_date_yyyy_mm_dd(end_date)
    if start_date and not start_dt:
        return None, None, "invalid startDate"
    if end_date and not end_dt:
        return None, None, "invalid endDate"
    if start_dt and end_dt and start_dt > end_dt:
        return None, None, "startDate must be <= endDate"

    if start_dt:
        where_sql += " AND created_at >= %s"
        where_params.append(start_dt.strftime("%Y-%m-%d 00:00:00"))
    if end_dt:
        where_sql += " AND created_at < %s"
        where_params.append((end_dt + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00"))

    list_sql = f"""
        SELECT id,
               operator_id AS operatorId,
               operator_name AS operatorName,
               operator_role AS operatorRole,
               action,
               target_type AS targetType,
               target_id AS targetId,
               detail_json AS detailJson,
               ip,
               created_at AS createdAt
        FROM audit_log
        WHERE 1=1 {where_sql}
        ORDER BY id DESC
    """
    list_params = list(where_params)

    if limit is not None:
        list_sql += " LIMIT %s OFFSET %s"
        list_params.extend([max(1, int(limit)), max(0, int(offset))])

    rows = query(list_sql, list_params)

    total = None
    if with_total:
        total_rows = query(f"SELECT COUNT(*) AS cnt FROM audit_log WHERE 1=1 {where_sql}", where_params)
        total = int((total_rows[0] or {}).get("cnt") or 0) if total_rows else 0

    return rows, total, ""


def _extract_json_object(raw_text):
    text = str(raw_text or "")
    if not text:
        return ""

    start = text.find("{")
    if start < 0:
        return ""

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
            continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return ""


def _normalize_agent_time(raw_time):
    if isinstance(raw_time, list):
        parts = [str(x or "").strip() for x in raw_time]
    else:
        normalized = str(raw_time or "").replace("，", ",").replace("；", ",").replace("、", ",")
        parts = [x.strip() for x in normalized.split(",")]
    clean = []
    for part in parts:
        if not part:
            continue
        canonical = _canonicalize_slot_text(part)
        if canonical:
            clean.append(canonical)
    return ",".join(clean)


def _cn_to_int(token):
    raw = str(token or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        try:
            return int(raw)
        except Exception:
            return None
    if raw == "十":
        return 10
    if raw in _CN_DIGIT_MAP:
        return int(_CN_DIGIT_MAP[raw])
    if raw.startswith("十"):
        tail = raw[1:]
        if tail in _CN_DIGIT_MAP:
            return 10 + int(_CN_DIGIT_MAP[tail])
    if raw.endswith("十"):
        head = raw[:-1]
        if head in _CN_DIGIT_MAP:
            return int(_CN_DIGIT_MAP[head]) * 10
    if "十" in raw:
        parts = raw.split("十", 1)
        left = parts[0].strip()
        right = parts[1].strip()
        left_num = _CN_DIGIT_MAP.get(left) if left else 1
        right_num = _CN_DIGIT_MAP.get(right) if right else 0
        if left_num is not None and right_num is not None:
            return int(left_num) * 10 + int(right_num)
    return None


def _parse_period_token(token):
    val = _cn_to_int(token)
    if val is None:
        return None
    return int(val) if int(val) in PERIOD_INDEX_TO_SLOT else None


def _extract_time_from_period_expression(text):
    raw = str(text or "")
    if not raw:
        return ""

    s = (
        raw.replace("－", "-")
        .replace("—", "-")
        .replace("～", "-")
        .replace("~", "-")
        .replace("到", "-")
        .replace("至", "-")
        .replace("。", ".")
        .replace("．", ".")
    )

    seq = []

    def add_period(n):
        if n is None:
            return
        if n not in PERIOD_INDEX_TO_SLOT:
            return
        if n not in seq:
            seq.append(n)

    # 1-2节 / 第一-第二节 / 第1节-第2节
    for m in re.finditer(r"第?\s*([0-9一二三四五六七八九十两]+)\s*-\s*第?\s*([0-9一二三四五六七八九十两]+)\s*节", s):
        a = _parse_period_token(m.group(1))
        b = _parse_period_token(m.group(2))
        if a is None or b is None:
            continue
        if a <= b:
            for n in range(a, b + 1):
                add_period(n)
        else:
            for n in range(a, b - 1, -1):
                add_period(n)

    # 12节 / 34节 / 56节 / 78节 (紧凑说法)
    for m in re.finditer(r"(?<!\d)([1-9]{2})\s*节", s):
        pair = m.group(1)
        for ch in pair:
            add_period(_parse_period_token(ch))

    # 12两节 / 34两节
    for m in re.finditer(r"(?<!\d)([1-9]{2})\s*两节", s):
        pair = m.group(1)
        for ch in pair:
            add_period(_parse_period_token(ch))

    # 9.10两节 / 1,2节 / 第3、4节
    for m in re.finditer(
        r"第?\s*([0-9一二三四五六七八九十两]+)\s*[、,，.]\s*第?\s*([0-9一二三四五六七八九十两]+?)\s*两?节",
        s,
    ):
        add_period(_parse_period_token(m.group(1)))
        add_period(_parse_period_token(m.group(2)))

    # 第一节 第二节 / 第9节
    for m in re.finditer(r"第?\s*([0-9一二三四五六七八九十两]+)\s*节", s):
        add_period(_parse_period_token(m.group(1)))

    if not seq:
        return ""

    ordered = sorted(seq)
    slots = [PERIOD_INDEX_TO_SLOT[n] for n in ordered if n in PERIOD_INDEX_TO_SLOT]
    return ",".join(slots)


def _normalize_agent_missing_fields(raw_missing):
    normalized = []
    seen = set()
    for item in raw_missing or []:
        key = str(item or "").strip().lower().replace(" ", "").replace("-", "_")
        if not key:
            continue
        mapped = ""
        if key in {"date", "day", "日期", "预约日期"}:
            mapped = "date"
        elif key in {"time", "slot", "timeslot", "时段", "时间", "节次"}:
            mapped = "time"
        elif key in {
            "lab",
            "lab_id",
            "labid",
            "lab_name",
            "labname",
            "实验室",
            "教室",
            "机房",
            "地点",
        }:
            mapped = "lab"
        if not mapped or mapped in seen:
            continue
        seen.add(mapped)
        normalized.append(mapped)
    return normalized


def _extract_date_from_text(text):
    raw = str(text or "").strip()
    if not raw:
        return ""

    today = datetime.now().date()
    if "今天" in raw:
        return today.strftime("%Y-%m-%d")
    if "明天" in raw:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if "大后天" in raw:
        return (today + timedelta(days=3)).strftime("%Y-%m-%d")
    if "后天" in raw:
        return (today + timedelta(days=2)).strftime("%Y-%m-%d")

    for m in re.finditer(r"(?<!\d)(20\d{2})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})\s*日?", raw):
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue

    for m in re.finditer(r"(?<!\d)(\d{1,2})\s*(?:月|/|\.)\s*(\d{1,2})\s*日?", raw):
        try:
            dt = datetime(today.year, int(m.group(1)), int(m.group(2)))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
    return ""


def _extract_lab_name_from_text(text):
    raw = str(text or "").strip()
    if not raw:
        return ""

    for m in re.finditer(r"(?<![A-Za-z0-9])([A-Za-z]{1,2}\s*\d{3,4})(?![A-Za-z0-9])", raw):
        code = re.sub(r"\s+", "", str(m.group(1) or "")).upper()
        if code:
            return code

    patterns = [
        r"(?:在|到|去|预约|预定|申请)\s*([^\s，。,.；;]{1,24}(?:实验室|机房|教室))",
        r"([^\s，。,.；;]{1,24}(?:实验室|机房|教室))",
    ]
    for pattern in patterns:
        m = re.search(pattern, raw)
        if not m:
            continue
        candidate = re.sub(r"\s+", "", str(m.group(1) or "").strip())
        candidate = re.sub(
            r"^(?:今天|明天|后天|大后天|本周[一二三四五六日天]?|下周[一二三四五六日天]?)+",
            "",
            candidate,
        )
        candidate = re.sub(
            r"^(?:取消|撤销|查看|查询|检查|检索|统计|预约|预定|申请|所有|我的|目前|当前|请|帮我|帮忙|想|要)+",
            "",
            candidate,
        )
        candidate = str(candidate or "").strip()
        if not candidate:
            continue
        generic_candidates = {
            "实验室",
            "机房",
            "教室",
            "这个实验室",
            "该实验室",
            "某实验室",
            "具体实验室",
            "哪个实验室",
            "哪间实验室",
            "所有实验室",
        }
        if candidate in generic_candidates:
            continue
        if candidate in {"实验室", "机房", "教室"}:
            continue
        if len(candidate) > 12:
            continue
        if any(
            x in candidate
            for x in (
                "哪些",
                "哪个",
                "哪间",
                "空闲",
                "有空",
                "可用",
                "有没有",
                "有无",
                "空着",
                "预约",
                "预定",
                "申请",
                "今天",
                "明天",
                "后天",
                "大后天",
            )
        ):
            continue
        if candidate:
            return candidate
    return ""


def _extract_nickname_from_text(text):
    raw = str(text or "").strip()
    if not raw:
        return ""

    normalized = re.sub(r"\s+", " ", raw.replace("：", " ").replace(":", " ")).strip()
    patterns = [
        r"(?:帮我|请|麻烦)?(?:把|将)?(?:我(?:的)?)?昵称(?:改成|改为|换成|设为|设置为|叫做?)\s*[\"“”']?([^\"“”'，。,.!?！？]{1,24})",
        r"(?:帮我|请|麻烦)?(?:把|将)?名字(?:改成|改为|换成|设为|设置为)\s*[\"“”']?([^\"“”'，。,.!?！？]{1,24})",
        r"(?:我的?)?昵称(?:是|叫)\s*[\"“”']?([^\"“”'，。,.!?！？]{1,24})",
    ]
    for pat in patterns:
        m = re.search(pat, normalized, flags=re.IGNORECASE)
        if not m:
            continue
        nickname = str(m.group(1) or "").strip()
        nickname = re.sub(r"[，。,.!?！？]+$", "", nickname)
        nickname = re.sub(r"\s+", "", nickname)
        if nickname:
            return nickname[:24]
    return ""


def _is_my_reservations_query(text):
    raw = str(text or "").strip()
    if not raw:
        return False
    direct_phrases = (
        "我的预约",
        "我目前的预约",
        "查看预约",
        "查询预约",
        "预约记录",
        "有多少预约",
        "几条预约",
    )
    if any(x in raw for x in direct_phrases):
        return True
    has_reserve_word = any(x in raw for x in ("预约", "预定"))
    has_query_word = any(x in raw for x in ("查看", "查询", "多少", "几条", "记录", "列表", "状态", "目前", "当前"))
    has_self_word = any(x in raw for x in ("我", "我的", "本人"))
    return has_reserve_word and has_query_word and has_self_word


def _agent_handle_my_reservations_query(user_name, limit=5):
    owner = str(user_name or "").strip()
    if not owner:
        return _agent_response(code=401, msg="unauthorized", reply="登录状态失效，请重新登录。", action="error", http_status=401)

    total_rows = query("SELECT COUNT(*) AS cnt FROM reservation WHERE user_name=%s", (owner,))
    total = int((total_rows[0] or {}).get("cnt") or 0) if total_rows else 0
    if total <= 0:
        return _agent_response(code=0, msg="ok", reply="你目前还没有预约记录。", action="reservation_summary", http_status=200)

    status_rows = query(
        """
        SELECT status, COUNT(*) AS cnt
        FROM reservation
        WHERE user_name=%s
        GROUP BY status
        """,
        (owner,),
    )
    status_counter = {}
    for row in status_rows:
        k = str((row or {}).get("status") or "").strip()
        if not k:
            continue
        status_counter[k] = int((row or {}).get("cnt") or 0)

    today = datetime.now().strftime("%Y-%m-%d")
    active_rows = query(
        """
        SELECT COUNT(*) AS cnt
        FROM reservation
        WHERE user_name=%s
          AND status IN ('pending', 'approved')
          AND date>=%s
        """,
        (owner, today),
    )
    active_cnt = int((active_rows[0] or {}).get("cnt") or 0) if active_rows else 0

    recent_rows = query(
        """
        SELECT id, lab_name AS labName, date, time, status
        FROM reservation
        WHERE user_name=%s
        ORDER BY date DESC, id DESC
        LIMIT %s
        """,
        (owner, max(1, int(limit))),
    )

    status_label = {
        "pending": "待审批",
        "approved": "已通过",
        "rejected": "已拒绝",
        "cancelled": "已取消",
    }
    ordered_status = ["pending", "approved", "rejected", "cancelled"]
    status_parts = []
    for key in ordered_status:
        cnt = int(status_counter.get(key) or 0)
        if cnt <= 0:
            continue
        status_parts.append(f"{status_label.get(key, key)}{cnt}条")
    for key, cnt in status_counter.items():
        if key in ordered_status:
            continue
        n = int(cnt or 0)
        if n > 0:
            status_parts.append(f"{key}{n}条")
    status_text = "，".join(status_parts) if status_parts else "暂无状态统计"

    lines = []
    idx = 1
    for row in recent_rows:
        rid = int((row or {}).get("id") or 0)
        lab_name = str((row or {}).get("labName") or "").strip() or "未命名实验室"
        date_text = str((row or {}).get("date") or "").strip()
        time_text = str((row or {}).get("time") or "").strip()
        status_text_line = status_label.get(str((row or {}).get("status") or "").strip(), str((row or {}).get("status") or "").strip())
        lines.append(f"{idx}. #{rid} {lab_name} {date_text} {time_text}（{status_text_line}）")
        idx += 1

    detail = "\n".join(lines)
    reply = (
        f"你目前共有{total}条预约记录，其中当前有效预约{active_cnt}条。状态分布：{status_text}。"
        f"\n最近{len(lines)}条如下：\n{detail}"
    )
    return _agent_response(code=0, msg="ok", reply=reply, action="reservation_summary", http_status=200)


def _reservation_status_label(status):
    raw = str(status or "").strip()
    mapping = {
        "pending": "待审批",
        "approved": "已通过",
        "rejected": "已拒绝",
        "cancelled": "已取消",
    }
    return mapping.get(raw, raw or "未知状态")


def _is_lab_reservations_query(text):
    raw = str(text or "").strip()
    if not raw:
        return False
    has_reserve_word = any(x in raw for x in ("预约", "预定"))
    has_query_word = any(x in raw for x in ("检查", "查看", "查询", "检索", "统计", "记录", "列表", "所有"))
    has_lab_word = any(x in raw for x in ("实验室", "机房", "教室"))
    has_lab_code = bool(re.search(r"(?<![A-Za-z0-9])[A-Za-z]{1,2}\s*\d{3,4}(?![A-Za-z0-9])", raw))
    if not has_reserve_word or not has_query_word:
        return False
    return has_lab_word or has_lab_code


def _is_cancel_all_reservations_request(text):
    raw = str(text or "").strip()
    if not raw:
        return False
    direct = (
        "取消所有预约",
        "一键取消所有预约",
        "全部取消预约",
        "清空预约",
        "取消全部预约",
    )
    if any(x in raw for x in direct):
        return True
    has_cancel = any(x in raw for x in ("取消", "撤销"))
    has_all = any(x in raw for x in ("所有", "全部", "一键", "全都"))
    has_reserve = any(x in raw for x in ("预约", "预定"))
    return has_cancel and has_all and has_reserve


def _is_cancel_lab_reservations_request(text, lab_name=""):
    raw = str(text or "").strip()
    if not raw:
        return False
    has_cancel = any(x in raw for x in ("取消", "撤销"))
    has_reserve = any(x in raw for x in ("预约", "预定"))
    has_lab_word = any(x in raw for x in ("实验室", "机房", "教室"))
    has_lab_name = bool(str(lab_name or "").strip())
    return has_cancel and has_reserve and (has_lab_word or has_lab_name)


def _is_confirmation_text(text):
    raw = str(text or "").strip().lower()
    if not raw:
        return False
    if any(x in raw for x in ("确认取消所有预约", "确认全部取消", "确定取消所有预约")):
        return True
    return ("确认" in raw or "确定" in raw) and ("所有预约" in raw or "全部预约" in raw)


def _is_cancel_confirmation_text(text):
    raw = str(text or "").strip().lower()
    if not raw:
        return False
    return raw in {"取消", "算了", "不用了", "不", "否", "no", "不用"}


def _extract_reservation_id_from_text(text):
    raw = str(text or "").strip()
    if not raw:
        return None
    patterns = [
        r"(?:#|预约编号|编号|id)\s*(\d{1,9})",
        r"(?<![A-Za-z0-9])(\d{1,9})\s*号?预约",
    ]
    for pat in patterns:
        m = re.search(pat, raw, flags=re.IGNORECASE)
        if not m:
            continue
        try:
            rid = int(m.group(1))
        except Exception:
            rid = 0
        if rid > 0:
            return rid
    if re.fullmatch(r"\d{1,9}", raw):
        try:
            rid = int(raw)
        except Exception:
            rid = 0
        if rid > 0:
            return rid
    return None


def _is_reschedule_request(text):
    raw = str(text or "").strip()
    if not raw:
        return False
    strong_keywords = ("改期", "改时间", "调整到", "延期", "重新安排")
    if any(x in raw for x in strong_keywords):
        return True
    weak_keywords = ("改到", "改成", "改为", "改一下", "调整")
    has_weak = any(x in raw for x in weak_keywords)
    has_reserve_hint = any(x in raw for x in ("预约", "预定", "时段", "时间", "日期", "节次", "#", "编号", "实验室"))
    if has_weak and has_reserve_hint:
        return True
    has_change = any(x in raw for x in ("改", "调整", "挪"))
    has_reserve = any(x in raw for x in ("预约", "预定", "时间"))
    return has_change and has_reserve


def _reschedule_reservation_internal(rid, date, time_range, operator_user="", is_admin=False):
    rid_int = _to_int_or_none(rid)
    date_text = str(date or "").strip()
    time_text = str(time_range or "").strip()
    operator = str(operator_user or "").strip()
    if not rid_int or not date_text or not time_text:
        raise BizError("params error", 400)
    schedule_error = validate_reservation_schedule(date_text, time_text)
    if schedule_error:
        raise BizError(schedule_error, 400)

    def _tx(cur):
        cur.execute(
            """
            SELECT id, lab_name AS labName, user_name AS user, status, date, time
            FROM reservation
            WHERE id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (rid_int,),
        )
        row = cur.fetchone()
        if not row:
            raise BizError("reservation not found", 404)
        if not is_admin and str(row.get("user") or "").strip() != operator:
            raise BizError("forbidden", 403)
        if str(row.get("status") or "").strip() not in ("pending", "approved"):
            raise BizError("invalid status", 400)

        lab_name = str(row.get("labName") or "").strip()
        lock_key = _reservation_lock_key(lab_name, date_text)
        if not _acquire_named_lock(cur, lock_key):
            raise BizError("reservation busy, try again", 409)
        try:
            if has_approved_conflict_with_cur(cur, lab_name, date_text, time_text, exclude_id=rid_int):
                raise BizError("reservation conflict with approved", 409)
            cur.execute(
                """
                UPDATE reservation
                SET date=%s, time=%s, status='pending', reject_reason=''
                WHERE id=%s
                """,
                (date_text, time_text, rid_int),
            )
            if int(cur.rowcount or 0) != 1:
                raise BizError("reservation status changed, retry", 409)
        finally:
            _release_named_lock(cur, lock_key)

        return {
            "id": rid_int,
            "labName": lab_name,
            "oldDate": str(row.get("date") or "").strip(),
            "oldTime": str(row.get("time") or "").strip(),
            "date": date_text,
            "time": time_text,
            "status": "pending",
        }

    return run_in_transaction(_tx)


def _agent_handle_reschedule_request(user_name, role, reservation_id, lab_name, date_text, time_text):
    owner = str(user_name or "").strip()
    if not owner:
        return _agent_response(code=401, msg="unauthorized", reply="登录状态失效，请重新登录。", action="error", http_status=401)

    rid = _to_int_or_none(reservation_id)
    new_date = str(date_text or "").strip()
    new_time = str(time_text or "").strip()
    lab_text = str(lab_name or "").strip()
    is_admin = str(role or "").strip() == "admin"

    if not new_date or not new_time:
        missing = []
        if not new_date:
            missing.append("日期")
        if not new_time:
            missing.append("时段")
        _agent_pending_set(owner, "reschedule", new_date, new_time, extra={"targetReservationId": int(rid or 0), "labName": lab_text})
        reply = f"改期还缺少：{'、'.join(missing)}。例如：把 #12 改到明天 1-2节。"
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    slot_error = _validate_time_with_rule_slots(new_time, get_reservation_rules_payload())
    if slot_error:
        _agent_pending_set(owner, "reschedule", new_date, "", extra={"targetReservationId": int(rid or 0), "labName": lab_text})
        reply = f"时段格式不符合预约规则：{slot_error}。请使用标准时段后重试。"
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    target = None
    if rid:
        rows = query(
            """
            SELECT id, lab_name AS labName, user_name AS user, status, date, time
            FROM reservation
            WHERE id=%s
            LIMIT 1
            """,
            (rid,),
        )
        if not rows:
            return _agent_response(code=0, msg="ok", reply=f"未找到预约 #{rid}。请确认编号后重试。", action="ask_info", http_status=200)
        row = rows[0]
        if not is_admin and str(row.get("user") or "").strip() != owner:
            return _agent_response(code=403, msg="forbidden", reply=f"预约 #{rid} 不属于你，无法改期。", action="error", http_status=403)
        if str(row.get("status") or "").strip() not in ("pending", "approved"):
            status_label = _reservation_status_label(row.get("status"))
            return _agent_response(code=0, msg="ok", reply=f"预约 #{rid} 当前状态为{status_label}，不能改期。", action="ask_info", http_status=200)
        target = row
    else:
        resolved_lab_name = ""
        if lab_text:
            try:
                lab = _resolve_lab_from_agent(lab_name=lab_text)
                resolved_lab_name = str(lab.get("name") or "").strip()
            except BizError as e:
                return _agent_response(code=e.status, msg=e.msg, reply=f"实验室信息有问题：{e.msg}", action="ask_info", http_status=e.status)

        params = [owner]
        where_sql = " WHERE user_name=%s AND status IN ('pending','approved') "
        if resolved_lab_name:
            where_sql += " AND lab_name=%s "
            params.append(resolved_lab_name)
        rows = query(
            f"""
            SELECT id, lab_name AS labName, user_name AS user, status, date, time
            FROM reservation
            {where_sql}
            ORDER BY date DESC, id DESC
            LIMIT 30
            """,
            tuple(params),
        )
        if not rows:
            if resolved_lab_name:
                reply = f"在 {resolved_lab_name} 没有可改期的预约（仅待审批/已通过可改期）。"
            else:
                reply = "你当前没有可改期的预约（仅待审批/已通过可改期）。"
            return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)
        if len(rows) == 1:
            target = rows[0]
        else:
            _agent_pending_set(owner, "reschedule", new_date, new_time, extra={"labName": resolved_lab_name})
            preview = rows[:5]
            lines = []
            for idx, row in enumerate(preview, start=1):
                lines.append(
                    f"{idx}. #{int((row or {}).get('id') or 0)} {str((row or {}).get('labName') or '')} "
                    f"{str((row or {}).get('date') or '')} {str((row or {}).get('time') or '')}（{_reservation_status_label(row.get('status'))}）"
                )
            reply = "找到多条可改期预约，请先指定预约编号（例如：#12）。\n" + "\n".join(lines)
            return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    try:
        updated = _reschedule_reservation_internal(
            rid=target.get("id"),
            date=new_date,
            time_range=new_time,
            operator_user=owner,
            is_admin=False,
        )
    except BizError as e:
        if int(e.status or 0) == 409:
            return _agent_response(code=0, msg="ok", reply="改期失败：新时段有冲突或被占用，请换一个时间。", action="conflict", http_status=200)
        return _agent_response(code=e.status, msg=e.msg, reply=f"改期失败：{e.msg}", action="error", http_status=e.status)

    _agent_pending_clear(owner)
    reply = (
        f"已将预约 #{updated['id']}（{updated['labName']} {updated['oldDate']} {updated['oldTime']}）"
        f"改期为 {updated['date']} {updated['time']}，当前状态已重置为待审批。"
    )
    audit_log(
        "agent.chat.reschedule.success",
        target_type="reservation",
        target_id=updated["id"],
        detail={
            "labName": updated["labName"],
            "oldDate": updated["oldDate"],
            "oldTime": updated["oldTime"],
            "newDate": updated["date"],
            "newTime": updated["time"],
        },
    )
    return _agent_response(code=0, msg="ok", reply=reply, action="reschedule_done", http_status=200)


def _agent_handle_lab_reservations_query(user_name, role, lab_name, date_text="", time_text="", limit=12):
    owner = str(user_name or "").strip()
    if not owner:
        return _agent_response(code=401, msg="unauthorized", reply="登录状态失效，请重新登录。", action="error", http_status=401)
    if not str(lab_name or "").strip():
        return _agent_response(code=0, msg="ok", reply="请先告诉我要查询的实验室，例如：检查 C406 实验室的预约。", action="ask_info", http_status=200)

    try:
        lab = _resolve_lab_from_agent(lab_name=lab_name)
    except BizError as e:
        return _agent_response(code=e.status, msg=e.msg, reply=f"实验室信息有问题：{e.msg}", action="ask_info", http_status=e.status)

    where_sql = " WHERE lab_name=%s "
    params = [str(lab.get("name") or "")]
    is_admin = str(role or "").strip() == "admin"
    if not is_admin:
        where_sql += " AND user_name=%s "
        params.append(owner)
    if str(date_text or "").strip():
        where_sql += " AND date=%s "
        params.append(str(date_text or "").strip())

    rows = query(
        f"""
        SELECT id, lab_name AS labName, user_name AS user, date, time, status, reason
        FROM reservation
        {where_sql}
        ORDER BY date DESC, id DESC
        LIMIT %s
        """,
        tuple(params + [max(1, int(limit))]),
    )

    target_slots = parse_slots(time_text) if str(time_text or "").strip() else set()
    if str(time_text or "").strip() and not target_slots:
        return _agent_response(code=0, msg="ok", reply="时段格式不正确，请用例如 1-2节 或 08:00-08:40,08:45-09:35。", action="ask_info", http_status=200)

    filtered = []
    for row in rows:
        if target_slots:
            row_slots = parse_slots(row.get("time"))
            if not row_slots or not (target_slots & row_slots):
                continue
        filtered.append(row)

    if not filtered:
        if is_admin:
            reply = f"{lab.get('name')} 当前没有匹配的预约记录。"
        else:
            reply = f"{lab.get('name')} 当前没有你名下的匹配预约记录。"
        return _agent_response(code=0, msg="ok", reply=reply, action="lab_reservation_list", http_status=200)

    status_counter = {}
    for row in filtered:
        key = str((row or {}).get("status") or "").strip()
        if not key:
            continue
        status_counter[key] = int(status_counter.get(key) or 0) + 1

    ordered_status = ["pending", "approved", "rejected", "cancelled"]
    status_parts = []
    for key in ordered_status:
        cnt = int(status_counter.get(key) or 0)
        if cnt > 0:
            status_parts.append(f"{_reservation_status_label(key)}{cnt}条")
    for key, cnt in status_counter.items():
        if key in ordered_status:
            continue
        n = int(cnt or 0)
        if n > 0:
            status_parts.append(f"{key}{n}条")
    status_text = "，".join(status_parts) if status_parts else "暂无状态统计"

    lines = []
    for idx, row in enumerate(filtered[:10], start=1):
        rid = int((row or {}).get("id") or 0)
        user_text = str((row or {}).get("user") or "").strip()
        date_row = str((row or {}).get("date") or "").strip()
        time_row = str((row or {}).get("time") or "").strip()
        status_row = _reservation_status_label((row or {}).get("status"))
        if is_admin:
            lines.append(f"{idx}. #{rid} {date_row} {time_row}（{status_row}，用户：{user_text}）")
        else:
            lines.append(f"{idx}. #{rid} {date_row} {time_row}（{status_row}）")

    header = f"{lab.get('name')} 预约记录共{len(filtered)}条，状态分布：{status_text}。"
    if not is_admin:
        header += "（当前账号仅显示你自己的预约）"
    reply = header + "\n最近记录：\n" + "\n".join(lines)
    return _agent_response(code=0, msg="ok", reply=reply, action="lab_reservation_list", http_status=200)


def _agent_handle_cancel_lab_reservations(user_name, lab_name, date_text="", time_text=""):
    owner = str(user_name or "").strip()
    if not owner:
        return _agent_response(code=401, msg="unauthorized", reply="登录状态失效，请重新登录。", action="error", http_status=401)
    if not str(lab_name or "").strip():
        return _agent_response(code=0, msg="ok", reply="请先说明要取消哪个实验室的预约，例如：取消 C406 的预约。", action="ask_info", http_status=200)

    try:
        lab = _resolve_lab_from_agent(lab_name=lab_name)
    except BizError as e:
        return _agent_response(code=e.status, msg=e.msg, reply=f"实验室信息有问题：{e.msg}", action="ask_info", http_status=e.status)

    params = [owner, str(lab.get("name") or "")]
    where_sql = " WHERE user_name=%s AND lab_name=%s AND status IN ('pending','approved') "
    if str(date_text or "").strip():
        where_sql += " AND date=%s "
        params.append(str(date_text or "").strip())

    rows = query(
        f"""
        SELECT id, date, time, status
        FROM reservation
        {where_sql}
        ORDER BY date DESC, id DESC
        LIMIT 300
        """,
        tuple(params),
    )

    slot_filter = parse_slots(time_text) if str(time_text or "").strip() else set()
    if str(time_text or "").strip() and not slot_filter:
        return _agent_response(code=0, msg="ok", reply="时段格式不正确，请用例如 1-2节 或 08:00-08:40,08:45-09:35。", action="ask_info", http_status=200)

    target_rows = []
    for row in rows:
        if slot_filter:
            row_slots = parse_slots(row.get("time"))
            if not row_slots or not (slot_filter & row_slots):
                continue
        target_rows.append(row)

    if not target_rows:
        return _agent_response(
            code=0,
            msg="ok",
            reply=f"在 {lab.get('name')} 没有找到可取消的预约（仅可取消待审批/已通过）。",
            action="cancel_done",
            http_status=200,
        )

    ids = [int((x or {}).get("id") or 0) for x in target_rows if int((x or {}).get("id") or 0) > 0]
    if not ids:
        return _agent_response(code=0, msg="ok", reply="没有可取消的预约。", action="cancel_done", http_status=200)

    placeholders = ",".join(["%s"] * len(ids))

    def _tx(cur):
        cur.execute(f"UPDATE reservation SET status='cancelled' WHERE id IN ({placeholders})", ids)
        return int(cur.rowcount or 0)

    affected = int(run_in_transaction(_tx) or 0)
    audit_log(
        "agent.chat.cancel.lab",
        target_type="reservation",
        detail={"labName": str(lab.get("name") or ""), "date": str(date_text or ""), "time": str(time_text or ""), "count": affected},
    )

    preview_count = len(target_rows) if affected <= 0 else min(int(affected), len(target_rows))
    preview = target_rows[: min(5, preview_count)]
    lines = [f"{idx}. #{int((r or {}).get('id') or 0)} {str((r or {}).get('date') or '')} {str((r or {}).get('time') or '')}" for idx, r in enumerate(preview, start=1)]
    extra = "\n".join(lines)
    reply = f"已取消 {lab.get('name')} 的{affected}条预约。"
    if extra:
        reply += f"\n已取消记录（最多展示5条）：\n{extra}"
    return _agent_response(code=0, msg="ok", reply=reply, action="cancel_done", http_status=200)


def _agent_prepare_cancel_all(user_name):
    owner = str(user_name or "").strip()
    if not owner:
        return _agent_response(code=401, msg="unauthorized", reply="登录状态失效，请重新登录。", action="error", http_status=401)
    rows = query(
        """
        SELECT COUNT(*) AS cnt
        FROM reservation
        WHERE user_name=%s AND status IN ('pending','approved')
        """,
        (owner,),
    )
    cnt = int((rows[0] or {}).get("cnt") or 0) if rows else 0
    if cnt <= 0:
        return _agent_response(code=0, msg="ok", reply="你当前没有可取消的预约（仅待审批/已通过可取消）。", action="cancel_done", http_status=200)

    _agent_pending_set(user_name, "cancel_all_confirm", extra={"pendingCancelCount": cnt})
    reply = f"将为你取消全部预约（共{cnt}条，可取消状态：待审批/已通过）。请回复“确认取消所有预约”继续，或回复“算了”放弃。"
    return _agent_response(code=0, msg="ok", reply=reply, action="ask_confirm", http_status=200)


def _agent_execute_cancel_all(user_name):
    owner = str(user_name or "").strip()
    if not owner:
        return _agent_response(code=401, msg="unauthorized", reply="登录状态失效，请重新登录。", action="error", http_status=401)

    def _tx(cur):
        cur.execute(
            """
            UPDATE reservation
            SET status='cancelled'
            WHERE user_name=%s AND status IN ('pending','approved')
            """,
            (owner,),
        )
        return int(cur.rowcount or 0)

    affected = int(run_in_transaction(_tx) or 0)
    _agent_pending_clear(user_name)
    audit_log(
        "agent.chat.cancel.all",
        target_type="reservation",
        detail={"count": affected},
    )
    reply = f"已为你一键取消{affected}条预约。"
    return _agent_response(code=0, msg="ok", reply=reply, action="cancel_all_done", http_status=200)


def _is_lab_availability_query(text):
    raw = str(text or "").strip()
    if not raw:
        return False
    lower = raw.lower()
    has_lab_word = ("lab" in lower) or any(x in raw for x in ("实验室", "机房", "教室"))
    if not has_lab_word:
        return False
    has_free_word = any(x in raw for x in ("空闲", "有空", "空着", "可用", "可预约", "空余"))
    has_query_word = any(x in raw for x in ("哪些", "哪个", "哪间", "有哪", "有哪些"))
    return has_free_word or has_query_word


def _find_available_labs(date_text, time_range, limit=12):
    date_str = str(date_text or "").strip()
    time_str = str(time_range or "").strip()
    slots = parse_slots(time_str)
    if not date_str or not slots:
        return []

    all_labs = query("SELECT id, name FROM lab ORDER BY id ASC")
    if not all_labs:
        return []

    occupied_rows = query(
        """
        SELECT lab_id AS labId, lab_name AS labName, time
        FROM reservation
        WHERE date=%s AND status='approved'
        """,
        (date_str,),
    )

    occupied_ids = set()
    occupied_names = set()
    for row in occupied_rows:
        row_slots = parse_slots(row.get("time"))
        if not row_slots or not (slots & row_slots):
            continue
        rid = _to_int_or_none(row.get("labId"))
        if rid is not None:
            occupied_ids.add(int(rid))
        rname = str(row.get("labName") or "").strip()
        if rname:
            occupied_names.add(rname)

    available = []
    for lab in all_labs:
        lid = _to_int_or_none(lab.get("id"))
        lname = str(lab.get("name") or "").strip()
        if not lname:
            continue
        if (lid is not None and lid in occupied_ids) or (lname in occupied_names):
            continue
        available.append({"id": lid, "name": lname})

    if limit and len(available) > int(limit):
        return available[: int(limit)]
    return available


def _agent_pending_key(user_name):
    return str(user_name or "").strip().lower()


def _agent_pending_get(user_name):
    key = _agent_pending_key(user_name)
    if not key:
        return {}
    now_ts = int(time.time())
    with _AGENT_PENDING_LOCK:
        row = _AGENT_PENDING_CONTEXT.get(key)
        if not row:
            return {}
        expires_at = int(row.get("expiresAt") or 0)
        if expires_at and expires_at <= now_ts:
            _AGENT_PENDING_CONTEXT.pop(key, None)
            return {}
        return dict(row)


def _agent_pending_set(user_name, intent, date_text="", time_text="", extra=None):
    key = _agent_pending_key(user_name)
    if not key:
        return
    now_ts = int(time.time())
    payload = {
        "intent": str(intent or "").strip(),
        "date": str(date_text or "").strip(),
        "time": str(time_text or "").strip(),
        "updatedAt": now_ts,
        "expiresAt": now_ts + max(60, int(AGENT_PENDING_TTL_SECONDS)),
    }
    if isinstance(extra, dict):
        for k, v in extra.items():
            if not str(k or "").strip():
                continue
            payload[str(k)] = v
    with _AGENT_PENDING_LOCK:
        _AGENT_PENDING_CONTEXT[key] = payload


def _agent_pending_clear(user_name):
    key = _agent_pending_key(user_name)
    if not key:
        return
    with _AGENT_PENDING_LOCK:
        _AGENT_PENDING_CONTEXT.pop(key, None)


def _agent_handle_availability_query(user_name, date_text, time_text, rule_payload):
    date_str = str(date_text or "").strip()
    time_str = str(time_text or "").strip()

    if not date_str or not time_str:
        _agent_pending_set(user_name, "availability", date_str, time_str)
        missing = []
        if not date_str:
            missing.append("日期")
        if not time_str:
            missing.append("时段")
        reply = f"查询空闲实验室还缺少：{'、'.join(missing)}。例如：明天 1-2节 有哪些实验室空闲。"
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    slot_error = _validate_time_with_rule_slots(time_str, rule_payload)
    if slot_error:
        _agent_pending_set(user_name, "availability", date_str, "")
        reply = f"时段格式不符合预约规则：{slot_error}。请使用标准时段后重试。"
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    schedule_error = validate_reservation_schedule(date_str, time_str)
    if schedule_error:
        _agent_pending_set(user_name, "availability", "", time_str)
        reply = f"查询时间不合法：{schedule_error}。请调整日期或时段。"
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    available_labs = _find_available_labs(date_str, time_str, limit=0)
    _agent_pending_clear(user_name)
    if not available_labs:
        reply = f"{date_str} {time_str} 暂无空闲实验室。"
        return _agent_response(code=0, msg="ok", reply=reply, action="availability_empty", http_status=200)

    show_items = available_labs[:12]
    lab_names = "、".join([str(x.get("name") or "") for x in show_items if str(x.get("name") or "").strip()])
    if len(available_labs) > len(show_items):
        reply = f"{date_str} {time_str} 空闲实验室：{lab_names}（共{len(available_labs)}间，已展示前{len(show_items)}间）。"
    else:
        reply = f"{date_str} {time_str} 空闲实验室：{lab_names}。"
    return _agent_response(code=0, msg="ok", reply=reply, action="availability", http_status=200)


def _validate_time_with_rule_slots(time_range, rule_payload):
    slots = parse_slots(time_range)
    if not slots:
        return "time required"
    allowed_slots = set(_resolve_rule_slots(rule_payload))
    invalid = sorted([s for s in slots if s not in allowed_slots])
    if invalid:
        return f"time slots not allowed: {','.join(invalid)}"
    return ""


def _resolve_lab_from_agent(lab_id=None, lab_name=""):
    lab_id = _to_int_or_none(lab_id)
    name = str(lab_name or "").strip()

    if lab_id:
        rows = query("SELECT id, name FROM lab WHERE id=%s LIMIT 1", (lab_id,))
        if not rows:
            raise BizError("lab not found", 404)
        return rows[0]

    if not name:
        raise BizError("missing lab info", 400)

    exact = query("SELECT id, name FROM lab WHERE name=%s LIMIT 1", (name,))
    if exact:
        return exact[0]

    fuzzy = query(
        """
        SELECT id, name
        FROM lab
        WHERE name LIKE %s
        ORDER BY id ASC
        LIMIT 5
        """,
        (f"%{name}%",),
    )
    if not fuzzy:
        raise BizError("lab not found", 404)
    if len(fuzzy) > 1:
        options = "、".join([str(x.get("name") or "") for x in fuzzy if x.get("name")])
        raise BizError(f"lab ambiguous, candidates: {options}", 400)
    return fuzzy[0]


def _call_siliconflow_chat(messages, temperature=0.1):
    if not SILICONFLOW_API_KEY:
        raise BizError("SILICONFLOW_API_KEY not configured", 500)

    payload = {
        "model": SILICONFLOW_MODEL,
        "messages": messages,
        "temperature": float(temperature),
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(
        f"{SILICONFLOW_BASE_URL}/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        },
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=max(3, int(SILICONFLOW_TIMEOUT_SECONDS))) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="ignore")
        except Exception:
            detail = ""
        raise BizError(f"llm http error: {e.code} {detail[:200]}", 502)
    except URLError as e:
        raise BizError(f"llm connect error: {e}", 502)
    except Exception as e:
        raise BizError(f"llm request failed: {e}", 502)

    try:
        api_result = json.loads(raw)
    except Exception:
        raise BizError("llm response is not json", 502)

    content = ""
    try:
        choices = api_result.get("choices") or []
        content = str((((choices[0] or {}).get("message") or {}).get("content")) or "")
    except Exception:
        content = ""
    if not content:
        raise BizError("llm empty response", 502)
    return content


def _call_siliconflow_to_parse(text, rule_payload):
    rule_slots = _resolve_rule_slots(rule_payload)
    slot_text = ", ".join(rule_slots)
    system_prompt = (
        "你是实验室预约参数解析器。"
        "请把用户输入解析为严格JSON，不要输出JSON以外任何字符。"
        "JSON字段固定为: intent, lab_id, lab_name, date, time, reason, missing。"
        "intent只允许 reserve 或 ask。"
        "date格式必须是YYYY-MM-DD。"
        "time格式必须是一个或多个时段，用英文逗号分隔，每个时段是HH:MM-HH:MM。"
        f"节次映射如下: {PERIOD_MAPPING_TEXT}。"
        "若用户说第X节、X-Y节、12两节、9.10两节，请按映射转换成time字段。"
        f"可用时段仅限: {slot_text}。"
        "若信息不足，intent输出ask，并在missing中给出缺失字段数组。"
    )

    content = _call_siliconflow_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": str(text or "")},
        ],
        temperature=0.1,
    )

    try:
        parsed = json.loads(content)
    except Exception:
        extracted = _extract_json_object(content)
        if not extracted:
            raise BizError("llm output parse failed", 502)
        try:
            parsed = json.loads(extracted)
        except Exception:
            raise BizError("llm output parse failed", 502)

    if not isinstance(parsed, dict):
        raise BizError("llm output not object", 502)

    return {
        "intent": str(parsed.get("intent") or "").strip().lower() or "ask",
        "labId": _to_int_or_none(parsed.get("lab_id")),
        "labName": str(parsed.get("lab_name") or parsed.get("lab") or "").strip(),
        "date": str(parsed.get("date") or "").strip(),
        "time": _normalize_agent_time(parsed.get("time")),
        "reason": str(parsed.get("reason") or "").strip(),
        "missing": parsed.get("missing") if isinstance(parsed.get("missing"), list) else [],
        "raw": parsed,
    }


def _call_siliconflow_general_reply(text):
    system_prompt = (
        "你是一个中文智能助手，运行在高校实验室管理系统中。"
        "除预约相关外，普通问题（学习、常识、安全、工具使用）也要直接回答，不要只回复模板话术。"
        "禁止输出“您好我是助手”等固定开场，不要反问用户需要哪类帮助。"
        "用户提问时请给出可执行、简洁、准确的回答。"
        "若涉及安全、消防、急救，优先强调确保人身安全、及时报警并联系现场管理人员。"
        "不要编造你已经完成了系统操作。"
    )
    content = _call_siliconflow_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": str(text or "")},
        ],
        temperature=0.3,
    )
    return str(content or "").strip()


def _looks_like_reservation_request(text, parsed=None, fallback_date="", fallback_time="", fallback_lab=""):
    raw = str(text or "").strip()
    if not raw:
        return False

    info = parsed or {}
    intent = str(info.get("intent") or "").strip().lower()
    if intent == "reserve":
        return True

    date_text = str(info.get("date") or "").strip() or str(fallback_date or "").strip()
    time_text = str(info.get("time") or "").strip() or str(fallback_time or "").strip()
    has_lab = bool(info.get("labId")) or bool(str(info.get("labName") or "").strip()) or bool(str(fallback_lab or "").strip())
    if date_text and time_text and has_lab:
        return True

    has_reserve_keyword = any(
        k in raw for k in ("预约", "预定", "订", "申请", "借用", "借", "安排")
    )
    has_lab_keyword = any(k in raw for k in ("实验室", "机房", "教室", "lab"))
    has_period_expr = bool(
        re.search(
            r"第?\s*[0-9一二三四五六七八九十两]+\s*(?:[-到至~～]\s*第?\s*[0-9一二三四五六七八九十两]+)?\s*节",
            raw,
        )
    )

    if has_reserve_keyword and (has_lab_keyword or has_lab or date_text or time_text or has_period_expr):
        return True
    if has_period_expr and (has_lab_keyword or has_lab or "在" in raw):
        return True
    return False


def _agent_response(code=0, msg="ok", reply="", action="reply", reservation=None, extra=None, http_status=200):
    data = {"reply": str(reply or ""), "action": str(action or "reply")}
    if reservation is not None:
        data["reservation"] = reservation
    if isinstance(extra, dict):
        for k, v in extra.items():
            key = str(k or "").strip()
            if not key:
                continue
            data[key] = v
    return jsonify({"code": int(code), "msg": str(msg or ""), "data": data}), int(http_status)


def _agent_general_response(text):
    try:
        reply = _call_siliconflow_general_reply(text)
    except BizError as e:
        if str(e.msg or "").strip() == "SILICONFLOW_API_KEY not configured":
            return _agent_response(
                code=0,
                msg="ok",
                reply="管理员未配置 AI 密钥（SILICONFLOW_API_KEY），当前无法使用智能助手。请先在后端 lab-api/.env 中配置后重启服务。",
                action="error",
                http_status=200,
            )
        return _agent_response(
            code=e.status,
            msg=e.msg,
            reply="智能助手暂时不可用，请稍后重试。",
            action="error",
            http_status=e.status,
        )
    if not reply:
        reply = "我在。你可以继续问我实验室、课程或安全相关问题。"
    return _agent_response(code=0, msg="ok", reply=reply, action="reply", http_status=200)


def _agent_handle_reserve_create(
    user_name,
    text,
    rule_payload,
    fallback_date_text="",
    period_time_text="",
    fallback_lab_name="",
    force_reservation=False,
):
    try:
        parsed = _call_siliconflow_to_parse(text, rule_payload)
    except BizError as e:
        print(f"[warn] agent parse fallback used: {e.msg}")
        parsed = {
            "intent": "reserve",
            "labId": None,
            "labName": fallback_lab_name,
            "date": fallback_date_text,
            "time": period_time_text,
            "reason": "",
            "missing": [],
            "raw": {"fallback": True, "error": str(e.msg or "")},
        }

    intent = parsed.get("intent") or "ask"
    date_text = str(parsed.get("date") or "").strip()
    time_text = str(parsed.get("time") or "").strip()
    reason = str(parsed.get("reason") or "").strip()
    lab_id = parsed.get("labId")
    lab_name = parsed.get("labName") or ""
    missing = _normalize_agent_missing_fields(parsed.get("missing") or [])

    if fallback_date_text:
        date_text = fallback_date_text
    if fallback_lab_name:
        lab_id = None
        lab_name = fallback_lab_name
    elif not lab_id:
        # Do not trust inferred lab names when user text does not explicitly mention one.
        lab_name = ""
    if period_time_text:
        fallback_slot_error = _validate_time_with_rule_slots(period_time_text, rule_payload)
        if not fallback_slot_error:
            time_text = period_time_text

    if not force_reservation:
        is_reservation_request = _looks_like_reservation_request(
            text=text,
            parsed={"intent": intent, "labId": lab_id, "labName": lab_name, "date": date_text, "time": time_text},
            fallback_date=fallback_date_text,
            fallback_time=period_time_text,
            fallback_lab=fallback_lab_name,
        )
        if not is_reservation_request:
            return _agent_general_response(text)

    if intent != "reserve":
        intent = "reserve"

    if not date_text:
        missing.append("date")
    if not time_text:
        missing.append("time")
    if not lab_id and not str(lab_name).strip():
        missing.append("lab")
    if date_text:
        missing = [x for x in missing if str(x).strip().lower() != "date"]
    if time_text:
        missing = [x for x in missing if str(x).strip().lower() != "time"]
    if lab_id or str(lab_name).strip():
        missing = [x for x in missing if str(x).strip().lower() != "lab"]

    if missing:
        missing_fields = []
        seen_missing = set()
        for x in missing:
            key = str(x or "").strip().lower()
            if not key or key in seen_missing:
                continue
            seen_missing.add(key)
            missing_fields.append(key)
        field_label = {"date": "日期", "time": "时段", "lab": "实验室"}
        missing_names = [field_label.get(x, x) for x in missing_fields]
        reply = f"还缺少预约信息：{', '.join(missing_names)}。请补充后我再为你提交预约。"
        _agent_pending_set(
            user_name,
            "reserve_create",
            date_text,
            time_text,
            extra={"labName": str(lab_name or "").strip(), "reason": str(reason or "").strip()},
        )
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    slot_error = _validate_time_with_rule_slots(time_text, rule_payload)
    if slot_error:
        reply = f"时段格式不符合预约规则：{slot_error}。请使用标准时段，或直接说第1节/1-2节/9.10两节后重试。"
        _agent_pending_set(
            user_name,
            "reserve_create",
            date_text,
            "",
            extra={"labName": str(lab_name or "").strip(), "reason": str(reason or "").strip()},
        )
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    schedule_error = validate_reservation_schedule(date_text, time_text)
    if schedule_error:
        reply = f"预约时间不合法：{schedule_error}。请调整日期或时段。"
        _agent_pending_set(
            user_name,
            "reserve_create",
            "",
            time_text,
            extra={"labName": str(lab_name or "").strip(), "reason": str(reason or "").strip()},
        )
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    try:
        lab = _resolve_lab_from_agent(lab_id=lab_id, lab_name=lab_name)
    except BizError as e:
        _agent_pending_set(
            user_name,
            "reserve_create",
            date_text,
            time_text,
            extra={"labName": str(lab_name or "").strip(), "reason": str(reason or "").strip()},
        )
        return _agent_response(code=e.status, msg=e.msg, reply=f"实验室信息有问题：{e.msg}", action="ask_info", http_status=e.status)

    try:
        # create_reservation_internal is defined in routes_b after module split;
        # import lazily to avoid circular import issues during bootstrap.
        from . import routes_b as _routes_b

        created = _routes_b.create_reservation_internal(
            user_name=user_name,
            lab_id=lab.get("id"),
            lab_name=lab.get("name"),
            date=date_text,
            time_range=time_text,
            reason=reason or "智能助手自动预约",
        )
    except BizError as e:
        if int(e.status) == 409:
            reply = "该时段已冲突或被占用，请换一个时段，我可以继续帮你提交。"
            return _agent_response(code=0, msg="ok", reply=reply, action="conflict", http_status=200)
        return _agent_response(code=e.status, msg=e.msg, reply=f"预约失败：{e.msg}", action="error", http_status=e.status)

    reply = f"已为你提交预约：{created['labName']}，{created['date']} {created['time']}，当前状态为待审批。"
    _agent_pending_clear(user_name)
    audit_log(
        "agent.chat.reserve.success",
        target_type="reservation",
        target_id=created["id"],
        detail={
            "source": "agent",
            "labId": created["labId"],
            "labName": created["labName"],
            "date": created["date"],
            "time": created["time"],
        },
    )
    return _agent_response(
        code=0,
        msg="ok",
        reply=reply,
        action="reserve_created",
        reservation={
            "id": created["id"],
            "labId": created["labId"],
            "labName": created["labName"],
            "date": created["date"],
            "time": created["time"],
            "status": created["status"],
        },
        http_status=200,
    )


def _agent_translate_intent(text, pending_ctx, fallback_date_text="", period_time_text="", fallback_lab_name=""):
    raw = str(text or "").strip()
    pending_intent = str((pending_ctx or {}).get("intent") or "").strip()
    reservation_id = _extract_reservation_id_from_text(raw)
    coarse_reservation_request = _looks_like_reservation_request(
        text=raw,
        parsed=None,
        fallback_date=fallback_date_text,
        fallback_time=period_time_text,
        fallback_lab=fallback_lab_name,
    )

    result = {
        "op": "",
        "labName": str(fallback_lab_name or "").strip(),
        "date": str(fallback_date_text or "").strip(),
        "time": str(period_time_text or "").strip(),
        "reservationId": int(reservation_id or 0),
        "nickname": "",
        "clearCancelPending": False,
    }

    if pending_intent == "cancel_all_confirm":
        if _is_confirmation_text(raw):
            result["op"] = "cancel_all_confirm"
            return result
        if _is_cancel_confirmation_text(raw):
            result["op"] = "cancel_all_abort"
            return result
        result["clearCancelPending"] = True

    if _is_cancel_all_reservations_request(raw):
        result["op"] = "cancel_all_prepare"
        return result
    nickname = _extract_nickname_from_text(raw)
    if nickname:
        result["op"] = "update_profile"
        result["nickname"] = nickname
        return result
    if _is_reschedule_request(raw):
        result["op"] = "reschedule"
        return result
    if _is_my_reservations_query(raw):
        result["op"] = "reservation_summary"
        return result
    if _is_lab_reservations_query(raw):
        result["op"] = "lab_reservation_list"
        return result
    if _is_cancel_lab_reservations_request(raw, result["labName"]):
        result["op"] = "cancel_lab"
        return result
    if _is_lab_availability_query(raw):
        result["op"] = "availability"
        return result

    if pending_intent == "availability":
        has_followup_info = bool(result["date"] or result["time"])
        if has_followup_info and not coarse_reservation_request:
            result["op"] = "availability"
            result["date"] = result["date"] or str((pending_ctx or {}).get("date") or "").strip()
            result["time"] = result["time"] or str((pending_ctx or {}).get("time") or "").strip()
            return result
    if pending_intent == "reschedule":
        has_followup_info = bool(result["date"] or result["time"] or result["reservationId"] or result["labName"])
        should_apply_pending = has_followup_info and (not coarse_reservation_request or int(result["reservationId"] or 0) > 0)
        if should_apply_pending:
            result["op"] = "reschedule"
            result["date"] = result["date"] or str((pending_ctx or {}).get("date") or "").strip()
            result["time"] = result["time"] or str((pending_ctx or {}).get("time") or "").strip()
            if int(result["reservationId"] or 0) <= 0:
                result["reservationId"] = int((pending_ctx or {}).get("targetReservationId") or 0)
            if not result["labName"]:
                result["labName"] = str((pending_ctx or {}).get("labName") or "").strip()
            return result
    if pending_intent == "reserve_create":
        has_followup_info = bool(result["date"] or result["time"] or result["labName"])
        if has_followup_info:
            result["op"] = "reserve_create"
            result["date"] = result["date"] or str((pending_ctx or {}).get("date") or "").strip()
            result["time"] = result["time"] or str((pending_ctx or {}).get("time") or "").strip()
            if not result["labName"]:
                result["labName"] = str((pending_ctx or {}).get("labName") or "").strip()
            return result

    if coarse_reservation_request:
        result["op"] = "reserve_create"
    else:
        result["op"] = "general_reply"
    return result


def _agent_execute_tool(tool_call, user_name, current_role, text, rule_payload):
    op = str((tool_call or {}).get("op") or "").strip()
    if op not in AGENT_TOOL_WHITELIST:
        op = "general_reply"
    if bool((tool_call or {}).get("clearCancelPending")):
        _agent_pending_clear(user_name)

    if op == "reservation_summary":
        return _agent_handle_my_reservations_query(user_name=user_name, limit=5)
    if op == "lab_reservation_list":
        return _agent_handle_lab_reservations_query(
            user_name=user_name,
            role=current_role,
            lab_name=str((tool_call or {}).get("labName") or "").strip(),
            date_text=str((tool_call or {}).get("date") or "").strip(),
            time_text=str((tool_call or {}).get("time") or "").strip(),
            limit=20,
        )
    if op == "cancel_lab":
        return _agent_handle_cancel_lab_reservations(
            user_name=user_name,
            lab_name=str((tool_call or {}).get("labName") or "").strip(),
            date_text=str((tool_call or {}).get("date") or "").strip(),
            time_text=str((tool_call or {}).get("time") or "").strip(),
        )
    if op == "reschedule":
        return _agent_handle_reschedule_request(
            user_name=user_name,
            role=current_role,
            reservation_id=_to_int_or_none((tool_call or {}).get("reservationId")),
            lab_name=str((tool_call or {}).get("labName") or "").strip(),
            date_text=str((tool_call or {}).get("date") or "").strip(),
            time_text=str((tool_call or {}).get("time") or "").strip(),
        )
    if op == "cancel_all_prepare":
        return _agent_prepare_cancel_all(user_name=user_name)
    if op == "cancel_all_confirm":
        return _agent_execute_cancel_all(user_name=user_name)
    if op == "cancel_all_abort":
        _agent_pending_clear(user_name)
        return _agent_response(code=0, msg="ok", reply="已取消本次一键取消操作。", action="cancel_aborted", http_status=200)
    if op == "update_profile":
        nickname = str((tool_call or {}).get("nickname") or "").strip()
        if not nickname:
            return _agent_response(
                code=0,
                msg="ok",
                reply="请告诉我要改成的昵称，例如：把昵称改成大帅比。",
                action="ask_info",
                http_status=200,
            )
        return _agent_response(
            code=0,
            msg="ok",
            reply=f"已帮你把昵称改成“{nickname}”。",
            action="update_profile",
            extra={"profile": {"nickname": nickname}},
            http_status=200,
        )
    if op == "availability":
        return _agent_handle_availability_query(
            user_name=user_name,
            date_text=str((tool_call or {}).get("date") or "").strip(),
            time_text=str((tool_call or {}).get("time") or "").strip(),
            rule_payload=rule_payload,
        )
    if op == "reserve_create":
        return _agent_handle_reserve_create(
            user_name=user_name,
            text=text,
            rule_payload=rule_payload,
            fallback_date_text=str((tool_call or {}).get("date") or "").strip(),
            period_time_text=str((tool_call or {}).get("time") or "").strip(),
            fallback_lab_name=str((tool_call or {}).get("labName") or "").strip(),
            force_reservation=True,
        )
    return _agent_general_response(text)


try:
    ensure_user_password_column()
except Exception as e:
    print(f"[warn] ensure_user_password_column failed: {e}")

try:
    ensure_auth_refresh_table()
except Exception as e:
    print(f"[warn] ensure_auth_refresh_table failed: {e}")

try:
    ensure_audit_log_table()
except Exception as e:
    print(f"[warn] ensure_audit_log_table failed: {e}")

try:
    ensure_announcement_table()
except Exception as e:
    print(f"[warn] ensure_announcement_table failed: {e}")

try:
    ensure_lost_found_claim_columns()
except Exception as e:
    print(f"[warn] ensure_lost_found_claim_columns failed: {e}")


