<?php
$password = readline("Password: ");
$saltRaw = random_bytes(8);
$salt = base64_encode($saltRaw);
$result = crypt($password,'$6' . '$' . $salt .'$');
print $result . "\n";
?>
