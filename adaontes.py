import asyncio
import httpx
import datetime
import multiprocessing
import time
from telegram import Update, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

# Mendefinisikan status percakapan
TIME_INPUT, PRODUCT_ID_INPUT, COOKIE_INPUT, FINALIZE_CHECKOUT = range(4)

# ID pemilik bot (ganti dengan ID pemilik bot yang sesuai)
BOT_OWNER_ID = 824218598  # Ganti dengan ID pemilik bot yang sesuai

# URL dan template header untuk request
url = "https://imgs-ac.alipay.com/imgw.htm"

headers_template = {
    "Host": "imgs-ac.alipay.com",
    "appid": "DANA_WALLET_ID",
    "appkey": "DANA_WALLET_ID_ANDROID",
    "accept-language": "in_ID",
    "workspaceid": "default",
    "content-type": "application/x-www-form-urlencoded; charset=utf-8",
    "accept-encoding": "gzip",
    "user-agent": "okhttp/3.12.12",
}

# Payload untuk API
payload = {
    "operationType": "ap.alipayplusrewards.eshop.order.place",
    "requestData": """[ 
        {
            "channel": "WALLET_DANA",
            "envInfo": {
                "appId": "",
                "appVersion": "2.81.0",
                "extendInfo": {
                    "channel": "WALLET_DANA",
                    "clientName": "dana"
                },
                "locale": "in_ID",
                "miniProgramVersion": "5.0.0",
                "osType": "Android",
                "osVersion": "11",
                "sdkVersion": "",
                "terminalType": "miniapp",
                "tokenId": ""
            },
            "extParams": {
                "chInfo": "aplusrewards",
                "clientCode": "REWARDS",
                "extAudienceId": ""
            },
            "orderStockIds": [
                {
                    "budgetId": "2022061810800462248",
                    "budgetType": "PRODUCT_STOCK"
                }
            ],
            "payPoint": 0,
            "paymentMethodList": [
                "WALLET"
            ],
            "paymentType": "ONE_TIME",
            "productId": "2022061810802909623",
            "quantity": 1,
            "saleAmount": {
                "amount": 500.00,
                "cent": 50000,
                "centFactor": 100,
                "currency": "IDR",
                "currencyCode": "IDR",
                "currencyValue": "360"
            },
             "source": "Dana_HomeGridBanner#a1702.b34738.c89032.d183824#aac.bflash_sales_page.cFlashSales_Page.FlashSales_Area.PrizeInfo#ac-flash-rewards-v2#3#202504241900000000994108002900043323"
        }
    ]"""
}

# Opsi productId yang tersedia
PRODUCT_IDS = {
    "kasd": "202207051080331x9006",
    "mkcs": "202211041080465x5577",
    "lkso": "202504101081240x5682",
    "njd": "2023062710806629x654",
    "tes2": "2022061810802884x853",
    "tes": "2022061810802909623",
}

# Dictionary untuk melacak status produk (aktif atau tidak)
product_status = {
    "kasd": False,
    "mkcs": False,
    "lkso": False,
    "njd": False,
    "tes2": False,
    "tes": False,
}

# Fungsi untuk memeriksa apakah bot admin di grup
async def is_bot_admin(update: Update, context: CallbackContext) -> bool:
    chat_id = update.message.chat.id
    bot_user_id = context.bot.id
    
    # Mendapatkan status chat member untuk bot di grup
    chat_member = await context.bot.get_chat_member(chat_id, bot_user_id)
    
    # Memeriksa apakah bot adalah admin
    return chat_member.status in [ChatMember.ADMINISTRATOR, 'creator']  # Menggunakan string 'creator' untuk menggantikan ChatMember.CREATOR

# Fungsi untuk memeriksa apakah pesan berasal dari chat pribadi dan bot owner
async def is_owner(update: Update) -> bool:
    # Periksa apakah chat berasal dari chat pribadi dan apakah pengguna adalah pemilik bot
    return update.message.chat.type == "private" and update.message.from_user.id == BOT_OWNER_ID

# Fungsi untuk memproses checkout untuk setiap tugas secara paralel
def process_all_checkout(cookies, product_ids, product_names, target_time_str):
    processes = []
    success_counter = [0]  # Counter untuk melacak jumlah checkout yang berhasil

    for idx, product_id in enumerate(product_ids):
        # Lewati produk yang tidak aktif
        if not product_status.get(product_names[idx], False):
            continue
        
        for cookie_idx, cookie in enumerate(cookies, 1):  # Mulai dari 1 untuk indeks cookie
            p = multiprocessing.Process(target=checkout_task, args=(cookie, product_id, product_names[idx], target_time_str, cookie_idx, success_counter))
            processes.append(p)
            p.start()

    for p in processes:
        p.join()  # Tunggu hingga semua proses selesai

    return success_counter[0]  # Kembalikan jumlah checkout yang berhasil

