import streamlit as st
from typing import Tuple


# ───────────────────────────────────────── sidebar ──────────────────────────────────────────
def sidebar() -> dict:
    st.sidebar.markdown("### 📌 単語の追加")
    new_word  = st.sidebar.text_input("単語を追加", key="add_word")
    new_mean  = st.sidebar.text_input("意味を追加", key="add_mean")
    new_memo  = st.sidebar.text_input("一言メモを追加 (任意)", key="add_memo")
    add_btn   = st.sidebar.button("追加する", key="add_btn")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 単語検索")
    query = st.sidebar.text_input("キーワードを入力", key="search_box")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🗑️ 単語の削除")
    del_target = st.sidebar.selectbox(
        "削除する単語を選んでください",
        st.session_state.get("all_words_for_select", []),
        key="delete_select",
    )
    del_btn = st.sidebar.button("削除する", key="delete_btn")

    return {
        "add":    (new_word, new_mean, new_memo, add_btn),
        "search": query,
        "delete": (del_target, del_btn),
    }


# ────────────────────────────────────────── main card ───────────────────────────────────────
def main_card(word: str, meaning: str, memo: str) -> None:
    st.markdown(f"## {word}  📝")
    st.write(meaning)
    if memo:
        st.info(memo)


# ───────────────────────────────────────── big button ───────────────────────────────────────
def big_button(label: str, *, key: str) -> bool:
    """ワイドなボタンを返す"""
    return st.button(
        label,
        key=key,
        use_container_width=True,
        help="クリックで次の単語へ",
    )
