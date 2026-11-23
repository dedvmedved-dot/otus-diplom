#!/usr/bin/env python3
"""Forgejo task poller (no-LLM): spawn the agent profile on NEW issues assigned to it.

Config via env: FORGEJO_HOST, FORGEJO_TOKEN, FORGEJO_REPO, FORGEJO_ASSIGNEE,
FORGEJO_ROLE, FORGEJO_STATE_FILE. Baseline on first run (no spawn).
"""
import json, os, subprocess, sys, urllib.request, urllib.error

HOST = os.environ.get("FORGEJO_HOST", "git.aiopslab.online")
TOKEN = os.environ.get("FORGEJO_TOKEN", "")
REPO = os.environ.get("FORGEJO_REPO", "aiopslab/otus-diplom")
ASSIGNEE = os.environ.get("FORGEJO_ASSIGNEE", "")
ROLE = os.environ.get("FORGEJO_ROLE", "engineer")
PEER = os.environ.get("FORGEJO_PEER", "")
HOME = os.environ.get("HOME", "")
STATE_FILE = os.environ.get("FORGEJO_STATE_FILE", os.path.join(HOME, ".hermes", "forgejo-poll-state.json"))

API = "https://%s/api/v1" % HOST

def api_get(path):
    req = urllib.request.Request(API + path, headers={"Authorization": "token " + TOKEN})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError as e:
        print("Forgejo HTTP %s on %s: %s" % (e.code, path, e.read().decode()[:200]), file=sys.stderr)
        sys.exit(1)

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"seen": {}}

def save_state(s):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(s, f)
    os.replace(tmp, STATE_FILE)

def spawn(issue):
    num = issue["number"]
    title = issue.get("title") or ""
    body = issue.get("body") or ""
    url = issue.get("html_url") or ""
    if ROLE == "engineer":
        completion = (
            "По завершении ЗАКРОЙ эту задачу (#%d) и создай НОВУЮ задачу с assignee '%s' (архитектор), "
            "заголовком 'review #%d: <короткий итог>' и телом: ссылка на PR/SHA, что сделано, критерии проверки. "
            "НЕ оставляй результат только комментарием — комментарий не будит архитектора (поллер видит только новые issue)."
            % (num, PEER, num)
        )
    else:
        completion = (
            "При необходимости разложи это задание и создай задачу инженеру (assignee '%s'), "
            "по завершении отчитайся комментарием в этой задаче (#%d) с фактическими ссылками и SHA."
            % (PEER, num)
        )
    prompt = (
        "Новое задание из очереди Forgejo #%d: %s\n\n%s\n\nPermalink: %s\n\n"
        "Выполни это задание в роли %s. Материалы и репозиторий: "
        "https://%s/%s (Forgejo, закрытый). "
        "Работай в рабочей ветке, внеси изменения, при необходимости создай PR. %s"
        % (num, title, body, url, ROLE, HOST, REPO, completion)
    )
    prompt_file = os.path.join(HOME, ".hermes", "task-prompt-%d.txt" % num)
    with open(prompt_file, "w") as f:
        f.write(prompt)
    unit = "otus-%s-issue%d" % (ROLE, num)
    chk = subprocess.run(["systemctl", "--user", "is-active", "--quiet", unit], capture_output=True)
    if chk.returncode == 0:
        print("already running: %s" % unit)
        return unit
    wrapper = os.path.join(HOME, ".hermes", "agent-task.sh")
    subprocess.run([
        "systemd-run", "--user", "--unit=" + unit,
        "--description=OTUS %s issue %d" % (ROLE, num),
        "--setenv=HOME=" + HOME,
        "--setenv=PATH=%s/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" % HOME,
        "--setenv=HERMES_HOME=%s/.hermes" % HOME,
        "--setenv=FORGEJO_TOKEN=" + TOKEN,
        "--setenv=FORGEJO_HOST=" + HOST,
        "--setenv=FORGEJO_REPO=" + REPO,
        "--setenv=FORGEJO_ASSIGNEE=" + ASSIGNEE,
        "--setenv=FORGEJO_ROLE=" + ROLE,
        "--setenv=FORGEJO_PEER=" + PEER,
        "--quiet", "bash", wrapper, ROLE, str(num), title,
    ], check=True)
    print("spawned %s for issue #%d" % (unit, num))
    return unit

def main():
    if not TOKEN or not ASSIGNEE:
        print("FORGEJO_TOKEN / FORGEJO_ASSIGNEE not set", file=sys.stderr)
        sys.exit(2)
    issues = api_get("/repos/%s/issues?state=open&limit=50" % REPO)
    state = load_state()
    if not state.get("initialized"):
        for i in issues:
            state["seen"][str(i["number"])] = i.get("updated_at", "")
        state["initialized"] = True
        save_state(state)
        print("baseline: recorded %d open issues" % len(issues))
        return
    for i in issues:
        num = i["number"]
        assignees = [a["login"] for a in (i.get("assignees") or [])]
        if ASSIGNEE not in assignees:
            continue
        key = str(num)
        if key not in state["seen"]:
            spawn(i)
            state["seen"][key] = i.get("updated_at", "")
            save_state(state)
            print("handled new issue #%d" % num)
    save_state(state)

if __name__ == "__main__":
    main()
