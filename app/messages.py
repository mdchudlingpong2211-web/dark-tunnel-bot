"""User-facing text templates, kept separate from bot logic for easy editing."""

from __future__ import annotations

from app.config import CHANNEL_URL

FORCE_JOIN_START = (
    "╭──────────────────────────────╮\n"
    "│      ⚠️ ACCESS DENIED ⚠️     │\n"
    "├──────────────────────────────┤\n"
    "│ বোটটি ব্যবহার করতে হলে আপনাকে │\n"
    "│ অবশ্যই আমাদের চ্যানেলে জয়েন │\n"
    "│ করতে হবে।                    │\n"
    "├──────────────────────────────┤\n"
    "│ নিচের বাটনে ক্লিক করে জয়েন   │\n"
    "│ করুন এবং Check Join 🟢     │\n"
    "│ বাটনে চাপুন।                 │\n"
    "╰──────────────────────────────╯"
)

FORCE_JOIN_FILE = (
    "╭──────────────────────────────╮\n"
    "│    ❌ JOIN CHANNEL FIRST ❌  │\n"
    "├──────────────────────────────┤\n"
    "│ আমাদের চ্যানেলের মেম্বার না   │\n"
    "│ হলে ফাইল আনলক করা যাবে না।   │\n"
    "├──────────────────────────────┤\n"
    "│ দয়া করে নিচের চ্যানেল বাটনে  │\n"
    "│ ক্লিক করে জয়েন সম্পন্ন করুন। │\n"
    "╰──────────────────────────────╯"
)

WELCOME = (
    "╭──────────────────────────────╮\n"
    "│  👋 𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐓𝐎 𝐃𝐀𝐑𝐊 𝐓𝐔𝐍𝐍𝐄𝐋  │\n"
    "│   💎 𝐂𝐎𝐍𝐅𝐈𝐆 𝐃𝐄𝐂𝐑𝐘𝐏𝐓𝐎𝐑 𝐁𝐎𝐓 💎 │\n"
    "├──────────────────────────────┤\n"
    "│  ⚡ 𝐒𝐭𝐚𝐭𝐮𝐬    : Unlocking Active│\n"
    "│  🚀 𝐒𝐩𝐞𝐞𝐝    : Ultra Fast      │\n"
    "│  👨‍💻 𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫 : @Rahmatullah_1     │\n"
    "├──────────────────────────────┤\n"
    "│  📂 এখন যেকোনো `dark` কনফিগ │\n"
    "│  ফাইল পাঠান, মুহূর্তেই আনলক   │\n"
    "│  হয়ে যাবে।😁                   │\n"
    "╰──────────────────────────────╯"
)

JOIN_SUCCESS = (
    "╭──────────────────────────────╮\n"
    "│     ✅ JOINED SUCCESS 🎉     │\n"
    "├──────────────────────────────┤\n"
    "│ ধন্যবাদ আমাদের সাথে থাকার জন্য│\n"
    "│                              │\n"
    "│ এখন আপনার কাঙ্ক্ষিত `.dark`   │\n"
    "│ ফাইলটি বোটে সেন্ড করুন।       │\n"
    "╰──────────────────────────────╯"
)

JOIN_STILL_MISSING = "❌ আপনি এখনো জয়েন করেননি! দয়া করে জয়েন করুন।"
JOIN_CONFIRMED_ALERT = "Success! You have joined. 🎉"
PROCESSING_TEXT = "⚡ **Processing & Decrypting...**"
SENDING_TEXT = "📤 **Sending Unlocked File...**"
UNLOCK_DONE_CAPTION = "┠─━━ 🔓 UNLOCK DONE ━━─┨"
FILE_TOO_LARGE = "❌ **Error:** File is too large. Please send a smaller `.dark` export."
UNSUPPORTED_FILE = "⚠️ Please send a valid `.dark` config file."
GENERIC_ERROR = "❌ **Error:** {error}"

__all__ = [
    "CHANNEL_URL",
    "FORCE_JOIN_START",
    "FORCE_JOIN_FILE",
    "WELCOME",
    "JOIN_SUCCESS",
    "JOIN_STILL_MISSING",
    "JOIN_CONFIRMED_ALERT",
    "PROCESSING_TEXT",
    "SENDING_TEXT",
    "UNLOCK_DONE_CAPTION",
    "FILE_TOO_LARGE",
    "UNSUPPORTED_FILE",
    "GENERIC_ERROR",
]
