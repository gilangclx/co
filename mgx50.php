<?php
// Fungsi untuk memperpendek URL menggunakan PieceURL
function shorten_url_pieceurl($long_url, $length = 6) {
    $api_url = "http://pieceurl.com/generate.php";
    $payload = http_build_query([
        'link' => $long_url,
        'length' => $length
    ]);

    $options = [
        'http' => [
            'header'  => "Content-Type: application/x-www-form-urlencoded\r\n",
            'method'  => 'POST',
            'content' => $payload,
        ]
    ];

    $context  = stream_context_create($options);
    $result = file_get_contents($api_url, false, $context);

    if ($result !== FALSE) {
        // Asumsikan responsnya adalah URL pendek dalam format HTML
        $dom = new DOMDocument;
        @$dom->loadHTML($result);
        $tds = $dom->getElementsByTagName('td');
        
        if ($tds->length > 1) {
            $short_url = $tds->item(1)->nodeValue;
            $short_url = str_replace("http://", "", $short_url); // Menghapus "http://"
            return $short_url;
        }
    }

    echo "Gagal memendekkan URL.\n";
    return null;
}

// Fungsi untuk menyimpan URL ke file dengan jeda baris setiap 100 URL
function save_url_to_file($short_url, $file_path, $counter) {
    $file = fopen($file_path, "a");
    fwrite($file, $short_url . "\n");
    $counter++;

    if ($counter % 100 == 0) {
        fwrite($file, "\n");
    }

    fclose($file);
    return $counter;
}

// Fungsi untuk menyimpan trx_id ke file
function save_trx_id_to_file($trx_id, $trx_id_file_path) {
    $file = fopen($trx_id_file_path, "a");
    fwrite($file, $trx_id . "\n");
    fclose($file);
}

// Path file untuk menyimpan URL dan trx_id
$file_path = "C:/bot/botlink/mgx50.txt";
$trx_id_file_path = "C:/bot/botlink/trxid.txt";

$url_counter = 0;
$topup_count = readline("Masukkan berapa kali ingin melakukan top-up: ");
$url_top_up = "https://upoint.id/top-up/megaxus";
$url_purchase_trx = "https://upoint.id/api/purchase-trx";
$url_purchase_co = "https://upoint.id/api/purchase-co";

for ($i = 0; $i < $topup_count; $i++) {
    echo "\nTop-up ke-" . ($i + 1) . " dimulai...\n";

    $response = file_get_contents($url_top_up);

    if ($response !== FALSE) {
        $trx_id = uniqid();
        $product_id = 22;
        $payment_method = 7;
        $mobile_number = "087705442663";
        $email = "faisalgilang68@gmail.com";
        $role_eva = "YOUR_ROLE_EVA";

        $data_trx = [
            "trx_id" => $trx_id,
            "product_id" => $product_id,
            "payment_method" => $payment_method,
            "mobile_number" => $mobile_number,
            "email" => $email,
            "role_eva" => $role_eva
        ];

        $options_trx = [
            'http' => [
                'header'  => "Content-Type: application/json\r\n",
                'method'  => 'POST',
                'content' => json_encode($data_trx),
            ]
        ];
        $context_trx = stream_context_create($options_trx);
        $post_response_trx = file_get_contents($url_purchase_trx, false, $context_trx);

        if ($post_response_trx !== FALSE) {
            save_trx_id_to_file($trx_id, $trx_id_file_path); // Menyimpan trx_id ke file
            
            $purchase_co_data = [
                "trx_id" => $trx_id,
                "product_id" => $product_id,
                "payment_method" => $payment_method,
                "mobile_number" => $mobile_number,
                "email" => $email,
                "role_eva" => $role_eva
            ];

            $options_co = [
                'http' => [
                    'header'  => "Content-Type: application/json\r\n",
                    'method'  => 'POST',
                    'content' => json_encode($purchase_co_data),
                ]
            ];
            $context_co = stream_context_create($options_co);
            $post_response_co = file_get_contents($url_purchase_co, false, $context_co);

            if ($post_response_co !== FALSE) {
                $response_co_data = json_decode($post_response_co, true);
                echo "trx_id dari hasil purchase-trx: $trx_id\n";

                $redirect_url = $response_co_data['responseCo']['callback']['redirect_url'];
                $short_url = shorten_url_pieceurl($redirect_url);  // Menggunakan fungsi PieceURL
                if ($short_url) {
                    echo "URL DANA Shortened: $short_url\n";  // Hanya menampilkan short URL
                    $url_counter = save_url_to_file($short_url, $file_path, $url_counter);
                } else {
                    echo "Gagal memperpendek URL DANA.\n";
                }
            } else {
                echo "Gagal melakukan POST ke purchase-co.\n";
            }
        } else {
            echo "Gagal melakukan POST ke purchase-trx.\n";
        }
    } else {
        echo "Gagal mengakses halaman top-up.\n";
    }

    echo "Top-up ke-" . ($i + 1) . " selesai.\n";
}

echo "Proses top-up selesai.\n";
?>
