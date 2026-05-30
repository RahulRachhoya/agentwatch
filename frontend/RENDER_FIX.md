# Render Deployment Fix Required

## Current Issue

Service `srv-d8db9h7avr4c73fio3o0` failing with:
```
error: failed to solve: failed to read dockerfile: open Dockerfile: no such file or directory
```

## Root Cause

Render service config looking for Dockerfile in wrong location:
- dockerContext: `./backend` ✅
- dockerfilePath: `Dockerfile` ✅
- Expected file: `backend/Dockerfile` ✅ (exists in repo)

BUT: Docker build process in Render looking for Dockerfile at **wrong path relative to context**.

## The Problem

When Render clones repo and sets dockerContext to `./backend`, it should look for `Dockerfile` **inside** that context.

File structure:
```
repo/
├── backend/
│   ├── Dockerfile  ← File is HERE
│   ├── main.py
│   └── ...
└── render.yaml
```

Render config says:
- Context: `./backend`
- Dockerfile: `Dockerfile`

Should find: `./backend/Dockerfile` ← this path is correct

## Why It's Failing

Service was created manually BEFORE render.yaml existed. Dashboard config may have:
- Absolute path like `./backend/Dockerfile` instead of relative `Dockerfile`
- OR different root directory setting
- OR stale build cache

## Solution

### Option 1: Manual Dashboard Fix (REQUIRED)
1. Go to: https://dashboard.render.com/web/srv-d8db9h7avr4c73fio3o0/settings
2. Build & Deploy section
3. **Root Directory**: Should be EMPTY or `/` (not `./backend`)
4. **Docker Context**: Should be `./backend`
5. **Dockerfile Path**: Should be `Dockerfile` (NOT `./backend/Dockerfile`)
6. Clear build cache
7. Trigger manual deploy

### Option 2: Delete & Recreate from Blueprint
```bash
# 1. Note down DATABASE_URL and API_KEY from env vars
# 2. Delete service (KEEP database)
render services delete srv-d8db9h7avr4c73fio3o0 --confirm

# 3. Create from blueprint
# Dashboard → New → Blueprint → Point to GitHub repo
# render.yaml will auto-create service with correct settings
```

## Verification

After fix, build should show:
```
==> Cloning from https://github.com/RahulRachhoya/agentwatch
==> Checking out commit [hash] in branch main
#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: [size]B done
#1 DONE [time]s
#2 [internal] load metadata for docker.io/library/python:3.11-slim
...
```

NO "open Dockerfile: no such file or directory" error.
