const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
const { URLSearchParams } = require('url');

// Ganti 'YOUR_TELEGRAM_BOT_TOKEN' dengan token bot Anda
const token = '8079874285:AAGyx-XBx1r-jQ3lNpCdHoIhVqeaBpC_ZVY';
const bot = new TelegramBot(token, { polling: true });

// State percakapan pengguna
const userState = {};

// URL dan template header untuk request
const url = "https://imgs-ac.alipay.com/imgw.htm";
const headers_template = {
    "Host": "imgs-ac.alipay.com",
    "appid": "DANA_WALLET_ID",
    "appkey": "DANA_WALLET_ID_ANDROID",
    "accept-language": "in_ID",
    "workspaceid": "default",
    "content-type": "application/x-www-form-urlencoded; charset=utf-8",
    "accept-encoding": "gzip",
    "user-agent": "okhttp/3.12.12",
};

// Payload untuk API (perhatikan format JSON stringified)
const payload = {
    "operationType": "ap.alipayplusrewards.eshop.order.place",
    "requestData": "[ { \"channel\": \"WALLET_DANA\", \"envInfo\": { \"appId\": \"\", \"appVersion\": \"2.81.0\", \"extendInfo\": { \"channel\": \"WALLET_DANA\", \"clientName\": \"dana\" }, \"locale\": \"in_ID\", \"miniProgramVersion\": \"5.0.0\", \"osType\": \"Android\", \"osVersion\": \"11\", \"sdkVersion\": \"\", \"terminalType\": \"miniapp\", \"tokenId\": \"\" }, \"extParams\": { \"chInfo\": \"aplusrewards\", \"clientCode\": \"REWARDS\", \"extAudienceId\": \"\" }, \"orderStockIds\": [ { \"budgetId\": \"2022061810800462248\", \"budgetType\": \"PRODUCT_STOCK\" } ], \"payPoint\": 0, \"paymentMethodList\": [ \"WALLET\" ], \"paymentType\": \"ONE_TIME\", \"productId\": \"2023063010806699269\", \"quantity\": 1, \"saleAmount\": { \"amount\": 15000.00, \"cent\": 1500000, \"centFactor\": 100, \"currency\": \"IDR\", \"currencyCode\": \"IDR\", \"currencyValue\": \"360\" }, \"source\": \"Dana_HomeGridBanner#a1702.b34738.c89032.d183824#aac.bflash_sales_page.cFlashSales_Page.FlashSales_Area.PrizeInfo#ac-flash-rewards-v2#3#202504241900000000994108002900043323\" } ]",
};

// Opsi productId yang tersedia
const PRODUCT_IDS = {
    "r2": "2023063010806699269",
};

// Fungsi untuk proses checkout
async function checkout_task(cookie, product_id, product_name, cookie_idx, chatId) {
    const headers = { ...headers_template,
        cookie: cookie
    };
    const requestDataParsed = JSON.parse(payload.requestData);
    requestDataParsed[0].productId = product_id;
    const updatedPayload = {
        ...payload,
        requestData: JSON.stringify(requestDataParsed)
    };
    const params = new URLSearchParams(updatedPayload).toString();

    const max_retry = 300;
    for (let retry = 0; retry < max_retry; retry++) {
        try {
            const response = await axios.post(url, params, {
                headers
            });
            const res_json = response.data;
            const currentTime = new Date().toLocaleTimeString('id-ID');

            // Cek Berhasil - kirim ke bot dan konsol
            if (res_json.result && res_json.result.success) {
                const orderId = res_json.result.orderId || "Tidak Ada Order ID";
                const successMsg = `[${currentTime}][${product_name}][${product_id}] [Cookie ke-${cookie_idx}] Berhasil checkout pada percobaan ke-${retry + 1}! ORDER ID: ${orderId}`;
                console.log(successMsg);
                bot.sendMessage(chatId, successMsg);
                return true; // Berhasil
            }

            // GAGAL - Cek kode error spesifik dan hanya tampilkan di konsol
            const errorCode = res_json.result && res_json.result.errorCode;
            if (["AE15115999000006", "AE15115999000011", "AE15115999000026"].includes(errorCode)) {
                const errorMessage = res_json.result.errorMessage || "Tidak diketahui";
                const errorMsg = `[${currentTime}][${product_name}][${product_id}] [Cookie ke-${cookie_idx}] Checkout dihentikan! Error: ${errorMessage}`;
                console.log(errorMsg); // Hanya di konsol
                return false; // Kesalahan fatal
            }

            // Cek Login timeout - hanya tampilkan di konsol
            if (res_json.resultStatus === 2000 && res_json.memo === "Login timeout!") {
                const timeoutMsg = `[${currentTime}][${product_name}][${product_id}] [Cookie ke-${cookie_idx}] Login timeout pada percobaan ke-${retry + 1}! Harap login ulang.`;
                console.log(timeoutMsg); // Hanya di konsol
                return false; // Kesalahan fatal
            }
            
            // Gagal lainnya - hanya tampilkan di konsol
            const failMsg = `[${currentTime}][${product_name}][${product_id}] [Cookie ke-${cookie_idx}] Gagal: ${JSON.stringify(res_json)}`;
            console.log(failMsg);

        } catch (e) {
            // ERROR - hanya tampilkan di konsol
            const errorMsg = `[${currentTime}][${product_name}][${product_id}] [Cookie ke-${cookie_idx}] Error saat mencoba checkout: ${e.message}`;
            console.log(errorMsg);
        }

        if (retry < max_retry - 1) {
            console.log(`[Cookie ke-${cookie_idx}] Retry ${retry + 1}/${max_retry} | Gagal, mencoba lagi...`);
            await new Promise(resolve => setTimeout(resolve, 0));
        }
    }
    return false;
}

