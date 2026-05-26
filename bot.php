<?php

require 'vendor/autoload.php';

use Telegram\Bot\Api;

$TOKEN = "YOUR_BOT_TOKEN";
$ADMIN_ID = 123456789;

$bot = new Api($TOKEN);

// ================= MYSQL =================
$host = "localhost";
$user = "YOUR_DB_USER";
$pass = "YOUR_DB_PASSWORD";
$dbname = "bot_db";

$conn = new mysqli($host, $user, $pass, $dbname);

if ($conn->connect_error) {
    die("❌ DB Connection Failed");
}


// ================= STORAGE =================
$temp_access = [];
$sent_videos = [];
$current_folder = [];

$channel_folder = "DEFAULT";


// ================= CONFIG =================
function set_config($key, $value)
{
    global $conn;

    $stmt = $conn->prepare("
        INSERT INTO config (`key`, `value`)
        VALUES (?, ?)
        ON DUPLICATE KEY UPDATE value=VALUES(value)
    ");

    $stmt->bind_param("ss", $key, $value);
    $stmt->execute();
}

function get_config($key)
{
    global $conn;

    $stmt = $conn->prepare("
        SELECT value FROM config WHERE `key`=?
    ");

    $stmt->bind_param("s", $key);
    $stmt->execute();

    $result = $stmt->get_result();

    if ($row = $result->fetch_assoc()) {
        return $row['value'];
    }

    return null;
}


// ================= USERS =================
function add_premium($user_id)
{
    global $conn;

    $premium = 1;

    $stmt = $conn->prepare("
        INSERT INTO users (user_id, premium)
        VALUES (?, ?)
        ON DUPLICATE KEY UPDATE premium=1
    ");

    $stmt->bind_param("ii", $user_id, $premium);
    $stmt->execute();
}

function is_premium($user_id)
{
    global $conn;

    $stmt = $conn->prepare("
        SELECT premium FROM users WHERE user_id=?
    ");

    $stmt->bind_param("i", $user_id);
    $stmt->execute();

    $result = $stmt->get_result();

    if ($row = $result->fetch_assoc()) {
        return $row['premium'] == 1;
    }

    return false;
}


// ================= VIDEOS =================
function add_video($folder, $file_id)
{
    global $conn;

    $check = $conn->prepare("
        SELECT id FROM videos WHERE file_id=?
    ");

    $check->bind_param("s", $file_id);
    $check->execute();

    if ($check->get_result()->num_rows == 0) {

        $stmt = $conn->prepare("
            INSERT INTO videos (folder, file_id)
            VALUES (?, ?)
        ");

        $stmt->bind_param("ss", $folder, $file_id);
        $stmt->execute();
    }
}

function get_folders()
{
    global $conn;

    $result = $conn->query("
        SELECT DISTINCT folder FROM videos
    ");

    $folders = [];

    while ($row = $result->fetch_assoc()) {
        $folders[] = $row['folder'];
    }

    return $folders;
}

function get_videos($folder)
{
    global $conn;

    $stmt = $conn->prepare("
        SELECT * FROM videos
        WHERE folder=?
        ORDER BY id DESC
    ");

    $stmt->bind_param("s", $folder);
    $stmt->execute();

    return $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
}

function delete_folder($name)
{
    global $conn;

    $stmt = $conn->prepare("
        DELETE FROM videos WHERE folder=?
    ");

    $stmt->bind_param("s", $name);
    $stmt->execute();
}

function delete_video($folder, $index)
{
    global $conn;

    $videos = get_videos($folder);

    if (isset($videos[$index])) {

        $id = $videos[$index]['id'];

        $stmt = $conn->prepare("
            DELETE FROM videos WHERE id=?
        ");

        $stmt->bind_param("i", $id);
        $stmt->execute();
    }
}


// ================= EXPIRY =================
function set_expiry($user_id, $message_ids, $chat_id, $expire_at)
{
    global $conn;

    $messages = json_encode($message_ids);

    $stmt = $conn->prepare("
        INSERT INTO expiry
        (user_id, message_ids, chat_id, expire_at)
        VALUES (?, ?, ?, ?)
    ");

    $stmt->bind_param(
        "isii",
        $user_id,
        $messages,
        $chat_id,
        $expire_at
    );

    $stmt->execute();
}

function get_expired($now)
{
    global $conn;

    $stmt = $conn->prepare("
        SELECT * FROM expiry
        WHERE expire_at <= ?
    ");

    $stmt->bind_param("i", $now);
    $stmt->execute();

    return $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
}

function delete_expiry($id)
{
    global $conn;

    $stmt = $conn->prepare("
        DELETE FROM expiry
        WHERE id=?
    ");

    $stmt->bind_param("i", $id);
    $stmt->execute();
}


// ================= AUTO DELETE =================
function check_expiry()
{
    global $bot;

    $expired = get_expired(time());

    foreach ($expired as $item) {

        $chat_id = $item['chat_id'];

        $messages = json_decode($item['message_ids'], true);

        foreach ($messages as $mid) {

            try {

                $bot->deleteMessage([
                    'chat_id' => $chat_id,
                    'message_id' => $mid
                ]);

            } catch (Exception $e) {

            }
        }

        delete_expiry($item['id']);
    }
}

check_expiry();


// ================= START =================
function start($chat_id)
{
    global $bot;

    $text = get_config("start_text") ?: "👋 Welcome";

    $keyboard = [
        'keyboard' => [
            [['text' => '📥 Download']]
        ],
        'resize_keyboard' => true
    ];

    // ❌ BUY BUTTON FULL REMOVE

    $bot->sendMessage([
        'chat_id' => $chat_id,
        'text' => $text,
        'reply_markup' => json_encode($keyboard)
    ]);
}


// ================= UPDATE =================
$update = $bot->getWebhookUpdate();

$message = $update->getMessage();
$callback = $update->getCallbackQuery();


// ================= CALLBACK =================
if ($callback) {

    $data = $callback->getData();

    // ❌ PAID SYSTEM REMOVE
}


// ================= MESSAGE =================
if ($message) {

    $chat_id = $message->getChat()->getId();
    $user_id = $message->getFrom()->getId();

    $text = $message->getText();


// ================= START =================
    if ($text == "/start") {

        start($chat_id);
    }


// ================= ADMIN =================
    elseif ($text == "/admin") {

        if ($user_id != $ADMIN_ID) {

            $bot->sendMessage([
                'chat_id' => $chat_id,
                'text' => "❌ Not allowed"
            ]);

            exit;
        }

        $panel =
            "🛠 ADMIN PANEL\n\n" .
            "📂 /setfolder NAME\n" .
            "📂 /setchannelfolder NAME\n" .
            "📁 /folders\n" .
            "🗑 /delfolder NAME\n" .
            "❌ /delvideo INDEX\n";

        $bot->sendMessage([
            'chat_id' => $chat_id,
            'text' => $panel
        ]);
    }


// ================= SET FOLDER =================
    elseif (strpos($text, "/setfolder") === 0) {

        if ($user_id != $ADMIN_ID) {
            exit;
        }

        $name = trim(str_replace("/setfolder", "", $text));

        $current_folder[$user_id] = $name;

        $bot->sendMessage([
            'chat_id' => $chat_id,
            'text' => "📂 Active folder: $name"
        ]);
    }


// ================= SHOW FOLDERS =================
    elseif ($text == "/folders") {

        $folders = get_folders();

        $txt = "📂 Folders:\n\n";

        foreach ($folders as $f) {

            $count = count(get_videos($f));

            $txt .= "👉 $f ($count)\n";
        }

        $bot->sendMessage([
            'chat_id' => $chat_id,
            'text' => $txt
        ]);
    }


// ================= SAVE VIDEO =================
    elseif ($message->getVideo()) {

        if ($user_id != $ADMIN_ID) {
            exit;
        }

        if (!isset($current_folder[$user_id])) {

            $bot->sendMessage([
                'chat_id' => $chat_id,
                'text' => "❌ Use /setfolder first"
            ]);

            exit;
        }

        $video = $message->getVideo();

        add_video(
            $current_folder[$user_id],
            $video->getFileId()
        );

        $bot->sendMessage([
            'chat_id' => $chat_id,
            'text' => "✅ Video saved"
        ]);
    }


// ================= DOWNLOAD =================
    elseif ($text == "📥 Download") {

        // ❌ PREMIUM CHECK REMOVE

        $temp_access[$user_id] = true;

        $folders = get_folders();

        if (!$folders) {

            $bot->sendMessage([
                'chat_id' => $chat_id,
                'text' => "❌ No folders"
            ]);

            exit;
        }

        $keyboard = [
            'keyboard' => [],
            'resize_keyboard' => true
        ];

        foreach ($folders as $f) {

            $keyboard['keyboard'][] = [
                ['text' => "📂 $f"]
            ];
        }

        $bot->sendMessage([
            'chat_id' => $chat_id,
            'text' => "⏳ Videos ready (auto delete in 15 min)",
            'reply_markup' => json_encode($keyboard)
        ]);
    }


// ================= OPEN FOLDER =================
    elseif (strpos($text, "📂 ") === 0) {

        if (!isset($temp_access[$user_id])) {

            $bot->sendMessage([
                'chat_id' => $chat_id,
                'text' => "❌ Click Download first"
            ]);

            exit;
        }

        $folder = str_replace("📂 ", "", $text);

        $videos = get_videos($folder);

        if (!$videos) {

            $bot->sendMessage([
                'chat_id' => $chat_id,
                'text' => "❌ No videos"
            ]);

            exit;
        }

        $sent_videos[$user_id] = [];

        foreach ($videos as $v) {

            $m = $bot->sendVideo([
                'chat_id' => $chat_id,
                'video' => $v['file_id'],
                'protect_content' => true
            ]);

            $sent_videos[$user_id][] = $m->getMessageId();
        }

        set_expiry(
            $user_id,
            $sent_videos[$user_id],
            $chat_id,
            time() + 900
        );
    }
}

echo "Bot Running";

?>
