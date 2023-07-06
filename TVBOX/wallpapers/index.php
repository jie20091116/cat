<?php
#随机图片名称 取得值1-233之间的随机数
$img =  rand(1,22).'.jpg';
#拼凑,完整的图片地址
$URI = 'https://cdn.jsdelivr.net/gh/fantaiying7/sqmrts@main/wallpapers/'.$img;
# 301转向
header("HTTP/1.1 301 Moved Permanently");
header("Location: $URI");
exit();
?>