# Fungsi checkout untuk tiap tugas
def checkout_task(cookie, product_id, product_name, target_time_str, cookie_idx, success_counter):
    headers = headers_template.copy()
    full_cookie = f"{cookie}"
    headers["cookie"] = full_cookie

    # Update productId dalam payload
    updated_payload = payload.copy()
    updated_payload["requestData"] = updated_payload["requestData"].replace("2022061810802909623", product_id)

    async def process_checkout():
        async with httpx.AsyncClient(http2=True) as client:
            max_retry = 100  # Jumlah maksimal retry
            for retry in range(max_retry):
                try:
                    response = await client.post(url, headers=headers, data=updated_payload)
                    res_json = response.json()

                    # Dapatkan waktu saat ini
                    current_time = datetime.datetime.now().strftime("%H:%M:%S")

                    # === Cek Berhasil ===
                    if res_json.get("result", {}).get("success") is True:
                        order_id = res_json.get("result", {}).get("orderId", "Tidak Ada Order ID")
                        success_counter[0] += 1
                        print(f"[{current_time}][{product_name}][{product_id}] [Cookie ke-{cookie_idx}] Berhasil checkout pada percakapan ke-{retry + 1}! ORDER ID: {order_id}")
                        break

                    # === Cek Produk habis atau limit pembelian ===
                    error_code = res_json.get("result", {}).get("errorCode")
                    if error_code in ["AE15115999000006", "AE15115999000011", "AE15115999000026"]:
                        error_msg = res_json["result"].get("errorMessage", "Tidak diketahui")
                        print(f"[{current_time}][{product_name}][{product_id}] [Cookie ke-{cookie_idx}] Produk habis terjual atau limit tercapai pada percakapan ke-{retry + 1}! Error: {error_msg}")
                        break

                    # === Cek Login timeout ===
                    if res_json.get("resultStatus") == 2000 and res_json.get("memo") == "Login timeout!":
                        print(f"[{current_time}][{product_name}][{product_id}] [Cookie ke-{cookie_idx}] Login timeout pada percakapan ke-{retry + 1}! Harap login ulang.")
                        break

                except Exception as e:
                    print(f"[{current_time}][{product_name}][{product_id}] [Cookie ke-{cookie_idx}] Error saat checkout: {e}")

                time.sleep(0)

    # Tunggu hingga waktu checkout tercapai
    target_time = datetime.datetime.strptime(target_time_str, "%H:%M:%S").time()
    now = datetime.datetime.now().time()

    while now < target_time:
        now = datetime.datetime.now().time()  # Update current time
        time.sleep(0.1)  # Tunggu sampai waktu yang diinginkan

    asyncio.run(process_checkout())  # Jalankan proses checkout setelah waktu tercapai

# Fungsi untuk mengaktifkan produk
async def on_product(update: Update, context: CallbackContext):
    if not await is_owner(update):
        await update.message.reply_text("Anda tidak diizinkan untuk menggunakan perintah ini.")
        return

    product_name = update.message.text.strip().split()[1]
    
    if product_name in PRODUCT_IDS:
        product_status[product_name] = True  # Set produk sebagai aktif
        await update.message.reply_text(f"Produk {product_name} telah diaktifkan.")
    else:
        await update.message.reply_text(f"Produk {product_name} tidak ditemukan.")

# Fungsi untuk menonaktifkan produk
async def off_product(update: Update, context: CallbackContext):
    if not await is_owner(update):
        await update.message.reply_text("Anda tidak diizinkan untuk menggunakan perintah ini.")
        return

    product_name = update.message.text.strip().split()[1]
    
    if product_name in PRODUCT_IDS:
        product_status[product_name] = False  # Set produk sebagai tidak aktif
        await update.message.reply_text(f"Produk {product_name} telah dinonaktifkan.")
    else:
        await update.message.reply_text(f"Produk {product_name} tidak ditemukan.")

# Fungsi untuk memeriksa status produk
async def status_product(update: Update, context: CallbackContext):
    if not await is_owner(update):
        await update.message.reply_text("Anda tidak diizinkan untuk menggunakan perintah ini.")
        return

    if len(update.message.text.split()) < 2:
        await update.message.reply_text("Silakan berikan nama produk (misalnya, /status tes).")
        return

    product_name = update.message.text.strip().split()[1]  # Ambil nama produk setelah perintah (/status)
    
    if product_name in PRODUCT_IDS:
        status = "aktif" if product_status[product_name] else "tidak aktif"
        await update.message.reply_text(f"Produk {product_name} saat ini {status}.")
    else:
        await update.message.reply_text(f"Produk {product_name} tidak ditemukan.")

