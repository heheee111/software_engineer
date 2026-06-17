# -*- coding: utf-8 -*-

from drg_agent.virtual_docs import VirtualDocumentStore, next_patch_version


def test_next_patch_version():
    assert next_patch_version("1.0.0") == "1.0.1"
    assert next_patch_version("2.3") == "2.3.1"
    assert next_patch_version(None) == "0.0.1"


def test_submit_and_update_versions(tmp_path):
    store = VirtualDocumentStore(tmp_path)

    first = store.submit(
        content="# SRS\n首次提交",
        doc_type="srs",
        title="需求规格说明书",
        change_note="首次提交",
        source_agent="docgen",
    )

    assert first["status"] == "success"
    assert first["current_version"] == "1.0.0"
    assert len(first["versions"]) == 1

    second = store.submit(
        content="# SRS\n修订版",
        doc_type="srs",
        title="需求规格说明书",
        change_note="修订说明",
        source_agent="web",
        doc_id=first["doc_id"],
    )

    assert second["status"] == "success"
    assert second["current_version"] == "1.0.1"
    assert len(second["versions"]) == 2
    assert second["versions"][1]["change_note"] == "修订说明"

    old = store.get(first["doc_id"], version="1.0.0")
    latest = store.get(first["doc_id"])
    assert old["content"].endswith("首次提交")
    assert latest["content"].endswith("修订版")


def test_list_by_type(tmp_path):
    store = VirtualDocumentStore(tmp_path)
    store.submit(content="SRS", doc_type="srs", title="SRS")
    store.submit(content="AI", doc_type="ai_custom", title="AI 自定义")

    srs_docs = store.list(doc_type="srs")

    assert len(srs_docs) == 1
    assert srs_docs[0]["doc_type"] == "srs"
