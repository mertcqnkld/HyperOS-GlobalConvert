#!/usr/bin/env python3
"""
HyperOS-GlobalConvert - Automated GitHub Push Utility
Pushes the project to https://github.com/mertcqnkld/HyperOS-GlobalConvert.
"""

import os
import sys
import shutil
import subprocess

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

GITHUB_USER = "mertcqnkld"
REPO_NAME = "HyperOS-GlobalConvert"
REPO_FULL = f"{GITHUB_USER}/{REPO_NAME}"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def find_git_executable():
    paths = [
        "git",
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe"
    ]
    for p in paths:
        if shutil.which(p) or os.path.exists(p):
            return p
    return "git"

GIT_BIN = find_git_executable()

def run_cmd(cmd, cwd=BASE_DIR, check=True):
    print(f"  [RUN] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check and result.returncode != 0:
        print(f"[-] Command failed (code {result.returncode}):\n{result.stderr}")
        raise RuntimeError(result.stderr)
    return result

def push_to_github():
    print("===============================================================")
    print(f"   [*] GitHub Deployment: {REPO_FULL}")
    print("===============================================================\n")

    if not os.path.exists(os.path.join(BASE_DIR, ".git")):
        run_cmd([GIT_BIN, "init"])

    run_cmd([GIT_BIN, "config", "user.name", GITHUB_USER], check=False)
    run_cmd([GIT_BIN, "config", "user.email", f"{GITHUB_USER}@users.noreply.github.com"], check=False)

    print("1. Staging project files...")
    run_cmd([GIT_BIN, "add", "."])

    print("2. Creating Git commit...")
    commit_msg = "feat: add zero-dependency WebUI, Magisk generator, and run launchers"
    run_cmd([GIT_BIN, "commit", "-m", commit_msg], check=False)

    print("3. Configuring remote origin...")
    public_remote = f"https://github.com/{REPO_FULL}.git"
    run_cmd([GIT_BIN, "remote", "remove", "origin"], check=False)
    run_cmd([GIT_BIN, "remote", "add", "origin", public_remote])

    print("4. Pushing to GitHub (main branch)...")
    run_cmd([GIT_BIN, "branch", "-M", "main"])
    run_cmd([GIT_BIN, "push", "-u", "origin", "main"])

    print("\n" + "=" * 63)
    print(f"[+] Başarıyla GitHub'a Pushlandı!")
    print(f"[*] Repository URL: https://github.com/{REPO_FULL}")
    print("===============================================================\n")

if __name__ == "__main__":
    push_to_github()
