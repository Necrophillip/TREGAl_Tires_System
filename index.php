<?php
// Definir una constante para la ruta raíz para que los 'includes' sean más robustos.
define('ROOT_PATH', __DIR__);

$request_path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

// Si la petición es para un archivo estático existente (css, js, etc.), déjalo pasar.
// Esto es importante para que el servidor de desarrollo sirva archivos como `index.html` si no lo especificamos.
if (php_sapi_name() === 'cli-server' && is_file(__DIR__ . $request_path)) {
    return false;
}

// Si la petición es a la raíz, servir el index.html
if ($request_path === '/' || $request_path === '/index.html') {
    readfile('index.html');
    exit();
}

// --- Lógica de la API ---

// Headers de la API
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");
header("Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS");
header("Access-Control-Max-Age: 3600");
header("Access-Control-Allow-Headers: Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// --- Configuración Principal de la API ---
require_once ROOT_PATH . '/api/vendor/autoload.php';
require_once ROOT_PATH . '/api/config/database.php';
require_once ROOT_PATH . '/api/config/core.php';

$uri = explode('/', trim($request_path, '/'));
// La URI ya no contiene `/api/`, así que los recursos empiezan en el índice 0
$resource = isset($uri[0]) ? $uri[0] : null;
$id = isset($uri[1]) ? $uri[1] : null;
$action = isset($uri[2]) ? $uri[2] : null;

error_log("API Resource: $resource, ID: $id, Action: $action");

$database = new Database();
$db = $database->getConnection();

// --- Rutas Especiales de la API ---

// Login
if ($resource === 'users' && $id === 'login') {
    require_once 'api/controllers/UsersController.php';
    $controller = new UsersController($db);
    if ($_SERVER['REQUEST_METHOD'] === 'POST') $controller->login();
    else http_response_code(405);
    exit();
}

// --- Enrutador CRUD Genérico de la API ---
if ($resource) {
    $controllerName = ucfirst($resource) . 'Controller';
    $controllerFile = 'api/controllers/' . $controllerName . '.php';

    if (file_exists($controllerFile)) {
        require_once $controllerFile;
        // Los controladores ahora están en el subdirectorio `api`
        // y sus `require_once` internos también deben ser ajustados.
        $controller = new $controllerName($db);
        $method = $_SERVER['REQUEST_METHOD'];

        switch ($method) {
            case 'GET':
                if ($id) { if (method_exists($controller, 'readOne')) $controller->readOne($id); else http_response_code(501); }
                else { if (method_exists($controller, 'read')) $controller->read(); else http_response_code(501); }
                break;
            case 'POST':
                if (method_exists($controller, 'create')) $controller->create(); else http_response_code(501);
                break;
            case 'PUT':
                if ($id && method_exists($controller, 'update')) $controller->update($id); else http_response_code(400);
                break;
            case 'DELETE':
                if ($id && method_exists($controller, 'delete')) $controller->delete($id); else http_response_code(400);
                break;
            default:
                http_response_code(405);
                break;
        }
    } else {
        http_response_code(404);
        echo json_encode(['message' => "Recurso no encontrado: $resource"]);
    }
} else {
    // Si no es una ruta de API y no es la raíz, es un 404.
    http_response_code(404);
    echo json_encode(['message' => 'Ruta no encontrada.']);
}
?>