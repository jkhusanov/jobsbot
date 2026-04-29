"""All user-visible strings (Uzbek, Latin script).

Centralised so a future translation pass is a single-file diff.
"""

WELCOME = (
    "Assalomu alaykum!\n\n"
    "Bu bot orqali siz ochiq vakansiyalarni ko'rishingiz va ularga ariza "
    "topshirishingiz mumkin."
)

HELP = (
    "Buyruqlar:\n"
    "/start — Botni boshidan ishga tushirish\n"
    "/help — Yordam\n"
    "/cancel — Joriy amalni bekor qilish"
)

# Buttons
BTN_VIEW_JOBS = "📋 Vakansiyalarni ko'rish"
BTN_APPLY = "📨 Ariza yuborish"
BTN_BACK = "⬅️ Orqaga"
BTN_PREV = "⬅️ Oldingi"
BTN_NEXT = "Keyingi ➡️"
BTN_SHARE_PHONE = "📱 Raqamni yuborish"
BTN_CANCEL = "❌ Bekor qilish"
BTN_CONFIRM = "✅ Tasdiqlash"

# Jobs list
NO_JOBS = "Hozircha vakansiyalar yo'q."
JOBS_FETCH_ERROR = (
    "Vakansiyalarni yuklashda xatolik. Birozdan so'ng qayta urinib ko'ring."
)
JOB_CARD = "<b>{title}</b>\n{meta}\n\n{description}"
JOBS_PAGE_INDICATOR = "Sahifa {page} / {total}"

# Apply flow
ASK_NAME = "Ismingiz va familiyangizni yozing:"
ASK_PHONE = (
    "Telefon raqamingizni yuboring. Quyidagi tugmadan foydalanishingiz "
    "yoki o'zingiz yozishingiz mumkin (masalan: +998901234567)."
)
PHONE_ACCEPTED = "Telefon raqami qabul qilindi."
ASK_EMAIL = "Email manzilingizni yozing (masalan: ism@example.com):"
ASK_CV = "CV faylingizni yuboring (PDF, DOC yoki DOCX, {max_mb}MB gacha)."
ASK_CONFIRM = "Ma'lumotlaringiz to'g'rimi?"

CONFIRMATION_SUMMARY = (
    "<b>Vakansiya:</b> {job_title}\n"
    "<b>Ism:</b> {name}\n"
    "<b>Telefon:</b> {phone}\n"
    "<b>Email:</b> {email}\n"
    "<b>CV:</b> {cv_name}"
)

# Validation errors
INVALID_NAME = "Ism noto'g'ri. Iltimos, ism va familiyangizni qayta yozing."
INVALID_PHONE = (
    "Telefon raqami noto'g'ri. Iltimos, O'zbekiston raqamini kiriting "
    "(masalan: +998901234567)."
)
INVALID_EMAIL = "Email manzili noto'g'ri. Iltimos, qayta kiriting."
INVALID_CV_TYPE = "Fayl formati noto'g'ri. Faqat PDF, DOC yoki DOCX qabul qilinadi."
INVALID_CV_SIZE = "Fayl hajmi {max_mb}MB dan oshmasligi kerak."
NEED_DOCUMENT = "Iltimos, CV ni fayl ko'rinishida yuboring (PDF/DOC/DOCX)."

# Outcomes
CANCELLED = "Ariza bekor qilindi."
APPLICATION_RECEIVED = "Arizangiz qabul qilindi. Tez orada siz bilan bog'lanamiz."
RATE_LIMITED = "Bu vakansiya bo'yicha kunlik ariza yuborish chegarasiga yetdingiz."
JOB_NOT_AVAILABLE = (
    "Bu vakansiya endi mavjud emas. Iltimos, boshqa vakansiyalarni ko'ring."
)
SHARED_CONTACT_REJECTED = (
    "Iltimos, faqat o'zingizning telefon raqamingizni yuboring."
)

# Admin-side messages (HTML)
ADMIN_NEW_APPLICATION = (
    "🆕 <b>Yangi ariza</b>\n\n"
    "<b>Vakansiya:</b> {job_title} ({job_id})\n"
    "<b>Ism:</b> {name}\n"
    "<b>Telefon:</b> {phone}\n"
    "<b>Email:</b> {email}\n"
    "<b>Telegram:</b> {tg_link} (id: {tg_user_id})\n"
    "<b>Vaqt:</b> {created_at} UTC"
)
ADMIN_CV_CAPTION = "{name} — {job_id}"

# Internal log line — English; for ops, not users.
LOG_BOOTSTRAP = "[BOOTSTRAP] Received /start from chat_id={chat_id} username={username}"
