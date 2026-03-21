"""Integration tests for AnkiConnect service and router."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.anki_service import (
    AnkiConnectClient,
)
from app.exceptions import AnkiConnectError
from app.models.schemas import (
    WordDefinition,
    KanjiDefinition,
    AnkiBatchResponse,
)


class TestAnkiConnectClient:
    """Tests for AnkiConnectClient class."""

    @pytest.mark.asyncio
    async def test_invoke_success(self):
        """Test successful AnkiConnect invocation."""
        client = AnkiConnectClient()
        mock_response = {"result": ["model1", "model2"], "error": None}

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = AsyncMock(
                json=AsyncMock(return_value=mock_response), raise_for_status=AsyncMock()
            )()

            result = await client.invoke("modelNames", {})
            assert result == ["model1", "model2"]

    @pytest.mark.asyncio
    async def test_invoke_anki_error(self):
        """Test AnkiConnect error response."""
        client = AnkiConnectClient()
        mock_response = {"result": None, "error": "Invalid action"}

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = AsyncMock(
                json=AsyncMock(return_value=mock_response), raise_for_status=AsyncMock()
            )()

            with pytest.raises(AnkiConnectError, match="Invalid action"):
                await client.invoke("invalidAction", {})

    @pytest.mark.asyncio
    async def test_invoke_timeout(self):
        """Test AnkiConnect timeout handling."""
        import httpx

        client = AnkiConnectClient(timeout=1)

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Timeout")

            with pytest.raises(AnkiConnectError, match="timed out"):
                await client.invoke("modelNames", {})

    @pytest.mark.asyncio
    async def test_invoke_connection_error(self):
        """Test AnkiConnect connection error."""
        import httpx

        client = AnkiConnectClient()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(AnkiConnectError, match="Failed to connect"):
                await client.invoke("modelNames", {})

    @pytest.mark.asyncio
    async def test_get_model_names(self):
        """Test getting model names."""
        client = AnkiConnectClient()
        mock_response = {"result": ["Word", "Kanji"], "error": None}

        with patch.object(client, "invoke", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = ["Word", "Kanji"]
            result = await client.get_model_names()
            assert result == ["Word", "Kanji"]
            mock_invoke.assert_called_once_with("modelNames")

    @pytest.mark.asyncio
    async def test_get_model_field_names(self):
        """Test getting model field names."""
        client = AnkiConnectClient()

        with patch.object(client, "invoke", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = ["Word", "Furigana", "Definitions"]
            result = await client.get_model_field_names("Word")
            assert result == ["Word", "Furigana", "Definitions"]
            mock_invoke.assert_called_once_with(
                "modelFieldNames", {"modelName": "Word"}
            )

    @pytest.mark.asyncio
    async def test_check_valid_model_success(self):
        """Test successful model validation."""
        client = AnkiConnectClient()

        with patch.object(client, "invoke", new_callable=AsyncMock) as mock_invoke:
            # First call returns models, second returns fields
            mock_invoke.side_effect = [
                ["Word", "Kanji"],
                ["Word", "Furigana", "Definitions"],
            ]
            result = await client.check_valid_model("Word", ["Word", "Furigana"])
            assert result is True

    @pytest.mark.asyncio
    async def test_check_valid_model_not_found(self):
        """Test model validation with missing model."""
        client = AnkiConnectClient()

        with patch.object(client, "invoke", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = ["Word", "Kanji"]
            with pytest.raises(AnkiConnectError, match="not found"):
                await client.check_valid_model("InvalidModel", ["Word"])

    @pytest.mark.asyncio
    async def test_check_valid_model_missing_fields(self):
        """Test model validation with missing required fields."""
        client = AnkiConnectClient()

        with patch.object(client, "invoke", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.side_effect = [
                ["Word", "Kanji"],
                ["Word", "Furigana"],  # Missing "Definitions"
            ]
            with pytest.raises(AnkiConnectError, match="missing required fields"):
                await client.check_valid_model("Word", ["Word", "Furigana", "Definitions"])

    @pytest.mark.asyncio
    async def test_add_notes_success(self):
        """Test successful note addition."""
        client = AnkiConnectClient()

        with patch.object(client, "invoke", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = [1234567890, 1234567891]
            result = await client.add_notes(
                "TestDeck",
                [
                    {"modelName": "Word", "fields": {"Word": "test"}},
                    {"modelName": "Word", "fields": {"Word": "test2"}},
                ],
            )
            assert result == [1234567890, 1234567891]

    @pytest.mark.asyncio
    async def test_add_notes_failure(self):
        """Test note addition failure (all-or-nothing)."""
        client = AnkiConnectClient()

        with patch.object(client, "invoke", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = [None, None]  # AllFailed
            with pytest.raises(AnkiConnectError, match="Failed to add 2 out of 2"):
                await client.add_notes(
                    "TestDeck",
                    [
                        {"modelName": "Word", "fields": {"Word": "test"}},
                        {"modelName": "Word", "fields": {"Word": "test2"}},
                    ],
                )


class TestAddWordsToAnki:
    """Tests for add_words_to_anki function."""

    @pytest.mark.asyncio
    async def test_add_words_success(self):
        """Test successful word addition."""
        words = [
            WordDefinition(
                word="言葉",
                furigana="ことば",
                definitions=["word", "language"],
            ),
            WordDefinition(
                word="学生",
                furigana="がくせい",
                definitions=["student"],
            ),
        ]

        with patch.object(AnkiConnectClient, "check_valid_model", new_callable=AsyncMock):
            with patch.object(AnkiConnectClient, "create_deck", new_callable=AsyncMock):
                with patch.object(AnkiConnectClient, "add_notes", new_callable=AsyncMock) as mock_add:
                    mock_add.return_value = [111, 222]
                    result = await add_words_to_anki("TestDeck", words)
                    assert result.success_count == 2
                    assert result.failed_count == 0
                    assert result.duplicates_skipped == 0

    @pytest.mark.asyncio
    async def test_add_words_duplicate_detection(self):
        """Test duplicate word detection within batch."""
        words = [
            WordDefinition(word="言葉", furigana="ことば", definitions=["word"]),
            WordDefinition(word="言葉", furigana="ことば", definitions=["word"]),  # Duplicate
            WordDefinition(word="学生", furigana="がくせい", definitions=["student"]),
        ]

        with patch.object(AnkiConnectClient, "check_valid_model", new_callable=AsyncMock):
            with patch.object(AnkiConnectClient, "create_deck", new_callable=AsyncMock):
                with patch.object(AnkiConnectClient, "add_notes", new_callable=AsyncMock) as mock_add:
                    mock_add.return_value = [111, 222]
                    result = await add_words_to_anki("TestDeck", words)
                    assert result.success_count == 2
                    assert result.duplicates_skipped == 1

    @pytest.mark.asyncio
    async def test_add_words_tagging(self):
        """Test that words are tagged with 'from-gakuji'."""
        words = [
            WordDefinition(word="言葉", furigana="ことば", definitions=["word"]),
        ]

        with patch.object(AnkiConnectClient, "check_valid_model", new_callable=AsyncMock):
            with patch.object(AnkiConnectClient, "create_deck", new_callable=AsyncMock):
                with patch.object(AnkiConnectClient, "add_notes", new_callable=AsyncMock) as mock_add:
                    mock_add.return_value = [111]
                    await add_words_to_anki("TestDeck", words)

                    # Verify that tags include "from-gakuji"
                    call_args = mock_add.call_args[0]
                    notes = call_args[1]
                    assert len(notes) == 1
                    assert "from-gakuji" in notes[0]["tags"]

    @pytest.mark.asyncio
    async def test_add_words_invalid_model(self):
        """Test word addition with invalid model."""
        words = [
            WordDefinition(word="言葉", furigana="ことば", definitions=["word"]),
        ]

        with patch.object(AnkiConnectClient, "check_valid_model", new_callable=AsyncMock) as mock_check:
            mock_check.side_effect = AnkiConnectError("Model 'InvalidModel' not found")

            with pytest.raises(AnkiConnectError, match="not found"):
                await add_words_to_anki("TestDeck", words, model_name="InvalidModel")

    @pytest.mark.asyncio
    async def test_add_words_empty_list(self):
        """Test word addition with empty list."""
        words = []

        with patch.object(AnkiConnectClient, "check_valid_model", new_callable=AsyncMock):
            with patch.object(AnkiConnectClient, "create_deck", new_callable=AsyncMock):
                result = await add_words_to_anki("TestDeck", words)
                assert result.success_count == 0
                assert result.failed_count == 0


class TestAddKanjiToAnki:
    """Tests for add_kanji_to_anki function."""

    @pytest.mark.asyncio
    async def test_add_kanji_success(self):
        """Test successful kanji addition."""
        kanji = [
            KanjiDefinition(
                kanji="文",
                onyomi=["ぶん", "もん"],
                kunyomi=["ふみ"],
                definitions=["sentence", "letter"],
                jlpt_level=1,
            ),
            KanjiDefinition(
                kanji="学",
                onyomi=["がく"],
                kunyomi=["まな"],
                definitions=["study", "learn"],
                jlpt_level=1,
            ),
        ]

        with patch.object(AnkiConnectClient, "check_valid_model", new_callable=AsyncMock):
            with patch.object(AnkiConnectClient, "create_deck", new_callable=AsyncMock):
                with patch.object(AnkiConnectClient, "add_notes", new_callable=AsyncMock) as mock_add:
                    mock_add.return_value = [111, 222]
                    result = await add_kanji_to_anki("TestDeck", kanji)
                    assert result.success_count == 2
                    assert result.failed_count == 0
                    assert result.duplicates_skipped == 0

    @pytest.mark.asyncio
    async def test_add_kanji_duplicate_detection(self):
        """Test duplicate kanji detection by character."""
        kanji = [
            KanjiDefinition(
                kanji="文",
                onyomi=["ぶん"],
                kunyomi=["ふみ"],
                definitions=["sentence"],
            ),
            KanjiDefinition(
                kanji="文",  # Duplicate character
                onyomi=["もん"],
                kunyomi=["ふみ"],
                definitions=["sentence"],
            ),
            KanjiDefinition(
                kanji="学",
                onyomi=["がく"],
                kunyomi=["まな"],
                definitions=["study"],
            ),
        ]

        with patch.object(AnkiConnectClient, "check_valid_model", new_callable=AsyncMock):
            with patch.object(AnkiConnectClient, "create_deck", new_callable=AsyncMock):
                with patch.object(AnkiConnectClient, "add_notes", new_callable=AsyncMock) as mock_add:
                    mock_add.return_value = [111, 222]
                    result = await add_kanji_to_anki("TestDeck", kanji)
                    assert result.success_count == 2
                    assert result.duplicates_skipped == 1

    @pytest.mark.asyncio
    async def test_add_kanji_tagging(self):
        """Test that kanji are tagged with 'from-gakuji'."""
        kanji = [
            KanjiDefinition(
                kanji="文",
                onyomi=["ぶん"],
                kunyomi=["ふみ"],
                definitions=["sentence"],
            ),
        ]

        with patch.object(AnkiConnectClient, "check_valid_model", new_callable=AsyncMock):
            with patch.object(AnkiConnectClient, "create_deck", new_callable=AsyncMock):
                with patch.object(AnkiConnectClient, "add_notes", new_callable=AsyncMock) as mock_add:
                    mock_add.return_value = [111]
                    await add_kanji_to_anki("TestDeck", kanji)

                    # Verify that tags include "from-gakuji"
                    call_args = mock_add.call_args[0]
                    notes = call_args[1]
                    assert len(notes) == 1
                    assert "from-gakuji" in notes[0]["tags"]

    @pytest.mark.asyncio
    async def test_add_kanji_handles_none_jlpt(self):
        """Test kanji addition with None JLPT level."""
        kanji = [
            KanjiDefinition(
                kanji="文",
                onyomi=["ぶん"],
                kunyomi=["ふみ"],
                definitions=["sentence"],
                jlpt_level=None,  # None value
            ),
        ]

        with patch.object(AnkiConnectClient, "check_valid_model", new_callable=AsyncMock):
            with patch.object(AnkiConnectClient, "create_deck", new_callable=AsyncMock):
                with patch.object(AnkiConnectClient, "add_notes", new_callable=AsyncMock) as mock_add:
                    mock_add.return_value = [111]
                    result = await add_kanji_to_anki("TestDeck", kanji)
                    assert result.success_count == 1
                    assert result.failed_count == 0


class TestFieldMapping:
    """Tests for custom field mapping."""

    @pytest.mark.asyncio
    async def test_custom_word_field_mapping(self):
        """Test words with custom field mapping."""
        words = [
            WordDefinition(word="言葉", furigana="ことば", definitions=["word"]),
        ]
        custom_mapping = {
            "CustomWordField": "word",
            "CustomFuriganaField": "furigana",
            "CustomDefinitionsField": "definitions",
        }

        with patch.object(AnkiConnectClient, "check_valid_model", new_callable=AsyncMock) as mock_check:
            with patch.object(AnkiConnectClient, "create_deck", new_callable=AsyncMock):
                with patch.object(AnkiConnectClient, "add_notes", new_callable=AsyncMock) as mock_add:
                    mock_add.return_value = [111]

                    await add_words_to_anki(
                        "TestDeck",
                        words,
                        model_name="CustomModel",
                        field_mapping=custom_mapping,
                    )

                    # Verify model validation used custom fields
                    mock_check.assert_called_once()
                    call_args = mock_check.call_args[0]
                    assert set(call_args[1]) == set(custom_mapping.keys())

    @pytest.mark.asyncio
    async def test_custom_kanji_field_mapping(self):
        """Test kanji with custom field mapping."""
        kanji = [
            KanjiDefinition(
                kanji="文",
                onyomi=["ぶん"],
                kunyomi=["ふみ"],
                definitions=["sentence"],
            ),
        ]
        custom_mapping = {
            "KanjiCharacter": "kanji",
            "OnyomiReading": "onyomi",
            "KunyomiReading": "kunyomi",
            "Meanings": "definitions",
            "Level": "jlpt_level",
        }

        with patch.object(AnkiConnectClient, "check_valid_model", new_callable=AsyncMock) as mock_check:
            with patch.object(AnkiConnectClient, "create_deck", new_callable=AsyncMock):
                with patch.object(AnkiConnectClient, "add_notes", new_callable=AsyncMock) as mock_add:
                    mock_add.return_value = [111]

                    await add_kanji_to_anki(
                        "TestDeck",
                        kanji,
                        model_name="CustomKanjiModel",
                        field_mapping=custom_mapping,
                    )

                    # Verify model validation used custom fields
                    mock_check.assert_called_once()
                    call_args = mock_check.call_args[0]
                    assert set(call_args[1]) == set(custom_mapping.keys())
