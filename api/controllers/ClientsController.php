<?php
class ClientsController {
    private $db;
    private $client;
    private $auth_user;

    public function __construct($db) {
        $this->db = $db;
        require_once dirname(__DIR__) . '/auth/validate_token.php';
        require_once dirname(__DIR__) . '/models/Client.php';
        $this->client = new Client($this->db);
        $this->auth_user = validate_token();
    }

    // Listar todos los clientes
    public function read() {
        $stmt = $this->client->read();
        $num = $stmt->rowCount();

        if ($num > 0) {
            $clients_arr = [];
            $clients_arr["records"] = [];

            while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
                extract($row);
                $client_item = [
                    "id_cliente" => $id_cliente,
                    "nombre" => $nombre,
                    "rfc" => $rfc,
                    "correo" => $correo,
                    "telefono" => $telefono,
                    "direccion" => $direccion
                ];
                array_push($clients_arr["records"], $client_item);
            }
            http_response_code(200);
            echo json_encode($clients_arr);
        } else {
            http_response_code(404);
            echo json_encode(["message" => "No se encontraron clientes."]);
        }
    }

    // Obtener un solo cliente
    public function readOne($id) {
        $this->client->id_cliente = $id;
        if ($this->client->readOne()) {
            $client_item = [
                "id_cliente" => $this->client->id_cliente,
                "nombre" => $this->client->nombre,
                "rfc" => $this->client->rfc,
                "correo" => $this->client->correo,
                "telefono" => $this->client->telefono,
                "direccion" => $this->client->direccion
            ];
            http_response_code(200);
            echo json_encode($client_item);
        } else {
            http_response_code(404);
            echo json_encode(["message" => "Cliente no encontrado."]);
        }
    }

    // Crear un nuevo cliente
    public function create() {
        $data = json_decode(file_get_contents("php://input"));

        if (!empty($data->nombre) && !empty($data->correo)) {
            $this->client->nombre = $data->nombre;
            $this->client->rfc = $data->rfc ?? '';
            $this->client->correo = $data->correo;
            $this->client->telefono = $data->telefono ?? '';
            $this->client->direccion = $data->direccion ?? '';

            if ($this->client->create()) {
                http_response_code(201);
                echo json_encode(["message" => "Cliente creado exitosamente.", "id_cliente" => $this->client->id_cliente]);
            } else {
                http_response_code(503);
                echo json_encode(["message" => "No se pudo crear el cliente."]);
            }
        } else {
            http_response_code(400);
            echo json_encode(["message" => "Datos incompletos. Nombre y correo son requeridos."]);
        }
    }

    // Actualizar un cliente
    public function update($id) {
        $data = json_decode(file_get_contents("php://input"));

        if (!empty($id) && !empty($data->nombre) && !empty($data->correo)) {
            $this->client->id_cliente = $id;
            $this->client->nombre = $data->nombre;
            $this->client->rfc = $data->rfc ?? '';
            $this->client->correo = $data->correo;
            $this->client->telefono = $data->telefono ?? '';
            $this->client->direccion = $data->direccion ?? '';

            if ($this->client->update()) {
                http_response_code(200);
                echo json_encode(["message" => "Cliente actualizado exitosamente."]);
            } else {
                http_response_code(503);
                echo json_encode(["message" => "No se pudo actualizar el cliente."]);
            }
        } else {
            http_response_code(400);
            echo json_encode(["message" => "Datos incompletos o ID de cliente no proporcionado."]);
        }
    }

    // Eliminar un cliente
    public function delete($id) {
        // Solo un admin puede eliminar
        if ($this->auth_user->rol !== 'admin') {
            http_response_code(403); // Forbidden
            echo json_encode(["message" => "Acceso denegado. Se requiere rol de administrador."]);
            return;
        }

        if (!empty($id)) {
            $this->client->id_cliente = $id;
            if ($this->client->delete()) {
                http_response_code(200);
                echo json_encode(["message" => "Cliente eliminado exitosamente."]);
            } else {
                http_response_code(503);
                echo json_encode(["message" => "No se pudo eliminar el cliente."]);
            }
        } else {
            http_response_code(400);
            echo json_encode(["message" => "ID de cliente no proporcionado."]);
        }
    }
}
?>
