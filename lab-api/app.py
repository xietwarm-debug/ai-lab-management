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
from collections import deque
from threading import Lock
from functools import wraps
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from flask import g
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(__file__)


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
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
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


def _call_siliconflow_to_parse(text, rule_payload):
    if not SILICONFLOW_API_KEY:
        raise BizError("SILICONFLOW_API_KEY not configured", 500)

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

    payload = {
        "model": SILICONFLOW_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": str(text or "")},
        ],
        "temperature": 0.1,
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


def _agent_response(code=0, msg="ok", reply="", action="reply", reservation=None, http_status=200):
    data = {"reply": str(reply or ""), "action": str(action or "reply")}
    if reservation is not None:
        data["reservation"] = reservation
    return jsonify({"code": int(code), "msg": str(msg or ""), "data": data}), int(http_status)


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


@app.get("/health")
def health():
    return jsonify({"ok": True, "time": datetime.now().isoformat(timespec="seconds")})


@app.get("/reservation-rules")
@auth_required()
def reservation_rules():
    return jsonify({"ok": True, "data": get_reservation_rules_payload()})


@app.get("/ai/recommend-slots")
@auth_required()
def ai_recommend_slots():
    try:
        lab_id = _to_int_or_none(request.args.get("lab_id"))
        days = _to_int_or_none(request.args.get("days"))
        k = _to_int_or_none(request.args.get("k"))

        if not lab_id or lab_id <= 0:
            raise BizError("lab_id required", 400)

        days = int(days or 14)
        k = int(k or 3)
        days = max(1, min(days, 60))
        k = max(1, min(k, 20))

        user_name = (g.current_user.get("username") or "").strip()
        if not user_name:
            raise BizError("unauthorized", 401)

        lab_rows = query("SELECT id, name FROM lab WHERE id=%s LIMIT 1", (lab_id,))
        if not lab_rows:
            raise BizError("lab not found", 404)
        lab_name = (lab_rows[0].get("name") or "").strip()
        if not lab_name:
            raise BizError("lab not found", 404)

        rule_payload = get_reservation_rules_payload()
        candidate_slots = _resolve_rule_slots(rule_payload)
        if not candidate_slots:
            raise BizError("no available rule slots", 409)
        candidate_windows = _build_recommend_time_windows(candidate_slots)
        if not candidate_windows:
            raise BizError("no candidate windows", 409)

        user_rows = query(
            """
            SELECT time
            FROM reservation
            WHERE user_name=%s AND status<>'cancelled'
            """,
            (user_name,),
        )
        global_rows = query(
            """
            SELECT time
            FROM reservation
            WHERE lab_id=%s AND status<>'cancelled'
            """,
            (lab_id,),
        )

        user_freq, user_max = _count_slot_frequency(user_rows)
        global_freq, global_max = _count_slot_frequency(global_rows)

        base_date = datetime.now().date()
        picked = []

        for offset in range(days):
            date_text = (base_date + timedelta(days=offset)).strftime("%Y-%m-%d")
            for window in candidate_windows:
                time_range = window["time"]
                schedule_error = validate_reservation_schedule(date_text, time_range)
                if schedule_error:
                    continue
                if has_approved_conflict(lab_name, date_text, time_range):
                    continue

                slot_items = window.get("slots") or []
                if not slot_items:
                    continue
                user_score = sum((float(user_freq.get(s) or 0) / float(user_max)) if user_max > 0 else 0.0 for s in slot_items) / len(slot_items)
                global_score = sum((float(global_freq.get(s) or 0) / float(global_max)) if global_max > 0 else 0.0 for s in slot_items) / len(slot_items)
                score = 0.7 * user_score + 0.3 * global_score

                picked.append(
                    {
                        "date": date_text,
                        "time": time_range,
                        "scoreRaw": score,
                        "sortStart": int(window.get("firstStart") or 0),
                        "reason": "双节连排推荐（基于历史预约偏好与实验室热度）",
                    }
                )

        picked.sort(key=lambda x: (-x["scoreRaw"], x["date"], x["sortStart"], x["time"]))

        recommendations = []
        for row in picked[:k]:
            recommendations.append(
                {
                    "date": row["date"],
                    "time": row["time"],
                    "score": round(float(row["scoreRaw"]), 4),
                    "reason": row["reason"],
                }
            )

        return jsonify({"code": 0, "data": {"recommendations": recommendations}, "msg": "ok"})
    except BizError as e:
        return jsonify({"code": int(e.status or 1), "data": {"recommendations": []}, "msg": e.msg}), e.status
    except Exception:
        return jsonify({"code": 500, "data": {"recommendations": []}, "msg": "internal error"}), 500


@app.post("/agent/chat")
@auth_required()
def agent_chat():
    data = request.get_json(force=True) or {}
    text = str(data.get("text") or "").strip()
    if not text:
        return _agent_response(code=400, msg="text required", reply="请先输入你要预约的内容。", action="ask_info", http_status=400)

    user_name = (g.current_user.get("username") or "").strip()
    if not user_name:
        return _agent_response(code=401, msg="unauthorized", reply="登录状态失效，请重新登录。", action="error", http_status=401)

    rule_payload = get_reservation_rules_payload()
    try:
        parsed = _call_siliconflow_to_parse(text, rule_payload)
    except BizError as e:
        return _agent_response(
            code=e.status,
            msg=e.msg,
            reply="智能助手暂时不可用，请稍后重试。",
            action="error",
            http_status=e.status,
        )

    intent = parsed.get("intent") or "ask"
    date_text = str(parsed.get("date") or "").strip()
    time_text = str(parsed.get("time") or "").strip()
    reason = str(parsed.get("reason") or "").strip()
    lab_id = parsed.get("labId")
    lab_name = parsed.get("labName") or ""
    missing = list(parsed.get("missing") or [])
    period_time_text = _extract_time_from_period_expression(text)

    if period_time_text:
        if not time_text:
            time_text = period_time_text
        else:
            parsed_slot_error = _validate_time_with_rule_slots(time_text, rule_payload)
            if parsed_slot_error:
                fallback_slot_error = _validate_time_with_rule_slots(period_time_text, rule_payload)
                if not fallback_slot_error:
                    time_text = period_time_text

    if intent != "reserve":
        reply = "我可以帮你自动预约，请告诉我实验室、日期和时段。例如：明天在软件实验室上 1-2 节。"
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    if not date_text:
        missing.append("date")
    if not time_text:
        missing.append("time")
    if not lab_id and not str(lab_name).strip():
        missing.append("lab")
    if time_text:
        missing = [x for x in missing if str(x).strip().lower() != "time"]

    if missing:
        missing_fields = sorted({str(x) for x in missing if str(x)})
        reply = f"还缺少预约信息：{', '.join(missing_fields)}。请补充后我再为你提交预约。"
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    slot_error = _validate_time_with_rule_slots(time_text, rule_payload)
    if slot_error:
        reply = f"时段格式不符合预约规则：{slot_error}。请使用标准时段，或直接说第1节/1-2节/9.10两节后重试。"
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    schedule_error = validate_reservation_schedule(date_text, time_text)
    if schedule_error:
        reply = f"预约时间不合法：{schedule_error}。请调整日期或时段。"
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    try:
        lab = _resolve_lab_from_agent(lab_id=lab_id, lab_name=lab_name)
    except BizError as e:
        return _agent_response(code=e.status, msg=e.msg, reply=f"实验室信息有问题：{e.msg}", action="ask_info", http_status=e.status)

    try:
        created = create_reservation_internal(
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


@app.post("/login")
def login():
    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = str(data.get("password") or "")
    role_want = (data.get("role") or "").strip()  # optional
    ip = get_client_ip()

    limited = enforce_rate_limit("login", f"{ip}:{username.lower()}")
    if limited:
        return limited

    if not username or not password:
        audit_log(
            "auth.login.failed",
            target_type="auth",
            target_id=username,
            detail={"reason": "params_error"},
            actor={"username": username},
        )
        return jsonify({"ok": False, "msg": "params error"}), 400

    row = query(
        "SELECT id, username, role, password_hash AS passwordHash FROM user WHERE username=%s LIMIT 1",
        (username,),
    )
    if not row:
        audit_log(
            "auth.login.failed",
            target_type="auth",
            target_id=username,
            detail={"reason": "user_not_found"},
            actor={"username": username},
        )
        return jsonify({"ok": False, "msg": "user not found"}), 404

    password_hash = (row[0].get("passwordHash") or "").strip()
    if not password_hash or not check_password_hash(password_hash, password):
        audit_log(
            "auth.login.failed",
            target_type="auth",
            target_id=username,
            detail={"reason": "invalid_password"},
            actor={"id": row[0]["id"], "username": row[0]["username"], "role": row[0]["role"]},
        )
        return jsonify({"ok": False, "msg": "invalid username or password"}), 400

    db_role = row[0]["role"]
    is_admin = (db_role == "admin")

    if role_want:
        if role_want not in ("user", "admin"):
            return jsonify({"ok": False, "msg": "params error"}), 400
        if role_want == "admin" and not is_admin:
            return jsonify({"ok": False, "msg": "not admin"}), 403

    token = create_access_token({"id": row[0]["id"], "username": row[0]["username"], "role": db_role})
    refresh_token = issue_refresh_token(row[0]["id"])
    audit_log(
        "auth.login.success",
        target_type="auth",
        target_id=row[0]["id"],
        detail={"role": db_role},
        actor={"id": row[0]["id"], "username": row[0]["username"], "role": db_role},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "userId": row[0]["id"],
                "username": row[0]["username"],
                "role": db_role,
                "token": token,
                "refreshToken": refresh_token,
                "expiresIn": JWT_EXPIRE_SECONDS,
            },
        }
    )


