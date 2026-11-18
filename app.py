"""app.py — Flask REST API for the Fault-to-Recovery grid simulator (BESCOM Theme 9).

Endpoints:
  POST /api/login            {email, password}
  POST /api/otp/send         {mobile}          → issues 6-digit OTP, returns expiry
  POST /api/otp/verify       {mobile, otp}      → verifies OTP, returns access token
  GET  /api/network/state    full grid snapshot (also advances live telemetry)
  POST /api/simulate/fault   {scenario:"S1"|"S2"} or {edge_id:"..."}
  POST /api/simulate/restore apply recommended switching actions
  POST /api/simulate/reset   restore default healthy topology
  GET  /api/events           ?type=fault&q=...  filterable audit log

The app also serves the compiled frontend at GET / (same origin → no CORS issues).
CORS is enabled so the file:// frontend works too.

Run:  python app.py   →  http://localhost:5000
"""
import os
import re
import secrets
import time
from flask import Flask, jsonify, request, send_from_directory

from flask_cors import CORS

import db
import engine

app = Flask(__name__)
CORS(app, origins="*")  # allow file:// frontend and cross-origin dev

# Frontend HTML lives next to app.py (download/bescom-grid.html)
FRONTEND_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_FILE = "bescom-grid.html"

# ---------------------------------------------------------------- OTP store
# In-memory OTP store: {mobile: {"otp": "123456", "expires_at": ts, "attempts_left": 3, "issued_at": ts}}
# Single-operator simulation → in-memory is fine. In production this would live
# in Redis with TTL or in a dedicated `otp_codes` table.
_OTP_STORE = {}
_OTP_TTL_SEC = 5 * 60        # OTP valid for 5 minutes
_OTP_MAX_ATTEMPTS = 3        # 3 verification attempts before re-issue required
_OTP_RESEND_COOLDOWN = 30    # 30s between resend requests
_MOBILE_RE = re.compile(r"^\d{10}$")

# ---------------------------------------------------------------- boot
@app.before_request
def _ensure_booted():
    if not getattr(app, "_booted", False):
        db.init_db()
        engine.recompute()
        if db.telemetry_empty():
            engine.seed_telemetry()
        app._booted = True


# ---------------------------------------------------------------- routes
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, FRONTEND_FILE)