// Handler untuk command /start
bot.onText(/\/start/, (msg) => {
    const chatId = msg.chat.id;
    userState[chatId] = {
        step: 'time',
        products: [],
        cookies: []
    };
    bot.sendMessage(chatId, "Selamat datang! Masukkan waktu checkout (format HHMMSS, misalnya 000000):");
});

// Handler untuk command /cancel
bot.onText(/\/cancel/, (msg) => {
    const chatId = msg.chat.id;
    if (userState[chatId]) {
        delete userState[chatId];
        bot.sendMessage(chatId, "Proses checkout dibatalkan.");
    } else {
        bot.sendMessage(chatId, "Tidak ada proses yang sedang berjalan untuk dibatalkan.");
    }
});

// Handler untuk command /ubah
bot.onText(/\/ubah/, (msg) => {
    const chatId = msg.chat.id;
    userState[chatId] = {
        step: 'update_product_id',
    };
    bot.sendMessage(chatId, "Masukkan ID produk baru untuk 'r2':");
});

// Handler untuk pesan teks
bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text.trim();

    if (text.startsWith('/')) {
        return;
    }

    if (!userState[chatId]) {
        bot.sendMessage(chatId, "Silakan gunakan perintah /start untuk memulai atau /ubah untuk mengubah produk.");
        return;
    }

    const currentState = userState[chatId].step;

    switch (currentState) {
        case 'time':
            if (text.length !== 6 || !/^\d+$/.test(text)) {
                bot.sendMessage(chatId, "Format waktu salah! Harap masukkan dalam format HHMMSS, misalnya 091000.");
            } else {
                userState[chatId].target_time = text.match(/.{2}/g).join(':');
                const productList = Object.keys(PRODUCT_IDS).join(', ');
                bot.sendMessage(chatId, `Waktu target diatur ke ${userState[chatId].target_time}. Sekarang, masukkan nama produk yang ingin Anda pilih (${productList}):`);
                userState[chatId].step = 'product';
            }
            break;

        case 'product':
            if (PRODUCT_IDS[text.toLowerCase()]) {
                const productId = PRODUCT_IDS[text.toLowerCase()];
                const productName = text.toLowerCase();
                userState[chatId].products.push({
                    id: productId,
                    name: productName
                });
                bot.sendMessage(chatId, "Berhasil menambahkan produk. Sekarang, tempelkan atau ketik cookies (satu per baris). Ketika selesai, kirim 's'.");
                userState[chatId].step = 'cookie';
            } else {
                bot.sendMessage(chatId, "Nama produk tidak valid. Silakan coba lagi.");
            }
            break;

        case 'cookie':
            if (text.toLowerCase() === 'n') {
                if (userState[chatId].cookies.length === 0) {
                    bot.sendMessage(chatId, "Anda belum memasukkan cookie. Silakan coba lagi.");
                } else {
                    const cookies = userState[chatId].cookies;
                    const products = userState[chatId].products;
                    const targetTime = userState[chatId].target_time;

                    bot.sendMessage(chatId, `Memulai proses checkout untuk ${cookies.length} cookie dan ${products.length} produk. Mohon tunggu...`);

                    const [targetHour, targetMinute, targetSecond] = targetTime.split(':').map(Number);
                    const now = new Date();
                    const targetDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), targetHour, targetMinute, targetSecond, 0);
                    const timeUntilTarget = targetDate.getTime() - now.getTime();

                    if (timeUntilTarget > 0) {
                        bot.sendMessage(chatId, `Menunggu hingga waktu target: ${targetTime}...`);
                        await new Promise(resolve => setTimeout(resolve, timeUntilTarget));
                    }

                    const tasks = [];
                    for (const product of products) {
                        cookies.forEach((cookie, index) => {
                            tasks.push(checkout_task(cookie, product.id, product.name, index + 1, chatId));
                        });
                    }

                    const results = await Promise.all(tasks);
                    const successCount = results.filter(result => result).length;

                    bot.sendMessage(chatId, `Proses checkout selesai! Berhasil: ${successCount} checkout(s)!`);

                    delete userState[chatId];
                }
            } else {
                userState[chatId].cookies.push(...text.split('\n').filter(c => c.trim() !== ''));
                bot.sendMessage(chatId, `Berhasil menambahkan cookie. Ketik 'n' untuk melanjutkan.`);
            }
            break;

        case 'update_product_id':
            if (text && text.length > 0) {
                PRODUCT_IDS['r2'] = text;
                userState[chatId].step = 'update_amount_cent';
                bot.sendMessage(chatId, "ID produk 'r2' berhasil diubah. Sekarang masukkan nilai 'amount' dan 'cent' (misalnya: 15000 1500000):");
            } else {
                bot.sendMessage(chatId, "ID produk tidak valid. Silakan coba lagi.");
            }
            break;

        case 'update_amount_cent':
            const values = text.split(' ').map(Number);
            if (values.length === 2 && !isNaN(values[0]) && !isNaN(values[1])) {
                const [newAmount, newCent] = values;
                
                const requestDataParsed = JSON.parse(payload.requestData);
                requestDataParsed[0].saleAmount.amount = newAmount;
                requestDataParsed[0].saleAmount.cent = newCent;
                payload.requestData = JSON.stringify(requestDataParsed);
                
                bot.sendMessage(chatId, `Nilai 'amount' dan 'cent' berhasil diubah menjadi ${newAmount} dan ${newCent}. Silakan ketik /start untuk memulai checkout dengan data baru.`);
                delete userState[chatId];
            } else {
                bot.sendMessage(chatId, "Format tidak valid. Harap masukkan dua angka dipisahkan oleh spasi (misalnya: 15000 1500000).");
            }
            break;
    }
});

console.log('Bot sedang berjalan...');