@app.post("/register")
def register():
    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = str(data.get("password") or "")
    ip = get_client_ip()

    limited = enforce_rate_limit("register", f"{ip}:{username.lower()}")
    if limited:
        return limited

    if not username:
        audit_log(
            "auth.register.failed",
            target_type="auth",
            detail={"reason": "username_required"},
            actor={"username": username},
        )
        return jsonify({"ok": False, "msg": "username required"}), 400
    if len(password) < 6:
        audit_log(
            "auth.register.failed",
            target_type="auth",
            target_id=username,
            detail={"reason": "password_too_short"},
            actor={"username": username},
        )
        return jsonify({"ok": False, "msg": "password must be at least 6 chars"}), 400

    row = query("SELECT id FROM user WHERE username=%s LIMIT 1", (username,))
    if row:
        audit_log(
            "auth.register.failed",
            target_type="auth",
            target_id=username,
            detail={"reason": "user_exists"},
            actor={"username": username},
        )
        return jsonify({"ok": False, "msg": "user exists"}), 409

    new_id = execute_insert(
        "INSERT INTO user (username, role, password_hash) VALUES (%s, %s, %s)",
        (username, "student", generate_password_hash(password)),
    )
    token = create_access_token({"id": new_id, "username": username, "role": "student"})
    refresh_token = issue_refresh_token(new_id)
    audit_log(
        "auth.register.success",
        target_type="auth",
        target_id=new_id,
        detail={"role": "student"},
        actor={"id": new_id, "username": username, "role": "student"},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "userId": new_id,
                "username": username,
                "role": "student",
                "token": token,
                "refreshToken": refresh_token,
                "expiresIn": JWT_EXPIRE_SECONDS,
            },
        }
    )


@app.post("/auth/refresh")
def refresh_access_token():
    data = request.get_json(force=True) or {}
    refresh_token = str(data.get("refreshToken") or "").strip()
    ip = get_client_ip()
    limited = enforce_rate_limit("refresh", f"{ip}:{hash_refresh_token(refresh_token)[:12] if refresh_token else 'none'}")
    if limited:
        return limited
    if not refresh_token:
        audit_log("auth.refresh.failed", target_type="auth", detail={"reason": "refresh_token_required"})
        return jsonify({"ok": False, "msg": "refreshToken required"}), 400

    row = get_refresh_token_row(refresh_token)
    if not is_refresh_token_valid(row):
        audit_log("auth.refresh.failed", target_type="auth", detail={"reason": "invalid_refresh_token"})
        return jsonify({"ok": False, "msg": "invalid refresh token"}), 401

    user_rows = query("SELECT id, username, role FROM user WHERE id=%s LIMIT 1", (row["userId"],))
    if not user_rows:
        revoke_refresh_token(refresh_token)
        audit_log("auth.refresh.failed", target_type="auth", detail={"reason": "user_not_found"})
        return jsonify({"ok": False, "msg": "invalid refresh token"}), 401
    user = user_rows[0]

    new_refresh = issue_refresh_token(user["id"])
    revoke_refresh_token(refresh_token, replaced_by_hash=hash_refresh_token(new_refresh))
    access_token = create_access_token({"id": user["id"], "username": user["username"], "role": user["role"]})
    audit_log(
        "auth.refresh.success",
        target_type="auth",
        target_id=user["id"],
        detail={"role": user["role"]},
        actor={"id": user["id"], "username": user["username"], "role": user["role"]},
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "userId": user["id"],
                "username": user["username"],
                "role": user["role"],
                "token": access_token,
                "refreshToken": new_refresh,
                "expiresIn": JWT_EXPIRE_SECONDS,
            },
        }
    )


@app.post("/auth/logout")
@auth_required()
def logout():
    data = request.get_json(force=True) or {}
    refresh_token = str(data.get("refreshToken") or "").strip()
    if refresh_token:
        revoke_refresh_token(refresh_token)
    return jsonify({"ok": True})


@app.post("/auth/change-password")
@auth_required()
def change_password():
    data = request.get_json(force=True) or {}
    old_password = str(data.get("oldPassword") or "")
    new_password = str(data.get("newPassword") or "")
    uid = g.current_user["id"]

    limited = enforce_rate_limit("change_password", f"{get_client_ip()}:{uid}")
    if limited:
        return limited

    if not old_password or len(new_password) < 6:
        audit_log(
            "auth.change_password.failed",
            target_type="auth",
            target_id=uid,
            detail={"reason": "params_error"},
        )
        return jsonify({"ok": False, "msg": "params error"}), 400

    row = query("SELECT id, password_hash AS passwordHash FROM user WHERE id=%s LIMIT 1", (uid,))
    if not row:
        audit_log(
            "auth.change_password.failed",
            target_type="auth",
            target_id=uid,
            detail={"reason": "user_not_found"},
        )
        return jsonify({"ok": False, "msg": "user not found"}), 404
    password_hash = (row[0].get("passwordHash") or "").strip()
    if not password_hash or not check_password_hash(password_hash, old_password):
        audit_log(
            "auth.change_password.failed",
            target_type="auth",
            target_id=uid,
            detail={"reason": "old_password_incorrect"},
        )
        return jsonify({"ok": False, "msg": "old password incorrect"}), 400

    execute("UPDATE user SET password_hash=%s WHERE id=%s", (generate_password_hash(new_password), uid))
    execute("UPDATE auth_refresh_token SET revoked_at=%s WHERE user_id=%s AND revoked_at IS NULL", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid))
    audit_log("auth.change_password.success", target_type="auth", target_id=uid)
    return jsonify({"ok": True})


@app.get("/users")
@auth_required(roles=["admin"])
def list_users():
    rows = query("SELECT id, username, role FROM user ORDER BY id ASC")
    return jsonify(rows)


@app.get("/audit-logs")
@auth_required(roles=["admin"])
def list_audit_logs():
    action = request.args.get("action", "").strip()
    operator = request.args.get("operator", "").strip()
    target_type = request.args.get("targetType", "").strip()
    start_date = request.args.get("startDate", "").strip()
    end_date = request.args.get("endDate", "").strip()
    page_raw = request.args.get("page", "1").strip()
    page_size_raw = request.args.get("pageSize", request.args.get("limit", "50")).strip()

    try:
        page = int(page_raw)
    except ValueError:
        page = 1
    try:
        page_size = int(page_size_raw)
    except ValueError:
        page_size = 50

    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    offset = (page - 1) * page_size

    rows, total, err = fetch_audit_logs(
        action=action,
        operator=operator,
        target_type=target_type,
        start_date=start_date,
        end_date=end_date,
        limit=page_size,
        offset=offset,
        with_total=True,
    )
    if err:
        return jsonify({"ok": False, "msg": err}), 400

    for row in rows:
        raw = (row.get("detailJson") or "").strip()
        if raw:
            try:
                row["detail"] = json.loads(raw)
            except Exception:
                row["detail"] = {"raw": raw}
        else:
            row["detail"] = {}
        row["createdAt"] = _to_text_time(row.get("createdAt"))
        row.pop("detailJson", None)

    return jsonify(
        {
            "ok": True,
            "data": rows,
            "meta": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "hasMore": (offset + len(rows)) < int(total or 0),
            },
        }
    )


