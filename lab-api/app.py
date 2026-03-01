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
from collections import deque
from threading import Lock
from functools import wraps
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
RESERVATION_MIN_DAYS_AHEAD = env_int("RESERVATION_MIN_DAYS_AHEAD", 0)
RESERVATION_MAX_DAYS_AHEAD = env_int("RESERVATION_MAX_DAYS_AHEAD", 30)
RESERVATION_MIN_TIME = os.getenv("RESERVATION_MIN_TIME", "08:00")
RESERVATION_MAX_TIME = os.getenv("RESERVATION_MAX_TIME", "22:00")
RESERVATION_LOCK_TIMEOUT_SECONDS = env_int("RESERVATION_LOCK_TIMEOUT_SECONDS", 5)
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


def parse_slots(time_range):
    return {t.strip() for t in (time_range or "").split(",") if t.strip()}


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


def get_reservation_rules_payload():
    today = datetime.now().date()
    min_days = max(0, RESERVATION_MIN_DAYS_AHEAD)
    max_days = max(min_days, RESERVATION_MAX_DAYS_AHEAD)
    min_date = (today + timedelta(days=min_days)).strftime("%Y-%m-%d")
    max_date = (today + timedelta(days=max_days)).strftime("%Y-%m-%d")
    return {
        "minDaysAhead": min_days,
        "maxDaysAhead": max_days,
        "minTime": RESERVATION_MIN_TIME,
        "maxTime": RESERVATION_MAX_TIME,
        "minDate": min_date,
        "maxDate": max_date,
    }


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
    schedule_error = validate_reservation_schedule(date, time_range)
    if schedule_error:
        return jsonify({"ok": False, "msg": schedule_error}), 400

    lab_row = query("SELECT id, name FROM lab WHERE name=%s LIMIT 1", (lab_name,))
    if not lab_row:
        return jsonify({"ok": False, "msg": "lab not found"}), 404
    lab_id = lab_row[0]["id"]

    created_at = datetime.now().isoformat(timespec="seconds")

    try:
        def _tx(cur):
            lock_key = _reservation_lock_key(lab_name, date)
            if not _acquire_named_lock(cur, lock_key):
                raise BizError("reservation busy, try again", 409)
            try:
                if has_approved_conflict_with_cur(cur, lab_name, date, time_range):
                    raise BizError("reservation conflict with approved", 409)
                cur.execute(
                    """
                    INSERT INTO reservation (lab_id, lab_name, user_name, date, time, reason, status, reject_reason, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,'pending','',%s)
                    """,
                    (lab_id, lab_name, user_name, date, time_range, reason, created_at),
                )
                return cur.lastrowid
            finally:
                _release_named_lock(cur, lock_key)

        new_id = run_in_transaction(_tx)
    except BizError as e:
        return jsonify({"ok": False, "msg": e.msg}), e.status

    return jsonify({"ok": True, "data": {"id": new_id}})


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
