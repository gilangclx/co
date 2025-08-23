import asyncio
import httpx
import datetime
import multiprocessing
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

# Define conversation states
TIME_INPUT, PRODUCT_ID_INPUT, COOKIE_INPUT, FINALIZE_CHECKOUT = range(4)  # Mendefinisikan status percakapan

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
    "i": "2022070510803319006",
    "t": "2022110410804655577",
    "a": "2025041010812405682",
    "r": "2023062710806629654",
    "b": "2022061810802884853",
    "p": "2022061810802909623",
}

# Fungsi checkout untuk tiap task
def checkout_task(cookie, product_id, product_name, target_time_str, cookie_idx, success_counter):
    # Ini akan dijalankan di setiap proses paralel
    headers = headers_template.copy()
    full_cookie = f"{cookie}"
    headers["cookie"] = full_cookie

    # Update productId dalam payload
    updated_payload = payload.copy()
    updated_payload["requestData"] = updated_payload["requestData"].replace("2022061810802909623", product_id)

    async def process_checkout():
        async with httpx.AsyncClient(http2=True) as client:
            max_retry = 300  # Jumlah maksimal retry
            for retry in range(max_retry):
                try:
                    response = await client.post(url, headers=headers, data=updated_payload)
                    res_json = response.json()

                    # Dapatkan waktu saat ini
                    current_time = datetime.datetime.now().strftime("%H:%M:%S")

                    # === Cek Berhasil ===
                    if res_json.get("result", {}).get("success") is True:
                        order_id = res_json.get("result", {}).get("orderId", "Tidak Ada Order ID")
                        success_counter[0] += 1  # Increment counter jika checkout berhasil
                        print(f"[{current_time}][{product_name}][{product_id}] [Cookie ke-{cookie_idx}] Berhasil checkout pada percobaan ke-{retry + 1}! ORDER ID: {order_id}")
                        break

                    # === Cek Produk habis atau limit pembelian ===
                    error_code = res_json.get("result", {}).get("errorCode")
                    if error_code in ["AE15115999000006", "AE15115999000011", "AE15115999000026"]:
                        error_msg = res_json["result"].get("errorMessage", "Tidak diketahui")
                        print(f"[{current_time}][{product_name}][{product_id}] [Cookie ke-{cookie_idx}] Gagal checkout pada percobaan ke-{retry + 1}! Error: {error_msg}")
                        break

                    # === Cek Login timeout ===
                    if res_json.get("resultStatus") == 2000 and res_json.get("memo") == "Login timeout!":
                        print(f"[{current_time}][{product_name}][{product_id}] [Cookie ke-{cookie_idx}] Login timeout pada percobaan ke-{retry + 1}! Harap login ulang.")
                        break

                except Exception as e:
                    print(f"[{current_time}][{product_name}][{product_id}] [Cookie ke-{cookie_idx}] Error saat mencoba checkout: {e}")

                # Tunggu beberapa detik sebelum mencoba lagi
                time.sleep(0)  # Tunggu 0 detik antar percakapan (bisa disesuaikan)

    # Tunggu hingga waktu checkout tercapai
    target_time = datetime.datetime.strptime(target_time_str, "%H:%M:%S").time()
    now = datetime.datetime.now().time()

    while now < target_time:
        now = datetime.datetime.now().time()  # Update current time
        time.sleep(0.1)  # Tunggu sampai waktu yang diinginkan

    asyncio.run(process_checkout())  # Jalankan proses checkout setelah waktu tercapai

# Fungsi untuk menjalankan semua task secara paralel
def process_all_checkout(cookies, product_ids, product_names, target_time_str):
    processes = []
    success_counter = [0]  # Counter untuk melacak jumlah checkout yang berhasil

    for idx, product_id in enumerate(product_ids):
        for cookie_idx, cookie in enumerate(cookies, 1):  # Mulai dari 1 untuk indeks cookie
            p = multiprocessing.Process(target=checkout_task, args=(cookie, product_id, product_names[idx], target_time_str, cookie_idx, success_counter))
            processes.append(p)
            p.start()

    for p in processes:
        p.join()  # Tunggu sampai semua proses selesai

    return success_counter[0]  # Kembalikan jumlah checkout yang berhasil

