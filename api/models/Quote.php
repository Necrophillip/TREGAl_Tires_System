<?php
class Quote {
    private $conn;
    private $table_name = "cotizaciones";

    // Propiedades del objeto
    public $id_cotizacion;
    public $folio;
    public $cliente_id;
    public $vehiculo_id;
    public $fecha;
    public $validez;
    public $notas;
    public $condiciones;
    public $subtotal;
    public $descuento;
    public $iva;
    public $total;
    public $estatus;

    // Propiedades para JOINs
    public $cliente_nombre;
    public $vehiculo_info;

    public function __construct($db) {
        $this->conn = $db;
    }

    // Crear una nueva cotización
    // Esta función manejará la transacción para la cotización y sus items.
    public function create($items_data) {
        // Iniciar transacción
        $this->conn->beginTransaction();

        try {
            // 1. Insertar la cotización principal (con totales en 0 temporalmente)
            $query = "INSERT INTO " . $this->table_name . "
                      SET cliente_id=:cliente_id, vehiculo_id=:vehiculo_id, fecha=:fecha, validez=:validez, notas=:notas, condiciones=:condiciones, estatus=:estatus, subtotal=0, descuento=0, iva=0, total=0, folio=''";

            $stmt = $this->conn->prepare($query);

            // Limpiar datos
            $this->cliente_id = htmlspecialchars(strip_tags($this->cliente_id));
            $this->vehiculo_id = htmlspecialchars(strip_tags($this->vehiculo_id));
            $this->fecha = htmlspecialchars(strip_tags($this->fecha));
            $this->validez = htmlspecialchars(strip_tags($this->validez));
            $this->notas = htmlspecialchars(strip_tags($this->notas));
            $this->condiciones = htmlspecialchars(strip_tags($this->condiciones));
            $this->estatus = htmlspecialchars(strip_tags($this->estatus));

            // Vincular parámetros
            $stmt->bindParam(":cliente_id", $this->cliente_id);
            $stmt->bindParam(":vehiculo_id", $this->vehiculo_id);
            $stmt->bindParam(":fecha", $this->fecha);
            $stmt->bindParam(":validez", $this->validez);
            $stmt->bindParam(":notas", $this->notas);
            $stmt->bindParam(":condiciones", $this->condiciones);
            $stmt->bindParam(":estatus", $this->estatus);

            if (!$stmt->execute()) {
                throw new Exception("No se pudo crear la cotización principal.");
            }

            $this->id_cotizacion = $this->conn->lastInsertId();

            // 2. Insertar los items de la cotización y calcular totales
            require_once __DIR__ . '/QuoteItem.php';
            $quote_item = new QuoteItem($this->conn);

            $total_subtotal = 0;
            $total_descuento = 0;
            $total_iva = 0;

            foreach ($items_data as $item_data) {
                $quote_item->cotizacion_id = $this->id_cotizacion;
                $quote_item->tipo = $item_data->tipo;
                $quote_item->descripcion = $item_data->descripcion;
                $quote_item->cantidad = $item_data->cantidad;
                $quote_item->precio_unitario = $item_data->precio_unitario;
                $quote_item->descuento = $item_data->descuento ?? 0;
                $quote_item->aplica_iva = $item_data->aplica_iva ?? true;

                // Calcular importe del item
                $importe_bruto = $quote_item->cantidad * $quote_item->precio_unitario;
                $valor_descuento = $importe_bruto * ($quote_item->descuento / 100);
                $subtotal_item = $importe_bruto - $valor_descuento;
                $iva_item = $quote_item->aplica_iva ? $subtotal_item * 0.16 : 0;
                $quote_item->importe = $subtotal_item + $iva_item;

                // Acumular totales
                $total_subtotal += $importe_bruto;
                $total_descuento += $valor_descuento;
                $total_iva += $iva_item;

                if (!$quote_item->create()) {
                    throw new Exception("No se pudo crear un item de la cotización.");
                }
            }

            // 3. Actualizar la cotización principal con los totales y el folio
            $this->folio = "AUT-" . str_pad($this->id_cotizacion, 4, '0', STR_PAD_LEFT);
            $this->subtotal = $total_subtotal;
            $this->descuento = $total_descuento;
            $this->iva = $total_iva;
            $this->total = ($total_subtotal - $total_descuento) + $total_iva;

            $update_query = "UPDATE " . $this->table_name . "
                             SET folio=:folio, subtotal=:subtotal, descuento=:descuento, iva=:iva, total=:total
                             WHERE id_cotizacion=:id_cotizacion";

            $update_stmt = $this->conn->prepare($update_query);
            $update_stmt->bindParam(':folio', $this->folio);
            $update_stmt->bindParam(':subtotal', $this->subtotal);
            $update_stmt->bindParam(':descuento', $this->descuento);
            $update_stmt->bindParam(':iva', $this->iva);
            $update_stmt->bindParam(':total', $this->total);
            $update_stmt->bindParam(':id_cotizacion', $this->id_cotizacion);

            if (!$update_stmt->execute()) {
                throw new Exception("No se pudo actualizar la cotización con los totales.");
            }

            // Si todo fue bien, confirmar la transacción
            $this->conn->commit();
            return true;

        } catch (Exception $e) {
            // Si algo falla, revertir la transacción
            $this->conn->rollBack();
            // Opcional: registrar el error $e->getMessage()
            return false;
        }
    }

