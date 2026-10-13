#!/usr/bin/env python3
"""변경 파일을 경로 규칙으로 1차 분류해 타입·scope 후보와 위험 플래그를 출력한다.

결과는 힌트일 뿐이다. 최종 타입과 그룹은 diff 내용을 읽고 정한다.
사용법: classify_changes.py [--json] [pathspec ...]
"""
import fnmatch
import json
import os
import re
import subprocess
import sys

LARGE_FILE_BYTES = 10 * 1024 * 1024

# (타입, 패턴 목록). 위에서부터 먼저 걸리는 규칙을 쓴다.
RULES = [
    ("ci", [".github/*", ".gitlab-ci.yml", "Jenkinsfile", ".circleci/*"]),
    ("build", ["requirements*.txt", "pyproject.toml", "setup.py", "setup.cfg", "poetry.lock",
               "uv.lock", "Pipfile*", "environment*.yml", "Dockerfile*", "docker-compose*.yml", "Makefile"]),
    ("test", ["tests/*", "test/*", "test_*.py", "*_test.py", "conftest.py", "*expectations/*"]),
    ("metric", ["metrics/*", "*metric*", "*kpi*", "semantic/*"]),
    ("exp", ["experiments/*", "configs/exp*", "params.yaml", "params.yml", "dvc.yaml", "dvc.lock", "mlruns/*"]),
    ("model", ["models/*.py", "features/*", "train*.py", "*predict*.py", "*.pkl", "*.joblib", "*.onnx", "*.pt", "*.h5"]),
    ("etl", ["etl/*", "pipelines/*", "pipeline/*", "dags/*", "dbt/*", "ingest*", "*.sql", "read_*.py", "load_*.py", "extract_*.py"]),
    ("data", ["data/*", "schemas/*", "*schema*", "generate_*data*.py", "*.csv", "*.parquet", "*.xlsx", "*.feather", "*.dvc"]),
    ("analysis", ["analysis/*", "analyses/*", "eda/*", "notebooks/*", "*.ipynb"]),
    ("report", ["reports/*", "report/*", "figures/*", "dashboards/*", "outputs/*", "*.png", "*.svg", "*.html", "*.pdf"]),
    ("docs", ["docs/*", "*.md", "*.rst"]),
    ("chore", [".gitignore", ".gitattributes", ".editorconfig", ".pre-commit-config.yaml", ".claude/*", ".vscode/*"]),
]

# 타입 우선순위 (낮을수록 우선). references/convention.md 2절과 같은 순서.
PRIORITY = {t: i for i, t in enumerate(
    ["metric", "data", "etl", "model", "exp", "fix", "analysis", "feat", "perf", "refactor",
     "report", "test", "docs", "build", "ci", "style", "chore", "code"])}

SECRET_PATTERNS = [".env", ".env.*", "*credential*", "*secret*", "*.pem", "*.key", "*token*", "id_rsa*"]
NO_SCOPE_TYPES = {"build", "ci", "chore"}
GENERIC_DIRS = {"analysis", "analyses", "eda", "notebooks", "reports", "report", "figures", "outputs",
                "data", "src", "scripts", "tests", "test", "docs", "dags", "etl", "pipelines", "models",
                "features", "experiments", "metrics", "dashboards", "configs", "raw", "processed", "interim"}
TOPIC_SUFFIX = re.compile(r"[-_](analysis|analyses|report|eda|notebook|pipeline|etl|dag|model|test)$")
TOPIC_PREFIX = re.compile(r"^(test|read|load|extract|generate|train)[-_]")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def changed_files(pathspecs):
    out = git("status", "--porcelain=v1", "-z", "-uall", "--", *pathspecs)
    entries, parts, i = [], out.split("\0"), 0
    while i < len(parts):
        rec = parts[i]
        i += 1
        if not rec:
            continue
        status, path, orig = rec[:2], rec[3:], None
        if status[0] in "RC":
            orig = parts[i]
            i += 1
        entries.append({"status": status, "path": path, "orig": orig})
    return entries