# Fungsi utama untuk bot
async def start_checkout(update: Update, context: CallbackContext):
    context.user_data.clear()
    await update.message.reply_text("Masukkan waktu checkout (format HHMMSS, misalnya 000000):")
    return TIME_INPUT

# Fungsi untuk menerima waktu input dari pengguna
async def time_input(update: Update, context: CallbackContext):
    target_time_raw = update.message.text.strip()

    # Validasi format waktu yang dimasukkan (HHMMSS)
    if len(target_time_raw) != 6 or not target_time_raw.isdigit():
        await update.message.reply_text("Format waktu salah! Harus dalam format HHMMSS, misalnya 091000.")
        return TIME_INPUT

    target_time_str = f"{target_time_raw[:2]}:{target_time_raw[2:4]}:{target_time_raw[4:]}"
    context.user_data["target_time"] = target_time_str
    await update.message.reply_text(f"Pilih productId yang ingin digunakan:")
    return PRODUCT_ID_INPUT

# Fungsi untuk menampilkan pilihan produk dengan nama produk
async def product_id_input(update: Update, context: CallbackContext):
    product_name = update.message.text.strip()

    # Validasi nama produk
    if product_name not in PRODUCT_IDS:
        await update.message.reply_text(f"Nama produk tidak valid. Pilih salah satu dari berikut:\n{', '.join(PRODUCT_IDS.keys())}")
        return PRODUCT_ID_INPUT

    product_id = PRODUCT_IDS[product_name]

    if "products" not in context.user_data:
        context.user_data["products"] = []

    context.user_data["products"].append(product_id)
    await update.message.reply_text(f"Product {product_name} dengan ID {product_id} telah ditambahkan. Sekarang, masukkan cookies untuk produk ini (pisahkan dengan baris baru):")
    return COOKIE_INPUT

# Fungsi untuk menerima input cookies
async def cookie_input(update: Update, context: CallbackContext):
    cookies = update.message.text.strip().splitlines()

    if not cookies:
        await update.message.reply_text("Tidak ada cookie yang dimasukkan. Silakan coba lagi.")
        return COOKIE_INPUT

    context.user_data["cookies"] = cookies

    await update.message.reply_text("Apakah Anda ingin menambah productId lain? (ketik 'y' atau 'n' untuk melanjutkan checkout)")
    return FINALIZE_CHECKOUT

# Fungsi untuk menyelesaikan proses checkout
async def finalize_checkout(update: Update, context: CallbackContext):
    if update.message.text.lower() == "n":
        cookies = context.user_data["cookies"]
        products = context.user_data["products"]
        product_names = [name for name in PRODUCT_IDS.keys()]

        # Jalankan semua task checkout secara paralel menggunakan multiprocessing
        success_count = process_all_checkout(cookies, products, product_names, context.user_data["target_time"])

        # Kirim pesan sukses dengan jumlah checkout yang berhasil
        await update.message.reply_text(f"Proses checkout selesai! Berhasil: {success_count} checkout(s)!")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Silakan masukkan productId lagi.")
        return PRODUCT_ID_INPUT

# Fungsi cancel untuk membatalkan proses
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Proses checkout dibatalkan.")
    return ConversationHandler.END

# Fungsi utama untuk bot
def main():
    application = Application.builder().token("1790912768:AAHQLfQ7KpTVpmPaNQydabNUgyub2GIONRI").build()

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_checkout)],
        states={
            TIME_INPUT: [MessageHandler(filters.TEXT, time_input)],
            PRODUCT_ID_INPUT: [MessageHandler(filters.TEXT, product_id_input)],
            COOKIE_INPUT: [MessageHandler(filters.TEXT, cookie_input)],
            FINALIZE_CHECKOUT: [MessageHandler(filters.TEXT, finalize_checkout)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],  # Menghapus perintah /close
    )

    application.add_handler(conversation_handler)
    application.run_polling()

if __name__ == "__main__":
    main()

