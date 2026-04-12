from __future__ import annotations

import os
import threading
import time
import traceback
from html import escape
from urllib.parse import urlparse

import requests

from engine import ShortlinkBypassEngine

API_BASE = "https://api.telegram.org"
POLL_TIMEOUT = 30
PROGRESS_UPDATE_SECONDS = 8


class TelegramShortlinkBot:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"{API_BASE}/bot{token}"
        self.session = requests.Session()
        self.offset = 0

    def api(self, method: str, **kwargs):
        response = self.session.post(f"{self.base_url}/{method}", json=kwargs, timeout=60)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(data)
        return data["result"]

    def send_message(self, chat_id: int, text: str, reply_to_message_id: int | None = None):
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_to_message_id:
            payload["reply_parameters"] = {"message_id": reply_to_message_id}
        return self.api("sendMessage", **payload)

    def edit_message(self, chat_id: int, message_id: int, text: str):
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        return self.api("editMessageText", **payload)

    def safe_edit_message(self, chat_id: int, message_id: int, text: str) -> bool:
        try:
            self.edit_message(chat_id, message_id, text)
            return True
        except Exception as exc:
            if "message is not modified" in str(exc).lower():
                return True
            print(f"edit_message error: {exc}", flush=True)
            return False

    def progress_profile(self, url: str, elapsed: int) -> tuple[str, str, str]:
        host = urlparse(url).netloc.lower()
        if host == "link.adlink.click" or host.endswith(".adlink.click"):
            if elapsed < 6:
                stage = "cek family dan entry page"
            elif elapsed < 12:
                stage = "coba tembus Cloudflare"
            elif elapsed < 20:
                stage = "ambil link final dari blog adlink"
            else:
                stage = "fallback ke rantai maqal360"
            note = "Normalnya 10 sampai 20 detik. Kalau fast-lane gagal, bot turun ke fallback yang lebih lama."
            return host, stage, note
        if host == "oii.la" or host.endswith(".oii.la"):
            if elapsed < 15:
                stage = "cek token dan config captcha"
            else:
                stage = "analisis lane bypass"
            note = "Kalau token/redirect bisa diekstrak cepat, hasil biasanya keluar lebih singkat."
            return host, stage, note
        if host == "shrinkme.click" or host.endswith(".shrinkme.click"):
            if elapsed < 15:
                stage = "cek entry page dan timer"
            else:
                stage = "analisis captcha dan next hop"
            note = "Family ini masih cenderung lebih berat kalau captcha gate aktif."
            return host, stage, note
        return host or url, "analisis target", "Bot lagi map alur link dulu."

    def format_progress(self, url: str, elapsed: int, initial: bool = False) -> str:
        target, stage, note = self.progress_profile(url, elapsed)
        lines = [
            "<b>Bypass sedang diproses...</b>",
            f"<b>Target:</b> <code>{escape(target)}</code>",
            f"<b>Tahap:</b> {escape(stage)}",
            f"<b>Elapsed:</b> {elapsed}s",
        ]
        if initial:
            lines.append("<i>Bot bakal update status di pesan ini, jadi tidak diam doang.</i>")
        if note:
            lines.append(f"<i>{escape(note)}</i>")
        return "\n".join(lines)

    def format_result(self, result):
        if result.status == 1 and result.bypass_url:
            return "\n".join([
                f"<b>Bypass {escape(result.family)}:</b>",
                f"<code>{escape(result.bypass_url)}</code>",
            ])

        lines = [
            f"<b>Family:</b> {escape(result.family)}",
            f"<b>Message:</b> {escape(result.message)}",
        ]
        if result.facts.get("captcha_type"):
            lines.append(f"<b>Captcha:</b> {escape(str(result.facts.get('captcha_type')))}")
        if result.facts.get("sitekey"):
            lines.append(f"<b>Sitekey:</b> <code>{escape(str(result.facts.get('sitekey')))}</code>")
        if result.facts.get("counter_value"):
            lines.append(f"<b>Timer:</b> {escape(str(result.facts.get('counter_value')))}")
        if result.stage:
            lines.append(f"<b>Stage:</b> {escape(str(result.stage))}")
        if result.blockers:
            lines.append("")
            lines.append("<b>Blockers:</b>")
            for item in result.blockers[:4]:
                lines.append(f"- {escape(item)}")
        return "\n".join(lines)

    def handle_text(self, chat_id: int, message_id: int, text: str):
        parts = text.strip().split(maxsplit=1)
        raw_command = parts[0].strip()
        command = raw_command.split("@", 1)[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        print(f"handle_text chat_id={chat_id} raw_command={raw_command} command={command} arg={arg[:120]}", flush=True)

        if command in {"/start", "/help"}:
            self.send_message(
                chat_id,
                "<b>Perintah:</b>\n"
                "<code>/bypass URL</code>\n"
                "<code>/adlink URL</code>\n\n"
                "Bot sekarang kasih ack cepat lalu update status berkala di pesan yang sama kalau prosesnya lama.",
                reply_to_message_id=message_id,
            )
            return

        if command not in {"/bypass", "/adlink"}:
            return
        if not arg:
            self.send_message(chat_id, "Format: <code>/bypass URL</code>", reply_to_message_id=message_id)
            return

        status_message_id = None
        try:
            status_message = self.send_message(
                chat_id,
                self.format_progress(arg, 0, initial=True),
                reply_to_message_id=message_id,
            )
            status_message_id = status_message.get("message_id")
        except Exception as exc:
            print(f"initial status send error: {exc}", flush=True)

        box = {}

        def worker():
            try:
                engine = ShortlinkBypassEngine()
                box["result"] = engine.analyze(arg)
            except Exception as exc:
                box["error"] = exc
                box["traceback"] = traceback.format_exc()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        started_at = time.time()
        next_update = PROGRESS_UPDATE_SECONDS
        while thread.is_alive():
            thread.join(timeout=1)
            elapsed = int(time.time() - started_at)
            if status_message_id and elapsed >= next_update:
                self.safe_edit_message(chat_id, status_message_id, self.format_progress(arg, elapsed))
                next_update += PROGRESS_UPDATE_SECONDS

        if box.get("error") is not None:
            print(box.get("traceback") or box["error"], flush=True)
            final_text = f"Gagal: <code>{escape(str(box['error']))}</code>"
        else:
            final_text = self.format_result(box["result"])

        if status_message_id:
            if not self.safe_edit_message(chat_id, status_message_id, final_text):
                self.send_message(chat_id, final_text, reply_to_message_id=message_id)
        else:
            self.send_message(chat_id, final_text, reply_to_message_id=message_id)

    def run(self):
        while True:
            try:
                updates = self.api(
                    "getUpdates",
                    timeout=POLL_TIMEOUT,
                    offset=self.offset,
                    allowed_updates=["message"],
                )
                for update in updates:
                    self.offset = update["update_id"] + 1
                    message = update.get("message") or {}
                    text = message.get("text")
                    chat = message.get("chat") or {}
                    print(
                        f"update update_id={update.get('update_id')} chat_id={chat.get('id')} chat_type={chat.get('type')} text={repr(text)[:240]}",
                        flush=True,
                    )
                    if not text:
                        continue
                    self.handle_text(chat.get("id"), message.get("message_id"), text)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"loop error: {exc}", flush=True)
                traceback.print_exc()
                time.sleep(3)


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN belum diisi")
    print("shortlink-bypass-bot starting", flush=True)
    TelegramShortlinkBot(token).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
