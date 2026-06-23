#!/usr/bin/env python3
"""
To-Do Core
==========
A beautifully designed task manager with Apple-quality animations.
Uses ZERO external dependencies — pure Python stdlib only.

Run:
    python todo_core.py

The app opens automatically in your default browser.
Press Ctrl+C in the terminal to quit.
"""

import os
import sys
import json
import time
import hashlib
import threading
import webbrowser
import urllib.parse
from datetime import datetime, date
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "tdc_users.json")
TASKS_DIR  = os.path.join(BASE_DIR, "tdc_tasks")
os.makedirs(TASKS_DIR, exist_ok=True)

PORT = int(os.environ.get("PORT", 7890))
# ── Data helpers ──────────────────────────────────────────────────────────────
def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_users(u: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(u, f, indent=2)

def tasks_path(username: str) -> str:
    return os.path.join(TASKS_DIR, f"{username}.json")

def load_tasks(username: str) -> list:
    p = tasks_path(username)
    if os.path.exists(p):
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_tasks(username: str, tasks: list):
    with open(tasks_path(username), "w") as f:
        json.dump(tasks, f, indent=2)

# ── HTML ──────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>To-Do Core</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet"/>
<style>
/* ═══════════════════════════════════════════════════════════════
   DESIGN TOKENS
═══════════════════════════════════════════════════════════════ */
:root {
  --c-bg:         #0a0a0f;
  --c-surface:    #13131a;
  --c-surface2:   #1c1c27;
  --c-surface3:   #252535;
  --c-border:     rgba(255,255,255,0.07);
  --c-border2:    rgba(255,255,255,0.12);
  --c-text:       #f0f0f8;
  --c-text2:      #8888aa;
  --c-text3:      #5555777;
  --c-accent:     #6c63ff;
  --c-accent2:    #8b85ff;
  --c-accentglow: rgba(108,99,255,0.35);
  --c-high:       #ff5f6d;
  --c-med:        #ffc371;
  --c-low:        #43e97b;
  --c-danger:     #ff5f6d;
  --c-success:    #43e97b;
  --radius-sm:    10px;
  --radius:       16px;
  --radius-lg:    22px;
  --radius-xl:    32px;
  --blur:         blur(24px);
  --shadow:       0 8px 32px rgba(0,0,0,0.45);
  --shadow-lg:    0 20px 60px rgba(0,0,0,0.6);
  --transition:   all 0.28s cubic-bezier(0.34,1.2,0.64,1);
  --transition-f: all 0.2s cubic-bezier(0.4,0,0.2,1);
}

/* ═══════════════════════════════════════════════════════════════
   RESET & BASE
═══════════════════════════════════════════════════════════════ */
*,*::before,*::after { box-sizing:border-box; margin:0; padding:0; }

html { height:100%; }

body {
  font-family: 'Inter', system-ui, sans-serif;
  background: var(--c-bg);
  color: var(--c-text);
  height: 100vh;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
}

/* Animated background mesh */
body::before {
  content:'';
  position:fixed;
  inset:0;
  background:
    radial-gradient(ellipse 80% 50% at 20% 10%, rgba(108,99,255,0.12) 0%, transparent 60%),
    radial-gradient(ellipse 60% 40% at 80% 80%, rgba(67,233,123,0.06) 0%, transparent 55%),
    radial-gradient(ellipse 50% 60% at 70% 20%, rgba(255,95,109,0.05) 0%, transparent 50%);
  pointer-events:none;
  z-index:0;
  animation: meshPulse 12s ease-in-out infinite alternate;
}

@keyframes meshPulse {
  0%   { opacity: 0.7; }
  100% { opacity: 1.0; }
}

/* Floating orbs */
.orb {
  position:fixed;
  border-radius:50%;
  filter:blur(80px);
  pointer-events:none;
  z-index:0;
  animation: orbFloat 18s ease-in-out infinite alternate;
}
.orb1 { width:400px; height:400px; top:-100px; left:-80px;
         background:rgba(108,99,255,0.08); animation-delay:0s; }
.orb2 { width:300px; height:300px; bottom:-80px; right:60px;
         background:rgba(67,233,123,0.06); animation-delay:-6s; }
.orb3 { width:250px; height:250px; top:40%; right:-60px;
         background:rgba(255,95,109,0.05); animation-delay:-12s; }

@keyframes orbFloat {
  0%   { transform:translate(0,0) scale(1); }
  100% { transform:translate(30px,-40px) scale(1.15); }
}

/* ═══════════════════════════════════════════════════════════════
   SCROLLBAR
═══════════════════════════════════════════════════════════════ */
::-webkit-scrollbar { width:6px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:var(--c-surface3); border-radius:99px; }
::-webkit-scrollbar-thumb:hover { background:var(--c-accent); }

/* ═══════════════════════════════════════════════════════════════
   SCREENS
═══════════════════════════════════════════════════════════════ */
.screen {
  position:fixed;
  inset:0;
  display:flex;
  align-items:center;
  justify-content:center;
  z-index:10;
  opacity:1;
  transform:translateY(0) scale(1);
  transition: opacity 0.45s cubic-bezier(0.4,0,0.2,1),
              transform 0.45s cubic-bezier(0.4,0,0.2,1);
}
.screen.hidden {
  opacity:0;
  transform:translateY(24px) scale(0.97);
  pointer-events:none;
}

/* ═══════════════════════════════════════════════════════════════
   AUTH CARD
═══════════════════════════════════════════════════════════════ */
.auth-card {
  width: 420px;
  background: rgba(19,19,26,0.85);
  border: 1px solid var(--c-border2);
  border-radius: var(--radius-xl);
  padding: 44px 40px 36px;
  backdrop-filter: var(--blur);
  box-shadow: var(--shadow-lg),
              0 0 0 1px rgba(108,99,255,0.1),
              inset 0 1px 0 rgba(255,255,255,0.06);
  position:relative;
  overflow:hidden;
  animation: cardIn 0.6s cubic-bezier(0.34,1.2,0.64,1) both;
}

@keyframes cardIn {
  from { opacity:0; transform:translateY(40px) scale(0.94); }
  to   { opacity:1; transform:translateY(0) scale(1); }
}

.auth-card::before {
  content:'';
  position:absolute;
  top:-1px; left:10%; right:10%; height:1px;
  background:linear-gradient(90deg,transparent,rgba(108,99,255,0.6),transparent);
}

/* ── Logo ── */
.logo {
  display:flex;
  align-items:center;
  gap:12px;
  margin-bottom:8px;
  justify-content:center;
}

.logo-icon {
  width:52px; height:52px;
  background:linear-gradient(135deg,#6c63ff 0%,#a78bfa 50%,#43e97b 100%);
  border-radius:16px;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:26px;
  box-shadow:0 8px 24px rgba(108,99,255,0.4);
  animation: logoFloat 3s ease-in-out infinite alternate;
  flex-shrink:0;
}

@keyframes logoFloat {
  0%   { transform:translateY(0) rotate(-2deg); box-shadow:0 8px 24px rgba(108,99,255,0.4); }
  100% { transform:translateY(-4px) rotate(2deg); box-shadow:0 14px 36px rgba(108,99,255,0.55); }
}

.logo-text {
  display:flex;
  flex-direction:column;
}

.logo-name {
  font-size:22px;
  font-weight:800;
  letter-spacing:-0.5px;
  background:linear-gradient(135deg,#fff 0%,#a78bfa 100%);
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent;
  background-clip:text;
  line-height:1.1;
}

.logo-tagline {
  font-size:11px;
  font-weight:500;
  color:var(--c-text2);
  letter-spacing:0.5px;
  text-transform:uppercase;
}

.auth-subtitle {
  text-align:center;
  color:var(--c-text2);
  font-size:13.5px;
  font-weight:400;
  margin-bottom:28px;
  margin-top:4px;
}

/* ── Form elements ── */
.field {
  margin-bottom:14px;
}

.field label {
  display:block;
  font-size:12px;
  font-weight:600;
  color:var(--c-text2);
  text-transform:uppercase;
  letter-spacing:0.6px;
  margin-bottom:7px;
}

.field input, .field textarea, .field select {
  width:100%;
  padding:13px 16px;
  background:rgba(255,255,255,0.04);
  border:1.5px solid var(--c-border2);
  border-radius:var(--radius-sm);
  color:var(--c-text);
  font-family:inherit;
  font-size:14px;
  font-weight:400;
  outline:none;
  transition: border-color 0.22s ease,
              background 0.22s ease,
              box-shadow 0.22s ease;
}

.field input:focus, .field textarea:focus, .field select:focus {
  border-color:var(--c-accent);
  background:rgba(108,99,255,0.07);
  box-shadow:0 0 0 4px rgba(108,99,255,0.15);
}

.field input::placeholder { color:var(--c-text2); opacity:0.6; }
.field textarea { resize:none; min-height:76px; line-height:1.5; }

.field select {
  appearance:none;
  cursor:pointer;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' fill='none'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%238888aa' stroke-width='1.5' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat:no-repeat;
  background-position:right 14px center;
  padding-right:40px;
}

.field select option { background:var(--c-surface2); color:var(--c-text); }

/* ── Buttons ── */
.btn {
  display:inline-flex;
  align-items:center;
  justify-content:center;
  gap:8px;
  padding:13px 22px;
  border-radius:var(--radius-sm);
  font-family:inherit;
  font-size:14px;
  font-weight:600;
  cursor:pointer;
  border:none;
  outline:none;
  transition: var(--transition);
  user-select:none;
  position:relative;
  overflow:hidden;
}

.btn::after {
  content:'';
  position:absolute;
  inset:0;
  background:linear-gradient(135deg,rgba(255,255,255,0.1) 0%,transparent 60%);
  opacity:0;
  transition:opacity 0.2s ease;
}

.btn:hover::after { opacity:1; }
.btn:active { transform:scale(0.96) !important; }

.btn-primary {
  background:linear-gradient(135deg,#6c63ff 0%,#a78bfa 100%);
  color:#fff;
  width:100%;
  box-shadow:0 4px 20px rgba(108,99,255,0.4);
  letter-spacing:0.2px;
}

.btn-primary:hover {
  transform:translateY(-2px);
  box-shadow:0 8px 30px rgba(108,99,255,0.55);
}

.btn-ghost {
  background:transparent;
  color:var(--c-accent2);
  padding:0;
  font-size:13px;
  font-weight:500;
}

.btn-ghost:hover { color:#fff; transform:none; }

.btn-danger {
  background:rgba(255,95,109,0.12);
  color:var(--c-danger);
  border:1px solid rgba(255,95,109,0.2);
}

.btn-danger:hover {
  background:rgba(255,95,109,0.2);
  transform:translateY(-1px);
}

.btn-icon {
  width:32px; height:32px;
  padding:0;
  border-radius:8px;
  background:rgba(255,255,255,0.05);
  color:var(--c-text2);
  border:1px solid var(--c-border);
  font-size:14px;
}

.btn-icon:hover {
  background:rgba(108,99,255,0.15);
  color:var(--c-accent2);
  border-color:rgba(108,99,255,0.3);
  transform:scale(1.08);
}

/* ── Auth toggle row ── */
.auth-footer {
  margin-top:20px;
  text-align:center;
  font-size:13px;
  color:var(--c-text2);
  display:flex;
  align-items:center;
  justify-content:center;
  gap:6px;
}

/* ── Error message ── */
.error-msg {
  background:rgba(255,95,109,0.1);
  border:1px solid rgba(255,95,109,0.25);
  color:#ff8c95;
  border-radius:var(--radius-sm);
  padding:10px 14px;
  font-size:13px;
  font-weight:500;
  margin-bottom:14px;
  display:none;
  animation: errIn 0.3s cubic-bezier(0.34,1.2,0.64,1);
}

@keyframes errIn {
  from { opacity:0; transform:translateY(-6px) scale(0.98); }
  to   { opacity:1; transform:translateY(0) scale(1); }
}

.error-msg.visible { display:block; }

/* ── Divider ── */
.divider {
  display:flex;
  align-items:center;
  gap:12px;
  margin:20px 0;
}

.divider::before,.divider::after {
  content:'';
  flex:1;
  height:1px;
  background:var(--c-border2);
}

.divider span {
  font-size:11px;
  color:var(--c-text2);
  font-weight:500;
  text-transform:uppercase;
  letter-spacing:0.5px;
}

/* ═══════════════════════════════════════════════════════════════
   MAIN APP LAYOUT
═══════════════════════════════════════════════════════════════ */
#app-screen {
  align-items:stretch;
  z-index:5;
}

.app-layout {
  display:flex;
  width:100vw;
  height:100vh;
  position:relative;
  z-index:2;
}

/* ── Sidebar ── */
.sidebar {
  width:240px;
  flex-shrink:0;
  background:rgba(13,13,19,0.8);
  border-right:1px solid var(--c-border);
  backdrop-filter:blur(20px);
  display:flex;
  flex-direction:column;
  padding:24px 16px;
  gap:4px;
  overflow-y:auto;
  transition:var(--transition-f);
}

.sidebar-logo {
  display:flex;
  align-items:center;
  gap:10px;
  padding:8px 10px 20px;
  border-bottom:1px solid var(--c-border);
  margin-bottom:12px;
}

.sidebar-logo-icon {
  width:38px; height:38px;
  background:linear-gradient(135deg,#6c63ff,#a78bfa);
  border-radius:11px;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:18px;
  box-shadow:0 4px 12px rgba(108,99,255,0.35);
  flex-shrink:0;
}

.sidebar-logo-text {
  font-size:16px;
  font-weight:800;
  background:linear-gradient(135deg,#fff,#a78bfa);
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent;
  background-clip:text;
  letter-spacing:-0.3px;
}

/* Sidebar nav sections */
.nav-section-label {
  font-size:10.5px;
  font-weight:700;
  color:var(--c-text2);
  text-transform:uppercase;
  letter-spacing:1px;
  padding:10px 12px 4px;
  opacity:0.7;
}

.nav-item {
  display:flex;
  align-items:center;
  gap:10px;
  padding:10px 12px;
  border-radius:var(--radius-sm);
  cursor:pointer;
  font-size:13.5px;
  font-weight:500;
  color:var(--c-text2);
  transition:var(--transition-f);
  user-select:none;
  position:relative;
}

.nav-item:hover {
  background:rgba(255,255,255,0.05);
  color:var(--c-text);
}

.nav-item.active {
  background:rgba(108,99,255,0.18);
  color:var(--c-accent2);
}

.nav-item.active::before {
  content:'';
  position:absolute;
  left:0; top:20%; bottom:20%;
  width:3px;
  background:linear-gradient(180deg,#6c63ff,#a78bfa);
  border-radius:0 4px 4px 0;
}

.nav-item .nav-icon {
  font-size:15px;
  width:22px;
  text-align:center;
}

.nav-badge {
  margin-left:auto;
  background:rgba(108,99,255,0.25);
  color:var(--c-accent2);
  font-size:10px;
  font-weight:700;
  padding:2px 7px;
  border-radius:99px;
}

/* Stats block */
.stats-block {
  margin:16px 4px 0;
  background:rgba(255,255,255,0.03);
  border:1px solid var(--c-border);
  border-radius:var(--radius);
  padding:14px;
}

.stats-title {
  font-size:10.5px;
  font-weight:700;
  text-transform:uppercase;
  letter-spacing:1px;
  color:var(--c-text2);
  opacity:0.7;
  margin-bottom:12px;
}

.stat-row {
  display:flex;
  align-items:center;
  justify-content:space-between;
  margin-bottom:8px;
}

.stat-row:last-child { margin-bottom:0; }

.stat-label {
  font-size:12px;
  color:var(--c-text2);
  font-weight:500;
}

.stat-val {
  font-size:14px;
  font-weight:700;
  color:var(--c-text);
}

.stat-val.green  { color:var(--c-success); }
.stat-val.yellow { color:var(--c-med); }
.stat-val.red    { color:var(--c-danger); }

/* Progress bar */
.progress-bar {
  height:4px;
  background:rgba(255,255,255,0.06);
  border-radius:99px;
  overflow:hidden;
  margin-top:12px;
}

.progress-fill {
  height:100%;
  background:linear-gradient(90deg,#6c63ff,#43e97b);
  border-radius:99px;
  transition:width 0.7s cubic-bezier(0.4,0,0.2,1);
}

/* Sidebar bottom */
.sidebar-bottom {
  margin-top:auto;
  padding-top:16px;
  border-top:1px solid var(--c-border);
}

.user-chip {
  display:flex;
  align-items:center;
  gap:10px;
  padding:10px;
  border-radius:var(--radius-sm);
  background:rgba(255,255,255,0.04);
  margin-bottom:8px;
}

.user-avatar {
  width:34px; height:34px;
  border-radius:50%;
  background:linear-gradient(135deg,#6c63ff,#43e97b);
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:14px;
  font-weight:700;
  color:#fff;
  flex-shrink:0;
}

.user-info .user-name {
  font-size:13px;
  font-weight:600;
  color:var(--c-text);
  line-height:1.2;
}

.user-info .user-role {
  font-size:11px;
  color:var(--c-text2);
}

.logout-btn {
  display:flex;
  align-items:center;
  gap:8px;
  width:100%;
  padding:9px 12px;
  border-radius:var(--radius-sm);
  background:transparent;
  border:none;
  color:var(--c-text2);
  font-family:inherit;
  font-size:13px;
  font-weight:500;
  cursor:pointer;
  transition:var(--transition-f);
}

.logout-btn:hover {
  background:rgba(255,95,109,0.1);
  color:var(--c-danger);
}

/* ── Main content ── */
.main-content {
  flex:1;
  display:flex;
  flex-direction:column;
  overflow:hidden;
}

/* Top bar */
.topbar {
  padding:20px 28px 0;
  display:flex;
  align-items:flex-start;
  gap:16px;
  flex-wrap:wrap;
}

.topbar-left { flex:1; }

.topbar-greeting {
  font-size:13px;
  color:var(--c-text2);
  font-weight:400;
  margin-bottom:2px;
}

.topbar-title {
  font-size:26px;
  font-weight:800;
  letter-spacing:-0.5px;
  color:var(--c-text);
  line-height:1.1;
}

.topbar-right {
  display:flex;
  align-items:center;
  gap:10px;
}

.search-bar {
  display:flex;
  align-items:center;
  gap:8px;
  background:rgba(255,255,255,0.05);
  border:1.5px solid var(--c-border2);
  border-radius:var(--radius-sm);
  padding:0 14px;
  height:40px;
  transition:var(--transition-f);
  width:220px;
}

.search-bar:focus-within {
  border-color:var(--c-accent);
  background:rgba(108,99,255,0.07);
  box-shadow:0 0 0 4px rgba(108,99,255,0.12);
  width:260px;
}

.search-bar input {
  flex:1;
  background:none;
  border:none;
  color:var(--c-text);
  font-family:inherit;
  font-size:13.5px;
  outline:none;
}

.search-bar input::placeholder { color:var(--c-text2); opacity:0.7; }

.search-icon { font-size:14px; opacity:0.5; flex-shrink:0; }

.add-btn {
  display:flex;
  align-items:center;
  gap:7px;
  padding:0 18px;
  height:40px;
  border-radius:var(--radius-sm);
  background:linear-gradient(135deg,#6c63ff,#a78bfa);
  color:#fff;
  border:none;
  font-family:inherit;
  font-size:13.5px;
  font-weight:600;
  cursor:pointer;
  box-shadow:0 4px 16px rgba(108,99,255,0.4);
  transition:var(--transition);
  white-space:nowrap;
}

.add-btn:hover {
  transform:translateY(-2px);
  box-shadow:0 8px 28px rgba(108,99,255,0.55);
}

.add-btn:active { transform:scale(0.96) translateY(0); }

.add-btn .plus {
  font-size:20px;
  font-weight:300;
  line-height:1;
  margin-top:-1px;
}

/* Filter chips */
.filter-row {
  display:flex;
  align-items:center;
  gap:6px;
  padding:16px 28px 0;
  flex-wrap:wrap;
}

.filter-chip {
  padding:6px 14px;
  border-radius:99px;
  font-size:12.5px;
  font-weight:500;
  color:var(--c-text2);
  background:rgba(255,255,255,0.04);
  border:1px solid var(--c-border2);
  cursor:pointer;
  transition:var(--transition-f);
  user-select:none;
}

.filter-chip:hover {
  background:rgba(255,255,255,0.08);
  color:var(--c-text);
}

.filter-chip.active {
  background:rgba(108,99,255,0.2);
  color:var(--c-accent2);
  border-color:rgba(108,99,255,0.4);
}

.sort-select {
  margin-left:auto;
  background:rgba(255,255,255,0.04);
  border:1px solid var(--c-border2);
  border-radius:var(--radius-sm);
  color:var(--c-text2);
  font-family:inherit;
  font-size:12px;
  padding:5px 28px 5px 10px;
  outline:none;
  cursor:pointer;
  appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' fill='none'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%238888aa' stroke-width='1.5' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat:no-repeat;
  background-position:right 10px center;
  transition:var(--transition-f);
}

.sort-select:focus {
  border-color:var(--c-accent);
  color:var(--c-text);
}

.sort-select option { background:var(--c-surface); }

/* ── Inline Add Panel ── */
.add-panel {
  margin:14px 28px 0;
  background:rgba(108,99,255,0.07);
  border:1.5px solid rgba(108,99,255,0.25);
  border-radius:var(--radius-lg);
  padding:20px 22px;
  backdrop-filter:blur(10px);
  overflow:hidden;
  max-height:0;
  opacity:0;
  padding-top:0;
  padding-bottom:0;
  transition: max-height 0.5s cubic-bezier(0.4,0,0.2,1),
              opacity    0.4s cubic-bezier(0.4,0,0.2,1),
              padding    0.4s cubic-bezier(0.4,0,0.2,1),
              border     0.3s ease;
}

.add-panel.open {
  max-height:500px;
  opacity:1;
  padding:20px 22px;
}

.add-panel-title {
  font-size:15px;
  font-weight:700;
  color:var(--c-text);
  margin-bottom:14px;
  display:flex;
  align-items:center;
  gap:8px;
}

.add-panel-grid {
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:12px;
  margin-bottom:12px;
}

.add-panel-grid .field { margin-bottom:0; }

.add-panel-title-input {
  width:100%;
  padding:11px 15px;
  background:rgba(255,255,255,0.05);
  border:1.5px solid var(--c-border2);
  border-radius:var(--radius-sm);
  color:var(--c-text);
  font-family:inherit;
  font-size:14.5px;
  font-weight:500;
  outline:none;
  margin-bottom:12px;
  transition:var(--transition-f);
}

.add-panel-title-input:focus {
  border-color:var(--c-accent);
  background:rgba(108,99,255,0.07);
  box-shadow:0 0 0 4px rgba(108,99,255,0.15);
}

.add-panel-title-input::placeholder { color:var(--c-text2); opacity:0.6; }

.add-panel-actions {
  display:flex;
  align-items:center;
  gap:8px;
  justify-content:flex-end;
  margin-top:14px;
}

.add-panel-actions .btn-cancel {
  padding:9px 18px;
  border-radius:var(--radius-sm);
  background:transparent;
  border:1px solid var(--c-border2);
  color:var(--c-text2);
  font-family:inherit;
  font-size:13px;
  font-weight:500;
  cursor:pointer;
  transition:var(--transition-f);
}

.add-panel-actions .btn-cancel:hover {
  background:rgba(255,255,255,0.05);
  color:var(--c-text);
}

.add-panel-actions .btn-save {
  padding:9px 22px;
  border-radius:var(--radius-sm);
  background:linear-gradient(135deg,#6c63ff,#a78bfa);
  color:#fff;
  border:none;
  font-family:inherit;
  font-size:13px;
  font-weight:600;
  cursor:pointer;
  box-shadow:0 4px 16px rgba(108,99,255,0.35);
  transition:var(--transition);
}

.add-panel-actions .btn-save:hover {
  transform:translateY(-1px);
  box-shadow:0 6px 22px rgba(108,99,255,0.5);
}

.add-panel-actions .btn-save:active { transform:scale(0.96); }

/* ── Task list ── */
.task-list-container {
  flex:1;
  overflow-y:auto;
  padding:14px 28px 28px;
}

/* Empty state */
.empty-state {
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  height:100%;
  min-height:260px;
  gap:14px;
  opacity:0.7;
  animation:fadeIn 0.5s ease;
}

.empty-icon {
  font-size:52px;
  animation:emptyBob 3s ease-in-out infinite alternate;
}

@keyframes emptyBob {
  0%   { transform:translateY(0); }
  100% { transform:translateY(-8px); }
}

.empty-title {
  font-size:17px;
  font-weight:700;
  color:var(--c-text);
}

.empty-sub {
  font-size:13.5px;
  color:var(--c-text2);
}

/* Task card */
.task-card {
  display:flex;
  align-items:flex-start;
  gap:14px;
  background:rgba(255,255,255,0.03);
  border:1px solid var(--c-border);
  border-radius:var(--radius);
  padding:16px 18px;
  margin-bottom:10px;
  position:relative;
  overflow:hidden;
  cursor:default;
  transition: var(--transition-f),
              transform 0.25s cubic-bezier(0.34,1.2,0.64,1),
              box-shadow 0.25s ease;
  animation: taskIn 0.4s cubic-bezier(0.34,1.2,0.64,1) both;
}

@keyframes taskIn {
  from { opacity:0; transform:translateY(12px) scale(0.97); }
  to   { opacity:1; transform:translateY(0) scale(1); }
}

.task-card:hover {
  background:rgba(255,255,255,0.05);
  border-color:var(--c-border2);
  transform:translateY(-2px);
  box-shadow:0 8px 32px rgba(0,0,0,0.35);
}

/* Priority left stripe */
.task-card::before {
  content:'';
  position:absolute;
  left:0; top:0; bottom:0;
  width:4px;
  border-radius:var(--radius) 0 0 var(--radius);
}

.task-card.p-high::before   { background:var(--c-high); }
.task-card.p-medium::before { background:var(--c-med); }
.task-card.p-low::before    { background:var(--c-low); }

/* Shimmer on hover */
.task-card::after {
  content:'';
  position:absolute;
  inset:0;
  background:linear-gradient(135deg,rgba(255,255,255,0.025) 0%,transparent 60%);
  opacity:0;
  transition:opacity 0.25s ease;
}

.task-card:hover::after { opacity:1; }

/* Checkbox */
.task-check-wrap {
  flex-shrink:0;
  padding-top:2px;
}

.task-checkbox {
  width:20px; height:20px;
  border-radius:6px;
  border:2px solid var(--c-border2);
  background:transparent;
  cursor:pointer;
  appearance:none;
  display:flex;
  align-items:center;
  justify-content:center;
  transition:var(--transition);
  position:relative;
  flex-shrink:0;
}

.task-checkbox:hover {
  border-color:var(--c-accent);
  background:rgba(108,99,255,0.1);
  transform:scale(1.1);
}

.task-checkbox:checked {
  background:linear-gradient(135deg,#6c63ff,#a78bfa);
  border-color:transparent;
  box-shadow:0 2px 8px rgba(108,99,255,0.4);
}

.task-checkbox:checked::after {
  content:'✓';
  position:absolute;
  color:#fff;
  font-size:12px;
  font-weight:700;
  line-height:1;
}

/* Task body */
.task-body { flex:1; min-width:0; }

.task-title {
  font-size:14.5px;
  font-weight:600;
  color:var(--c-text);
  line-height:1.3;
  transition:var(--transition-f);
  word-break:break-word;
}

.task-card.done .task-title {
  color:var(--c-text2);
  text-decoration:line-through;
  text-decoration-color:rgba(136,136,170,0.4);
}

.task-desc {
  font-size:12.5px;
  color:var(--c-text2);
  margin-top:4px;
  line-height:1.5;
  word-break:break-word;
}

/* Task meta row */
.task-meta {
  display:flex;
  align-items:center;
  gap:8px;
  margin-top:10px;
  flex-wrap:wrap;
}

.task-tag {
  display:inline-flex;
  align-items:center;
  gap:4px;
  padding:3px 9px;
  border-radius:99px;
  font-size:11px;
  font-weight:600;
  letter-spacing:0.2px;
}

.tag-cat {
  background:rgba(255,255,255,0.06);
  color:var(--c-text2);
  border:1px solid var(--c-border);
}

.tag-high   { background:rgba(255,95,109,0.15);  color:#ff8c95; }
.tag-medium { background:rgba(255,195,113,0.15); color:#ffd98a; }
.tag-low    { background:rgba(67,233,123,0.12);  color:#6ceea0; }

.tag-due {
  background:rgba(255,255,255,0.04);
  color:var(--c-text2);
  border:1px solid var(--c-border);
}

.tag-due.overdue  { color:#ff8c95; background:rgba(255,95,109,0.12); border-color:rgba(255,95,109,0.2); }
.tag-due.today    { color:#ffd98a; background:rgba(255,195,113,0.12); border-color:rgba(255,195,113,0.2); }
.tag-due.soon     { color:#ffd98a; }

/* Task actions */
.task-actions {
  display:flex;
  align-items:center;
  gap:6px;
  flex-shrink:0;
  opacity:0;
  transform:translateX(8px);
  transition:var(--transition-f);
}

.task-card:hover .task-actions {
  opacity:1;
  transform:translateX(0);
}

/* ── Toast notification ── */
.toast {
  position:fixed;
  bottom:28px;
  left:50%;
  transform:translateX(-50%) translateY(20px);
  background:rgba(30,30,42,0.95);
  border:1px solid var(--c-border2);
  border-radius:var(--radius);
  padding:12px 22px;
  color:var(--c-text);
  font-size:13.5px;
  font-weight:500;
  backdrop-filter:blur(16px);
  box-shadow:var(--shadow);
  z-index:1000;
  opacity:0;
  pointer-events:none;
  display:flex;
  align-items:center;
  gap:10px;
  transition:all 0.35s cubic-bezier(0.34,1.2,0.64,1);
}

.toast.show {
  opacity:1;
  transform:translateX(-50%) translateY(0);
}

.toast-icon { font-size:16px; }

/* ── Loading overlay ── */
.loader-overlay {
  position:fixed;
  inset:0;
  background:var(--c-bg);
  display:flex;
  align-items:center;
  justify-content:center;
  z-index:100;
  flex-direction:column;
  gap:18px;
  transition:opacity 0.5s ease;
}

.loader-overlay.fade-out { opacity:0; pointer-events:none; }

.loader-logo {
  width:64px; height:64px;
  background:linear-gradient(135deg,#6c63ff,#a78bfa,#43e97b);
  border-radius:20px;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:32px;
  box-shadow:0 16px 40px rgba(108,99,255,0.4);
  animation:loaderPulse 1.2s ease-in-out infinite alternate;
}

@keyframes loaderPulse {
  0%   { transform:scale(1) rotate(-3deg);   box-shadow:0 16px 40px rgba(108,99,255,0.4); }
  100% { transform:scale(1.08) rotate(3deg); box-shadow:0 20px 56px rgba(108,99,255,0.6); }
}

.loader-text {
  font-size:16px;
  font-weight:700;
  background:linear-gradient(135deg,#fff,#a78bfa);
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent;
  background-clip:text;
  letter-spacing:-0.2px;
}

.loader-dots {
  display:flex;
  gap:6px;
}

.loader-dots span {
  width:7px; height:7px;
  border-radius:50%;
  background:var(--c-accent);
  animation:dotBounce 1.2s ease-in-out infinite;
}

.loader-dots span:nth-child(2) { animation-delay:0.15s; }
.loader-dots span:nth-child(3) { animation-delay:0.3s; }

@keyframes dotBounce {
  0%,80%,100% { transform:translateY(0) scale(1); opacity:0.6; }
  40%          { transform:translateY(-10px) scale(1.15); opacity:1; }
}

/* ── Misc animations ── */
@keyframes fadeIn {
  from { opacity:0; }
  to   { opacity:1; }
}

@keyframes slideUp {
  from { opacity:0; transform:translateY(16px); }
  to   { opacity:1; transform:translateY(0); }
}

/* Checkbox pulse animation */
@keyframes checkPop {
  0%   { transform:scale(1); }
  40%  { transform:scale(1.3); }
  70%  { transform:scale(0.9); }
  100% { transform:scale(1); }
}

.check-popped { animation:checkPop 0.4s cubic-bezier(0.34,1.56,0.64,1); }

/* Skeleton loading */
.skeleton {
  background:linear-gradient(90deg,
    rgba(255,255,255,0.04) 25%,
    rgba(255,255,255,0.08) 50%,
    rgba(255,255,255,0.04) 75%);
  background-size:200% 100%;
  animation:shimmer 1.4s ease-in-out infinite;
  border-radius:6px;
}

@keyframes shimmer {
  0%   { background-position:200% 0; }
  100% { background-position:-200% 0; }
}
</style>
</head>

<body>

<!-- ── Background orbs ── -->
<div class="orb orb1"></div>
<div class="orb orb2"></div>
<div class="orb orb3"></div>

<!-- ── Loading screen ── -->
<div class="loader-overlay" id="loader">
  <div class="loader-logo">✅</div>
  <div class="loader-text">To-Do Core</div>
  <div class="loader-dots"><span></span><span></span><span></span></div>
</div>

<!-- ══════════════════════════════════════════════════════════════
     LOGIN SCREEN
══════════════════════════════════════════════════════════════ -->
<div class="screen hidden" id="login-screen">
  <div class="auth-card">

    <div class="logo">
      <div class="logo-icon">✅</div>
      <div class="logo-text">
        <span class="logo-name">To-Do Core</span>
        <span class="logo-tagline">Your tasks. Your flow.</span>
      </div>
    </div>

    <p class="auth-subtitle" id="login-subtitle">Sign in to continue</p>

    <div class="error-msg" id="login-error"></div>

    <div class="field">
      <label>Username</label>
      <input type="text" id="login-user" placeholder="Enter your username" autocomplete="username"/>
    </div>

    <div class="field">
      <label>Password</label>
      <input type="password" id="login-pass" placeholder="Enter your password" autocomplete="current-password"/>
    </div>

    <br/>
    <button class="btn btn-primary" id="login-btn">Sign In</button>

    <div class="divider"><span>or</span></div>

    <div class="auth-footer">
      <span>Don't have an account?</span>
      <button class="btn btn-ghost" onclick="showRegister()">Create one</button>
    </div>

  </div>
</div>

<!-- ══════════════════════════════════════════════════════════════
     REGISTER SCREEN
══════════════════════════════════════════════════════════════ -->
<div class="screen hidden" id="register-screen">
  <div class="auth-card" style="padding:36px 40px 30px;">

    <div class="logo" style="margin-bottom:6px;">
      <div class="logo-icon" style="width:44px;height:44px;font-size:22px;">✅</div>
      <div class="logo-text">
        <span class="logo-name">To-Do Core</span>
        <span class="logo-tagline">Your tasks. Your flow.</span>
      </div>
    </div>

    <p class="auth-subtitle" style="margin-bottom:20px;">Create your free account</p>

    <div class="error-msg" id="reg-error"></div>

    <div class="field">
      <label>Full Name</label>
      <input type="text" id="reg-name" placeholder="e.g. Rahul Sharma" autocomplete="name"/>
    </div>

    <div class="field">
      <label>Username</label>
      <input type="text" id="reg-user" placeholder="3–20 chars, letters/numbers/underscore" autocomplete="username"/>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
      <div class="field" style="margin-bottom:0;">
        <label>Password</label>
        <input type="password" id="reg-pass" placeholder="Min 6 chars" autocomplete="new-password"/>
      </div>
      <div class="field" style="margin-bottom:0;">
        <label>Confirm</label>
        <input type="password" id="reg-conf" placeholder="Repeat password" autocomplete="new-password"/>
      </div>
    </div>

    <br/>
    <button class="btn btn-primary" id="reg-btn">Create Account</button>

    <div class="divider"><span>or</span></div>

    <div class="auth-footer">
      <span>Already have an account?</span>
      <button class="btn btn-ghost" onclick="showLogin()">Sign In</button>
    </div>

  </div>
</div>

<!-- ══════════════════════════════════════════════════════════════
     MAIN APP SCREEN
══════════════════════════════════════════════════════════════ -->
<div class="screen hidden" id="app-screen">
  <div class="app-layout">

    <!-- ── Sidebar ── -->
    <aside class="sidebar">
      <div class="sidebar-logo">
        <div class="sidebar-logo-icon">✅</div>
        <span class="sidebar-logo-text">To-Do Core</span>
      </div>

      <div class="nav-section-label">Views</div>

      <div class="nav-item active" data-filter="All" onclick="setFilter('All',this)">
        <span class="nav-icon">📋</span> All Tasks
        <span class="nav-badge" id="badge-all">0</span>
      </div>
      <div class="nav-item" data-filter="Today" onclick="setFilter('Today',this)">
        <span class="nav-icon">☀️</span> Today
        <span class="nav-badge" id="badge-today" style="display:none">0</span>
      </div>
      <div class="nav-item" data-filter="Upcoming" onclick="setFilter('Upcoming',this)">
        <span class="nav-icon">📆</span> Upcoming
      </div>
      <div class="nav-item" data-filter="Completed" onclick="setFilter('Completed',this)">
        <span class="nav-icon">✅</span> Completed
      </div>
      <div class="nav-item" data-filter="High Priority" onclick="setFilter('High Priority',this)">
        <span class="nav-icon">🔴</span> High Priority
      </div>

      <div class="nav-section-label" style="margin-top:10px;">Category</div>
      <div class="nav-item active" id="cat-all" data-cat="All" onclick="setCat('All',this)">
        <span class="nav-icon">🌐</span> All
      </div>
      <div class="nav-item" data-cat="Work"     onclick="setCat('Work',this)"><span class="nav-icon">💼</span> Work</div>
      <div class="nav-item" data-cat="Personal" onclick="setCat('Personal',this)"><span class="nav-icon">🏠</span> Personal</div>
      <div class="nav-item" data-cat="Health"   onclick="setCat('Health',this)"><span class="nav-icon">❤️</span> Health</div>
      <div class="nav-item" data-cat="Study"    onclick="setCat('Study',this)"><span class="nav-icon">📚</span> Study</div>
      <div class="nav-item" data-cat="Shopping" onclick="setCat('Shopping',this)"><span class="nav-icon">🛒</span> Shopping</div>
      <div class="nav-item" data-cat="Finance"  onclick="setCat('Finance',this)"><span class="nav-icon">💰</span> Finance</div>
      <div class="nav-item" data-cat="Other"    onclick="setCat('Other',this)"><span class="nav-icon">📌</span> Other</div>

      <!-- Stats -->
      <div class="stats-block" style="margin-top:16px;">
        <div class="stats-title">Progress</div>
        <div class="stat-row">
          <span class="stat-label">Total</span>
          <span class="stat-val" id="st-total">0</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Done</span>
          <span class="stat-val green" id="st-done">0</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Pending</span>
          <span class="stat-val yellow" id="st-pending">0</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Overdue</span>
          <span class="stat-val red" id="st-overdue">0</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" id="st-progress" style="width:0%"></div>
        </div>
      </div>

      <div class="sidebar-bottom">
        <div class="user-chip">
          <div class="user-avatar" id="user-avatar">?</div>
          <div class="user-info">
            <div class="user-name" id="user-display">—</div>
            <div class="user-role">Personal Account</div>
          </div>
        </div>
        <button class="logout-btn" onclick="logout()">
          🚪 &nbsp;Log Out
        </button>
      </div>
    </aside>

    <!-- ── Main Content ── -->
    <div class="main-content">

      <!-- Top bar -->
      <div class="topbar">
        <div class="topbar-left">
          <div class="topbar-greeting" id="topbar-greeting">Good morning!</div>
          <div class="topbar-title" id="topbar-title">All Tasks</div>
        </div>
        <div class="topbar-right">
          <div class="search-bar">
            <span class="search-icon">🔍</span>
            <input type="text" id="search-input" placeholder="Search tasks…" oninput="renderTasks()"/>
          </div>
          <button class="add-btn" onclick="toggleAddPanel()">
            <span class="plus">+</span> New Task
          </button>
        </div>
      </div>

      <!-- Inline Add Panel -->
      <div class="add-panel" id="add-panel">
        <div class="add-panel-title">✨ New Task</div>
        <input class="add-panel-title-input" type="text" id="new-title"
               placeholder="What needs to be done?" maxlength="120"/>
        <div class="field" style="margin-bottom:10px;">
          <label>Description (optional)</label>
          <textarea id="new-desc" rows="2" placeholder="Add details…"></textarea>
        </div>
        <div class="add-panel-grid">
          <div class="field">
            <label>Category</label>
            <select id="new-cat">
              <option>Personal</option><option>Work</option><option>Health</option>
              <option>Study</option><option>Shopping</option><option>Finance</option>
              <option>Other</option>
            </select>
          </div>
          <div class="field">
            <label>Priority</label>
            <select id="new-pri">
              <option value="Medium">Medium</option>
              <option value="High">High</option>
              <option value="Low">Low</option>
            </select>
          </div>
          <div class="field">
            <label>Due Date</label>
            <input type="date" id="new-due"/>
          </div>
        </div>
        <div class="add-panel-actions">
          <button class="btn-cancel" onclick="closeAddPanel()">Cancel</button>
          <button class="btn-save" onclick="addTask()">Add Task ✓</button>
        </div>
      </div>

      <!-- Filter chips -->
      <div class="filter-row">
        <span class="filter-chip active" onclick="setFilter('All',null,this)">All</span>
        <span class="filter-chip" onclick="setFilter('Today',null,this)">Today</span>
        <span class="filter-chip" onclick="setFilter('Upcoming',null,this)">Upcoming</span>
        <span class="filter-chip" onclick="setFilter('Completed',null,this)">Completed</span>
        <span class="filter-chip" onclick="setFilter('High Priority',null,this)">🔴 High</span>
        <select class="sort-select" id="sort-select" onchange="renderTasks()">
          <option value="due">Sort: Due Date</option>
          <option value="priority">Sort: Priority</option>
          <option value="created">Sort: Newest</option>
        </select>
      </div>

      <!-- Task list -->
      <div class="task-list-container" id="task-list"></div>

    </div>
  </div>
</div>

<!-- ── Toast ── -->
<div class="toast" id="toast">
  <span class="toast-icon" id="toast-icon">✅</span>
  <span id="toast-msg"></span>
</div>

<script>
// ═══════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════
let tasks        = [];
let currentUser  = null;
let currentFilter = 'All';
let currentCat    = 'All';
let editingId     = null;
let addPanelOpen  = false;
let toastTimer    = null;

const PRIO_ORDER = { High:0, Medium:1, Low:2 };

// ═══════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════
window.addEventListener('load', () => {
  setTimeout(() => {
    document.getElementById('loader').classList.add('fade-out');
    setTimeout(() => {
      document.getElementById('loader').style.display = 'none';
      showLogin();
    }, 500);
  }, 1400);
});

// ═══════════════════════════════════════════════════════════════
// SCREEN TRANSITIONS
// ═══════════════════════════════════════════════════════════════
function showScreen(id) {
  ['login-screen','register-screen','app-screen'].forEach(s => {
    document.getElementById(s).classList.add('hidden');
  });
  const el = document.getElementById(id);
  el.classList.remove('hidden');
}

function showLogin() {
  clearErr('login-error');
  showScreen('login-screen');
  setTimeout(() => document.getElementById('login-user').focus(), 300);
}

function showRegister() {
  clearErr('reg-error');
  showScreen('register-screen');
  setTimeout(() => document.getElementById('reg-name').focus(), 300);
}

// ═══════════════════════════════════════════════════════════════
// AUTH — login
// ═══════════════════════════════════════════════════════════════
document.getElementById('login-btn').addEventListener('click', doLogin);
document.addEventListener('keydown', e => {
  const ls = document.getElementById('login-screen');
  if (!ls.classList.contains('hidden') && e.key === 'Enter') doLogin();
  const rs = document.getElementById('register-screen');
  if (!rs.classList.contains('hidden') && e.key === 'Enter') doRegister();
});

function doLogin() {
  const u = val('login-user');
  const p = val('login-pass');
  if (!u || !p) { showErr('login-error','Please fill in both fields.'); return; }

  animBtn('login-btn', 'Signing in…');
  fetch('/api/login', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({username:u, password:p})
  })
  .then(r => r.json())
  .then(d => {
    resetBtn('login-btn','Sign In');
    if (d.ok) {
      currentUser = d;
      launchApp();
    } else {
      showErr('login-error', d.error || 'Login failed.');
    }
  })
  .catch(() => { resetBtn('login-btn','Sign In'); showErr('login-error','Server error. Try again.'); });
}

// AUTH — register
document.getElementById('reg-btn').addEventListener('click', doRegister);

function doRegister() {
  const name  = val('reg-name');
  const uname = val('reg-user');
  const pw    = val('reg-pass');
  const conf  = val('reg-conf');
  if (!name||!uname||!pw||!conf) { showErr('reg-error','All fields are required.'); return; }
  if (pw !== conf) { showErr('reg-error','Passwords do not match.'); return; }
  if (pw.length < 6) { showErr('reg-error','Password must be at least 6 characters.'); return; }
  if (!/^\w{3,20}$/.test(uname)) { showErr('reg-error','Username: 3–20 chars, letters/numbers/underscore.'); return; }

  animBtn('reg-btn','Creating…');
  fetch('/api/register', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name, username:uname, password:pw})
  })
  .then(r => r.json())
  .then(d => {
    resetBtn('reg-btn','Create Account');
    if (d.ok) {
      currentUser = d;
      launchApp();
    } else {
      showErr('reg-error', d.error || 'Registration failed.');
    }
  })
  .catch(() => { resetBtn('reg-btn','Create Account'); showErr('reg-error','Server error. Try again.'); });
}

// ═══════════════════════════════════════════════════════════════
// LAUNCH APP
// ═══════════════════════════════════════════════════════════════
function launchApp() {
  // Update greeting
  const h = new Date().getHours();
  const greet = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
  const first = currentUser.display_name.split(' ')[0];
  document.getElementById('topbar-greeting').textContent = `${greet}, ${first}! 👋`;
  document.getElementById('user-display').textContent    = currentUser.display_name;
  document.getElementById('user-avatar').textContent     = first[0].toUpperCase();

  // Load tasks
  fetch(`/api/tasks?user=${encodeURIComponent(currentUser.username)}`)
    .then(r => r.json())
    .then(d => {
      tasks = d.tasks || [];
      showScreen('app-screen');
      renderTasks();
    });
}

// ═══════════════════════════════════════════════════════════════
// LOGOUT
// ═══════════════════════════════════════════════════════════════
function logout() {
  currentUser   = null;
  tasks         = [];
  currentFilter = 'All';
  currentCat    = 'All';
  closeAddPanel();
  showLogin();
  clearInputs(['login-user','login-pass']);
}

// ═══════════════════════════════════════════════════════════════
// FILTERS
// ═══════════════════════════════════════════════════════════════
function setFilter(f, navEl, chipEl) {
  currentFilter = f;

  // Update sidebar nav
  if (navEl) {
    document.querySelectorAll('[data-filter]').forEach(el => el.classList.remove('active'));
    navEl.classList.add('active');
  }

  // Update chips
  if (chipEl) {
    document.querySelectorAll('.filter-chip').forEach(el => el.classList.remove('active'));
    chipEl.classList.add('active');
  } else {
    // sync chip from sidebar click
    document.querySelectorAll('.filter-chip').forEach(el => {
      el.classList.toggle('active', el.textContent.replace('🔴 ','').trim() === f ||
                                    (f === 'High Priority' && el.textContent.includes('High')));
    });
  }

  const titles = {
    'All':'All Tasks','Today':'Due Today','Upcoming':'Upcoming',
    'Completed':'Completed','High Priority':'High Priority'
  };
  document.getElementById('topbar-title').textContent = titles[f] || f;
  renderTasks();
}

function setCat(c, el) {
  currentCat = c;
  document.querySelectorAll('[data-cat]').forEach(n => n.classList.remove('active'));
  if (el) el.classList.add('active');
  renderTasks();
}

// ═══════════════════════════════════════════════════════════════
// ADD PANEL
// ═══════════════════════════════════════════════════════════════
function toggleAddPanel() {
  addPanelOpen ? closeAddPanel() : openAddPanel();
}

function openAddPanel() {
  addPanelOpen = true;
  editingId    = null;
  clearInputs(['new-title','new-desc','new-due']);
  document.getElementById('new-cat').value = 'Personal';
  document.getElementById('new-pri').value = 'Medium';
  document.querySelector('.add-panel-title').textContent = '✨ New Task';
  document.querySelector('.btn-save').textContent = 'Add Task ✓';
  const panel = document.getElementById('add-panel');
  panel.classList.add('open');
  setTimeout(() => document.getElementById('new-title').focus(), 350);
}

function closeAddPanel() {
  addPanelOpen = false;
  editingId    = null;
  document.getElementById('add-panel').classList.remove('open');
}

// ═══════════════════════════════════════════════════════════════
// ADD / SAVE TASK
// ═══════════════════════════════════════════════════════════════
function addTask() {
  const title = val('new-title');
  if (!title) {
    document.getElementById('new-title').style.borderColor = 'var(--c-danger)';
    setTimeout(() => document.getElementById('new-title').style.borderColor = '', 1400);
    showToast('⚠️','Please enter a task title.','#ffd98a');
    return;
  }
  const task = {
    id:       Date.now().toString(),
    title,
    desc:     val('new-desc'),
    category: document.getElementById('new-cat').value,
    priority: document.getElementById('new-pri').value,
    due_date: document.getElementById('new-due').value,
    done:     false,
    created:  new Date().toISOString().slice(0,10),
  };

  if (editingId) {
    const idx = tasks.findIndex(t => t.id === editingId);
    if (idx !== -1) {
      task.id      = editingId;
      task.done    = tasks[idx].done;
      task.created = tasks[idx].created;
      tasks[idx]   = task;
      showToast('✏️','Task updated!');
    }
    editingId = null;
  } else {
    tasks.unshift(task);
    showToast('✅','Task added!');
  }

  saveTasks();
  closeAddPanel();
  renderTasks();
}

// ═══════════════════════════════════════════════════════════════
// EDIT TASK
// ═══════════════════════════════════════════════════════════════
function editTask(id) {
  const t = tasks.find(x => x.id === id);
  if (!t) return;
  editingId = id;
  openAddPanel();
  setTimeout(() => {
    document.getElementById('new-title').value = t.title;
    document.getElementById('new-desc').value  = t.desc || '';
    document.getElementById('new-cat').value   = t.category;
    document.getElementById('new-pri').value   = t.priority;
    document.getElementById('new-due').value   = t.due_date || '';
    document.querySelector('.add-panel-title').textContent = '✏️ Edit Task';
    document.querySelector('.btn-save').textContent = 'Save Changes ✓';
  }, 80);
}

// ═══════════════════════════════════════════════════════════════
// TOGGLE DONE
// ═══════════════════════════════════════════════════════════════
function toggleDone(id) {
  const t = tasks.find(x => x.id === id);
  if (!t) return;
  t.done = !t.done;

  // Animate checkbox
  const cb = document.getElementById(`cb-${id}`);
  if (cb) { cb.classList.add('check-popped'); setTimeout(() => cb.classList.remove('check-popped'), 400); }

  saveTasks();
  setTimeout(() => renderTasks(), 120);
  showToast(t.done ? '✅' : '↩️', t.done ? 'Task completed!' : 'Marked as pending.');
}

// ═══════════════════════════════════════════════════════════════
// DELETE TASK
// ═══════════════════════════════════════════════════════════════
function deleteTask(id) {
  const card = document.getElementById(`card-${id}`);
  if (card) {
    card.style.transition = 'all 0.3s cubic-bezier(0.4,0,1,1)';
    card.style.opacity    = '0';
    card.style.transform  = 'translateX(30px) scale(0.95)';
    card.style.maxHeight  = card.offsetHeight + 'px';
    setTimeout(() => { card.style.maxHeight = '0'; card.style.margin = '0'; card.style.padding = '0'; }, 250);
    setTimeout(() => {
      tasks = tasks.filter(t => t.id !== id);
      saveTasks();
      renderTasks();
      showToast('🗑️','Task deleted.');
    }, 480);
  }
}

// ═══════════════════════════════════════════════════════════════
// SAVE
// ═══════════════════════════════════════════════════════════════
function saveTasks() {
  if (!currentUser) return;
  fetch('/api/tasks', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({username: currentUser.username, tasks})
  });
}

// ═══════════════════════════════════════════════════════════════
// RENDER
// ═══════════════════════════════════════════════════════════════
function renderTasks() {
  const listEl = document.getElementById('task-list');
  const query  = document.getElementById('search-input').value.trim().toLowerCase();
  const sort   = document.getElementById('sort-select').value;
  const today  = todayStr();

  // --- Filter ---
  let visible = tasks.filter(t => {
    if (currentCat !== 'All' && t.category !== currentCat) return false;
    if (query && !t.title.toLowerCase().includes(query) &&
        !(t.desc||'').toLowerCase().includes(query)) return false;

    if (currentFilter === 'Completed')    return t.done;
    if (currentFilter === 'High Priority') return t.priority === 'High' && !t.done;
    if (currentFilter === 'Today')        return !t.done && t.due_date === today;
    if (currentFilter === 'Upcoming')     return !t.done && t.due_date && t.due_date > today;
    return true; // All
  });

  // --- Sort ---
  visible = [...visible].sort((a, b) => {
    if (sort === 'priority') return PRIO_ORDER[a.priority] - PRIO_ORDER[b.priority];
    if (sort === 'created')  return (b.created||'') > (a.created||'') ? 1 : -1;
    // due date — undated last
    const da = a.due_date || '9999';
    const db = b.due_date || '9999';
    return da < db ? -1 : da > db ? 1 : 0;
  });

  // --- Stats ---
  const total   = tasks.length;
  const done    = tasks.filter(t => t.done).length;
  const pending = total - done;
  const overdue = tasks.filter(t => !t.done && t.due_date && t.due_date < today).length;
  const pct     = total ? Math.round(done / total * 100) : 0;
  document.getElementById('st-total').textContent   = total;
  document.getElementById('st-done').textContent    = done;
  document.getElementById('st-pending').textContent = pending;
  document.getElementById('st-overdue').textContent = overdue;
  document.getElementById('st-progress').style.width = pct + '%';

  // --- Badges ---
  document.getElementById('badge-all').textContent = total;
  const todayCount = tasks.filter(t => !t.done && t.due_date === today).length;
  const todayBadge = document.getElementById('badge-today');
  todayBadge.textContent = todayCount;
  todayBadge.style.display = todayCount ? '' : 'none';

  // --- Empty state ---
  if (!visible.length) {
    const msgs = {
      'All':          ['📋','No tasks yet','Hit "+ New Task" to get started!'],
      'Today':        ['☀️','Nothing due today','Enjoy your clear schedule!'],
      'Upcoming':     ['📆','No upcoming tasks','You\'re all caught up!'],
      'Completed':    ['🎉','Nothing completed yet','Start checking off tasks!'],
      'High Priority':['🔴','No high-priority tasks','Everything looks calm.'],
    };
    const [icon, title, sub] = msgs[currentFilter] || ['📋','No tasks',''];
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">${icon}</div>
        <div class="empty-title">${title}</div>
        <div class="empty-sub">${sub}</div>
      </div>`;
    return;
  }

  // --- Render cards (preserve existing DOM for non-edited items) ---
  const existingIds = new Set([...listEl.querySelectorAll('.task-card')].map(el => el.id.replace('card-','')));
  const newIds      = new Set(visible.map(t => t.id));

  // Remove cards no longer visible
  existingIds.forEach(id => {
    if (!newIds.has(id)) {
      const el = document.getElementById(`card-${id}`);
      if (el) el.remove();
    }
  });

  // Insert / update cards in order
  visible.forEach((t, i) => {
    const cardHtml = buildCard(t, today);
    const existing = document.getElementById(`card-${t.id}`);
    if (existing) {
      existing.outerHTML = cardHtml;
    } else {
      const tmp = document.createElement('div');
      tmp.innerHTML = cardHtml;
      const newCard = tmp.firstElementChild;
      newCard.style.animationDelay = (i * 0.04) + 's';
      if (i < listEl.children.length) {
        listEl.insertBefore(newCard, listEl.children[i]);
      } else {
        listEl.appendChild(newCard);
      }
    }
  });
}

function buildCard(t, today) {
  const pClr   = { High:'p-high', Medium:'p-medium', Low:'p-low' }[t.priority] || 'p-low';
  const pTag   = { High:'tag-high', Medium:'tag-medium', Low:'tag-low' }[t.priority] || '';
  const catIcon= { Personal:'🏠', Work:'💼', Health:'❤️', Study:'📚',
                   Shopping:'🛒', Finance:'💰', Other:'📌' }[t.category] || '📌';

  let dueMeta = '';
  if (t.due_date) {
    let dueClass = 'tag-due';
    let dueLabel = '📅 ' + t.due_date;
    if (!t.done && t.due_date < today)      { dueClass += ' overdue'; dueLabel = '⚠️ Overdue'; }
    else if (!t.done && t.due_date === today){ dueClass += ' today';   dueLabel = '📅 Due Today'; }
    else {
      const diff = Math.ceil((new Date(t.due_date) - new Date(today)) / 86400000);
      if (!t.done && diff <= 3) { dueClass += ' soon'; dueLabel = `📅 In ${diff}d`; }
    }
    dueMeta = `<span class="task-tag ${dueClass}">${dueLabel}</span>`;
  }

  const descHtml = t.desc ? `<div class="task-desc">${escHtml(t.desc)}</div>` : '';

  return `
<div class="task-card ${pClr} ${t.done ? 'done' : ''}" id="card-${t.id}">
  <div class="task-check-wrap">
    <input type="checkbox" class="task-checkbox" id="cb-${t.id}"
           ${t.done ? 'checked' : ''} onchange="toggleDone('${t.id}')"/>
  </div>
  <div class="task-body">
    <div class="task-title">${escHtml(t.title)}</div>
    ${descHtml}
    <div class="task-meta">
      <span class="task-tag tag-cat">${catIcon} ${t.category}</span>
      <span class="task-tag ${pTag}">${t.priority}</span>
      ${dueMeta}
    </div>
  </div>
  <div class="task-actions">
    <button class="btn btn-icon" title="Edit" onclick="editTask('${t.id}')">✏️</button>
    <button class="btn btn-icon" title="Delete" onclick="deleteTask('${t.id}')"
            style="color:var(--c-danger);">🗑</button>
  </div>
</div>`;
}

// ═══════════════════════════════════════════════════════════════
// TOAST
// ═══════════════════════════════════════════════════════════════
function showToast(icon, msg) {
  const t = document.getElementById('toast');
  document.getElementById('toast-icon').textContent = icon;
  document.getElementById('toast-msg').textContent  = msg;
  t.classList.add('show');
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2400);
}

// ═══════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════
function val(id) { return document.getElementById(id).value.trim(); }

function clearInputs(ids) {
  ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
}

function showErr(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.classList.add('visible');
}

function clearErr(id) {
  const el = document.getElementById(id);
  if (el) { el.textContent = ''; el.classList.remove('visible'); }
}

function animBtn(id, text) {
  const el = document.getElementById(id);
  if (!el) return;
  el._orig = el.textContent;
  el.textContent  = text;
  el.style.opacity = '0.7';
  el.disabled = true;
}

function resetBtn(id, text) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent   = text;
  el.style.opacity = '1';
  el.disabled      = false;
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

// Close add panel on Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && addPanelOpen) closeAddPanel();
});
</script>
</body>
</html>"""

# ── HTTP Handler ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # silence access log

    def _send(self, code, ctype, body):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type",   ctype)
        self.send_header("Content-Length", len(body))
        self.send_header("Cache-Control",  "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code=200):
        self._send(code, "application/json", json.dumps(data))

    def do_GET(self):
        path = urllib.parse.urlparse(self.path)

        if path.path == "/" or path.path == "/index.html":
            self._send(200, "text/html; charset=utf-8", HTML)
            return

        if path.path == "/api/tasks":
            qs   = urllib.parse.parse_qs(path.query)
            user = qs.get("user", [""])[0]
            if not user:
                self._json({"error": "Missing user"}, 400)
                return
            self._json({"tasks": load_tasks(user)})
            return

        self._send(404, "text/plain", "Not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length) or b"{}")
        path   = self.path

        if path == "/api/login":
            u  = body.get("username", "").strip()
            pw = body.get("password", "")
            if not u or not pw:
                self._json({"ok": False, "error": "Missing fields."})
                return
            users = load_users()
            if u not in users:
                self._json({"ok": False, "error": "Account not found."})
                return
            if users[u]["password"] != _hash(pw):
                self._json({"ok": False, "error": "Incorrect password."})
                return
            self._json({"ok": True, "username": u,
                        "display_name": users[u]["display_name"]})
            return

        if path == "/api/register":
            name  = body.get("name",     "").strip()
            uname = body.get("username", "").strip()
            pw    = body.get("password", "")
            import re as _re
            if not all([name, uname, pw]):
                self._json({"ok": False, "error": "All fields required."})
                return
            if not _re.match(r"^\w{3,20}$", uname):
                self._json({"ok": False,
                            "error": "Username: 3–20 chars, letters/numbers/underscore."})
                return
            if len(pw) < 6:
                self._json({"ok": False, "error": "Password must be ≥ 6 characters."})
                return
            users = load_users()
            if uname in users:
                self._json({"ok": False, "error": "Username already taken."})
                return
            users[uname] = {
                "display_name": name,
                "password":     _hash(pw),
                "joined":       datetime.now().strftime("%Y-%m-%d"),
            }
            save_users(users)
            self._json({"ok": True, "username": uname, "display_name": name})
            return

        if path == "/api/tasks":
            uname = body.get("username", "")
            tlist = body.get("tasks",    [])
            if not uname:
                self._json({"ok": False, "error": "Missing username."})
                return
            save_tasks(uname, tlist)
            self._json({"ok": True})
            return

        self._send(404, "text/plain", "Not found")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    url    = f"http://127.0.0.1:{PORT}"

    print(f"\n{'─'*52}")
    print(f"  ✅  To-Do Core is running at  {url}")
    print(f"{'─'*52}")
    print(f"  Opening browser automatically…")
    print(f"  Press  Ctrl+C  in this terminal to quit.\n")

    threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Goodbye! 👋\n")
        server.shutdown()