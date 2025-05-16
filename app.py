# -------------------------------------------------------------
# AI 単語カード – メインアプリ
# -------------------------------------------------------------
import json, shutil, datetime, os
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st
from notion_client import Client, APIResponseError

from ui_components import sidebar, main_card, big_button


# ──────────────────────────── 環境定数 ───────────────────────────
NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
NOTION_DB_ID = st.secrets["NOTION_DB_ID"]

# Notion プロパティ名
PROP_WORD = "用語"      # Title
PROP_MEAN = "定義"      # Rich-text
PROP_MEMO = "一言メモ"  # Rich-text (optional)

# ローカル JSON
DATA_DIR      = Path(__file__).parent
WORDS_FILE    = DATA_DIR / "words.json"
LEARNED_FILE  = DATA_DIR / "learned_words.json"
BACKUP_DIR    = DATA_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)


# ──────────────────────────── JSONユーティリティ ───────────────────────────
def _trim_backups(stem: str, keep: int = 5) -> None:
    snaps = sorted(BACKUP_DIR.glob(f"{stem}_*.json"))
    for old in snaps[:-keep]:
        old.unlink(missing_ok=True)


def _json_dump(path: Path, data: Any) -> None:
    if path.exists():
        snap = BACKUP_DIR / f"{path.stem}_{datetime.datetime.now():%Y-%m-%d_%H%M%S}.json"
        shutil.copy2(path, snap)
        _trim_backups(path.stem)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")


def load_words() -> Dict[str, Dict[str, str]]:
    if not WORDS_FILE.exists():
        WORDS_FILE.write_text("{}", encoding="utf-8")
    return json.loads(WORDS_FILE.read_text(encoding="utf-8"))


def save_words(words: Dict[str, Dict[str, str]]) -> None:
    _json_dump(WORDS_FILE, words)


def load_learned() -> List[str]:
    if not LEARNED_FILE.exists():
        LEARNED_FILE.write_text("[]", encoding="utf-8")
    return json.loads(LEARNED_FILE.read_text(encoding="utf-8"))


def save_learned(learned: List[str]) -> None:
    _json_dump(LEARNED_FILE, learned)


# ──────────────────────────── Notion 同期 ───────────────────────────
notion = Client(auth=NOTION_TOKEN)


def fetch_notion_rows() -> List[Dict[str, str]]:
    """Notion DB → [{word, meaning, memo}, …]"""
    try:
        results = notion.databases.query(database_id=NOTION_DB_ID)["results"]
    except APIResponseError as e:
        body = e.body if isinstance(e.body, dict) else {}
        msg  = body.get("message", str(e))
        st.error(f"❌ {e.status} – {e.code}\n{msg}")
        st.stop()

    rows: List[Dict[str, str]] = []
    for r in results:
        rows.append(
            {
                "word":    r["properties"][PROP_WORD]["title"][0]["plain_text"],
                "meaning": r["properties"][PROP_MEAN]["rich_text"][0]["plain_text"],
                "memo": (
                    r["properties"][PROP_MEMO]["rich_text"][0]["plain_text"]
                    if r["properties"][PROP_MEMO]["rich_text"]
                    else ""
                ),
            }
        )
    return rows


def sync_from_notion() -> Dict[str, Dict[str, str]]:
    words: Dict[str, Dict[str, str]] = {}
    for entry in fetch_notion_rows():
        words[entry["word"]] = {"meaning": entry["meaning"], "memo": entry["memo"]}
    save_words(words)
    return words


# ──────────────────────────── セッション初期化 ───────────────────────────
if "words" not in st.session_state:
    st.session_state["words"]   = load_words()
    st.session_state["learned"] = load_learned()
    # 1 回だけ Notion と同期
    st.session_state["words"] |= sync_from_notion()

# ドロップダウン用
st.session_state["all_words_for_select"] = sorted(st.session_state["words"])


# ──────────────────────────── サイドバー ───────────────────────────
actions = sidebar()

# === 追加 ===
new_word, new_mean, new_memo, add_clicked = actions["add"]
if add_clicked and new_word and new_mean:
    st.session_state["words"][new_word] = {"meaning": new_mean, "memo": new_memo}
    save_words(st.session_state["words"])
    st.success(f"✅ **{new_word}** を追加しました！")

# === 検索 ===
query = actions["search"]
if query:
    results = {
        w: v
        for w, v in st.session_state["words"].items()
        if query.lower() in w.lower() or query.lower() in v["meaning"].lower()
    }
    st.markdown(f"### 🔍 検索結果 ({len(results)}) 件")
    for w, v in results.items():
        st.write(f"- **{w}** – {v['meaning']}")

# === 削除 ===
del_target, del_clicked = actions["delete"]
if del_clicked and del_target in st.session_state["words"]:
    st.session_state["words"].pop(del_target)
    st.session_state["learned"] = [w for w in st.session_state["learned"] if w != del_target]
    save_words(st.session_state["words"])
    save_learned(st.session_state["learned"])
    st.success(f"🗑️ **{del_target}** を削除しました！")


# ──────────────────────────── メイン画面 ───────────────────────────
st.markdown("## 🧠 AI 単語カード")
mode = st.radio("モードを選んでください", ("学習モード", "復習モード"), horizontal=True)

words   = st.session_state["words"]
learned = st.session_state["learned"]

if mode == "学習モード":
    queue = [w for w in words if w not in learned]
    if not queue:
        st.success("🎉 すべての単語を覚えました！")
        st.stop()

    current = queue[0]
    entry   = words[current]
    main_card(current, entry["meaning"], entry["memo"])

    c1, c2 = st.columns(2)
    with c1:
        if big_button("覚えた", key="learned_btn_"):
            learned.append(current)
            save_learned(learned)
            st.rerun()         # ← ここ
    with c2:
        big_button("覚えていない", key="retry_btn_")

else:  # 復習モード
    if not learned:
        st.success("👏 復習する単語はありません！")
        st.stop()

    target = st.selectbox("復習する単語を選んでください", learned, key="review_select")
    entry  = words[target]
    main_card(target, entry["meaning"], entry["memo"])

    c1, c2 = st.columns(2)
    with c1:
        if big_button("覚え直し", key="relearn_btn_"):
            learned.remove(target)
            save_learned(learned)
            st.rerun()         # ← ここ
    with c2:
        big_button("覚えていない", key="review_ng_btn_")