@app.get("/audit-logs/export")
@auth_required(roles=["admin"])
def export_audit_logs():
    action = request.args.get("action", "").strip()
    operator = request.args.get("operator", "").strip()
    target_type = request.args.get("targetType", "").strip()
    start_date = request.args.get("startDate", "").strip()
    end_date = request.args.get("endDate", "").strip()
    limit_raw = request.args.get("limit", "2000").strip()

    try:
        limit = int(limit_raw)
    except ValueError:
        limit = 2000
    limit = max(1, min(limit, 5000))

    rows, _, err = fetch_audit_logs(
        action=action,
        operator=operator,
        target_type=target_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=0,
        with_total=False,
    )
    if err:
        return jsonify({"ok": False, "msg": err}), 400

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "created_at",
        "action",
        "operator_id",
        "operator_name",
        "operator_role",
        "target_type",
        "target_id",
        "ip",
        "detail_json",
    ])
    for r in rows:
        writer.writerow([
            r.get("id"),
            _to_text_time(r.get("createdAt")),
            r.get("action"),
            r.get("operatorId"),
            r.get("operatorName"),
            r.get("operatorRole"),
            r.get("targetType"),
            r.get("targetId"),
            r.get("ip"),
            r.get("detailJson") or "",
        ])
    csv_data = output.getvalue()
    return (
        csv_data,
        200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": "attachment; filename=audit_logs.csv",
        },
    )


@app.post("/users/<int:uid>/promote")
@auth_required(roles=["admin"])
def promote_user(uid):
    operator = (g.current_user.get("username") or "").strip()
    if operator != "admin1":
        return jsonify({"ok": False, "msg": "forbidden"}), 403

    row = query("SELECT id, username, role FROM user WHERE id=%s LIMIT 1", (uid,))
    if not row:
        return jsonify({"ok": False, "msg": "user not found"}), 404

    if row[0]["role"] == "admin":
        return jsonify({"ok": True, "msg": "already admin"})

    execute("UPDATE user SET role='admin' WHERE id=%s", (uid,))
    audit_log(
        "admin.user.promote",
        target_type="user",
        target_id=uid,
        detail={"fromRole": row[0]["role"], "toRole": "admin", "targetUsername": row[0]["username"]},
    )
    return jsonify({"ok": True})


@app.post("/users/<int:uid>/demote")
@auth_required(roles=["admin"])
def demote_user(uid):
    operator = (g.current_user.get("username") or "").strip()
    if operator != "admin1":
        return jsonify({"ok": False, "msg": "forbidden"}), 403

    row = query("SELECT id, username, role FROM user WHERE id=%s LIMIT 1", (uid,))
    if not row:
        return jsonify({"ok": False, "msg": "user not found"}), 404

    if row[0]["role"] != "admin":
        return jsonify({"ok": True, "msg": "already non-admin"})

    execute("UPDATE user SET role='student' WHERE id=%s", (uid,))
    audit_log(
        "admin.user.demote",
        target_type="user",
        target_id=uid,
        detail={"fromRole": row[0]["role"], "toRole": "student", "targetUsername": row[0]["username"]},
    )
    return jsonify({"ok": True})


@app.get("/lostfound")
@auth_required()
def list_lost_found():
    status = request.args.get("status", "").strip()
    item_type = request.args.get("type", "").strip()
    owner = request.args.get("owner", "").strip()
    student_id = request.args.get("studentId", "").strip()
    student_name = request.args.get("studentName", "").strip()
    student_class = request.args.get("studentClass", "").strip()
    claim_apply_status = request.args.get("claimApplyStatus", "").strip()
    claim_apply_user = request.args.get("claimApplyUser", "").strip()

    sql = """
        SELECT id, title, item_type AS type, description, location,
               contact, status, owner, created_at AS createdAt,
               image_url AS imageUrl,
               claim_student_id AS claimStudentId,
               claim_name AS claimName,
               claim_class AS claimClass,
               claim_apply_status AS claimApplyStatus,
               claim_apply_user AS claimApplyUser,
               claim_apply_reason AS claimApplyReason,
               claim_apply_student_id AS claimApplyStudentId,
               claim_apply_name AS claimApplyName,
               claim_apply_class AS claimApplyClass,
               claim_apply_at AS claimApplyAt,
               claim_reviewed_by AS claimReviewedBy,
               claim_reviewed_at AS claimReviewedAt,
               claim_review_note AS claimReviewNote
        FROM lost_found
        WHERE 1=1
    """
    params = []

    if status:
        sql += " AND status=%s"
        params.append(status)
    if item_type:
        sql += " AND item_type=%s"
        params.append(item_type)
    if owner:
        sql += " AND owner=%s"
        params.append(owner)
    if student_id:
        sql += " AND claim_student_id LIKE %s"
        params.append(f"%{student_id}%")
    if student_name:
        sql += " AND claim_name LIKE %s"
        params.append(f"%{student_name}%")
    if student_class:
        sql += " AND claim_class LIKE %s"
        params.append(f"%{student_class}%")
    if claim_apply_status:
        if claim_apply_status == "none":
            sql += " AND (claim_apply_status='' OR claim_apply_status IS NULL)"
        else:
            sql += " AND claim_apply_status=%s"
            params.append(claim_apply_status)
    if claim_apply_user:
        sql += " AND claim_apply_user=%s"
        params.append(claim_apply_user)

    sql += " ORDER BY id DESC"
    rows = query(sql, params)
    for row in rows:
        row["claimApplyAt"] = _to_text_time(row.get("claimApplyAt"))
        row["claimReviewedAt"] = _to_text_time(row.get("claimReviewedAt"))
    return jsonify(rows)


@app.post("/lostfound")
@auth_required()
def create_lost_found():
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    item_type = (data.get("type") or "").strip()  # lost/found
    description = (data.get("description") or "").strip()
    location = (data.get("location") or "").strip()
    contact = (data.get("contact") or "").strip()
    owner = (g.current_user.get("username") or "").strip()
    image_url = (data.get("imageUrl") or "").strip()

    if not title or item_type not in ("lost", "found"):
        return jsonify({"ok": False, "msg": "params error"}), 400

    created_at = datetime.now().isoformat(timespec="seconds")
    new_id = execute_insert(
        """
        INSERT INTO lost_found (title, item_type, description, location, contact, status, owner, created_at, image_url)
        VALUES (%s,%s,%s,%s,%s,'open',%s,%s,%s)
        """,
        (title, item_type, description, location, contact, owner, created_at, image_url),
    )
    return jsonify({"ok": True, "data": {"id": new_id}})


@app.post("/lostfound/<int:lid>/claim-apply")
@auth_required()
def apply_lost_found_claim(lid):
    data = request.get_json(force=True) or {}
    applicant = (g.current_user.get("username") or "").strip()
    claim_student_id = (data.get("claimStudentId") or "").strip()
    claim_name = (data.get("claimName") or "").strip()
    claim_class = (data.get("claimClass") or "").strip()
    claim_reason = (data.get("claimReason") or "").strip()
    if not applicant:
        return jsonify({"ok": False, "msg": "unauthorized"}), 401
    if not claim_student_id or not claim_name or not claim_class:
        return jsonify({"ok": False, "msg": "claim info required"}), 400

    try:
        def _tx(cur):
            cur.execute(
                """
                SELECT id, title, item_type AS type, status, owner,
                       claim_apply_status AS claimApplyStatus,
                       claim_apply_user AS claimApplyUser
                FROM lost_found
                WHERE id=%s
                LIMIT 1
                FOR UPDATE
                """,
                (lid,),
            )
            row = cur.fetchone()
            if not row:
                raise BizError("not found", 404)
            if row["type"] != "found":
                raise BizError("only found item can be claimed", 400)
            if row["status"] != "open":
                raise BizError("item already closed", 409)
            if (row.get("owner") or "").strip() == applicant:
                raise BizError("owner cannot claim own item", 403)
            if row.get("claimApplyStatus") == "approved":
                raise BizError("claim already approved", 409)
            pending_user = (row.get("claimApplyUser") or "").strip()
            if row.get("claimApplyStatus") == "pending" and pending_user and pending_user != applicant:
                raise BizError("another claim is pending", 409)

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                """
                UPDATE lost_found
                SET claim_apply_status='pending',
                    claim_apply_user=%s,
                    claim_apply_reason=%s,
                    claim_apply_student_id=%s,
                    claim_apply_name=%s,
                    claim_apply_class=%s,
                    claim_apply_at=%s,
                    claim_reviewed_by='',
                    claim_reviewed_at=NULL,
                    claim_review_note=''
                WHERE id=%s
                """,
                (applicant, claim_reason, claim_student_id, claim_name, claim_class, now, lid),
            )
            return {"title": row.get("title") or "", "owner": row.get("owner") or ""}

        result = run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log(
        "user.lostfound.claim_apply",
        target_type="lostfound",
        target_id=lid,
        detail={
            "claimUser": applicant,
            "claimStudentId": claim_student_id,
            "claimName": claim_name,
            "claimClass": claim_class,
            "claimReason": claim_reason,
        },
    )
    return jsonify({"ok": True, "data": result})


