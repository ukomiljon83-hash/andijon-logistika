import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database import init_db, get_conn

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "SIZNING_BOT_TOKENINGIZ"      # @BotFather dan oling
ADMIN_CHAT_ID = 000000000                 # o'zingizning Telegram user_id (kuryer arizalari shu yerga keladi)
# ======================================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)


class OrderForm(StatesGroup):
    dropoff = State()
    comment = State()
    phone = State()


class CourierForm(StatesGroup):
    name = State()
    phone = State()


# ---------- /start ----------
@router.message(CommandStart())
async def start_handler(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📦 Buyurtma berish")],
        [KeyboardButton(text="🚴 Kuryer bo'lish")]
    ], resize_keyboard=True)
    await message.answer(
        "Assalomu alaykum! Andijon shahri bo'ylab yetkazib berish xizmatiga xush kelibsiz.",
        reply_markup=kb
    )


# ---------- Mijoz: buyurtma berish oqimi ----------
@router.message(F.text == "📦 Buyurtma berish")
async def order_start(message: Message, state: FSMContext):
    await state.set_state(OrderForm.dropoff)
    await message.answer("Qayerga yetkazib berish kerak? Manzilni yozing:", reply_markup=ReplyKeyboardRemove())


@router.message(OrderForm.dropoff, ~F.text.in_({"📦 Buyurtma berish", "🚴 Kuryer bo'lish"}))
async def order_dropoff(message: Message, state: FSMContext):
    await state.update_data(dropoff=message.text)
    await state.set_state(OrderForm.comment)
    await message.answer("Nima olib borish kerak? Qisqacha yozing:")


@router.message(OrderForm.comment, ~F.text.in_({"📦 Buyurtma berish", "🚴 Kuryer bo'lish"}))
async def order_comment(message: Message, state: FSMContext):
    await state.update_data(comment=message.text)
    await state.set_state(OrderForm.phone)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer("Telefon raqamingizni yuboring:", reply_markup=kb)


@router.message(OrderForm.phone, F.contact)
async def order_phone(message: Message, state: FSMContext):
    data = await state.update_data(phone=message.contact.phone_number)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO orders (client_id, client_name, phone, dropoff_address, comment, status) "
            "VALUES (?, ?, ?, ?, ?, 'Yangi')",
            (message.from_user.id, message.from_user.full_name, data["phone"], data["dropoff"], data["comment"])
        )
        conn.commit()
        order_id = cur.lastrowid

    await message.answer("✅ Buyurtmangiz qabul qilindi! Tez orada kuryer biriktiriladi.",
                          reply_markup=ReplyKeyboardRemove())
    await state.clear()
    await notify_couriers(order_id)


async def notify_couriers(order_id: int):
    with get_conn() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        couriers = conn.execute("SELECT * FROM couriers WHERE active=1 AND status='Bosh'").fetchall()

    text = (f"🆕 Yangi buyurtma #{order_id}\n"
            f"📍 Manzil: {order['dropoff_address']}\n"
            f"📦 Tavsif: {order['comment']}\n"
            f"📞 Tel: {order['phone']}")
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Men olaman", callback_data=f"take_{order_id}")
    ]])
    for c in couriers:
        try:
            await bot.send_message(c["id"], text, reply_markup=kb)
        except Exception as e:
            logging.warning(f"Kuryerga yuborib bo'lmadi: {e}")


@router.callback_query(F.data.startswith("take_"))
async def take_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    with get_conn() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if order["status"] != "Yangi":
            await callback.answer("Bu buyurtma allaqachon olingan.", show_alert=True)
            return
        conn.execute("UPDATE orders SET status='Biriktirildi', courier_id=? WHERE id=?",
                     (callback.from_user.id, order_id))
        conn.execute("UPDATE couriers SET status='Band' WHERE id=?", (callback.from_user.id,))
        conn.commit()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚚 Yo'lga chiqdim", callback_data=f"onway_{order_id}")],
        [InlineKeyboardButton(text="✅ Yetkazdim", callback_data=f"delivered_{order_id}")]
    ])
    await callback.message.edit_text(callback.message.text + "\n\n✅ Siz oldingiz.")
    await callback.message.answer(
        "Buyurtma sizga biriktirildi.\n"
        "📍 Iltimos, Telegramda 'Location' -> 'Share Live Location' orqali "
        "jonli lokatsiyangizni yuboring, shunda admin panelda xaritada ko'rinasiz.",
        reply_markup=kb
    )
    await bot.send_message(order["client_id"], f"Buyurtmangiz #{order_id} kuryerga biriktirildi 🚴")


