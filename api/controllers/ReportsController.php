<?php
class ReportsController {
    private $db;

    public function __construct($db) {
        $this->db = $db;
        require_once 'auth/validate_token.php';
        validate_token();
    }

    // Reporte de ventas por mes
    public function salesByMonth() {
        $query = "SELECT
                    DATE_FORMAT(c.fecha, '%Y-%m') AS mes,
                    SUM(c.total) AS total_ventas
                  FROM
                    cotizaciones c
                  WHERE
                    c.estatus IN ('aceptada', 'finalizada', 'entregada')
                  GROUP BY
                    DATE_FORMAT(c.fecha, '%Y-%m')
                  ORDER BY
                    mes ASC";

        $stmt = $this->db->prepare($query);
        $stmt->execute();
        $this->returnJson($stmt);
    }

    // Reporte de ingresos por cliente
    public function revenueByClient() {
        $query = "SELECT
                    cl.nombre AS cliente,
                    SUM(c.total) AS total_ingresos,
                    COUNT(c.id_cotizacion) AS numero_ordenes
                  FROM
                    cotizaciones c
                  JOIN
                    clientes cl ON c.cliente_id = cl.id_cliente
                  WHERE
                    c.estatus IN ('aceptada', 'finalizada', 'entregada')
                  GROUP BY
                    cl.nombre
                  ORDER BY
                    total_ingresos DESC";

        $stmt = $this->db->prepare($query);
        $stmt->execute();
        $this->returnJson($stmt);
    }

    // Reporte de servicios más comunes
    public function commonServices() {
        $query = "SELECT
                    ci.descripcion AS servicio,
                    COUNT(ci.id_item) AS cantidad_veces
                  FROM
                    cotizacion_items ci
                  WHERE
                    ci.tipo = 'mano_obra'
                  GROUP BY
                    ci.descripcion
                  ORDER BY
                    cantidad_veces DESC
                  LIMIT 10"; // Top 10

        $stmt = $this->db->prepare($query);
        $stmt->execute();
        $this->returnJson($stmt);
    }

    public function ping() {
        http_response_code(200);
        echo json_encode(["message" => "pong"]);
    }

    // Helper para devolver resultados como JSON
    private function returnJson($stmt) {
        $num = $stmt->rowCount();
        if ($num > 0) {
            $records = $stmt->fetchAll(PDO::FETCH_ASSOC);
            http_response_code(200);
            echo json_encode(["records" => $records]);
        } else {
            http_response_code(404);
            echo json_encode(["message" => "No se encontraron datos para este reporte."]);
        }
    }
}
?>
