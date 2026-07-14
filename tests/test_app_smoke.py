import csv
import re
import time
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


def _button(app, key):
    return next(widget for widget in app.button if widget.key == key)


class HskAppSmokeTest(unittest.TestCase):
    def test_vocab_file_has_all_official_rows_and_known_source_fixes(self):
        with Path("hsk_vocabnew_fixed.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 11000)
        self.assertEqual([int(row["id"]) for row in rows], list(range(1, 11001)))
        self.assertTrue(all(all(str(value).strip() for value in row.values()) for row in rows))
        self.assertEqual(rows[44]["pos_zh"], "形、代、（动、数、副）")
        self.assertEqual(rows[45]["pos_zh"], "代")
        self.assertEqual(rows[326]["word"], "打1")
        self.assertEqual(rows[5441]["trans_th"], "นัดหยุดงาน")

    def test_vocab_translations_are_clean_after_rebuild(self):
        han = re.compile(r"[\u3400-\u9fff]")
        thai = re.compile(r"[ก-๙]")
        with Path("hsk_vocabnew_fixed.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertTrue(all(thai.search(row["trans_th"]) for row in rows))
        self.assertFalse(any(han.search(row["trans_th"]) for row in rows))
        self.assertFalse(any(han.search(row["trans_en"]) for row in rows))
        self.assertFalse(any(han.search(row["example_th"]) for row in rows))
        self.assertFalse(any(han.search(row["example_en"]) for row in rows))
        self.assertFalse(any(row["example_zh"] == "这个词是语法词。" for row in rows))
        self.assertFalse(any(row["example_zh"].startswith("请给我一") and "|" not in row["example_zh"] for row in rows))

    def _guest_app(self):
        app = AppTest.from_file("streamlit_app.py", default_timeout=20)
        app.run()
        self.assertEqual(list(app.exception), [])
        _button(app, "id_anon_btn").click().run()
        self.assertEqual(list(app.exception), [])
        return app

    def test_guest_can_open_all_main_sections(self):
        app = self._guest_app()
        menu = next(widget for widget in app.radio if widget.key == "active_tab_radio")

        menu.set_value("Quiz").run()
        self.assertEqual(list(app.exception), [])
        listen = next(button for button in app.button if button.label == "ฟังเสียง → เลือกคำ")
        listen.click().run()
        self.assertEqual(list(app.exception), [])

        _button(app, "back_to_flashcard_btn").click().run()
        self.assertEqual(list(app.exception), [])
        self.assertEqual(app.session_state["active_tab_radio"], "Flashcard")

        menu = next(widget for widget in app.radio if widget.key == "active_tab_radio")
        menu.set_value("คำศัพท์").run()
        self.assertEqual(list(app.exception), [])

        menu = next(widget for widget in app.radio if widget.key == "active_tab_radio")
        menu.set_value("ประวัติ").run()
        self.assertEqual(list(app.exception), [])

    def test_quiz_auto_advance_moves_to_next_question_after_deadline(self):
        app = self._guest_app()
        app.session_state["active_tab_radio"] = "Quiz"
        app.run()
        self.assertEqual(list(app.exception), [])

        first_id = str(app.session_state["quiz_question"]["id"])
        app.session_state["quiz_auto_next"] = True
        app.session_state["quiz_auto_advance_pending"] = True
        app.session_state["quiz_auto_advance_at"] = time.time() - 1
        app.run()
        self.assertEqual(list(app.exception), [])
        self.assertNotEqual(str(app.session_state["quiz_question"]["id"]), first_id)

    def test_study_progress_shows_percentage_and_fills_bar(self):
        app = self._guest_app()
        progress_markup = "\n".join(widget.value for widget in app.markdown)
        self.assertIn("0 / 20 คำ (0%)", progress_markup)
        self.assertIn('style="width:0%"', progress_markup)

        app.session_state["remembered"] = {"1", "2", "3"}
        app.run()
        progress_markup = "\n".join(widget.value for widget in app.markdown)
        self.assertIn("3 / 20 คำ (15%)", progress_markup)
        self.assertIn('style="width:15%"', progress_markup)

    def test_theme_toggle_renders_without_errors(self):
        app = self._guest_app()
        theme = next(widget for widget in app.radio if widget.key == "theme_mode")
        theme.set_value("ดำ").run()
        self.assertEqual(list(app.exception), [])
        theme = next(widget for widget in app.radio if widget.key == "theme_mode")
        theme.set_value("ขาว").run()
        self.assertEqual(list(app.exception), [])

    def test_leaderboard_orders_by_correct_and_hides_private_players(self):
        app = self._guest_app()
        app.session_state["player_name"] = "Alice"
        app.session_state["_active_player_context"] = "Alice"
        app.session_state["players_data"] = {
            "Alice": {"correct": 8, "total": 10, "leaderboard_visible": True, "history": []},
            "Bob": {"correct": 9, "total": 20, "leaderboard_visible": True, "history": []},
            "Hidden": {"correct": 99, "total": 100, "leaderboard_visible": False, "history": []},
            "Guest": {"correct": 100, "total": 100, "leaderboard_visible": True, "history": []},
        }
        app.session_state["play_history"] = []
        app.session_state["active_tab_radio"] = "ประวัติ"
        app.run()
        self.assertEqual(list(app.exception), [])

        board = app.dataframe[0].value
        self.assertEqual(board["ผู้เล่น"].tolist(), ["Bob", "⭐ Alice (คุณ)"])
        self.assertNotIn("Hidden", board["ผู้เล่น"].tolist())
        self.assertNotIn("Guest", board["ผู้เล่น"].tolist())

    def test_wrong_card_does_not_repeat_within_next_five_cards(self):
        app = self._guest_app()
        app.session_state["player_name"] = "SpacingTester"
        app.session_state["_active_player_context"] = "SpacingTester"
        app.session_state["players_data"] = {
            "SpacingTester": {
                "correct": 0,
                "total": 0,
                "leaderboard_visible": False,
                "history": [],
            }
        }
        app.session_state["srs_data"] = {"SpacingTester": {}}
        app.session_state["play_history"] = []
        app.run()
        self.assertEqual(list(app.exception), [])

        first_id = str(app.session_state["current_word"]["id"])
        _button(app, "forget_btn").click().run()
        self.assertEqual(list(app.exception), [])

        for index in range(5):
            current_id = str(app.session_state["current_word"]["id"])
            self.assertNotEqual(current_id, first_id)
            if index < 4:
                _button(app, "forget_btn").click().run()
                self.assertEqual(list(app.exception), [])


if __name__ == "__main__":
    unittest.main()
