<?php
class WorkordersController {
    private $db;
    private $work_order;

    public function __construct($db) {
        $this->db = $db;
        require_once dirname(__DIR__) . '/auth/validate_token.php';
        require_once dirname(__DIR__) . '/models/WorkOrder.php';
        $this->work_order = new WorkOrder($this->db);
        validate_token();
    }

    // Crear una nueva orden de trabajo desde una cotización
    public function create() {
        $data = json_decode(file_get_contents("php://input"));

        if (!empty($data->cotizacion_id) && !empty($data->fecha_inicio)) {
            $this->work_order->cotizacion_id = $data->cotizacion_id;
            $this->work_order->fecha_inicio = $data->fecha_inicio;

            if ($this->work_order->create()) {
                http_response_code(201);
                echo json_encode([
                    "message" => "Orden de trabajo creada exitosamente.",
                    "id_ot" => $this->work_order->id_ot
                ]);
            } else {
                http_response_code(400); // Bad Request, podría ser porque la cotización no está aceptada
                echo json_encode(["message" => "No se pudo crear la orden de trabajo. Verifique que la cotización esté aceptada."]);
            }
        } else {
            http_response_code(400);
            echo json_encode(["message" => "Datos incompletos. Se requiere cotizacion_id y fecha_inicio."]);
        }
    }

    // Actualizar una orden de trabajo
    public function update($id) {
        $data = json_decode(file_get_contents("php://input"));

        if (!empty($id) && !empty($data->estatus)) {
            $this->work_order->id_ot = $id;
            $this->work_order->estatus = $data->estatus;
            $this->work_order->tecnico_asignado = $data->tecnico_asignado ?? null;
            $this->work_order->fecha_fin = $data->fecha_fin ?? null;

            if ($this->work_order->update()) {
                http_response_code(200);
                echo json_encode(["message" => "Orden de trabajo actualizada."]);
            } else {
                http_response_code(503);
                echo json_encode(["message" => "No se pudo actualizar la orden de trabajo."]);
            }
        } else {
            http_response_code(400);
            echo json_encode(["message" => "Datos incompletos o ID de OT no proporcionado."]);
        }
    }
}
?>