@app.post("/lostfound/<int:lid>/claim-review")
@auth_required(roles=["admin"])
def review_lost_found_claim(lid):
    data = request.get_json(force=True) or {}
    action = (data.get("action") or "").strip()  # approve/reject
    note = (data.get("note") or "").strip()
    reviewer = (g.current_user.get("username") or "").strip()
    if action not in ("approve", "reject"):
        return jsonify({"ok": False, "msg": "invalid action"}), 400

    try:
        def _tx(cur):
            cur.execute(
                """
                SELECT id, title, item_type AS type, status,
                       claim_apply_status AS claimApplyStatus,
                       claim_apply_user AS claimApplyUser,
                       claim_apply_student_id AS claimApplyStudentId,
                       claim_apply_name AS claimApplyName,
                       claim_apply_class AS claimApplyClass
                FROM lost_found
                WHERE id=%s
                LIMIT 1
                FOR UPDATE
                """,
                (lid,),
            )
            row = cur.fetchone()
            if not row:
                raise BizError("not found", 404)
            if row["type"] != "found":
                raise BizError("only found item has claim review", 400)
            if row.get("claimApplyStatus") != "pending":
                raise BizError("no pending claim", 409)

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if action == "approve":
                if not row.get("claimApplyStudentId") or not row.get("claimApplyName") or not row.get("claimApplyClass"):
                    raise BizError("claim info required", 400)
                cur.execute(
                    """
                    UPDATE lost_found
                    SET status='closed',
                        claim_student_id=claim_apply_student_id,
                        claim_name=claim_apply_name,
                        claim_class=claim_apply_class,
                        claim_apply_status='approved',
                        claim_reviewed_by=%s,
                        claim_reviewed_at=%s,
                        claim_review_note=%s,
                        created_at=%s
                    WHERE id=%s
                    """,
                    (reviewer, now, note, now, lid),
                )
            else:
                cur.execute(
                    """
                    UPDATE lost_found
                    SET claim_apply_status='rejected',
                        claim_reviewed_by=%s,
                        claim_reviewed_at=%s,
                        claim_review_note=%s
                    WHERE id=%s
                    """,
                    (reviewer, now, note, lid),
                )
            return {
                "title": row.get("title") or "",
                "claimUser": row.get("claimApplyUser") or "",
            }

        result = run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log(
        "admin.lostfound.claim_review",
        target_type="lostfound",
        target_id=lid,
        detail={"action": action, "note": note},
    )
    return jsonify({"ok": True, "data": result})


@app.post("/lostfound/<int:lid>/status")
@auth_required(roles=["admin"])
def update_lost_found_status(lid):
    data = request.get_json(force=True) or {}
    status = (data.get("status") or "").strip()  # open/closed
    claim_student_id = (data.get("claimStudentId") or "").strip()
    claim_name = (data.get("claimName") or "").strip()
    claim_class = (data.get("claimClass") or "").strip()

    if status not in ("open", "closed"):
        return jsonify({"ok": False, "msg": "invalid status"}), 400
    if status == "closed" and (not claim_student_id or not claim_name or not claim_class):
        return jsonify({"ok": False, "msg": "claim info required"}), 400

    row = query("SELECT id FROM lost_found WHERE id=%s LIMIT 1", (lid,))
    if not row:
        return jsonify({"ok": False, "msg": "not found"}), 404

    status_time = datetime.now().isoformat(timespec="seconds")
    execute(
        """
        UPDATE lost_found
        SET status=%s,
            claim_student_id=%s,
            claim_name=%s,
            claim_class=%s,
            created_at=CASE WHEN %s='closed' THEN %s ELSE created_at END
        WHERE id=%s
        """,
        (status, claim_student_id, claim_name, claim_class, status, status_time, lid),
    )
    audit_log(
        "admin.lostfound.status",
        target_type="lostfound",
        target_id=lid,
        detail={
            "status": status,
            "claimStudentId": claim_student_id,
            "claimName": claim_name,
            "claimClass": claim_class,
        },
    )
    return jsonify({"ok": True})


@app.post("/upload")
@auth_required()
def upload():
    if "file" not in request.files:
        return jsonify({"ok": False, "msg": "file required"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"ok": False, "msg": "filename required"}), 400

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        return jsonify({"ok": False, "msg": "invalid file type"}), 400

    name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, name)
    f.save(path)
    return jsonify({"ok": True, "data": {"url": f"/uploads/{name}"}})


