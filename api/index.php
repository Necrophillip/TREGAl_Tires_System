<?php
// Headers
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");
header("Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS");
header("Access-Control-Max-Age: 3600");
header("Access-Control-Allow-Headers: Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// --- Main Setup ---
require_once 'vendor/autoload.php';
require_once 'config/database.php';
require_once 'config/core.php';

$uri = explode('/', trim(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH), '/'));
$resource = isset($uri[1]) ? $uri[1] : null;
$id = isset($uri[2]) ? $uri[2] : null;
$action = isset($uri[3]) ? $uri[3] : null;

$database = new Database();
$db = $database->getConnection();

// --- Special Routes ---

// Login
if ($resource === 'users' && $id === 'login') {
    require_once 'controllers/UsersController.php';
    $controller = new UsersController($db);
    if ($_SERVER['REQUEST_METHOD'] === 'POST') $controller->login();
    else http_response_code(405);
    exit();
}

// Reports
if ($resource === 'reports' && $id) {
    require_once 'controllers/ReportsController.php';
    $controller = new ReportsController($db);
    $action = $id; // e.g., salesByMonth
    if (method_exists($controller, $action) && $_SERVER['REQUEST_METHOD'] === 'GET') {
        $controller->$action();
    } else {
        http_response_code(404);
        echo json_encode(['message' => 'Reporte no encontrado.']);
    }
    exit();
}

// Quote actions
if ($resource === 'quotes' && $id && $action) {
    require_once 'controllers/QuotesController.php';
    $controller = new QuotesController($db);
    if ($action === 'status' && $_SERVER['REQUEST_METHOD'] === 'PUT') $controller->updateStatus($id);
    elseif ($action === 'pdf' && $_SERVER['REQUEST_METHOD'] === 'GET') $controller->generatePdf($id);
    else http_response_code(404);
    exit();
}

// --- Generic CRUD Router ---
if ($resource) {
    $controllerName = ucfirst($resource) . 'Controller';
    $controllerFile = 'controllers/' . $controllerName . '.php';

    if (file_exists($controllerFile)) {
        require_once $controllerFile;
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
    http_response_code(200);
    echo json_encode(['message' => 'API de Autotech ERP está en funcionamiento.']);
}
?>
