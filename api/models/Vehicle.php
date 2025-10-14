<?php
class Vehicle {
    private $conn;
    private $table_name = "vehiculos";

    // Propiedades del objeto Vehiculo
    public $id_vehiculo;
    public $cliente_id;
    public $marca;
    public $modelo;
    public $anio;
    public $vin;
    public $placas;
    public $km;

    // Propiedades para JOIN con cliente
    public $cliente_nombre;

    public function __construct($db) {
        $this->conn = $db;
    }

    // Crear un nuevo vehículo
    public function create() {
        $query = "INSERT INTO " . $this->table_name . " SET cliente_id=:cliente_id, marca=:marca, modelo=:modelo, anio=:anio, vin=:vin, placas=:placas, km=:km";
        $stmt = $this->conn->prepare($query);

        // Limpiar datos
        $this->cliente_id = htmlspecialchars(strip_tags($this->cliente_id));
        $this->marca = htmlspecialchars(strip_tags($this->marca));
        $this->modelo = htmlspecialchars(strip_tags($this->modelo));
        $this->vin = htmlspecialchars(strip_tags($this->vin));
        $this->placas = htmlspecialchars(strip_tags($this->placas));

        // Vincular parámetros
        $stmt->bindParam(":cliente_id", $this->cliente_id);
        $stmt->bindParam(":marca", $this->marca);
        $stmt->bindParam(":modelo", $this->modelo);
        $stmt->bindParam(":anio", $this->anio);
        $stmt->bindParam(":vin", $this->vin);
        $stmt->bindParam(":placas", $this->placas);
        $stmt->bindParam(":km", $this->km);

        if ($stmt->execute()) {
            $this->id_vehiculo = $this->conn->lastInsertId();
            return true;
        }
        return false;
    }

    // Leer todos los vehículos (con el nombre del cliente)
    public function read() {
        $query = "SELECT v.id_vehiculo, v.cliente_id, v.marca, v.modelo, v.anio, v.vin, v.placas, v.km, c.nombre as cliente_nombre
                  FROM " . $this->table_name . " v
                  LEFT JOIN clientes c ON v.cliente_id = c.id_cliente
                  ORDER BY v.marca ASC, v.modelo ASC";
        $stmt = $this->conn->prepare($query);
        $stmt->execute();
        return $stmt;
    }

    // Leer un solo vehículo por ID
    public function readOne() {
        $query = "SELECT v.id_vehiculo, v.cliente_id, v.marca, v.modelo, v.anio, v.vin, v.placas, v.km, c.nombre as cliente_nombre
                  FROM " . $this->table_name . " v
                  LEFT JOIN clientes c ON v.cliente_id = c.id_cliente
                  WHERE v.id_vehiculo = ?
                  LIMIT 0,1";

        $stmt = $this->conn->prepare($query);
        $stmt->bindParam(1, $this->id_vehiculo);
        $stmt->execute();

        $row = $stmt->fetch(PDO::FETCH_ASSOC);

        if($row) {
            $this->cliente_id = $row['cliente_id'];
            $this->marca = $row['marca'];
            $this->modelo = $row['modelo'];
            $this->anio = $row['anio'];
            $this->vin = $row['vin'];
            $this->placas = $row['placas'];
            $this->km = $row['km'];
            $this->cliente_nombre = $row['cliente_nombre'];
            return true;
        }
        return false;
    }

    // Actualizar un vehículo
    public function update() {
        $query = "UPDATE " . $this->table_name . "
                SET
                    cliente_id = :cliente_id,
                    marca = :marca,
                    modelo = :modelo,
                    anio = :anio,
                    vin = :vin,
                    placas = :placas,
                    km = :km
                WHERE
                    id_vehiculo = :id_vehiculo";

        $stmt = $this->conn->prepare($query);

        // Limpiar datos
        $this->id_vehiculo = htmlspecialchars(strip_tags($this->id_vehiculo));
        $this->cliente_id = htmlspecialchars(strip_tags($this->cliente_id));
        $this->marca = htmlspecialchars(strip_tags($this->marca));
        $this->modelo = htmlspecialchars(strip_tags($this->modelo));
        $this->vin = htmlspecialchars(strip_tags($this->vin));
        $this->placas = htmlspecialchars(strip_tags($this->placas));

        // Vincular parámetros
        $stmt->bindParam(':id_vehiculo', $this->id_vehiculo);
        $stmt->bindParam(':cliente_id', $this->cliente_id);
        $stmt->bindParam(':marca', $this->marca);
        $stmt->bindParam(':modelo', $this->modelo);
        $stmt->bindParam(':vin', $this->vin);
        $stmt->bindParam(':placas', $this->placas);

        // Tratar campos que pueden ser NULL
        if (!is_null($this->anio)) {
            $stmt->bindValue(":anio", htmlspecialchars(strip_tags($this->anio)), PDO::PARAM_INT);
        } else {
            $stmt->bindValue(":anio", null, PDO::PARAM_NULL);
        }
        if (!is_null($this->km)) {
            $stmt->bindValue(":km", htmlspecialchars(strip_tags($this->km)), PDO::PARAM_INT);
        } else {
            $stmt->bindValue(":km", null, PDO::PARAM_NULL);
        }

        if ($stmt->execute()) {
            return true;
        }
        return false;
    }

    // Eliminar un vehículo
    public function delete() {
        $query = "DELETE FROM " . $this->table_name . " WHERE id_vehiculo = ?";
        $stmt = $this->conn->prepare($query);
        $this->id_vehiculo = htmlspecialchars(strip_tags($this->id_vehiculo));
        $stmt->bindParam(1, $this->id_vehiculo);

        if ($stmt->execute()) {
            return true;
        }
        return false;
    }
}
?>