def match(path, patterns):
    name = os.path.basename(path)
    # fnmatch 의 * 는 / 도 매칭하므로 "data/*" 는 하위 디렉터리까지 잡는다
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(name, p) for p in patterns)


def classify(path):
    for typ, patterns in RULES:
        if match(path, patterns):
            return typ
    return "code"  # 일반 소스: feat/fix/refactor/perf 는 diff 를 읽고 정한다


def topic(path):
    """업무 주제(scope) 후보. 일반적인 디렉터리 이름은 건너뛴다."""
    parts = path.split("/")
    for d in parts[:-1]:
        if d.lower() not in GENERIC_DIRS and not d.startswith("."):
            return normalize(d)
    stem = os.path.splitext(parts[-1])[0]
    if stem.startswith(".") or stem.lower() in {"readme", "report", "index", "__init__", "main"}:
        return None
    return normalize(stem)


def normalize(name):
    name = name.lower().replace("_", "-")
    name = TOPIC_PREFIX.sub("", name)
    return TOPIC_SUFFIX.sub("", name)


def flags_for(entry):
    path, flags = entry["path"], []
    if entry["status"][1] == "D" or entry["status"][0] == "D":
        return flags
    try:
        size = os.path.getsize(path)
    except OSError:
        return flags
    if size > LARGE_FILE_BYTES:
        flags.append(f"large-file({size / (1024 * 1024):.1f}MB): DVC/LFS 검토")
    if match(path, SECRET_PATTERNS):
        flags.append("secret-like: 자격 증명 의심, 커밋 제외 검토")
    if path.endswith(".ipynb"):
        try:
            with open(path, encoding="utf-8") as f:
                nb = json.load(f)
            if any(c.get("outputs") for c in nb.get("cells", [])):
                flags.append("notebook-outputs: 출력 셀 남음, nbstripout 검토")
        except (OSError, ValueError):
            pass
    return flags


def main():
    args = sys.argv[1:]
    as_json = "--json" in args
    pathspecs = [a for a in args if a != "--json"]
    try:
        entries = changed_files(pathspecs)
    except subprocess.CalledProcessError as e:
        sys.exit(e.stderr.strip())

    for e in entries:
        e["type"] = classify(e["path"])
        # 설정·인프라 파일은 업무 주제가 없으므로 scope 를 붙이지 않는다
        e["topic"] = None if e["type"] in NO_SCOPE_TYPES else topic(e["path"])
        e["flags"] = flags_for(e)

    excluded = [e for e in entries if e["flags"]]
    groups = {}
    for e in entries:
        if e["flags"]:
            continue
        groups.setdefault(e["topic"] or f"({e['type']})", []).append(e)
    suggestions = []
    for key, files in groups.items():
        typ = min((f["type"] for f in files), key=lambda t: PRIORITY.get(t, 99))
        suggestions.append({"scope": None if key.startswith("(") else key, "type": typ,
                            "files": [p for f in files for p in ([f["orig"]] if f["orig"] else []) + [f["path"]]]})

    if as_json:
        print(json.dumps({"files": entries, "groups": suggestions,
                          "excluded": [e["path"] for e in excluded]}, ensure_ascii=False, indent=2))
        return
    if not entries:
        print("변경 사항 없음")
        return
    print("## 파일별 1차 분류")
    for e in entries:
        src = f"{e['orig']} -> " if e["orig"] else ""
        flag = f"  !! {'; '.join(e['flags'])}" if e["flags"] else ""
        print(f"[{e['status']}] {src}{e['path']}  type={e['type']} topic={e['topic'] or '-'}{flag}")
    print("\n## 주제별 그룹 후보 (diff 확인 후 확정)")
    for g in suggestions:
        scope = f"({g['scope']})" if g["scope"] else ""
        print(f"- {g['type']}{scope}: {', '.join(g['files'])}")
    if excluded:
        print("\n## 제외 후보 (위험 플래그)")
        for e in excluded:
            print(f"- {e['path']}: {'; '.join(e['flags'])}")


if __name__ == "__main__":
    main()