@app.get("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.get("/labs")
@auth_required()
def get_labs():
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        rows = query(
            """
            SELECT id, name, status, capacity,
                   device_count AS deviceCount,
                   description, image_url AS imageUrl
            FROM lab
            ORDER BY id DESC
            """
        )
        return jsonify(rows)

    rows = query(
        """
        SELECT id, name, status, capacity,
               device_count AS deviceCount,
               description, image_url AS imageUrl
        FROM lab
        WHERE name LIKE %s
        ORDER BY id DESC
        """,
        (f"%{keyword}%",),
    )
    return jsonify(rows)


@app.post("/labs/<int:lid>")
@auth_required(roles=["admin"])
def update_lab(lid):
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    status = (data.get("status") or "").strip()
    description = (data.get("description") or "").strip()
    image_url = (data.get("imageUrl") or "").strip()
    capacity_raw = _to_int_or_none(data.get("capacity"))
    device_count_raw = _to_int_or_none(data.get("deviceCount"))

    if not name:
        return jsonify({"ok": False, "msg": "name required"}), 400
    if status not in ("free", "busy"):
        return jsonify({"ok": False, "msg": "invalid status"}), 400
    if data.get("capacity") not in (None, "") and capacity_raw is None:
        return jsonify({"ok": False, "msg": "invalid capacity"}), 400
    if data.get("deviceCount") not in (None, "") and device_count_raw is None:
        return jsonify({"ok": False, "msg": "invalid deviceCount"}), 400

    capacity = max(0, int(capacity_raw or 0))
    device_count = max(0, int(device_count_raw or 0))

    row = query("SELECT id FROM lab WHERE id=%s LIMIT 1", (lid,))
    if not row:
        return jsonify({"ok": False, "msg": "lab not found"}), 404

    execute(
        """
        UPDATE lab
        SET name=%s, status=%s, capacity=%s, device_count=%s, description=%s, image_url=%s
        WHERE id=%s
        """,
        (name, status, capacity, device_count, description, image_url, lid),
    )
    audit_log(
        "admin.lab.update",
        target_type="lab",
        target_id=lid,
        detail={
            "name": name,
            "status": status,
            "capacity": capacity,
            "deviceCount": device_count,
            "description": description,
            "imageUrl": image_url,
        },
    )
    return jsonify({"ok": True})


@app.post("/labs")
@auth_required(roles=["admin"])
def create_lab():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    status = (data.get("status") or "free").strip()
    description = (data.get("description") or "").strip()
    image_url = (data.get("imageUrl") or "").strip()
    capacity = _to_int_or_none(data.get("capacity"))
    device_count = _to_int_or_none(data.get("deviceCount"))

    if not name:
        return jsonify({"ok": False, "msg": "name required"}), 400
    if status not in ("free", "busy"):
        return jsonify({"ok": False, "msg": "invalid status"}), 400
    if data.get("capacity") not in (None, "") and capacity is None:
        return jsonify({"ok": False, "msg": "invalid capacity"}), 400
    if data.get("deviceCount") not in (None, "") and device_count is None:
        return jsonify({"ok": False, "msg": "invalid deviceCount"}), 400

    capacity = max(0, int(capacity or 0))
    device_count = max(0, int(device_count or 0))

    dup = query("SELECT id FROM lab WHERE name=%s LIMIT 1", (name,))
    if dup:
        return jsonify({"ok": False, "msg": "lab name exists"}), 409

    new_id = execute_insert(
        """
        INSERT INTO lab (name, status, capacity, device_count, description, image_url)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (name, status, capacity, device_count, description, image_url),
    )
    audit_log(
        "admin.lab.create",
        target_type="lab",
        target_id=new_id,
        detail={
            "name": name,
            "status": status,
            "capacity": capacity,
            "deviceCount": device_count,
            "description": description,
            "imageUrl": image_url,
        },
    )
    return jsonify({"ok": True, "data": {"id": new_id}})


@app.post("/labs/<int:lid>/delete")
@auth_required(roles=["admin"])
def delete_lab(lid):
    row = query("SELECT id, name FROM lab WHERE id=%s LIMIT 1", (lid,))
    if not row:
        return jsonify({"ok": False, "msg": "lab not found"}), 404
    lab_name = row[0]["name"]

    ref = query(
        """
        SELECT COUNT(*) AS cnt
        FROM reservation
        WHERE lab_id=%s OR lab_name=%s
        """,
        (lid, lab_name),
    )
    ref_count = int((ref[0] or {}).get("cnt") or 0) if ref else 0
    if ref_count > 0:
        return jsonify({"ok": False, "msg": "lab has reservation history, cannot delete"}), 409

    execute("DELETE FROM lab WHERE id=%s", (lid,))
    audit_log(
        "admin.lab.delete",
        target_type="lab",
        target_id=lid,
        detail={"name": lab_name},
    )
    return jsonify({"ok": True})


def create_reservation_internal(user_name, date, time_range, reason="", lab_id=None, lab_name=""):
    user = str(user_name or "").strip()
    date_text = str(date or "").strip()
    time_text = str(time_range or "").strip()
    reason_text = str(reason or "").strip()
    lab_id_val = _to_int_or_none(lab_id)
    lab_name_val = str(lab_name or "").strip()

    if not user:
        raise BizError("user required", 400)
    if not date_text or not time_text:
        raise BizError("params error", 400)

    schedule_error = validate_reservation_schedule(date_text, time_text)
    if schedule_error:
        raise BizError(schedule_error, 400)

    if lab_id_val:
        lab_rows = query("SELECT id, name FROM lab WHERE id=%s LIMIT 1", (lab_id_val,))
    elif lab_name_val:
        lab_rows = query("SELECT id, name FROM lab WHERE name=%s LIMIT 1", (lab_name_val,))
    else:
        raise BizError("lab required", 400)

    if not lab_rows:
        raise BizError("lab not found", 404)

    resolved_lab_id = int(lab_rows[0]["id"])
    resolved_lab_name = str(lab_rows[0]["name"] or "").strip()
    if not resolved_lab_name:
        raise BizError("lab not found", 404)

    created_at = datetime.now().isoformat(timespec="seconds")

    def _tx(cur):
        lock_key = _reservation_lock_key(resolved_lab_name, date_text)
        if not _acquire_named_lock(cur, lock_key):
            raise BizError("reservation busy, try again", 409)
        try:
            if has_approved_conflict_with_cur(cur, resolved_lab_name, date_text, time_text):
                raise BizError("reservation conflict with approved", 409)
            cur.execute(
                """
                INSERT INTO reservation (lab_id, lab_name, user_name, date, time, reason, status, reject_reason, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,'pending','',%s)
                """,
                (resolved_lab_id, resolved_lab_name, user, date_text, time_text, reason_text, created_at),
            )
            return cur.lastrowid
        finally:
            _release_named_lock(cur, lock_key)

    new_id = run_in_transaction(_tx)
    return {
        "id": int(new_id),
        "labId": resolved_lab_id,
        "labName": resolved_lab_name,
        "date": date_text,
        "time": time_text,
        "reason": reason_text,
        "status": "pending",
    }


@app.post("/reservations")
@auth_required()
def create_reservation():
    data = request.get_json(force=True) or {}

    required = ["labName", "date", "time"]
    missing = [k for k in required if not str(data.get(k, "")).strip()]
    if missing:
        return jsonify({"ok": False, "msg": f"missing: {', '.join(missing)}"}), 400

    lab_name = data["labName"].strip()
    user_name = (g.current_user.get("username") or "").strip()
    date = data["date"].strip()
    time_range = data["time"].strip()
    reason = (data.get("reason") or "").strip()
    try:
        created = create_reservation_internal(
            user_name=user_name,
            lab_name=lab_name,
            date=date,
            time_range=time_range,
            reason=reason,
        )
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    return jsonify({"ok": True, "data": {"id": created["id"]}})


@app.post("/reservations/<int:rid>/cancel")
@auth_required()
def cancel_reservation(rid):
    user = (g.current_user.get("username") or "").strip()
    if not user:
        return jsonify({"ok": False, "msg": "user required"}), 400

    row = query("SELECT id, user_name AS user, status FROM reservation WHERE id=%s LIMIT 1", (rid,))
    if not row:
        return jsonify({"ok": False, "msg": "reservation not found"}), 404
    if row[0]["user"] != user:
        return jsonify({"ok": False, "msg": "forbidden"}), 403

    if row[0]["status"] in ("rejected", "cancelled"):
        return jsonify({"ok": True})

    execute("UPDATE reservation SET status='cancelled' WHERE id=%s", (rid,))
    return jsonify({"ok": True})


@app.post("/reservations/<int:rid>/reschedule")
@auth_required()
def reschedule_reservation(rid):
    data = request.get_json(force=True) or {}
    user = (g.current_user.get("username") or "").strip()
    date = (data.get("date") or "").strip()
    time_range = (data.get("time") or "").strip()
    if not user or not date or not time_range:
        return jsonify({"ok": False, "msg": "params error"}), 400
    schedule_error = validate_reservation_schedule(date, time_range)
    if schedule_error:
        return jsonify({"ok": False, "msg": schedule_error}), 400

    try:
        def _tx(cur):
            cur.execute(
                """
                SELECT id, lab_name AS labName, user_name AS user, status
                FROM reservation
                WHERE id=%s
                LIMIT 1
                FOR UPDATE
                """,
                (rid,),
            )
            row = cur.fetchone()
            if not row:
                raise BizError("reservation not found", 404)
            if row["user"] != user:
                raise BizError("forbidden", 403)
            if row["status"] not in ("pending", "approved"):
                raise BizError("invalid status", 400)

            lab_name = row["labName"]
            lock_key = _reservation_lock_key(lab_name, date)
            if not _acquire_named_lock(cur, lock_key):
                raise BizError("reservation busy, try again", 409)
            try:
                if has_approved_conflict_with_cur(cur, lab_name, date, time_range, exclude_id=rid):
                    raise BizError("reservation conflict with approved", 409)
                cur.execute(
                    """
                    UPDATE reservation
                    SET date=%s, time=%s, status='pending', reject_reason=''
                    WHERE id=%s
                    """,
                    (date, time_range, rid),
                )
            finally:
                _release_named_lock(cur, lock_key)

        run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    return jsonify({"ok": True})


@app.post("/reservations/<int:rid>/admin-cancel")
@auth_required(roles=["admin"])
def admin_cancel_reservation(rid):
    row = query("SELECT id FROM reservation WHERE id=%s LIMIT 1", (rid,))
    if not row:
        return jsonify({"ok": False, "msg": "reservation not found"}), 404

    execute("UPDATE reservation SET status='cancelled' WHERE id=%s", (rid,))
    audit_log("admin.reservation.cancel", target_type="reservation", target_id=rid)
    return jsonify({"ok": True})


@app.post("/reservations/<int:rid>/admin-reschedule")
@auth_required(roles=["admin"])
def admin_reschedule_reservation(rid):
    data = request.get_json(force=True) or {}
    date = (data.get("date") or "").strip()
    time_range = (data.get("time") or "").strip()
    if not date or not time_range:
        return jsonify({"ok": False, "msg": "params error"}), 400
    schedule_error = validate_reservation_schedule(date, time_range)
    if schedule_error:
        return jsonify({"ok": False, "msg": schedule_error}), 400

    try:
        def _tx(cur):
            cur.execute(
                """
                SELECT id, lab_name AS labName, status
                FROM reservation
                WHERE id=%s
                LIMIT 1
                FOR UPDATE
                """,
                (rid,),
            )
            row = cur.fetchone()
            if not row:
                raise BizError("reservation not found", 404)
            if row["status"] not in ("pending", "approved"):
                raise BizError("invalid status", 400)

            lab_name = row["labName"]
            lock_key = _reservation_lock_key(lab_name, date)
            if not _acquire_named_lock(cur, lock_key):
                raise BizError("reservation busy, try again", 409)
            try:
                if has_approved_conflict_with_cur(cur, lab_name, date, time_range, exclude_id=rid):
                    raise BizError("reservation conflict with approved", 409)
                cur.execute(
                    """
                    UPDATE reservation
                    SET date=%s, time=%s, status='pending', reject_reason=''
                    WHERE id=%s
                    """,
                    (date, time_range, rid),
                )
            finally:
                _release_named_lock(cur, lock_key)

        run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log(
        "admin.reservation.reschedule",
        target_type="reservation",
        target_id=rid,
        detail={"date": date, "time": time_range},
    )
    return jsonify({"ok": True})


@app.post("/reservations/batch")
@auth_required(roles=["admin"])
def batch_reservations():
    data = request.get_json(force=True) or {}
    action = (data.get("action") or "").strip()  # approve/cancel
    ids = data.get("ids") or []
    if action not in ("approve", "cancel") or not isinstance(ids, list):
        return jsonify({"ok": False, "msg": "params error"}), 400

    clean_ids = []
    for rid in ids:
        try:
            n = int(rid)
        except (TypeError, ValueError):
            continue
        if n > 0:
            clean_ids.append(n)

    if not clean_ids:
        return jsonify({"ok": True, "data": {"count": 0}})

    if action == "approve":
        approved_ids = []
        conflict_ids = []
        invalid_status_ids = []
        invalid_schedule_ids = []
        not_found_ids = []
        busy_ids = []

        def _tx(cur):
            for rid in clean_ids:
                cur.execute(
                    """
                    SELECT id, lab_name AS labName, date, time, status
                    FROM reservation
                    WHERE id=%s
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (rid,),
                )
                row = cur.fetchone()
                if not row:
                    not_found_ids.append(rid)
                    continue
                if row["status"] != "pending":
                    invalid_status_ids.append(rid)
                    continue

                schedule_error = validate_reservation_schedule(row["date"], row["time"])
                if schedule_error:
                    invalid_schedule_ids.append(rid)
                    continue

                lock_key = _reservation_lock_key(row["labName"], row["date"])
                if not _acquire_named_lock(cur, lock_key):
                    busy_ids.append(rid)
                    continue
                try:
                    if has_approved_conflict_with_cur(cur, row["labName"], row["date"], row["time"], exclude_id=rid):
                        conflict_ids.append(rid)
                        continue
                    cur.execute(
                        """
                        UPDATE reservation
                        SET status='approved', reject_reason=''
                        WHERE id=%s AND status='pending'
                        """,
                        (rid,),
                    )
                    if cur.rowcount == 1:
                        approved_ids.append(rid)
                    else:
                        invalid_status_ids.append(rid)
                finally:
                    _release_named_lock(cur, lock_key)

        run_in_transaction(_tx)

        audit_log(
            "admin.reservation.batch_approve",
            target_type="reservation",
            detail={
                "requested": _compact_ids(clean_ids),
                "approved": _compact_ids(approved_ids),
                "conflict": _compact_ids(conflict_ids),
                "invalidStatus": _compact_ids(invalid_status_ids),
                "invalidSchedule": _compact_ids(invalid_schedule_ids),
                "notFound": _compact_ids(not_found_ids),
                "busy": _compact_ids(busy_ids),
            },
        )
        return jsonify(
            {
                "ok": True,
                "data": {
                    "count": len(approved_ids),
                    "approvedIds": approved_ids,
                    "conflictIds": conflict_ids,
                    "invalidStatusIds": invalid_status_ids,
                    "invalidScheduleIds": invalid_schedule_ids,
                    "notFoundIds": not_found_ids,
                    "busyIds": busy_ids,
                },
            }
        )
    else:
        placeholders = ",".join(["%s"] * len(clean_ids))

        def _tx(cur):
            cur.execute(f"UPDATE reservation SET status='cancelled' WHERE id IN ({placeholders})", clean_ids)
            return cur.rowcount

        affected = run_in_transaction(_tx)
        audit_log(
            "admin.reservation.batch_cancel",
            target_type="reservation",
            detail={"cancelled": _compact_ids(clean_ids)},
        )

    return jsonify({"ok": True, "data": {"count": int(affected or 0)}})


@app.get("/reservations")
@auth_required()
def list_reservations():
    status = request.args.get("status", "").strip()
    user = request.args.get("user", "").strip()
    user_keyword = request.args.get("userKeyword", "").strip()
    lab_name = request.args.get("labName", "").strip()
    lab_keyword = request.args.get("labKeyword", "").strip()
    date = request.args.get("date", "").strip()
    date_from = request.args.get("dateFrom", "").strip()
    date_to = request.args.get("dateTo", "").strip()
    page_raw = request.args.get("page", "").strip()
    page_size_raw = request.args.get("pageSize", "").strip()
    current_user = g.current_user
    is_admin = current_user.get("role") == "admin"
    use_pagination = bool(page_raw or page_size_raw)

    # non-admin: user filter can only query self
    if not is_admin and user and user != current_user.get("username"):
        return jsonify({"ok": False, "msg": "forbidden"}), 403
    if not is_admin and user_keyword:
        return jsonify({"ok": False, "msg": "forbidden"}), 403

    # non-admin and no explicit user filter: default to self unless this is a lab calendar query
    if not is_admin and not user:
        if not (lab_name and date and status):
            user = current_user.get("username")

    where_sql = " WHERE 1=1"
    params = []

    if status:
        if "," in status:
            parts = [s.strip() for s in status.split(",") if s.strip()]
            if parts:
                where_sql += " AND status IN (" + ",".join(["%s"] * len(parts)) + ")"
                params.extend(parts)
        else:
            where_sql += " AND status=%s"
            params.append(status)

    if user:
        where_sql += " AND user_name=%s"
        params.append(user)
    elif user_keyword:
        where_sql += " AND user_name LIKE %s"
        params.append(f"%{user_keyword}%")

    if lab_name:
        where_sql += " AND lab_name=%s"
        params.append(lab_name)
    elif lab_keyword:
        where_sql += " AND lab_name LIKE %s"
        params.append(f"%{lab_keyword}%")

    if date:
        where_sql += " AND date=%s"
        params.append(date)
    else:
        date_from_dt = _parse_date_yyyy_mm_dd(date_from)
        date_to_dt = _parse_date_yyyy_mm_dd(date_to)
        if date_from and not date_from_dt:
            return jsonify({"ok": False, "msg": "invalid dateFrom"}), 400
        if date_to and not date_to_dt:
            return jsonify({"ok": False, "msg": "invalid dateTo"}), 400
        if date_from_dt and date_to_dt and date_from_dt > date_to_dt:
            return jsonify({"ok": False, "msg": "dateFrom must be <= dateTo"}), 400
        if date_from_dt:
            where_sql += " AND date >= %s"
            params.append(date_from_dt.strftime("%Y-%m-%d"))
        if date_to_dt:
            where_sql += " AND date <= %s"
            params.append(date_to_dt.strftime("%Y-%m-%d"))

    base_sql = """
        SELECT id,
               lab_name AS labName,
               user_name AS user,
               date,
               time,
               reason,
               status,
               reject_reason AS rejectReason,
               admin_note AS adminNote,
               created_at AS createdAt
        FROM reservation
    """

    if not use_pagination:
        rows = query(base_sql + where_sql + " ORDER BY id DESC", params)
        return jsonify(rows)

    try:
        page = int(page_raw or "1")
    except ValueError:
        page = 1
    try:
        page_size = int(page_size_raw or "20")
    except ValueError:
        page_size = 20
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    count_rows = query("SELECT COUNT(*) AS cnt FROM reservation" + where_sql, params)
    total = int((count_rows[0] or {}).get("cnt") or 0) if count_rows else 0

    list_sql = base_sql + where_sql + " ORDER BY id DESC LIMIT %s OFFSET %s"
    list_params = list(params) + [page_size, offset]
    rows = query(list_sql, list_params)

    return jsonify(
        {
            "ok": True,
            "data": rows,
            "meta": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "hasMore": (offset + len(rows)) < total,
            },
        }
    )


