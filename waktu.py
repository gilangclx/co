import time
import speedtest
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Fungsi untuk cek waktu server
async def check_time(update: Update, context: CallbackContext):
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    await update.message.reply_text(f"Waktu saat ini di server: {current_time}")

# Fungsi untuk cek kecepatan internet
async def check_speed(update: Update, context: CallbackContext):
    st = speedtest.Speedtest()
    st.get_best_server()
    download_speed = st.download() / 1_000_000  # Convert to Mbps
    upload_speed = st.upload() / 1_000_000  # Convert to Mbps
    ping = st.results.ping

    await update.message.reply_text(f"Kecepatan Download: {download_speed:.2f} Mbps\n"
                                    f"Kecepatan Upload: {upload_speed:.2f} Mbps\n"
                                    f"Ping: {ping} ms")

# Fungsi utama untuk bot
def main():
    # Masukkan token bot Anda di sini
    application = Application.builder().token("1729307559:AAEXU87g-UjoKRqSkNWodsXON2Z11XtU-XU").build()

    # Menambahkan handler untuk perintah /waktu dan /speed
    application.add_handler(CommandHandler("waktu", check_time))
    application.add_handler(CommandHandler("speed", check_speed))

    # Jalankan bot
    application.run_polling()

if __name__ == "__main__":
    main()