@router.callback_query(F.data.startswith("onway_"))
async def order_onway(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    with get_conn() as conn:
        conn.execute("UPDATE orders SET status='Yolda' WHERE id=?", (order_id,))
        conn.commit()
    await callback.answer("Status: Yo'lda ✅")


@router.callback_query(F.data.startswith("delivered_"))
async def order_delivered(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    with get_conn() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        conn.execute("UPDATE orders SET status='Yetkazildi' WHERE id=?", (order_id,))
        conn.execute("UPDATE couriers SET status='Bosh' WHERE id=?", (callback.from_user.id,))
        conn.commit()
    await callback.answer("Rahmat! Status: Yetkazildi ✅")
    await bot.send_message(order["client_id"],
                            f"Buyurtmangiz #{order_id} yetkazildi ✅ Xizmatimizdan foydalanganingiz uchun rahmat!")


# ---------- Kuryer ro'yxatdan o'tishi ----------
@router.message(F.text == "🚴 Kuryer bo'lish")
async def courier_start(message: Message, state: FSMContext):
    await state.set_state(CourierForm.name)
    await message.answer("Ismingizni kiriting:", reply_markup=ReplyKeyboardRemove())


@router.message(CourierForm.name, ~F.text.in_({"📦 Buyurtma berish", "🚴 Kuryer bo'lish"}))
async def courier_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(CourierForm.phone)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer("Telefon raqamingizni yuboring:", reply_markup=kb)


@router.message(CourierForm.phone, F.contact)
async def courier_phone(message: Message, state: FSMContext):
    data = await state.update_data(phone=message.contact.phone_number)
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO couriers (id, name, phone, active, status) VALUES (?, ?, ?, 0, 'Offline')",
            (message.from_user.id, data["name"], data["phone"])
        )
        conn.commit()
    await message.answer("✅ Arizangiz qabul qilindi. Admin tasdiqlagach faol bo'lasiz.",
                          reply_markup=ReplyKeyboardRemove())
    if ADMIN_CHAT_ID:
        try:
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"🆕 Yangi kuryer arizasi: {data['name']} ({data['phone']}) — admin panelda tasdiqlang."
            )
        except Exception:
            pass
    await state.clear()


# ---------- Live lokatsiya ----------
@router.edited_message(F.location)
@router.message(F.location)
async def location_handler(message: Message):
    with get_conn() as conn:
        courier = conn.execute("SELECT * FROM couriers WHERE id=?", (message.from_user.id,)).fetchone()
        if courier:
            conn.execute(
                "UPDATE couriers SET lat=?, lon=?, updated_at=? WHERE id=?",
                (message.location.latitude, message.location.longitude,
                 datetime.now().isoformat(), message.from_user.id)
            )
            conn.commit()


# ==================== FastAPI (admin panel uchun) ====================
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/orders")
def api_orders():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
        return {"orders": [dict(r) for r in rows]}


@app.get("/api/couriers")
def api_couriers():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM couriers ORDER BY id DESC").fetchall()
        return {"couriers": [dict(r) for r in rows]}


@app.post("/api/couriers/{courier_id}/approve")
def approve_courier(courier_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE couriers SET active=1, status='Bosh' WHERE id=?", (courier_id,))
        conn.commit()
    return {"ok": True}


@app.post("/api/orders/{order_id}/assign/{courier_id}")
def assign_order(order_id: int, courier_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE orders SET status='Biriktirildi', courier_id=? WHERE id=?", (courier_id, order_id))
        conn.commit()
    return {"ok": True}


@app.delete("/api/orders/{order_id}")
def delete_order(order_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM orders WHERE id=?", (order_id,))
        conn.commit()
    return {"ok": True}


# ==================== Ishga tushirish ====================
async def main():
    init_db()
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    await asyncio.gather(
        dp.start_polling(bot),
        server.serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())
