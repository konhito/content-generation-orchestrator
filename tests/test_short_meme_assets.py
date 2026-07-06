from src.short.meme_assets import _select_giphy_item, resolve_meme_assets


def test_resolve_meme_assets_fetches_and_attaches_imgflip_metadata(tmp_path, monkeypatch):
    templates = [
        {"id": "11", "name": "Surprised Pikachu"},
        {"id": "22", "name": "Drake Hotline Bling"},
    ]
    created = []

    monkeypatch.setattr("src.short.meme_assets.fetch_templates", lambda: templates)

    def fake_create_meme(template_id, text_top, text_bottom, out_dir, username=None, password=None):
        out_path = out_dir / f"{template_id}.jpg"
        out_path.write_text(f"{template_id}:{text_top}:{text_bottom}", encoding="utf-8")
        created.append((template_id, text_top, text_bottom, out_dir))
        return out_path

    monkeypatch.setattr("src.short.meme_assets.create_meme", fake_create_meme)

    memes = [
        {
            "type": "meme",
            "query": "choice between two models",
            "template_hint": "drake",
            "meme_text_top": "MODEL A",
            "meme_text_bottom": "MODEL B",
        }
    ]

    resolved = resolve_meme_assets(memes, tmp_path, public_root=tmp_path)

    assert len(resolved) == 1
    assert resolved[0]["meme_template_id"] == "22"
    assert resolved[0]["meme_template_name"] == "Drake Hotline Bling"
    assert resolved[0]["image_path"] == "22.jpg"
    assert resolved[0]["provider"] == "imgflip"
    assert created[0][0] == "22"


def test_resolve_meme_assets_fetches_and_attaches_giphy_metadata(tmp_path, monkeypatch):
    items = [
        {
            "id": "gif123",
            "title": "Anime girl coding reaction",
            "url": "https://giphy.com/gifs/gif123",
            "images": {"downsized": {"url": "https://media.giphy.com/media/gif123/giphy.gif"}},
        }
    ]

    monkeypatch.setattr("src.short.meme_assets.get_giphy_api_key", lambda: "key")
    monkeypatch.setattr("src.short.meme_assets.fetch_giphy_items", lambda query, api_key, limit=8, kind="gifs": items)

    def fake_download_giphy_asset(item, out_dir):
        out_path = out_dir / "giphy_gif123.mp4"
        out_path.write_bytes(b"mp4")
        return out_path

    monkeypatch.setattr("src.short.meme_assets.download_giphy_asset", fake_download_giphy_asset)

    memes = [
        {
            "type": "meme",
            "query": "reality of coding",
            "template_hint": "anime girl",
            "meme_text_top": "DEBUGGING",
            "meme_text_bottom": "AT 3AM",
        }
    ]

    resolved = resolve_meme_assets(memes, tmp_path, public_root=tmp_path, provider="giphy")

    assert resolved[0]["provider"] == "giphy"
    assert resolved[0]["giphy_id"] == "gif123"
    assert resolved[0]["giphy_title"] == "Anime girl coding reaction"
    assert resolved[0]["image_path"] == "giphy_gif123.mp4"


def test_giphy_query_uses_anime_reactions_not_topic_terms(tmp_path, monkeypatch):
    items = [
        {
            "id": "gif123",
            "title": "Anime girl reaction",
            "url": "https://giphy.com/gifs/gif123",
            "images": {"downsized": {"url": "https://media.giphy.com/media/gif123/giphy.gif"}},
        }
    ]
    queries = []

    monkeypatch.setattr("src.short.meme_assets.get_giphy_api_key", lambda: "key")

    def fake_fetch_giphy_items(query, api_key, limit=8, kind="gifs"):
        queries.append(query)
        return items

    monkeypatch.setattr("src.short.meme_assets.fetch_giphy_items", fake_fetch_giphy_items)
    monkeypatch.setattr("src.short.meme_assets.download_giphy_asset", lambda item, out_dir: out_dir / "giphy_gif123.mp4")

    resolve_meme_assets(
        [
            {
                "type": "meme",
                "query": "GTA 6 physical disc rumor",
                "template_hint": "surprised",
                "meme_text_top": "CONFIDENTLY WRONG",
                "meme_text_bottom": "REAL STORY IS SIGNAL VERSUS NOISE",
            }
        ],
        tmp_path,
        public_root=tmp_path,
        provider="giphy",
    )

    assert queries == ["anime girl surprised reaction"]


def test_select_giphy_item_rejects_unrelated_human_reactions():
    items = [
        {"id": "human", "title": "Tom Hanks Hello GIF", "images": {"original": {}}},
        {"id": "anime", "title": "Shocked Anime Girl GIF", "images": {"original": {}}},
    ]

    assert _select_giphy_item(items, offset=0)["id"] == "anime"


def test_mixed_provider_alternates_imgflip_and_giphy(tmp_path, monkeypatch):
    calls = []

    def fake_imgflip(memes, out_dir, **kwargs):
        calls.append(("imgflip", len(memes)))
        return [{**memes[0], "provider": "imgflip", "image_path": "classic.jpg"}]

    def fake_giphy(memes, out_dir, **kwargs):
        calls.append(("giphy", len(memes)))
        return [{**memes[0], "provider": "giphy", "image_path": "anime.mp4"}]

    monkeypatch.setattr("src.short.meme_assets._resolve_imgflip_assets", fake_imgflip)
    monkeypatch.setattr("src.short.meme_assets._resolve_giphy_assets", fake_giphy)
    memes = [{"type": "meme", "query": str(index)} for index in range(4)]

    resolved = resolve_meme_assets(memes, tmp_path, provider="mixed")

    assert [item["provider"] for item in resolved] == ["imgflip", "giphy", "imgflip", "giphy"]
    assert calls == [("imgflip", 1), ("giphy", 1), ("imgflip", 1), ("giphy", 1)]
