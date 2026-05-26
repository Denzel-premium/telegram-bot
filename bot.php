<?php

/*
|--------------------------------------------------------------------------
| TELEGRAM VIDEO BOT
| SINGLE FILE WEBHOOK VERSION
|--------------------------------------------------------------------------
| SET:
| 1. BOT TOKEN
| 2. ADMIN ID
| 3. DATABASE DETAILS
|--------------------------------------------------------------------------
*/


// ================= CONFIG =================
define('API_KEY','BOT_TOKEN_HERE');

$ADMIN_ID = 123456789;


// ================= DATABASE =================
$db_host = "localhost";
$db_name = "YOUR_DB_NAME";
$db_user = "YOUR_DB_USER";
$db_pass = "YOUR_DB_PASSWORD";

$conn = mysqli_connect($db_host,$db_user,$db_pass,$db_name);

if(!$conn){
    die("DB ERROR");
}


// ================= BOT FUNCTION =================
function bot($method,$data=[]){

    $url = "https://api.telegram.org/bot".API_KEY."/".$method;

    $ch = curl_init();

    curl_setopt($ch,CURLOPT_URL,$url);
    curl_setopt($ch,CURLOPT_RETURNTRANSFER,true);
    curl_setopt($ch,CURLOPT_POSTFIELDS,$data);

    $res = curl_exec($ch);

    return json_decode($res,true);
}


// ================= CREATE TABLES =================
mysqli_query($conn,"
CREATE TABLE IF NOT EXISTS videos(
id INT AUTO_INCREMENT PRIMARY KEY,
folder TEXT,
file_id TEXT
)");

mysqli_query($conn,"
CREATE TABLE IF NOT EXISTS expiry(
id INT AUTO_INCREMENT PRIMARY KEY,
chat_id BIGINT,
message_ids LONGTEXT,
expire_at BIGINT
)");


// ================= UPDATE =================
$update = json_decode(file_get_contents("php://input"),true);

$message = $update['message'];
$text = $message['text'];
$chat_id = $message['chat']['id'];
$user_id = $message['from']['id'];


// ================= AUTO DELETE =================
$now = time();

$get = mysqli_query($conn,"
SELECT * FROM expiry
WHERE expire_at <= '$now'
");

while($exp = mysqli_fetch_assoc($get)){

    $msgs = json_decode($exp['message_ids'],true);

    foreach($msgs as $mid){

        bot('deleteMessage',[
            'chat_id'=>$exp['chat_id'],
            'message_id'=>$mid
        ]);
    }

    mysqli_query($conn,"
    DELETE FROM expiry
    WHERE id='".$exp['id']."'
    ");
}


// ================= START =================
if($text == "/start"){

    $keyboard = [
        'keyboard'=>[
            [['text'=>"📥 Download"]]
        ],
        'resize_keyboard'=>true
    ];

    bot('sendMessage',[
        'chat_id'=>$chat_id,
        'text'=>"👋 Welcome",
        'reply_markup'=>json_encode($keyboard)
    ]);
}


// ================= ADMIN =================
elseif($text == "/admin"){

    if($user_id != $ADMIN_ID){
        exit;
    }

    $txt =
    "🛠 ADMIN PANEL\n\n".
    "📂 /setfolder NAME\n".
    "📁 /folders\n".
    "🗑 /delfolder NAME\n";

    bot('sendMessage',[
        'chat_id'=>$chat_id,
        'text'=>$txt
    ]);
}


// ================= SET FOLDER =================
elseif(strpos($text,"/setfolder") === 0){

    if($user_id != $ADMIN_ID){
        exit;
    }

    $folder = trim(str_replace("/setfolder","",$text));

    file_put_contents("folder.txt",$folder);

    bot('sendMessage',[
        'chat_id'=>$chat_id,
        'text'=>"✅ Folder Set: ".$folder
    ]);
}


// ================= SAVE VIDEO =================
elseif(isset($message['video'])){

    if($user_id != $ADMIN_ID){
        exit;
    }

    $folder = @file_get_contents("folder.txt");

    if(!$folder){

        bot('sendMessage',[
            'chat_id'=>$chat_id,
            'text'=>"❌ Use /setfolder first"
        ]);

        exit;
    }

    $file_id = $message['video']['file_id'];

    mysqli_query($conn,"
    INSERT INTO videos(folder,file_id)
    VALUES('$folder','$file_id')
    ");

    bot('sendMessage',[
        'chat_id'=>$chat_id,
        'text'=>"✅ Video Saved"
    ]);
}


// ================= DOWNLOAD =================
elseif($text == "📥 Download"){

    $get = mysqli_query($conn,"
    SELECT DISTINCT folder FROM videos
    ");

    $keyboard = [
        'keyboard'=>[],
        'resize_keyboard'=>true
    ];

    while($row = mysqli_fetch_assoc($get)){

        $keyboard['keyboard'][] = [
            ['text'=>"📂 ".$row['folder']]
        ];
    }

    bot('sendMessage',[
        'chat_id'=>$chat_id,
        'text'=>"📂 Select Folder",
        'reply_markup'=>json_encode($keyboard)
    ]);
}


// ================= OPEN FOLDER =================
elseif(strpos($text,"📂 ") === 0){

    $folder = trim(str_replace("📂 ","",$text));

    $get = mysqli_query($conn,"
    SELECT * FROM videos
    WHERE folder='$folder'
    ORDER BY id DESC
    ");

    $ids = [];

    while($video = mysqli_fetch_assoc($get)){

        $send = bot('sendVideo',[
            'chat_id'=>$chat_id,
            'video'=>$video['file_id'],
            'protect_content'=>true
        ]);

        $ids[] = $send['result']['message_id'];
    }

    $json = json_encode($ids);

    $expire = time() + 900;

    mysqli_query($conn,"
    INSERT INTO expiry(chat_id,message_ids,expire_at)
    VALUES('$chat_id','$json','$expire')
    ");
}

?>
