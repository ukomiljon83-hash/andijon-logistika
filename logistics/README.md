# Andijon Mini-Logistika (MVP)

## Tarkibi
- `main.py` — Telegram bot (aiogram) + API server (FastAPI), bitta jarayonda birga ishlaydi
- `database.py` — SQLite baza (avtomatik yaratiladi: `logistics.db`)
- `admin.html` — Admin panel (xarita + buyurtmalar + kuryerlar)
- `requirements.txt` — kerakli kutubxonalar

## O'rnatish

```bash
cd logistics
pip install -r requirements.txt
```

## Sozlash

`main.py` faylining boshida:

```python
BOT_TOKEN = "SIZNING_BOT_TOKENINGIZ"   # @BotFather dan oling: /newbot
ADMIN_CHAT_ID = 000000000              # o'z Telegram ID'ingiz (kuryer arizalari shu yerga keladi)
```

O'z Telegram ID'ingizni bilish uchun Telegramda **@userinfobot** ga yozing.

## Ishga tushirish

```bash
python main.py
```

Bu bir vaqtning o'zida:
- Telegram botni ishga tushiradi
- `http://127.0.0.1:8000/api/...` orqali API serverni ishga tushiradi

## Admin panelni ochish

`admin.html` faylini load qilish uchun oddiy `file://` orqali ochish ba'zi brauzerlarda CORS bilan muammo qilishi mumkin. Eng ishonchli yo'l — shu papkada mini server ishga tushirish:

```bash
python -m http.server 5500
```

Keyin brauzerda: `http://127.0.0.1:5500/admin.html`

**Muhim:** `main.py` (bot+API) alohida terminalda, `http.server` (admin.html uchun) boshqa terminalda — ikkalasi bir vaqtda ishlab turishi kerak.

## Ishlash oqimi (MVP)

1. Mijoz botga `/start` yozadi → "📦 Buyurtma berish" → manzil, tavsif, telefon
2. Barcha faol ("Bosh") kuryerlarga buyurtma yuboriladi, birinchi "✅ Men olaman" bosgan kuryer oladi
3. Kuryer Telegramda **Live Location** yuboradi (📎 → Location → Share Live Location) — bu joylashuv admin panel xaritasida ko'rinadi
4. Kuryer "Yo'lga chiqdim" va "Yetkazdim" tugmalarini bosib statusni yangilaydi
5. Yangi kuryer botga `/start` → "🚴 Kuryer bo'lish" orqali ariza qoldiradi, admin panelda "Tasdiqlash" bosilgach faol bo'ladi

## Keyingi bosqichlar (hozircha kiritilmagan)
- Online to'lov (Payme/Click) integratsiyasi
- Buyurtma narxini hisoblash (masofaga qarab)
- Kuryerlar reytingi, statistikasi
- SQLite o'rniga PostgreSQL (ko'p foydalanuvchi bo'lsa)
- Serverga (VPS) joylashtirish + HTTPS domen (127.0.0.1 o'rniga)

## Eslatma
Bu **MVP (minimal ishlaydigan versiya)** — g'oyangizni tekshirish uchun yetarli. Andijon shahrida haqiqiy foydalanuvchilar bilan sinab, keyin xarita masofasi bo'yicha narx hisoblash, to'lov, statistikani qo'shib boramiz.
