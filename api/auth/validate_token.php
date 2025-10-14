<?php
require_once 'vendor/autoload.php';
use Firebase\JWT\JWT;
use Firebase\JWT\Key;

function validate_token() {
    $headers = getallheaders();

    if (!isset($headers['Authorization'])) {
        http_response_code(401);
        echo json_encode(["message" => "Acceso denegado. No se proporcionó token."]);
        exit();
    }

    $auth_header = $headers['Authorization'];
    list($jwt) = sscanf($auth_header, 'Bearer %s');

    if (!$jwt) {
        http_response_code(401);
        echo json_encode(["message" => "Acceso denegado. Token malformado."]);
        exit();
    }

    try {
        // La configuración del token se carga en index.php
        $decoded = JWT::decode($jwt, new Key(JWT_KEY, 'HS256'));
        return $decoded->data;
    } catch (Exception $e) {
        http_response_code(401);
        echo json_encode(["message" => "Acceso denegado. Token inválido.", "error" => $e->getMessage()]);
        exit();
    }
}
?>