<?php
class VehiclesController {
    private $db;
    private $vehicle;

    public function __construct($db) {
        $this->db = $db;
        require_once 'auth/validate_token.php';
        require_once 'models/Vehicle.php';
        $this->vehicle = new Vehicle($this->db);
        // Todas las acciones en este controlador requieren un token válido.
        validate_token();
    }

    // Listar todos los vehículos
    public function read() {
        $stmt = $this->vehicle->read();
        $num = $stmt->rowCount();

        if ($num > 0) {
            $vehicles_arr = ["records" => []];
            while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
                extract($row);
                $vehicle_item = [
                    "id_vehiculo" => $id_vehiculo,
                    "cliente_id" => $cliente_id,
                    "cliente_nombre" => $cliente_nombre,
                    "marca" => $marca,
                    "modelo" => $modelo,
                    "anio" => $anio,
                    "vin" => $vin,
                    "placas" => $placas,
                    "km" => $km
                ];
                array_push($vehicles_arr["records"], $vehicle_item);
            }
            http_response_code(200);
            echo json_encode($vehicles_arr);
        } else {
            http_response_code(404);
            echo json_encode(["message" => "No se encontraron vehículos."]);
        }
    }

    // Obtener un solo vehículo
    public function readOne($id) {
        $this->vehicle->id_vehiculo = $id;
        if ($this->vehicle->readOne()) {
            $vehicle_item = [
                "id_vehiculo" => $this->vehicle->id_vehiculo,
                "cliente_id" => $this->vehicle->cliente_id,
                "cliente_nombre" => $this->vehicle->cliente_nombre,
                "marca" => $this->vehicle->marca,
                "modelo" => $this->vehicle->modelo,
                "anio" => $this->vehicle->anio,
                "vin" => $this->vehicle->vin,
                "placas" => $this->vehicle->placas,
                "km" => $this->vehicle->km
            ];
            http_response_code(200);
            echo json_encode($vehicle_item);
        } else {
            http_response_code(404);
            echo json_encode(["message" => "Vehículo no encontrado."]);
        }
    }

    // Crear un nuevo vehículo
    public function create() {
        $data = json_decode(file_get_contents("php://input"));

        if (!empty($data->cliente_id) && !empty($data->marca) && !empty($data->modelo)) {
            $this->vehicle->cliente_id = $data->cliente_id;
            $this->vehicle->marca = $data->marca;
            $this->vehicle->modelo = $data->modelo;
            $this->vehicle->anio = $data->anio ?? null;
            $this->vehicle->vin = $data->vin ?? '';
            $this->vehicle->placas = $data->placas ?? '';
            $this->vehicle->km = $data->km ?? null;

            if ($this->vehicle->create()) {
                http_response_code(201);
                echo json_encode(["message" => "Vehículo creado exitosamente.", "id_vehiculo" => $this->vehicle->id_vehiculo]);
            } else {
                http_response_code(503);
                echo json_encode(["message" => "No se pudo crear el vehículo."]);
            }
        } else {
            http_response_code(400);
            echo json_encode(["message" => "Datos incompletos. Se requiere cliente_id, marca y modelo."]);
        }
    }

    // Actualizar un vehículo
    public function update($id) {
        $data = json_decode(file_get_contents("php://input"));

        if (!empty($id) && !empty($data->cliente_id) && !empty($data->marca) && !empty($data->modelo)) {
            $this->vehicle->id_vehiculo = $id;
            $this->vehicle->cliente_id = $data->cliente_id;
            $this->vehicle->marca = $data->marca;
            $this->vehicle->modelo = $data->modelo;
            $this->vehicle->anio = $data->anio ?? null;
            $this->vehicle->vin = $data->vin ?? '';
            $this->vehicle->placas = $data->placas ?? '';
            $this->vehicle->km = $data->km ?? null;

            if ($this->vehicle->update()) {
                http_response_code(200);
                echo json_encode(["message" => "Vehículo actualizado exitosamente."]);
            } else {
                http_response_code(503);
                echo json_encode(["message" => "No se pudo actualizar el vehículo."]);
            }
        } else {
            http_response_code(400);
            echo json_encode(["message" => "Datos incompletos o ID de vehículo no proporcionado."]);
        }
    }

    // Eliminar un vehículo
    public function delete($id) {
        if (!empty($id)) {
            $this->vehicle->id_vehiculo = $id;
            if ($this->vehicle->delete()) {
                http_response_code(200);
                echo json_encode(["message" => "Vehículo eliminado exitosamente."]);
            } else {
                http_response_code(503);
                echo json_encode(["message" => "No se pudo eliminar el vehículo."]);
            }
        } else {
            http_response_code(400);
            echo json_encode(["message" => "ID de vehículo no proporcionado."]);
        }
    }
}
?>