@app.get("/reservations/<int:rid>")
@auth_required()
def get_reservation(rid):
    row = query(
        """
        SELECT id,
               lab_name AS labName,
               user_name AS user,
               date,
               time,
               reason,
               status,
               reject_reason AS rejectReason,
               admin_note AS adminNote,
               created_at AS createdAt
        FROM reservation
        WHERE id=%s
        LIMIT 1
        """,
        (rid,),
    )
    if not row:
        return jsonify({"ok": False, "msg": "reservation not found"}), 404
    current_user = g.current_user
    if current_user.get("role") != "admin" and row[0].get("user") != current_user.get("username"):
        return jsonify({"ok": False, "msg": "forbidden"}), 403
    return jsonify({"ok": True, "data": row[0]})


@app.get("/reservations/export")
@auth_required(roles=["admin"])
def export_reservations():
    status = request.args.get("status", "").strip()
    lab_name = request.args.get("labName", "").strip()
    lab_keyword = request.args.get("labKeyword", "").strip()
    user = request.args.get("user", "").strip()
    user_keyword = request.args.get("userKeyword", "").strip()
    date = request.args.get("date", "").strip()
    date_from = request.args.get("dateFrom", "").strip()
    date_to = request.args.get("dateTo", "").strip()
    sql = """
        SELECT id, lab_name, user_name, date, time, reason, status,
               reject_reason, admin_note, created_at
        FROM reservation
        WHERE 1=1
    """
    params = []
    if status:
        sql += " AND status=%s"
        params.append(status)
    if lab_name:
        sql += " AND lab_name=%s"
        params.append(lab_name)
    elif lab_keyword:
        sql += " AND lab_name LIKE %s"
        params.append(f"%{lab_keyword}%")
    if user:
        sql += " AND user_name=%s"
        params.append(user)
    elif user_keyword:
        sql += " AND user_name LIKE %s"
        params.append(f"%{user_keyword}%")
    if date:
        sql += " AND date=%s"
        params.append(date)
    else:
        date_from_dt = _parse_date_yyyy_mm_dd(date_from)
        date_to_dt = _parse_date_yyyy_mm_dd(date_to)
        if date_from and not date_from_dt:
            return jsonify({"ok": False, "msg": "invalid dateFrom"}), 400
        if date_to and not date_to_dt:
            return jsonify({"ok": False, "msg": "invalid dateTo"}), 400
        if date_from_dt and date_to_dt and date_from_dt > date_to_dt:
            return jsonify({"ok": False, "msg": "dateFrom must be <= dateTo"}), 400
        if date_from_dt:
            sql += " AND date >= %s"
            params.append(date_from_dt.strftime("%Y-%m-%d"))
        if date_to_dt:
            sql += " AND date <= %s"
            params.append(date_to_dt.strftime("%Y-%m-%d"))
    sql += " ORDER BY id DESC"
    rows = query(sql, params)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "lab_name", "user_name", "date", "time",
        "reason", "status", "reject_reason", "admin_note", "created_at"
    ])
    for r in rows:
        writer.writerow([
            r.get("id"), r.get("lab_name"), r.get("user_name"), r.get("date"), r.get("time"),
            r.get("reason"), r.get("status"), r.get("reject_reason"), r.get("admin_note"), r.get("created_at")
        ])
    csv_data = output.getvalue()
    return (csv_data, 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": "attachment; filename=reservations.csv"
    })


