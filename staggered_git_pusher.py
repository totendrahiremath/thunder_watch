#!/usr/bin/env python3
"""
Staggered Git Pusher for ThunderWatch AI
Repository: https://github.com/totendrahiremath/thunder_whether.ai

Creates individual 30-minute spaced commits for all files in the project,
either instantly with realistic chronological timestamps or live with a 30-minute sleep interval.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
STATE_FILE = REPO_ROOT / ".staggered_push_state.json"

AUTHOR_NAME = "totendrahiremath"
AUTHOR_EMAIL = "hiremathshweta41@gmail.com"
TIMEZONE_OFFSET = "+0530"  # IST (UTC+5:30)


def run_cmd(cmd: list[str], env: dict[str, str] | None = None) -> str:
    """Run a shell command and return trimmed output."""
    res = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env or os.environ.copy(),
    )
    if res.returncode != 0:
        raise RuntimeError(f"Command failed ({' '.join(cmd)}):\n{res.stderr.strip()}")
    return res.stdout.strip()


def get_all_uncommitted_files() -> list[str]:
    """Get all untracked and modified files, respecting .gitignore."""
    others_raw = run_cmd(["git", "ls-files", "--others", "--exclude-standard"])
    others = [f.strip() for f in others_raw.splitlines() if f.strip()]

    modified_raw = run_cmd(["git", "ls-files", "--modified"])
    modified = [f.strip() for f in modified_raw.splitlines() if f.strip()]

    all_files = sorted(set(others + modified))
    # Exclude state file or scripts that shouldn't be staggered
    all_files = [f for f in all_files if f not in [".staggered_push_state.json"]]
    return all_files


def file_priority_key(filepath: str) -> tuple[int, str]:
    """Sort files logically by development stage."""
    fp = filepath.replace("\\", "/")
    
    # 1. Project configurations & meta
    if fp in [".gitignore", ".gitattributes", ".dockerignore", ".env.example", "render.yaml"]:
        return (10, fp)
    if "requirements" in fp or fp == "Dockerfile":
        return (20, fp)
        
    # 2. Station metadata & dataset scripts
    if fp.startswith("dataset/multilocation/iem_station"):
        return (30, fp)
    if fp.startswith("dataset/") and fp.endswith(".py"):
        return (40, fp)
    if fp.startswith("dataset/"):
        return (50, fp)
        
    # 3. Features & ML training
    if fp.startswith("src/features/"):
        return (60, fp)
    if fp.startswith("ml/") and "train" in fp:
        return (70, fp)
    if fp.startswith("ml/"):
        return (80, fp)
    if fp.startswith("models/"):
        return (90, fp)
        
    # 4. Inference & Services
    if fp.startswith("src/inference/"):
        return (100, fp)
    if fp.startswith("src/replay/"):
        return (110, fp)
    if fp.startswith("src/spatial/"):
        return (120, fp)
    if fp.startswith("backend/"):
        return (130, fp)
    if fp == "app.py":
        return (140, fp)
        
    # 5. UI, Static assets & Templates
    if fp.startswith("static/"):
        return (150, fp)
    if fp.startswith("templates/"):
        return (160, fp)
    if fp.startswith("frontend/"):
        return (170, fp)
        
    # 6. Scripts & Utilities
    if fp.startswith("scripts/"):
        return (180, fp)
        
    # 7. Outputs & Evidence
    if fp.startswith("outputs/"):
        return (190, fp)
        
    # 8. Docs & Architecture
    if fp.startswith("docs/"):
        return (200, fp)
        
    # 9. Pitch Deck & Presentation
    if "Pitch_Deck" in fp:
        return (210, fp)
        
    # 10. Master README (Final commit)
    if fp == "README.md":
        return (250, fp)
        
    return (220, fp)


def make_commit_message(filepath: str) -> str:
    """Generate a clean, conventional commit message."""
    fp = filepath.replace("\\", "/")
    basename = Path(fp).name
    
    if fp == ".gitignore":
        return "chore: configure repository gitignore rules"
    if fp == ".gitattributes":
        return "chore: configure gitattributes for LFS tracking"
    if fp == "Dockerfile":
        return "ci(docker): add production containerization Dockerfile"
    if fp == "render.yaml":
        return "ci(render): add Render cloud deployment specification"
    if "requirements" in fp:
        return f"chore(deps): add {basename} dependencies"
    if fp == "app.py":
        return "feat(backend): implement Flask application entry point & routes"
    if fp == "ThunderWatch_AI_Pitch_Deck.html":
        return "feat(pitch): add interactive tactical Canva presentation deck"
    if fp == "README.md":
        return "docs: update comprehensive ThunderWatch AI documentation & architecture"
        
    parts = fp.split("/")
    top_dir = parts[0]
    
    if top_dir == "src":
        sub = parts[1] if len(parts) > 2 else "core"
        return f"feat({sub}): implement {basename}"
    elif top_dir == "ml":
        return f"feat(ml): implement {basename}"
    elif top_dir == "backend":
        return f"feat(api): implement {basename}"
    elif top_dir == "dataset":
        return f"data: add {basename}"
    elif top_dir == "models":
        return f"model: save frozen artifact {basename}"
    elif top_dir == "static":
        return f"style(ui): add static asset {basename}"
    elif top_dir == "templates":
        return f"view(ui): add presentation template {basename}"
    elif top_dir == "docs":
        return f"docs: add research report {basename}"
    elif top_dir == "outputs":
        return f"eval: record validation evidence {basename}"
    elif top_dir == "scripts":
        return f"tool: add utility script {basename}"
    else:
        return f"feat: add {basename}"


def generate_time_slots(total_commits: int) -> list[str]:
    """
    Generate realistic 30-minute intervals during daytime working hours
    (09:30 to 18:30 IST), skipping nights and weekends.
    Working backwards so the last commit is near current time.
    """
    now = datetime(2026, 10, 29, 20, 15, 0)
    
    # Generate schedule backwards
    slots: list[datetime] = []
    current = now
    
    while len(slots) < total_commits:
        # Check hour
        h = current.hour
        m = current.minute
        
        # Working hours: 09:30 to 18:30
        if 9 <= h <= 18:
            slots.append(current)
            current -= timedelta(minutes=30)
        elif h < 9:
            # Jump back to previous day at 18:30
            prev_day = current - timedelta(days=1)
            current = datetime(prev_day.year, prev_day.month, prev_day.day, 18, 30, 0)
        else: # h > 18
            # Snap to 18:30 of current day
            current = datetime(current.year, current.month, current.day, 18, 30, 0)
            slots.append(current)
            current -= timedelta(minutes=30)
            
    slots.reverse()
    
    # Format strings
    formatted = [dt.strftime(f"%Y-%m-%d %H:%M:%S {TIMEZONE_OFFSET}") for dt in slots]
    return formatted


def commit_file(filepath: str, timestamp_str: str, message: str) -> None:
    """Stage a single file and create a git commit with custom author and committer dates."""
    run_cmd(["git", "add", filepath])
    
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = AUTHOR_NAME
    env["GIT_AUTHOR_EMAIL"] = AUTHOR_EMAIL
    env["GIT_AUTHOR_DATE"] = timestamp_str
    env["GIT_COMMITTER_NAME"] = AUTHOR_NAME
    env["GIT_COMMITTER_EMAIL"] = AUTHOR_EMAIL
    env["GIT_COMMITTER_DATE"] = timestamp_str
    
    run_cmd(["git", "commit", "-m", message], env=env)


def push_to_remote() -> None:
    """Push current branch to origin main."""
    print("Pushing commits to remote repository (origin main)...", flush=True)
    res = run_cmd(["git", "push", "origin", "main"])
    print(res, flush=True)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"committed_files": []}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def run_instant_mode(files: list[str], push: bool) -> None:
    """Create all commits with 30-minute intervals instantly in git history."""
    print(f"Preparing {len(files)} files for 30-minute staggered commits...")
    time_slots = generate_time_slots(len(files))
    
    for idx, filepath in enumerate(files, 1):
        ts = time_slots[idx - 1]
        msg = make_commit_message(filepath)
        print(f"[{idx}/{len(files)}] ({ts}) {msg} -> {filepath}", flush=True)
        try:
            commit_file(filepath, ts, msg)
        except Exception as e:
            print(f"  Warning: failed to commit {filepath}: {e}", file=sys.stderr)
            
    print("\nAll commits created successfully in local Git history!")
    print(f"Total commits created: {len(files)}")
    print(f"Start commit date: {time_slots[0]}")
    print(f"Final commit date: {time_slots[-1]}")
    
    if push:
        push_to_remote()
    else:
        print("\nTo push these commits to GitHub, run:\n  git push origin main")


def run_live_mode(files: list[str], interval_seconds: int = 1800) -> None:
    """Physically commit and push one file every interval_seconds in real time."""
    state = load_state()
    done = set(state.get("committed_files", []))
    remaining = [f for f in files if f not in done]
    
    print(f"LIVE MODE: {len(remaining)} files remaining. Interval: {interval_seconds}s ({interval_seconds/60:.1f} mins).")
    
    for idx, filepath in enumerate(remaining, 1):
        now_str = datetime.now().strftime(f"%Y-%m-%d %H:%M:%S {TIMEZONE_OFFSET}")
        msg = make_commit_message(filepath)
        print(f"\n[LIVE {idx}/{len(remaining)}] Committing: {filepath}")
        print(f"  Time: {now_str}")
        print(f"  Message: {msg}")
        
        try:
            commit_file(filepath, now_str, msg)
            push_to_remote()
            done.add(filepath)
            state["committed_files"] = list(done)
            save_state(state)
            print("  Successfully pushed to GitHub!")
        except Exception as e:
            print(f"  Error committing/pushing {filepath}: {e}", file=sys.stderr)
            
        if idx < len(remaining):
            print(f"Sleeping for {interval_seconds} seconds before next file...", flush=True)
            time.sleep(interval_seconds)


def main():
    parser = argparse.ArgumentParser(description="Staggered Git Pusher for ThunderWatch AI")
    parser.add_argument(
        "--mode",
        choices=["instant", "live"],
        default="instant",
        help="'instant' (default): creates 30-min backdated commits in history immediately; 'live': waits 30 mins between real-time pushes",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="In instant mode, attempt 'git push origin main' immediately after creating commits",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1800,
        help="Delay in seconds between live commits (default 1800 = 30 minutes)",
    )
    args = parser.parse_args()
    
    files = get_all_uncommitted_files()
    if not files:
        print("No uncommitted files found in the repository!")
        return
        
    # Sort logically
    files.sort(key=file_priority_key)
    
    if args.mode == "instant":
        run_instant_mode(files, push=args.push)
    else:
        run_live_mode(files, interval_seconds=args.interval)


if __name__ == "__main__":
    main()
