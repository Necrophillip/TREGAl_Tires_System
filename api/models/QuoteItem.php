<?php
class QuoteItem {
    private $conn;
    private $table_name = "cotizacion_items";

    // Propiedades del objeto
    public $id_item;
    public $cotizacion_id;
    public $tipo;
    public $descripcion;
    public $cantidad;
    public $precio_unitario;
    public $descuento;
    public $aplica_iva;
    public $importe;

    public function __construct($db) {
        $this->conn = $db;
    }

    // Leer todos los items de una cotización específica
    public function readByQuoteId($quote_id) {
        $query = "SELECT * FROM " . $this->table_name . " WHERE cotizacion_id = ?";
        $stmt = $this->conn->prepare($query);
        $stmt->bindParam(1, $quote_id);
        $stmt->execute();
        return $stmt;
    }

    // Crear un nuevo item de cotización
    public function create() {
        $query = "INSERT INTO " . $this->table_name . "
                  SET
                    cotizacion_id=:cotizacion_id,
                    tipo=:tipo,
                    descripcion=:descripcion,
                    cantidad=:cantidad,
                    precio_unitario=:precio_unitario,
                    descuento=:descuento,
                    aplica_iva=:aplica_iva,
                    importe=:importe";

        $stmt = $this->conn->prepare($query);

        // Limpiar datos
        $this->cotizacion_id = htmlspecialchars(strip_tags($this->cotizacion_id));
        $this->tipo = htmlspecialchars(strip_tags($this->tipo));
        $this->descripcion = htmlspecialchars(strip_tags($this->descripcion));
        // Los valores numéricos y booleanos no necesitan strip_tags

        // Vincular parámetros
        $stmt->bindParam(":cotizacion_id", $this->cotizacion_id);
        $stmt->bindParam(":tipo", $this->tipo);
        $stmt->bindParam(":descripcion", $this->descripcion);
        $stmt->bindParam(":cantidad", $this->cantidad);
        $stmt->bindParam(":precio_unitario", $this->precio_unitario);
        $stmt->bindParam(":descuento", $this->descuento);
        $stmt->bindParam(":aplica_iva", $this->aplica_iva);
        $stmt->bindParam(":importe", $this->importe);

        if ($stmt->execute()) {
            return true;
        }

        return false;
    }
}
?>