@app.get("/notifications")
@auth_required()
def notifications():
    user = (g.current_user.get("username") or "").strip()
    type_filter = request.args.get("type", "").strip()
    if not user:
        return jsonify([])

    allowed_types = {"reservation", "lostfound"}
    types = set()
    if type_filter:
        for part in type_filter.split(","):
            p = part.strip()
            if p in allowed_types:
                types.add(p)
    else:
        types = set(allowed_types)

    notices = []

    if "reservation" in types:
        reservation_rows = query(
            """
            SELECT id, lab_name AS labName, status, reject_reason AS rejectReason,
                   admin_note AS adminNote, created_at AS createdAt
            FROM reservation
            WHERE user_name=%s
            ORDER BY id DESC
            LIMIT 100
            """,
            (user,),
        )
        for r in reservation_rows:
            status = r.get("status") or ""
            if status == "approved":
                msg = "预约已通过"
            elif status == "rejected":
                msg = f"预约已驳回：{r.get('rejectReason') or ''}"
            elif status == "cancelled":
                msg = "预约已取消"
            elif status == "pending":
                msg = "预约待审批"
            else:
                msg = f"预约状态：{status}"

            note = (r.get("adminNote") or "").strip()
            if note:
                msg = f"{msg}（备注：{note}）"
            notices.append(
                {
                    "id": f"reservation-{r.get('id')}",
                    "type": "reservation",
                    "labName": r.get("labName"),
                    "status": status,
                    "message": msg,
                    "createdAt": _to_text_time(r.get("createdAt")),
                    "_sortAt": _to_datetime(r.get("createdAt")),
                }
            )

    if "lostfound" in types:
        lost_found_rows = query(
            """
            SELECT id, title, item_type AS type, status, owner,
                   claim_student_id AS claimStudentId,
                   claim_name AS claimName,
                   claim_class AS claimClass,
                   claim_apply_status AS claimApplyStatus,
                   claim_apply_user AS claimApplyUser,
                   claim_apply_name AS claimApplyName,
                   claim_apply_reason AS claimApplyReason,
                   claim_apply_at AS claimApplyAt,
                   claim_reviewed_at AS claimReviewedAt,
                   claim_review_note AS claimReviewNote,
                   created_at AS createdAt
            FROM lost_found
            WHERE owner=%s OR claim_apply_user=%s
            ORDER BY id DESC
            LIMIT 100
            """,
            (user, user),
        )
        for r in lost_found_rows:
            title = r.get("title") or "失物招领"
            row_type = r.get("type") or ""
            owner = (r.get("owner") or "").strip()
            claim_apply_status = (r.get("claimApplyStatus") or "").strip()
            claim_apply_user = (r.get("claimApplyUser") or "").strip()

            # owner notifications
            if owner == user:
                if row_type == "found":
                    if claim_apply_status == "pending":
                        who = (r.get("claimApplyName") or claim_apply_user or "用户")
                        notices.append(
                            {
                                "id": f"lostfound-owner-{r.get('id')}-pending",
                                "type": "lostfound",
                                "labName": title,
                                "status": "claim_pending",
                                "message": f"你拾到的物品《{title}》收到认领申请：{who}",
                                "createdAt": _to_text_time(r.get("claimApplyAt") or r.get("createdAt")),
                                "_sortAt": _to_datetime(r.get("claimApplyAt") or r.get("createdAt")),
                            }
                        )
                    elif claim_apply_status == "approved":
                        claim_text = "、".join(
                            [x for x in [r.get("claimStudentId"), r.get("claimName"), r.get("claimClass")] if x]
                        )
                        msg = f"你拾到的物品《{title}》已完成认领"
                        if claim_text:
                            msg = f"{msg}（认领信息：{claim_text}）"
                        notices.append(
                            {
                                "id": f"lostfound-owner-{r.get('id')}-approved",
                                "type": "lostfound",
                                "labName": title,
                                "status": "claim_approved",
                                "message": msg,
                                "createdAt": _to_text_time(r.get("claimReviewedAt") or r.get("createdAt")),
                                "_sortAt": _to_datetime(r.get("claimReviewedAt") or r.get("createdAt")),
                            }
                        )
                    elif claim_apply_status == "rejected":
                        note = (r.get("claimReviewNote") or "").strip()
                        msg = f"你拾到的物品《{title}》的认领申请已驳回"
                        if note:
                            msg = f"{msg}（原因：{note}）"
                        notices.append(
                            {
                                "id": f"lostfound-owner-{r.get('id')}-rejected",
                                "type": "lostfound",
                                "labName": title,
                                "status": "claim_rejected",
                                "message": msg,
                                "createdAt": _to_text_time(r.get("claimReviewedAt") or r.get("createdAt")),
                                "_sortAt": _to_datetime(r.get("claimReviewedAt") or r.get("createdAt")),
                            }
                        )
                    else:
                        row_status = (r.get("status") or "").strip()
                        if row_status == "closed":
                            claim_text = "、".join(
                                [x for x in [r.get("claimStudentId"), r.get("claimName"), r.get("claimClass")] if x]
                            )
                            msg = f"你拾到的物品《{title}》已处理"
                            if claim_text:
                                msg = f"{msg}（认领信息：{claim_text}）"
                        else:
                            msg = f"你拾到的物品《{title}》处理中"
                        notices.append(
                            {
                                "id": f"lostfound-owner-{r.get('id')}-open",
                                "type": "lostfound",
                                "labName": title,
                                "status": row_status or "open",
                                "message": msg,
                                "createdAt": _to_text_time(r.get("createdAt")),
                                "_sortAt": _to_datetime(r.get("createdAt")),
                            }
                        )
                else:
                    status = r.get("status") or ""
                    if status == "closed":
                        claim_text = "、".join(
                            [x for x in [r.get("claimStudentId"), r.get("claimName"), r.get("claimClass")] if x]
                        )
                        msg = f"你发布的失物《{title}》已处理"
                        if claim_text:
                            msg = f"{msg}（认领信息：{claim_text}）"
                    else:
                        msg = f"你发布的失物《{title}》处理中"
                    notices.append(
                        {
                            "id": f"lostfound-owner-{r.get('id')}-status",
                            "type": "lostfound",
                            "labName": title,
                            "status": status,
                            "message": msg,
                            "createdAt": _to_text_time(r.get("createdAt")),
                            "_sortAt": _to_datetime(r.get("createdAt")),
                        }
                    )

            # claimant notifications
            if claim_apply_user == user and owner != user:
                if claim_apply_status == "pending":
                    msg = f"你提交的《{title}》认领申请待审核"
                    status = "claim_pending"
                    at = r.get("claimApplyAt") or r.get("createdAt")
                elif claim_apply_status == "approved":
                    msg = f"你提交的《{title}》认领申请已通过"
                    status = "claim_approved"
                    at = r.get("claimReviewedAt") or r.get("createdAt")
                elif claim_apply_status == "rejected":
                    note = (r.get("claimReviewNote") or "").strip()
                    msg = f"你提交的《{title}》认领申请已驳回"
                    if note:
                        msg = f"{msg}（原因：{note}）"
                    status = "claim_rejected"
                    at = r.get("claimReviewedAt") or r.get("createdAt")
                else:
                    msg = f"你提交的《{title}》认领申请处理中"
                    status = "claim_pending"
                    at = r.get("claimApplyAt") or r.get("createdAt")
                notices.append(
                    {
                        "id": f"lostfound-claimant-{r.get('id')}-{claim_apply_status or 'none'}",
                        "type": "lostfound",
                        "labName": title,
                        "status": status,
                        "message": msg,
                        "createdAt": _to_text_time(at),
                        "_sortAt": _to_datetime(at),
                    }
                )

    notices.sort(key=lambda x: x.get("_sortAt", datetime.min), reverse=True)
    for n in notices:
        n.pop("_sortAt", None)
    return jsonify(notices[:100])