    // Leer todas las cotizaciones
    public function read() {
        $query = "SELECT q.*, c.nombre as cliente_nombre, CONCAT(v.marca, ' ', v.modelo, ' ', v.ano) as vehiculo_info
                  FROM " . $this->table_name . " q
                  LEFT JOIN clientes c ON q.cliente_id = c.id_cliente
                  LEFT JOIN vehiculos v ON q.vehiculo_id = v.id_vehiculo
                  ORDER BY q.id_cotizacion DESC";
        $stmt = $this->conn->prepare($query);
        $stmt->execute();
        return $stmt;
    }

    // Leer una sola cotización por ID
    public function readOne() {
        $query = "SELECT q.*, c.nombre as cliente_nombre, CONCAT(v.marca, ' ', v.modelo, ' ', v.ano) as vehiculo_info
                  FROM " . $this->table_name . " q
                  LEFT JOIN clientes c ON q.cliente_id = c.id_cliente
                  LEFT JOIN vehiculos v ON q.vehiculo_id = v.id_vehiculo
                  WHERE q.id_cotizacion = ?
                  LIMIT 0,1";

        $stmt = $this->conn->prepare($query);
        $stmt->bindParam(1, $this->id_cotizacion);
        $stmt->execute();

        $row = $stmt->fetch(PDO::FETCH_ASSOC);

        if($row) {
            $this->folio = $row['folio'];
            $this->cliente_id = $row['cliente_id'];
            $this->vehiculo_id = $row['vehiculo_id'];
            $this->fecha = $row['fecha'];
            $this->validez = $row['validez'];
            $this->notas = $row['notas'];
            $this->condiciones = $row['condiciones'];
            $this->subtotal = $row['subtotal'];
            $this->descuento = $row['descuento'];
            $this->iva = $row['iva'];
            $this->total = $row['total'];
            $this->estatus = $row['estatus'];
            $this->cliente_nombre = $row['cliente_nombre'];
            $this->vehiculo_info = $row['vehiculo_info'];
            return true;
        }
        return false;
    }

    // Actualizar solo el estatus de una cotización
    public function updateStatus() {
        $query = "UPDATE " . $this->table_name . " SET estatus = :estatus WHERE id_cotizacion = :id_cotizacion";
        $stmt = $this->conn->prepare($query);

        // Limpiar datos
        $this->estatus = htmlspecialchars(strip_tags($this->estatus));
        $this->id_cotizacion = htmlspecialchars(strip_tags($this->id_cotizacion));

        // Vincular parámetros
        $stmt->bindParam(':estatus', $this->estatus);
        $stmt->bindParam(':id_cotizacion', $this->id_cotizacion);

        if ($stmt->execute()) {
            return true;
        }
        return false;
    }
}
?>
