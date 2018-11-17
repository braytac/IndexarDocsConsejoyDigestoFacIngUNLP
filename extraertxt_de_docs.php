<?php

include("doc2txt.class.long.php");

$f = $argv[1];

// $fd = fopen($f, "r");
//print_r( fread($fd, filesize($f)));

$doc2txt = new Doc2Txt($f);
echo utf8_decode($doc2txt->convertToText());

?>
