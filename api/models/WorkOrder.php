<?php
class WorkOrder {
    private $conn;
    private $table_name = "ordenes_trabajo";

    // Propiedades del objeto
    public $id_ot;
    public $cotizacion_id;
    public $fecha_inicio;
    public $fecha_fin;
    public $tecnico_asignado;
    public $estatus;

    public function __construct($db) {
        $this->conn = $db;
    }

    // Crear una nueva orden de trabajo a partir de una cotización
    public function create() {
        // Primero, verificar que la cotización exista y esté 'aceptada'
        $quote_query = "SELECT cliente_id, vehiculo_id, estatus FROM cotizaciones WHERE id_cotizacion = :cotizacion_id";
        $quote_stmt = $this->conn->prepare($quote_query);
        $quote_stmt->bindParam(":cotizacion_id", $this->cotizacion_id);
        $quote_stmt->execute();
        $quote = $quote_stmt->fetch(PDO::FETCH_ASSOC);

        if (!$quote || $quote['estatus'] !== 'aceptada') {
            // No se puede crear la OT si la cotización no está aceptada
            return false;
        }

        // Segundo, crear la orden de trabajo
        $query = "INSERT INTO " . $this->table_name . "
                  SET
                    cotizacion_id=:cotizacion_id,
                    cliente_id=:cliente_id,
                    vehiculo_id=:vehiculo_id,
                    fecha_inicio=:fecha_inicio,
                    estatus='pendiente'"; // Por defecto al crear

        $stmt = $this->conn->prepare($query);

        // Limpiar datos
        $this->cotizacion_id = htmlspecialchars(strip_tags($this->cotizacion_id));
        $this->fecha_inicio = htmlspecialchars(strip_tags($this->fecha_inicio));
        $cliente_id = htmlspecialchars(strip_tags($quote['cliente_id']));
        $vehiculo_id = htmlspecialchars(strip_tags($quote['vehiculo_id']));

        // Vincular parámetros
        $stmt->bindParam(":cotizacion_id", $this->cotizacion_id);
        $stmt->bindParam(":cliente_id", $cliente_id);
        $stmt->bindParam(":vehiculo_id", $vehiculo_id);
        $stmt->bindParam(":fecha_inicio", $this->fecha_inicio);

        if ($stmt->execute()) {
            $this->id_ot = $this->conn->lastInsertId();
            return true;
        }

        return false;
    }

    // Actualizar estatus o técnico de una orden de trabajo
    public function update() {
        $query = "UPDATE " . $this->table_name . "
                SET
                    fecha_fin = :fecha_fin,
                    tecnico_asignado = :tecnico_asignado,
                    estatus = :estatus
                WHERE
                    id_ot = :id_ot";

        $stmt = $this->conn->prepare($query);

        // Limpiar datos
        $this->id_ot = htmlspecialchars(strip_tags($this->id_ot));
        $this->tecnico_asignado = htmlspecialchars(strip_tags($this->tecnico_asignado));
        $this->estatus = htmlspecialchars(strip_tags($this->estatus));

        // Vincular parámetros
        $stmt->bindParam(':id_ot', $this->id_ot);
        $stmt->bindParam(':tecnico_asignado', $this->tecnico_asignado);
        $stmt->bindParam(':estatus', $this->estatus);

        // Tratar fecha_fin que puede ser NULL
        if (!is_null($this->fecha_fin)) {
            $stmt->bindValue(":fecha_fin", htmlspecialchars(strip_tags($this->fecha_fin)));
        } else {
            $stmt->bindValue(":fecha_fin", null, PDO::PARAM_NULL);
        }

        if ($stmt->execute()) {
            return true;
        }
        return false;
    }
}
?>