@app.route("/api/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    if email and len(password) >= 3:
        return jsonify({"ok": True, "token": "demo." + str(abs(hash(email))),
                        "user": {"email": email, "name": "Grid Operator",
                                 "role": "Shift Engineer", "station": "BESCOM Circle 4"}})
    return jsonify({"ok": False, "error": "Invalid credentials. Use admin@bescom.sim / demo123."}), 401


# ---------------------------------------------------------------- OTP routes
# Two-step mobile OTP verification:
#   1. POST /api/otp/send    {mobile:"9876543210"}   → server generates 6-digit code
#   2. POST /api/otp/verify  {mobile, otp}            → on success returns access token
#
# The OTP is included in the /send response (dev/demo mode) so you can see it on
# screen without an SMS gateway. In production you'd plug in an SMS provider
# (e.g. Twilio, MSG91, AWS SNS) and never return the code in the response.
@app.route("/api/otp/send", methods=["POST"])
def otp_send():
    body = request.get_json(silent=True) or {}
    mobile = (body.get("mobile") or "").strip()

    # Validate Indian-format 10-digit mobile (digits only, no country code).
    if not mobile or not _MOBILE_RE.match(mobile):
        return jsonify({"ok": False,
                        "error": "Enter a valid 10-digit mobile number."}), 400

    now = time.time()

    # Resend cooldown — prevent abuse / accidental spam.
    existing = _OTP_STORE.get(mobile)
    if existing and (now - existing["issued_at"]) < _OTP_RESEND_COOLDOWN:
        wait = int(_OTP_RESEND_COOLDOWN - (now - existing["issued_at"]))
        return jsonify({"ok": False,
                        "error": f"Please wait {wait}s before requesting another OTP.",
                        "retry_after_sec": wait}), 429

    # Generate a fresh 6-digit code.
    code = f"{secrets.randbelow(1000000):06d}"
    _OTP_STORE[mobile] = {
        "otp": code,
        "issued_at": now,
        "expires_at": now + _OTP_TTL_SEC,
        "attempts_left": _OTP_MAX_ATTEMPTS,
        "verified": False,
    }

    # DEV MODE: return the code so the frontend can display it.
    # Production: replace this block with an SMS dispatch call.
    return jsonify({
        "ok": True,
        "mobile": mobile,
        "expires_in_sec": _OTP_TTL_SEC,
        "attempts_left": _OTP_MAX_ATTEMPTS,
        "demo_otp": code,            # <-- remove in production after wiring SMS
        "channel": "sms",
        "message": f"OTP sent to +91 {mobile}. (Demo mode: code is {code}.)",
    })


@app.route("/api/otp/verify", methods=["POST"])
def otp_verify():
    body = request.get_json(silent=True) or {}
    mobile = (body.get("mobile") or "").strip()
    otp = (body.get("otp") or "").strip()

    if not mobile or not _MOBILE_RE.match(mobile):
        return jsonify({"ok": False, "error": "Invalid mobile number."}), 400
    if not otp or not re.match(r"^\d{6}$", otp):
        return jsonify({"ok": False, "error": "OTP must be 6 digits."}), 400

    record = _OTP_STORE.get(mobile)
    if not record:
        return jsonify({"ok": False, "error": "No OTP issued for this number. Request a new one."}), 404

    now = time.time()
    if now > record["expires_at"]:
        # Expired — clear it so a fresh send is required.
        _OTP_STORE.pop(mobile, None)
        return jsonify({"ok": False, "error": "OTP expired. Please request a new one."}), 410

    if record["verified"]:
        return jsonify({"ok": False, "error": "OTP already used. Request a new one."}), 409

    if otp != record["otp"]:
        record["attempts_left"] -= 1
        if record["attempts_left"] <= 0:
            _OTP_STORE.pop(mobile, None)
            return jsonify({"ok": False,
                            "error": "Too many wrong attempts. Please request a new OTP.",
                            "attempts_left": 0}), 403
        return jsonify({"ok": False,
                        "error": f"Incorrect OTP. {record['attempts_left']} attempt(s) left.",
                        "attempts_left": record["attempts_left"]}), 401

    # Success — mark verified + issue a real access token.
    record["verified"] = True
    token = "otp." + secrets.token_hex(16)
    return jsonify({
        "ok": True,
        "token": token,
        "mobile": mobile,
        "user": {
            "email": f"+91{mobile}@bescom.sim",
            "name": "Grid Operator",
            "role": "Shift Engineer",
            "station": "BESCOM Circle 4",
            "mobile": mobile,
            "verified_at": int(now),
        },
        "message": "OTP verified. Access granted.",
    })

@app.route("/api/network/state", methods=["GET"])
def network_state():
    engine.tick_telemetry()
    return jsonify(engine.build_state())

@app.route("/api/simulate/fault", methods=["POST"])
def simulate_fault():
    body = request.get_json(silent=True) or {}
    scenario = body.get("scenario")
    edge_id = body.get("edge_id")
    if not scenario and not edge_id:
        return jsonify({"error": "Provide 'scenario' (S1/S2) or 'edge_id'."}), 400
    state = engine.trigger_fault(scenario=scenario, edge_id=edge_id)
    return jsonify(state)

@app.route("/api/simulate/restore", methods=["POST"])
def simulate_restore():
    state = engine.apply_restoration()
    return jsonify(state)

@app.route("/api/simulate/reset", methods=["POST"])
def simulate_reset():
    state = engine.reset_grid()
    return jsonify(state)

@app.route("/api/events", methods=["GET"])
def events():
    type_filter = request.args.get("type", "all")
    q = request.args.get("q", "").strip().lower()
    evs = db.get_events(limit=500)
    out = []
    for e in evs:
        if type_filter != "all" and e["type"] != type_filter:
            continue
        if q and q not in (e["detail"] or "").lower() and q not in (e["location"] or "").lower() \
                and q not in (e["fault_id"] or "").lower():
            continue
        out.append(engine._ser_event(e))
    return jsonify(out)

@app.errorhandler(400)
@app.errorhandler(401)
def _err(e):
    return jsonify({"error": str(e.description) if hasattr(e, "description") else str(e)}), e.code


if __name__ == "__main__":
    db.init_db()
    if db.telemetry_empty():
        engine.seed_telemetry()
    engine.recompute()
    print("=" * 60)
    print(" Fault to Recovery — BESCOM Theme 9 backend")
    print(" API:      http://localhost:5000/api")
    print(" Frontend: http://localhost:5000/")
    print(" Login:    admin@bescom.sim / demo123")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
