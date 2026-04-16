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
ALLOWED_MEMBER_STATUSES = {"member", "administrator", "creator"}


class TelegramShortlinkBot:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"{API_BASE}/bot{token}"
        self.session = requests.Session()
        self.offset = 0
        self.required_join_chat_id = int(os.environ.get("SHORTLINK_REQUIRED_JOIN_CHAT_ID", "-1003843116263"))
        self.required_join_title = os.environ.get("SHORTLINK_REQUIRED_JOIN_TITLE", "Cari Garapan").strip() or "Cari Garapan"
        self.required_join_link = os.environ.get("SHORTLINK_REQUIRED_JOIN_LINK", "https://t.me/+Vfpap1m10v5iODA1").strip()

    def api(self, method: str, **kwargs):
        response = self.session.post(f"{self.base_url}/{method}", json=kwargs, timeout=60)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(data)
        return data["result"]

    def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: int | None = None,
        reply_markup: dict | None = None,
    ):
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_to_message_id:
            payload["reply_parameters"] = {"message_id": reply_to_message_id}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.api("sendMessage", **payload)

    def edit_message(self, chat_id: int, message_id: int, text: str, reply_markup: dict | None = None):
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.api("editMessageText", **payload)

    def answer_callback_query(self, callback_query_id: str, text: str | None = None, show_alert: bool = False):
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        if show_alert:
            payload["show_alert"] = True
        return self.api("answerCallbackQuery", **payload)

    def safe_edit_message(self, chat_id: int, message_id: int, text: str, reply_markup: dict | None = None) -> bool:
        try:
            self.edit_message(chat_id, message_id, text, reply_markup=reply_markup)
            return True
        except Exception as exc:
            if "message is not modified" in str(exc).lower():
                return True
            print(f"edit_message error: {exc}", flush=True)
            return False

    def required_join_keyboard(self) -> dict:
        return {
            "inline_keyboard": [[
                {"text": "Join Cari Garapan", "url": self.required_join_link},
                {"text": "Sudah join, cek lagi", "callback_data": "check_join"},
            ]]
        }

    def required_join_text(self) -> str:
        return "\n".join([
            "<b>Akses bot dikunci dulu.</b>",
            f"Buat pakai bot ini, kamu wajib join grup <b>{escape(self.required_join_title)}</b> dulu.",
            "",
            "Setelah join, pencet tombol <b>Sudah join, cek lagi</b> di bawah.",
        ])

    def help_text(self) -> str:
        return "\n".join([
            "<b>Shortlink Bypass Bot</b>",
            "",
            "<b>Command utama:</b>",
            "<code>/bypass URL</code> , deteksi family otomatis lalu coba ambil hasil final",
            "<code>/adlink URL</code> , paksa jalur Adlink kalau targetnya keluarga adlink",
            "<code>/status</code> , lihat status singkat bot dan family yang lagi disupport",
            "<code>/ping</code> , cek bot masih nyala atau tidak",
            "<code>/help</code> , tampilkan bantuan ini lagi",
            "",
            "<b>Tips:</b>",
            "- Bisa kirim plain URL langsung, bot bakal anggap itu sama seperti <code>/bypass URL</code>",
            "- Hasil final cuma dianggap valid kalau memang sudah keluar URL downstream, bukan interstitial doang",
            "- Kalau proses agak lama, bot update status di pesan yang sama biar gak spam",
            "",
            "<b>Contoh:</b>",
            "<code>/bypass https://shrinkme.click/ZTvkQYPJ</code>",
            "<code>/bypass https://link.adlink.click/CBr27fn4of3</code>",
        ])

    def start_text(self) -> str:
        return "\n".join([
            "<b>Siap, bot bypass aktif.</b>",
            f"Akses dipakai lewat bot ini, tapi user tetap wajib join grup <b>{escape(self.required_join_title)}</b> dulu.",
            "Kalau aksesmu sudah kebuka, tinggal kirim <code>/bypass URL</code> atau langsung kirim URL-nya.",
            "",
            self.help_text(),
        ])

    def status_text(self) -> str:
        return "\n".join([
            "<b>Status bot:</b> online",
            "",
            "<b>Family saat ini:</b>",
            "- <code>link.adlink.click</code> , live bypass",
            "- <code>shrinkme.click</code> , live bypass",
            "- <code>oii.la</code> , analysis only",
            "",
            "<b>Belum ada handler:</b>",
            "- <code>linkcut.pro</code>",
            "- <code>aii.sh</code>",
            "- <code>tpi.li</code>",
            "- <code>lnbz.la</code>",
        ])

    def is_plain_url(self, text: str) -> bool:
        value = text.strip()
        if not value.lower().startswith(("http://", "https://")):
            return False
        parsed = urlparse(value)
        return bool(parsed.scheme and parsed.netloc)

    def parse_command(self, text: str) -> tuple[str, str]:
        raw = text.strip()
        if self.is_plain_url(raw):
            return "/bypass", raw
        parts = raw.split(maxsplit=1)
        raw_command = parts[0].strip() if parts else ""
        command = raw_command.split("@", 1)[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        return command, arg

    def member_has_access(self, status: str | None) -> bool:
        return (status or "").lower() in ALLOWED_MEMBER_STATUSES

    def ensure_join_access(self, user_id: int | None) -> tuple[bool, str | None]:
        if not user_id:
            return False, "missing-user-id"
        try:
            member = self.api("getChatMember", chat_id=self.required_join_chat_id, user_id=user_id)
        except Exception as exc:
            print(f"getChatMember error: {exc}", flush=True)
            return False, f"cek membership gagal: {exc}"
        status = str(member.get("status") or "")
        if self.member_has_access(status):
            return True, None
        return False, status or "not-member"

    def send_join_gate(self, chat_id: int, message_id: int | None = None):
        return self.send_message(
            chat_id,
            self.required_join_text(),
            reply_to_message_id=message_id,
            reply_markup=self.required_join_keyboard(),
        )

    def handle_callback(self, callback_query: dict):
        data = (callback_query.get("data") or "").strip()
        query_id = callback_query.get("id")
        from_user = callback_query.get("from") or {}
        message = callback_query.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        message_id = message.get("message_id")
        user_id = from_user.get("id")

        if data != "check_join" or not query_id or not chat_id or not message_id or not user_id:
            return

        allowed, _detail = self.ensure_join_access(user_id)
        if allowed:
            self.answer_callback_query(query_id, "Sip, aksesmu udah kebuka.")
            self.safe_edit_message(chat_id, message_id, self.start_text())
            return

        self.answer_callback_query(query_id, "Masih belum kebaca join-nya. Coba join dulu lalu pencet lagi.")
        self.safe_edit_message(chat_id, message_id, self.required_join_text(), reply_markup=self.required_join_keyboard())

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
            note = "Normalnya 5 sampai 20 detik. Kalau fast-lane gagal, bot turun ke fallback yang lebih lama."
            return host, stage, note
        if host == "oii.la" or host.endswith(".oii.la"):
            if elapsed < 15:
                stage = "cek token dan config captcha"
            else:
                stage = "analisis lane bypass"
            note = "Kalau token atau redirect bisa diekstrak cepat, hasil biasanya keluar lebih singkat."
            return host, stage, note
        if host == "shrinkme.click" or host.endswith(".shrinkme.click"):
            if elapsed < 12:
                stage = "cek entry page dan timer"
            else:
                stage = "analisis next hop final"
            note = "Family ini masih punya timer downstream yang cukup keras."
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

    def handle_text(self, chat_id: int, message_id: int, user_id: int | None, chat_type: str, text: str):
        command, arg = self.parse_command(text)
        print(f"handle_text chat_id={chat_id} chat_type={chat_type} command={command} arg={arg[:120]}", flush=True)

        allowed, _detail = self.ensure_join_access(user_id)
        if not allowed:
            self.send_join_gate(chat_id, message_id)
            return

        if command in {"/start", "/help"}:
            text_out = self.start_text() if command == "/start" else self.help_text()
            self.send_message(chat_id, text_out, reply_to_message_id=message_id)
            return

        if command == "/status":
            self.send_message(chat_id, self.status_text(), reply_to_message_id=message_id)
            return

        if command == "/ping":
            self.send_message(chat_id, "<b>Pong.</b> Bot aktif dan siap kerja.", reply_to_message_id=message_id)
            return

        if command not in {"/bypass", "/adlink"}:
            self.send_message(
                chat_id,
                "Command belum dikenal. Coba <code>/help</code> buat lihat cara pakainya, atau langsung kirim URL shortlink.",
                reply_to_message_id=message_id,
            )
            return
        if not arg:
            self.send_message(
                chat_id,
                "Format yang benar:\n<code>/bypass URL</code>\n\nAtau kirim URL langsung tanpa command juga boleh.",
                reply_to_message_id=message_id,
            )
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

        box: dict[str, object] = {}

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
                    allowed_updates=["message", "callback_query"],
                )
                for update in updates:
                    self.offset = update["update_id"] + 1
                    callback_query = update.get("callback_query") or {}
                    if callback_query:
                        self.handle_callback(callback_query)
                        continue

                    message = update.get("message") or {}
                    text = message.get("text")
                    chat = message.get("chat") or {}
                    from_user = message.get("from") or {}
                    print(
                        f"update update_id={update.get('update_id')} chat_id={chat.get('id')} chat_type={chat.get('type')} text={repr(text)[:240]}",
                        flush=True,
                    )
                    if not text:
                        continue
                    self.handle_text(
                        chat.get("id"),
                        message.get("message_id"),
                        from_user.get("id"),
                        chat.get("type") or "",
                        text,
                    )
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