# Fungsi utama untuk bot
async def start_checkout(update: Update, context: CallbackContext):
    if not await is_bot_admin(update, context):
        await update.message.reply_text("Hi! 👋")
        return ConversationHandler.END

    context.user_data.clear()
    await update.message.reply_text("Masukkan waktu checkout ⏰ (format HHMMSS, misalnya 000000):")
    return TIME_INPUT

# Fungsi untuk menerima waktu input dari pengguna
async def time_input(update: Update, context: CallbackContext):
    target_time_raw = update.message.text.strip()

    if len(target_time_raw) != 6 or not target_time_raw.isdigit():
        await update.message.reply_text("Format waktu salah! Harus dalam format HHMMSS, misalnya 091000.")
        return TIME_INPUT

    target_time_str = f"{target_time_raw[:2]}:{target_time_raw[2:4]}:{target_time_raw[4:]}"
    context.user_data["target_time"] = target_time_str
    await update.message.reply_text(f"Pilih productId yang ingin digunakan 🛍️:")
    return PRODUCT_ID_INPUT

# Fungsi untuk menampilkan pilihan produk dengan nama produk
async def product_id_input(update: Update, context: CallbackContext):
    product_name = update.message.text.strip()

    if product_name not in PRODUCT_IDS:
        await update.message.reply_text(f"Masukkan productId yang valid! ❌")
        return PRODUCT_ID_INPUT

    if not product_status.get(product_name, False):
        await update.message.reply_text(f"Produk {product_name} sudah dinonaktifkan dan tidak dapat dicekout.")
        return PRODUCT_ID_INPUT

    product_id = PRODUCT_IDS[product_name]

    if "products" not in context.user_data:
        context.user_data["products"] = []

    context.user_data["products"].append(product_id)
    await update.message.reply_text(f"Produk {product_name} telah ditambahkan ✅. Sekarang, masukkan cookie untuk produk ini 🍪:")
    return COOKIE_INPUT

# Fungsi untuk menerima input cookies
async def cookie_input(update: Update, context: CallbackContext):
    cookies = update.message.text.strip().splitlines()

    if not cookies:
        await update.message.reply_text("Tidak ada cookie yang dimasukkan ❌. Silakan coba lagi.")
        return COOKIE_INPUT

    context.user_data["cookies"] = cookies
    await update.message.reply_text("Cookies diterima ✅. Ketik 'n' untuk melanjutkan ke checkout 🛒.")
    return FINALIZE_CHECKOUT

# Fungsi untuk menyelesaikan proses checkout
async def finalize_checkout(update: Update, context: CallbackContext):
    if update.message.text.lower() == "n":
        cookies = context.user_data["cookies"]
        products = context.user_data["products"]
        product_names = [name for name in PRODUCT_IDS.keys()]

        success_count = process_all_checkout(cookies, products, product_names, context.user_data["target_time"])

        if success_count > 0:
            await update.message.reply_text(f"Proses checkout selesai! 🎉 Checkout berhasil! 🛍️")
        else:
            await update.message.reply_text(f"Proses checkout selesai! 😞 Tidak ada checkout yang berhasil.")

        return ConversationHandler.END
    else:
        await update.message.reply_text("Silakan masukkan productId lagi.")
        return PRODUCT_ID_INPUT

# Fungsi cancel untuk membatalkan proses
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Proses checkout dibatalkan ❌.")
    return ConversationHandler.END

# Fungsi utama untuk bot
def main():
    application = Application.builder().token("6386501863:AAEJPhF1DZZGDZofBHxBdkSdmPDQQmhdrsc").build()

    # Command handlers untuk mengaktifkan dan menonaktifkan produk
    application.add_handler(CommandHandler("on", on_product))
    application.add_handler(CommandHandler("off", off_product))
    application.add_handler(CommandHandler("status", status_product))

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_checkout)],
        states={
            TIME_INPUT: [MessageHandler(filters.TEXT, time_input)],
            PRODUCT_ID_INPUT: [MessageHandler(filters.TEXT, product_id_input)],
            COOKIE_INPUT: [MessageHandler(filters.TEXT, cookie_input)],
            FINALIZE_CHECKOUT: [MessageHandler(filters.TEXT, finalize_checkout)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conversation_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