@app.get("/announcements")
@auth_required()
def get_announcements():
    limit_raw = request.args.get("limit", "").strip()
    try:
        limit = int(limit_raw or "20")
    except ValueError:
        limit = 20
    limit = max(1, min(limit, 100))

    rows = query(
        """
        SELECT id,
               title,
               content,
               publisher_name AS publisherName,
               created_at AS createdAt
        FROM announcement
        ORDER BY id DESC
        LIMIT %s
        """,
        (limit,),
    )

    data = []
    for row in rows:
        data.append(
            {
                "id": row.get("id"),
                "title": row.get("title") or "",
                "content": row.get("content") or "",
                "publisherName": row.get("publisherName") or "",
                "createdAt": _to_text_time(row.get("createdAt")),
                "type": "announcement",
            }
        )
    return jsonify({"ok": True, "data": data})


@app.post("/announcements")
@auth_required(roles=["admin"])
def publish_announcement():
    payload = request.get_json(force=True) or {}
    title = str(payload.get("title") or "").strip()
    content = str(payload.get("content") or "").strip()

    if not title:
        return jsonify({"ok": False, "msg": "title required"}), 400
    if not content:
        return jsonify({"ok": False, "msg": "content required"}), 400
    if len(title) > 120:
        return jsonify({"ok": False, "msg": "title too long"}), 400
    if len(content) > 5000:
        return jsonify({"ok": False, "msg": "content too long"}), 400

    current_user = g.current_user or {}
    publisher_id = _to_int_or_none(current_user.get("id"))
    publisher_name = str(current_user.get("username") or "").strip()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_id = execute_insert(
        """
        INSERT INTO announcement (title, content, publisher_id, publisher_name, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (title, content, publisher_id, publisher_name, created_at),
    )

    audit_log(
        "admin.announcement.publish",
        target_type="announcement",
        target_id=new_id,
        detail={"title": title},
    )

    return jsonify(
        {
            "ok": True,
            "data": {
                "id": new_id,
                "title": title,
                "content": content,
                "publisherName": publisher_name,
                "createdAt": created_at,
                "type": "announcement",
            },
        }
    )


@app.post("/reservations/<int:rid>/approve")
@auth_required(roles=["admin"])
def approve_reservation(rid):
    try:
        def _tx(cur):
            cur.execute(
                """
                SELECT id, lab_name AS labName, date, time, status
                FROM reservation
                WHERE id=%s
                LIMIT 1
                FOR UPDATE
                """,
                (rid,),
            )
            row = cur.fetchone()
            if not row:
                raise BizError("reservation not found", 404)
            if row["status"] != "pending":
                raise BizError("invalid status", 409)

            schedule_error = validate_reservation_schedule(row["date"], row["time"])
            if schedule_error:
                raise BizError(f"invalid reservation schedule: {schedule_error}", 400)

            lock_key = _reservation_lock_key(row["labName"], row["date"])
            if not _acquire_named_lock(cur, lock_key):
                raise BizError("reservation busy, try again", 409)
            try:
                if has_approved_conflict_with_cur(cur, row["labName"], row["date"], row["time"], exclude_id=rid):
                    raise BizError("reservation conflict with approved", 409)
                cur.execute(
                    """
                    UPDATE reservation
                    SET status='approved', reject_reason=''
                    WHERE id=%s AND status='pending'
                    """,
                    (rid,),
                )
                if cur.rowcount != 1:
                    raise BizError("reservation status changed, retry", 409)
            finally:
                _release_named_lock(cur, lock_key)

        run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log("admin.reservation.approve", target_type="reservation", target_id=rid)
    return jsonify({"ok": True})


@app.post("/reservations/<int:rid>/reject")
@auth_required(roles=["admin"])
def reject_reservation(rid):
    data = request.get_json(force=True) or {}
    reason = (data.get("rejectReason") or "").strip()
    try:
        def _tx(cur):
            cur.execute("SELECT id, status FROM reservation WHERE id=%s LIMIT 1 FOR UPDATE", (rid,))
            row = cur.fetchone()
            if not row:
                raise BizError("reservation not found", 404)
            if row["status"] != "pending":
                raise BizError("invalid status", 409)
            cur.execute(
                "UPDATE reservation SET status='rejected', reject_reason=%s WHERE id=%s AND status='pending'",
                (reason, rid),
            )
            if cur.rowcount != 1:
                raise BizError("reservation status changed, retry", 409)

        run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    audit_log(
        "admin.reservation.reject",
        target_type="reservation",
        target_id=rid,
        detail={"rejectReason": reason},
    )
    return jsonify({"ok": True})


@app.post("/reservations/<int:rid>/note")
@auth_required(roles=["admin"])
def add_reservation_note(rid):
    data = request.get_json(force=True) or {}
    note = (data.get("note") or "").strip()
    if not note:
        return jsonify({"ok": False, "msg": "params error"}), 400

    row = query("SELECT id FROM reservation WHERE id=%s LIMIT 1", (rid,))
    if not row:
        return jsonify({"ok": False, "msg": "reservation not found"}), 404

    execute("UPDATE reservation SET admin_note=%s WHERE id=%s", (note, rid))
    audit_log(
        "admin.reservation.note",
        target_type="reservation",
        target_id=rid,
        detail={"note": note},
    )
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
