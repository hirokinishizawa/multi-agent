import os
import sys
import re
import json
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from openai import OpenAI
from .agents import FRAMER, SQL, FINISHER

load_dotenv()


# -----------------------------
# utils
# -----------------------------
def slug(s: str, max_len: int = 40) -> str:
    keep = []
    for ch in s.strip():
        if ch.isalnum():
            keep.append(ch)
        elif ch in " _-":
            keep.append("_")
    out = "".join(keep)
    while "__" in out:
        out = out.replace("__", "_")
    return out[:max_len].strip("_") or "run"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_fenced_code_blocks(text: str):
    """
    Extract markdown fenced code blocks.
    Returns list of dicts: {lang: str|None, code: str}
    """
    blocks = []
    # ```lang\n ... \n```
    pattern = re.compile(r"```([a-zA-Z0-9_+-]*)\n(.*?)\n```", re.DOTALL)
    for m in pattern.finditer(text or ""):
        lang = (m.group(1) or "").strip() or None
        code = (m.group(2) or "").strip()
        blocks.append({"lang": lang, "code": code})
    return blocks


def git_head(repo_root: Path) -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        return "no-git"


def update_project_context_last_run(repo_root: Path, block: str) -> None:
    """
    Update PROJECT_CONTEXT.md AUTO block:
    <!-- AUTO:LAST_RUN_START -->
    ...
    <!-- AUTO:LAST_RUN_END -->
    If markers don't exist, append them at the end.
    """
    pc = repo_root / "PROJECT_CONTEXT.md"
    if not pc.exists():
        return

    text = pc.read_text(encoding="utf-8")
    pattern = r"(<!-- AUTO:LAST_RUN_START -->)(.*?)(<!-- AUTO:LAST_RUN_END -->)"
    m = re.search(pattern, text, flags=re.DOTALL)

    if m:
        new_text = re.sub(
            pattern,
            r"\1\n" + block + r"\n\3",
            text,
            flags=re.DOTALL,
        )
        if new_text != text:
            pc.write_text(new_text, encoding="utf-8")
        return

    # markers not found -> append
    append = (
        "\n\n<!-- AUTO:LAST_RUN_START -->\n"
        + block
        + "\n<!-- AUTO:LAST_RUN_END -->\n"
    )
    pc.write_text(text + append, encoding="utf-8")


def update_state_and_context(
    *,
    repo_root: Path,
    request: str,
    model: str,
    md_path: Path,
    manifest_path: Path,
    finisher_sql_files: list[Path],
) -> None:
    """
    Append to STATE.md and refresh PROJECT_CONTEXT.md last-run block.
    """
    tz = ZoneInfo("Asia/Tokyo")
    now = datetime.now(tz)
    ts = now.strftime("%Y-%m-%d %H:%M:%S JST")
    git = git_head(repo_root)

    state = repo_root / "STATE.md"
    if not state.exists():
        state.write_text("# STATE (Auto log)\n\n---\n\n", encoding="utf-8")

    req_short = request.replace("\n", " ").strip()
    if len(req_short) > 220:
        req_short = req_short[:220] + "..."

    md_sha = sha256_file(md_path) if md_path.exists() else "missing"
    manifest_sha = sha256_file(manifest_path) if manifest_path.exists() else "missing"
    sql_names = [p.name for p in finisher_sql_files]
    sql_section = ""
    if sql_names:
        sql_section = "  - finisher_sql:\n" + "".join(
            [f"    - `{name}`\n" for name in sql_names]
        )

    entry = (
        f"## {ts}\n"
        f"- model: `{model}`\n"
        f"- git: `{git}`\n"
        f"- request: {req_short}\n"
        f"- outputs:\n"
        f"  - markdown: `{md_path.as_posix()}` (sha256: `{md_sha}`)\n"
        f"  - manifest: `{manifest_path.as_posix()}` (sha256: `{manifest_sha}`)\n"
        f"{sql_section}\n"
    )

    with state.open("a", encoding="utf-8") as f:
        f.write(entry)

    last_run_block = (
        f"- {ts}\n"
        f"- request: {req_short}\n"
        f"- markdown: `{md_path.name}`\n"
        f"- manifest: `{manifest_path.name}`\n"
        + (f"- sql: " + ", ".join([f"`{n}`" for n in sql_names]) + "\n" if sql_names else "")
    ).strip()

    update_project_context_last_run(repo_root, last_run_block)


