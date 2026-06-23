import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import httpx
from config import config  # ← ИСПРАВЛЕНО!

logging.basicConfig(level=logging.ERROR)

class EcoBot:
    def __init__(self):
        self.app = Application.builder().token(config.bot_token).build()
        self.api_url = "http://0.0.0.0:8080/api"
        self.user_states = {}
        self.setup_handlers()

    # ... остальной код как в разделённой версии, но с from config import config
    
    def run(self):
        print("Бот запущен!")
        self.app.run_polling(drop_pending_updates=True)
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("menu", self.menu_cmd))
        self.app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))

    async def call_api(self, endpoint: str, data: dict = None, files: dict = None):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if files:
                    response = await client.post(f"{self.api_url}/{endpoint}", files=files, data=data)
                elif data:
                    response = await client.post(f"{self.api_url}/{endpoint}", json=data)
                else:
                    response = await client.get(f"{self.api_url}/{endpoint}")
                if response.status_code != 200:
                    return {"status": "error", "message": f"API error: {response.status_code}"}
                return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        keyboard = [[InlineKeyboardButton("🚀 Начать", callback_data="start")]]
        reply = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"🌱 **Добро пожаловать, {user.first_name}!**\n\n"
            f"Я **EcoScan Bot** — ваш помощник в оценке углеродного следа покупок.\n\n"
            f"📸 Отправьте фото чека, и я:\n"
            f"• распознаю все продукты,\n"
            f"• рассчитаю общий CO₂-след,\n"
            f"• дам экосовет для снижения выбросов.\n\n"
            f"👇 **Нажмите «Начать», чтобы продолжить.**",
            reply_markup=reply,
            parse_mode='Markdown')

    async def main_menu(self, message, first_name: str):
        keyboard = [[InlineKeyboardButton("📸 Анализ чека", callback_data="scan_receipt")],
            [InlineKeyboardButton("ℹ️ О проекте", callback_data="about")],
            [InlineKeyboardButton("📧 Связь с разработчиками", callback_data="contact")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]]
        reply = InlineKeyboardMarkup(keyboard)
        await message.reply_text(f"🌱 **Привет, {first_name}!**\n\n"
            f"Я помогу вам оценить углеродный след ваших покупок.\n\n"
            f"📸 Отправьте фото чека — я найду продукты и рассчитаю их CO₂-след.\n\n"
            f"🔽 **Что хотите сделать?**",
            reply_markup=reply,
            parse_mode='Markdown')

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg_status = await update.message.reply_text("🔍 Анализирую чек...")
        try:
            photo = update.message.photo[-1]
            file = await photo.get_file()
            photo_bytes = await file.download_as_bytearray()
            photo_bytes = bytes(photo_bytes)

            if not photo_bytes:
                await msg_status.edit_text("😔 Не удалось загрузить фото. Попробуйте ещё раз.")
                return

            files = {'image': ('receipt.jpg', photo_bytes, 'image/jpeg')}
            data = {'user_id': str(update.effective_user.id)}
            result = await self.call_api("analyze_receipt", data=data, files=files)
            
            if result.get('status') == 'error':
                await msg_status.edit_text(f"😔 {result.get('message', 'Ошибка при анализе чека.')}")
                return

            analysis = result['data']
            response = "🌱 **ЭКОАНАЛИЗ** 🌱\n\n"
            response += f"🔍 **Найдено продуктов:** {len(analysis['products'])}\n\n"
            response += "📋 **Найденные продукты:**\n"
            for product in analysis['products']:
                response += f"• {product['receipt_name']}\n"
                response += f"  → {product['category']}: {product['co2']:.2f} кг CO₂/кг\n\n"

            if analysis['total_co2'] > 0:
                response += f"\n📌 **Для справки**\n"
                response += f"🚗 Если сложить выбросы CO₂ при производстве 1 кг каждого из найденных продуктов, получится столько же, сколько автомобиль выделяет за {analysis['total_co2'] * 4:.0f} км пути.\n"
                response += f"🌳 Столько CO₂ поглощает дерево за {analysis['total_co2'] / 20:.1f} мес."

            response += f"\n\n💡 **Экосовет дня**\n{analysis['eco_tip']}"

            await msg_status.edit_text(response, parse_mode='Markdown')

            keyboard = [
                [InlineKeyboardButton("📸 Анализировать ещё чек", callback_data="scan_receipt")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="to_menu")]
            ]
            reply = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("✨ **Что дальше?** ✨\n\nХотите проанализировать ещё один чек или вернуться в главное меню?",
                reply_markup=reply, parse_mode='Markdown')

        except Exception as e:
            print(f"Error handling photo: {e}")
            await msg_status.edit_text("😔 Ошибка при анализе чека. Попробуйте ещё раз.")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == "start":
            await self.main_menu(query.message, update.effective_user.first_name)
        elif query.data == "scan_receipt":
            keyboard = [[InlineKeyboardButton("🔙 Вернуться в меню", callback_data="to_menu")]]
            reply = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("📸 **Отправьте фото чека**\n\n"
                "Советы для лучшего распознавания\n"
                "• Фотографируйте при хорошем освещении\n"
                "• Держите камеру ровно\n"
                "• Чек должен занимать почти весь кадр\n\n"
                "После отправки фото бот проведёт анализ и покажет результат.",
                reply_markup=reply,
                parse_mode='Markdown')
        elif query.data == "about":
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="to_menu")]]
            reply = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("🌱 **О проекте EcoScan**\n\n"
                "Этот бот помогает оценить углеродный след продуктов из ваших чеков.\n\n"
                "📊 **Как это работает**\n"
                "• Бот распознаёт товары из чека с помощью OCR и ChatGPT\n"
                "• Сравнивает с базой данных углеродного следа продуктов\n"
                "• Показывает количество выбросов CO₂ из расчёта на 1 кг продукта\n"
                "• Даёт экосоветы для снижения воздействия на климат\n\n"
                "🌍 **Почему это важно**\n"
                "Производство продуктов питания отвечает за ~25 % мировых выбросов\n"
                "парниковых газов. Каждый осознанный выбор имеет значение!\n\n"
                "💚 **Наша миссия**\n"
                "Мы стараемся помочь каждому сделать экологичный выбор и снизить свой углеродный след.",
                reply_markup=reply,
                parse_mode='Markdown')
        elif query.data == "contact":
            keyboard = [[InlineKeyboardButton("📝 Написать разработчикам", callback_data="fb_start")], [InlineKeyboardButton("🔙 Главное меню", callback_data="to_menu")]]
            reply = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("📧 **Связь с разработчиками**\n\n"
                "Вы можете отправить нам сообщение прямо в боте!\n\n"
                "💬 **Что можно отправить:**\n"
                "• предложения по улучшению бота,\n"
                "• сообщения об ошибках,\n"
                "• скриншоты проблемных чеков,\n"
                "• общие вопросы.\n\n"
                "👇 Нажмите «Написать разработчикам», чтобы начать.",
                reply_markup=reply,
                parse_mode='Markdown')
        elif query.data == "fb_start":
            self.user_states[update.effective_user.id] = {"waiting_fb": True}
            keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="contact")]]
            reply = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("📝 **Написать разработчикам**\n\n"
                "Напишите ваше обращение в ответ на это сообщение.\n\n"
                "После отправки ваше сообщение будет доставлено разработчикам.\n\n"
                "✏️ **Напишите ваше сообщение**",
                reply_markup=reply,
                parse_mode='Markdown')
        elif query.data == "help":
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="to_menu")]]
            reply = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("❓ **Помощь**\n\n"
                "📸 **Как пользоваться**\n"
                "1. Нажмите «Анализ чека» в главном меню\n"
                "2. Отправьте фото чека\n"
                "3. Бот распознает товары и рассчитает углеродный след\n"
                "4. Получите экосовет\n\n"
                "🏪 **Поддерживаемые магазины**\n"
                "• Перекрёсток\n• Пятёрочка\n• Магнит\n• Лента\n• О'КЕЙ\n\n"
                "⚠️ **Возможные проблемы**\n"
                "• Плохое качество фото → распознавание может быть неточным\n"
                "• Не все продукты есть в базе данных (она пополняется)\n\n"
                "📊 **Оценка углеродного следа**\n"
                "• 1 кг CO₂ ≈ 4 км на автомобиле\n"
                "• 1 дерево поглощает ~20 кг CO₂ в год\n\n"
                "💡 **Экосовет дня**\n"
                "Даётся, если в чеке есть продукты с высоким CO₂ (>2 кг/кг).",
                reply_markup=reply,
                parse_mode='Markdown')
        elif query.data == "to_menu":
            await self.main_menu(query.message, update.effective_user.first_name)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if self.user_states.get(user_id, {}).get("waiting_fb"):
            user_name = update.effective_user.first_name
            username = update.effective_user.username or "нет username"
            user_text = update.message.text
            admin_chat_id = config.admin_chat_id

            message_for_admin = (f"📩 **Новое сообщение от пользователя!**\n\n"
                f"👤 **Имя:** {user_name}\n"
                f"🆔 **Username:** @{username}\n"
                f"🔢 **ID:** {user_id}\n"
                f"📝 **Сообщение:**\n{user_text}")

            try:
                if admin_chat_id:
                    await context.bot.send_message(chat_id=admin_chat_id, text=message_for_admin, parse_mode='Markdown')
                    await update.message.reply_text("✅ **Сообщение отправлено разработчикам!**\n\n"
                        "Спасибо за вашу обратную связь! Мы рассмотрим ваше сообщение в ближайшее время.\n\n"
                        "🔙 Вернуться в главное меню — нажмите /start",
                        parse_mode='Markdown')
                else:
                    await update.message.reply_text("❌ **Ошибка**\n\n"
                        "Не найден ID администратора.\n\n"
                        "🔙 /start",
                        parse_mode='Markdown')
            except Exception as e:
                print(f"Ошибка отправки: {e}")
                await update.message.reply_text("❌ **Ошибка отправки**\n\n"
                    "Не удалось отправить сообщение. Пожалуйста, попробуйте позже.\n\n"
                    "🔙 /start",
                    parse_mode='Markdown')
            self.user_states.pop(user_id, None)
        else:
            await self.start(update, context)

    async def menu_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.main_menu(update.message, update.effective_user.first_name)

    def run(self):
        print("Бот запущен!")
        self.app.run_polling(drop_pending_updates=True)