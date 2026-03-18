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
from urllib import parse as urlparse
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
RESERVATION_APPROVAL_MODE = str(os.getenv("RESERVATION_APPROVAL_MODE", "admin") or "").strip().lower()
RESERVATION_PEAK_FORCE_APPROVAL = str(os.getenv("RESERVATION_PEAK_FORCE_APPROVAL", "0") or "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
RESERVATION_PEAK_SLOTS_TEXT = str(os.getenv("RESERVATION_PEAK_SLOTS", "") or "").strip()
RESERVATION_APPROVAL_MODE_SET = {"auto", "teacher", "admin"}
RESERVATION_RULE_CONFIG_CACHE_SECONDS = max(1, env_int("RESERVATION_RULE_CONFIG_CACHE_SECONDS", 5))
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "").strip()
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn").strip().rstrip("/")
SILICONFLOW_MODEL = os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct").strip()
SILICONFLOW_TIMEOUT_SECONDS = env_int("SILICONFLOW_TIMEOUT_SECONDS", 20)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
TAVILY_BASE_URL = os.getenv("TAVILY_BASE_URL", "https://api.tavily.com").strip().rstrip("/")
TAVILY_TIMEOUT_SECONDS = env_int("TAVILY_TIMEOUT_SECONDS", 15)
AGENT_WEB_SEARCH_MAX_RESULTS = max(1, min(8, env_int("AGENT_WEB_SEARCH_MAX_RESULTS", 5)))
OPEN_METEO_GEOCODING_BASE_URL = os.getenv("OPEN_METEO_GEOCODING_BASE_URL", "https://geocoding-api.open-meteo.com").strip().rstrip("/")
OPEN_METEO_FORECAST_BASE_URL = os.getenv("OPEN_METEO_FORECAST_BASE_URL", "https://api.open-meteo.com").strip().rstrip("/")
OPEN_METEO_TIMEOUT_SECONDS = env_int("OPEN_METEO_TIMEOUT_SECONDS", 12)
KNOWLEDGE_CHUNK_CHAR_LIMIT = max(200, min(1200, env_int("KNOWLEDGE_CHUNK_CHAR_LIMIT", 420)))
KNOWLEDGE_CHUNK_OVERLAP = max(20, min(200, env_int("KNOWLEDGE_CHUNK_OVERLAP", 60)))
KNOWLEDGE_SEARCH_TOP_K = max(1, min(8, env_int("KNOWLEDGE_SEARCH_TOP_K", 4)))
KNOWLEDGE_SCOPE_ROLE_SET = {"all", "student", "teacher", "admin"}
KNOWLEDGE_CATEGORY_SET = {"rule", "manual", "safety", "course", "repair", "faq", "other"}
_RATE_LIMIT_BUCKETS = {}
_RATE_LIMIT_LOCK = Lock()
_RESERVATION_RULE_LOCK = Lock()
_RESERVATION_RULE_CACHE = {"expireAt": 0.0, "payload": None}
AGENT_PENDING_TTL_SECONDS = max(60, env_int("AGENT_PENDING_TTL_SECONDS", 600))
_AGENT_PENDING_LOCK = Lock()
_AGENT_PENDING_CONTEXT = {}
AI_PERMISSION_RESERVATION_CHECK_OCCUPANCY = "ai.reservation.check_occupancy"
AI_PERMISSION_RESERVATION_VIEW_OWNER = "ai.reservation.view_owner"
AI_PERMISSION_CODE_SET = {
    AI_PERMISSION_RESERVATION_CHECK_OCCUPANCY,
    AI_PERMISSION_RESERVATION_VIEW_OWNER,
}
PERMISSION_DUTY_OPERATOR = "duty.operator"
PERMISSION_ASSET_MANAGER = "asset.manager"
PERMISSION_SCHEDULE_MANAGER = "schedule.manager"
PERMISSION_AUDIT_VIEWER = "audit.viewer"
GENERAL_PERMISSION_CODE_SET = {
    PERMISSION_DUTY_OPERATOR,
    PERMISSION_ASSET_MANAGER,
    PERMISSION_SCHEDULE_MANAGER,
    PERMISSION_AUDIT_VIEWER,
}
RESERVATION_PRIVATE_VIEW_ROLE_SET = {"admin"}
RESERVATION_ACTIVE_STATUS_SET = {"pending", "approved"}
AGENT_TOOL_WHITELIST = {
    "reservation_summary",
    "repair_list",
    "repair_create",
    "repair_advice",
    "alarm_advice",
    "lab_reservation_list",
    "progress_summary",
    "availability",
    "cancel_lab",
    "cancel_reservation_prepare",
    "cancel_reservation_execute",
    "cancel_reservation_abort",
    "cancel_all_prepare",
    "cancel_all_confirm",
    "cancel_all_abort",
    "reschedule",
    "reschedule_prepare",
    "reschedule_execute",
    "reschedule_abort",
    "reserve_create",
    "rule_explain",
    "update_profile",
    "general_reply",
}
AGENT_MULTI_TURN_TOOL_INTENT_MAP = {
    "reserve_create": "reserve_create",
    "lab_reservation_list": "reserve_query",
    "repair_create": "repair_create",
}
AGENT_MULTI_TURN_INTENT_TOOL_MAP = {v: k for k, v in AGENT_MULTI_TURN_TOOL_INTENT_MAP.items()}
AGENT_PENDING_STATE_SET = {"collecting", "confirming"}
AGENT_PENDING_SLOT_LABELS = {
    "labName": "实验室名称",
    "date": "日期",
    "time": "时间段",
    "reason": "用途",
    "selectedPlanId": "备选方案",
    "description": "故障描述",
    "location": "报修位置",
    "equipmentHint": "设备编号",
}
AGENT_PENDING_SLOT_QUESTIONS = {
    "labName": "请告诉我实验室名称。",
    "date": "请告诉我预约日期（例如 2026-03-05）。",
    "time": "请告诉我预约时间段（例如 1-2节 或 08:00-08:40）。",
    "reason": "请告诉我预约用途。",
    "selectedPlanId": "请选择方案（例如：选2 / 方案B / 第一个）。",
    "description": "请描述故障现象。",
    "location": "报修位置是哪个实验室或设备编号？",
    "equipmentHint": "请补充设备编号（例如 PC-A1）。",
}
AGENT_MULTI_TURN_SCHEMA = {
    "reserve_create": {
        "required": ["labName", "date", "time"],
        "optional": ["reason"],
    },
    "reserve_query": {
        "required": ["labName"],
        "optional": ["date", "time"],
    },
    "repair_create": {
        "required": ["description", "location"],
        "optional": ["issueType", "labName", "equipmentHint"],
    },
    "reserve_plan_pick": {
        "required": ["selectedPlanId"],
        "optional": ["plans", "reason", "labName", "date", "time"],
    },
}
AGENT_CONFIRM_TEXT_SET = {"确认", "确定", "好", "好的", "可以", "行", "ok", "yes", "确认继续", "确认提交"}
AGENT_CANCEL_TEXT_SET = {"取消", "取消吧", "算了", "不用了", "不", "否", "no", "重来", "重新来", "重新开始", "从头开始"}
AGENT_REPAIR_ISSUE_ALIAS = {
    "computer": "computer",
    "pc": "computer",
    "lighting": "lighting",
    "light": "lighting",
    "floor": "floor",
    "network": "network",
    "wifi": "network",
    "other": "other",
}
AGENT_REPAIR_ISSUE_SET = {"computer", "lighting", "floor", "network", "other"}
REPAIR_TRIAGE_ISSUE_ALIAS = {
    "computer": "computer",
    "pc": "computer",
    "host": "computer",
    "lighting": "lighting",
    "light": "lighting",
    "floor": "floor",
    "desk": "floor",
    "chair": "floor",
    "network": "network",
    "wifi": "network",
    "internet": "network",
    "other": "other",
    "unknown": "other",
}
REPAIR_TRIAGE_ISSUE_SET = {"computer", "lighting", "floor", "network", "other"}
REPAIR_TRIAGE_PRIORITY_SET = {"P0", "P1", "P2"}
NOTIFICATION_TYPE_ITEMS = ("reservation", "repair", "sensor_alarm", "lostfound", "course_task", "asset_borrow")
NOTIFICATION_TYPE_SET = set(NOTIFICATION_TYPE_ITEMS)


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


def ensure_user_profile_columns():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "nickname": "VARCHAR(64) NOT NULL DEFAULT ''",
            "phone": "VARCHAR(32) NOT NULL DEFAULT ''",
            "email": "VARCHAR(128) NOT NULL DEFAULT ''",
            "student_no": "VARCHAR(64) NOT NULL DEFAULT ''",
            "job_no": "VARCHAR(64) NOT NULL DEFAULT ''",
            "avatar_url": "VARCHAR(255) NOT NULL DEFAULT ''",
        }
        with conn.cursor() as cur:
            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='user'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE user ADD COLUMN {col} {ddl}")
        conn.commit()
    finally:
        conn.close()


def ensure_user_governance_columns():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "is_active": "TINYINT(1) NOT NULL DEFAULT 1",
            "is_frozen": "TINYINT(1) NOT NULL DEFAULT 0",
            "last_login_at": "DATETIME NULL",
            "last_login_ip": "VARCHAR(64) NOT NULL DEFAULT ''",
            "class_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "graduation_year": "INT NOT NULL DEFAULT 0",
        }
        with conn.cursor() as cur:
            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='user'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE user ADD COLUMN {col} {ddl}")
            cur.execute("UPDATE user SET is_active=1 WHERE is_active IS NULL")
            cur.execute("UPDATE user SET is_frozen=0 WHERE is_frozen IS NULL")
            cur.execute("UPDATE user SET class_name='' WHERE class_name IS NULL")
            cur.execute("UPDATE user SET graduation_year=0 WHERE graduation_year IS NULL")
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
            extra_columns = {
                "device_name": "VARCHAR(128) NOT NULL DEFAULT ''",
                "user_agent": "VARCHAR(255) NOT NULL DEFAULT ''",
                "login_ip": "VARCHAR(64) NOT NULL DEFAULT ''",
                "last_seen_at": "DATETIME NULL",
            }
            for col, ddl in extra_columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='auth_refresh_token'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE auth_refresh_token ADD COLUMN {col} {ddl}")
            cur.execute("UPDATE auth_refresh_token SET last_seen_at=created_at WHERE last_seen_at IS NULL")
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


def ensure_reservation_rule_config_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS reservation_rule_config (
                    id INT PRIMARY KEY,
                    config_json LONGTEXT NOT NULL,
                    updated_by VARCHAR(64) NOT NULL DEFAULT '',
                    updated_at DATETIME NOT NULL,
                    INDEX idx_updated_at (updated_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_reservation_review_columns():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "review_role": "VARCHAR(16) NOT NULL DEFAULT 'admin'",
            "review_policy": "VARCHAR(32) NOT NULL DEFAULT ''",
        }
        with conn.cursor() as cur:
            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='reservation'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE reservation ADD COLUMN {col} {ddl}")
        conn.commit()
    finally:
        conn.close()


def ensure_reservation_query_indexes():
    conn = pymysql.connect(**DB)
    try:
        indexes = {
            "idx_reservation_lab_date_status": "lab_name, date, status",
            "idx_reservation_user_status": "user_name, status",
        }
        with conn.cursor() as cur:
            for index_name, column_sql in indexes.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='reservation'
                      AND INDEX_NAME=%s
                    """,
                    (DB["database"], index_name),
                )
                has_index = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_index:
                    cur.execute(f"ALTER TABLE reservation ADD INDEX {index_name} ({column_sql})")
        conn.commit()
    finally:
        conn.close()


def ensure_ai_user_permission_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_user_permission (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id BIGINT NOT NULL DEFAULT 0,
                    username VARCHAR(64) NOT NULL DEFAULT '',
                    permission_code VARCHAR(128) NOT NULL DEFAULT '',
                    granted_by BIGINT NULL,
                    granted_by_name VARCHAR(64) NOT NULL DEFAULT '',
                    expires_at DATETIME NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_ai_user_permission_user_code (user_id, permission_code),
                    INDEX idx_ai_user_permission_username (username),
                    INDEX idx_ai_user_permission_code_expires (permission_code, expires_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_user_permission_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_permission (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id BIGINT NOT NULL DEFAULT 0,
                    username VARCHAR(64) NOT NULL DEFAULT '',
                    permission_code VARCHAR(128) NOT NULL DEFAULT '',
                    granted_by BIGINT NULL,
                    granted_by_name VARCHAR(64) NOT NULL DEFAULT '',
                    expires_at DATETIME NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_user_permission_user_code (user_id, permission_code),
                    INDEX idx_user_permission_username (username),
                    INDEX idx_user_permission_code_expires (permission_code, expires_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_duty_roster_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS duty_roster (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    duty_date DATE NOT NULL,
                    shift_name VARCHAR(32) NOT NULL DEFAULT '',
                    assignee_name VARCHAR(64) NOT NULL DEFAULT '',
                    assignee_phone VARCHAR(32) NOT NULL DEFAULT '',
                    backup_name VARCHAR(64) NOT NULL DEFAULT '',
                    backup_phone VARCHAR(32) NOT NULL DEFAULT '',
                    status VARCHAR(16) NOT NULL DEFAULT 'scheduled',
                    note VARCHAR(255) NOT NULL DEFAULT '',
                    created_by VARCHAR(64) NOT NULL DEFAULT '',
                    updated_by VARCHAR(64) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_duty_roster_date (duty_date),
                    INDEX idx_duty_roster_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_emergency_contact_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS emergency_contact (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(64) NOT NULL DEFAULT '',
                    role_name VARCHAR(64) NOT NULL DEFAULT '',
                    phone VARCHAR(32) NOT NULL DEFAULT '',
                    priority_no INT NOT NULL DEFAULT 100,
                    status VARCHAR(16) NOT NULL DEFAULT 'active',
                    description VARCHAR(255) NOT NULL DEFAULT '',
                    created_by VARCHAR(64) NOT NULL DEFAULT '',
                    updated_by VARCHAR(64) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_emergency_contact_status (status),
                    INDEX idx_emergency_contact_priority (priority_no)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_incident_record_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_record (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    incident_no VARCHAR(32) NOT NULL DEFAULT '',
                    lab_id BIGINT NULL,
                    lab_name VARCHAR(128) NOT NULL DEFAULT '',
                    title VARCHAR(120) NOT NULL DEFAULT '',
                    incident_level VARCHAR(16) NOT NULL DEFAULT 'medium',
                    status VARCHAR(16) NOT NULL DEFAULT 'reported',
                    reporter_name VARCHAR(64) NOT NULL DEFAULT '',
                    reporter_phone VARCHAR(32) NOT NULL DEFAULT '',
                    emergency_contact_name VARCHAR(64) NOT NULL DEFAULT '',
                    description TEXT NULL,
                    disposal_note TEXT NULL,
                    closed_at DATETIME NULL,
                    created_by VARCHAR(64) NOT NULL DEFAULT '',
                    updated_by VARCHAR(64) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_incident_record_no (incident_no),
                    INDEX idx_incident_record_status (status),
                    INDEX idx_incident_record_level (incident_level),
                    INDEX idx_incident_record_lab (lab_id),
                    INDEX idx_incident_record_created_at (created_at)
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
                    publish_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    is_pinned TINYINT(1) NOT NULL DEFAULT 0,
                    pinned_at DATETIME NULL,
                    INDEX idx_created_at (created_at),
                    INDEX idx_publish_at (publish_at),
                    INDEX idx_is_pinned (is_pinned),
                    INDEX idx_pinned_at (pinned_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_announcement_manage_columns():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "publish_at": "DATETIME NULL",
            "updated_at": "DATETIME NULL",
            "is_pinned": "TINYINT(1) NOT NULL DEFAULT 0",
            "pinned_at": "DATETIME NULL",
            "status": "VARCHAR(16) NOT NULL DEFAULT 'published'",
            "category": "VARCHAR(32) NOT NULL DEFAULT 'general'",
            "audience_type": "VARCHAR(16) NOT NULL DEFAULT 'all'",
            "audience_course_ids": "VARCHAR(255) NOT NULL DEFAULT ''",
            "content_format": "VARCHAR(16) NOT NULL DEFAULT 'plain'",
            "attachments_json": "TEXT NULL",
            "down_at": "DATETIME NULL",
            "is_carousel": "TINYINT(1) NOT NULL DEFAULT 0",
            "nudge_count": "INT NOT NULL DEFAULT 0",
            "last_nudged_at": "DATETIME NULL",
        }
        indexes = {
            "idx_publish_at": "publish_at",
            "idx_is_pinned": "is_pinned",
            "idx_pinned_at": "pinned_at",
            "idx_announcement_status": "status",
            "idx_announcement_category": "category",
            "idx_announcement_audience_type": "audience_type",
            "idx_announcement_down_at": "down_at",
            "idx_announcement_is_carousel": "is_carousel",
        }

        with conn.cursor() as cur:
            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='announcement'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE announcement ADD COLUMN {col} {ddl}")

            cur.execute("UPDATE announcement SET publish_at=created_at WHERE publish_at IS NULL")
            cur.execute("UPDATE announcement SET updated_at=created_at WHERE updated_at IS NULL")
            cur.execute("UPDATE announcement SET status='published' WHERE status IS NULL OR status=''")
            cur.execute("UPDATE announcement SET category='general' WHERE category IS NULL OR category=''")
            cur.execute("UPDATE announcement SET audience_type='all' WHERE audience_type IS NULL OR audience_type=''")
            cur.execute("UPDATE announcement SET audience_course_ids='' WHERE audience_course_ids IS NULL")
            cur.execute("UPDATE announcement SET content_format='plain' WHERE content_format IS NULL OR content_format=''")
            cur.execute("UPDATE announcement SET is_carousel=0 WHERE is_carousel IS NULL")
            cur.execute("UPDATE announcement SET nudge_count=0 WHERE nudge_count IS NULL")

            for index_name, column_name in indexes.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='announcement'
                      AND INDEX_NAME=%s
                    """,
                    (DB["database"], index_name),
                )
                has_index = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_index:
                    cur.execute(f"ALTER TABLE announcement ADD INDEX {index_name} ({column_name})")
        conn.commit()
    finally:
        conn.close()


def ensure_announcement_read_state_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS announcement_read_state (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    announcement_id BIGINT NOT NULL,
                    user_name VARCHAR(64) NOT NULL,
                    read_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    UNIQUE KEY uk_announcement_user (announcement_id, user_name),
                    INDEX idx_announcement_id (announcement_id),
                    INDEX idx_user_name (user_name),
                    INDEX idx_read_at (read_at),
                    INDEX idx_updated_at (updated_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_notification_read_state_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_read_state (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_name VARCHAR(64) NOT NULL,
                    notice_type VARCHAR(32) NOT NULL,
                    last_read_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    UNIQUE KEY uk_user_notice_type (user_name, notice_type),
                    INDEX idx_user_name (user_name),
                    INDEX idx_notice_type (notice_type),
                    INDEX idx_updated_at (updated_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_user_feedback_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_name VARCHAR(64) NOT NULL,
                    user_role VARCHAR(16) NOT NULL DEFAULT '',
                    feedback_type VARCHAR(32) NOT NULL DEFAULT '',
                    content TEXT NOT NULL,
                    contact VARCHAR(120) NOT NULL DEFAULT '',
                    source VARCHAR(32) NOT NULL DEFAULT 'app',
                    status VARCHAR(16) NOT NULL DEFAULT 'submitted',
                    admin_reply TEXT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    INDEX idx_user_name (user_name),
                    INDEX idx_user_role (user_role),
                    INDEX idx_feedback_type (feedback_type),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_agent_chat_message_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_chat_message (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_name VARCHAR(64) NOT NULL,
                    role VARCHAR(16) NOT NULL,
                    content TEXT NOT NULL,
                    action VARCHAR(64) NOT NULL DEFAULT '',
                    meta_json TEXT NULL,
                    created_at DATETIME NOT NULL,
                    INDEX idx_user_name (user_name),
                    INDEX idx_role (role),
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


def ensure_assets_tables():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS equipment (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    asset_code VARCHAR(64) NOT NULL UNIQUE,
                    name VARCHAR(128) NOT NULL,
                    model VARCHAR(128) NULL,
                    brand VARCHAR(128) NULL,
                    lab_id BIGINT NULL,
                    lab_name VARCHAR(128) NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'in_service',
                    keeper VARCHAR(128) NULL,
                    purchase_date DATE NULL,
                    price DECIMAL(10,2) NULL,
                    spec_json TEXT NULL,
                    image_url VARCHAR(255) NULL,
                    allow_borrow TINYINT(1) NOT NULL DEFAULT 1,
                    is_borrowed TINYINT(1) NOT NULL DEFAULT 0,
                    borrowed_by_id INT NULL,
                    borrowed_by VARCHAR(64) NOT NULL DEFAULT '',
                    borrowed_at DATETIME NULL,
                    expected_return_at DATETIME NULL,
                    last_returned_at DATETIME NULL,
                    last_transfer_from_lab_id BIGINT NULL,
                    last_transfer_from_lab_name VARCHAR(128) NOT NULL DEFAULT '',
                    last_transfer_at DATETIME NULL,
                    next_maintenance_at DATETIME NULL,
                    last_maintained_at DATETIME NULL,
                    maintenance_cycle_days INT NULL,
                    maintenance_note VARCHAR(255) NOT NULL DEFAULT '',
                    warranty_until DATE NULL,
                    qr_token VARCHAR(64) NOT NULL DEFAULT '',
                    barcode_value VARCHAR(128) NOT NULL DEFAULT '',
                    location_note VARCHAR(128) NOT NULL DEFAULT '',
                    scrap_reason VARCHAR(255) NOT NULL DEFAULT '',
                    scrapped_at DATETIME NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_lab_id (lab_id),
                    INDEX idx_status (status),
                    INDEX idx_allow_borrow (allow_borrow),
                    INDEX idx_is_borrowed (is_borrowed),
                    INDEX idx_next_maintenance_at (next_maintenance_at),
                    INDEX idx_warranty_until (warranty_until),
                    INDEX idx_qr_token (qr_token),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS equipment_event (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    equipment_id BIGINT NOT NULL,
                    event_type VARCHAR(32) NOT NULL,
                    operator_id INT NULL,
                    operator_name VARCHAR(128) NULL,
                    note TEXT NULL,
                    attachment_url VARCHAR(255) NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_equipment_id (equipment_id),
                    INDEX idx_event_type (event_type),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS repair_work_order (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    order_no VARCHAR(40) NOT NULL UNIQUE,
                    equipment_id BIGINT NULL,
                    asset_code VARCHAR(64) NOT NULL DEFAULT '',
                    equipment_name VARCHAR(128) NOT NULL DEFAULT '',
                    lab_id BIGINT NULL,
                    lab_name VARCHAR(128) NOT NULL DEFAULT '',
                    issue_type VARCHAR(32) NOT NULL DEFAULT 'other',
                    description TEXT NOT NULL,
                    attachment_url VARCHAR(255) NOT NULL DEFAULT '',
                    ai_issue_type VARCHAR(32) NULL,
                    ai_priority VARCHAR(8) NULL,
                    ai_suggestions TEXT NULL,
                    ai_confidence DECIMAL(5,4) NULL,
                    ai_raw_json TEXT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'submitted',
                    submitter_id INT NULL,
                    submitter_name VARCHAR(128) NOT NULL DEFAULT '',
                    assignee_id INT NULL,
                    assignee_name VARCHAR(128) NOT NULL DEFAULT '',
                    submitted_at DATETIME NOT NULL,
                    accepted_at DATETIME NULL,
                    processing_at DATETIME NULL,
                    completed_at DATETIME NULL,
                    followup_score INT NULL,
                    followup_comment VARCHAR(500) NOT NULL DEFAULT '',
                    followup_at DATETIME NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_rwo_equipment_id (equipment_id),
                    INDEX idx_rwo_lab_id (lab_id),
                    INDEX idx_rwo_status (status),
                    INDEX idx_rwo_submitter_name (submitter_name),
                    INDEX idx_rwo_assignee_name (assignee_name),
                    INDEX idx_rwo_submitted_at (submitted_at),
                    INDEX idx_rwo_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS equipment_inventory_session (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    inventory_no VARCHAR(40) NOT NULL UNIQUE,
                    lab_id BIGINT NULL,
                    lab_name VARCHAR(128) NOT NULL DEFAULT '',
                    status VARCHAR(16) NOT NULL DEFAULT 'open',
                    planned_count INT NOT NULL DEFAULT 0,
                    checked_count INT NOT NULL DEFAULT 0,
                    diff_count INT NOT NULL DEFAULT 0,
                    started_by VARCHAR(64) NOT NULL DEFAULT '',
                    started_at DATETIME NOT NULL,
                    closed_by VARCHAR(64) NOT NULL DEFAULT '',
                    closed_at DATETIME NULL,
                    note VARCHAR(255) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_inventory_lab_id (lab_id),
                    INDEX idx_inventory_status (status),
                    INDEX idx_inventory_started_at (started_at),
                    INDEX idx_inventory_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS equipment_inventory_item (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    session_id BIGINT NOT NULL,
                    equipment_id BIGINT NULL,
                    asset_code VARCHAR(64) NOT NULL DEFAULT '',
                    equipment_name VARCHAR(128) NOT NULL DEFAULT '',
                    expected_lab_id BIGINT NULL,
                    expected_lab_name VARCHAR(128) NOT NULL DEFAULT '',
                    scanned_lab_id BIGINT NULL,
                    scanned_lab_name VARCHAR(128) NOT NULL DEFAULT '',
                    scan_status VARCHAR(16) NOT NULL DEFAULT 'pending',
                    discrepancy_type VARCHAR(32) NOT NULL DEFAULT '',
                    scanned_by VARCHAR(64) NOT NULL DEFAULT '',
                    scanned_at DATETIME NULL,
                    note VARCHAR(255) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_inventory_session_asset (session_id, asset_code),
                    INDEX idx_inventory_item_session_id (session_id),
                    INDEX idx_inventory_item_equipment_id (equipment_id),
                    INDEX idx_inventory_item_status (scan_status),
                    INDEX idx_inventory_item_diff (discrepancy_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_equipment_borrow_tables():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS equipment_borrow_request (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    equipment_id BIGINT NOT NULL,
                    equipment_asset_code VARCHAR(64) NOT NULL DEFAULT '',
                    equipment_name VARCHAR(128) NOT NULL DEFAULT '',
                    equipment_lab_name VARCHAR(128) NOT NULL DEFAULT '',
                    applicant_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    applicant_role VARCHAR(16) NOT NULL DEFAULT '',
                    applicant_name VARCHAR(64) NOT NULL DEFAULT '',
                    applicant_student_no VARCHAR(64) NOT NULL DEFAULT '',
                    applicant_class_name VARCHAR(64) NOT NULL DEFAULT '',
                    applicant_job_no VARCHAR(64) NOT NULL DEFAULT '',
                    borrow_start_at DATETIME NOT NULL,
                    expected_return_at DATETIME NOT NULL,
                    purpose VARCHAR(255) NOT NULL DEFAULT '',
                    status VARCHAR(16) NOT NULL DEFAULT 'pending',
                    reject_reason VARCHAR(255) NOT NULL DEFAULT '',
                    admin_note VARCHAR(255) NOT NULL DEFAULT '',
                    remind_count INT NOT NULL DEFAULT 0,
                    last_remind_at DATETIME NULL,
                    approved_by VARCHAR(64) NOT NULL DEFAULT '',
                    approved_at DATETIME NULL,
                    returned_by VARCHAR(64) NOT NULL DEFAULT '',
                    returned_at DATETIME NULL,
                    risk_flag TINYINT(1) NOT NULL DEFAULT 0,
                    risk_reason VARCHAR(255) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_borrow_request_equipment_id (equipment_id),
                    INDEX idx_borrow_request_applicant (applicant_user_name),
                    INDEX idx_borrow_request_status (status),
                    INDEX idx_borrow_request_expected_return_at (expected_return_at),
                    INDEX idx_borrow_request_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS equipment_borrow_reminder_log (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    request_id BIGINT NOT NULL,
                    remind_type VARCHAR(16) NOT NULL DEFAULT 'manual',
                    remind_date DATE NOT NULL,
                    reminded_by VARCHAR(64) NOT NULL DEFAULT '',
                    message VARCHAR(255) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_borrow_reminder_unique (request_id, remind_type, remind_date),
                    INDEX idx_borrow_reminder_request_id (request_id),
                    INDEX idx_borrow_reminder_date (remind_date),
                    INDEX idx_borrow_reminder_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_equipment_lifecycle_columns():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "equipment": {
                "allow_borrow": "TINYINT(1) NOT NULL DEFAULT 1",
                "is_borrowed": "TINYINT(1) NOT NULL DEFAULT 0",
                "borrowed_by_id": "INT NULL",
                "borrowed_by": "VARCHAR(64) NOT NULL DEFAULT ''",
                "borrowed_at": "DATETIME NULL",
                "expected_return_at": "DATETIME NULL",
                "last_returned_at": "DATETIME NULL",
                "last_transfer_from_lab_id": "BIGINT NULL",
                "last_transfer_from_lab_name": "VARCHAR(128) NOT NULL DEFAULT ''",
                "last_transfer_at": "DATETIME NULL",
                "next_maintenance_at": "DATETIME NULL",
                "last_maintained_at": "DATETIME NULL",
                "maintenance_cycle_days": "INT NULL",
                "maintenance_note": "VARCHAR(255) NOT NULL DEFAULT ''",
                "warranty_until": "DATE NULL",
                "qr_token": "VARCHAR(64) NOT NULL DEFAULT ''",
                "barcode_value": "VARCHAR(128) NOT NULL DEFAULT ''",
                "location_note": "VARCHAR(128) NOT NULL DEFAULT ''",
                "scrap_reason": "VARCHAR(255) NOT NULL DEFAULT ''",
                "scrapped_at": "DATETIME NULL",
                "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
            },
            "equipment_inventory_session": {
                "inventory_no": "VARCHAR(40) NOT NULL DEFAULT ''",
                "lab_id": "BIGINT NULL",
                "lab_name": "VARCHAR(128) NOT NULL DEFAULT ''",
                "status": "VARCHAR(16) NOT NULL DEFAULT 'open'",
                "planned_count": "INT NOT NULL DEFAULT 0",
                "checked_count": "INT NOT NULL DEFAULT 0",
                "diff_count": "INT NOT NULL DEFAULT 0",
                "started_by": "VARCHAR(64) NOT NULL DEFAULT ''",
                "started_at": "DATETIME NULL",
                "closed_by": "VARCHAR(64) NOT NULL DEFAULT ''",
                "closed_at": "DATETIME NULL",
                "note": "VARCHAR(255) NOT NULL DEFAULT ''",
                "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
            },
            "equipment_inventory_item": {
                "session_id": "BIGINT NOT NULL DEFAULT 0",
                "equipment_id": "BIGINT NULL",
                "asset_code": "VARCHAR(64) NOT NULL DEFAULT ''",
                "equipment_name": "VARCHAR(128) NOT NULL DEFAULT ''",
                "expected_lab_id": "BIGINT NULL",
                "expected_lab_name": "VARCHAR(128) NOT NULL DEFAULT ''",
                "scanned_lab_id": "BIGINT NULL",
                "scanned_lab_name": "VARCHAR(128) NOT NULL DEFAULT ''",
                "scan_status": "VARCHAR(16) NOT NULL DEFAULT 'pending'",
                "discrepancy_type": "VARCHAR(32) NOT NULL DEFAULT ''",
                "scanned_by": "VARCHAR(64) NOT NULL DEFAULT ''",
                "scanned_at": "DATETIME NULL",
                "note": "VARCHAR(255) NOT NULL DEFAULT ''",
                "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
            },
        }

        indexes = {
            "equipment": {
                "idx_allow_borrow": "INDEX idx_allow_borrow (allow_borrow)",
                "idx_is_borrowed": "INDEX idx_is_borrowed (is_borrowed)",
                "idx_next_maintenance_at": "INDEX idx_next_maintenance_at (next_maintenance_at)",
                "idx_warranty_until": "INDEX idx_warranty_until (warranty_until)",
                "idx_qr_token": "INDEX idx_qr_token (qr_token)",
                "idx_updated_at": "INDEX idx_updated_at (updated_at)",
            },
            "equipment_inventory_session": {
                "idx_inventory_lab_id": "INDEX idx_inventory_lab_id (lab_id)",
                "idx_inventory_status": "INDEX idx_inventory_status (status)",
                "idx_inventory_started_at": "INDEX idx_inventory_started_at (started_at)",
            },
            "equipment_inventory_item": {
                "idx_inventory_item_session_id": "INDEX idx_inventory_item_session_id (session_id)",
                "idx_inventory_item_equipment_id": "INDEX idx_inventory_item_equipment_id (equipment_id)",
                "idx_inventory_item_status": "INDEX idx_inventory_item_status (scan_status)",
                "idx_inventory_item_diff": "INDEX idx_inventory_item_diff (discrepancy_type)",
            },
        }

        added_columns = {}
        with conn.cursor() as cur:
            for table, table_columns in columns.items():
                for col, ddl in table_columns.items():
                    cur.execute(
                        """
                        SELECT COUNT(*) AS cnt
                        FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA=%s
                          AND TABLE_NAME=%s
                          AND COLUMN_NAME=%s
                        """,
                        (DB["database"], table, col),
                    )
                    has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                    if not has_col:
                        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                        added_columns.setdefault(table, set()).add(col)

            for table, table_indexes in indexes.items():
                for index_name, ddl in table_indexes.items():
                    cur.execute(
                        """
                        SELECT COUNT(*) AS cnt
                        FROM information_schema.STATISTICS
                        WHERE TABLE_SCHEMA=%s
                          AND TABLE_NAME=%s
                          AND INDEX_NAME=%s
                        """,
                        (DB["database"], table, index_name),
                    )
                    has_idx = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                    if not has_idx:
                        cur.execute(f"ALTER TABLE {table} ADD {ddl}")

            if "allow_borrow" in added_columns.get("equipment", set()):
                cur.execute(
                    """
                    UPDATE equipment
                    SET allow_borrow=0
                    WHERE allow_borrow=1
                      AND ((lab_id IS NOT NULL AND lab_id>0) OR COALESCE(lab_name, '')<>'')
                      AND (
                          UPPER(COALESCE(asset_code, '')) LIKE 'PC-%'
                          OR COALESCE(name, '') LIKE '%电脑%'
                          OR LOWER(COALESCE(spec_json, '')) LIKE '%"category":"pc"%'
                          OR LOWER(COALESCE(spec_json, '')) LIKE '%"category":"computer"%'
                      )
                    """
                )

        conn.commit()
    finally:
        conn.close()


def ensure_repair_work_order_ai_columns():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "ai_issue_type": "VARCHAR(32) NULL",
            "ai_priority": "VARCHAR(8) NULL",
            "ai_suggestions": "TEXT NULL",
            "ai_confidence": "DECIMAL(5,4) NULL",
            "ai_raw_json": "TEXT NULL",
        }
        with conn.cursor() as cur:
            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='repair_work_order'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE repair_work_order ADD COLUMN {col} {ddl}")
        conn.commit()
    finally:
        conn.close()


def ensure_lab_sensor_alarm_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS lab_sensor_alarm (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    lab_id BIGINT NOT NULL,
                    lab_name VARCHAR(128) NOT NULL DEFAULT '',
                    alarm_code VARCHAR(64) NOT NULL,
                    level VARCHAR(16) NOT NULL DEFAULT 'alarm',
                    message VARCHAR(255) NOT NULL DEFAULT '',
                    metric_json TEXT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_lab_id (lab_id),
                    INDEX idx_alarm_code (alarm_code),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def _generate_course_code_with_cur(cur, used_codes=None):
    used = used_codes if isinstance(used_codes, set) else set()
    for _ in range(200):
        candidate = str((uuid.uuid4().int % 900000) + 100000)
        if candidate in used:
            continue
        cur.execute("SELECT id FROM course WHERE course_code=%s LIMIT 1", (candidate,))
        if cur.fetchone():
            continue
        used.add(candidate)
        return candidate
    raise RuntimeError("failed to generate unique course code")


def ensure_course_tables():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "description": "TEXT NULL",
            "class_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "course_code": "VARCHAR(6) NOT NULL DEFAULT ''",
            "teacher_id": "INT NULL",
            "teacher_user_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "status": "VARCHAR(16) NOT NULL DEFAULT 'enabled'",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        }
        indexes = {
            "idx_class_name": "class_name",
            "idx_teacher_user_name": "teacher_user_name",
            "idx_teacher_id": "teacher_id",
            "idx_status": "status",
            "idx_created_at": "created_at",
        }
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS course (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(120) NOT NULL DEFAULT '',
                    description TEXT NULL,
                    class_name VARCHAR(64) NOT NULL DEFAULT '',
                    course_code VARCHAR(6) NOT NULL DEFAULT '',
                    teacher_id INT NULL,
                    teacher_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    status VARCHAR(16) NOT NULL DEFAULT 'enabled',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_course_code (course_code),
                    INDEX idx_class_name (class_name),
                    INDEX idx_teacher_user_name (teacher_user_name),
                    INDEX idx_teacher_id (teacher_id),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='course'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE course ADD COLUMN {col} {ddl}")

            cur.execute("UPDATE course SET status='enabled' WHERE status IS NULL OR status=''")
            cur.execute("SELECT id, course_code AS courseCode FROM course ORDER BY id ASC")
            rows = cur.fetchall() or []
            used_codes = set()
            for row in rows:
                raw_code = str((row or {}).get("courseCode") or "").strip()
                if re.match(r"^\d{6}$", raw_code) and raw_code not in used_codes:
                    used_codes.add(raw_code)
                    continue
                new_code = _generate_course_code_with_cur(cur, used_codes)
                cur.execute("UPDATE course SET course_code=%s WHERE id=%s", (new_code, row.get("id")))

            for index_name, column_name in indexes.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='course'
                      AND INDEX_NAME=%s
                    """,
                    (DB["database"], index_name),
                )
                has_index = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_index:
                    cur.execute(f"ALTER TABLE course ADD INDEX {index_name} ({column_name})")

            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA=%s
                  AND TABLE_NAME='course'
                  AND INDEX_NAME='uk_course_code'
                """,
                (DB["database"],),
            )
            has_unique = int((cur.fetchone() or {}).get("cnt") or 0) > 0
            if not has_unique:
                cur.execute("ALTER TABLE course ADD UNIQUE INDEX uk_course_code (course_code)")

        conn.commit()
    finally:
        conn.close()


def ensure_experiment_task_tables():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "description": "TEXT NULL",
            "lab_id": "BIGINT NULL",
            "deadline": "DATETIME NULL",
            "teacher_id": "INT NULL",
            "teacher_user_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "status": "VARCHAR(16) NOT NULL DEFAULT 'active'",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        }
        indexes = {
            "idx_task_course_id": "course_id",
            "idx_task_lab_id": "lab_id",
            "idx_task_deadline": "deadline",
            "idx_task_teacher_user_name": "teacher_user_name",
            "idx_task_status": "status",
            "idx_task_created_at": "created_at",
        }
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS experiment_task (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    course_id BIGINT NOT NULL,
                    title VARCHAR(160) NOT NULL DEFAULT '',
                    description TEXT NULL,
                    lab_id BIGINT NULL,
                    deadline DATETIME NULL,
                    teacher_id INT NULL,
                    teacher_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    status VARCHAR(16) NOT NULL DEFAULT 'active',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_task_course_id (course_id),
                    INDEX idx_task_lab_id (lab_id),
                    INDEX idx_task_deadline (deadline),
                    INDEX idx_task_teacher_user_name (teacher_user_name),
                    INDEX idx_task_status (status),
                    INDEX idx_task_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='experiment_task'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE experiment_task ADD COLUMN {col} {ddl}")

            cur.execute("UPDATE experiment_task SET status='active' WHERE status IS NULL OR status=''")

            for index_name, column_name in indexes.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='experiment_task'
                      AND INDEX_NAME=%s
                    """,
                    (DB["database"], index_name),
                )
                has_index = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_index:
                    cur.execute(f"ALTER TABLE experiment_task ADD INDEX {index_name} ({column_name})")

        conn.commit()
    finally:
        conn.close()


def ensure_experiment_task_file_tables():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "course_id": "BIGINT NOT NULL DEFAULT 0",
            "file_name": "VARCHAR(255) NOT NULL DEFAULT ''",
            "file_url": "VARCHAR(255) NOT NULL DEFAULT ''",
            "file_size": "BIGINT NOT NULL DEFAULT 0",
            "mime_type": "VARCHAR(128) NOT NULL DEFAULT ''",
            "uploader_id": "INT NULL",
            "uploader_user_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "status": "VARCHAR(16) NOT NULL DEFAULT 'active'",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        }
        indexes = {
            "idx_task_file_task_id": "task_id",
            "idx_task_file_course_id": "course_id",
            "idx_task_file_uploader_user_name": "uploader_user_name",
            "idx_task_file_status": "status",
            "idx_task_file_created_at": "created_at",
        }
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS experiment_task_file (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    task_id BIGINT NOT NULL,
                    course_id BIGINT NOT NULL DEFAULT 0,
                    file_name VARCHAR(255) NOT NULL DEFAULT '',
                    file_url VARCHAR(255) NOT NULL DEFAULT '',
                    file_size BIGINT NOT NULL DEFAULT 0,
                    mime_type VARCHAR(128) NOT NULL DEFAULT '',
                    uploader_id INT NULL,
                    uploader_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    status VARCHAR(16) NOT NULL DEFAULT 'active',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_task_file_task_id (task_id),
                    INDEX idx_task_file_course_id (course_id),
                    INDEX idx_task_file_uploader_user_name (uploader_user_name),
                    INDEX idx_task_file_status (status),
                    INDEX idx_task_file_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='experiment_task_file'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE experiment_task_file ADD COLUMN {col} {ddl}")

            cur.execute("UPDATE experiment_task_file SET status='active' WHERE status IS NULL OR status=''")

            for index_name, column_name in indexes.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='experiment_task_file'
                      AND INDEX_NAME=%s
                    """,
                    (DB["database"], index_name),
                )
                has_index = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_index:
                    cur.execute(f"ALTER TABLE experiment_task_file ADD INDEX {index_name} ({column_name})")

        conn.commit()
    finally:
        conn.close()


def ensure_experiment_task_submission_tables():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "course_id": "BIGINT NOT NULL DEFAULT 0",
            "student_id": "INT NULL",
            "student_user_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "student_display_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "file_name": "VARCHAR(255) NOT NULL DEFAULT ''",
            "file_url": "VARCHAR(255) NOT NULL DEFAULT ''",
            "file_size": "BIGINT NOT NULL DEFAULT 0",
            "mime_type": "VARCHAR(128) NOT NULL DEFAULT ''",
            "status": "VARCHAR(16) NOT NULL DEFAULT 'active'",
            "review_status": "VARCHAR(16) NOT NULL DEFAULT 'pending'",
            "review_score": "DECIMAL(6,2) NULL",
            "review_note": "VARCHAR(255) NOT NULL DEFAULT ''",
            "reviewed_by": "VARCHAR(64) NOT NULL DEFAULT ''",
            "reviewed_at": "DATETIME NULL",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        }
        indexes = {
            "idx_task_submission_task_id": "task_id",
            "idx_task_submission_course_id": "course_id",
            "idx_task_submission_student_user_name": "student_user_name",
            "idx_task_submission_status": "status",
            "idx_task_submission_review_status": "review_status",
            "idx_task_submission_reviewed_at": "reviewed_at",
            "idx_task_submission_created_at": "created_at",
        }
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS experiment_task_submission (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    task_id BIGINT NOT NULL,
                    course_id BIGINT NOT NULL DEFAULT 0,
                    student_id INT NULL,
                    student_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    student_display_name VARCHAR(64) NOT NULL DEFAULT '',
                    file_name VARCHAR(255) NOT NULL DEFAULT '',
                    file_url VARCHAR(255) NOT NULL DEFAULT '',
                    file_size BIGINT NOT NULL DEFAULT 0,
                    mime_type VARCHAR(128) NOT NULL DEFAULT '',
                    status VARCHAR(16) NOT NULL DEFAULT 'active',
                    review_status VARCHAR(16) NOT NULL DEFAULT 'pending',
                    review_score DECIMAL(6,2) NULL,
                    review_note VARCHAR(255) NOT NULL DEFAULT '',
                    reviewed_by VARCHAR(64) NOT NULL DEFAULT '',
                    reviewed_at DATETIME NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_task_submission_task_id (task_id),
                    INDEX idx_task_submission_course_id (course_id),
                    INDEX idx_task_submission_student_user_name (student_user_name),
                    INDEX idx_task_submission_status (status),
                    INDEX idx_task_submission_review_status (review_status),
                    INDEX idx_task_submission_reviewed_at (reviewed_at),
                    INDEX idx_task_submission_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='experiment_task_submission'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE experiment_task_submission ADD COLUMN {col} {ddl}")

            cur.execute("UPDATE experiment_task_submission SET status='active' WHERE status IS NULL OR status=''")
            cur.execute("UPDATE experiment_task_submission SET review_status='pending' WHERE review_status IS NULL OR review_status=''")

            for index_name, column_name in indexes.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='experiment_task_submission'
                      AND INDEX_NAME=%s
                    """,
                    (DB["database"], index_name),
                )
                has_index = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_index:
                    cur.execute(f"ALTER TABLE experiment_task_submission ADD INDEX {index_name} ({column_name})")

        conn.commit()
    finally:
        conn.close()


def ensure_course_member_tables():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "course_id": "BIGINT NOT NULL",
            "student_id": "INT NULL",
            "student_user_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "student_display_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "status": "VARCHAR(16) NOT NULL DEFAULT 'active'",
            "joined_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        }
        indexes = {
            "uk_course_student": "course_id,student_user_name",
            "idx_course_member_course_id": "course_id",
            "idx_course_member_student_user_name": "student_user_name",
            "idx_course_member_status": "status",
            "idx_course_member_joined_at": "joined_at",
        }
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS course_member (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    course_id BIGINT NOT NULL,
                    student_id INT NULL,
                    student_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    student_display_name VARCHAR(64) NOT NULL DEFAULT '',
                    status VARCHAR(16) NOT NULL DEFAULT 'active',
                    joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_course_student (course_id, student_user_name),
                    INDEX idx_course_member_course_id (course_id),
                    INDEX idx_course_member_student_user_name (student_user_name),
                    INDEX idx_course_member_status (status),
                    INDEX idx_course_member_joined_at (joined_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='course_member'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE course_member ADD COLUMN {col} {ddl}")

            cur.execute("UPDATE course_member SET status='active' WHERE status IS NULL OR status=''")

            for index_name, column_name in indexes.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='course_member'
                      AND INDEX_NAME=%s
                    """,
                    (DB["database"], index_name),
                )
                has_index = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_index:
                    if index_name.startswith("uk_"):
                        cur.execute(f"ALTER TABLE course_member ADD UNIQUE INDEX {index_name} ({column_name})")
                    else:
                        cur.execute(f"ALTER TABLE course_member ADD INDEX {index_name} ({column_name})")

        conn.commit()
    finally:
        conn.close()


def ensure_course_task_notice_tables():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "course_id": "BIGINT NOT NULL DEFAULT 0",
            "task_id": "BIGINT NOT NULL DEFAULT 0",
            "to_user_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "teacher_user_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "message": "VARCHAR(255) NOT NULL DEFAULT ''",
            "status": "VARCHAR(16) NOT NULL DEFAULT 'active'",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        }
        indexes = {
            "idx_course_task_notice_to_user_name": "to_user_name",
            "idx_course_task_notice_course_id": "course_id",
            "idx_course_task_notice_task_id": "task_id",
            "idx_course_task_notice_status": "status",
            "idx_course_task_notice_created_at": "created_at",
        }
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS course_task_notice (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    course_id BIGINT NOT NULL DEFAULT 0,
                    task_id BIGINT NOT NULL DEFAULT 0,
                    to_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    teacher_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    message VARCHAR(255) NOT NULL DEFAULT '',
                    status VARCHAR(16) NOT NULL DEFAULT 'active',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_course_task_notice_to_user_name (to_user_name),
                    INDEX idx_course_task_notice_course_id (course_id),
                    INDEX idx_course_task_notice_task_id (task_id),
                    INDEX idx_course_task_notice_status (status),
                    INDEX idx_course_task_notice_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='course_task_notice'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE course_task_notice ADD COLUMN {col} {ddl}")

            cur.execute("UPDATE course_task_notice SET status='active' WHERE status IS NULL OR status=''")

            for index_name, column_name in indexes.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='course_task_notice'
                      AND INDEX_NAME=%s
                    """,
                    (DB["database"], index_name),
                )
                has_index = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_index:
                    cur.execute(f"ALTER TABLE course_task_notice ADD INDEX {index_name} ({column_name})")

        conn.commit()
    finally:
        conn.close()


def ensure_course_task_notice_subscription_table():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "user_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "enabled": "TINYINT NOT NULL DEFAULT 1",
            "before_hours": "INT NOT NULL DEFAULT 24",
            "remind_overdue": "TINYINT NOT NULL DEFAULT 1",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        }
        indexes = {
            "uk_course_task_notice_subscription_user_name": "user_name",
            "idx_course_task_notice_subscription_enabled": "enabled",
            "idx_course_task_notice_subscription_updated_at": "updated_at",
        }
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS course_task_notice_subscription (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_name VARCHAR(64) NOT NULL DEFAULT '',
                    enabled TINYINT NOT NULL DEFAULT 1,
                    before_hours INT NOT NULL DEFAULT 24,
                    remind_overdue TINYINT NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_course_task_notice_subscription_user_name (user_name),
                    INDEX idx_course_task_notice_subscription_enabled (enabled),
                    INDEX idx_course_task_notice_subscription_updated_at (updated_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='course_task_notice_subscription'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE course_task_notice_subscription ADD COLUMN {col} {ddl}")

            cur.execute("UPDATE course_task_notice_subscription SET enabled=1 WHERE enabled IS NULL")
            cur.execute("UPDATE course_task_notice_subscription SET remind_overdue=1 WHERE remind_overdue IS NULL")
            cur.execute(
                """
                UPDATE course_task_notice_subscription
                SET before_hours=24
                WHERE before_hours IS NULL OR before_hours<=0
                """
            )

            for index_name, column_name in indexes.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='course_task_notice_subscription'
                      AND INDEX_NAME=%s
                    """,
                    (DB["database"], index_name),
                )
                has_index = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_index:
                    if index_name.startswith("uk_"):
                        cur.execute(
                            f"ALTER TABLE course_task_notice_subscription ADD UNIQUE INDEX {index_name} ({column_name})"
                        )
                    else:
                        cur.execute(f"ALTER TABLE course_task_notice_subscription ADD INDEX {index_name} ({column_name})")

        conn.commit()
    finally:
        conn.close()


def ensure_course_task_auto_notice_log_table():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "course_id": "BIGINT NOT NULL DEFAULT 0",
            "task_id": "BIGINT NOT NULL DEFAULT 0",
            "to_user_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "reminder_kind": "VARCHAR(32) NOT NULL DEFAULT ''",
            "remind_date": "DATE NOT NULL",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        }
        indexes = {
            "uk_course_task_auto_notice": "task_id,to_user_name,reminder_kind,remind_date",
            "idx_course_task_auto_notice_course_id": "course_id",
            "idx_course_task_auto_notice_task_id": "task_id",
            "idx_course_task_auto_notice_to_user_name": "to_user_name",
            "idx_course_task_auto_notice_created_at": "created_at",
        }
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS course_task_auto_notice_log (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    course_id BIGINT NOT NULL DEFAULT 0,
                    task_id BIGINT NOT NULL DEFAULT 0,
                    to_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    reminder_kind VARCHAR(32) NOT NULL DEFAULT '',
                    remind_date DATE NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_course_task_auto_notice (task_id, to_user_name, reminder_kind, remind_date),
                    INDEX idx_course_task_auto_notice_course_id (course_id),
                    INDEX idx_course_task_auto_notice_task_id (task_id),
                    INDEX idx_course_task_auto_notice_to_user_name (to_user_name),
                    INDEX idx_course_task_auto_notice_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='course_task_auto_notice_log'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE course_task_auto_notice_log ADD COLUMN {col} {ddl}")

            for index_name, column_name in indexes.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='course_task_auto_notice_log'
                      AND INDEX_NAME=%s
                    """,
                    (DB["database"], index_name),
                )
                has_index = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_index:
                    if index_name.startswith("uk_"):
                        cur.execute(f"ALTER TABLE course_task_auto_notice_log ADD UNIQUE INDEX {index_name} ({column_name})")
                    else:
                        cur.execute(f"ALTER TABLE course_task_auto_notice_log ADD INDEX {index_name} ({column_name})")

        conn.commit()
    finally:
        conn.close()


def ensure_class_period_configs_table():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "period_index": "INT NOT NULL DEFAULT 0",
            "period_name": "VARCHAR(32) NOT NULL DEFAULT ''",
            "start_time": "TIME NOT NULL DEFAULT '00:00:00'",
            "end_time": "TIME NOT NULL DEFAULT '00:00:00'",
            "sort_order": "INT NOT NULL DEFAULT 0",
            "status": "VARCHAR(16) NOT NULL DEFAULT 'active'",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        }
        indexes = {
            "uk_class_period_configs_period_index": "period_index",
            "idx_class_period_configs_status": "status",
            "idx_class_period_configs_sort_order": "sort_order",
        }
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS class_period_configs (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    period_index INT NOT NULL DEFAULT 0,
                    period_name VARCHAR(32) NOT NULL DEFAULT '',
                    start_time TIME NOT NULL DEFAULT '00:00:00',
                    end_time TIME NOT NULL DEFAULT '00:00:00',
                    sort_order INT NOT NULL DEFAULT 0,
                    status VARCHAR(16) NOT NULL DEFAULT 'active',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_class_period_configs_period_index (period_index),
                    INDEX idx_class_period_configs_status (status),
                    INDEX idx_class_period_configs_sort_order (sort_order)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='class_period_configs'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE class_period_configs ADD COLUMN {col} {ddl}")

            cur.execute("UPDATE class_period_configs SET status='active' WHERE status IS NULL OR status=''")
            cur.execute(
                """
                UPDATE class_period_configs
                SET sort_order=period_index
                WHERE sort_order IS NULL OR sort_order=0
                """
            )

            for index_name, column_name in indexes.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='class_period_configs'
                      AND INDEX_NAME=%s
                    """,
                    (DB["database"], index_name),
                )
                has_index = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_index:
                    if index_name.startswith("uk_"):
                        cur.execute(f"ALTER TABLE class_period_configs ADD UNIQUE INDEX {index_name} ({column_name})")
                    else:
                        cur.execute(f"ALTER TABLE class_period_configs ADD INDEX {index_name} ({column_name})")

            for item in PERIOD_SLOT_ITEMS:
                period_idx = int(_to_int_or_none(item.get("index")) or 0)
                if period_idx <= 0:
                    continue
                time_text = str(item.get("time") or "").strip()
                start_text = ""
                end_text = ""
                if "-" in time_text:
                    parts = [x.strip() for x in time_text.split("-", 1)]
                    if len(parts) >= 2:
                        start_text = parts[0]
                        end_text = parts[1]
                if not start_text:
                    start_text = "00:00"
                if not end_text:
                    end_text = "00:00"
                if len(start_text) == 5:
                    start_text = f"{start_text}:00"
                if len(end_text) == 5:
                    end_text = f"{end_text}:00"
                period_name = str(item.get("label") or f"第{period_idx}节").strip()
                cur.execute(
                    """
                    INSERT INTO class_period_configs (
                        period_index, period_name, start_time, end_time, sort_order, status
                    ) VALUES (%s, %s, %s, %s, %s, 'active')
                    ON DUPLICATE KEY UPDATE
                        period_name=IF(period_name='', VALUES(period_name), period_name),
                        start_time=IF(start_time='00:00:00', VALUES(start_time), start_time),
                        end_time=IF(end_time='00:00:00', VALUES(end_time), end_time),
                        sort_order=IF(sort_order=0, VALUES(sort_order), sort_order)
                    """,
                    (period_idx, period_name, start_text, end_text, period_idx),
                )

        conn.commit()
    finally:
        conn.close()


def ensure_course_schedule_templates_table():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "term_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "semester_start_date": "DATE NULL",
            "semester_weeks": "INT NOT NULL DEFAULT 20",
            "source_type": "VARCHAR(16) NOT NULL DEFAULT 'manual'",
            "raw_payload": "LONGTEXT NULL",
            "status": "VARCHAR(16) NOT NULL DEFAULT 'draft'",
            "reminder_lead_minutes": "INT NOT NULL DEFAULT 20",
            "created_by": "VARCHAR(64) NOT NULL DEFAULT ''",
            "updated_by": "VARCHAR(64) NOT NULL DEFAULT ''",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        }
        indexes = {
            "idx_schedule_templates_status": "status",
            "idx_schedule_templates_start_date": "semester_start_date",
            "idx_schedule_templates_created_by": "created_by",
            "idx_schedule_templates_created_at": "created_at",
        }
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS course_schedule_templates (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    term_name VARCHAR(64) NOT NULL DEFAULT '',
                    semester_start_date DATE NULL,
                    semester_weeks INT NOT NULL DEFAULT 20,
                    source_type VARCHAR(16) NOT NULL DEFAULT 'manual',
                    raw_payload LONGTEXT NULL,
                    status VARCHAR(16) NOT NULL DEFAULT 'draft',
                    reminder_lead_minutes INT NOT NULL DEFAULT 20,
                    created_by VARCHAR(64) NOT NULL DEFAULT '',
                    updated_by VARCHAR(64) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_schedule_templates_status (status),
                    INDEX idx_schedule_templates_start_date (semester_start_date),
                    INDEX idx_schedule_templates_created_by (created_by),
                    INDEX idx_schedule_templates_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='course_schedule_templates'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE course_schedule_templates ADD COLUMN {col} {ddl}")

            cur.execute("UPDATE course_schedule_templates SET status='draft' WHERE status IS NULL OR status=''")
            cur.execute(
                """
                UPDATE course_schedule_templates
                SET semester_weeks=20
                WHERE semester_weeks IS NULL OR semester_weeks<=0
                """
            )
            cur.execute(
                """
                UPDATE course_schedule_templates
                SET reminder_lead_minutes=20
                WHERE reminder_lead_minutes IS NULL OR reminder_lead_minutes<0
                """
            )

            for index_name, column_name in indexes.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='course_schedule_templates'
                      AND INDEX_NAME=%s
                    """,
                    (DB["database"], index_name),
                )
                has_index = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_index:
                    cur.execute(f"ALTER TABLE course_schedule_templates ADD INDEX {index_name} ({column_name})")

        conn.commit()
    finally:
        conn.close()


def ensure_course_schedule_items_table():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "template_id": "BIGINT NOT NULL DEFAULT 0",
            "course_name": "VARCHAR(160) NOT NULL DEFAULT ''",
            "teacher_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "class_name": "VARCHAR(160) NOT NULL DEFAULT ''",
            "lab_id": "BIGINT NULL",
            "lab_name": "VARCHAR(128) NOT NULL DEFAULT ''",
            "week_day": "INT NOT NULL DEFAULT 1",
            "period_start": "INT NOT NULL DEFAULT 1",
            "period_end": "INT NOT NULL DEFAULT 1",
            "time_range": "VARCHAR(255) NOT NULL DEFAULT ''",
            "week_start": "INT NOT NULL DEFAULT 1",
            "week_end": "INT NOT NULL DEFAULT 20",
            "week_type": "VARCHAR(16) NOT NULL DEFAULT 'all'",
            "note": "VARCHAR(255) NOT NULL DEFAULT ''",
            "source_row_no": "INT NOT NULL DEFAULT 0",
            "status": "VARCHAR(16) NOT NULL DEFAULT 'active'",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        }
        indexes = {
            "idx_schedule_items_template_id": "template_id",
            "idx_schedule_items_lab_id": "lab_id",
            "idx_schedule_items_week_day": "week_day",
            "idx_schedule_items_period_start": "period_start",
            "idx_schedule_items_week_start": "week_start",
            "idx_schedule_items_week_end": "week_end",
            "idx_schedule_items_status": "status",
        }
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS course_schedule_items (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    template_id BIGINT NOT NULL DEFAULT 0,
                    course_name VARCHAR(160) NOT NULL DEFAULT '',
                    teacher_name VARCHAR(64) NOT NULL DEFAULT '',
                    class_name VARCHAR(160) NOT NULL DEFAULT '',
                    lab_id BIGINT NULL,
                    lab_name VARCHAR(128) NOT NULL DEFAULT '',
                    week_day INT NOT NULL DEFAULT 1,
                    period_start INT NOT NULL DEFAULT 1,
                    period_end INT NOT NULL DEFAULT 1,
                    time_range VARCHAR(255) NOT NULL DEFAULT '',
                    week_start INT NOT NULL DEFAULT 1,
                    week_end INT NOT NULL DEFAULT 20,
                    week_type VARCHAR(16) NOT NULL DEFAULT 'all',
                    note VARCHAR(255) NOT NULL DEFAULT '',
                    source_row_no INT NOT NULL DEFAULT 0,
                    status VARCHAR(16) NOT NULL DEFAULT 'active',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_schedule_items_template_id (template_id),
                    INDEX idx_schedule_items_lab_id (lab_id),
                    INDEX idx_schedule_items_week_day (week_day),
                    INDEX idx_schedule_items_period_start (period_start),
                    INDEX idx_schedule_items_week_start (week_start),
                    INDEX idx_schedule_items_week_end (week_end),
                    INDEX idx_schedule_items_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='course_schedule_items'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE course_schedule_items ADD COLUMN {col} {ddl}")

            cur.execute("UPDATE course_schedule_items SET status='active' WHERE status IS NULL OR status=''")
            cur.execute("UPDATE course_schedule_items SET week_type='all' WHERE week_type IS NULL OR week_type=''")
            cur.execute("UPDATE course_schedule_items SET week_start=1 WHERE week_start IS NULL OR week_start<=0")
            cur.execute(
                """
                UPDATE course_schedule_items
                SET week_end=CASE WHEN week_end IS NULL OR week_end<=0 THEN 20 ELSE week_end END
                """
            )
            cur.execute(
                """
                UPDATE course_schedule_items
                SET period_end=CASE WHEN period_end IS NULL OR period_end<=0 THEN period_start ELSE period_end END
                """
            )

            for index_name, column_name in indexes.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='course_schedule_items'
                      AND INDEX_NAME=%s
                    """,
                    (DB["database"], index_name),
                )
                has_index = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_index:
                    cur.execute(f"ALTER TABLE course_schedule_items ADD INDEX {index_name} ({column_name})")

        conn.commit()
    finally:
        conn.close()


def ensure_door_open_reminders_table():
    conn = pymysql.connect(**DB)
    try:
        columns = {
            "template_id": "BIGINT NOT NULL DEFAULT 0",
            "schedule_item_id": "BIGINT NOT NULL DEFAULT 0",
            "lab_id": "BIGINT NULL",
            "lab_name": "VARCHAR(128) NOT NULL DEFAULT ''",
            "course_name": "VARCHAR(160) NOT NULL DEFAULT ''",
            "teacher_name": "VARCHAR(64) NOT NULL DEFAULT ''",
            "class_name": "VARCHAR(160) NOT NULL DEFAULT ''",
            "occurrence_date": "DATE NULL",
            "week_no": "INT NOT NULL DEFAULT 0",
            "week_day": "INT NOT NULL DEFAULT 1",
            "period_start": "INT NOT NULL DEFAULT 1",
            "period_end": "INT NOT NULL DEFAULT 1",
            "start_at": "DATETIME NULL",
            "end_at": "DATETIME NULL",
            "remind_at": "DATETIME NULL",
            "remind_status": "VARCHAR(16) NOT NULL DEFAULT 'pending'",
            "door_status": "VARCHAR(16) NOT NULL DEFAULT 'pending'",
            "remind_sent_at": "DATETIME NULL",
            "handled_by": "VARCHAR(64) NOT NULL DEFAULT ''",
            "handled_at": "DATETIME NULL",
            "handle_note": "VARCHAR(255) NOT NULL DEFAULT ''",
            "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        }
        indexes = {
            "uk_door_open_occurrence": "template_id,schedule_item_id,occurrence_date,period_start,period_end",
            "idx_door_open_occurrence_date": "occurrence_date",
            "idx_door_open_lab_id": "lab_id",
            "idx_door_open_remind_status": "remind_status",
            "idx_door_open_door_status": "door_status",
            "idx_door_open_remind_at": "remind_at",
            "idx_door_open_start_at": "start_at",
        }
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS door_open_reminders (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    template_id BIGINT NOT NULL DEFAULT 0,
                    schedule_item_id BIGINT NOT NULL DEFAULT 0,
                    lab_id BIGINT NULL,
                    lab_name VARCHAR(128) NOT NULL DEFAULT '',
                    course_name VARCHAR(160) NOT NULL DEFAULT '',
                    teacher_name VARCHAR(64) NOT NULL DEFAULT '',
                    class_name VARCHAR(160) NOT NULL DEFAULT '',
                    occurrence_date DATE NULL,
                    week_no INT NOT NULL DEFAULT 0,
                    week_day INT NOT NULL DEFAULT 1,
                    period_start INT NOT NULL DEFAULT 1,
                    period_end INT NOT NULL DEFAULT 1,
                    start_at DATETIME NULL,
                    end_at DATETIME NULL,
                    remind_at DATETIME NULL,
                    remind_status VARCHAR(16) NOT NULL DEFAULT 'pending',
                    door_status VARCHAR(16) NOT NULL DEFAULT 'pending',
                    remind_sent_at DATETIME NULL,
                    handled_by VARCHAR(64) NOT NULL DEFAULT '',
                    handled_at DATETIME NULL,
                    handle_note VARCHAR(255) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_door_open_occurrence (template_id, schedule_item_id, occurrence_date, period_start, period_end),
                    INDEX idx_door_open_occurrence_date (occurrence_date),
                    INDEX idx_door_open_lab_id (lab_id),
                    INDEX idx_door_open_remind_status (remind_status),
                    INDEX idx_door_open_door_status (door_status),
                    INDEX idx_door_open_remind_at (remind_at),
                    INDEX idx_door_open_start_at (start_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            for col, ddl in columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='door_open_reminders'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE door_open_reminders ADD COLUMN {col} {ddl}")

            cur.execute("UPDATE door_open_reminders SET remind_status='pending' WHERE remind_status IS NULL OR remind_status=''")
            cur.execute("UPDATE door_open_reminders SET door_status='pending' WHERE door_status IS NULL OR door_status=''")

            for index_name, column_name in indexes.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='door_open_reminders'
                      AND INDEX_NAME=%s
                    """,
                    (DB["database"], index_name),
                )
                has_index = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_index:
                    if index_name.startswith("uk_"):
                        cur.execute(f"ALTER TABLE door_open_reminders ADD UNIQUE INDEX {index_name} ({column_name})")
                    else:
                        cur.execute(f"ALTER TABLE door_open_reminders ADD INDEX {index_name} ({column_name})")

        conn.commit()
    finally:
        conn.close()


def ensure_task_rubric_tables():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS task_rubric_template (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    task_id BIGINT NOT NULL DEFAULT 0,
                    course_id BIGINT NOT NULL DEFAULT 0,
                    teacher_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    title VARCHAR(160) NOT NULL DEFAULT '',
                    description VARCHAR(500) NOT NULL DEFAULT '',
                    total_score DECIMAL(6,2) NOT NULL DEFAULT 100.00,
                    status VARCHAR(16) NOT NULL DEFAULT 'active',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_task_rubric_task_id (task_id),
                    INDEX idx_task_rubric_course_id (course_id),
                    INDEX idx_task_rubric_teacher (teacher_user_name),
                    INDEX idx_task_rubric_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS task_rubric_item (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    template_id BIGINT NOT NULL DEFAULT 0,
                    item_title VARCHAR(160) NOT NULL DEFAULT '',
                    description VARCHAR(500) NOT NULL DEFAULT '',
                    max_score DECIMAL(6,2) NOT NULL DEFAULT 0.00,
                    sort_order INT NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_task_rubric_item_template_id (template_id),
                    INDEX idx_task_rubric_item_sort_order (sort_order)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS task_submission_rubric_score (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    submission_id BIGINT NOT NULL DEFAULT 0,
                    item_id BIGINT NOT NULL DEFAULT 0,
                    item_title VARCHAR(160) NOT NULL DEFAULT '',
                    max_score DECIMAL(6,2) NOT NULL DEFAULT 0.00,
                    score DECIMAL(6,2) NULL,
                    comment VARCHAR(500) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_submission_rubric_item (submission_id, item_id),
                    INDEX idx_submission_rubric_submission_id (submission_id),
                    INDEX idx_submission_rubric_item_id (item_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS task_submission_annotation (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    submission_id BIGINT NOT NULL DEFAULT 0,
                    annotation_type VARCHAR(32) NOT NULL DEFAULT 'comment',
                    anchor_type VARCHAR(32) NOT NULL DEFAULT 'file',
                    anchor_key VARCHAR(128) NOT NULL DEFAULT '',
                    content VARCHAR(500) NOT NULL DEFAULT '',
                    created_by VARCHAR(64) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_submission_annotation_submission_id (submission_id),
                    INDEX idx_submission_annotation_created_by (created_by),
                    INDEX idx_submission_annotation_anchor (anchor_type, anchor_key)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_reservation_waitlist_tables():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS reservation_waitlist (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    lab_id BIGINT NULL,
                    lab_name VARCHAR(128) NOT NULL DEFAULT '',
                    user_name VARCHAR(64) NOT NULL DEFAULT '',
                    user_role VARCHAR(16) NOT NULL DEFAULT '',
                    date DATE NOT NULL,
                    time VARCHAR(64) NOT NULL DEFAULT '',
                    reason VARCHAR(255) NOT NULL DEFAULT '',
                    status VARCHAR(16) NOT NULL DEFAULT 'waiting',
                    priority_score DECIMAL(8,2) NOT NULL DEFAULT 0.00,
                    priority_breakdown_json TEXT NULL,
                    source_reservation_id BIGINT NULL,
                    promoted_reservation_id BIGINT NULL,
                    promoted_at DATETIME NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_waitlist_slot (lab_name, date),
                    INDEX idx_waitlist_status (status),
                    INDEX idx_waitlist_user_name (user_name),
                    INDEX idx_waitlist_priority (priority_score),
                    INDEX idx_waitlist_source_reservation_id (source_reservation_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS reservation_priority_rule (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    status VARCHAR(16) NOT NULL DEFAULT 'active',
                    teacher_weight INT NOT NULL DEFAULT 30,
                    student_weight INT NOT NULL DEFAULT 10,
                    admin_weight INT NOT NULL DEFAULT 20,
                    teaching_weight INT NOT NULL DEFAULT 25,
                    research_weight INT NOT NULL DEFAULT 15,
                    default_weight INT NOT NULL DEFAULT 5,
                    violation_penalty INT NOT NULL DEFAULT 15,
                    wait_hour_bonus DECIMAL(6,2) NOT NULL DEFAULT 1.00,
                    wait_hour_bonus_cap INT NOT NULL DEFAULT 48,
                    updated_by VARCHAR(64) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_reservation_priority_rule_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS reservation_rule_preview_log (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    preview_by VARCHAR(64) NOT NULL DEFAULT '',
                    request_json LONGTEXT NULL,
                    result_json LONGTEXT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_reservation_rule_preview_by (preview_by),
                    INDEX idx_reservation_rule_preview_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute("SELECT COUNT(*) AS cnt FROM reservation_priority_rule")
            has_rule = int((cur.fetchone() or {}).get("cnt") or 0)
            if has_rule <= 0:
                cur.execute(
                    """
                    INSERT INTO reservation_priority_rule (
                        status, teacher_weight, student_weight, admin_weight,
                        teaching_weight, research_weight, default_weight,
                        violation_penalty, wait_hour_bonus, wait_hour_bonus_cap, updated_by
                    )
                    VALUES ('active', 30, 10, 20, 25, 15, 5, 15, 1.00, 48, 'system')
                    """
                )
        conn.commit()
    finally:
        conn.close()


def ensure_borrow_extension_tables():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS borrow_extension_request (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    request_id BIGINT NOT NULL DEFAULT 0,
                    applicant_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    requested_return_at DATETIME NOT NULL,
                    reason VARCHAR(255) NOT NULL DEFAULT '',
                    status VARCHAR(16) NOT NULL DEFAULT 'pending',
                    reviewed_by VARCHAR(64) NOT NULL DEFAULT '',
                    reviewed_at DATETIME NULL,
                    reject_reason VARCHAR(255) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_borrow_extension_request_id (request_id),
                    INDEX idx_borrow_extension_status (status),
                    INDEX idx_borrow_extension_applicant (applicant_user_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS borrow_return_log (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    request_id BIGINT NOT NULL DEFAULT 0,
                    equipment_id BIGINT NOT NULL DEFAULT 0,
                    operator_name VARCHAR(64) NOT NULL DEFAULT '',
                    operator_role VARCHAR(16) NOT NULL DEFAULT '',
                    return_channel VARCHAR(16) NOT NULL DEFAULT 'manual',
                    scan_token VARCHAR(128) NOT NULL DEFAULT '',
                    note VARCHAR(255) NOT NULL DEFAULT '',
                    returned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_borrow_return_request_id (request_id),
                    INDEX idx_borrow_return_equipment_id (equipment_id),
                    INDEX idx_borrow_return_channel (return_channel),
                    INDEX idx_borrow_return_returned_at (returned_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS borrow_compensation_order (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    request_id BIGINT NOT NULL DEFAULT 0,
                    equipment_id BIGINT NOT NULL DEFAULT 0,
                    applicant_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    damage_level VARCHAR(32) NOT NULL DEFAULT 'normal',
                    description VARCHAR(500) NOT NULL DEFAULT '',
                    image_url VARCHAR(255) NOT NULL DEFAULT '',
                    amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                    status VARCHAR(16) NOT NULL DEFAULT 'pending',
                    handled_by VARCHAR(64) NOT NULL DEFAULT '',
                    handled_at DATETIME NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_borrow_compensation_request_id (request_id),
                    INDEX idx_borrow_compensation_equipment_id (equipment_id),
                    INDEX idx_borrow_compensation_applicant (applicant_user_name),
                    INDEX idx_borrow_compensation_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_attendance_tables():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance_session (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    course_id BIGINT NOT NULL DEFAULT 0,
                    course_name VARCHAR(160) NOT NULL DEFAULT '',
                    teacher_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    lab_id BIGINT NULL,
                    lab_name VARCHAR(128) NOT NULL DEFAULT '',
                    attendance_code VARCHAR(32) NOT NULL DEFAULT '',
                    code_expires_at DATETIME NULL,
                    recheck_code VARCHAR(32) NOT NULL DEFAULT '',
                    recheck_started_at DATETIME NULL,
                    recheck_expires_at DATETIME NULL,
                    status VARCHAR(16) NOT NULL DEFAULT 'open',
                    start_at DATETIME NULL,
                    end_at DATETIME NULL,
                    geo_lat DECIMAL(10,7) NULL,
                    geo_lng DECIMAL(10,7) NULL,
                    geo_radius_meter INT NOT NULL DEFAULT 150,
                    require_location TINYINT(1) NOT NULL DEFAULT 1,
                    require_device_binding TINYINT(1) NOT NULL DEFAULT 1,
                    require_seat_code TINYINT(1) NOT NULL DEFAULT 1,
                    allowed_network_hint VARCHAR(128) NOT NULL DEFAULT '',
                    seat_code_prefix VARCHAR(32) NOT NULL DEFAULT '',
                    anti_cheat_mode VARCHAR(64) NOT NULL DEFAULT 'dynamic_geo_device_seat',
                    note VARCHAR(255) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_attendance_session_course_id (course_id),
                    INDEX idx_attendance_session_teacher (teacher_user_name),
                    INDEX idx_attendance_session_status (status),
                    INDEX idx_attendance_session_start_at (start_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance_record (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    session_id BIGINT NOT NULL DEFAULT 0,
                    course_id BIGINT NOT NULL DEFAULT 0,
                    student_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    student_display_name VARCHAR(64) NOT NULL DEFAULT '',
                    device_id VARCHAR(128) NOT NULL DEFAULT '',
                    device_name VARCHAR(128) NOT NULL DEFAULT '',
                    network_name VARCHAR(128) NOT NULL DEFAULT '',
                    seat_code VARCHAR(64) NOT NULL DEFAULT '',
                    status VARCHAR(16) NOT NULL DEFAULT 'pending_confirm',
                    latitude DECIMAL(10,7) NULL,
                    longitude DECIMAL(10,7) NULL,
                    distance_meter DECIMAL(10,2) NULL,
                    suspicion_level INT NOT NULL DEFAULT 0,
                    suspicion_reason VARCHAR(255) NOT NULL DEFAULT '',
                    first_checkin_at DATETIME NULL,
                    final_checkin_at DATETIME NULL,
                    recheck_required TINYINT(1) NOT NULL DEFAULT 0,
                    recheck_completed_at DATETIME NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_attendance_session_student (session_id, student_user_name),
                    INDEX idx_attendance_record_course_id (course_id),
                    INDEX idx_attendance_record_status (status),
                    INDEX idx_attendance_record_device_id (device_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance_device_binding (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_name VARCHAR(64) NOT NULL DEFAULT '',
                    device_id VARCHAR(128) NOT NULL DEFAULT '',
                    device_name VARCHAR(128) NOT NULL DEFAULT '',
                    bind_status VARCHAR(16) NOT NULL DEFAULT 'active',
                    risk_level INT NOT NULL DEFAULT 0,
                    last_ip VARCHAR(64) NOT NULL DEFAULT '',
                    note VARCHAR(255) NOT NULL DEFAULT '',
                    first_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_attendance_device_binding (user_name, device_id),
                    INDEX idx_attendance_binding_user_name (user_name),
                    INDEX idx_attendance_binding_device_id (device_id),
                    INDEX idx_attendance_binding_status (bind_status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance_recheck_log (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    session_id BIGINT NOT NULL DEFAULT 0,
                    record_id BIGINT NULL,
                    student_user_name VARCHAR(64) NOT NULL DEFAULT '',
                    action_type VARCHAR(16) NOT NULL DEFAULT 'issued',
                    code_value VARCHAR(32) NOT NULL DEFAULT '',
                    seat_code VARCHAR(64) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_attendance_recheck_session_id (session_id),
                    INDEX idx_attendance_recheck_record_id (record_id),
                    INDEX idx_attendance_recheck_student (student_user_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_ai_action_log_table():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_action_log (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    action_type VARCHAR(64) NOT NULL DEFAULT '',
                    target_type VARCHAR(64) NOT NULL DEFAULT '',
                    target_id VARCHAR(64) NOT NULL DEFAULT '',
                    actor_name VARCHAR(64) NOT NULL DEFAULT '',
                    actor_role VARCHAR(16) NOT NULL DEFAULT '',
                    suggestion_json LONGTEXT NULL,
                    execute_payload_json LONGTEXT NULL,
                    result_status VARCHAR(16) NOT NULL DEFAULT 'success',
                    result_message VARCHAR(255) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_ai_action_type (action_type),
                    INDEX idx_ai_action_target (target_type, target_id),
                    INDEX idx_ai_action_actor (actor_name),
                    INDEX idx_ai_action_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def log_ai_action(action_type, target_type="", target_id="", suggestion=None, execute_payload=None, result_status="success", result_message="", actor=None):
    actor = actor or getattr(g, "current_user", {}) or {}
    actor_name = str(actor.get("username") or "")
    actor_role = str(actor.get("role") or "")
    try:
        execute_insert(
            """
            INSERT INTO ai_action_log (
                action_type, target_type, target_id, actor_name, actor_role,
                suggestion_json, execute_payload_json, result_status, result_message, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(action_type or ""),
                str(target_type or ""),
                str(target_id or ""),
                actor_name,
                actor_role,
                json.dumps(suggestion or {}, ensure_ascii=False, separators=(",", ":")),
                json.dumps(execute_payload or {}, ensure_ascii=False, separators=(",", ":")),
                str(result_status or "success"),
                str(result_message or "")[:255],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
    except Exception as e:
        print(f"[warn] log_ai_action failed: {e}")


def ensure_knowledge_base_tables():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_document (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    title VARCHAR(200) NOT NULL DEFAULT '',
                    category VARCHAR(32) NOT NULL DEFAULT 'other',
                    scope_role VARCHAR(16) NOT NULL DEFAULT 'all',
                    status VARCHAR(16) NOT NULL DEFAULT 'draft',
                    source_type VARCHAR(16) NOT NULL DEFAULT 'text',
                    source_url VARCHAR(500) NOT NULL DEFAULT '',
                    summary VARCHAR(255) NOT NULL DEFAULT '',
                    keywords VARCHAR(500) NOT NULL DEFAULT '',
                    source_content LONGTEXT NULL,
                    chunk_count INT NOT NULL DEFAULT 0,
                    last_indexed_at DATETIME NULL,
                    uploader_id BIGINT NULL,
                    uploader_name VARCHAR(64) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_knowledge_doc_category (category),
                    INDEX idx_knowledge_doc_scope (scope_role),
                    INDEX idx_knowledge_doc_status (status),
                    INDEX idx_knowledge_doc_updated_at (updated_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_chunk (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    document_id BIGINT NOT NULL,
                    chunk_no INT NOT NULL DEFAULT 0,
                    section_title VARCHAR(200) NOT NULL DEFAULT '',
                    chunk_text LONGTEXT NULL,
                    keywords VARCHAR(500) NOT NULL DEFAULT '',
                    text_hash VARCHAR(64) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_knowledge_chunk_document_id (document_id),
                    INDEX idx_knowledge_chunk_no (chunk_no),
                    INDEX idx_knowledge_chunk_hash (text_hash)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_query_log (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id BIGINT NULL,
                    username VARCHAR(64) NOT NULL DEFAULT '',
                    role VARCHAR(16) NOT NULL DEFAULT '',
                    query_text VARCHAR(500) NOT NULL DEFAULT '',
                    answer_text LONGTEXT NULL,
                    matched_count INT NOT NULL DEFAULT 0,
                    hit_document_ids_json TEXT NULL,
                    hit_chunk_ids_json TEXT NULL,
                    latency_ms INT NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_knowledge_query_user (username),
                    INDEX idx_knowledge_query_role (role),
                    INDEX idx_knowledge_query_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_feedback (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    query_log_id BIGINT NOT NULL,
                    user_id BIGINT NULL,
                    username VARCHAR(64) NOT NULL DEFAULT '',
                    helpful TINYINT(1) NOT NULL DEFAULT 1,
                    comment VARCHAR(255) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_knowledge_feedback_query_log_id (query_log_id),
                    INDEX idx_knowledge_feedback_username (username)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def ensure_repair_ai_v2_tables():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS repair_attachment (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    work_order_id BIGINT NOT NULL,
                    file_url VARCHAR(500) NOT NULL DEFAULT '',
                    file_name VARCHAR(200) NOT NULL DEFAULT '',
                    file_type VARCHAR(32) NOT NULL DEFAULT 'image',
                    mime_type VARCHAR(100) NOT NULL DEFAULT '',
                    ocr_text TEXT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_repair_attachment_work_order_id (work_order_id),
                    INDEX idx_repair_attachment_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS repair_ai_diagnosis_log (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    work_order_id BIGINT NULL,
                    equipment_id BIGINT NULL,
                    lab_id BIGINT NULL,
                    user_id BIGINT NULL,
                    input_text LONGTEXT NULL,
                    attachment_json LONGTEXT NULL,
                    issue_type VARCHAR(32) NOT NULL DEFAULT 'other',
                    fault_part VARCHAR(100) NOT NULL DEFAULT '',
                    priority VARCHAR(8) NOT NULL DEFAULT 'P2',
                    summary VARCHAR(500) NOT NULL DEFAULT '',
                    possible_causes_json TEXT NULL,
                    suggestions_json TEXT NULL,
                    ocr_summary TEXT NULL,
                    confidence DECIMAL(5,4) NOT NULL DEFAULT 0.0000,
                    model_name VARCHAR(120) NOT NULL DEFAULT '',
                    result_json LONGTEXT NULL,
                    fallback_flag TINYINT(1) NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_repair_ai_log_work_order_id (work_order_id),
                    INDEX idx_repair_ai_log_equipment_id (equipment_id),
                    INDEX idx_repair_ai_log_lab_id (lab_id),
                    INDEX idx_repair_ai_log_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            repair_columns = {
                "ai_fault_part": "VARCHAR(100) NULL",
                "ai_summary": "VARCHAR(500) NULL",
                "ai_possible_causes": "TEXT NULL",
                "ai_ocr_text": "TEXT NULL",
                "ai_model_name": "VARCHAR(120) NULL",
            }
            for col, ddl in repair_columns.items():
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA=%s
                      AND TABLE_NAME='repair_work_order'
                      AND COLUMN_NAME=%s
                    """,
                    (DB["database"], col),
                )
                has_col = int((cur.fetchone() or {}).get("cnt") or 0) > 0
                if not has_col:
                    cur.execute(f"ALTER TABLE repair_work_order ADD COLUMN {col} {ddl}")
        conn.commit()
    finally:
        conn.close()


def ensure_equipment_failure_prediction_tables():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS equipment_feature_snapshot (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    equipment_id BIGINT NOT NULL,
                    snapshot_date DATE NOT NULL,
                    repair_count_7d INT NOT NULL DEFAULT 0,
                    repair_count_30d INT NOT NULL DEFAULT 0,
                    repair_count_90d INT NOT NULL DEFAULT 0,
                    alarm_count_7d INT NOT NULL DEFAULT 0,
                    alarm_count_30d INT NOT NULL DEFAULT 0,
                    borrow_count_30d INT NOT NULL DEFAULT 0,
                    last_repair_days INT NULL,
                    age_days INT NULL,
                    current_status VARCHAR(32) NOT NULL DEFAULT '',
                    feature_json LONGTEXT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_equipment_snapshot_unique (equipment_id, snapshot_date),
                    INDEX idx_equipment_snapshot_date (snapshot_date),
                    INDEX idx_equipment_snapshot_equipment_id (equipment_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS equipment_failure_prediction (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    equipment_id BIGINT NOT NULL,
                    predict_date DATE NOT NULL,
                    horizon_days INT NOT NULL DEFAULT 7,
                    risk_score DECIMAL(6,2) NOT NULL DEFAULT 0.00,
                    failure_probability DECIMAL(6,4) NOT NULL DEFAULT 0.0000,
                    risk_level VARCHAR(16) NOT NULL DEFAULT 'low',
                    predicted_issue_type VARCHAR(32) NOT NULL DEFAULT 'other',
                    top_factors_json LONGTEXT NULL,
                    recommendation VARCHAR(500) NOT NULL DEFAULT '',
                    model_name VARCHAR(120) NOT NULL DEFAULT '',
                    model_version VARCHAR(32) NOT NULL DEFAULT '',
                    status VARCHAR(16) NOT NULL DEFAULT 'new',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_equipment_prediction_unique (equipment_id, predict_date, horizon_days),
                    INDEX idx_equipment_prediction_date (predict_date),
                    INDEX idx_equipment_prediction_level (risk_level),
                    INDEX idx_equipment_prediction_equipment_id (equipment_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        conn.commit()
    finally:
        conn.close()


def _json_dumps_safe(value, max_len=20000):
    try:
        text = json.dumps(value if value is not None else {}, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        text = "{}"
    if len(text) > int(max_len):
        text = text[: int(max_len)]
    return text


def _knowledge_normalize_category(value, default_value="other"):
    text = str(value or "").strip().lower() or str(default_value or "other").strip().lower()
    if text not in KNOWLEDGE_CATEGORY_SET:
        return "other"
    return text


def _knowledge_normalize_scope_role(value, default_value="all"):
    text = str(value or "").strip().lower() or str(default_value or "all").strip().lower()
    if text not in KNOWLEDGE_SCOPE_ROLE_SET:
        return "all"
    return text


def _knowledge_scope_matches(scope_role, current_role=""):
    scope = _knowledge_normalize_scope_role(scope_role)
    role = str(current_role or "").strip().lower()
    return scope == "all" or (role and scope == role)


def _knowledge_tokenize(text, limit=120):
    raw = re.sub(r"\s+", " ", str(text or "").strip().lower())
    if not raw:
        return []
    normalized = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", raw)
    tokens = []
    for part in normalized.split():
        if not part:
            continue
        if re.search(r"[\u4e00-\u9fff]", part):
            if len(part) <= 8:
                tokens.append(part)
            for size in (2, 3):
                if len(part) < size:
                    continue
                for idx in range(0, len(part) - size + 1):
                    tokens.append(part[idx : idx + size])
        else:
            if len(part) >= 2:
                tokens.append(part)
    dedup = []
    seen = set()
    for token in tokens:
        item = str(token or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        dedup.append(item)
        if len(dedup) >= int(limit):
            break
    return dedup


def _knowledge_build_keywords(text, max_len=500):
    keywords = ",".join(_knowledge_tokenize(text, limit=30))
    return keywords[: int(max_len)]


def _knowledge_extract_summary(text, max_len=160):
    summary = re.sub(r"\s+", " ", str(text or "").strip())
    if len(summary) > int(max_len):
        summary = summary[: int(max_len)] + "..."
    return summary


def _knowledge_split_text(content, title=""):
    normalized = str(content or "").replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [re.sub(r"\s+", " ", item).strip() for item in re.split(r"\n{2,}", normalized) if str(item or "").strip()]
    pieces = []
    for paragraph in paragraphs:
        if len(paragraph) <= KNOWLEDGE_CHUNK_CHAR_LIMIT:
            pieces.append(paragraph)
            continue
        sentences = [seg.strip() for seg in re.split(r"(?<=[。！？!?；;])", paragraph) if seg.strip()]
        if not sentences:
            sentences = [paragraph]
        for sentence in sentences:
            if len(sentence) <= KNOWLEDGE_CHUNK_CHAR_LIMIT:
                pieces.append(sentence)
                continue
            start = 0
            step = max(80, KNOWLEDGE_CHUNK_CHAR_LIMIT - KNOWLEDGE_CHUNK_OVERLAP)
            while start < len(sentence):
                pieces.append(sentence[start : start + KNOWLEDGE_CHUNK_CHAR_LIMIT])
                start += step

    chunks = []
    section_title = str(title or "").strip()
    current = ""
    for piece in pieces:
        text = str(piece or "").strip()
        if not text:
            continue
        is_heading = len(text) <= 30 and bool(re.match(r"^(#|第[一二三四五六七八九十0-9]+|[0-9一二三四五六七八九十]+[、.．])", text))
        if is_heading:
            section_title = text.lstrip("#").strip()
            continue
        if not current:
            current = text
            continue
        if len(current) + len(text) + 1 <= KNOWLEDGE_CHUNK_CHAR_LIMIT:
            current = f"{current}\n{text}"
            continue
        chunks.append(
            {
                "sectionTitle": section_title,
                "chunkText": current,
                "keywords": _knowledge_build_keywords(f"{title} {section_title} {current}"),
            }
        )
        overlap = current[-KNOWLEDGE_CHUNK_OVERLAP :] if KNOWLEDGE_CHUNK_OVERLAP > 0 else ""
        current = f"{overlap}{text}" if overlap else text
        if len(current) > KNOWLEDGE_CHUNK_CHAR_LIMIT:
            current = current[-KNOWLEDGE_CHUNK_CHAR_LIMIT :]
    if current:
        chunks.append(
            {
                "sectionTitle": section_title,
                "chunkText": current,
                "keywords": _knowledge_build_keywords(f"{title} {section_title} {current}"),
            }
        )
    for idx, item in enumerate(chunks, start=1):
        item["chunkNo"] = idx
    return chunks


def rebuild_knowledge_document_chunks(document_id):
    rows = query(
        """
        SELECT id,
               title,
               source_content AS sourceContent
        FROM knowledge_document
        WHERE id=%s
        LIMIT 1
        """,
        (int(document_id),),
    )
    row = rows[0] if rows else None
    if not row:
        raise BizError("knowledge document not found", 404)

    content = str(row.get("sourceContent") or "").strip()
    if not content:
        raise BizError("knowledge document content required", 400)
    title = str(row.get("title") or "").strip()
    chunks = _knowledge_split_text(content, title=title)
    if not chunks:
        raise BizError("knowledge document content required", 400)

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = _knowledge_extract_summary(content)
    keywords = _knowledge_build_keywords(f"{title} {content}")

    def _tx(cur):
        cur.execute("DELETE FROM knowledge_chunk WHERE document_id=%s", (int(document_id),))
        for item in chunks:
            chunk_text = str(item.get("chunkText") or "").strip()
            cur.execute(
                """
                INSERT INTO knowledge_chunk (
                    document_id, chunk_no, section_title, chunk_text, keywords, text_hash, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    int(document_id),
                    int(item.get("chunkNo") or 0),
                    str(item.get("sectionTitle") or "").strip()[:200],
                    chunk_text,
                    str(item.get("keywords") or "").strip()[:500],
                    hashlib.sha1(chunk_text.encode("utf-8", errors="ignore")).hexdigest(),
                    now_text,
                ),
            )
        cur.execute(
            """
            UPDATE knowledge_document
            SET summary=%s,
                keywords=%s,
                chunk_count=%s,
                last_indexed_at=%s,
                updated_at=%s
            WHERE id=%s
            """,
            (summary, keywords, len(chunks), now_text, now_text, int(document_id)),
        )
        return {"documentId": int(document_id), "chunkCount": len(chunks), "summary": summary}

    return run_in_transaction(_tx)


def search_knowledge_chunks(query_text, current_role="", limit=None):
    query_raw = re.sub(r"\s+", " ", str(query_text or "").strip())
    if not query_raw:
        return []
    query_tokens = _knowledge_tokenize(query_raw, limit=50)
    if not query_tokens:
        return []
    top_k = max(1, min(8, int(limit or KNOWLEDGE_SEARCH_TOP_K)))
    scope_roles = ["all"]
    role = str(current_role or "").strip().lower()
    if role and role in KNOWLEDGE_SCOPE_ROLE_SET and role != "all":
        scope_roles.append(role)
    placeholders = ",".join(["%s"] * len(scope_roles))
    rows = query(
        f"""
        SELECT kc.id,
               kc.document_id AS documentId,
               kc.chunk_no AS chunkNo,
               kc.section_title AS sectionTitle,
               kc.chunk_text AS chunkText,
               kc.keywords AS chunkKeywords,
               kd.title,
               kd.category,
               kd.scope_role AS scopeRole,
               kd.summary
        FROM knowledge_chunk kc
        INNER JOIN knowledge_document kd ON kd.id=kc.document_id
        WHERE kd.status='active'
          AND kd.scope_role IN ({placeholders})
        ORDER BY kd.updated_at DESC, kc.document_id DESC, kc.chunk_no ASC
        LIMIT 600
        """,
        tuple(scope_roles),
    )
    query_token_set = set(query_tokens)
    scored = []
    for row in rows or []:
        title = str(row.get("title") or "").strip()
        section_title = str(row.get("sectionTitle") or "").strip()
        chunk_text = str(row.get("chunkText") or "").strip()
        searchable_text = f"{title} {section_title} {row.get('chunkKeywords') or ''} {chunk_text}"
        chunk_tokens = set(_knowledge_tokenize(searchable_text, limit=160))
        overlap = [token for token in query_tokens if token in chunk_tokens]
        if not overlap:
            continue
        overlap_count = len(overlap)
        coverage = overlap_count / float(max(1, len(query_token_set)))
        score = overlap_count * 1.4 + coverage * 3.0
        lowered_query = query_raw.lower()
        if lowered_query and lowered_query in title.lower():
            score += 2.4
        elif lowered_query and lowered_query in chunk_text.lower():
            score += 1.4
        if any(token in title.lower() for token in overlap):
            score += 0.8
        if any(token in section_title.lower() for token in overlap):
            score += 0.5
        if coverage < 0.18 and overlap_count < 2:
            score -= 0.8
        if score <= 0:
            continue
        item = dict(row)
        item["score"] = round(score, 4)
        item["overlapTokens"] = overlap[:8]
        scored.append(item)
    scored.sort(key=lambda x: (-float(x.get("score") or 0), int(x.get("documentId") or 0), int(x.get("chunkNo") or 0)))
    return scored[:top_k]


def _build_knowledge_sources(hits):
    sources = []
    seen = set()
    for item in hits or []:
        row = item if isinstance(item, dict) else {}
        key = (int(row.get("documentId") or 0), int(row.get("chunkNo") or 0))
        if key in seen:
            continue
        seen.add(key)
        section = str(row.get("sectionTitle") or "").strip()
        label = str(row.get("title") or "").strip() or f"知识文档#{key[0]}"
        if section:
            label = f"{label} · {section}"
        sources.append(
            {
                "documentId": key[0],
                "chunkNo": key[1],
                "title": label[:200],
                "category": str(row.get("category") or "").strip(),
                "sectionTitle": section[:200],
                "excerpt": _knowledge_extract_summary(row.get("chunkText"), max_len=180),
                "score": round(float(row.get("score") or 0), 4),
            }
        )
        if len(sources) >= KNOWLEDGE_SEARCH_TOP_K:
            break
    return sources


def _build_knowledge_fallback_reply(query_text, hits):
    sources = _build_knowledge_sources(hits)
    if not sources:
        return ""
    lines = []
    for idx, item in enumerate(sources[:3], start=1):
        title = str(item.get("title") or f"来源{idx}").strip()
        excerpt = str(item.get("excerpt") or "").strip()
        if excerpt:
            lines.append(f"{idx}. {title}：{excerpt}")
        else:
            lines.append(f"{idx}. {title}")
    return "我在知识库里找到了这些相关内容：\n" + "\n".join(lines)


def _call_siliconflow_grounded_knowledge_reply(query_text, hits):
    if not hits:
        return ""
    evidence_blocks = []
    for idx, item in enumerate(hits[:KNOWLEDGE_SEARCH_TOP_K], start=1):
        title = str(item.get("title") or "").strip()
        section = str(item.get("sectionTitle") or "").strip()
        chunk_text = str(item.get("chunkText") or "").strip()
        category = str(item.get("category") or "").strip()
        evidence_blocks.append(f"[{idx}] 文档：{title}\n分类：{category}\n章节：{section}\n内容：{chunk_text}")
    prompt = (
        "你是高校实验室知识库助手。"
        "必须严格基于给定知识片段回答，不能编造制度、参数或流程。"
        "如果知识片段不足以确认，请明确说“知识库暂无足够依据”。"
        "回答要简洁、清楚，并在关键结论后用[1][2]标明依据。"
    )
    content = _call_siliconflow_chat(
        [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"问题：{query_text}\n\n知识片段：\n" + "\n\n".join(evidence_blocks)},
        ],
        temperature=0.2,
    )
    return str(content or "").strip()


def ask_knowledge_base(query_text, current_role="", actor=None, limit=None):
    actor = actor or getattr(g, "current_user", {}) or {}
    started_at = time.time()
    hits = search_knowledge_chunks(query_text, current_role=current_role, limit=limit)
    if not hits:
        return {"matched": False, "answer": "", "sources": [], "hits": [], "queryLogId": 0}

    top_score = float((hits[0] or {}).get("score") or 0)
    if top_score < 1.2:
        return {"matched": False, "answer": "", "sources": [], "hits": [], "queryLogId": 0}

    try:
        answer = _call_siliconflow_grounded_knowledge_reply(query_text, hits) if SILICONFLOW_API_KEY else ""
    except BizError:
        answer = ""
    if not answer:
        answer = _build_knowledge_fallback_reply(query_text, hits)
    sources = _build_knowledge_sources(hits)
    latency_ms = int(round((time.time() - started_at) * 1000))
    query_log_id = execute_insert(
        """
        INSERT INTO knowledge_query_log (
            user_id, username, role, query_text, answer_text, matched_count,
            hit_document_ids_json, hit_chunk_ids_json, latency_ms, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            _to_int_or_none(actor.get("id")),
            str(actor.get("username") or "").strip(),
            str(current_role or actor.get("role") or "").strip(),
            str(query_text or "").strip()[:500],
            str(answer or ""),
            len(hits),
            _json_dumps_safe([int(item.get("documentId") or 0) for item in hits]),
            _json_dumps_safe([int(item.get("id") or 0) for item in hits]),
            latency_ms,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    return {
        "matched": True,
        "answer": answer,
        "sources": sources,
        "hits": hits,
        "queryLogId": int(query_log_id or 0),
    }


def _build_equipment_prediction_recommendation(risk_score, status_text, top_factors):
    if risk_score >= 85:
        return "建议 7 天内安排优先巡检，并评估是否需要停用或更换。"
    if risk_score >= 65:
        return "建议在下一轮维护中优先检查，并关注近期故障复发。"
    if status_text == "repairing":
        return "当前处于维修中，建议维修完成后做回归验证。"
    if top_factors:
        return "建议保持例行巡检，并重点关注高权重风险因子。"
    return "建议保持常规巡检。"


def refresh_equipment_failure_predictions(target_date=None, horizon_days_list=None):
    ensure_equipment_failure_prediction_tables()
    if str(target_date or "").strip():
        parsed_dt = _parse_date_yyyy_mm_dd(target_date)
        today_dt = parsed_dt if parsed_dt else datetime.now()
    else:
        today_dt = datetime.now()
    snapshot_date = today_dt.strftime("%Y-%m-%d")
    horizon_days_values = horizon_days_list if isinstance(horizon_days_list, (list, tuple)) and horizon_days_list else [7, 30]
    horizon_days_values = [int(x) for x in horizon_days_values if int(x) in {7, 30}]
    if not horizon_days_values:
        horizon_days_values = [7, 30]

    equipment_rows = query(
        """
        SELECT id,
               asset_code AS assetCode,
               name,
               lab_id AS labId,
               status,
               purchase_date AS purchaseDate,
               next_maintenance_at AS nextMaintenanceAt
        FROM equipment
        WHERE status<>'scrapped'
        ORDER BY id ASC
        """
    )
    if not equipment_rows:
        return {"snapshotDate": snapshot_date, "equipmentCount": 0, "predictionCount": 0}

    now_text = today_dt.strftime("%Y-%m-%d %H:%M:%S")
    d7 = (today_dt - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    d30 = (today_dt - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    d90 = (today_dt - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")

    repair_rows = query(
        """
        SELECT equipment_id AS equipmentId,
               issue_type AS issueType,
               SUM(CASE WHEN created_at >= %s THEN 1 ELSE 0 END) AS repair7d,
               SUM(CASE WHEN created_at >= %s THEN 1 ELSE 0 END) AS repair30d,
               SUM(CASE WHEN created_at >= %s THEN 1 ELSE 0 END) AS repair90d,
               MAX(created_at) AS lastRepairAt,
               COUNT(*) AS totalCount
        FROM repair_work_order
        WHERE equipment_id IS NOT NULL
        GROUP BY equipment_id, issue_type
        """,
        (d7, d30, d90),
    )
    repair_stats = {}
    for row in repair_rows or []:
        equipment_id = int(row.get("equipmentId") or 0)
        if equipment_id <= 0:
            continue
        stat = repair_stats.setdefault(
            equipment_id,
            {"repair7d": 0, "repair30d": 0, "repair90d": 0, "lastRepairAt": "", "issueCounts": {}},
        )
        stat["repair7d"] += int(row.get("repair7d") or 0)
        stat["repair30d"] += int(row.get("repair30d") or 0)
        stat["repair90d"] += int(row.get("repair90d") or 0)
        last_repair_at = _to_text_time(row.get("lastRepairAt"))
        if last_repair_at and (not stat["lastRepairAt"] or last_repair_at > stat["lastRepairAt"]):
            stat["lastRepairAt"] = last_repair_at
        issue_type = str(row.get("issueType") or "").strip().lower() or "other"
        stat["issueCounts"][issue_type] = int(stat["issueCounts"].get(issue_type) or 0) + int(row.get("totalCount") or 0)

    borrow_rows = query(
        """
        SELECT equipment_id AS equipmentId,
               SUM(CASE WHEN borrow_start_at >= %s THEN 1 ELSE 0 END) AS borrow30d
        FROM equipment_borrow_request
        WHERE equipment_id IS NOT NULL
          AND status IN ('approved', 'returned')
        GROUP BY equipment_id
        """,
        (d30,),
    )
    borrow_stats = {int(row.get("equipmentId") or 0): int(row.get("borrow30d") or 0) for row in (borrow_rows or []) if int(row.get("equipmentId") or 0) > 0}

    alarm_rows = query(
        """
        SELECT lab_id AS labId,
               SUM(CASE WHEN created_at >= %s THEN 1 ELSE 0 END) AS alarm7d,
               SUM(CASE WHEN created_at >= %s THEN 1 ELSE 0 END) AS alarm30d
        FROM lab_sensor_alarm
        WHERE lab_id IS NOT NULL
        GROUP BY lab_id
        """,
        (d7, d30),
    )
    alarm_stats = {int(row.get("labId") or 0): {"alarm7d": int(row.get("alarm7d") or 0), "alarm30d": int(row.get("alarm30d") or 0)} for row in (alarm_rows or []) if int(row.get("labId") or 0) > 0}

    snapshot_rows = []
    prediction_rows = []
    for equipment in equipment_rows:
        equipment_id = int(equipment.get("id") or 0)
        repair_stat = repair_stats.get(equipment_id, {})
        alarm_stat = alarm_stats.get(int(equipment.get("labId") or 0), {})
        borrow_30d = int(borrow_stats.get(equipment_id) or 0)

        last_repair_days = None
        last_repair_text = str(repair_stat.get("lastRepairAt") or "").strip()
        if last_repair_text:
            last_repair_dt = _to_datetime(last_repair_text)
            if last_repair_dt != datetime.min:
                last_repair_days = max(0, (today_dt.date() - last_repair_dt.date()).days)

        purchase_dt = _parse_date_yyyy_mm_dd(str(equipment.get("purchaseDate") or "").strip())
        age_days = None
        if purchase_dt:
            age_days = max(0, (today_dt.date() - purchase_dt.date()).days)

        next_maintenance_dt = _to_datetime(equipment.get("nextMaintenanceAt"))
        maintenance_due = bool(next_maintenance_dt != datetime.min and next_maintenance_dt.date() <= today_dt.date())
        status_text = str(equipment.get("status") or "").strip()
        snapshot_payload = {
            "repairCount7d": int(repair_stat.get("repair7d") or 0),
            "repairCount30d": int(repair_stat.get("repair30d") or 0),
            "repairCount90d": int(repair_stat.get("repair90d") or 0),
            "alarmCount7d": int(alarm_stat.get("alarm7d") or 0),
            "alarmCount30d": int(alarm_stat.get("alarm30d") or 0),
            "borrowCount30d": borrow_30d,
            "lastRepairDays": last_repair_days,
            "ageDays": age_days,
            "maintenanceDue": maintenance_due,
            "currentStatus": status_text,
        }
        snapshot_rows.append({"equipmentId": equipment_id, "payload": snapshot_payload})

        issue_counts = repair_stat.get("issueCounts") if isinstance(repair_stat.get("issueCounts"), dict) else {}
        predicted_issue_type = "other"
        if issue_counts:
            predicted_issue_type = sorted(issue_counts.items(), key=lambda x: (-int(x[1] or 0), str(x[0] or "")))[0][0]

        for horizon_days in horizon_days_values:
            horizon_factor = 0.88 if int(horizon_days) == 7 else 1.0
            factor_items = []
            risk_score = 18.0

            def _push_factor(label, score):
                nonlocal risk_score
                score_value = round(float(score or 0), 2)
                if score_value <= 0:
                    return
                risk_score += score_value
                factor_items.append({"label": label, "score": score_value})

            _push_factor("近7天报修频次", snapshot_payload["repairCount7d"] * 18 * horizon_factor)
            _push_factor("近30天报修频次", snapshot_payload["repairCount30d"] * 9 * horizon_factor)
            _push_factor("近90天报修频次", snapshot_payload["repairCount90d"] * 3.5)
            _push_factor("近30天借用频次", min(18, snapshot_payload["borrowCount30d"] * 1.5))
            _push_factor("实验室近30天告警", min(16, snapshot_payload["alarmCount30d"] * 2.5))
            if status_text == "repairing":
                _push_factor("当前状态为维修中", 10)
            if maintenance_due:
                _push_factor("已到维护周期", 8)
            if last_repair_days is not None and last_repair_days <= 15:
                _push_factor("最近维修间隔较短", 12 if last_repair_days <= 7 else 7)
            if age_days is not None and age_days >= 365 * 4:
                _push_factor("设备服役时间较长", 6 if age_days < 365 * 6 else 10)

            risk_score = min(99.0, round(risk_score, 2))
            failure_probability = round(min(0.99, max(0.05, risk_score / 100.0)), 4)
            risk_level = "high" if risk_score >= 85 else "medium" if risk_score >= 65 else "low"
            factor_items.sort(key=lambda x: (-float(x.get("score") or 0), str(x.get("label") or "")))
            prediction_rows.append(
                {
                    "equipmentId": equipment_id,
                    "predictDate": snapshot_date,
                    "horizonDays": int(horizon_days),
                    "riskScore": risk_score,
                    "failureProbability": failure_probability,
                    "riskLevel": risk_level,
                    "predictedIssueType": predicted_issue_type,
                    "topFactors": factor_items[:5],
                    "recommendation": _build_equipment_prediction_recommendation(risk_score, status_text, factor_items[:5]),
                    "modelName": "heuristic-risk-v2",
                    "modelVersion": "2026.03",
                }
            )

    def _tx(cur):
        snapshot_count = 0
        prediction_count = 0
        for item in snapshot_rows:
            payload = item.get("payload") or {}
            cur.execute(
                """
                INSERT INTO equipment_feature_snapshot (
                    equipment_id, snapshot_date,
                    repair_count_7d, repair_count_30d, repair_count_90d,
                    alarm_count_7d, alarm_count_30d, borrow_count_30d,
                    last_repair_days, age_days, current_status, feature_json,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    repair_count_7d=VALUES(repair_count_7d),
                    repair_count_30d=VALUES(repair_count_30d),
                    repair_count_90d=VALUES(repair_count_90d),
                    alarm_count_7d=VALUES(alarm_count_7d),
                    alarm_count_30d=VALUES(alarm_count_30d),
                    borrow_count_30d=VALUES(borrow_count_30d),
                    last_repair_days=VALUES(last_repair_days),
                    age_days=VALUES(age_days),
                    current_status=VALUES(current_status),
                    feature_json=VALUES(feature_json),
                    updated_at=VALUES(updated_at)
                """,
                (
                    int(item.get("equipmentId") or 0),
                    snapshot_date,
                    int(payload.get("repairCount7d") or 0),
                    int(payload.get("repairCount30d") or 0),
                    int(payload.get("repairCount90d") or 0),
                    int(payload.get("alarmCount7d") or 0),
                    int(payload.get("alarmCount30d") or 0),
                    int(payload.get("borrowCount30d") or 0),
                    payload.get("lastRepairDays"),
                    payload.get("ageDays"),
                    str(payload.get("currentStatus") or "").strip()[:32],
                    _json_dumps_safe(payload),
                    now_text,
                    now_text,
                ),
            )
            snapshot_count += 1

        for item in prediction_rows:
            cur.execute(
                """
                INSERT INTO equipment_failure_prediction (
                    equipment_id, predict_date, horizon_days, risk_score, failure_probability,
                    risk_level, predicted_issue_type, top_factors_json, recommendation,
                    model_name, model_version, status, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'new', %s, %s)
                ON DUPLICATE KEY UPDATE
                    risk_score=VALUES(risk_score),
                    failure_probability=VALUES(failure_probability),
                    risk_level=VALUES(risk_level),
                    predicted_issue_type=VALUES(predicted_issue_type),
                    top_factors_json=VALUES(top_factors_json),
                    recommendation=VALUES(recommendation),
                    model_name=VALUES(model_name),
                    model_version=VALUES(model_version),
                    updated_at=VALUES(updated_at)
                """,
                (
                    int(item.get("equipmentId") or 0),
                    snapshot_date,
                    int(item.get("horizonDays") or 7),
                    float(item.get("riskScore") or 0),
                    float(item.get("failureProbability") or 0),
                    str(item.get("riskLevel") or "low").strip(),
                    str(item.get("predictedIssueType") or "other").strip(),
                    _json_dumps_safe(item.get("topFactors") or []),
                    str(item.get("recommendation") or "").strip()[:500],
                    str(item.get("modelName") or "heuristic-risk-v2").strip()[:120],
                    str(item.get("modelVersion") or "2026.03").strip()[:32],
                    now_text,
                    now_text,
                ),
            )
            prediction_count += 1
        return {"snapshotCount": snapshot_count, "predictionCount": prediction_count}

    tx_result = run_in_transaction(_tx)
    return {"snapshotDate": snapshot_date, "equipmentCount": len(snapshot_rows), **tx_result}


def list_equipment_failure_predictions(limit=8, horizon_days=30, auto_refresh=True):
    ensure_equipment_failure_prediction_tables()
    predict_date = datetime.now().strftime("%Y-%m-%d")
    target_horizon = 30 if int(horizon_days or 30) == 30 else 7
    limit_num = max(1, min(int(limit or 8), 30))

    def _query_rows():
        return query(
            """
            SELECT p.id,
                   p.equipment_id AS equipmentId,
                   p.predict_date AS predictDate,
                   p.horizon_days AS horizonDays,
                   p.risk_score AS riskScore,
                   p.failure_probability AS failureProbability,
                   p.risk_level AS riskLevel,
                   p.predicted_issue_type AS predictedIssueType,
                   p.top_factors_json AS topFactorsJson,
                   p.recommendation,
                   p.model_name AS modelName,
                   p.model_version AS modelVersion,
                   e.asset_code AS assetCode,
                   e.name,
                   e.status,
                   e.lab_id AS labId,
                   e.lab_name AS labName,
                   s.repair_count_7d AS repairCount7d,
                   s.repair_count_30d AS repairCount30d,
                   s.repair_count_90d AS repairCount90d,
                   s.alarm_count_7d AS alarmCount7d,
                   s.alarm_count_30d AS alarmCount30d,
                   s.borrow_count_30d AS borrowCount30d,
                   s.last_repair_days AS lastRepairDays,
                   s.age_days AS ageDays
            FROM equipment_failure_prediction p
            INNER JOIN equipment e ON e.id=p.equipment_id
            LEFT JOIN equipment_feature_snapshot s ON s.equipment_id=p.equipment_id AND s.snapshot_date=p.predict_date
            WHERE p.predict_date=%s
              AND p.horizon_days=%s
            ORDER BY p.risk_score DESC, p.failure_probability DESC, p.equipment_id DESC
            LIMIT %s
            """,
            (predict_date, target_horizon, limit_num),
        )

    rows = _query_rows()
    if auto_refresh and not rows:
        refresh_equipment_failure_predictions(target_date=predict_date, horizon_days_list=[target_horizon])
        rows = _query_rows()

    items = []
    for row in rows or []:
        try:
            top_factors = json.loads(str(row.get("topFactorsJson") or "[]"))
        except Exception:
            top_factors = []
        if not isinstance(top_factors, list):
            top_factors = []
        items.append(
            {
                "predictionId": int(row.get("id") or 0),
                "equipmentId": int(row.get("equipmentId") or 0),
                "assetCode": str(row.get("assetCode") or "").strip(),
                "name": str(row.get("name") or "").strip() or f"设备#{int(row.get('equipmentId') or 0)}",
                "status": str(row.get("status") or "").strip(),
                "labId": _to_int_or_none(row.get("labId")),
                "labName": str(row.get("labName") or "").strip(),
                "predictDate": str(row.get("predictDate") or "").strip(),
                "horizonDays": int(row.get("horizonDays") or target_horizon),
                "riskScore": round(float(row.get("riskScore") or 0), 2),
                "failureProbability": round(float(row.get("failureProbability") or 0), 4),
                "riskLevel": str(row.get("riskLevel") or "").strip() or "low",
                "predictedIssueType": str(row.get("predictedIssueType") or "").strip() or "other",
                "recommendation": str(row.get("recommendation") or "").strip(),
                "modelName": str(row.get("modelName") or "").strip(),
                "modelVersion": str(row.get("modelVersion") or "").strip(),
                "repairCount7d": int(row.get("repairCount7d") or 0),
                "repairCount30d": int(row.get("repairCount30d") or 0),
                "repairCount90d": int(row.get("repairCount90d") or 0),
                "alarmCount7d": int(row.get("alarmCount7d") or 0),
                "alarmCount30d": int(row.get("alarmCount30d") or 0),
                "borrowCount30d": int(row.get("borrowCount30d") or 0),
                "lastRepairDays": _to_int_or_none(row.get("lastRepairDays")),
                "ageDays": _to_int_or_none(row.get("ageDays")),
                "topFactors": top_factors[:5],
            }
        )
    return {"predictDate": predict_date, "horizonDays": target_horizon, "items": items}


def _normalize_course_task_reminder_before_hours(raw_value, default_value=24):
    val = _to_int_or_none(raw_value)
    if val is None:
        val = int(default_value or 24)
    val = int(val)
    if val < 1:
        val = 1
    if val > 168:
        val = 168
    return int(val)


def get_course_task_reminder_subscription(user_name):
    user = str(user_name or "").strip()
    if not user:
        return {"enabled": True, "beforeHours": 24, "remindOverdue": True}

    rows = query(
        """
        SELECT enabled,
               before_hours AS beforeHours,
               remind_overdue AS remindOverdue
        FROM course_task_notice_subscription
        WHERE user_name=%s
        LIMIT 1
        """,
        (user,),
    )
    if not rows:
        return {"enabled": True, "beforeHours": 24, "remindOverdue": True}

    row = rows[0] or {}
    return {
        "enabled": bool(int(row.get("enabled") or 0) == 1),
        "beforeHours": _normalize_course_task_reminder_before_hours(row.get("beforeHours"), 24),
        "remindOverdue": bool(int(row.get("remindOverdue") or 0) == 1),
    }


def save_course_task_reminder_subscription(user_name, enabled=True, before_hours=24, remind_overdue=True):
    user = str(user_name or "").strip()
    if not user:
        raise BizError("user required", 400)

    enabled_flag = 1 if bool(enabled) else 0
    remind_overdue_flag = 1 if bool(remind_overdue) else 0
    normalized_before_hours = _normalize_course_task_reminder_before_hours(before_hours, 24)
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    execute(
        """
        INSERT INTO course_task_notice_subscription (
            user_name, enabled, before_hours, remind_overdue, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            enabled=VALUES(enabled),
            before_hours=VALUES(before_hours),
            remind_overdue=VALUES(remind_overdue),
            updated_at=VALUES(updated_at)
        """,
        (
            user,
            enabled_flag,
            normalized_before_hours,
            remind_overdue_flag,
            now_text,
            now_text,
        ),
    )
    return {
        "enabled": bool(enabled_flag == 1),
        "beforeHours": int(normalized_before_hours),
        "remindOverdue": bool(remind_overdue_flag == 1),
    }


def insert_course_task_auto_notice_log_with_cur(
    cur,
    course_id,
    task_id,
    to_user_name,
    reminder_kind,
    remind_date,
    created_at="",
):
    if cur is None:
        return False
    to_user = str(to_user_name or "").strip()
    kind = str(reminder_kind or "").strip()
    date_text = str(remind_date or "").strip()
    if not to_user or not kind or not date_text:
        return False
    created = str(created_at or "").strip() or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """
        INSERT IGNORE INTO course_task_auto_notice_log (
            course_id, task_id, to_user_name, reminder_kind, remind_date, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            int(_to_int_or_none(course_id) or 0),
            int(_to_int_or_none(task_id) or 0),
            to_user,
            kind,
            date_text,
            created,
        ),
    )
    return int(cur.rowcount or 0) > 0


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


def issue_refresh_token(user_id, device_name="", user_agent="", login_ip=""):
    raw = create_refresh_token()
    token_hash = hash_refresh_token(raw)
    now = datetime.now()
    exp = now.timestamp() + REFRESH_EXPIRE_SECONDS
    expires_at = datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M:%S")
    created_at = now.strftime("%Y-%m-%d %H:%M:%S")
    safe_device_name = str(device_name or "").strip()[:128]
    safe_user_agent = str(user_agent or "").strip()[:255]
    safe_login_ip = str(login_ip or "").strip()[:64]
    execute_insert(
        """
        INSERT INTO auth_refresh_token (
            user_id, token_hash, expires_at, created_at, device_name, user_agent, login_ip, last_seen_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (user_id, token_hash, expires_at, created_at, safe_device_name, safe_user_agent, safe_login_ip, created_at),
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
               revoked_at AS revokedAt, device_name AS deviceName, user_agent AS userAgent,
               login_ip AS loginIp, last_seen_at AS lastSeenAt
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


def auth_required(roles=None, permissions=None, require_all_permissions=False):
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
            row = query(
                """
                SELECT id,
                       username,
                       role,
                       is_active AS isActive,
                       is_frozen AS isFrozen
                FROM user
                WHERE id=%s
                LIMIT 1
                """,
                (uid,),
            )
            if not row:
                return jsonify({"ok": False, "msg": "unauthorized"}), 401
            current_user = row[0]
            if int(current_user.get("isActive") or 0) != 1:
                return jsonify({"ok": False, "msg": "account disabled"}), 403
            if int(current_user.get("isFrozen") or 0) == 1:
                return jsonify({"ok": False, "msg": "account frozen"}), 403
            role_allowed = bool(not roles or current_user["role"] in roles)
            permission_items = [str(item or "").strip() for item in (permissions or []) if str(item or "").strip()]
            current_user["permissions"] = list_effective_user_permissions(current_user) if permission_items else []
            permission_allowed = True
            if permission_items:
                checks = [has_user_permission(current_user, code) for code in permission_items]
                permission_allowed = all(checks) if require_all_permissions else any(checks)
            if roles and permission_items:
                if not (role_allowed or permission_allowed):
                    return jsonify({"ok": False, "msg": "forbidden"}), 403
            elif roles:
                if not role_allowed:
                    return jsonify({"ok": False, "msg": "forbidden"}), 403
            elif permission_items and not permission_allowed:
                return jsonify({"ok": False, "msg": "forbidden"}), 403
            g.current_user = current_user
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def _normalize_profile_nickname(value):
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if len(text) > 24:
        raise BizError("nickname too long", 400)
    return text


def _normalize_profile_phone(value):
    text = str(value or "").strip()
    if len(text) > 20:
        raise BizError("phone too long", 400)
    return text


def _normalize_profile_email(value):
    text = str(value or "").strip().lower()
    if len(text) > 120:
        raise BizError("email too long", 400)
    if text and not re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", text):
        raise BizError("invalid email", 400)
    return text


def _normalize_profile_class_name(value):
    text = str(value or "").strip()
    if len(text) > 64:
        raise BizError("className too long", 400)
    return text


def _normalize_profile_student_no(value):
    text = str(value or "").strip()
    if len(text) > 64:
        raise BizError("studentNo too long", 400)
    return text


def _normalize_profile_job_no(value):
    text = str(value or "").strip()
    if len(text) > 64:
        raise BizError("jobNo too long", 400)
    return text


def _normalize_profile_avatar_url(value):
    text = str(value or "").strip()
    if len(text) > 255:
        raise BizError("avatarUrl too long", 400)
    return text


def get_user_profile_row_by_id(uid):
    rows = query(
        """
        SELECT id,
               username,
               role,
               nickname,
               phone,
               email,
               class_name AS className,
               student_no AS studentNo,
               job_no AS jobNo,
               avatar_url AS avatarUrl
        FROM user
        WHERE id=%s
        LIMIT 1
        """,
        (uid,),
    )
    return rows[0] if rows else None


def get_user_profile_row_by_username(username):
    rows = query(
        """
        SELECT id,
               username,
               role,
               nickname,
               phone,
               email,
               class_name AS className,
               student_no AS studentNo,
               job_no AS jobNo,
               avatar_url AS avatarUrl
        FROM user
        WHERE username=%s
        LIMIT 1
        """,
        (username,),
    )
    return rows[0] if rows else None


def format_user_profile_payload(row):
    data = row or {}
    username = str(data.get("username") or "").strip()
    role = str(data.get("role") or "").strip()
    nickname = str(data.get("nickname") or "").strip() or username
    class_name = str(data.get("className") or "").strip()
    student_no = str(data.get("studentNo") or "").strip()
    job_no = str(data.get("jobNo") or "").strip()
    return {
        "userId": int(data.get("id") or 0),
        "username": username,
        "role": role,
        "nickname": nickname,
        "phone": str(data.get("phone") or "").strip(),
        "email": str(data.get("email") or "").strip(),
        "className": class_name,
        "studentNo": student_no,
        "jobNo": job_no,
        "avatarUrl": str(data.get("avatarUrl") or "").strip(),
    }


def update_user_profile_fields(
    uid,
    nickname=None,
    phone=None,
    email=None,
    class_name=None,
    student_no=None,
    job_no=None,
    avatar_url=None,
):
    existing = get_user_profile_row_by_id(uid)
    if not existing:
        raise BizError("user not found", 404)

    next_nickname = str(existing.get("nickname") or "").strip()
    next_phone = str(existing.get("phone") or "").strip()
    next_email = str(existing.get("email") or "").strip()
    next_class_name = str(existing.get("className") or "").strip()
    next_student_no = str(existing.get("studentNo") or "").strip()
    next_job_no = str(existing.get("jobNo") or "").strip()
    next_avatar_url = str(existing.get("avatarUrl") or "").strip()

    if nickname is not None:
        next_nickname = _normalize_profile_nickname(nickname)
    if phone is not None:
        next_phone = _normalize_profile_phone(phone)
    if email is not None:
        next_email = _normalize_profile_email(email)
    if class_name is not None:
        next_class_name = _normalize_profile_class_name(class_name)
    if student_no is not None:
        next_student_no = _normalize_profile_student_no(student_no)
    if job_no is not None:
        next_job_no = _normalize_profile_job_no(job_no)
    if avatar_url is not None:
        next_avatar_url = _normalize_profile_avatar_url(avatar_url)

    execute(
        """
        UPDATE user
        SET nickname=%s,
            phone=%s,
            email=%s,
            class_name=%s,
            student_no=%s,
            job_no=%s,
            avatar_url=%s
        WHERE id=%s
        """,
        (next_nickname, next_phone, next_email, next_class_name, next_student_no, next_job_no, next_avatar_url, uid),
    )

    updated = get_user_profile_row_by_id(uid)
    if not updated:
        raise BizError("user not found", 404)
    return format_user_profile_payload(updated)


def update_user_profile_by_username(
    username,
    nickname=None,
    phone=None,
    email=None,
    class_name=None,
    student_no=None,
    job_no=None,
    avatar_url=None,
):
    row = get_user_profile_row_by_username(username)
    if not row:
        raise BizError("user not found", 404)
    uid = int(row.get("id") or 0)
    if uid <= 0:
        raise BizError("user not found", 404)
    return update_user_profile_fields(
        uid,
        nickname=nickname,
        phone=phone,
        email=email,
        class_name=class_name,
        student_no=student_no,
        job_no=job_no,
        avatar_url=avatar_url,
    )


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


def _json_clone(value, fallback=None):
    try:
        return json.loads(json.dumps(value, ensure_ascii=False))
    except Exception:
        return {} if fallback is None else fallback


def _normalize_bool(value, default=False):
    if isinstance(value, bool):
        return value
    raw = str(value or "").strip().lower()
    if raw in {"1", "true", "yes", "on", "y"}:
        return True
    if raw in {"0", "false", "no", "off", "n"}:
        return False
    return bool(default)


def _normalize_rule_clock(text, fallback):
    raw = str(text or "").strip()
    if not raw:
        raw = str(fallback or "").strip()
    minutes = _clock_to_minutes(raw)
    if minutes is None:
        raw = str(fallback or "").strip()
        minutes = _clock_to_minutes(raw)
    if minutes is None:
        return ""
    return _minutes_to_hhmm(minutes)


def _normalize_rule_slots(raw_slots, min_time, max_time, fallback_slots=None, allow_empty=False):
    source = raw_slots
    if isinstance(source, str):
        source = [x.strip() for x in source.split(",") if x.strip()]
    if not isinstance(source, list):
        source = []

    allowed_start = _clock_to_minutes(min_time)
    allowed_end = _clock_to_minutes(max_time)
    resolved = []
    seen = set()
    for raw in source:
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

    if resolved:
        return resolved
    if allow_empty:
        return []

    fallback = fallback_slots
    if isinstance(fallback, str):
        fallback = [x.strip() for x in fallback.split(",") if x.strip()]
    if not isinstance(fallback, list) or not fallback:
        fallback = list(DEFAULT_RESERVATION_SLOTS)

    seen = set()
    for raw in fallback:
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


def _normalize_rule_date_list(raw_dates):
    source = raw_dates
    if isinstance(source, str):
        source = [x.strip() for x in source.split(",") if x.strip()]
    if not isinstance(source, list):
        return []

    resolved = []
    seen = set()
    for raw in source:
        dt = _parse_date_yyyy_mm_dd(raw)
        if not dt:
            continue
        text = dt.strftime("%Y-%m-%d")
        if text in seen:
            continue
        seen.add(text)
        resolved.append(text)
    resolved.sort()
    return resolved


def _normalize_rule_blackout_slots(raw_items, allowed_slots):
    if not isinstance(raw_items, list):
        return []
    allowed = set(allowed_slots or [])
    rows = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        dt = _parse_date_yyyy_mm_dd(item.get("date"))
        if not dt:
            continue
        slots_raw = item.get("slots")
        if slots_raw is None and item.get("time"):
            slots_raw = str(item.get("time") or "").split(",")
        slots = _normalize_rule_slots(slots_raw, "00:00", "23:59", [], allow_empty=True)
        if allowed:
            slots = [x for x in slots if x in allowed]
        if not slots:
            continue
        reason = str(item.get("reason") or "").strip()
        rows.append(
            {
                "date": dt.strftime("%Y-%m-%d"),
                "slots": slots,
                "reason": reason[:120],
            }
        )
    rows.sort(key=lambda x: (x.get("date") or "", ",".join(x.get("slots") or [])))
    return rows


def _default_approval_mode():
    mode = str(RESERVATION_APPROVAL_MODE or "").strip().lower()
    if mode not in RESERVATION_APPROVAL_MODE_SET:
        return "admin"
    return mode


def _normalize_rule_approval(raw_approval, allowed_slots, base=None):
    incoming = raw_approval if isinstance(raw_approval, dict) else {}
    base_dict = base if isinstance(base, dict) else {}

    if "mode" in incoming:
        mode = str(incoming.get("mode") or "").strip().lower()
    else:
        mode = str(base_dict.get("mode") or "").strip().lower() or _default_approval_mode()
    if mode not in RESERVATION_APPROVAL_MODE_SET:
        mode = _default_approval_mode()

    if "peakForceApproval" in incoming:
        peak_force = _normalize_bool(incoming.get("peakForceApproval"), False)
    elif "peakForceApproval" in base_dict:
        peak_force = _normalize_bool(base_dict.get("peakForceApproval"), False)
    else:
        peak_force = bool(RESERVATION_PEAK_FORCE_APPROVAL)

    if "peakSlots" in incoming:
        peak_source = incoming.get("peakSlots")
    elif "peakSlots" in base_dict:
        peak_source = base_dict.get("peakSlots")
    elif RESERVATION_PEAK_SLOTS_TEXT:
        peak_source = [x.strip() for x in RESERVATION_PEAK_SLOTS_TEXT.split(",") if x.strip()]
    else:
        peak_source = []
    peak_slots = _normalize_rule_slots(peak_source, "00:00", "23:59", [], allow_empty=True)
    allowed = set(allowed_slots or [])
    if allowed:
        peak_slots = [x for x in peak_slots if x in allowed]

    return {
        "mode": mode,
        "peakForceApproval": bool(peak_force),
        "peakSlots": peak_slots,
    }


def _default_reservation_rule_scope():
    min_days = max(0, int(RESERVATION_MIN_DAYS_AHEAD or 0))
    max_days = max(min_days, int(RESERVATION_MAX_DAYS_AHEAD or 0))
    min_time = _normalize_rule_clock(RESERVATION_MIN_TIME, "08:00")
    max_time = _normalize_rule_clock(RESERVATION_MAX_TIME, "22:00")
    if _clock_to_minutes(max_time) is None or _clock_to_minutes(min_time) is None or _clock_to_minutes(max_time) <= _clock_to_minutes(min_time):
        min_time = "08:00"
        max_time = "22:00"
    slots = _normalize_rule_slots(DEFAULT_RESERVATION_SLOTS, min_time, max_time, DEFAULT_RESERVATION_SLOTS)
    approval = _normalize_rule_approval({}, slots, base={})
    return {
        "minDaysAhead": min_days,
        "maxDaysAhead": max_days,
        "minTime": min_time,
        "maxTime": max_time,
        "slots": slots,
        "disabledDates": [],
        "blackoutSlots": [],
        "approval": approval,
    }


def _normalize_rule_name_list(value):
    if not isinstance(value, list):
        return []
    seen = set()
    items = []
    for raw in value:
        text = re.sub(r"\s+", " ", str(raw or "").strip())
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        items.append(text[:120])
    return items


def _default_borrow_approval_config():
    return {
        "requireSecondaryConfirm": False,
        "riskFlagForceSecondaryConfirm": True,
        "overdueHistoryForceSecondaryConfirm": True,
        "labNames": [],
        "assetKeywords": [],
    }


def _normalize_borrow_approval_config(raw_config, base=None):
    source = raw_config if isinstance(raw_config, dict) else {}
    fallback = base if isinstance(base, dict) else _default_borrow_approval_config()
    return {
        "requireSecondaryConfirm": bool(_normalize_bool(source.get("requireSecondaryConfirm", fallback.get("requireSecondaryConfirm")), fallback.get("requireSecondaryConfirm"))),
        "riskFlagForceSecondaryConfirm": bool(_normalize_bool(source.get("riskFlagForceSecondaryConfirm", fallback.get("riskFlagForceSecondaryConfirm")), fallback.get("riskFlagForceSecondaryConfirm"))),
        "overdueHistoryForceSecondaryConfirm": bool(
            _normalize_bool(source.get("overdueHistoryForceSecondaryConfirm", fallback.get("overdueHistoryForceSecondaryConfirm")), fallback.get("overdueHistoryForceSecondaryConfirm"))
        ),
        "labNames": _normalize_rule_name_list(source.get("labNames", fallback.get("labNames"))),
        "assetKeywords": _normalize_rule_name_list(source.get("assetKeywords", fallback.get("assetKeywords"))),
    }


def _merge_reservation_rule_scope(raw_scope, fallback_scope):
    base = _json_clone(fallback_scope if isinstance(fallback_scope, dict) else _default_reservation_rule_scope(), {})
    incoming = raw_scope if isinstance(raw_scope, dict) else {}

    min_days = base.get("minDaysAhead", 0)
    if "minDaysAhead" in incoming:
        parsed = _to_int_or_none(incoming.get("minDaysAhead"))
        if parsed is not None:
            min_days = max(0, min(365, int(parsed)))

    max_days = base.get("maxDaysAhead", min_days)
    if "maxDaysAhead" in incoming:
        parsed = _to_int_or_none(incoming.get("maxDaysAhead"))
        if parsed is not None:
            max_days = max(0, min(365, int(parsed)))
    if max_days < min_days:
        max_days = min_days

    min_time = base.get("minTime", "08:00")
    if "minTime" in incoming:
        min_time = _normalize_rule_clock(incoming.get("minTime"), min_time or "08:00")
    min_time = _normalize_rule_clock(min_time, "08:00")

    max_time = base.get("maxTime", "22:00")
    if "maxTime" in incoming:
        max_time = _normalize_rule_clock(incoming.get("maxTime"), max_time or "22:00")
    max_time = _normalize_rule_clock(max_time, "22:00")
    if _clock_to_minutes(max_time) is None or _clock_to_minutes(min_time) is None or _clock_to_minutes(max_time) <= _clock_to_minutes(min_time):
        min_time = _normalize_rule_clock(base.get("minTime"), "08:00")
        max_time = _normalize_rule_clock(base.get("maxTime"), "22:00")

    slots_source = incoming.get("slots") if "slots" in incoming else base.get("slots")
    slots = _normalize_rule_slots(slots_source, min_time, max_time, base.get("slots"))

    if "disabledDates" in incoming:
        date_source = incoming.get("disabledDates")
    elif "holidays" in incoming:
        date_source = incoming.get("holidays")
    else:
        date_source = base.get("disabledDates")
    disabled_dates = _normalize_rule_date_list(date_source)

    if "blackoutSlots" in incoming:
        blackout_source = incoming.get("blackoutSlots")
    elif "blacklistSlots" in incoming:
        blackout_source = incoming.get("blacklistSlots")
    else:
        blackout_source = base.get("blackoutSlots")
    blackout_slots = _normalize_rule_blackout_slots(blackout_source, slots)

    approval_source = incoming.get("approval") if "approval" in incoming else base.get("approval")
    approval = _normalize_rule_approval(approval_source, slots, base=base.get("approval"))

    return {
        "minDaysAhead": min_days,
        "maxDaysAhead": max_days,
        "minTime": min_time,
        "maxTime": max_time,
        "slots": slots,
        "disabledDates": disabled_dates,
        "blackoutSlots": blackout_slots,
        "approval": approval,
    }


def _normalize_reservation_rule_config(raw_config):
    raw = raw_config if isinstance(raw_config, dict) else {}
    default_scope = _default_reservation_rule_scope()
    borrow_approval = _normalize_borrow_approval_config(raw.get("borrowApproval"), raw.get("borrowApproval"))

    raw_global = raw.get("global") if isinstance(raw.get("global"), dict) else {}
    legacy_keys = {
        "minDaysAhead",
        "maxDaysAhead",
        "minTime",
        "maxTime",
        "slots",
        "holidays",
        "disabledDates",
        "blackoutSlots",
        "blacklistSlots",
        "approval",
    }
    if not raw_global:
        for key in legacy_keys:
            if key in raw:
                raw_global[key] = raw.get(key)

    global_scope = _merge_reservation_rule_scope(raw_global, default_scope)

    lab_rules = []
    seen_lab = set()
    raw_lab_rules = raw.get("labRules")
    if isinstance(raw_lab_rules, list):
        for item in raw_lab_rules:
            if not isinstance(item, dict):
                continue
            lab_id = _to_int_or_none(item.get("labId"))
            if lab_id is None or int(lab_id) <= 0:
                continue
            lab_id = int(lab_id)
            if lab_id in seen_lab:
                continue
            seen_lab.add(lab_id)
            enabled = _normalize_bool(item.get("enabled"), True)
            scope = _merge_reservation_rule_scope(item, global_scope)
            scope["labId"] = lab_id
            scope["labName"] = str(item.get("labName") or "").strip()
            scope["enabled"] = bool(enabled)
            lab_rules.append(scope)

    lab_rules.sort(key=lambda x: int(x.get("labId") or 0))
    return {
        "version": 1,
        "global": global_scope,
        "labRules": lab_rules,
        "borrowApproval": borrow_approval,
    }


def _load_reservation_rule_config_from_db():
    try:
        rows = query(
            """
            SELECT config_json AS configJson
            FROM reservation_rule_config
            WHERE id=1
            LIMIT 1
            """
        )
    except Exception:
        return {}
    if not rows:
        return {}
    text = str((rows[0] or {}).get("configJson") or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def get_reservation_rule_config(force_refresh=False):
    now = time.time()
    with _RESERVATION_RULE_LOCK:
        cached_payload = _RESERVATION_RULE_CACHE.get("payload")
        expire_at = float(_RESERVATION_RULE_CACHE.get("expireAt") or 0.0)
        if (not force_refresh) and isinstance(cached_payload, dict) and now < expire_at:
            return _json_clone(cached_payload, {})

    raw = _load_reservation_rule_config_from_db()
    normalized = _normalize_reservation_rule_config(raw)
    with _RESERVATION_RULE_LOCK:
        _RESERVATION_RULE_CACHE["payload"] = _json_clone(normalized, {})
        _RESERVATION_RULE_CACHE["expireAt"] = now + float(RESERVATION_RULE_CONFIG_CACHE_SECONDS)
    return _json_clone(normalized, {})


def save_reservation_rule_config(config_payload, updated_by=""):
    normalized = _normalize_reservation_rule_config(config_payload)
    config_json = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    operator = str(updated_by or "").strip()[:64]

    def _tx(cur):
        cur.execute(
            """
            INSERT INTO reservation_rule_config (id, config_json, updated_by, updated_at)
            VALUES (1, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                config_json=VALUES(config_json),
                updated_by=VALUES(updated_by),
                updated_at=VALUES(updated_at)
            """,
            (config_json, operator, now_text),
        )

    run_in_transaction(_tx)
    with _RESERVATION_RULE_LOCK:
        _RESERVATION_RULE_CACHE["payload"] = _json_clone(normalized, {})
        _RESERVATION_RULE_CACHE["expireAt"] = time.time() + float(RESERVATION_RULE_CONFIG_CACHE_SECONDS)
    return normalized


def _pick_lab_rule_scope(config_payload, lab_id=None, lab_name=""):
    config = config_payload if isinstance(config_payload, dict) else {}
    global_scope = config.get("global") if isinstance(config.get("global"), dict) else _default_reservation_rule_scope()
    lab_rules = config.get("labRules") if isinstance(config.get("labRules"), list) else []
    target_lab_id = _to_int_or_none(lab_id)
    target_lab_name = str(lab_name or "").strip().lower()

    selected = None
    if target_lab_id is not None and int(target_lab_id) > 0:
        for item in lab_rules:
            if not isinstance(item, dict):
                continue
            if not bool(item.get("enabled", True)):
                continue
            if int(_to_int_or_none(item.get("labId")) or 0) == int(target_lab_id):
                selected = item
                break
    if selected is None and target_lab_name:
        for item in lab_rules:
            if not isinstance(item, dict):
                continue
            if not bool(item.get("enabled", True)):
                continue
            item_name = str(item.get("labName") or "").strip().lower()
            if item_name and item_name == target_lab_name:
                selected = item
                break

    if isinstance(selected, dict):
        return _merge_reservation_rule_scope(selected, global_scope), {
            "labId": int(_to_int_or_none(selected.get("labId")) or 0),
            "labName": str(selected.get("labName") or "").strip(),
            "enabled": bool(selected.get("enabled", True)),
        }
    return _json_clone(global_scope, {}), None


def resolve_reservation_review_policy(lab_id=None, lab_name="", date_text="", time_range=""):
    rule_payload = get_reservation_rules_payload(lab_id=lab_id, lab_name=lab_name)
    approval = rule_payload.get("approval") if isinstance(rule_payload.get("approval"), dict) else {}
    mode = str(approval.get("mode") or "").strip().lower()
    if mode not in RESERVATION_APPROVAL_MODE_SET:
        mode = _default_approval_mode()
    peak_force = bool(approval.get("peakForceApproval"))
    peak_slots = set(_normalize_rule_slots(approval.get("peakSlots"), "00:00", "23:59", [], allow_empty=True))
    incoming_slots = parse_slots(time_range)
    is_peak_hit = bool(incoming_slots & peak_slots) if incoming_slots else False

    if mode == "auto" and not (peak_force and is_peak_hit):
        return {
            "status": "approved",
            "reviewRole": "",
            "reviewPolicy": "auto",
            "approvalRequired": False,
            "isPeakSlot": bool(is_peak_hit),
        }

    if mode == "teacher":
        review_role = "teacher"
        review_policy = "teacher"
    else:
        review_role = "admin"
        review_policy = "admin"

    if mode == "auto" and peak_force and is_peak_hit:
        review_role = "admin"
        review_policy = "peak_admin"

    return {
        "status": "pending",
        "reviewRole": review_role,
        "reviewPolicy": review_policy,
        "approvalRequired": True,
        "isPeakSlot": bool(is_peak_hit),
    }


def resolve_borrow_approval_policy(request_row):
    config_payload = get_reservation_rule_config(force_refresh=False)
    config = _normalize_borrow_approval_config(config_payload.get("borrowApproval"))
    item = request_row if isinstance(request_row, dict) else {}

    reasons = []
    if bool(config.get("requireSecondaryConfirm")):
        reasons.append("global")
    if bool(config.get("riskFlagForceSecondaryConfirm")) and int(item.get("riskFlag") or 0) == 1:
        reasons.append("risk_flag")

    applicant_user_name = str(item.get("applicantUserName") or "").strip()
    if bool(config.get("overdueHistoryForceSecondaryConfirm")) and applicant_user_name:
        overdue_rows = query(
            """
            SELECT COUNT(*) AS cnt
            FROM equipment_borrow_request
            WHERE applicant_user_name=%s
              AND (
                  (status='approved' AND returned_at IS NULL AND expected_return_at IS NOT NULL AND expected_return_at < NOW())
                  OR
                  (status='returned' AND returned_at IS NOT NULL AND expected_return_at IS NOT NULL AND returned_at > expected_return_at)
              )
            """,
            (applicant_user_name,),
        )
        overdue_count = int((overdue_rows[0] or {}).get("cnt") or 0) if overdue_rows else 0
        if overdue_count > 0:
            reasons.append("overdue_history")

    lab_name = str(item.get("equipmentLabName") or "").strip().lower()
    for rule_name in config.get("labNames") or []:
        candidate = str(rule_name or "").strip().lower()
        if candidate and candidate == lab_name:
            reasons.append(f"lab:{rule_name}")
            break

    asset_text = " ".join(
        [
            str(item.get("equipmentName") or "").strip(),
            str(item.get("equipmentAssetCode") or "").strip(),
        ]
    ).lower()
    for keyword in config.get("assetKeywords") or []:
        candidate = str(keyword or "").strip().lower()
        if candidate and candidate in asset_text:
            reasons.append(f"asset:{keyword}")
            break

    unique_reasons = []
    seen = set()
    for reason in reasons:
        if reason in seen:
            continue
        seen.add(reason)
        unique_reasons.append(reason)
    return {
        "secondaryConfirmRequired": bool(unique_reasons),
        "secondaryConfirmReasons": unique_reasons,
        "config": config,
    }


def can_review_reservation(actor_role, review_role):
    role = str(actor_role or "").strip().lower()
    required = str(review_role or "").strip().lower()
    if required not in {"teacher", "admin"}:
        required = "admin"
    return role == required


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


def _resolve_lab_for_reservation_plan(lab_id_or_name):
    lab_id_val = _to_int_or_none(lab_id_or_name)
    if lab_id_val and lab_id_val > 0:
        rows = query("SELECT id, name FROM lab WHERE id=%s LIMIT 1", (lab_id_val,))
        if not rows:
            raise BizError("lab not found", 404)
        row = rows[0] or {}
        return {"id": int(row.get("id") or 0), "name": str(row.get("name") or "").strip()}

    name = str(lab_id_or_name or "").strip()
    if not name:
        raise BizError("lab required", 400)
    rows = query("SELECT id, name FROM lab WHERE name=%s LIMIT 1", (name,))
    if rows:
        row = rows[0] or {}
        return {"id": int(row.get("id") or 0), "name": str(row.get("name") or "").strip()}
    try:
        lab = _resolve_lab_from_agent(lab_name=name)
    except Exception:
        raise BizError("lab not found", 404)
    return {"id": int((lab or {}).get("id") or 0), "name": str((lab or {}).get("name") or "").strip()}


def _parse_iso_date_or_none(text):
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except Exception:
        return None


def build_reservation_plans(user_name, lab_id_or_name, preferred_date, preferred_time, days=7, k=3):
    owner = str(user_name or "").strip()
    days_int = max(1, min(int(days or 7), 30))
    k_int = max(1, min(int(k or 3), 20))

    lab = _resolve_lab_for_reservation_plan(lab_id_or_name)
    lab_id = int((lab or {}).get("id") or 0)
    lab_name = str((lab or {}).get("name") or "").strip()
    if lab_id <= 0 or not lab_name:
        raise BizError("lab not found", 404)

    rule_payload = get_reservation_rules_payload(lab_id=lab_id, lab_name=lab_name)
    candidate_slots = _resolve_rule_slots(rule_payload)
    candidate_windows = _build_recommend_time_windows(candidate_slots)
    if not candidate_windows:
        return []

    user_rows = []
    if owner:
        user_rows = query(
            """
            SELECT time
            FROM reservation
            WHERE user_name=%s AND status<>'cancelled'
            """,
            (owner,),
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

    today = datetime.now().date()
    preferred_date_obj = _parse_iso_date_or_none(preferred_date)
    base_date = preferred_date_obj if preferred_date_obj and preferred_date_obj >= today else today
    preferred_slots = parse_slots(preferred_time)

    picked = []
    for offset in range(days_int):
        date_obj = base_date + timedelta(days=offset)
        date_text = date_obj.strftime("%Y-%m-%d")

        for window in candidate_windows:
            time_range = str(window.get("time") or "").strip()
            slot_items = list(window.get("slots") or [])
            if not time_range or not slot_items:
                continue

            schedule_error = validate_reservation_schedule(date_text, time_range, lab_id=lab_id, lab_name=lab_name)
            if schedule_error:
                continue
            if has_approved_conflict(lab_name, date_text, time_range):
                continue

            user_score = (
                sum((float(user_freq.get(s) or 0) / float(user_max)) if user_max > 0 else 0.0 for s in slot_items)
                / float(len(slot_items))
            )
            global_score = (
                sum((float(global_freq.get(s) or 0) / float(global_max)) if global_max > 0 else 0.0 for s in slot_items)
                / float(len(slot_items))
            )
            history_score = 0.7 * user_score + 0.3 * global_score

            overlap_ratio = 0.0
            if preferred_slots:
                set_slots = set(slot_items)
                union_size = len(preferred_slots | set_slots)
                if union_size > 0:
                    overlap_ratio = float(len(preferred_slots & set_slots)) / float(union_size)

            date_pref = 0.0
            if preferred_date_obj:
                date_gap = abs((date_obj - preferred_date_obj).days)
                date_pref = 1.0 / float(1 + date_gap)

            score_raw = 0.55 * history_score + 0.30 * overlap_ratio + 0.15 * date_pref
            reason_parts = ["该时段历史空闲率高且符合规则窗口"]
            if overlap_ratio >= 0.4:
                reason_parts.append("与偏好时段接近")
            if preferred_date_obj and date_pref >= 0.5:
                reason_parts.append("接近期望日期")

            picked.append(
                {
                    "labId": lab_id,
                    "labName": lab_name,
                    "date": date_text,
                    "time": time_range,
                    "scoreRaw": score_raw,
                    "sortStart": int(window.get("firstStart") or 0),
                    "reason": "，".join(reason_parts),
                }
            )

    picked.sort(key=lambda x: (-x["scoreRaw"], x["date"], x["sortStart"], x["time"]))
    plans = []
    for idx, row in enumerate(picked[:k_int], start=1):
        plans.append(
            {
                "planId": f"A{idx}",
                "labId": int(row.get("labId") or 0),
                "labName": str(row.get("labName") or "").strip(),
                "date": str(row.get("date") or "").strip(),
                "time": str(row.get("time") or "").strip(),
                "score": round(float(row.get("scoreRaw") or 0.0), 4),
                "reason": str(row.get("reason") or "").strip(),
            }
        )
    return plans


def get_reservation_rules_payload(lab_id=None, lab_name=""):
    config_payload = get_reservation_rule_config(force_refresh=False)
    scope, applied_lab_rule = _pick_lab_rule_scope(config_payload, lab_id=lab_id, lab_name=lab_name)

    min_days = max(0, int(scope.get("minDaysAhead") or 0))
    max_days = max(min_days, int(scope.get("maxDaysAhead") or min_days))
    min_time = _normalize_rule_clock(scope.get("minTime"), RESERVATION_MIN_TIME)
    max_time = _normalize_rule_clock(scope.get("maxTime"), RESERVATION_MAX_TIME)
    slots = _normalize_rule_slots(scope.get("slots"), min_time, max_time, DEFAULT_RESERVATION_SLOTS)
    disabled_dates = _normalize_rule_date_list(scope.get("disabledDates"))
    blackout_slots = _normalize_rule_blackout_slots(scope.get("blackoutSlots"), slots)
    approval = _normalize_rule_approval(scope.get("approval"), slots)

    today = datetime.now().date()
    min_date = (today + timedelta(days=min_days)).strftime("%Y-%m-%d")
    max_date = (today + timedelta(days=max_days)).strftime("%Y-%m-%d")
    payload = {
        "minDaysAhead": min_days,
        "maxDaysAhead": max_days,
        "minTime": min_time,
        "maxTime": max_time,
        "minDate": min_date,
        "maxDate": max_date,
        "slots": slots,
        "periodSlots": PERIOD_SLOT_ITEMS,
        "disabledDates": disabled_dates,
        "holidays": list(disabled_dates),
        "blackoutSlots": blackout_slots,
        "approval": approval,
    }
    if isinstance(applied_lab_rule, dict):
        payload["labRuleApplied"] = {
            "labId": int(_to_int_or_none(applied_lab_rule.get("labId")) or 0),
            "labName": str(applied_lab_rule.get("labName") or "").strip(),
            "enabled": bool(applied_lab_rule.get("enabled", True)),
        }
    else:
        payload["labRuleApplied"] = None
    return payload


def get_reservation_rules_admin_payload():
    config_payload = get_reservation_rule_config(force_refresh=False)
    try:
        labs = query("SELECT id, name FROM lab ORDER BY id ASC")
    except Exception:
        labs = []
    lab_options = []
    for row in labs or []:
        lid = _to_int_or_none((row or {}).get("id"))
        if lid is None or int(lid) <= 0:
            continue
        lab_options.append(
            {
                "labId": int(lid),
                "labName": str((row or {}).get("name") or "").strip(),
            }
        )
    return {
        "global": _json_clone(config_payload.get("global") if isinstance(config_payload.get("global"), dict) else {}, {}),
        "labRules": _json_clone(config_payload.get("labRules") if isinstance(config_payload.get("labRules"), list) else [], []),
        "borrowApproval": _normalize_borrow_approval_config(config_payload.get("borrowApproval")),
        "labs": lab_options,
    }


def validate_reservation_schedule(date_text, time_range, lab_id=None, lab_name=""):
    date_str = str(date_text or "").strip()
    time_str = str(time_range or "").strip()
    if not date_str or not time_str:
        return "params error"

    date_dt = _parse_date_yyyy_mm_dd(date_str)
    if not date_dt:
        return "invalid date"

    rule_payload = get_reservation_rules_payload(lab_id=lab_id, lab_name=lab_name)
    min_days = max(0, int(rule_payload.get("minDaysAhead") or 0))
    max_days = max(min_days, int(rule_payload.get("maxDaysAhead") or min_days))

    today = datetime.now().date()
    day_delta = (date_dt.date() - today).days
    if day_delta < min_days or day_delta > max_days:
        return f"date out of range ({min_days}-{max_days} days ahead)"

    disabled_dates = set(_normalize_rule_date_list(rule_payload.get("disabledDates")))
    if date_str in disabled_dates:
        return "date disabled by reservation rules"

    allowed_start = _clock_to_minutes(rule_payload.get("minTime"))
    allowed_end = _clock_to_minutes(rule_payload.get("maxTime"))
    if allowed_start is None or allowed_end is None or allowed_end <= allowed_start:
        return "invalid reservation time rule"

    ranges = []
    canonical_slots = []
    for slot in [x.strip() for x in time_str.split(",") if x.strip()]:
        canonical = _canonicalize_slot_text(slot)
        start, end = _slot_to_minutes(canonical)
        if start is None:
            return f"invalid time slot: {slot}"
        if start < allowed_start or end > allowed_end:
            return f"time out of range ({rule_payload.get('minTime')}-{rule_payload.get('maxTime')})"
        ranges.append((start, end))
        canonical_slots.append(canonical)

    if not ranges:
        return "time required"

    allowed_slots = set(_normalize_rule_slots(rule_payload.get("slots"), rule_payload.get("minTime"), rule_payload.get("maxTime"), DEFAULT_RESERVATION_SLOTS))
    if allowed_slots:
        invalid_slots = sorted([x for x in canonical_slots if x not in allowed_slots])
        if invalid_slots:
            return f"time slots not allowed: {','.join(invalid_slots)}"

    ranges.sort(key=lambda x: (x[0], x[1]))
    for i in range(1, len(ranges)):
        prev = ranges[i - 1]
        cur = ranges[i]
        if cur[0] < prev[1]:
            return "time slots overlap"

    incoming_set = set(canonical_slots)
    for item in _normalize_rule_blackout_slots(rule_payload.get("blackoutSlots"), list(allowed_slots)):
        if str(item.get("date") or "") != date_str:
            continue
        blocked = set(item.get("slots") or [])
        if incoming_set & blocked:
            reason = str(item.get("reason") or "").strip()
            return f"time blocked by blacklist slots{f' ({reason})' if reason else ''}"

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


def _normalize_ai_permission_code(value):
    code = str(value or "").strip()
    if code not in AI_PERMISSION_CODE_SET:
        raise BizError("invalid permissionCode", 400)
    return code


def _parse_ai_permission_expire_at(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    candidate = raw.replace("T", " ").strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1]
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        raise BizError("invalid expiresAt", 400)
    if getattr(parsed, "tzinfo", None) is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def normalize_ai_permission_expires_at_text(value):
    parsed = _parse_ai_permission_expire_at(value)
    if parsed is None:
        return ""
    if parsed <= datetime.now():
        raise BizError("expiresAt must be later than now", 400)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def get_ai_permission_status(current_user, permission_code):
    code = _normalize_ai_permission_code(permission_code)
    actor = current_user or {}
    role = str(actor.get("role") or "").strip().lower()
    user_id = _to_int_or_none(actor.get("id"))
    username = str(actor.get("username") or "").strip()

    base = {
        "permissionCode": code,
        "granted": False,
        "source": "none",
        "expiresAt": "",
    }
    if role == "admin":
        base["granted"] = True
        base["source"] = "role_default"
        return base
    if not user_id or not username:
        return base

    rows = query(
        """
        SELECT id,
               permission_code AS permissionCode,
               expires_at AS expiresAt
        FROM ai_user_permission
        WHERE user_id=%s
          AND permission_code=%s
        LIMIT 1
        """,
        (user_id, code),
    )
    if not rows:
        return base

    row = rows[0] or {}
    expires_at_text = _to_text_time(row.get("expiresAt"))
    expires_dt = _to_datetime(row.get("expiresAt"))
    base["expiresAt"] = expires_at_text
    if expires_dt != datetime.min and expires_dt <= datetime.now():
        base["source"] = "expired"
        return base

    base["granted"] = True
    base["source"] = "user_grant"
    return base


def has_ai_permission(current_user, permission_code):
    return bool(get_ai_permission_status(current_user, permission_code).get("granted"))


def list_user_ai_permission_statuses(target_user):
    actor = target_user or {}
    items = []
    for code in sorted(AI_PERMISSION_CODE_SET):
        items.append(get_ai_permission_status(actor, code))
    return items


def _normalize_general_permission_code(value):
    code = str(value or "").strip()
    if code not in GENERAL_PERMISSION_CODE_SET:
        raise BizError("invalid permissionCode", 400)
    return code


def get_user_permission_status(current_user, permission_code):
    code = _normalize_general_permission_code(permission_code)
    actor = current_user or {}
    role = str(actor.get("role") or "").strip().lower()
    user_id = _to_int_or_none(actor.get("id"))
    username = str(actor.get("username") or "").strip()

    base = {
        "permissionCode": code,
        "granted": False,
        "source": "none",
        "expiresAt": "",
    }
    if role == "admin":
        base["granted"] = True
        base["source"] = "role_default"
        return base
    if not user_id or not username:
        return base

    rows = query(
        """
        SELECT permission_code AS permissionCode, expires_at AS expiresAt
        FROM user_permission
        WHERE user_id=%s
          AND permission_code=%s
        LIMIT 1
        """,
        (user_id, code),
    )
    if not rows:
        return base

    row = rows[0] or {}
    base["expiresAt"] = _to_text_time(row.get("expiresAt"))
    expires_dt = _to_datetime(row.get("expiresAt"))
    if expires_dt != datetime.min and expires_dt <= datetime.now():
        base["source"] = "expired"
        return base

    base["granted"] = True
    base["source"] = "user_grant"
    return base


def has_user_permission(current_user, permission_code):
    return bool(get_user_permission_status(current_user, permission_code).get("granted"))


def list_user_permission_statuses(target_user):
    actor = target_user or {}
    items = []
    for code in sorted(GENERAL_PERMISSION_CODE_SET):
        items.append(get_user_permission_status(actor, code))
    return items


def list_effective_user_permissions(current_user):
    actor = current_user or {}
    items = []
    for code in sorted(GENERAL_PERMISSION_CODE_SET):
        if has_user_permission(actor, code):
            items.append(code)
    return items


def _normalize_notification_type(value):
    notice_type = str(value or "").strip()
    if notice_type not in NOTIFICATION_TYPE_SET:
        raise BizError("invalid notification type", 400)
    return notice_type


def _normalize_notification_last_read_at(value):
    text = str(value or "").strip()
    if not text:
        raise BizError("lastReadAt required", 400)
    dt = _to_datetime(text)
    if dt == datetime.min:
        raise BizError("invalid lastReadAt", 400)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_notification_read_state(user_name):
    user = str(user_name or "").strip()
    state = {k: "" for k in NOTIFICATION_TYPE_ITEMS}
    if not user:
        return state

    rows = query(
        """
        SELECT notice_type AS noticeType, last_read_at AS lastReadAt
        FROM notification_read_state
        WHERE user_name=%s
        """,
        (user,),
    )
    for row in rows or []:
        notice_type = str((row or {}).get("noticeType") or "").strip()
        if notice_type not in state:
            continue
        state[notice_type] = _to_text_time((row or {}).get("lastReadAt"))
    return state


def update_notification_read_state(user_name, read_state_patch):
    user = str(user_name or "").strip()
    if not user:
        raise BizError("user required", 400)
    if not isinstance(read_state_patch, dict):
        raise BizError("readState required", 400)

    normalized_items = []
    for raw_type, raw_time in (read_state_patch or {}).items():
        notice_type = _normalize_notification_type(raw_type)
        last_read_at = _normalize_notification_last_read_at(raw_time)
        normalized_items.append((notice_type, last_read_at))

    if not normalized_items:
        raise BizError("readState required", 400)

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _tx(cur):
        for notice_type, last_read_at in normalized_items:
            cur.execute(
                """
                INSERT INTO notification_read_state (user_name, notice_type, last_read_at, updated_at)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    last_read_at=GREATEST(last_read_at, VALUES(last_read_at)),
                    updated_at=VALUES(updated_at)
                """,
                (user, notice_type, last_read_at, now_text),
            )

    run_in_transaction(_tx)
    return get_notification_read_state(user)


def save_agent_chat_message(user_name, role, content, action="", meta=None):
    user = str(user_name or "").strip()
    role_text = str(role or "").strip().lower()
    text = str(content or "").strip()
    if not user or role_text not in {"user", "assistant"} or not text:
        return 0
    action_text = str(action or "").strip()[:64]
    meta_json = ""
    if isinstance(meta, dict):
        try:
            meta_json = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            meta_json = ""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return int(
        execute_insert(
            """
            INSERT INTO agent_chat_message (user_name, role, content, action, meta_json, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user, role_text, text, action_text, meta_json, created_at),
        )
        or 0
    )


def list_agent_chat_messages(user_name, limit=100):
    user = str(user_name or "").strip()
    if not user:
        return []
    n = max(1, min(int(_to_int_or_none(limit) or 100), 200))
    rows = query(
        """
        SELECT id, role, content, action, meta_json AS metaJson, created_at AS createdAt
        FROM agent_chat_message
        WHERE user_name=%s
        ORDER BY id DESC
        LIMIT %s
        """,
        (user, n),
    )
    data = []
    for row in reversed(rows or []):
        meta_obj = {}
        raw_meta = str((row or {}).get("metaJson") or "").strip()
        if raw_meta:
            try:
                parsed = json.loads(raw_meta)
                if isinstance(parsed, dict):
                    meta_obj = parsed
            except Exception:
                meta_obj = {}
        data.append(
            {
                "id": int((row or {}).get("id") or 0),
                "role": str((row or {}).get("role") or "").strip(),
                "text": str((row or {}).get("content") or ""),
                "action": str((row or {}).get("action") or "").strip(),
                "meta": meta_obj,
                "createdAt": _to_text_time((row or {}).get("createdAt")),
            }
        )
    return data


def clear_agent_chat_messages(user_name):
    user = str(user_name or "").strip()
    if not user:
        return 0
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM agent_chat_message WHERE user_name=%s", (user,))
            affected = int(cur.rowcount or 0)
        conn.commit()
        return affected
    finally:
        conn.close()


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


def _extract_time_from_text(text):
    raw = str(text or "")
    if not raw:
        return ""

    slots = []
    seen = set()

    period_text = _extract_time_from_period_expression(raw)
    for part in str(period_text or "").split(","):
        canonical = _canonicalize_slot_text(part)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        slots.append(canonical)

    for m in re.finditer(r"([0-2]?\d\s*:\s*[0-5]\d)\s*-\s*([0-2]?\d\s*:\s*[0-5]\d)", raw):
        start = re.sub(r"\s+", "", str(m.group(1) or ""))
        end = re.sub(r"\s+", "", str(m.group(2) or ""))
        canonical = _canonicalize_slot_text(f"{start}-{end}")
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        slots.append(canonical)

    return ",".join(slots)


def _extract_reservation_reason_from_text(text):
    raw = str(text or "").strip()
    if not raw:
        return ""
    normalized = re.sub(r"\s+", " ", raw.replace("：", ":")).strip()
    patterns = [
        r"(?:用途|原因|事由)\s*[:：]?\s*([^\n]{1,120})$",
        r"(?:用于|用来)\s*([^\n]{1,120})$",
    ]
    for pat in patterns:
        m = re.search(pat, normalized, flags=re.IGNORECASE)
        if not m:
            continue
        reason = str(m.group(1) or "").strip()
        reason = re.sub(r"[，。,.!?！？]+$", "", reason)
        if reason:
            return reason[:120]
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


def _extract_equipment_hint_from_text(text):
    raw = str(text or "").strip()
    if not raw:
        return ""

    m = re.search(r"(?<![A-Za-z0-9])(PC-[A-Za-z]{1,3}\s*\d{1,3})(?![A-Za-z0-9])", raw, flags=re.IGNORECASE)
    if m:
        return re.sub(r"\s+", "", str(m.group(1) or "")).upper()

    m = re.search(r"(?:设备|机位|座位|电脑|主机)\s*([A-Za-z]{1,3}\s*\d{1,3})", raw, flags=re.IGNORECASE)
    if m:
        seat = re.sub(r"\s+", "", str(m.group(1) or "")).upper()
        if seat:
            return seat

    m = re.search(r"(?<![A-Za-z0-9])([A-Za-z]{1,3}\s*\d{1,3})(?![A-Za-z0-9])", raw, flags=re.IGNORECASE)
    if m and len(raw) <= 24:
        seat = re.sub(r"\s+", "", str(m.group(1) or "")).upper()
        if seat:
            return seat
    return ""


def _extract_repair_issue_type_from_text(text):
    raw = str(text or "").strip().lower()
    if not raw:
        return "other"
    if any(k in raw for k in ("电脑", "主机", "显示器", "键盘", "鼠标", "开不了机", "蓝屏", "死机", "pc")):
        return "computer"
    if any(k in raw for k in ("照明", "灯", "灯管", "灯泡", "灯光")):
        return "lighting"
    if any(k in raw for k in ("地板", "地面", "地砖", "地胶", "桌椅")):
        return "floor"
    if any(k in raw for k in ("网络", "wifi", "网速", "断网", "上不了网", "无法联网", "连不上网")):
        return "network"
    return "other"


def _extract_repair_description_from_text(text):
    raw = str(text or "").strip()
    if not raw:
        return ""

    normalized = re.sub(r"\s+", " ", raw.replace("：", ":")).strip()
    patterns = [
        r"(?:报修|维修|工单)\s*[:：]?\s*(.+)$",
        r"(?:问题是|情况是|故障是)\s*[:：]?\s*(.+)$",
        r"(?:帮我|请|麻烦)?(?:提交|发起|创建|申请)?(?:一下)?(?:报修|维修)\s*(.+)$",
    ]
    for pat in patterns:
        m = re.search(pat, normalized, flags=re.IGNORECASE)
        if not m:
            continue
        detail = str(m.group(1) or "").strip()
        detail = re.sub(r"^[，。,.；;:：\s]+", "", detail)
        if detail:
            return detail[:500]

    if len(normalized) <= 10 and any(
        x in normalized for x in ("报修", "维修", "工单", "处理一下", "帮我修", "修一下", "故障")
    ):
        generic = re.sub(r"(报修|维修|工单|处理一下|帮我修|修一下|故障|请|帮我|麻烦|提交|发起|创建|申请)", "", normalized)
        if not generic.strip():
            return ""

    return normalized[:500]


def _is_repair_create_request(text):
    raw = str(text or "").strip().lower()
    if not raw:
        return False
    if any(
        x in raw
        for x in (
            "我的报修",
            "报修进度",
            "报修状态",
            "报修列表",
            "工单列表",
            "工单进度",
            "查看报修",
            "查询报修",
            "维修进度",
            "维修状态",
        )
    ):
        return False
    strong = ("报修", "维修", "工单")
    if any(x in raw for x in strong):
        return True
    return any(x in raw for x in ("坏了", "故障", "异常", "无法开机", "连不上网", "断网", "蓝屏", "死机"))


def _is_repair_advice_query(text):
    raw = str(text or "").strip().lower()
    if not raw:
        return False
    has_repair = any(x in raw for x in ("报修", "维修", "工单"))
    has_advice = any(x in raw for x in ("建议", "优先级", "先处理", "先做", "待办", "处理策略"))
    return has_repair and has_advice


def _is_alarm_advice_query(text):
    raw = str(text or "").strip().lower()
    if not raw:
        return False
    has_alarm = any(x in raw for x in ("报警", "告警", "安全", "联动", "烟雾", "电压", "温度"))
    has_advice = any(x in raw for x in ("建议", "怎么处理", "怎么做", "处置", "预案", "优先级", "待办"))
    return has_alarm and has_advice


def _is_my_repair_orders_query(text):
    raw = str(text or "").strip().lower()
    if not raw:
        return False
    direct = (
        "我的报修",
        "报修记录",
        "报修列表",
        "报修进度",
        "报修状态",
        "工单状态",
        "工单进度",
        "工单列表",
        "查看报修",
        "查询报修",
    )
    if any(x in raw for x in direct):
        return True
    has_repair_word = any(x in raw for x in ("报修", "维修", "工单"))
    has_query_word = any(x in raw for x in ("查看", "查询", "多少", "几条", "记录", "列表", "状态", "进度", "目前", "当前"))
    has_self_word = any(x in raw for x in ("我", "我的", "本人"))
    return has_repair_word and has_query_word and has_self_word


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


def _is_progress_summary_query(text):
    raw = str(text or "").strip().lower()
    if not raw:
        return False
    direct = (
        "查进度",
        "看进度",
        "查看进度",
        "查询进度",
        "我的进度",
        "最近进展",
        "进展怎么样",
        "现在怎么样了",
    )
    if any(x in raw for x in direct):
        return True
    has_progress = any(x in raw for x in ("进度", "进展", "状态", "处理到哪", "到哪了"))
    has_query = any(x in raw for x in ("查", "看", "问", "最近", "现在", "目前", "当前"))
    return has_progress and has_query


def _repair_status_label(status):
    raw = str(status or "").strip()
    mapping = {
        "submitted": "已提交",
        "accepted": "已受理",
        "processing": "处理中",
        "completed": "已完成",
    }
    return mapping.get(raw, raw or "未知状态")


def _repair_issue_label(issue_type):
    raw = str(issue_type or "").strip()
    mapping = {
        "computer": "电脑",
        "lighting": "照明",
        "floor": "地面",
        "network": "网络",
        "other": "其他",
    }
    return mapping.get(raw, raw or "其他")


def _agent_handle_my_repair_orders_query(user_name, role="", limit=5):
    owner = str(user_name or "").strip()
    if not owner:
        return _agent_response(code=401, msg="unauthorized", reply="登录状态失效，请重新登录。", action="error", http_status=401)

    total_rows = query("SELECT COUNT(*) AS cnt FROM repair_work_order WHERE submitter_name=%s", (owner,))
    total = int((total_rows[0] or {}).get("cnt") or 0) if total_rows else 0
    if total <= 0:
        return _agent_response(code=0, msg="ok", reply="你目前还没有报修工单。", action="repair_list", http_status=200)

    status_rows = query(
        """
        SELECT status, COUNT(*) AS cnt
        FROM repair_work_order
        WHERE submitter_name=%s
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

    ordered_status = ["submitted", "accepted", "processing", "completed"]
    status_parts = []
    for key in ordered_status:
        cnt = int(status_counter.get(key) or 0)
        if cnt > 0:
            status_parts.append(f"{_repair_status_label(key)}{cnt}条")
    for key, cnt in status_counter.items():
        if key in ordered_status:
            continue
        n = int(cnt or 0)
        if n > 0:
            status_parts.append(f"{key}{n}条")
    status_text = "，".join(status_parts) if status_parts else "暂无状态统计"

    rows = query(
        """
        SELECT id,
               order_no AS orderNo,
               lab_name AS labName,
               equipment_name AS equipmentName,
               asset_code AS assetCode,
               issue_type AS issueType,
               status,
               updated_at AS updatedAt
        FROM repair_work_order
        WHERE submitter_name=%s
        ORDER BY updated_at DESC, id DESC
        LIMIT %s
        """,
        (owner, max(1, int(limit))),
    )
    lines = []
    for idx, row in enumerate(rows, start=1):
        order_no = str((row or {}).get("orderNo") or "").strip() or f"#{int((row or {}).get('id') or 0)}"
        issue_label = _repair_issue_label((row or {}).get("issueType"))
        status_label = _repair_status_label((row or {}).get("status"))
        lab_name = str((row or {}).get("labName") or "").strip()
        equipment_name = str((row or {}).get("equipmentName") or "").strip() or str((row or {}).get("assetCode") or "").strip()
        target_text = equipment_name or lab_name or "未指定设备"
        updated_at = _to_text_time((row or {}).get("updatedAt"))
        lines.append(f"{idx}. {order_no} {issue_label} {target_text}（{status_label}，更新时间 {updated_at}）")

    detail = "\n".join(lines)
    role_note = "（管理员账号仅显示你本人提交的工单）" if str(role or "").strip() == "admin" else ""
    reply = f"你目前共有{total}条报修工单。状态分布：{status_text}。{role_note}\n最近{len(lines)}条如下：\n{detail}"
    return _agent_response(code=0, msg="ok", reply=reply, action="repair_list", http_status=200)


def _agent_handle_progress_summary(user_name, role="", reservation_limit=3, repair_limit=3):
    owner = str(user_name or "").strip()
    if not owner:
        return _agent_response(code=401, msg="unauthorized", reply="登录状态失效，请重新登录。", action="error", http_status=401)

    reservation_total_rows = query("SELECT COUNT(*) AS cnt FROM reservation WHERE user_name=%s", (owner,))
    reservation_total = int((reservation_total_rows[0] or {}).get("cnt") or 0) if reservation_total_rows else 0
    reservation_status_rows = query(
        """
        SELECT status, COUNT(*) AS cnt
        FROM reservation
        WHERE user_name=%s
        GROUP BY status
        """,
        (owner,),
    )
    reservation_status = {}
    for row in reservation_status_rows:
        status = str((row or {}).get("status") or "").strip()
        if status:
            reservation_status[status] = int((row or {}).get("cnt") or 0)
    reservation_rows = query(
        """
        SELECT id, lab_name AS labName, date, time, status
        FROM reservation
        WHERE user_name=%s
        ORDER BY date DESC, id DESC
        LIMIT %s
        """,
        (owner, max(1, int(reservation_limit))),
    )

    repair_total_rows = query("SELECT COUNT(*) AS cnt FROM repair_work_order WHERE submitter_name=%s", (owner,))
    repair_total = int((repair_total_rows[0] or {}).get("cnt") or 0) if repair_total_rows else 0
    repair_status_rows = query(
        """
        SELECT status, COUNT(*) AS cnt
        FROM repair_work_order
        WHERE submitter_name=%s
        GROUP BY status
        """,
        (owner,),
    )
    repair_status = {}
    for row in repair_status_rows:
        status = str((row or {}).get("status") or "").strip()
        if status:
            repair_status[status] = int((row or {}).get("cnt") or 0)
    repair_rows = query(
        """
        SELECT id,
               order_no AS orderNo,
               lab_name AS labName,
               equipment_name AS equipmentName,
               asset_code AS assetCode,
               status,
               updated_at AS updatedAt
        FROM repair_work_order
        WHERE submitter_name=%s
        ORDER BY updated_at DESC, id DESC
        LIMIT %s
        """,
        (owner, max(1, int(repair_limit))),
    )

    if reservation_total <= 0 and repair_total <= 0:
        return _agent_response(
            code=0,
            msg="ok",
            reply="你目前还没有预约或报修记录。需要的话，我可以直接帮你预约实验室或提交报修。",
            action="progress_summary",
            http_status=200,
        )

    reply_parts = []
    if reservation_total > 0:
        ordered_status = ["pending", "approved", "rejected", "cancelled"]
        status_parts = [
            f"{_reservation_status_label(key)}{int(reservation_status.get(key) or 0)}条"
            for key in ordered_status
            if int(reservation_status.get(key) or 0) > 0
        ]
        recent_lines = []
        for idx, row in enumerate(reservation_rows, start=1):
            recent_lines.append(
                f"{idx}. #{int((row or {}).get('id') or 0)} {str((row or {}).get('labName') or '').strip()} "
                f"{str((row or {}).get('date') or '').strip()} {str((row or {}).get('time') or '').strip()}（{_reservation_status_label((row or {}).get('status'))}）"
            )
        section = f"预约：共{reservation_total}条"
        if status_parts:
            section += f"，状态分布：{'，'.join(status_parts)}"
        if recent_lines:
            section += "。\n最近预约：\n" + "\n".join(recent_lines)
        reply_parts.append(section)

    if repair_total > 0:
        ordered_status = ["submitted", "accepted", "processing", "completed"]
        status_parts = [
            f"{_repair_status_label(key)}{int(repair_status.get(key) or 0)}条"
            for key in ordered_status
            if int(repair_status.get(key) or 0) > 0
        ]
        recent_lines = []
        for idx, row in enumerate(repair_rows, start=1):
            order_no = str((row or {}).get("orderNo") or "").strip() or f"#{int((row or {}).get('id') or 0)}"
            target_text = (
                str((row or {}).get("equipmentName") or "").strip()
                or str((row or {}).get("assetCode") or "").strip()
                or str((row or {}).get("labName") or "").strip()
                or "未指定位置"
            )
            recent_lines.append(
                f"{idx}. {order_no} {target_text}（{_repair_status_label((row or {}).get('status'))}，更新时间 {_to_text_time((row or {}).get('updatedAt'))}）"
            )
        section = f"报修：共{repair_total}条"
        if status_parts:
            section += f"，状态分布：{'，'.join(status_parts)}"
        if recent_lines:
            section += "。\n最近工单：\n" + "\n".join(recent_lines)
        reply_parts.append(section)

    reply = "\n\n".join(reply_parts) + "\n\n如果你要继续操作，可以直接说“取消 #12 预约”“把 #12 改到明天 3-4节”或“查看预约规则”。"
    return _agent_response(code=0, msg="ok", reply=reply, action="progress_summary", http_status=200)


def _normalize_agent_seat_code(value):
    text = re.sub(r"\s+", "", str(value or "").strip().upper())
    if not text:
        return ""
    m = re.fullmatch(r"([A-Z]{1,3})(\d{1,3})", text)
    if not m:
        return ""
    return f"{m.group(1)}{int(m.group(2))}"


def _resolve_equipment_from_agent_hint(equipment_hint):
    hint = str(equipment_hint or "").strip()
    if not hint:
        return None

    hint_id = _to_int_or_none(hint)
    if hint_id and int(hint_id) > 0:
        by_id = query(
            """
            SELECT id, asset_code AS assetCode, name, lab_id AS labId, lab_name AS labName
            FROM equipment
            WHERE id=%s
            LIMIT 1
            """,
            (int(hint_id),),
        )
        if by_id:
            return by_id[0]

    normalized = re.sub(r"\s+", "", hint).upper()
    seat_candidate = normalized
    if normalized.startswith("PC-"):
        seat_candidate = normalized[3:]
    seat_code = _normalize_agent_seat_code(seat_candidate)

    exact_codes = []
    if normalized:
        exact_codes.append(normalized)
    if seat_code:
        exact_codes.append(seat_code)
        exact_codes.append(f"PC-{seat_code}")

    seen = set()
    dedup_codes = []
    for code in exact_codes:
        k = str(code or "").strip().upper()
        if not k or k in seen:
            continue
        seen.add(k)
        dedup_codes.append(k)

    where_parts = []
    params = []
    for code in dedup_codes:
        where_parts.append("asset_code=%s")
        params.append(code)
    for code in dedup_codes[:2]:
        where_parts.append("name=%s")
        params.append(code)
    if seat_code:
        where_parts.append("spec_json LIKE %s")
        params.append(f"%{seat_code}%")

    if not where_parts:
        return None

    rows = query(
        """
        SELECT id, asset_code AS assetCode, name, lab_id AS labId, lab_name AS labName
        FROM equipment
        WHERE """
        + " OR ".join(where_parts)
        + """
        ORDER BY id DESC
        LIMIT 6
        """,
        tuple(params),
    )
    if not rows:
        return None

    exact = [r for r in rows if str((r or {}).get("assetCode") or "").strip().upper() in set(dedup_codes)]
    candidate_rows = exact if exact else rows
    if len(candidate_rows) == 1:
        return candidate_rows[0]

    options = [str((x or {}).get("assetCode") or "").strip() for x in candidate_rows if str((x or {}).get("assetCode") or "").strip()]
    option_text = "、".join(options[:5]) if options else "多个候选设备"
    raise BizError(f"equipment ambiguous, candidates: {option_text}", 400)


def _build_agent_repair_order_no():
    return f"WO{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"


def _agent_handle_repair_create(user_name, role, issue_type, description, lab_name="", equipment_hint=""):
    owner = str(user_name or "").strip()
    if not owner:
        return _agent_response(code=401, msg="unauthorized", reply="登录状态失效，请重新登录。", action="error", http_status=401)

    issue_raw = str(issue_type or "").strip().lower()
    issue = AGENT_REPAIR_ISSUE_ALIAS.get(issue_raw, issue_raw)
    if issue not in AGENT_REPAIR_ISSUE_SET:
        issue = _extract_repair_issue_type_from_text(description)
    if issue not in AGENT_REPAIR_ISSUE_SET:
        issue = "other"

    desc = _extract_repair_description_from_text(description)
    if not desc:
        _agent_pending_set(
            owner,
            "repair_create",
            extra={
                "issueType": issue,
                "labName": str(lab_name or "").strip(),
                "equipmentHint": str(equipment_hint or "").strip(),
            },
        )
        reply = "请补充故障描述，例如：C406 的 PC-A1 蓝屏无法开机。"
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    submitter_rows = query("SELECT id FROM user WHERE username=%s LIMIT 1", (owner,))
    submitter_id = int((submitter_rows[0] or {}).get("id") or 0) if submitter_rows else 0
    if submitter_id <= 0:
        return _agent_response(code=401, msg="unauthorized", reply="当前账号异常，请重新登录后重试。", action="error", http_status=401)

    equipment = None
    equipment_hint_text = str(equipment_hint or "").strip()
    if equipment_hint_text:
        try:
            equipment = _resolve_equipment_from_agent_hint(equipment_hint_text)
        except BizError as e:
            _agent_pending_set(
                owner,
                "repair_create",
                extra={
                    "issueType": issue,
                    "description": desc,
                    "labName": str(lab_name or "").strip(),
                    "equipmentHint": equipment_hint_text,
                },
            )
            return _agent_response(code=e.status, msg=e.msg, reply=f"设备信息有歧义：{e.msg}。请补充更准确的设备编号。", action="ask_info", http_status=e.status)
        if not equipment:
            _agent_pending_set(
                owner,
                "repair_create",
                extra={
                    "issueType": issue,
                    "description": desc,
                    "labName": str(lab_name or "").strip(),
                    "equipmentHint": equipment_hint_text,
                },
            )
            return _agent_response(
                code=0,
                msg="ok",
                reply=f"没有找到设备“{equipment_hint_text}”。请补充正确的设备编号（例如 PC-A1）或实验室名称。",
                action="ask_info",
                http_status=200,
            )

    resolved_lab_id = None
    resolved_lab_name = ""
    equipment_id = None
    asset_code = ""
    equipment_name = ""
    if equipment:
        equipment_id = int((equipment or {}).get("id") or 0)
        asset_code = str((equipment or {}).get("assetCode") or "").strip()
        equipment_name = str((equipment or {}).get("name") or "").strip()
        resolved_lab_id = _to_int_or_none((equipment or {}).get("labId"))
        resolved_lab_name = str((equipment or {}).get("labName") or "").strip()
    else:
        lab_text = str(lab_name or "").strip()
        if not lab_text:
            _agent_pending_set(
                owner,
                "repair_create",
                extra={
                    "issueType": issue,
                    "description": desc,
                    "equipmentHint": equipment_hint_text,
                },
            )
            return _agent_response(
                code=0,
                msg="ok",
                reply="请补充报修位置：实验室名称或设备编号（例如 C406 或 PC-A1）。",
                action="ask_info",
                http_status=200,
            )
        try:
            lab = _resolve_lab_from_agent(lab_name=lab_text)
        except BizError as e:
            _agent_pending_set(
                owner,
                "repair_create",
                extra={
                    "issueType": issue,
                    "description": desc,
                    "labName": lab_text,
                    "equipmentHint": equipment_hint_text,
                },
            )
            return _agent_response(code=e.status, msg=e.msg, reply=f"实验室信息有问题：{e.msg}", action="ask_info", http_status=e.status)
        resolved_lab_id = _to_int_or_none((lab or {}).get("id"))
        resolved_lab_name = str((lab or {}).get("name") or "").strip()

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        new_id = execute_insert(
            """
            INSERT INTO repair_work_order (
                order_no, equipment_id, asset_code, equipment_name, lab_id, lab_name,
                issue_type, description, attachment_url, status,
                submitter_id, submitter_name, assignee_id, assignee_name,
                submitted_at, accepted_at, processing_at, completed_at,
                followup_score, followup_comment, followup_at, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, 'submitted',
                %s, %s, NULL, '',
                %s, NULL, NULL, NULL,
                NULL, '', NULL, %s, %s
            )
            """,
            (
                _build_agent_repair_order_no(),
                equipment_id,
                asset_code,
                equipment_name,
                resolved_lab_id,
                resolved_lab_name,
                issue,
                desc[:1000],
                "",
                submitter_id,
                owner,
                now_text,
                now_text,
                now_text,
            ),
        )
    except Exception:
        return _agent_response(code=500, msg="repair create failed", reply="创建报修失败，请稍后重试。", action="error", http_status=500)

    order_rows = query(
        """
        SELECT id,
               order_no AS orderNo,
               status,
               issue_type AS issueType,
               lab_name AS labName,
               equipment_name AS equipmentName,
               asset_code AS assetCode
        FROM repair_work_order
        WHERE id=%s
        LIMIT 1
        """,
        (new_id,),
    )
    order = (order_rows[0] or {}) if order_rows else {"id": int(new_id), "status": "submitted"}

    _agent_pending_clear(owner)
    audit_log(
        "agent.chat.repair.create",
        target_type="repair_work_order",
        target_id=int(new_id or 0),
        detail={
            "issueType": issue,
            "labName": resolved_lab_name,
            "equipmentId": equipment_id,
            "assetCode": asset_code,
        },
        actor={"id": submitter_id, "username": owner, "role": role},
    )

    target_text = str(order.get("assetCode") or "").strip() or str(order.get("equipmentName") or "").strip() or str(order.get("labName") or "").strip()
    reply = (
        f"已为你创建报修工单：{str(order.get('orderNo') or f'#{int(order.get('id') or 0)}')}。"
        f"问题类型：{_repair_issue_label(order.get('issueType'))}；位置：{target_text or '未指定'}；状态：{_repair_status_label(order.get('status'))}。"
    )
    return _agent_response(
        code=0,
        msg="ok",
        reply=reply,
        action="repair_created",
        extra={
            "repairOrder": {
                "id": int(order.get("id") or 0),
                "orderNo": str(order.get("orderNo") or ""),
                "status": str(order.get("status") or ""),
                "issueType": str(order.get("issueType") or ""),
                "labName": str(order.get("labName") or ""),
                "equipmentName": str(order.get("equipmentName") or ""),
                "assetCode": str(order.get("assetCode") or ""),
            }
        },
        http_status=200,
    )


def _minutes_since(value):
    dt = _to_datetime(value)
    if dt == datetime.min:
        return None
    diff = int((datetime.now() - dt).total_seconds() // 60)
    return max(diff, 0)


def _agent_handle_repair_advice(user_name, role, limit=8):
    owner = str(user_name or "").strip()
    if not owner:
        return _agent_response(code=401, msg="unauthorized", reply="登录状态失效，请重新登录。", action="error", http_status=401)
    if str(role or "").strip() != "admin":
        return _agent_response(
            code=0,
            msg="ok",
            reply="报修调度建议仅管理员可用。你可以说“我的报修进度”查看个人工单状态。",
            action="repair_advice",
            http_status=200,
        )

    rows = query(
        """
        SELECT id,
               order_no AS orderNo,
               status,
               lab_name AS labName,
               equipment_name AS equipmentName,
               asset_code AS assetCode,
               issue_type AS issueType,
               submitted_at AS submittedAt,
               accepted_at AS acceptedAt,
               processing_at AS processingAt
        FROM repair_work_order
        WHERE status IN ('submitted','accepted','processing')
        ORDER BY submitted_at ASC, id ASC
        LIMIT 200
        """
    )
    if not rows:
        return _agent_response(code=0, msg="ok", reply="当前没有待处理的报修工单。", action="repair_advice", http_status=200)

    status_counter = {"submitted": 0, "accepted": 0, "processing": 0}
    candidates = []
    for row in rows:
        status = str((row or {}).get("status") or "").strip()
        if status in status_counter:
            status_counter[status] += 1

        submitted_mins = _minutes_since((row or {}).get("submittedAt"))
        accepted_mins = _minutes_since((row or {}).get("acceptedAt"))
        processing_mins = _minutes_since((row or {}).get("processingAt"))

        if status == "submitted":
            wait_mins = submitted_mins if submitted_mins is not None else 0
            level = "高" if wait_mins >= 120 else "中"
            advice = "建议立即受理并分配处理人。"
        elif status == "accepted":
            wait_mins = accepted_mins if accepted_mins is not None else (submitted_mins if submitted_mins is not None else 0)
            level = "高" if wait_mins >= 180 else "中"
            advice = "建议尽快转为处理中并安排现场排查。"
        else:
            wait_mins = processing_mins if processing_mins is not None else (accepted_mins if accepted_mins is not None else 0)
            level = "高" if wait_mins >= 360 else "中"
            advice = "建议同步当前进展并给出预计完成时间。"

        candidates.append(
            {
                "id": int((row or {}).get("id") or 0),
                "orderNo": str((row or {}).get("orderNo") or "").strip(),
                "status": status,
                "labName": str((row or {}).get("labName") or "").strip(),
                "target": str((row or {}).get("assetCode") or "").strip()
                or str((row or {}).get("equipmentName") or "").strip()
                or str((row or {}).get("labName") or "").strip()
                or "未指定设备",
                "waitMins": int(wait_mins or 0),
                "priority": 2 if level == "高" else 1,
                "levelText": level,
                "issueType": _repair_issue_label((row or {}).get("issueType")),
                "advice": advice,
            }
        )

    candidates.sort(key=lambda x: (-int(x.get("priority") or 0), -int(x.get("waitMins") or 0), int(x.get("id") or 0)))
    top = candidates[: max(1, min(int(_to_int_or_none(limit) or 8), 20))]

    lines = []
    for idx, item in enumerate(top, start=1):
        order_no = str(item.get("orderNo") or "").strip() or f"#{int(item.get('id') or 0)}"
        lines.append(
            f"{idx}. {order_no} {item.get('issueType')} {item.get('target')}（{_repair_status_label(item.get('status'))}，"
            f"等待约{int(item.get('waitMins') or 0)}分钟，优先级{item.get('levelText')}）{item.get('advice')}"
        )

    reply = (
        "报修调度建议如下："
        f"\n当前待处理工单：已提交{status_counter['submitted']}条，已受理{status_counter['accepted']}条，处理中{status_counter['processing']}条。"
        "\n优先建议：\n"
        + "\n".join(lines)
    )
    return _agent_response(code=0, msg="ok", reply=reply, action="repair_advice", http_status=200)


def _alarm_advice_for_code(alarm_code):
    code = str(alarm_code or "").strip()
    if code == "smoke_detected":
        return "立即现场核查并排除火情风险，必要时切断电源并按应急预案报警。"
    if code == "temp_high":
        return "先确认空调与通风状态，持续超温时安排人员离场并检查发热点设备。"
    if code == "voltage_fault":
        return "立即检查配电与UPS，暂停高负载设备，确认电压恢复稳定后再恢复使用。"
    if code == "current_overload":
        return "建议分批下电高负载设备，检查回路负载分配并安排电工复核。"
    if code == "people_overcrowded":
        return "建议立即分流人员并限制新增入场，确保不超过安全容量。"
    return "建议先现场核查并记录告警来源，按应急流程处理。"


def _agent_handle_alarm_advice(user_name, role, limit=5):
    owner = str(user_name or "").strip()
    if not owner:
        return _agent_response(code=401, msg="unauthorized", reply="登录状态失效，请重新登录。", action="error", http_status=401)
    if str(role or "").strip() != "admin":
        return _agent_response(
            code=0,
            msg="ok",
            reply="报警联动建议仅管理员可用。若你在现场，请优先保障人身安全并联系值班老师。",
            action="alarm_advice",
            http_status=200,
        )

    day_ago = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    rows = query(
        """
        SELECT id,
               lab_name AS labName,
               alarm_code AS alarmCode,
               level,
               message,
               created_at AS createdAt
        FROM lab_sensor_alarm
        WHERE created_at >= %s
        ORDER BY id DESC
        LIMIT 200
        """,
        (day_ago,),
    )
    if not rows:
        return _agent_response(code=0, msg="ok", reply="最近24小时没有新的传感器报警。", action="alarm_advice", http_status=200)

    grouped = {}
    for row in rows:
        lab_name = str((row or {}).get("labName") or "").strip() or "未命名实验室"
        alarm_code = str((row or {}).get("alarmCode") or "").strip() or "unknown"
        key = f"{lab_name}|{alarm_code}"
        if key not in grouped:
            grouped[key] = {
                "labName": lab_name,
                "alarmCode": alarm_code,
                "count": 0,
                "latestAt": "",
                "latestMsg": "",
                "level": str((row or {}).get("level") or "alarm").strip() or "alarm",
            }
        grouped[key]["count"] = int(grouped[key]["count"]) + 1
        created_at = _to_text_time((row or {}).get("createdAt"))
        if not grouped[key]["latestAt"] or created_at > grouped[key]["latestAt"]:
            grouped[key]["latestAt"] = created_at
            grouped[key]["latestMsg"] = str((row or {}).get("message") or "").strip()

    items = list(grouped.values())
    items = sorted(items, key=lambda x: (int(x.get("count") or 0), str(x.get("latestAt") or "")), reverse=True)
    top_n = max(1, min(int(_to_int_or_none(limit) or 5), 12))
    top = items[:top_n]

    lines = []
    for idx, item in enumerate(top, start=1):
        code = str(item.get("alarmCode") or "")
        message = str(item.get("latestMsg") or "").strip()
        message_text = message if message else code
        lines.append(
            f"{idx}. {item.get('labName')}：{message_text}（近24小时{int(item.get('count') or 0)}次，最新{item.get('latestAt') or '-'}）"
            f"\n处置建议：{_alarm_advice_for_code(code)}"
        )

    total_alarm_count = len(rows)
    reply = (
        f"最近24小时共有{total_alarm_count}条报警记录，重点联动建议如下：\n"
        + "\n".join(lines)
        + "\n请同步安排现场复核、通知值班人员，并在处理后复测确认。"
    )
    return _agent_response(code=0, msg="ok", reply=reply, action="alarm_advice", http_status=200)


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


def can_view_reservation_private_fields(actor_role):
    return str(actor_role or "").strip().lower() in RESERVATION_PRIVATE_VIEW_ROLE_SET


def _reservation_identity_code_label(user_role):
    return "学号" if str(user_role or "").strip().lower() == "student" else "工号"


def _build_reservation_reserver_payload(row):
    item = row or {}
    user_name = str(item.get("user") or item.get("userName") or "").strip()
    user_role = str(item.get("reserverRole") or item.get("userRole") or "").strip().lower()
    display_name = str(item.get("reserverNickname") or item.get("nickname") or "").strip() or user_name
    number_label = _reservation_identity_code_label(user_role)
    number_value = str(item.get("studentNo") or "").strip() if number_label == "学号" else str(item.get("jobNo") or "").strip()
    return {
        "identityVisible": True,
        "username": user_name,
        "name": display_name,
        "role": user_role,
        "numberLabel": number_label,
        "numberValue": number_value,
    }


def serialize_reservation_record_for_actor(row, actor=None, force_hide_private=False):
    actor = actor or {}
    actor_role = str(actor.get("role") or "").strip().lower()
    actor_username = str(actor.get("username") or "").strip()
    item = row or {}
    reserver_username = str(item.get("user") or item.get("userName") or "").strip()
    can_view_private = (not force_hide_private) and (
        can_view_reservation_private_fields(actor_role) or (actor_username and actor_username == reserver_username)
    )

    payload = {
        "id": int(item.get("id") or 0),
        "labId": _to_int_or_none(item.get("labId")),
        "labName": str(item.get("labName") or "").strip(),
        "date": str(item.get("date") or "").strip(),
        "time": str(item.get("time") or "").strip(),
        "status": str(item.get("status") or "").strip(),
        "rejectReason": str(item.get("rejectReason") or "").strip(),
        "adminNote": str(item.get("adminNote") or "").strip(),
        "reviewRole": str(item.get("reviewRole") or "").strip(),
        "reviewPolicy": str(item.get("reviewPolicy") or "").strip(),
        "createdAt": _to_text_time(item.get("createdAt")),
        "identityVisible": bool(can_view_private),
    }
    if can_view_private:
        payload["user"] = reserver_username
        payload["reason"] = str(item.get("reason") or "").strip()
        payload["reserver"] = _build_reservation_reserver_payload(item)
    else:
        payload["user"] = ""
        payload["reason"] = ""
        payload["reserver"] = {"identityVisible": False}
        payload["identityHidden"] = True
    return payload


def query_reservation_slot_privacy_guarded(lab_name, date_text="", time_text="", actor=None, limit=12, allow_private=False):
    actor = actor or {}
    safe_lab_name = str(lab_name or "").strip()
    safe_date = str(date_text or "").strip()
    safe_time = str(time_text or "").strip()
    target_slots = parse_slots(safe_time) if safe_time else set()
    if safe_time and not target_slots:
        raise BizError("invalid time", 400)

    where_sql = " WHERE r.lab_name=%s "
    params = [safe_lab_name]
    if safe_date:
        where_sql += " AND r.date=%s "
        params.append(safe_date)

    rows = query(
        f"""
        SELECT r.id,
               r.lab_id AS labId,
               r.lab_name AS labName,
               r.user_name AS user,
               r.date,
               r.time,
               r.reason,
               r.status,
               r.reject_reason AS rejectReason,
               r.admin_note AS adminNote,
               r.review_role AS reviewRole,
               r.review_policy AS reviewPolicy,
               r.created_at AS createdAt,
               u.role AS reserverRole,
               u.nickname AS reserverNickname,
               u.student_no AS studentNo,
               u.job_no AS jobNo
        FROM reservation r
        LEFT JOIN user u ON u.username=r.user_name
        {where_sql}
        ORDER BY r.date DESC, r.id DESC
        LIMIT %s
        """,
        tuple(params + [max(1, int(limit))]),
    )

    filtered = []
    active_rows = []
    for row in rows:
        if target_slots:
            row_slots = parse_slots(row.get("time"))
            if not row_slots or not (target_slots & row_slots):
                continue
        filtered.append(row)
        if str((row or {}).get("status") or "").strip().lower() in RESERVATION_ACTIVE_STATUS_SET:
            active_rows.append(row)

    is_slot_query = bool(safe_date and target_slots)
    matched_rows = active_rows if is_slot_query else filtered
    identity_visible = bool(allow_private)
    items = [
        serialize_reservation_record_for_actor(row, actor=actor, force_hide_private=not identity_visible)
        for row in matched_rows[: max(1, int(limit))]
    ]

    status_summary = {}
    for row in matched_rows:
        key = str((row or {}).get("status") or "").strip().lower()
        if not key:
            continue
        status_summary[key] = int(status_summary.get(key) or 0) + 1

    return {
        "slot": {"labName": safe_lab_name, "date": safe_date, "time": safe_time},
        "isSlotQuery": bool(is_slot_query),
        "booked": bool(active_rows),
        "identityVisible": bool(identity_visible),
        "identityRestricted": bool(active_rows) and not identity_visible,
        "count": len(matched_rows),
        "activeCount": len(active_rows),
        "statusSummary": status_summary,
        "items": items,
    }


def _is_reservation_identity_query(text):
    raw = str(text or "").strip()
    if not raw:
        return False
    identity_tokens = ("谁预约", "谁预定", "预约人", "预定人", "谁占用", "姓名", "学号", "工号", "原因", "用途")
    return any(token in raw for token in identity_tokens)


def _is_lab_reservations_query(text):
    raw = str(text or "").strip()
    if not raw:
        return False
    has_reserve_word = any(x in raw for x in ("预约", "预定"))
    has_query_word = any(x in raw for x in ("检查", "查看", "查询", "检索", "统计", "记录", "列表", "所有", "谁", "是谁", "占用"))
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


def _is_cancel_reservations_request(text, lab_name="", reservation_id=None):
    raw = str(text or "").strip()
    if not raw:
        return False
    has_cancel = any(x in raw for x in ("取消", "撤销"))
    has_reserve = any(x in raw for x in ("预约", "预定"))
    if not has_cancel or not has_reserve:
        return False
    if _is_cancel_all_reservations_request(raw):
        return False
    return True


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

    def _tx(cur):
        cur.execute(
            """
            SELECT id, lab_id AS labId, lab_name AS labName, user_name AS user, status, date, time
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

        lab_id = _to_int_or_none(row.get("labId"))
        lab_name = str(row.get("labName") or "").strip()
        schedule_error = validate_reservation_schedule(date_text, time_text, lab_id=lab_id, lab_name=lab_name)
        if schedule_error:
            raise BizError(schedule_error, 400)
        review_decision = resolve_reservation_review_policy(
            lab_id=lab_id,
            lab_name=lab_name,
            date_text=date_text,
            time_range=time_text,
        )
        next_status = str(review_decision.get("status") or "pending").strip() or "pending"
        review_role = str(review_decision.get("reviewRole") or "").strip().lower()
        review_policy = str(review_decision.get("reviewPolicy") or "").strip().lower()

        lock_key = _reservation_lock_key(lab_name, date_text)
        if not _acquire_named_lock(cur, lock_key):
            raise BizError("reservation busy, try again", 409)
        try:
            if has_approved_conflict_with_cur(cur, lab_name, date_text, time_text, exclude_id=rid_int):
                raise BizError("reservation conflict with approved", 409)
            cur.execute(
                """
                UPDATE reservation
                SET date=%s,
                    time=%s,
                    status=%s,
                    reject_reason='',
                    review_role=%s,
                    review_policy=%s
                WHERE id=%s
                """,
                (date_text, time_text, next_status, review_role, review_policy, rid_int),
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
            "status": next_status,
            "reviewRole": review_role,
            "reviewPolicy": review_policy,
        }

    return run_in_transaction(_tx)


def _agent_handle_reschedule_request(user_name, role, reservation_id, lab_name, date_text, time_text, confirmed=False):
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

    schedule_error = validate_reservation_schedule(new_date, new_time, lab_name=str((target or {}).get("labName") or lab_text or "").strip())
    if schedule_error:
        _agent_pending_set(
            owner,
            "reschedule",
            new_date,
            new_time,
            extra={"targetReservationId": int((target or {}).get("id") or rid or 0), "labName": str((target or {}).get("labName") or lab_text or "").strip()},
        )
        reply = f"改期时间不合法：{schedule_error}。请调整日期或时段后重试。"
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_info", http_status=200)

    if not confirmed:
        confirm_slots = {
            "targetReservationId": int((target or {}).get("id") or 0),
            "labName": str((target or {}).get("labName") or lab_text or "").strip(),
            "oldDate": str((target or {}).get("date") or "").strip(),
            "oldTime": str((target or {}).get("time") or "").strip(),
            "date": new_date,
            "time": new_time,
        }
        _agent_pending_set(owner, "reschedule_confirm", slots=confirm_slots, missing_slots=[], state="confirming")
        pending_payload = _agent_pending_to_public_payload({"intent": "reschedule_confirm", "slots": confirm_slots, "missing_slots": [], "state": "confirming"})
        reply = (
            f"确认将预约 #{int((target or {}).get('id') or 0)}（{str((target or {}).get('labName') or '').strip()} "
            f"{str((target or {}).get('date') or '').strip()} {str((target or {}).get('time') or '').strip()}）"
            f"改到 {new_date} {new_time}。回复“确认”继续，回复“算了”取消，也可以直接说新的日期或时段。"
        )
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_confirm", extra={"pending": pending_payload}, http_status=200)

    try:
        updated = _reschedule_reservation_internal(
            rid=target.get("id"),
            date=new_date,
            time_range=new_time,
            operator_user=owner,
            is_admin=is_admin,
        )
    except BizError as e:
        if int(e.status or 0) == 409:
            return _agent_response(code=0, msg="ok", reply="改期失败：新时段有冲突或被占用，请换一个时间。", action="conflict", http_status=200)
        return _agent_response(code=e.status, msg=e.msg, reply=f"改期失败：{e.msg}", action="error", http_status=e.status)

    _agent_pending_clear(owner)
    status_label = _reservation_status_label(updated.get("status"))
    reply = (
        f"已将预约 #{updated['id']}（{updated['labName']} {updated['oldDate']} {updated['oldTime']}）"
        f"改期为 {updated['date']} {updated['time']}，当前状态为{status_label}。"
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

    target_slots = parse_slots(time_text) if str(time_text or "").strip() else set()
    if str(time_text or "").strip() and not target_slots:
        return _agent_response(code=0, msg="ok", reply="时段格式不正确，请用例如 1-2节 或 08:00-08:40,08:45-09:35。", action="ask_info", http_status=200)

    actor = {"id": getattr(g, "current_user", {}).get("id"), "username": owner, "role": role}
    permission_status = get_ai_permission_status(actor, AI_PERMISSION_RESERVATION_VIEW_OWNER)
    can_view_owner = bool(permission_status.get("granted"))
    result = query_reservation_slot_privacy_guarded(
        lab_name=str(lab.get("name") or "").strip(),
        date_text=str(date_text or "").strip(),
        time_text=str(time_text or "").strip(),
        actor=actor,
        limit=max(1, int(limit)),
        allow_private=can_view_owner,
    )
    audit_log(
        "agent.reservation.slot_query",
        target_type="reservation",
        detail={
            "labName": result.get("slot", {}).get("labName"),
            "date": result.get("slot", {}).get("date"),
            "time": result.get("slot", {}).get("time"),
            "booked": bool(result.get("booked")),
            "identityVisible": bool(result.get("identityVisible")),
            "identityRequested": bool(result.get("isSlotQuery")) or _is_reservation_identity_query(str(lab_name or "")),
            "permissionCode": AI_PERMISSION_RESERVATION_VIEW_OWNER,
            "permissionGranted": can_view_owner,
            "permissionSource": str(permission_status.get("source") or ""),
            "permissionExpiresAt": str(permission_status.get("expiresAt") or ""),
            "count": int(result.get("count") or 0),
            "activeCount": int(result.get("activeCount") or 0),
        },
        actor=actor,
    )

    slot_info = result.get("slot") if isinstance(result.get("slot"), dict) else {}
    safe_lab_name = str(slot_info.get("labName") or lab.get("name") or "").strip()
    safe_date = str(slot_info.get("date") or "").strip()
    safe_time = str(slot_info.get("time") or "").strip()
    can_view_private = bool(result.get("identityVisible"))
    is_slot_query = bool(result.get("isSlotQuery"))
    items = result.get("items") if isinstance(result.get("items"), list) else []

    if is_slot_query:
        if not bool(result.get("booked")):
            reply = f"{safe_lab_name} {safe_date} {safe_time} 该时段未被预约。".strip()
            return _agent_response(
                code=0,
                msg="ok",
                reply=reply,
                action="lab_reservation_list",
                extra={"reservationQuery": result},
                http_status=200,
            )
        if not can_view_private:
            reply = f"{safe_lab_name} {safe_date} {safe_time} 该时段已被预约，你无权查看预约人信息。".strip()
            return _agent_response(
                code=0,
                msg="ok",
                reply=reply,
                action="lab_reservation_list",
                extra={"reservationQuery": result},
                http_status=200,
            )

        row = items[0] if items else {}
        reserver = row.get("reserver") if isinstance(row.get("reserver"), dict) else {}
        name_text = str(reserver.get("name") or row.get("user") or "").strip() or "未署名用户"
        number_label = str(reserver.get("numberLabel") or "").strip()
        number_value = str(reserver.get("numberValue") or "").strip()
        reason_text = str(row.get("reason") or "").strip()
        status_text = _reservation_status_label(row.get("status"))
        bits = [f"{safe_lab_name} {safe_date} {safe_time} 该时段已被预约。", f"预约人：{name_text}"]
        if number_label and number_value:
            bits.append(f"{number_label}：{number_value}")
        if reason_text:
            bits.append(f"用途：{reason_text}")
        bits.append(f"状态：{status_text}")
        reply = "，".join(bits) + "。"
        return _agent_response(
            code=0,
            msg="ok",
            reply=reply,
            action="lab_reservation_list",
            extra={"reservationQuery": result},
            http_status=200,
        )

    if not items:
        reply = f"{safe_lab_name} 当前没有匹配的预约记录。"
        return _agent_response(
            code=0,
            msg="ok",
            reply=reply,
            action="lab_reservation_list",
            extra={"reservationQuery": result},
            http_status=200,
        )

    status_counter = result.get("statusSummary") if isinstance(result.get("statusSummary"), dict) else {}
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

    if not can_view_private:
        summary_bits = [f"{safe_lab_name} 匹配预约共{int(result.get('count') or 0)}条"]
        if safe_date:
            summary_bits.append(f"日期：{safe_date}")
        if safe_time:
            summary_bits.append(f"时段：{safe_time}")
        if bool(result.get("booked")):
            summary_bits.append("当前存在已预约时段")
        else:
            summary_bits.append("当前没有已预约时段")
        summary_bits.append("无权查看预约人信息")
        reply = "，".join(summary_bits) + "。"
        return _agent_response(
            code=0,
            msg="ok",
            reply=reply,
            action="lab_reservation_list",
            extra={"reservationQuery": result},
            http_status=200,
        )

    lines = []
    for idx, row in enumerate(items[:10], start=1):
        reserver = row.get("reserver") if isinstance(row.get("reserver"), dict) else {}
        name_text = str(reserver.get("name") or row.get("user") or "").strip() or "未署名用户"
        number_label = str(reserver.get("numberLabel") or "").strip()
        number_value = str(reserver.get("numberValue") or "").strip()
        reason_text = str(row.get("reason") or "").strip()
        detail_bits = [f"{idx}. #{int(row.get('id') or 0)} {row.get('date') or ''} {row.get('time') or ''}（{_reservation_status_label(row.get('status'))}"]
        detail_tail = [f"预约人：{name_text}"]
        if number_label and number_value:
            detail_tail.append(f"{number_label}：{number_value}")
        if reason_text:
            detail_tail.append(f"用途：{reason_text}")
        lines.append(detail_bits[0] + "，" + "，".join(detail_tail) + "）")

    header = f"{safe_lab_name} 预约记录共{int(result.get('count') or 0)}条，状态分布：{status_text}。"
    reply = header + "\n最近记录：\n" + "\n".join(lines)
    return _agent_response(
        code=0,
        msg="ok",
        reply=reply,
        action="lab_reservation_list",
        extra={"reservationQuery": result},
        http_status=200,
    )


def _agent_handle_cancel_reservations(user_name, role, reservation_id=None, lab_name="", date_text="", time_text="", confirmed=False, target_ids=None):
    owner = str(user_name or "").strip()
    if not owner:
        return _agent_response(code=401, msg="unauthorized", reply="登录状态失效，请重新登录。", action="error", http_status=401)

    is_admin = str(role or "").strip() == "admin"
    rid = _to_int_or_none(reservation_id)
    requested_ids = []
    if isinstance(target_ids, (list, tuple)):
        requested_ids = [int(_to_int_or_none(x) or 0) for x in target_ids if int(_to_int_or_none(x) or 0) > 0]

    filters = {
        "reservationId": int(rid or 0),
        "labName": str(lab_name or "").strip(),
        "date": str(date_text or "").strip(),
        "time": str(time_text or "").strip(),
    }

    if filters["time"]:
        slot_filter = parse_slots(filters["time"])
        if not slot_filter:
            _agent_pending_set(owner, "cancel_reservation", slots=filters, missing_slots=[], state="collecting")
            return _agent_response(
                code=0,
                msg="ok",
                reply="时段格式不正确，请用例如 1-2节 或 08:00-08:40,08:45-09:35。",
                action="ask_info",
                http_status=200,
            )
    else:
        slot_filter = set()

    if not confirmed and not rid and not requested_ids and not filters["labName"] and not filters["date"] and not filters["time"]:
        _agent_pending_set(owner, "cancel_reservation", slots=filters, missing_slots=["reservationId"], state="collecting")
        return _agent_response(
            code=0,
            msg="ok",
            reply="请告诉我要取消哪条预约。你可以直接说“取消 #12 预约”，或说“取消 C406 明天 1-2节 的预约”。",
            action="ask_info",
            http_status=200,
        )

    resolved_lab_name = str(filters["labName"] or "").strip()
    rows = []
    if requested_ids:
        placeholders = ",".join(["%s"] * len(requested_ids))
        params = list(requested_ids)
        where_sql = f" WHERE id IN ({placeholders}) AND status IN ('pending','approved') "
        if not is_admin:
            where_sql += " AND user_name=%s "
            params.append(owner)
        rows = query(
            f"""
            SELECT id, lab_name AS labName, user_name AS user, date, time, status
            FROM reservation
            {where_sql}
            ORDER BY date DESC, id DESC
            """,
            tuple(params),
        )
    elif rid:
        rows = query(
            """
            SELECT id, lab_name AS labName, user_name AS user, date, time, status
            FROM reservation
            WHERE id=%s
            LIMIT 1
            """,
            (rid,),
        )
        if not rows:
            return _agent_response(code=0, msg="ok", reply=f"未找到预约 #{rid}。请确认编号后重试。", action="ask_info", http_status=200)
        current = rows[0]
        if not is_admin and str(current.get("user") or "").strip() != owner:
            return _agent_response(code=403, msg="forbidden", reply=f"预约 #{rid} 不属于你，无法取消。", action="error", http_status=403)
        current_status = str(current.get("status") or "").strip()
        if current_status not in ("pending", "approved"):
            return _agent_response(
                code=0,
                msg="ok",
                reply=f"预约 #{rid} 当前状态为{_reservation_status_label(current_status)}，不能再次取消。",
                action="ask_info",
                http_status=200,
            )
    else:
        if resolved_lab_name:
            try:
                lab = _resolve_lab_from_agent(lab_name=resolved_lab_name)
                resolved_lab_name = str(lab.get("name") or "").strip()
            except BizError as e:
                return _agent_response(code=e.status, msg=e.msg, reply=f"实验室信息有问题：{e.msg}", action="ask_info", http_status=e.status)

        params = []
        where_sql = " WHERE status IN ('pending','approved') "
        if not is_admin:
            where_sql += " AND user_name=%s "
            params.append(owner)
        if resolved_lab_name:
            where_sql += " AND lab_name=%s "
            params.append(resolved_lab_name)
        if filters["date"]:
            where_sql += " AND date=%s "
            params.append(filters["date"])
        rows = query(
            f"""
            SELECT id, lab_name AS labName, user_name AS user, date, time, status
            FROM reservation
            {where_sql}
            ORDER BY date DESC, id DESC
            LIMIT 300
            """,
            tuple(params),
        )

    filtered_rows = []
    for row in rows:
        if slot_filter:
            row_slots = parse_slots((row or {}).get("time"))
            if not row_slots or not (slot_filter & row_slots):
                continue
        filtered_rows.append(row)

    if not filtered_rows:
        parts = []
        if resolved_lab_name:
            parts.append(resolved_lab_name)
        if filters["date"]:
            parts.append(filters["date"])
        if filters["time"]:
            parts.append(filters["time"])
        desc = " ".join(parts).strip()
        prefix = f"在 {desc} " if desc else ""
        return _agent_response(
            code=0,
            msg="ok",
            reply=f"{prefix}没有找到可取消的预约（仅待审批/已通过支持取消）。",
            action="cancel_done",
            http_status=200,
        )

    ids = [int((row or {}).get("id") or 0) for row in filtered_rows if int((row or {}).get("id") or 0) > 0]
    if not ids:
        return _agent_response(code=0, msg="ok", reply="没有可取消的预约。", action="cancel_done", http_status=200)

    if not confirmed:
        preview_rows = filtered_rows[:5]
        preview_lines = [
            f"{idx}. #{int((row or {}).get('id') or 0)} {str((row or {}).get('labName') or '').strip()} "
            f"{str((row or {}).get('date') or '').strip()} {str((row or {}).get('time') or '').strip()}（{_reservation_status_label((row or {}).get('status'))}）"
            for idx, row in enumerate(preview_rows, start=1)
        ]
        confirm_slots = {
            "reservationId": int(rid or 0),
            "labName": resolved_lab_name,
            "date": filters["date"],
            "time": filters["time"],
            "targetIds": ids,
            "matchedCount": len(ids),
        }
        _agent_pending_set(owner, "cancel_reservation_confirm", slots=confirm_slots, missing_slots=[], state="confirming")
        pending_payload = _agent_pending_to_public_payload({"intent": "cancel_reservation_confirm", "slots": confirm_slots, "missing_slots": [], "state": "confirming"})
        if len(ids) == 1:
            row = filtered_rows[0]
            reply = (
                f"确认取消预约 #{int((row or {}).get('id') or 0)}（{str((row or {}).get('labName') or '').strip()} "
                f"{str((row or {}).get('date') or '').strip()} {str((row or {}).get('time') or '').strip()}）？"
                "回复“确认”继续，回复“算了”放弃。"
            )
        else:
            reply = f"确认取消符合条件的 {len(ids)} 条预约？\n" + "\n".join(preview_lines)
            if len(filtered_rows) > len(preview_rows):
                reply += f"\n其余 {len(filtered_rows) - len(preview_rows)} 条将在确认后一起取消。"
            reply += "\n回复“确认”继续，回复“算了”放弃。"
        return _agent_response(code=0, msg="ok", reply=reply, action="ask_confirm", extra={"pending": pending_payload}, http_status=200)

    placeholders = ",".join(["%s"] * len(ids))

    def _tx(cur):
        params = list(ids)
        where_sql = f" WHERE id IN ({placeholders}) AND status IN ('pending','approved') "
        if not is_admin:
            where_sql += " AND user_name=%s "
            params.append(owner)
        cur.execute(f"UPDATE reservation SET status='cancelled' {where_sql}", tuple(params))
        return int(cur.rowcount or 0)

    affected = int(run_in_transaction(_tx) or 0)
    _agent_pending_clear(owner)
    audit_log(
        "agent.chat.cancel.reservation",
        target_type="reservation",
        detail={"count": affected, "ids": ids[:20], "matchedCount": len(ids)},
    )
    if affected <= 0:
        return _agent_response(
            code=0,
            msg="ok",
            reply="没有取消任何预约，可能这些记录刚刚已被处理或状态已变化。请先刷新后重试。",
            action="cancel_done",
            http_status=200,
        )
    if affected == 1 and filtered_rows:
        row = filtered_rows[0]
        reply = (
            f"已取消预约 #{int((row or {}).get('id') or 0)}："
            f"{str((row or {}).get('labName') or '').strip()} {str((row or {}).get('date') or '').strip()} {str((row or {}).get('time') or '').strip()}。"
        )
    else:
        reply = f"已取消 {affected} 条预约。"
    return _agent_response(code=0, msg="ok", reply=reply, action="cancel_done", http_status=200)


def _agent_handle_cancel_lab_reservations(user_name, lab_name, date_text="", time_text=""):
    return _agent_handle_cancel_reservations(
        user_name=user_name,
        role="",
        reservation_id=None,
        lab_name=lab_name,
        date_text=date_text,
        time_text=time_text,
        confirmed=False,
    )


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


def _agent_pending_slot(pending_ctx, key, default=""):
    if not isinstance(pending_ctx, dict):
        return default
    raw_key = str(key or "").strip()
    if not raw_key:
        return default
    slots = pending_ctx.get("slots")
    if isinstance(slots, dict) and raw_key in slots:
        return slots.get(raw_key)
    return pending_ctx.get(raw_key, default)


def _normalize_agent_pending_missing_slots(raw_missing):
    normalized = []
    seen = set()
    items = raw_missing if isinstance(raw_missing, list) else []
    for item in items:
        key = str(item or "").strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def _agent_compact_slots(raw_slots):
    slots = {}
    if not isinstance(raw_slots, dict):
        return slots
    for k, v in raw_slots.items():
        key = str(k or "").strip()
        if not key:
            continue
        if isinstance(v, str):
            val = v.strip()
            if not val:
                continue
            slots[key] = val
            continue
        if v is None:
            continue
        slots[key] = v
    return slots


def _agent_pending_normalize_row(row):
    now_ts = int(time.time())
    raw = dict(row or {})
    slots = _agent_compact_slots(raw.get("slots") if isinstance(raw.get("slots"), dict) else {})
    legacy_keys = (
        "date",
        "time",
        "labName",
        "reason",
        "issueType",
        "description",
        "equipmentHint",
        "targetReservationId",
        "pendingCancelCount",
        "nickname",
        "reservationId",
    )
    for key in legacy_keys:
        if key in slots:
            continue
        val = raw.get(key)
        if isinstance(val, str):
            val = val.strip()
        if val in ("", None):
            continue
        slots[key] = val

    state = str(raw.get("state") or "").strip().lower()
    if state not in AGENT_PENDING_STATE_SET:
        state = "collecting"

    missing_slots = _normalize_agent_pending_missing_slots(raw.get("missing_slots"))
    if not missing_slots:
        missing_slots = _normalize_agent_pending_missing_slots(raw.get("missingSlots"))

    updated_at = _to_int_or_none(raw.get("updated_at"))
    if updated_at is None:
        updated_at = _to_int_or_none(raw.get("updatedAt"))
    updated_at = int(updated_at or now_ts)

    expires_at = _to_int_or_none(raw.get("expires_at"))
    if expires_at is None:
        expires_at = _to_int_or_none(raw.get("expiresAt"))
    expires_at = int(expires_at or (updated_at + max(60, int(AGENT_PENDING_TTL_SECONDS))))

    normalized = {
        "intent": str(raw.get("intent") or "").strip(),
        "slots": slots,
        "missing_slots": missing_slots,
        "state": state,
        "updated_at": updated_at,
        "expires_at": expires_at,
        "updatedAt": updated_at,
        "expiresAt": expires_at,
        "missingSlots": list(missing_slots),
    }
    for key, val in slots.items():
        normalized[key] = val
    return normalized


def _agent_pending_to_public_payload(pending_ctx):
    normalized = _agent_pending_normalize_row(pending_ctx)
    return {
        "intent": str(normalized.get("intent") or "").strip(),
        "slots": dict(normalized.get("slots") or {}),
        "missing_slots": list(normalized.get("missing_slots") or []),
        "state": str(normalized.get("state") or "").strip() or "collecting",
        "updated_at": int(normalized.get("updated_at") or 0),
        "expires_at": int(normalized.get("expires_at") or 0),
    }


def _agent_multiturn_intent_from_tool(tool_op):
    op = str(tool_op or "").strip()
    return str(AGENT_MULTI_TURN_TOOL_INTENT_MAP.get(op) or "").strip()


def _agent_multiturn_tool_from_intent(intent):
    key = str(intent or "").strip()
    if key == "reserve_plan_pick":
        return "reserve_create"
    return str(AGENT_MULTI_TURN_INTENT_TOOL_MAP.get(key) or "").strip()


def _agent_is_multiturn_intent(intent):
    key = str(intent or "").strip()
    return key in AGENT_MULTI_TURN_SCHEMA


def _agent_is_confirm_text(text):
    raw = str(text or "").strip().lower()
    if not raw:
        return False
    return raw in AGENT_CONFIRM_TEXT_SET or raw.startswith("确认")


def _agent_is_pending_abort_text(text):
    raw = str(text or "").strip().lower()
    if not raw:
        return False
    if raw in AGENT_CANCEL_TEXT_SET:
        return True
    return any(x in raw for x in ("取消", "重来", "重新开始"))


def _agent_merge_slot_values(base_slots, incoming_slots):
    merged = _agent_compact_slots(base_slots)
    updates = _agent_compact_slots(incoming_slots)
    for key, val in updates.items():
        merged[key] = val
    return merged


def _agent_is_valid_date_text(value):
    text = str(value or "").strip()
    if not text:
        return False
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except Exception:
        return False


def _agent_is_meaningful_repair_description(value):
    text = str(value or "").strip()
    if not text:
        return False
    compact = re.sub(r"\s+", "", text)
    if re.fullmatch(r"[A-Za-z]{1,2}\d{3,4}", compact):
        return False
    if re.fullmatch(r"(PC-)?[A-Za-z]{1,3}\d{1,3}", compact, flags=re.IGNORECASE):
        return False
    return len(text) >= 4 or any(x in text for x in ("坏", "故障", "异常", "无法", "断网", "蓝屏", "死机"))


def _agent_normalize_plan_items(raw_plans):
    plans = []
    used_ids = set()
    rows = raw_plans if isinstance(raw_plans, list) else []
    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        plan_id = str(row.get("planId") or "").strip().upper() or f"A{idx}"
        if plan_id in used_ids:
            plan_id = f"A{idx}"
        used_ids.add(plan_id)
        score = row.get("score")
        try:
            score_val = round(float(score), 4)
        except Exception:
            score_val = 0.0
        plans.append(
            {
                "planId": plan_id,
                "labId": _to_int_or_none(row.get("labId")),
                "labName": str(row.get("labName") or "").strip(),
                "date": str(row.get("date") or "").strip(),
                "time": str(row.get("time") or "").strip(),
                "score": score_val,
                "reason": str(row.get("reason") or "").strip(),
            }
        )
    return plans


def _agent_find_plan_by_id(plans, plan_id):
    target = str(plan_id or "").strip().upper()
    if not target:
        return None
    for item in _agent_normalize_plan_items(plans):
        if str(item.get("planId") or "").strip().upper() == target:
            return item
    return None


def _agent_extract_plan_choice(text, plans):
    normalized_plans = _agent_normalize_plan_items(plans)
    if not normalized_plans:
        return None
    raw = str(text or "").strip()
    if not raw:
        return None
    upper = raw.upper()

    for item in normalized_plans:
        pid = str(item.get("planId") or "").strip().upper()
        if not pid:
            continue
        if pid in upper:
            return item

    letter_map = {"A": 1, "B": 2, "C": 3, "D": 4}
    m_letter = re.search(r"方案\s*([A-Da-d])", raw)
    if m_letter:
        idx = int(letter_map.get(str(m_letter.group(1) or "").strip().upper()) or 0)
        if 1 <= idx <= len(normalized_plans):
            return normalized_plans[idx - 1]

    zh_map = {
        "第一个": 1,
        "第一项": 1,
        "第一套": 1,
        "第1个": 1,
        "第二个": 2,
        "第二项": 2,
        "第二套": 2,
        "第2个": 2,
        "第三个": 3,
        "第三项": 3,
        "第三套": 3,
        "第3个": 3,
    }
    for token, idx in zh_map.items():
        if token in raw and 1 <= idx <= len(normalized_plans):
            return normalized_plans[idx - 1]

    m_num = re.search(r"(?:选|方案|第)\s*([1-9]\d*)", raw)
    if not m_num and re.fullmatch(r"[1-9]\d*", raw):
        m_num = re.match(r"([1-9]\d*)", raw)
    if m_num:
        idx = int(m_num.group(1))
        if 1 <= idx <= len(normalized_plans):
            return normalized_plans[idx - 1]
    return None


def _agent_get_selected_plan_from_slots(slots):
    compact = _agent_compact_slots(slots if isinstance(slots, dict) else {})
    plans = _agent_normalize_plan_items(compact.get("plans"))
    selected_plan_id = str(compact.get("selectedPlanId") or "").strip()
    if not plans or not selected_plan_id:
        return None
    return _agent_find_plan_by_id(plans, selected_plan_id)


def _agent_build_plan_options_text(plans, prefix=""):
    normalized_plans = _agent_normalize_plan_items(plans)
    if not normalized_plans:
        return "该时段冲突，请换一个时间，或告诉我你希望的日期。"
    header = str(prefix or "").strip() or "该时段冲突，我给你3个可选方案："
    lines = []
    for idx, item in enumerate(normalized_plans, start=1):
        lines.append(
            f"{idx}. 方案{chr(ord('A') + idx - 1)}（{item.get('planId')}）："
            f"{item.get('labName')} {item.get('date')} {item.get('time')}（score {item.get('score')}）"
        )
    return header + "\n" + "\n".join(lines) + "\n回复“选2”/“方案B”/“第一个”即可。"


def _agent_collect_slots_for_intent(intent, text, tool_call=None, pending_ctx=None):
    key = str(intent or "").strip()
    call = tool_call if isinstance(tool_call, dict) else {}
    pending = _agent_pending_normalize_row(pending_ctx or {})
    base_slots = dict(pending.get("slots") or {})
    incoming = {}

    if key in {"reserve_create", "reserve_query"}:
        date_text = str(call.get("date") or "").strip() or _extract_date_from_text(text)
        time_text = str(call.get("time") or "").strip() or _extract_time_from_text(text)
        lab_name = str(call.get("labName") or "").strip() or _extract_lab_name_from_text(text)
        if date_text:
            incoming["date"] = date_text
        if time_text:
            incoming["time"] = time_text
        if lab_name:
            incoming["labName"] = lab_name
        if key == "reserve_create":
            reason = str(call.get("reason") or "").strip() or _extract_reservation_reason_from_text(text)
            if reason:
                incoming["reason"] = reason

    if key == "repair_create":
        issue_type = str(call.get("issueType") or "").strip().lower() or _extract_repair_issue_type_from_text(text)
        if issue_type:
            incoming["issueType"] = AGENT_REPAIR_ISSUE_ALIAS.get(issue_type, issue_type)
        desc = str(call.get("description") or "").strip()
        if not _agent_is_meaningful_repair_description(desc):
            desc = _extract_repair_description_from_text(text)
        if _agent_is_meaningful_repair_description(desc):
            incoming["description"] = desc
        lab_name = str(call.get("labName") or "").strip() or _extract_lab_name_from_text(text)
        equipment_hint = str(call.get("equipmentHint") or "").strip() or _extract_equipment_hint_from_text(text)
        if lab_name:
            incoming["labName"] = lab_name
        if equipment_hint:
            incoming["equipmentHint"] = equipment_hint

    if key == "reserve_plan_pick":
        plans = _agent_normalize_plan_items(call.get("plans") or base_slots.get("plans"))
        if plans:
            incoming["plans"] = plans
        selected = _agent_extract_plan_choice(text, plans)
        if selected:
            incoming["selectedPlanId"] = str(selected.get("planId") or "").strip()
            incoming["labId"] = selected.get("labId")
            incoming["labName"] = str(selected.get("labName") or "").strip()
            incoming["date"] = str(selected.get("date") or "").strip()
            incoming["time"] = str(selected.get("time") or "").strip()

    return _agent_merge_slot_values(base_slots, incoming)


def _agent_compute_missing_slots_for_intent(intent, slots):
    key = str(intent or "").strip()
    merged = _agent_compact_slots(slots if isinstance(slots, dict) else {})
    missing_slots = []

    if key == "reserve_create":
        if not str(merged.get("labName") or "").strip():
            missing_slots.append("labName")
        if not _agent_is_valid_date_text(merged.get("date")):
            missing_slots.append("date")
        time_text = str(merged.get("time") or "").strip()
        if not time_text or not parse_slots(time_text):
            missing_slots.append("time")
        return missing_slots

    if key == "reserve_query":
        if not str(merged.get("labName") or "").strip():
            missing_slots.append("labName")
        date_text = str(merged.get("date") or "").strip()
        if date_text and not _agent_is_valid_date_text(date_text):
            missing_slots.append("date")
        time_text = str(merged.get("time") or "").strip()
        if time_text and not parse_slots(time_text):
            missing_slots.append("time")
        return missing_slots

    if key == "repair_create":
        if not _agent_is_meaningful_repair_description(merged.get("description")):
            missing_slots.append("description")
        has_location = bool(str(merged.get("labName") or "").strip() or str(merged.get("equipmentHint") or "").strip())
        if not has_location:
            missing_slots.append("location")
        return missing_slots
    if key == "reserve_plan_pick":
        plans = _agent_normalize_plan_items(merged.get("plans"))
        selected_plan_id = str(merged.get("selectedPlanId") or "").strip()
        if not plans:
            missing_slots.append("selectedPlanId")
            return missing_slots
        if not selected_plan_id:
            missing_slots.append("selectedPlanId")
            return missing_slots
        selected_plan = _agent_find_plan_by_id(plans, selected_plan_id)
        if not selected_plan:
            missing_slots.append("selectedPlanId")
        return missing_slots

    return missing_slots


def _agent_build_questions_for_missing_slots(missing_slots):
    questions = []
    for key in _normalize_agent_pending_missing_slots(missing_slots):
        questions.append({"key": key, "question": AGENT_PENDING_SLOT_QUESTIONS.get(key, f"请补充 {key}。")})
    return questions


def _agent_build_need_more_info_reply(missing_slots):
    keys = _normalize_agent_pending_missing_slots(missing_slots)
    if not keys:
        return "我需要你补充必要信息。"
    labels = [AGENT_PENDING_SLOT_LABELS.get(key, key) for key in keys]
    first_key = keys[0]
    first_question = AGENT_PENDING_SLOT_QUESTIONS.get(first_key, f"请补充 {first_key}。")
    return f"我需要你补充：{'、'.join(labels)}。{first_question}"


def _agent_multiturn_build_tool_call(intent, slots):
    key = str(intent or "").strip()
    compact_slots = _agent_compact_slots(slots if isinstance(slots, dict) else {})
    if key == "reserve_create":
        return {
            "op": "reserve_create",
            "labName": str(compact_slots.get("labName") or "").strip(),
            "date": str(compact_slots.get("date") or "").strip(),
            "time": str(compact_slots.get("time") or "").strip(),
            "reason": str(compact_slots.get("reason") or "").strip(),
        }
    if key == "reserve_query":
        return {
            "op": "lab_reservation_list",
            "labName": str(compact_slots.get("labName") or "").strip(),
            "date": str(compact_slots.get("date") or "").strip(),
            "time": str(compact_slots.get("time") or "").strip(),
        }
    if key == "repair_create":
        return {
            "op": "repair_create",
            "issueType": str(compact_slots.get("issueType") or "").strip(),
            "description": str(compact_slots.get("description") or "").strip(),
            "labName": str(compact_slots.get("labName") or "").strip(),
            "equipmentHint": str(compact_slots.get("equipmentHint") or "").strip(),
        }
    if key == "reserve_plan_pick":
        selected_plan = _agent_get_selected_plan_from_slots(compact_slots)
        if not selected_plan:
            return {}
        return {
            "op": "reserve_create",
            "labName": str(selected_plan.get("labName") or "").strip(),
            "date": str(selected_plan.get("date") or "").strip(),
            "time": str(selected_plan.get("time") or "").strip(),
            "reason": str(compact_slots.get("reason") or "").strip() or "智能助手推荐方案",
            "selectedPlanId": str(selected_plan.get("planId") or "").strip(),
            "selectedPlan": selected_plan,
        }
    return {}


def _agent_multiturn_build_confirm_reply(intent, slots):
    key = str(intent or "").strip()
    compact_slots = _agent_compact_slots(slots if isinstance(slots, dict) else {})
    if key == "reserve_create":
        reason = str(compact_slots.get("reason") or "").strip() or "未填写"
        return (
            f"确认帮你预约：{compact_slots.get('labName')}，{compact_slots.get('date')} {compact_slots.get('time')}，"
            f"用途：{reason}。回复“确认”继续，或说“修改时间/实验室”。"
        )
    if key == "reserve_query":
        date_text = str(compact_slots.get("date") or "").strip()
        time_text = str(compact_slots.get("time") or "").strip()
        time_part = ""
        if date_text and time_text:
            time_part = f"{date_text} {time_text} 的"
        elif date_text:
            time_part = f"{date_text} 的"
        elif time_text:
            time_part = f"{time_text} 的"
        return (
            f"确认帮你查询：{compact_slots.get('labName')} {time_part}预约记录。"
            "回复“确认”继续，或说“修改实验室/时间”。"
        )
    if key == "repair_create":
        target = str(compact_slots.get("equipmentHint") or "").strip() or str(compact_slots.get("labName") or "").strip() or "未指定"
        return (
            f"确认帮你提交报修：位置 {target}，描述“{compact_slots.get('description')}”。"
            "回复“确认”继续，或说“修改描述/位置”。"
        )
    if key == "reserve_plan_pick":
        selected_plan = _agent_get_selected_plan_from_slots(compact_slots)
        if not selected_plan:
            return "请先选择一个方案，再回复“确认”。"
        reason = str(compact_slots.get("reason") or "").strip() or "未填写"
        return (
            f"确认按方案 {selected_plan.get('planId')} 预约：{selected_plan.get('labName')}，"
            f"{selected_plan.get('date')} {selected_plan.get('time')}，用途：{reason}。"
            "回复“确认”继续，或说“改成方案2”。"
        )
    return "请回复“确认”继续。"


def _agent_build_need_more_info_response(intent, slots, missing_slots):
    compact_slots = _agent_compact_slots(slots if isinstance(slots, dict) else {})
    reply_text = _agent_build_need_more_info_reply(missing_slots)
    extra_payload = {}
    if str(intent or "").strip() == "reserve_plan_pick":
        plans = _agent_normalize_plan_items(compact_slots.get("plans"))
        reply_text = _agent_build_plan_options_text(plans, prefix=str(compact_slots.get("planPrompt") or "").strip())
        extra_payload["plans"] = plans

    pending_payload = _agent_pending_to_public_payload(
        {
            "intent": str(intent or "").strip(),
            "slots": compact_slots,
            "missing_slots": _normalize_agent_pending_missing_slots(missing_slots),
            "state": "collecting",
        }
    )
    extra_payload["questions"] = _agent_build_questions_for_missing_slots(missing_slots)
    extra_payload["pending"] = pending_payload
    return _agent_response(
        code=0,
        msg="need_more_info",
        reply=reply_text,
        action="ask_info",
        extra=extra_payload,
        http_status=200,
    )


def _agent_build_confirm_response(intent, slots):
    tool_name = _agent_multiturn_tool_from_intent(intent)
    params = _agent_multiturn_build_tool_call(intent, slots)
    pending_payload = _agent_pending_to_public_payload(
        {
            "intent": str(intent or "").strip(),
            "slots": _agent_compact_slots(slots if isinstance(slots, dict) else {}),
            "missing_slots": [],
            "state": "confirming",
        }
    )
    return _agent_response(
        code=0,
        msg="ok",
        reply=_agent_multiturn_build_confirm_reply(intent, slots),
        action="confirm",
        extra={
            "meta": {"tool": tool_name, "params": params},
            "pending": pending_payload,
        },
        http_status=200,
    )


def _agent_pending_get(user_name):
    key = _agent_pending_key(user_name)
    if not key:
        return {}
    now_ts = int(time.time())
    timeout_payload = None
    with _AGENT_PENDING_LOCK:
        row = _AGENT_PENDING_CONTEXT.get(key)
        if not row:
            return {}
        normalized = _agent_pending_normalize_row(row)
        expires_at = int(normalized.get("expires_at") or 0)
        if expires_at and expires_at <= now_ts:
            timeout_payload = _AGENT_PENDING_CONTEXT.pop(key, None)
        else:
            _AGENT_PENDING_CONTEXT[key] = normalized
            return dict(normalized)
    if timeout_payload:
        timed_out = _agent_pending_normalize_row(timeout_payload)
        audit_log(
            "agent_pending_clear",
            target_type="agent_pending",
            target_id=key,
            detail={
                "reason": "timeout",
                "intent": str(timed_out.get("intent") or "").strip(),
                "state": str(timed_out.get("state") or "").strip(),
            },
            actor={"username": str(user_name or "").strip()},
        )
    return {}


def _agent_pending_set(user_name, intent, date_text="", time_text="", extra=None, slots=None, missing_slots=None, state="collecting"):
    key = _agent_pending_key(user_name)
    if not key:
        return
    now_ts = int(time.time())
    resolved_state = str(state or "").strip().lower()
    if resolved_state not in AGENT_PENDING_STATE_SET:
        resolved_state = "collecting"
    payload_slots = _agent_compact_slots(slots if isinstance(slots, dict) else {})
    date_val = str(date_text or "").strip()
    time_val = str(time_text or "").strip()
    if date_val:
        payload_slots["date"] = date_val
    if time_val:
        payload_slots["time"] = time_val
    extra_missing = []
    payload = {
        "intent": str(intent or "").strip(),
        "slots": payload_slots,
        "missing_slots": [],
        "state": resolved_state,
        "updated_at": now_ts,
        "expires_at": now_ts + max(60, int(AGENT_PENDING_TTL_SECONDS)),
        "updatedAt": now_ts,
        "expiresAt": now_ts + max(60, int(AGENT_PENDING_TTL_SECONDS)),
    }
    if isinstance(extra, dict):
        extra_missing = extra.get("missing_slots") or extra.get("missingSlots") or []
        extra_state = str(extra.get("state") or "").strip().lower()
        if extra_state in AGENT_PENDING_STATE_SET:
            payload["state"] = extra_state
        for k, v in extra.items():
            key_name = str(k or "").strip()
            if not key_name:
                continue
            if key_name in {"missing_slots", "missingSlots", "state"}:
                continue
            if isinstance(v, str):
                value = v.strip()
                if not value:
                    continue
                payload_slots[key_name] = value
                continue
            if v is None:
                continue
            payload_slots[key_name] = v
    normalized_missing = _normalize_agent_pending_missing_slots(missing_slots)
    if not normalized_missing:
        normalized_missing = _normalize_agent_pending_missing_slots(extra_missing)
    payload["missing_slots"] = normalized_missing
    payload["missingSlots"] = list(normalized_missing)
    for k, v in payload_slots.items():
        payload[k] = v
    normalized = _agent_pending_normalize_row(payload)
    with _AGENT_PENDING_LOCK:
        _AGENT_PENDING_CONTEXT[key] = normalized
    audit_log(
        "agent_pending_set",
        target_type="agent_pending",
        target_id=key,
        detail={
            "intent": str(normalized.get("intent") or "").strip(),
            "state": str(normalized.get("state") or "").strip(),
            "missingSlots": list(normalized.get("missing_slots") or []),
            "slotKeys": sorted(list((normalized.get("slots") or {}).keys())),
        },
        actor={"username": str(user_name or "").strip()},
    )


def _agent_pending_clear(user_name, reason="manual"):
    key = _agent_pending_key(user_name)
    if not key:
        return False
    removed = None
    with _AGENT_PENDING_LOCK:
        removed = _AGENT_PENDING_CONTEXT.pop(key, None)
    if not removed:
        return False
    normalized = _agent_pending_normalize_row(removed)
    audit_log(
        "agent_pending_clear",
        target_type="agent_pending",
        target_id=key,
        detail={
            "reason": str(reason or "manual"),
            "intent": str(normalized.get("intent") or "").strip(),
            "state": str(normalized.get("state") or "").strip(),
        },
        actor={"username": str(user_name or "").strip()},
    )
    return True


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


def _normalize_agent_search_query(text):
    raw = re.sub(r"\s+", " ", str(text or "")).strip()
    if not raw:
        return ""
    cleanup_patterns = [
        r"^(请|麻烦|帮我|给我|替我|你帮我)\s*",
        r"^(联网)?(搜索|搜一下|搜搜|搜一搜|查一下|查查|查一查|查找|检索)\s*",
        r"^(联网)?(帮我)?(搜索|搜一下|查一下)\s*",
    ]
    normalized = raw
    for pattern in cleanup_patterns:
        normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE).strip()
    normalized = normalized.strip("，。！？!?.,；;:：")
    return normalized or raw


def _agent_is_weather_query(text):
    raw = str(text or "").strip()
    if not raw:
        return False
    lower = raw.lower()
    weather_keywords = (
        "天气",
        "气温",
        "温度",
        "降雨",
        "降水",
        "下雨",
        "带伞",
        "雨伞",
        "收衣服",
        "晾衣服",
        "晒衣服",
        "洗车",
        "天气预报",
        "会不会下雨",
        "要不要收",
    )
    if any(token in raw for token in weather_keywords):
        return True
    return bool(re.search(r"\b(weather|forecast|temperature|rain|umbrella|laundry|clothes|drying)\b", lower))


def _agent_weather_advice_type(text):
    raw = str(text or "").strip()
    lower = raw.lower()
    if any(token in raw for token in ("收衣服", "晾衣服", "晒衣服", "洗衣服", "衣服")):
        return "laundry"
    if any(token in raw for token in ("带伞", "雨伞", "伞")) or "umbrella" in lower:
        return "umbrella"
    return "general"


def _extract_weather_location_fallback(text):
    raw = _normalize_agent_search_query(text)
    if not raw:
        return ""
    patterns = [
        r"([一-龥]{2,12})(?:今天|今日|明天|后天|今晚|本周末|这周末|周末)?(?:的)?天气",
        r"([一-龥]{2,12})(?:今天|今日|明天|后天|今晚|本周末|这周末|周末)?(?:会不会|会|是否|有没有)?(?:下雨|降雨|降水)",
        r"([一-龥]{2,12})(?:今天|今日|明天|后天|今晚|本周末|这周末|周末)?(?:适合|要不要|需不需要)?(?:收衣服|带伞)",
    ]
    for pattern in patterns:
        matched = re.search(pattern, raw)
        if matched:
            location = str(matched.group(1) or "").strip()
            if location.endswith("会") and "会下雨" in raw:
                location = location[:-1]
            return location
    return ""


def _extract_weather_time_scope_fallback(text):
    raw = str(text or "").strip()
    if any(token in raw for token in ("后天",)):
        return "后天"
    if any(token in raw for token in ("明天",)):
        return "明天"
    if any(token in raw for token in ("今晚", "今天晚上", "今夜")):
        return "今晚"
    if any(token in raw for token in ("本周末", "这周末", "周末")):
        return "周末"
    return "今天"


def _weather_time_scope_to_english(text):
    raw = str(text or "").strip()
    if raw == "明天":
        return "tomorrow"
    if raw == "后天":
        return "day after tomorrow"
    if raw == "今晚":
        return "tonight"
    if raw == "周末":
        return "this weekend"
    return "today"


def _call_siliconflow_weather_search_plan(text):
    system_prompt = (
        "你是天气联网搜索规划器。"
        "请把用户的中文天气问题改写成适合搜索引擎的英文短查询，并抽取地点与时间范围。"
        "只输出严格 JSON，不要输出 JSON 以外任何字符。"
        'JSON schema 固定为：{"locationZh":"","timeScopeZh":"","searchQueryEn":"","adviceType":"general|laundry|umbrella"}。'
        "searchQueryEn 必须是简洁英文搜索词，优先使用地点的拼音或英文地名，并包含 weather、forecast、rain 等必要词。"
        "若用户问是否收衣服，adviceType 输出 laundry；若问是否带伞，输出 umbrella；否则输出 general。"
        "timeScopeZh 只允许：今天、今晚、明天、后天、周末。没有明确提及时默认今天。"
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
            raise BizError("weather plan parse failed", 502)
        try:
            parsed = json.loads(extracted)
        except Exception:
            raise BizError("weather plan parse failed", 502)
    if not isinstance(parsed, dict):
        raise BizError("weather plan invalid", 502)
    advice_type = str(parsed.get("adviceType") or "general").strip().lower()
    if advice_type not in {"general", "laundry", "umbrella"}:
        advice_type = "general"
    time_scope = str(parsed.get("timeScopeZh") or "").strip()
    if time_scope not in {"今天", "今晚", "明天", "后天", "周末"}:
        time_scope = "今天"
    return {
        "locationZh": str(parsed.get("locationZh") or "").strip()[:32],
        "timeScopeZh": time_scope,
        "searchQueryEn": re.sub(r"\s+", " ", str(parsed.get("searchQueryEn") or "").strip())[:160],
        "adviceType": advice_type,
    }


def _build_weather_search_plan(text):
    fallback_location = _extract_weather_location_fallback(text)
    fallback_time_scope = _extract_weather_time_scope_fallback(text)
    fallback_advice_type = _agent_weather_advice_type(text)
    fallback_query = ""
    if fallback_location:
        fallback_query = f"{fallback_location} weather {_weather_time_scope_to_english(fallback_time_scope)} rain forecast"
    else:
        fallback_query = f"{_normalize_agent_search_query(text)} weather forecast"
    fallback_plan = {
        "locationZh": fallback_location,
        "timeScopeZh": fallback_time_scope,
        "searchQueryEn": re.sub(r"\s+", " ", fallback_query).strip()[:160],
        "adviceType": fallback_advice_type,
    }
    if not SILICONFLOW_API_KEY:
        return fallback_plan
    try:
        planned = _call_siliconflow_weather_search_plan(text)
    except Exception:
        planned = {}
    plan = dict(fallback_plan)
    if isinstance(planned, dict):
        if str(planned.get("locationZh") or "").strip():
            plan["locationZh"] = str(planned.get("locationZh") or "").strip()[:32]
        if str(planned.get("timeScopeZh") or "").strip():
            plan["timeScopeZh"] = str(planned.get("timeScopeZh") or "").strip()
        if str(planned.get("searchQueryEn") or "").strip():
            plan["searchQueryEn"] = re.sub(r"\s+", " ", str(planned.get("searchQueryEn") or "").strip())[:160]
        if str(planned.get("adviceType") or "").strip() in {"general", "laundry", "umbrella"}:
            plan["adviceType"] = str(planned.get("adviceType") or "").strip()
    query_en = re.sub(r"\s+", " ", str(plan.get("searchQueryEn") or "").strip())
    lower_query_en = query_en.lower()
    if "weather" not in lower_query_en:
        query_en = f"{query_en} weather".strip()
        lower_query_en = query_en.lower()
    if not any(token in lower_query_en for token in ("today", "tomorrow", "tonight", "weekend", "forecast")):
        query_en = f"{query_en} {_weather_time_scope_to_english(plan.get('timeScopeZh'))} forecast".strip()
        lower_query_en = query_en.lower()
    if "forecast" not in lower_query_en:
        query_en = f"{query_en} forecast".strip()
    plan["searchQueryEn"] = re.sub(r"\s+", " ", query_en).strip()[:160]
    if not str(plan.get("searchQueryEn") or "").strip():
        plan["searchQueryEn"] = fallback_plan["searchQueryEn"]
    return plan


def _http_get_json(url, timeout_seconds=10):
    req = urlrequest.Request(
        str(url or ""),
        headers={
            "User-Agent": "ai-lab-agent/1.0",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlrequest.urlopen(req, timeout=max(3, int(timeout_seconds or 10))) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="ignore")
        except Exception:
            detail = ""
        raise BizError(f"http error: {e.code} {detail[:200]}", 502)
    except URLError as e:
        raise BizError(f"connect error: {e}", 502)
    except Exception as e:
        raise BizError(f"request failed: {e}", 502)
    try:
        return json.loads(raw)
    except Exception:
        raise BizError("response is not json", 502)


def _open_meteo_weather_code_to_zh(code):
    mapping = {
        0: "晴",
        1: "晴",
        2: "多云",
        3: "阴",
        45: "雾",
        48: "雾凇",
        51: "小毛毛雨",
        53: "毛毛雨",
        55: "浓毛毛雨",
        56: "冻毛毛雨",
        57: "强冻毛毛雨",
        61: "小雨",
        63: "中雨",
        65: "大雨",
        66: "冻雨",
        67: "强冻雨",
        71: "小雪",
        73: "中雪",
        75: "大雪",
        77: "雪粒",
        80: "阵雨",
        81: "较强阵雨",
        82: "强阵雨",
        85: "阵雪",
        86: "强阵雪",
        95: "雷暴",
        96: "雷暴伴小冰雹",
        99: "雷暴伴大冰雹",
    }
    try:
        return mapping.get(int(code))
    except Exception:
        return ""


def _open_meteo_is_precipitation_code(code):
    try:
        val = int(code)
    except Exception:
        return False
    return val in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99}


def _open_meteo_target_index(time_scope_zh, daily_time_list):
    time_scope = str(time_scope_zh or "").strip() or "今天"
    items = [str(x or "").strip() for x in (daily_time_list or []) if str(x or "").strip()]
    if not items:
        return 0
    if time_scope == "明天":
        return 1 if len(items) >= 2 else 0
    if time_scope == "后天":
        return 2 if len(items) >= 3 else min(1, len(items) - 1)
    if time_scope == "周末":
        for idx, date_text in enumerate(items):
            dt = _to_datetime(f"{date_text} 00:00:00")
            if dt and dt.weekday() >= 5:
                return idx
    return 0


def _call_open_meteo_weather(location_text, time_scope_zh="今天"):
    location = str(location_text or "").strip()
    if not location:
        raise BizError("weather location required", 400)

    geo_query = urlparse.urlencode(
        {
            "name": location,
            "count": 5,
            "language": "zh",
            "format": "json",
            "countryCode": "CN",
        }
    )
    geo_url = f"{OPEN_METEO_GEOCODING_BASE_URL}/v1/search?{geo_query}"
    geo_payload = _http_get_json(geo_url, timeout_seconds=OPEN_METEO_TIMEOUT_SECONDS)
    geo_results = geo_payload.get("results") if isinstance(geo_payload.get("results"), list) else []
    if not geo_results:
        raise BizError("weather location not found", 404)

    best = None
    for item in geo_results:
        row = item if isinstance(item, dict) else {}
        country_code = str(row.get("country_code") or "").strip().upper()
        if country_code == "CN":
            best = row
            break
    if best is None:
        best = geo_results[0] if isinstance(geo_results[0], dict) else {}

    latitude = best.get("latitude")
    longitude = best.get("longitude")
    if latitude in (None, "") or longitude in (None, ""):
        raise BizError("weather coordinates missing", 502)

    forecast_query = urlparse.urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "Asia/Shanghai",
            "forecast_days": 7,
            "current": "temperature_2m,precipitation,rain,showers,snowfall,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,rain_sum,showers_sum,snowfall_sum,wind_speed_10m_max",
        }
    )
    forecast_url = f"{OPEN_METEO_FORECAST_BASE_URL}/v1/forecast?{forecast_query}"
    forecast_payload = _http_get_json(forecast_url, timeout_seconds=OPEN_METEO_TIMEOUT_SECONDS)

    daily = forecast_payload.get("daily") if isinstance(forecast_payload.get("daily"), dict) else {}
    current = forecast_payload.get("current") if isinstance(forecast_payload.get("current"), dict) else {}
    target_index = _open_meteo_target_index(time_scope_zh, daily.get("time"))
    day_date = str((daily.get("time") or [None])[target_index] or "")
    weather_code = (daily.get("weather_code") or [None])[target_index] if isinstance(daily.get("weather_code"), list) else None
    temp_max = (daily.get("temperature_2m_max") or [None])[target_index] if isinstance(daily.get("temperature_2m_max"), list) else None
    temp_min = (daily.get("temperature_2m_min") or [None])[target_index] if isinstance(daily.get("temperature_2m_min"), list) else None
    precip_prob = (daily.get("precipitation_probability_max") or [None])[target_index] if isinstance(daily.get("precipitation_probability_max"), list) else None
    precip_sum = (daily.get("precipitation_sum") or [None])[target_index] if isinstance(daily.get("precipitation_sum"), list) else None
    rain_sum = (daily.get("rain_sum") or [None])[target_index] if isinstance(daily.get("rain_sum"), list) else None
    showers_sum = (daily.get("showers_sum") or [None])[target_index] if isinstance(daily.get("showers_sum"), list) else None
    snowfall_sum = (daily.get("snowfall_sum") or [None])[target_index] if isinstance(daily.get("snowfall_sum"), list) else None
    wind_max = (daily.get("wind_speed_10m_max") or [None])[target_index] if isinstance(daily.get("wind_speed_10m_max"), list) else None

    return {
        "locationName": str(best.get("name") or location).strip(),
        "admin1": str(best.get("admin1") or "").strip(),
        "country": str(best.get("country") or "").strip(),
        "latitude": latitude,
        "longitude": longitude,
        "timezone": str(forecast_payload.get("timezone") or "Asia/Shanghai").strip(),
        "date": day_date,
        "timeScopeZh": str(time_scope_zh or "").strip() or "今天",
        "weatherCode": weather_code,
        "conditionZh": _open_meteo_weather_code_to_zh(weather_code),
        "tempMax": temp_max,
        "tempMin": temp_min,
        "precipitationProbabilityMax": precip_prob,
        "precipitationSum": precip_sum,
        "rainSum": rain_sum,
        "showersSum": showers_sum,
        "snowfallSum": snowfall_sum,
        "windSpeedMax": wind_max,
        "current": current,
        "forecastUrl": forecast_url,
        "geocodingUrl": geo_url,
    }


def _agent_execute_weather_lookup(text):
    plan = _build_weather_search_plan(text)
    location_zh = str(plan.get("locationZh") or "").strip() or _extract_weather_location_fallback(text)
    if not location_zh:
        raise BizError("weather location required", 400)
    weather_data = _call_open_meteo_weather(location_zh, plan.get("timeScopeZh"))
    source_content = (
        f"{weather_data.get('locationName') or location_zh} {weather_data.get('timeScopeZh') or '今天'} "
        f"{weather_data.get('conditionZh') or '天气'}，"
        f"最低 {weather_data.get('tempMin')}℃，最高 {weather_data.get('tempMax')}℃，"
        f"降水概率 {weather_data.get('precipitationProbabilityMax')}%。"
    )
    return {
        "query": location_zh,
        "topic": "weather",
        "results": [
            {
                "title": f"Open-Meteo 天气预报：{weather_data.get('locationName') or location_zh}",
                "url": str(weather_data.get("forecastUrl") or "").strip(),
                "content": source_content,
                "score": 1.0,
                "publishedDate": str(weather_data.get("date") or "").strip(),
            }
        ],
        "weatherPlan": plan,
        "weatherData": weather_data,
    }


def _agent_should_use_web_search(text):
    raw = str(text or "").strip()
    if not raw:
        return False
    lower = raw.lower()
    if _agent_is_weather_query(raw):
        return True
    explicit_keywords = (
        "联网搜索",
        "联网查",
        "联网搜",
        "帮我查",
        "帮我搜",
        "查一下",
        "搜一下",
        "搜索",
        "检索",
        "官网",
        "官方网站",
        "官方文档",
        "文档链接",
        "网址",
        "链接",
    )
    fresh_keywords = (
        "最新",
        "最近",
        "今日",
        "今天",
        "本周",
        "本月",
        "今年",
        "新闻",
        "头条",
        "快讯",
        "发布",
        "公告",
        "版本",
        "更新",
        "股价",
        "价格",
        "汇率",
        "比分",
        "战报",
    )
    if any(token in raw for token in explicit_keywords):
        return True
    if any(token in raw for token in fresh_keywords):
        return True
    if re.search(r"\b(search|latest|news|today|recent|official|docs?|documentation|release|update|price|stock|score|api)\b", lower):
        return True
    return False


def _agent_get_web_search_options(text):
    raw = str(text or "").strip()
    lower = raw.lower()
    if _agent_is_weather_query(raw):
        return {
            "topic": "general",
            "searchDepth": "advanced",
            "timeRange": "",
            "maxResults": min(4, int(AGENT_WEB_SEARCH_MAX_RESULTS)),
            "includeDomains": ["weather.com.cn", "nmc.cn"],
            "country": "china",
        }
    doc_like = any(token in raw for token in ("官网", "官方网站", "官方文档", "文档", "API", "api", "接口", "教程", "怎么用", "用法"))
    finance_like = any(token in raw for token in ("股价", "财报", "市值", "汇率", "币价", "价格")) or bool(
        re.search(r"\b(stock|finance|market|earnings|forex|crypto|price)\b", lower)
    )
    news_like = any(token in raw for token in ("新闻", "头条", "快讯", "最新", "最近", "今日", "今天", "昨晚", "昨日", "本周", "本月", "今年", "发布", "公告", "比分", "战报")) or bool(
        re.search(r"\b(latest|news|today|recent|release|update|score)\b", lower)
    )

    topic = "general"
    search_depth = "basic"
    time_range = ""

    if doc_like:
        topic = "general"
        search_depth = "advanced"
    elif finance_like:
        topic = "finance"
        search_depth = "basic"
    elif news_like:
        topic = "news"
        search_depth = "basic"
        time_range = "month" if any(token in raw for token in ("本月", "今年")) else "week"

    return {
        "topic": topic,
        "searchDepth": search_depth,
        "timeRange": time_range,
        "maxResults": int(AGENT_WEB_SEARCH_MAX_RESULTS),
    }


def _call_tavily_search(query_text, options=None):
    if not TAVILY_API_KEY:
        raise BizError("TAVILY_API_KEY not configured", 500)

    search_query = _normalize_agent_search_query(query_text)
    if not search_query:
        raise BizError("search query required", 400)

    opts = options if isinstance(options, dict) else {}
    topic = str(opts.get("topic") or "general").strip().lower() or "general"
    search_depth = str(opts.get("searchDepth") or "basic").strip().lower() or "basic"
    time_range = str(opts.get("timeRange") or "").strip().lower()
    country = str(opts.get("country") or "").strip().lower()
    max_results = _to_int_or_none(opts.get("maxResults")) or int(AGENT_WEB_SEARCH_MAX_RESULTS)
    max_results = max(1, min(8, int(max_results)))
    include_domains = [str(x or "").strip() for x in (opts.get("includeDomains") or []) if str(x or "").strip()]
    exclude_domains = [str(x or "").strip() for x in (opts.get("excludeDomains") or []) if str(x or "").strip()]

    payload = {
        "query": search_query,
        "topic": topic,
        "search_depth": search_depth,
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
        "include_favicon": False,
    }
    if time_range:
        payload["time_range"] = time_range
    if country and topic == "general":
        payload["country"] = country
    if include_domains:
        payload["include_domains"] = include_domains[:8]
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains[:8]

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(
        f"{TAVILY_BASE_URL}/search",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TAVILY_API_KEY}",
            "User-Agent": "ai-lab-agent/1.0",
        },
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=max(3, int(TAVILY_TIMEOUT_SECONDS))) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="ignore")
        except Exception:
            detail = ""
        raise BizError(f"tavily http error: {e.code} {detail[:200]}", 502)
    except URLError as e:
        raise BizError(f"tavily connect error: {e}", 502)
    except Exception as e:
        raise BizError(f"tavily request failed: {e}", 502)

    try:
        api_result = json.loads(raw)
    except Exception:
        raise BizError("tavily response is not json", 502)

    normalized_results = []
    for item in api_result.get("results") or []:
        row = item if isinstance(item, dict) else {}
        url = str(row.get("url") or "").strip()
        title = re.sub(r"\s+", " ", str(row.get("title") or "").strip())
        content = re.sub(r"\s+", " ", str(row.get("content") or "").strip())
        published_date = str(row.get("published_date") or row.get("publishedDate") or "").strip()
        if not url and not title and not content:
            continue
        try:
            score = round(float(row.get("score") or 0), 4)
        except Exception:
            score = 0.0
        normalized_results.append(
            {
                "title": title[:200],
                "url": url[:500],
                "content": content[:1200],
                "score": score,
                "publishedDate": published_date[:40],
            }
        )

    return {
        "query": search_query,
        "topic": topic,
        "searchDepth": search_depth,
        "timeRange": time_range,
        "results": normalized_results,
        "responseTime": api_result.get("response_time"),
        "requestId": str(api_result.get("request_id") or "").strip(),
        "answer": str(api_result.get("answer") or "").strip(),
    }


def _build_agent_web_search_evidence(search_payload):
    payload = search_payload if isinstance(search_payload, dict) else {}
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    blocks = []
    for idx, item in enumerate(results[: int(AGENT_WEB_SEARCH_MAX_RESULTS)], start=1):
        row = item if isinstance(item, dict) else {}
        title = str(row.get("title") or row.get("url") or f"结果{idx}").strip()
        url = str(row.get("url") or "").strip()
        content = str(row.get("content") or "").strip()
        published_date = str(row.get("publishedDate") or "").strip()
        meta_bits = []
        if published_date:
            meta_bits.append(f"日期：{published_date}")
        if row.get("score") not in (None, ""):
            meta_bits.append(f"相关度：{row.get('score')}")
        meta_line = f"\n元数据：{' | '.join(meta_bits)}" if meta_bits else ""
        blocks.append(f"[{idx}] 标题：{title}\n链接：{url}{meta_line}\n摘要：{content}")
    return "\n\n".join(blocks)


def _build_agent_weather_search_evidence(search_payload):
    payload = search_payload if isinstance(search_payload, dict) else {}
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    blocks = []
    for idx, item in enumerate(results[:2], start=1):
        row = item if isinstance(item, dict) else {}
        title = str(row.get("title") or row.get("url") or f"结果{idx}").strip()
        url = str(row.get("url") or "").strip()
        content = re.sub(r"\s+", " ", str(row.get("content") or "").strip())[:700]
        blocks.append(f"[{idx}] 标题：{title}\n链接：{url}\n摘要：{content}")
    return "\n\n".join(blocks)


def _build_agent_web_search_sources(search_payload):
    payload = search_payload if isinstance(search_payload, dict) else {}
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    lines = []
    for idx, item in enumerate(results[: int(AGENT_WEB_SEARCH_MAX_RESULTS)], start=1):
        row = item if isinstance(item, dict) else {}
        title = str(row.get("title") or row.get("url") or f"结果{idx}").strip()
        url = str(row.get("url") or "").strip()
        published_date = str(row.get("publishedDate") or "").strip()
        suffix = f"（{published_date}）" if published_date else ""
        if not url:
            continue
        lines.append(f"[{idx}] {title}{suffix} - {url}")
    return "\n".join(lines)


def _build_agent_web_search_fallback_reply(search_payload):
    payload = search_payload if isinstance(search_payload, dict) else {}
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    if not results:
        return "已尝试联网搜索，但没有找到足够相关的网页结果。你可以换个更具体的关键词再试。"

    summary_lines = []
    for idx, item in enumerate(results[:3], start=1):
        row = item if isinstance(item, dict) else {}
        title = str(row.get("title") or row.get("url") or f"结果{idx}").strip()
        content = str(row.get("content") or "").strip()
        published_date = str(row.get("publishedDate") or "").strip()
        prefix = f"{idx}. {title}"
        if published_date:
            prefix += f"（{published_date}）"
        if content:
            summary_lines.append(f"{prefix}：{content}")
        else:
            summary_lines.append(prefix)
    return "我查到以下网页结果，先给你一个精简整理：\n" + "\n".join(summary_lines)


def _call_siliconflow_grounded_web_reply(text, search_payload):
    evidence_text = _build_agent_web_search_evidence(search_payload)
    if not evidence_text:
        return ""

    today_text = datetime.now().strftime("%Y-%m-%d")
    system_prompt = (
        "你是一个中文联网助手，运行在高校实验室管理系统中。"
        "你必须严格基于提供的搜索结果回答，不能补造搜索结果中没有明确支持的事实。"
        "如果证据不足，请明确说“搜索结果不足以确认”。"
        "涉及时间敏感信息时，请优先写出具体日期。"
        "回答保持简洁、直接、可执行。"
        "不要输出固定寒暄，不要附加来源列表。"
    )
    user_prompt = (
        f"今天日期：{today_text}\n"
        f"用户问题：{str(text or '').strip()}\n"
        f"搜索查询：{str((search_payload or {}).get('query') or '').strip()}\n"
        f"搜索结果：\n{evidence_text}\n\n"
        "请基于以上结果直接回答用户问题。"
    )
    content = _call_siliconflow_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return str(content or "").strip()


def _call_siliconflow_grounded_weather_reply(text, search_payload, weather_plan=None):
    evidence_text = _build_agent_weather_search_evidence(search_payload)
    if not evidence_text:
        return ""

    plan = weather_plan if isinstance(weather_plan, dict) else {}
    location_zh = str(plan.get("locationZh") or "").strip()
    time_scope_zh = str(plan.get("timeScopeZh") or "").strip() or "今天"
    advice_type = str(plan.get("adviceType") or "general").strip().lower() or "general"
    advice_instruction = "最后给出是否建议收衣服的结论。"
    if advice_type == "umbrella":
        advice_instruction = "最后给出是否建议带伞的结论。"
    elif advice_type == "general":
        advice_instruction = "如果问题没有要求生活建议，就只给天气结论。"

    system_prompt = (
        "你是中文天气助手。"
        "你必须严格基于提供的搜索结果回答，不能编造天气数据。"
        "先给出地点与时间范围的天气摘要，再给出简短建议。"
        "如果搜索结果明确出现 sunny、clear、cloudy 等无雨信号，可以据此判断短时内通常不必收衣服或带伞；"
        "如果出现 rain、shower、thunderstorm、drizzle、sleet、snow 等降水信号，就应建议收衣服或带伞。"
        "如果证据不足，请明确说明不确定，但仍总结已知天气。"
        "回答保持 2 到 4 句，简洁直接，不要附加来源列表。"
    )
    user_prompt = (
        f"用户问题：{str(text or '').strip()}\n"
        f"地点：{location_zh or '未明确'}\n"
        f"时间范围：{time_scope_zh}\n"
        f"搜索查询：{str((search_payload or {}).get('query') or '').strip()}\n"
        f"要求：{advice_instruction}\n"
        f"搜索结果：\n{evidence_text}\n\n"
        "请基于这些结果回答。"
    )
    content = _call_siliconflow_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )
    return str(content or "").strip()


def _build_weather_reply_fallback(text, search_payload, weather_plan=None):
    payload = search_payload if isinstance(search_payload, dict) else {}
    plan = weather_plan if isinstance(weather_plan, dict) else {}
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    if not results:
        return "已尝试查询天气，但没有找到足够可靠的天气网页结果。"

    primary_row = None
    for item in results:
        row = item if isinstance(item, dict) else {}
        url = str(row.get("url") or "").strip().lower()
        if "weather.com.cn" in url or "nmc.cn" in url:
            primary_row = row
            break
    if primary_row is None:
        primary_row = results[0] if isinstance(results[0], dict) else {}
    combined = f"{str(primary_row.get('title') or '').strip()} {str(primary_row.get('content') or '').strip()}".lower()
    location_zh = str(plan.get("locationZh") or "").strip()
    time_scope_zh = str(plan.get("timeScopeZh") or "").strip() or "今天"
    advice_type = str(plan.get("adviceType") or _agent_weather_advice_type(text)).strip().lower() or "general"
    rain_like = bool(
        re.search(r"\brain\b|\brainy\b|\bshowers?\b|\bdrizzle\b|\bstorm\b|\bthunderstorms?\b|\bsleet\b|\bsnow\b", combined)
    ) or any(token in combined for token in ("小雨", "中雨", "大雨", "暴雨", "阵雨", "雷雨", "降雨", "有雨"))
    dry_like = bool(
        re.search(r"\bsunny\b|\bclear\b|\bcloudy\b|\brainless\b|\bno umbrellas?\b|\bwithout an umbrella\b", combined)
    ) or any(token in combined for token in ("晴", "多云", "阴"))
    location_text = location_zh or "当地"
    summary = f"{location_text}{time_scope_zh}天气已查到相关结果。"
    if advice_type == "laundry":
        if rain_like:
            return f"{summary} 搜索结果里有降雨信号，建议把衣服收起来。"
        if dry_like:
            return f"{summary} 结果以晴天或多云为主，暂时看不出明显降雨信号，一般不用急着收衣服。"
        return f"{summary} 但降雨信息不够明确，是否要收衣服还不能完全确定。"
    if advice_type == "umbrella":
        if rain_like:
            return f"{summary} 搜索结果里有降雨信号，建议带伞。"
        if dry_like:
            return f"{summary} 结果以晴天或多云为主，暂时看不出明显降雨信号，一般不用特意带伞。"
        return f"{summary} 但降雨信息不够明确，是否要带伞还不能完全确定。"
    if rain_like:
        return f"{summary} 搜索结果提示有降雨相关信号。"
    if dry_like:
        return f"{summary} 搜索结果显示以晴天或多云为主。"
    return summary


def _extract_primary_weather_result(search_payload):
    payload = search_payload if isinstance(search_payload, dict) else {}
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    for item in results:
        row = item if isinstance(item, dict) else {}
        url = str(row.get("url") or "").strip().lower()
        if "weather.com.cn" in url or "nmc.cn" in url:
            return row
    return results[0] if results and isinstance(results[0], dict) else {}


def _weather_condition_to_zh(condition_text):
    raw = str(condition_text or "").strip().lower()
    mapping = [
        ("thunderstorm", "雷阵雨"),
        ("heavy rain", "大雨"),
        ("moderate rain", "中雨"),
        ("light rain", "小雨"),
        ("drizzle", "毛毛雨"),
        ("shower", "阵雨"),
        ("snow", "降雪"),
        ("sleet", "雨夹雪"),
        ("overcast", "阴天"),
        ("cloudy", "多云"),
        ("clear", "晴"),
        ("sunny", "晴"),
    ]
    for key, label in mapping:
        if key in raw:
            return label
    return ""


def _extract_weather_snapshot(search_payload, weather_plan=None):
    row = _extract_primary_weather_result(search_payload)
    content = str((row or {}).get("content") or "").strip()
    title = str((row or {}).get("title") or "").strip()
    full_text = f"{title} {content}"
    temperatures = []
    for matched in re.findall(r"(-?\d{1,2})℃", full_text):
        try:
            temperatures.append(int(matched))
        except Exception:
            continue
    condition_hits = []
    for pattern in (
        "Thunderstorm",
        "Heavy rain",
        "Moderate rain",
        "Light rain",
        "Drizzle",
        "Shower",
        "Snow",
        "Sleet",
        "Overcast",
        "Cloudy",
        "Clear",
        "Sunny",
    ):
        if re.search(rf"\b{re.escape(pattern)}\b", full_text, flags=re.IGNORECASE):
            condition_hits.append(pattern)
    condition_zh = ""
    if condition_hits:
        seen = []
        for item in condition_hits:
            label = _weather_condition_to_zh(item)
            if label and label not in seen:
                seen.append(label)
        if len(seen) >= 2 and {"晴", "多云"}.issubset(set(seen)):
            condition_zh = "晴到多云"
        elif seen:
            condition_zh = seen[0]
    rain_like = bool(
        re.search(r"\brain\b|\brainy\b|\bshowers?\b|\bdrizzle\b|\bstorm\b|\bthunderstorms?\b|\bsleet\b|\bsnow\b", full_text.lower())
    ) or any(token in full_text for token in ("小雨", "中雨", "大雨", "暴雨", "阵雨", "雷雨", "降雨", "有雨"))
    dry_like = bool(re.search(r"\bsunny\b|\bclear\b|\bcloudy\b|\brainless\b|\bno umbrellas?\b|\bwithout an umbrella\b", full_text.lower())) or any(
        token in full_text for token in ("晴", "多云", "阴")
    )
    return {
        "row": row,
        "minTemp": min(temperatures) if temperatures else None,
        "maxTemp": max(temperatures) if temperatures else None,
        "conditionZh": condition_zh,
        "rainLike": rain_like,
        "dryLike": dry_like,
    }


def _build_weather_summary_reply(text, search_payload, weather_plan=None):
    plan = weather_plan if isinstance(weather_plan, dict) else {}
    location_zh = str(plan.get("locationZh") or "").strip() or "当地"
    time_scope_zh = str(plan.get("timeScopeZh") or "").strip() or "今天"
    advice_type = str(plan.get("adviceType") or _agent_weather_advice_type(text)).strip().lower() or "general"
    payload = search_payload if isinstance(search_payload, dict) else {}
    weather_data = payload.get("weatherData") if isinstance(payload.get("weatherData"), dict) else {}
    snapshot = _extract_weather_snapshot(search_payload, weather_plan)
    condition_zh = str(weather_data.get("conditionZh") or snapshot.get("conditionZh") or "").strip()
    min_temp = weather_data.get("tempMin") if weather_data.get("tempMin") not in (None, "") else snapshot.get("minTemp")
    max_temp = weather_data.get("tempMax") if weather_data.get("tempMax") not in (None, "") else snapshot.get("maxTemp")
    temp_text = ""
    if min_temp is not None and max_temp is not None:
        low = min(int(round(float(min_temp))), int(round(float(max_temp))))
        high = max(int(round(float(min_temp))), int(round(float(max_temp))))
        temp_text = f"，参考气温约 {low}℃~{high}℃"
    elif max_temp is not None:
        temp_text = f"，参考气温约 {int(round(float(max_temp)))}℃"
    summary = f"{location_zh}{time_scope_zh}"
    if condition_zh:
        summary += f"以{condition_zh}为主"
    else:
        summary += "已查到天气结果"
    summary += temp_text + "。"

    precip_prob = weather_data.get("precipitationProbabilityMax")
    precip_sum = weather_data.get("precipitationSum")
    rain_sum = weather_data.get("rainSum")
    showers_sum = weather_data.get("showersSum")
    snowfall_sum = weather_data.get("snowfallSum")
    weather_code = weather_data.get("weatherCode")
    rain_like = bool(snapshot.get("rainLike"))
    if precip_prob not in (None, ""):
        try:
            rain_like = rain_like or float(precip_prob) >= 35
        except Exception:
            pass
    for value in (precip_sum, rain_sum, showers_sum, snowfall_sum):
        try:
            if value is not None and float(value) > 0:
                rain_like = True
        except Exception:
            continue
    rain_like = rain_like or _open_meteo_is_precipitation_code(weather_code)
    dry_like = bool(snapshot.get("dryLike")) or (not rain_like and str(condition_zh or "") in {"晴", "多云", "晴到多云", "阴", "雾"})
    if not dry_like and not rain_like and precip_prob not in (None, ""):
        try:
            dry_like = float(precip_prob) <= 15
        except Exception:
            dry_like = dry_like
    if advice_type == "laundry":
        if rain_like and not dry_like:
            return f"{summary} 搜索结果里有降雨信号，建议把衣服收起来。"
        if dry_like:
            return f"{summary} 暂时看不出明显降雨信号，一般不用急着收衣服。"
        return f"{summary} 但降雨信息不够明确，是否要收衣服还不能完全确定。"
    if advice_type == "umbrella":
        if rain_like and not dry_like:
            return f"{summary} 搜索结果里有降雨信号，建议带伞。"
        if dry_like:
            return f"{summary} 暂时看不出明显降雨信号，一般不用特意带伞。"
        return f"{summary} 但降雨信息不够明确，是否要带伞还不能完全确定。"
    if rain_like and not dry_like:
        return f"{summary} 搜索结果提示有降雨相关信号。"
    if dry_like:
        return f"{summary} 暂时看不出明显降雨信号。"
    return summary


def _agent_execute_weather_search(text):
    plan = _build_weather_search_plan(text)
    options = _agent_get_web_search_options(text)
    query_text = str(plan.get("searchQueryEn") or "").strip() or _normalize_agent_search_query(text)
    try:
        payload = _call_tavily_search(query_text, options)
    except BizError as e:
        if "Query is invalid." in str(e.msg or ""):
            fallback_location = _extract_weather_location_fallback(text)
            fallback_time_scope = _extract_weather_time_scope_fallback(text)
            fallback_query = (
                f"{fallback_location} weather {_weather_time_scope_to_english(fallback_time_scope)} rain forecast"
                if fallback_location
                else f"{_normalize_agent_search_query(text)} weather forecast"
            )
            payload = _call_tavily_search(fallback_query, options)
            plan["searchQueryEn"] = fallback_query
        else:
            raise
    if not isinstance(payload.get("results"), list) or len(payload.get("results") or []) == 0:
        fallback_location = _extract_weather_location_fallback(text) or str(plan.get("locationZh") or "").strip()
        fallback_time_scope = str(plan.get("timeScopeZh") or "").strip() or _extract_weather_time_scope_fallback(text)
        fallback_query = (
            f"{fallback_location} weather {_weather_time_scope_to_english(fallback_time_scope)} forecast"
            if fallback_location
            else f"{_normalize_agent_search_query(text)} weather forecast"
        )
        payload = _call_tavily_search(fallback_query, options)
        plan["searchQueryEn"] = fallback_query
    payload["weatherPlan"] = plan
    return payload


def _normalize_repair_triage_issue_type(value, fallback="other"):
    raw = str(value or "").strip().lower()
    mapped = REPAIR_TRIAGE_ISSUE_ALIAS.get(raw, raw)
    if mapped not in REPAIR_TRIAGE_ISSUE_SET:
        mapped = str(fallback or "other").strip().lower()
    if mapped not in REPAIR_TRIAGE_ISSUE_SET:
        mapped = "other"
    return mapped


def _normalize_repair_triage_priority(value, fallback="P2"):
    raw = str(value or "").strip().upper()
    if raw not in REPAIR_TRIAGE_PRIORITY_SET:
        raw = str(fallback or "P2").strip().upper()
    if raw not in REPAIR_TRIAGE_PRIORITY_SET:
        raw = "P2"
    return raw


def _normalize_repair_triage_confidence(value):
    try:
        n = float(value)
    except Exception:
        n = 0.0
    if n < 0:
        n = 0.0
    if n > 1:
        n = 1.0
    return round(n, 4)


def _normalize_repair_triage_suggestions(value):
    items = []
    if isinstance(value, list):
        for item in value:
            text = str(item or "").strip()
            if not text:
                continue
            items.append(text)
    elif isinstance(value, str):
        raw = str(value or "").strip()
        if raw:
            parts = re.split(r"[;\n；]+", raw)
            for part in parts:
                text = str(part or "").strip()
                if text:
                    items.append(text)
    dedup = []
    seen = set()
    for item in items:
        text = re.sub(r"\s+", " ", item).strip()
        if not text:
            continue
        if len(text) > 120:
            text = text[:120]
        if text in seen:
            continue
        seen.add(text)
        dedup.append(text)
        if len(dedup) >= 5:
            break
    return dedup


def _normalize_repair_triage_short_text(value, max_len=255):
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return ""
    if len(text) > int(max_len):
        text = text[: int(max_len)]
    return text


def _normalize_repair_triage_possible_causes(value):
    items = _normalize_repair_triage_suggestions(value)
    return items[:4]


def _normalize_repair_triage_result(raw_result, fallback_issue_type="other"):
    result = raw_result if isinstance(raw_result, dict) else {}
    issue_type = _normalize_repair_triage_issue_type(result.get("issueType"), fallback=fallback_issue_type)
    priority = _normalize_repair_triage_priority(result.get("priority"), fallback="P2")
    suggestions = _normalize_repair_triage_suggestions(result.get("suggestions"))
    possible_causes = _normalize_repair_triage_possible_causes(result.get("possibleCauses"))
    fault_part = _normalize_repair_triage_short_text(result.get("faultPart"), max_len=100)
    summary = _normalize_repair_triage_short_text(result.get("summary"), max_len=500)
    ocr_summary = _normalize_repair_triage_short_text(result.get("ocrSummary"), max_len=500)
    confidence = _normalize_repair_triage_confidence(result.get("confidence"))
    raw_json = json.dumps(result if isinstance(result, dict) else {}, ensure_ascii=False, separators=(",", ":"))
    if len(raw_json) > 20000:
        raw_json = raw_json[:20000]
    return {
        "issueType": issue_type,
        "priority": priority,
        "faultPart": fault_part,
        "summary": summary,
        "possibleCauses": possible_causes,
        "ocrSummary": ocr_summary,
        "suggestions": suggestions,
        "confidence": confidence,
        "modelName": SILICONFLOW_MODEL if SILICONFLOW_API_KEY else "heuristic-fallback",
        "rawJson": raw_json,
    }


def ai_triage_repair(description, equipment_meta=None, lab_meta=None, attachments=None, history_context=None):
    desc = str(description or "").strip()
    if len(desc) > 1000:
        desc = desc[:1000]

    equipment_ctx = equipment_meta if isinstance(equipment_meta, dict) else {}
    lab_ctx = lab_meta if isinstance(lab_meta, dict) else {}
    issue_hint = (
        equipment_ctx.get("issueTypeHint")
        or equipment_ctx.get("issueType")
        or equipment_ctx.get("issue_type")
        or lab_ctx.get("issueTypeHint")
        or lab_ctx.get("issueType")
        or lab_ctx.get("issue_type")
        or ""
    )
    fallback_issue = _normalize_repair_triage_issue_type(
        issue_hint,
        fallback=_extract_repair_issue_type_from_text(desc),
    )
    fallback_raw = json.dumps(
        {
            "issueType": fallback_issue,
            "priority": "P2",
            "faultPart": "",
            "summary": "",
            "possibleCauses": [],
            "ocrSummary": "",
            "suggestions": [],
            "confidence": 0.0,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    fallback = {
        "issueType": fallback_issue,
        "priority": "P2",
        "faultPart": "",
        "summary": "",
        "possibleCauses": [],
        "ocrSummary": "",
        "suggestions": [],
        "confidence": 0.0,
        "modelName": "heuristic-fallback",
        "rawJson": fallback_raw,
    }
    attachment_rows = []
    if isinstance(attachments, list):
        for item in attachments[:5]:
            row = item if isinstance(item, dict) else {}
            attachment_rows.append(
                {
                    "name": _normalize_repair_triage_short_text(row.get("name"), max_len=200),
                    "url": _normalize_repair_triage_short_text(row.get("url"), max_len=500),
                    "ocrText": _normalize_repair_triage_short_text(row.get("ocrText"), max_len=500),
                    "fileType": _normalize_repair_triage_short_text(row.get("fileType") or "image", max_len=32),
                }
            )
    history_rows = []
    if isinstance(history_context, list):
        for item in history_context[:4]:
            row = item if isinstance(item, dict) else {}
            history_rows.append(
                {
                    "issueType": _normalize_repair_triage_issue_type(row.get("issueType"), fallback=fallback_issue),
                    "status": _normalize_repair_triage_short_text(row.get("status"), max_len=32),
                    "summary": _normalize_repair_triage_short_text(row.get("summary") or row.get("description"), max_len=180),
                    "createdAt": _normalize_repair_triage_short_text(row.get("createdAt"), max_len=32),
                }
            )
    if not desc and not attachment_rows:
        return dict(fallback)

    safe_equipment = {
        "id": _to_int_or_none(equipment_ctx.get("id")),
        "assetCode": str(equipment_ctx.get("assetCode") or "").strip()[:64],
        "name": str(equipment_ctx.get("name") or "").strip()[:128],
        "status": str(equipment_ctx.get("status") or "").strip()[:32],
        "issueTypeHint": _normalize_repair_triage_issue_type(issue_hint, fallback=fallback_issue),
    }
    safe_lab = {
        "id": _to_int_or_none(lab_ctx.get("id")),
        "name": str(lab_ctx.get("name") or "").strip()[:128],
        "status": str(lab_ctx.get("status") or "").strip()[:32],
    }

    system_prompt = (
        "你是实验室报修智能分诊助手。"
        "请严格输出 JSON，不要输出 JSON 以外任何字符。"
        "JSON schema 固定为："
        '{"issueType":"computer|lighting|floor|network|other","faultPart":"","priority":"P0|P1|P2","summary":"","possibleCauses":["..."],"ocrSummary":"","suggestions":["..."],"confidence":0.0}。'
        "issueType 只能是 computer/lighting/floor/network/other。"
        "faultPart 表示可能故障部位或对象，例如 显示器、电源、网口、地砖。"
        "priority 只能是 P0/P1/P2。"
        "summary 用一句中文总结问题。"
        "possibleCauses 最多 4 条。"
        "ocrSummary 用于概括截图/OCR中的关键信息，没有就输出空字符串。"
        "suggestions 最多 5 条，每条一句可执行动作。"
        "confidence 在 0 到 1 之间。"
    )
    user_payload = {
        "description": desc,
        "equipmentMeta": safe_equipment,
        "labMeta": safe_lab,
        "attachments": attachment_rows,
        "historyContext": history_rows,
    }
    try:
        content = _call_siliconflow_chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            temperature=0.1,
        )
        try:
            parsed = json.loads(content)
        except Exception:
            extracted = _extract_json_object(content)
            if not extracted:
                return dict(fallback)
            try:
                parsed = json.loads(extracted)
            except Exception:
                return dict(fallback)
        normalized = _normalize_repair_triage_result(parsed, fallback_issue_type=fallback_issue)
        if not normalized.get("rawJson"):
            normalized["rawJson"] = "{}"
        return normalized
    except Exception:
        return dict(fallback)


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


def _agent_general_response(text, current_role=""):
    knowledge_result = None
    if not _agent_should_use_web_search(text):
        try:
            knowledge_result = ask_knowledge_base(text, current_role=current_role, actor=getattr(g, "current_user", {}) or {})
        except Exception:
            knowledge_result = None
        if isinstance(knowledge_result, dict) and knowledge_result.get("matched") and knowledge_result.get("answer"):
            return _agent_response(
                code=0,
                msg="ok",
                reply=str(knowledge_result.get("answer") or "").strip(),
                action="knowledge_rag",
                extra={
                    "sources": knowledge_result.get("sources") or [],
                    "knowledge": {
                        "queryLogId": int(knowledge_result.get("queryLogId") or 0),
                        "matchedCount": len(knowledge_result.get("hits") or []),
                    },
                },
                http_status=200,
            )

    if _agent_should_use_web_search(text):
        is_weather_query = _agent_is_weather_query(text)
        weather_plan = {}
        try:
            if is_weather_query:
                try:
                    search_payload = _agent_execute_weather_lookup(text)
                except BizError:
                    search_payload = _agent_execute_weather_search(text)
                weather_plan = search_payload.get("weatherPlan") if isinstance(search_payload.get("weatherPlan"), dict) else {}
            else:
                search_payload = _call_tavily_search(text, _agent_get_web_search_options(text))
        except BizError as e:
            if str(e.msg or "").strip() == "TAVILY_API_KEY not configured":
                return _agent_response(
                    code=0,
                    msg="ok",
                    reply="管理员未配置联网搜索密钥（TAVILY_API_KEY），当前无法执行联网搜索。请先在后端 lab-api/.env 中配置后重启服务。",
                    action="error",
                    http_status=200,
                )
            return _agent_response(
                code=e.status,
                msg=e.msg,
                reply="联网搜索暂时不可用，请稍后重试。",
                action="error",
                http_status=e.status,
            )

        results = search_payload.get("results") if isinstance(search_payload.get("results"), list) else []
        if not results:
            return _agent_response(
                code=0,
                msg="ok",
                reply="已尝试联网搜索，但没有找到足够相关的网页结果。你可以换个更具体的关键词再试。",
                action="web_search_empty",
                extra={"search": search_payload, "sources": []},
                http_status=200,
            )

        if is_weather_query:
            reply = _build_weather_summary_reply(text, search_payload, weather_plan)
            if not reply:
                reply = _build_weather_reply_fallback(text, search_payload, weather_plan)
        else:
            try:
                reply = _call_siliconflow_grounded_web_reply(text, search_payload) if SILICONFLOW_API_KEY else ""
            except BizError:
                reply = ""
            if not reply:
                reply = _build_agent_web_search_fallback_reply(search_payload)

        return _agent_response(
            code=0,
            msg="ok",
            reply=reply,
            action="weather_search" if is_weather_query else "web_search",
            extra={"search": search_payload, "sources": results, "weatherPlan": weather_plan if is_weather_query else {}},
            http_status=200,
        )

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
    current_role,
    rule_payload,
    fallback_date_text="",
    period_time_text="",
    fallback_lab_name="",
    fallback_reason="",
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
            "reason": str(fallback_reason or "").strip(),
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
    if fallback_reason and not reason:
        reason = str(fallback_reason or "").strip()

    if not force_reservation:
        is_reservation_request = _looks_like_reservation_request(
            text=text,
            parsed={"intent": intent, "labId": lab_id, "labName": lab_name, "date": date_text, "time": time_text},
            fallback_date=fallback_date_text,
            fallback_time=period_time_text,
            fallback_lab=fallback_lab_name,
        )
        if not is_reservation_request:
            return _agent_general_response(text, current_role=current_role)

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

    if not parse_slots(time_text):
        reply = "时段格式不正确，请使用标准时段（如 08:00-08:40）或节次表达（如 1-2节）后重试。"
        _agent_pending_set(
            user_name,
            "reserve_create",
            date_text,
            "",
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

    schedule_error = validate_reservation_schedule(
        date_text,
        time_text,
        lab_id=_to_int_or_none((lab or {}).get("id")),
        lab_name=str((lab or {}).get("name") or "").strip(),
    )
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
            conflict_data = getattr(e, "data", None)
            plans = _agent_normalize_plan_items((conflict_data or {}).get("plans"))
            if plans:
                plan_prompt = str((conflict_data or {}).get("reply") or "").strip() or "该时段冲突，我给你3个可选方案："
                plan_slots = {
                    "labName": str(lab.get("name") or "").strip(),
                    "date": date_text,
                    "time": time_text,
                    "reason": str(reason or "").strip(),
                    "plans": plans,
                    "planPrompt": plan_prompt,
                }
                _agent_pending_set(
                    user_name,
                    "reserve_plan_pick",
                    slots=plan_slots,
                    missing_slots=["selectedPlanId"],
                    state="collecting",
                )
                audit_log(
                    "agent.reservation.plan.generated",
                    target_type="reservation_plan",
                    detail={
                        "source": "conflict",
                        "labName": str(lab.get("name") or "").strip(),
                        "preferredDate": date_text,
                        "preferredTime": time_text,
                        "planCount": len(plans),
                    },
                    actor={"username": user_name},
                )
                return _agent_response(
                    code=0,
                    msg="ok",
                    reply=_agent_build_plan_options_text(plans, prefix=plan_prompt),
                    action="plan_options",
                    extra={
                        "plans": plans,
                        "pending": _agent_pending_to_public_payload(
                            {
                                "intent": "reserve_plan_pick",
                                "slots": plan_slots,
                                "missing_slots": ["selectedPlanId"],
                                "state": "collecting",
                            }
                        ),
                    },
                    http_status=200,
                )
            reply = "该时段已冲突或被占用，请换一个时段，我可以继续帮你提交。"
            return _agent_response(code=0, msg="ok", reply=reply, action="conflict", http_status=200)
        return _agent_response(code=e.status, msg=e.msg, reply=f"预约失败：{e.msg}", action="error", http_status=e.status)

    reply = (
        f"已为你提交预约：{created['labName']}，{created['date']} {created['time']}，"
        f"当前状态为{_reservation_status_label(created.get('status'))}。"
    )
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


def _is_rule_explain_query(text):
    raw = str(text or "").strip()
    compact = re.sub(r"\s+", "", raw)
    if not compact:
        return False
    keyword_hits = (
        "预约规则",
        "审批规则",
        "开放规则",
        "为什么不能预约",
        "为啥不能预约",
        "为什么要审批",
        "为什么待审批",
        "冲突原因",
        "为什么冲突",
        "预约限制",
        "能预约吗",
        "可以预约吗",
    )
    if any(token in compact for token in keyword_hits):
        return True
    if "规则" in compact and ("预约" in compact or "实验室" in compact or "审批" in compact):
        return True
    if "审批" in compact and ("为什么" in compact or "怎么" in compact):
        return True
    return False


def _agent_handle_rule_explain_query(user_name, role, lab_name="", date_text="", time_text="", rule_payload=None):
    target_lab = str(lab_name or "").strip()
    payload = rule_payload if isinstance(rule_payload, dict) and not target_lab else get_reservation_rules_payload(lab_name=target_lab)
    payload = payload if isinstance(payload, dict) else {}
    slots = _resolve_rule_slots(payload)
    approval = payload.get("approval") if isinstance(payload.get("approval"), dict) else {}
    approval_mode = str(approval.get("mode") or "").strip().lower() or "admin"
    peak_force = bool(approval.get("peakForceApproval"))
    disabled_dates = _normalize_rule_date_list(payload.get("disabledDates"))
    blackout_slots = _normalize_rule_blackout_slots(payload.get("blackoutSlots"), list(slots))
    max_days = max(0, int(payload.get("maxDaysAhead") or 0))
    min_days = max(0, int(payload.get("minDaysAhead") or 0))
    min_time = str(payload.get("minTime") or "").strip() or "00:00"
    max_time = str(payload.get("maxTime") or "").strip() or "23:59"

    opening_summary = (
        f"{target_lab or '当前实验室'}目前支持提前 {min_days}-{max_days} 天预约，"
        f"可选时间通常在 {min_time}-{max_time}，"
        f"当前配置了 {len(slots)} 个可预约时段。"
    )
    rule_bits = [opening_summary]
    if disabled_dates:
        preview = "、".join(disabled_dates[:3])
        more_text = " 等" if len(disabled_dates) > 3 else ""
        rule_bits.append(f"系统已禁用 {len(disabled_dates)} 个日期，例如 {preview}{more_text}。")
    if blackout_slots:
        preview_slots = []
        for item in blackout_slots[:2]:
            slot_text = str(item.get("slot") or "").strip()
            reason_text = str(item.get("reason") or "").strip()
            if slot_text and reason_text:
                preview_slots.append(f"{slot_text}（{reason_text}）")
            elif slot_text:
                preview_slots.append(slot_text)
        if preview_slots:
            rule_bits.append(f"还有部分黑名单时段不可约，例如 {'、'.join(preview_slots)}。")

    approval_text_map = {
        "auto": "默认自动通过",
        "teacher": "默认需要教师审批",
        "admin": "默认需要管理员审批",
        "peak_admin": "高峰时段转管理员审批",
    }
    approval_summary = approval_text_map.get(approval_mode, "默认需要管理员审批")
    if approval_mode == "auto" and peak_force:
        approval_summary = "默认自动通过，但高峰时段会转管理员审批"
    rule_bits.append(f"审批策略：{approval_summary}。")

    detail_bits = []
    safe_date = str(date_text or "").strip()
    safe_time = str(time_text or "").strip()
    if safe_date and safe_time:
        schedule_error = validate_reservation_schedule(
            safe_date,
            safe_time,
            lab_name=target_lab,
        )
        if schedule_error:
            detail_bits.append(f"按你提供的时间看，这个申请暂时不能提交，原因是：{schedule_error}。")
        else:
            review = resolve_reservation_review_policy(lab_name=target_lab, date_text=safe_date, time_range=safe_time)
            if bool(review.get("approvalRequired")):
                reviewer = "教师" if str(review.get("reviewRole") or "").strip() == "teacher" else "管理员"
                detail_bits.append(f"{safe_date} {safe_time} 这个时段可以提交，但需要{reviewer}审批。")
            else:
                detail_bits.append(f"{safe_date} {safe_time} 这个时段符合规则，可以直接通过。")
            if target_lab and has_approved_conflict(target_lab, safe_date, safe_time):
                detail_bits.append("不过该实验室同一时段已经有已通过预约，仍然会产生冲突。")
    elif safe_date or safe_time:
        detail_bits.append("如果你把日期和时间段一起告诉我，我可以继续判断这次申请是否能过。")
    else:
        detail_bits.append("如果你告诉我实验室、日期和时间段，我还能直接帮你判断能不能约、要不要审批。")

    reply = " ".join([x for x in rule_bits + detail_bits if x])
    return _agent_response(
        code=0,
        msg="ok",
        reply=reply,
        action="rule_explain",
        extra={
            "ruleSummary": {
                "labName": target_lab,
                "minDaysAhead": min_days,
                "maxDaysAhead": max_days,
                "minTime": min_time,
                "maxTime": max_time,
                "slotCount": len(slots),
                "approvalMode": approval_mode,
                "disabledDateCount": len(disabled_dates),
                "blackoutCount": len(blackout_slots),
            }
        },
        http_status=200,
    )


def _agent_translate_intent(text, pending_ctx, fallback_date_text="", period_time_text="", fallback_lab_name=""):
    raw = str(text or "").strip()
    pending_intent_raw = str((pending_ctx or {}).get("intent") or "").strip()
    pending_intent = "lab_reservation_list" if pending_intent_raw == "reserve_query" else pending_intent_raw
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
        "issueType": _extract_repair_issue_type_from_text(raw),
        "description": _extract_repair_description_from_text(raw),
        "equipmentHint": _extract_equipment_hint_from_text(raw),
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
    if pending_intent == "reschedule_confirm":
        if _agent_is_confirm_text(raw):
            result["op"] = "reschedule_execute"
            result["reservationId"] = int(_agent_pending_slot(pending_ctx, "targetReservationId", 0) or 0)
            result["labName"] = str(_agent_pending_slot(pending_ctx, "labName", "") or "").strip()
            result["date"] = str(_agent_pending_slot(pending_ctx, "date", "") or "").strip()
            result["time"] = str(_agent_pending_slot(pending_ctx, "time", "") or "").strip()
            return result
        if _agent_is_pending_abort_text(raw):
            result["op"] = "reschedule_abort"
            return result
    if pending_intent == "cancel_reservation_confirm":
        if _agent_is_confirm_text(raw):
            result["op"] = "cancel_reservation_execute"
            result["reservationId"] = int(_agent_pending_slot(pending_ctx, "reservationId", 0) or 0)
            result["labName"] = str(_agent_pending_slot(pending_ctx, "labName", "") or "").strip()
            result["date"] = str(_agent_pending_slot(pending_ctx, "date", "") or "").strip()
            result["time"] = str(_agent_pending_slot(pending_ctx, "time", "") or "").strip()
            result["targetIds"] = list(_agent_pending_slot(pending_ctx, "targetIds", []) or [])
            return result
        if _agent_is_pending_abort_text(raw) and not _is_cancel_reservations_request(raw, result["labName"], result["reservationId"]):
            result["op"] = "cancel_reservation_abort"
            return result

    if _is_cancel_all_reservations_request(raw):
        result["op"] = "cancel_all_prepare"
        return result
    nickname = _extract_nickname_from_text(raw)
    if nickname:
        result["op"] = "update_profile"
        result["nickname"] = nickname
        return result
    if _is_repair_advice_query(raw):
        result["op"] = "repair_advice"
        return result
    if _is_alarm_advice_query(raw):
        result["op"] = "alarm_advice"
        return result
    if _is_my_repair_orders_query(raw):
        result["op"] = "repair_list"
        return result
    if _is_progress_summary_query(raw):
        result["op"] = "progress_summary"
        return result
    if _is_repair_create_request(raw):
        result["op"] = "repair_create"
        return result
    if _is_reschedule_request(raw):
        result["op"] = "reschedule_prepare"
        return result
    if _is_my_reservations_query(raw):
        result["op"] = "reservation_summary"
        return result
    if _is_lab_reservations_query(raw):
        result["op"] = "lab_reservation_list"
        return result
    if _is_cancel_reservations_request(raw, result["labName"], result["reservationId"]):
        result["op"] = "cancel_reservation_prepare"
        return result
    if _is_rule_explain_query(raw):
        result["op"] = "rule_explain"
        return result
    if _is_lab_availability_query(raw):
        result["op"] = "availability"
        return result

    if pending_intent == "availability":
        has_followup_info = bool(result["date"] or result["time"])
        if has_followup_info and not coarse_reservation_request:
            result["op"] = "availability"
            result["date"] = result["date"] or str(_agent_pending_slot(pending_ctx, "date", "") or "").strip()
            result["time"] = result["time"] or str(_agent_pending_slot(pending_ctx, "time", "") or "").strip()
            return result
    if pending_intent == "reschedule_confirm":
        has_followup_info = bool(result["date"] or result["time"] or result["reservationId"] or result["labName"])
        if has_followup_info:
            result["op"] = "reschedule_prepare"
            result["date"] = result["date"] or str(_agent_pending_slot(pending_ctx, "date", "") or "").strip()
            result["time"] = result["time"] or str(_agent_pending_slot(pending_ctx, "time", "") or "").strip()
            result["reservationId"] = int(result["reservationId"] or _agent_pending_slot(pending_ctx, "targetReservationId", 0) or 0)
            if not result["labName"]:
                result["labName"] = str(_agent_pending_slot(pending_ctx, "labName", "") or "").strip()
            return result
    if pending_intent == "reschedule":
        has_followup_info = bool(result["date"] or result["time"] or result["reservationId"] or result["labName"])
        should_apply_pending = has_followup_info and (not coarse_reservation_request or int(result["reservationId"] or 0) > 0)
        if should_apply_pending:
            result["op"] = "reschedule_prepare"
            result["date"] = result["date"] or str(_agent_pending_slot(pending_ctx, "date", "") or "").strip()
            result["time"] = result["time"] or str(_agent_pending_slot(pending_ctx, "time", "") or "").strip()
            if int(result["reservationId"] or 0) <= 0:
                result["reservationId"] = int(_agent_pending_slot(pending_ctx, "targetReservationId", 0) or 0)
            if not result["labName"]:
                result["labName"] = str(_agent_pending_slot(pending_ctx, "labName", "") or "").strip()
            return result
    if pending_intent == "cancel_reservation_confirm":
        has_followup_info = bool(result["date"] or result["time"] or result["reservationId"] or result["labName"])
        if has_followup_info or _is_cancel_reservations_request(raw, result["labName"], result["reservationId"]):
            result["op"] = "cancel_reservation_prepare"
            if int(result["reservationId"] or 0) <= 0:
                result["reservationId"] = int(_agent_pending_slot(pending_ctx, "reservationId", 0) or 0)
                result["date"] = result["date"] or str(_agent_pending_slot(pending_ctx, "date", "") or "").strip()
                result["time"] = result["time"] or str(_agent_pending_slot(pending_ctx, "time", "") or "").strip()
                if not result["labName"]:
                    result["labName"] = str(_agent_pending_slot(pending_ctx, "labName", "") or "").strip()
            return result
    if pending_intent == "cancel_reservation":
        if _agent_is_pending_abort_text(raw) and not _is_cancel_reservations_request(raw, result["labName"], result["reservationId"]):
            result["op"] = "cancel_reservation_abort"
            return result
        has_followup_info = bool(result["date"] or result["time"] or result["reservationId"] or result["labName"])
        if has_followup_info:
            result["op"] = "cancel_reservation_prepare"
            if int(result["reservationId"] or 0) <= 0:
                result["reservationId"] = int(_agent_pending_slot(pending_ctx, "reservationId", 0) or 0)
                result["date"] = result["date"] or str(_agent_pending_slot(pending_ctx, "date", "") or "").strip()
                result["time"] = result["time"] or str(_agent_pending_slot(pending_ctx, "time", "") or "").strip()
                if not result["labName"]:
                    result["labName"] = str(_agent_pending_slot(pending_ctx, "labName", "") or "").strip()
            return result
    if pending_intent == "reserve_create":
        has_followup_info = bool(result["date"] or result["time"] or result["labName"])
        if has_followup_info:
            result["op"] = "reserve_create"
            result["date"] = result["date"] or str(_agent_pending_slot(pending_ctx, "date", "") or "").strip()
            result["time"] = result["time"] or str(_agent_pending_slot(pending_ctx, "time", "") or "").strip()
            if not result["labName"]:
                result["labName"] = str(_agent_pending_slot(pending_ctx, "labName", "") or "").strip()
            return result
    if pending_intent == "repair_create":
        desc_text = str(result["description"] or "").strip()
        has_meaningful_desc = _agent_is_meaningful_repair_description(desc_text)
        has_followup_info = bool(has_meaningful_desc or result["labName"] or result["equipmentHint"])
        if has_followup_info:
            result["op"] = "repair_create"
            pending_desc = str(_agent_pending_slot(pending_ctx, "description", "") or "").strip()
            if (result["labName"] or result["equipmentHint"]) and pending_desc and len(desc_text) <= 12:
                result["description"] = pending_desc
            elif not result["description"]:
                result["description"] = pending_desc
            if not result["labName"]:
                result["labName"] = str(_agent_pending_slot(pending_ctx, "labName", "") or "").strip()
            if not result["equipmentHint"]:
                result["equipmentHint"] = str(_agent_pending_slot(pending_ctx, "equipmentHint", "") or "").strip()
            issue_from_pending = str(_agent_pending_slot(pending_ctx, "issueType", "") or "").strip().lower()
            if result["issueType"] not in AGENT_REPAIR_ISSUE_SET and issue_from_pending in AGENT_REPAIR_ISSUE_SET:
                result["issueType"] = issue_from_pending
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
    audit_log(
        "agent_tool_execute",
        target_type="agent_tool",
        target_id=op,
        detail={
            "op": op,
            "source": "agent_chat",
            "pendingIntent": str(_agent_multiturn_intent_from_tool(op) or ""),
        },
        actor={"username": str(user_name or "").strip(), "role": str(current_role or "").strip()},
    )
    if bool((tool_call or {}).get("clearCancelPending")):
        _agent_pending_clear(user_name)

    if op == "reservation_summary":
        return _agent_handle_my_reservations_query(user_name=user_name, limit=5)
    if op == "progress_summary":
        return _agent_handle_progress_summary(user_name=user_name, role=current_role, reservation_limit=3, repair_limit=3)
    if op == "repair_advice":
        return _agent_handle_repair_advice(user_name=user_name, role=current_role, limit=8)
    if op == "alarm_advice":
        return _agent_handle_alarm_advice(user_name=user_name, role=current_role, limit=5)
    if op == "repair_list":
        return _agent_handle_my_repair_orders_query(user_name=user_name, role=current_role, limit=5)
    if op == "repair_create":
        return _agent_handle_repair_create(
            user_name=user_name,
            role=current_role,
            issue_type=str((tool_call or {}).get("issueType") or "").strip(),
            description=str((tool_call or {}).get("description") or "").strip(),
            lab_name=str((tool_call or {}).get("labName") or "").strip(),
            equipment_hint=str((tool_call or {}).get("equipmentHint") or "").strip(),
        )
    if op == "lab_reservation_list":
        return _agent_handle_lab_reservations_query(
            user_name=user_name,
            role=current_role,
            lab_name=str((tool_call or {}).get("labName") or "").strip(),
            date_text=str((tool_call or {}).get("date") or "").strip(),
            time_text=str((tool_call or {}).get("time") or "").strip(),
            limit=20,
        )
    if op in {"cancel_lab", "cancel_reservation_prepare"}:
        return _agent_handle_cancel_reservations(
            user_name=user_name,
            role=current_role,
            reservation_id=_to_int_or_none((tool_call or {}).get("reservationId")),
            lab_name=str((tool_call or {}).get("labName") or "").strip(),
            date_text=str((tool_call or {}).get("date") or "").strip(),
            time_text=str((tool_call or {}).get("time") or "").strip(),
            confirmed=False,
        )
    if op == "cancel_reservation_execute":
        return _agent_handle_cancel_reservations(
            user_name=user_name,
            role=current_role,
            reservation_id=_to_int_or_none((tool_call or {}).get("reservationId")),
            lab_name=str((tool_call or {}).get("labName") or "").strip(),
            date_text=str((tool_call or {}).get("date") or "").strip(),
            time_text=str((tool_call or {}).get("time") or "").strip(),
            confirmed=True,
            target_ids=(tool_call or {}).get("targetIds"),
        )
    if op == "cancel_reservation_abort":
        _agent_pending_clear(user_name, reason="cancel_reservation_abort")
        return _agent_response(code=0, msg="ok", reply="已取消本次预约取消操作。", action="cancel_aborted", http_status=200)
    if op in {"reschedule", "reschedule_prepare"}:
        return _agent_handle_reschedule_request(
            user_name=user_name,
            role=current_role,
            reservation_id=_to_int_or_none((tool_call or {}).get("reservationId")),
            lab_name=str((tool_call or {}).get("labName") or "").strip(),
            date_text=str((tool_call or {}).get("date") or "").strip(),
            time_text=str((tool_call or {}).get("time") or "").strip(),
            confirmed=False,
        )
    if op == "reschedule_execute":
        return _agent_handle_reschedule_request(
            user_name=user_name,
            role=current_role,
            reservation_id=_to_int_or_none((tool_call or {}).get("reservationId")),
            lab_name=str((tool_call or {}).get("labName") or "").strip(),
            date_text=str((tool_call or {}).get("date") or "").strip(),
            time_text=str((tool_call or {}).get("time") or "").strip(),
            confirmed=True,
        )
    if op == "reschedule_abort":
        _agent_pending_clear(user_name, reason="reschedule_abort")
        return _agent_response(code=0, msg="ok", reply="已取消本次改期操作。", action="cancel_aborted", http_status=200)
    if op == "cancel_all_prepare":
        return _agent_prepare_cancel_all(user_name=user_name)
    if op == "cancel_all_confirm":
        return _agent_execute_cancel_all(user_name=user_name)
    if op == "cancel_all_abort":
        _agent_pending_clear(user_name, reason="cancel_all_abort")
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
        try:
            profile = update_user_profile_by_username(user_name, nickname=nickname)
        except BizError as e:
            return _agent_response(
                code=e.status,
                msg=e.msg,
                reply=f"修改昵称失败：{e.msg}",
                action="error",
                http_status=e.status,
            )

        audit_log(
            "user.profile.update",
            target_type="user",
            target_id=profile.get("userId"),
            detail={"source": "agent", "fields": ["nickname"], "nickname": profile.get("nickname")},
            actor={"id": profile.get("userId"), "username": user_name, "role": current_role},
        )
        return _agent_response(
            code=0,
            msg="ok",
            reply=f"已帮你把昵称改成“{profile.get('nickname') or nickname}”。",
            action="update_profile",
            extra={
                "profile": {
                    "nickname": profile.get("nickname") or "",
                    "phone": profile.get("phone") or "",
                    "avatarUrl": profile.get("avatarUrl") or "",
                }
            },
            http_status=200,
        )
    if op == "rule_explain":
        return _agent_handle_rule_explain_query(
            user_name=user_name,
            role=current_role,
            lab_name=str((tool_call or {}).get("labName") or "").strip(),
            date_text=str((tool_call or {}).get("date") or "").strip(),
            time_text=str((tool_call or {}).get("time") or "").strip(),
            rule_payload=rule_payload,
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
            current_role=current_role,
            rule_payload=rule_payload,
            fallback_date_text=str((tool_call or {}).get("date") or "").strip(),
            period_time_text=str((tool_call or {}).get("time") or "").strip(),
            fallback_lab_name=str((tool_call or {}).get("labName") or "").strip(),
            fallback_reason=str((tool_call or {}).get("reason") or "").strip(),
            force_reservation=True,
        )
    return _agent_general_response(text, current_role=current_role)


try:
    ensure_user_password_column()
except Exception as e:
    print(f"[warn] ensure_user_password_column failed: {e}")

try:
    ensure_user_profile_columns()
except Exception as e:
    print(f"[warn] ensure_user_profile_columns failed: {e}")

try:
    ensure_user_governance_columns()
except Exception as e:
    print(f"[warn] ensure_user_governance_columns failed: {e}")

try:
    ensure_auth_refresh_table()
except Exception as e:
    print(f"[warn] ensure_auth_refresh_table failed: {e}")

try:
    ensure_audit_log_table()
except Exception as e:
    print(f"[warn] ensure_audit_log_table failed: {e}")

try:
    ensure_reservation_rule_config_table()
except Exception as e:
    print(f"[warn] ensure_reservation_rule_config_table failed: {e}")

try:
    ensure_reservation_review_columns()
except Exception as e:
    print(f"[warn] ensure_reservation_review_columns failed: {e}")

try:
    ensure_reservation_query_indexes()
except Exception as e:
    print(f"[warn] ensure_reservation_query_indexes failed: {e}")

try:
    ensure_ai_user_permission_table()
except Exception as e:
    print(f"[warn] ensure_ai_user_permission_table failed: {e}")

try:
    ensure_user_permission_table()
except Exception as e:
    print(f"[warn] ensure_user_permission_table failed: {e}")

try:
    ensure_announcement_table()
except Exception as e:
    print(f"[warn] ensure_announcement_table failed: {e}")

try:
    ensure_announcement_manage_columns()
except Exception as e:
    print(f"[warn] ensure_announcement_manage_columns failed: {e}")

try:
    ensure_announcement_read_state_table()
except Exception as e:
    print(f"[warn] ensure_announcement_read_state_table failed: {e}")

try:
    ensure_notification_read_state_table()
except Exception as e:
    print(f"[warn] ensure_notification_read_state_table failed: {e}")

try:
    ensure_user_feedback_table()
except Exception as e:
    print(f"[warn] ensure_user_feedback_table failed: {e}")

try:
    ensure_agent_chat_message_table()
except Exception as e:
    print(f"[warn] ensure_agent_chat_message_table failed: {e}")

try:
    ensure_lost_found_claim_columns()
except Exception as e:
    print(f"[warn] ensure_lost_found_claim_columns failed: {e}")

try:
    ensure_assets_tables()
except Exception as e:
    print(f"[warn] ensure_assets_tables failed: {e}")

try:
    ensure_duty_roster_table()
except Exception as e:
    print(f"[warn] ensure_duty_roster_table failed: {e}")

try:
    ensure_emergency_contact_table()
except Exception as e:
    print(f"[warn] ensure_emergency_contact_table failed: {e}")

try:
    ensure_incident_record_table()
except Exception as e:
    print(f"[warn] ensure_incident_record_table failed: {e}")

try:
    ensure_equipment_borrow_tables()
except Exception as e:
    print(f"[warn] ensure_equipment_borrow_tables failed: {e}")

try:
    ensure_equipment_lifecycle_columns()
except Exception as e:
    print(f"[warn] ensure_equipment_lifecycle_columns failed: {e}")

try:
    ensure_repair_work_order_ai_columns()
except Exception as e:
    print(f"[warn] ensure_repair_work_order_ai_columns failed: {e}")

try:
    ensure_lab_sensor_alarm_table()
except Exception as e:
    print(f"[warn] ensure_lab_sensor_alarm_table failed: {e}")

try:
    ensure_course_tables()
except Exception as e:
    print(f"[warn] ensure_course_tables failed: {e}")

try:
    ensure_course_member_tables()
except Exception as e:
    print(f"[warn] ensure_course_member_tables failed: {e}")

try:
    ensure_experiment_task_tables()
except Exception as e:
    print(f"[warn] ensure_experiment_task_tables failed: {e}")

try:
    ensure_experiment_task_file_tables()
except Exception as e:
    print(f"[warn] ensure_experiment_task_file_tables failed: {e}")

try:
    ensure_experiment_task_submission_tables()
except Exception as e:
    print(f"[warn] ensure_experiment_task_submission_tables failed: {e}")

try:
    ensure_task_rubric_tables()
except Exception as e:
    print(f"[warn] ensure_task_rubric_tables failed: {e}")

try:
    ensure_course_task_notice_tables()
except Exception as e:
    print(f"[warn] ensure_course_task_notice_tables failed: {e}")

try:
    ensure_course_task_notice_subscription_table()
except Exception as e:
    print(f"[warn] ensure_course_task_notice_subscription_table failed: {e}")

try:
    ensure_course_task_auto_notice_log_table()
except Exception as e:
    print(f"[warn] ensure_course_task_auto_notice_log_table failed: {e}")

try:
    ensure_class_period_configs_table()
except Exception as e:
    print(f"[warn] ensure_class_period_configs_table failed: {e}")

try:
    ensure_course_schedule_templates_table()
except Exception as e:
    print(f"[warn] ensure_course_schedule_templates_table failed: {e}")

try:
    ensure_course_schedule_items_table()
except Exception as e:
    print(f"[warn] ensure_course_schedule_items_table failed: {e}")

try:
    ensure_door_open_reminders_table()
except Exception as e:
    print(f"[warn] ensure_door_open_reminders_table failed: {e}")

try:
    ensure_reservation_waitlist_tables()
except Exception as e:
    print(f"[warn] ensure_reservation_waitlist_tables failed: {e}")

try:
    ensure_borrow_extension_tables()
except Exception as e:
    print(f"[warn] ensure_borrow_extension_tables failed: {e}")

try:
    ensure_attendance_tables()
except Exception as e:
    print(f"[warn] ensure_attendance_tables failed: {e}")

try:
    ensure_knowledge_base_tables()
except Exception as e:
    print(f"[warn] ensure_knowledge_base_tables failed: {e}")

try:
    ensure_repair_ai_v2_tables()
except Exception as e:
    print(f"[warn] ensure_repair_ai_v2_tables failed: {e}")

try:
    ensure_equipment_failure_prediction_tables()
except Exception as e:
    print(f"[warn] ensure_equipment_failure_prediction_tables failed: {e}")

try:
    ensure_ai_action_log_table()
except Exception as e:
    print(f"[warn] ensure_ai_action_log_table failed: {e}")