# -----------------------------
# main
# -----------------------------
def main():
    if len(sys.argv) < 2:
        print('Usage: python -m src.run "your request"')
        sys.exit(1)

    model = os.getenv("MODEL", "")
    if not model:
        raise RuntimeError("MODEL is empty. Set MODEL in .env")

    user_text = sys.argv[1]
    client = OpenAI()

    agents = [FRAMER, SQL, FINISHER]

    outputs = []
    context = user_text

    for agent in agents:
        print(f"[Main] Calling {agent.name}...")
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": agent.system},
                {"role": "user", "content": context},
            ],
        )
        out = resp.output_text or ""
        outputs.append((agent.name, out))
        context = f"{user_text}\n\n---\nPrevious output from {agent.name}:\n{out}\n"

    # console output
    full_sections = []
    for name, out in outputs:
        block = f"## {name}\n{out}\n"
        print("\n" + block)
        full_sections.append(block)

    # repo root & runs dir (works from any CWD)
    repo_root = Path(__file__).resolve().parents[1]
    runs_dir = repo_root / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # timestamp in JST for filenames
    now_jst = datetime.now(ZoneInfo("Asia/Tokyo"))
    ts = now_jst.strftime("%Y%m%d_%H%M%S")
    base_name = f"{ts}_{slug(user_text)}"

    md_path = runs_dir / f"{base_name}.md"
    content = f"# Request\n{user_text}\n\n---\n\n" + "\n".join(full_sections)
    md_path.write_text(content, encoding="utf-8")
    print(f"[Main] Saved: {md_path}")

    # Extract Finisher SQL blocks (Production + 2 validations) and save them separately
    finisher_out = None
    for name, out in outputs:
        if name.lower() == "finisher":
            finisher_out = out
            break

    manifest = {
        "request": user_text,
        "model": model,
        "timestamp_jst": now_jst.strftime("%Y-%m-%d %H:%M:%S"),
        "git_head": git_head(repo_root),
        "saved_markdown": str(md_path),
        "finisher_sql_files": [],
        "hashes": {
            "markdown_sha256": sha256_text(content),
        },
        "notes": [],
    }

    finisher_sql_files: list[Path] = []

    if finisher_out is None:
        manifest["notes"].append("Finisher output not found; no SQL files extracted.")
    else:
        blocks = extract_fenced_code_blocks(finisher_out)

        # Prefer sql blocks first, but accept any language if present
        sql_like = [b for b in blocks if (b["lang"] or "").lower() in ("sql", "bigquery", "bq")]
        other = [b for b in blocks if b not in sql_like]
        ordered = sql_like + other

        if len(ordered) < 3:
            manifest["notes"].append(
                f"Expected 3 fenced code blocks from Finisher (prod + 2 validations), found {len(ordered)}."
            )

        labels = ["production", "validation_1", "validation_2"]
        for i, label in enumerate(labels):
            if i >= len(ordered):
                break
            code = ordered[i]["code"].strip()
            if not code:
                manifest["notes"].append(f"{label}: extracted block was empty; skipped.")
                continue
            sql_path = runs_dir / f"{base_name}_{label}.sql"
            sql_path.write_text(code + "\n", encoding="utf-8")
            finisher_sql_files.append(sql_path)

            manifest["finisher_sql_files"].append(str(sql_path))
            manifest["hashes"][f"{label}_sha256"] = sha256_text(code)

        if manifest["finisher_sql_files"]:
            print("[Main] Extracted Finisher SQL files:")
            for p in manifest["finisher_sql_files"]:
                print(f"  - {p}")

    # Save manifest (hashes / evidence)
    manifest_path = runs_dir / f"{base_name}_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[Main] Saved manifest: {manifest_path}")
    print(f"[Main] SHA256(markdown): {manifest['hashes']['markdown_sha256']}")
    for k, v in manifest["hashes"].items():
        if k.endswith("_sha256") and k != "markdown_sha256":
            print(f"[Main] SHA256({k.replace('_sha256','')}): {v}")

    # Auto-update STATE.md and PROJECT_CONTEXT.md
    update_state_and_context(
        repo_root=repo_root,
        request=user_text,
        model=model,
        md_path=md_path,
        manifest_path=manifest_path,
        finisher_sql_files=finisher_sql_files,
    )
    print("[Main] Updated STATE.md and PROJECT_CONTEXT.md")

    # CLI note: avoid backticks in zsh
    print(
        "\n[Note] zsh注意: テーブル名を `...` (バッククォート) で囲むとコマンド置換で事故ります。"
        "\n       BigQueryのテーブルはSQL内では `project.dataset.table` でOKですが、"
        "\n       ターミナルの引数文字列にバッククォートを入れないようにしてください。"
    )


if __name__ == "__main__":
    main()
