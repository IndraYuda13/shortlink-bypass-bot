import unittest

from bot import TelegramShortlinkBot


class FakeBot(TelegramShortlinkBot):
    def __init__(self):
        super().__init__("dummy")
        self.allowed = True
        self.sent_messages = []
        self.join_gate_calls = []
        self.callback_answers = []
        self.edits = []

    def ensure_join_access(self, user_id):
        return (self.allowed, None if self.allowed else "left")

    def send_message(self, chat_id, text, reply_to_message_id=None, reply_markup=None):
        payload = {
            "chat_id": chat_id,
            "text": text,
            "reply_to_message_id": reply_to_message_id,
            "reply_markup": reply_markup,
        }
        self.sent_messages.append(payload)
        return {"message_id": 123}

    def send_join_gate(self, chat_id, message_id=None):
        self.join_gate_calls.append({"chat_id": chat_id, "message_id": message_id})
        return {"message_id": 456}

    def answer_callback_query(self, callback_query_id, text=None, show_alert=False):
        self.callback_answers.append({
            "callback_query_id": callback_query_id,
            "text": text,
            "show_alert": show_alert,
        })
        return True

    def safe_edit_message(self, chat_id, message_id, text, reply_markup=None):
        self.edits.append({
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "reply_markup": reply_markup,
        })
        return True


class BotTests(unittest.TestCase):
    def test_plain_url_is_treated_as_bypass(self):
        bot = FakeBot()
        command, arg = bot.parse_command("https://shrinkme.click/ZTvkQYPJ")
        self.assertEqual(command, "/bypass")
        self.assertEqual(arg, "https://shrinkme.click/ZTvkQYPJ")

    def test_non_member_gets_join_gate(self):
        bot = FakeBot()
        bot.allowed = False

        bot.handle_text(1, 10, 99, "private", "/start")

        self.assertEqual(len(bot.join_gate_calls), 1)
        self.assertEqual(bot.join_gate_calls[0]["chat_id"], 1)
        self.assertEqual(len(bot.sent_messages), 0)

    def test_start_for_member_sends_helpful_message(self):
        bot = FakeBot()

        bot.handle_text(1, 10, 99, "private", "/start")

        self.assertEqual(len(bot.sent_messages), 1)
        self.assertIn("Shortlink Bypass Bot", bot.sent_messages[0]["text"])
        self.assertIn("/bypass URL", bot.sent_messages[0]["text"])

    def test_check_join_callback_unlocks_access_message(self):
        bot = FakeBot()
        callback_query = {
            "id": "abc",
            "data": "check_join",
            "from": {"id": 99},
            "message": {"message_id": 77, "chat": {"id": 1}},
        }

        bot.handle_callback(callback_query)

        self.assertEqual(len(bot.callback_answers), 1)
        self.assertIn("aksesmu udah kebuka", bot.callback_answers[0]["text"])
        self.assertEqual(len(bot.edits), 1)
        self.assertIn("Siap, bot bypass aktif.", bot.edits[0]["text"])

    def test_unknown_command_gets_help_hint(self):
        bot = FakeBot()

        bot.handle_text(1, 10, 99, "private", "/apaaja")

        self.assertEqual(len(bot.sent_messages), 1)
        self.assertIn("Command belum dikenal", bot.sent_messages[0]["text"])


if __name__ == "__main__":
    unittest.main()
