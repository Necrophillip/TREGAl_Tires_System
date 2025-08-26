<?php
class Client {
    private $conn;
    private $table_name = "clientes";

    // Propiedades del objeto Cliente
    public $id_cliente;
    public $nombre;
    public $rfc;
    public $correo;
    public $telefono;
    public $direccion;
    public $created_at;

    public function __construct($db) {
        $this->conn = $db;
    }

    // Método para crear un nuevo cliente
    public function create() {
        $query = "INSERT INTO " . $this->table_name . " SET nombre=:nombre, rfc=:rfc, correo=:correo, telefono=:telefono, direccion=:direccion";

        $stmt = $this->conn->prepare($query);

        // Limpiar datos
        $this->nombre = htmlspecialchars(strip_tags($this->nombre));
        $this->rfc = htmlspecialchars(strip_tags($this->rfc));
        $this->correo = htmlspecialchars(strip_tags($this->correo));
        $this->telefono = htmlspecialchars(strip_tags($this->telefono));
        $this->direccion = htmlspecialchars(strip_tags($this->direccion));

        // Vincular parámetros
        $stmt->bindParam(":nombre", $this->nombre);
        $stmt->bindParam(":rfc", $this->rfc);
        $stmt->bindParam(":correo", $this->correo);
        $stmt->bindParam(":telefono", $this->telefono);
        $stmt->bindParam(":direccion", $this->direccion);

        if ($stmt->execute()) {
            $this->id_cliente = $this->conn->lastInsertId();
            return true;
        }

        return false;
    }

    // Método para leer todos los clientes
    public function read() {
        $query = "SELECT id_cliente, nombre, rfc, correo, telefono, direccion FROM " . $this->table_name . " ORDER BY nombre ASC";
        $stmt = $this->conn->prepare($query);
        $stmt->execute();
        return $stmt;
    }

    // Método para leer un solo cliente por ID
    public function readOne() {
        $query = "SELECT id_cliente, nombre, rfc, correo, telefono, direccion FROM " . $this->table_name . " WHERE id_cliente = ? LIMIT 0,1";

        $stmt = $this->conn->prepare($query);
        $stmt->bindParam(1, $this->id_cliente);
        $stmt->execute();

        $row = $stmt->fetch(PDO::FETCH_ASSOC);

        if($row) {
            $this->nombre = $row['nombre'];
            $this->rfc = $row['rfc'];
            $this->correo = $row['correo'];
            $this->telefono = $row['telefono'];
            $this->direccion = $row['direccion'];
            return true;
        }

        return false;
    }

    // Método para actualizar un cliente
    public function update() {
        $query = "UPDATE " . $this->table_name . "
                SET
                    nombre = :nombre,
                    rfc = :rfc,
                    correo = :correo,
                    telefono = :telefono,
                    direccion = :direccion
                WHERE
                    id_cliente = :id_cliente";

        $stmt = $this->conn->prepare($query);

        // Limpiar datos
        $this->nombre = htmlspecialchars(strip_tags($this->nombre));
        $this->rfc = htmlspecialchars(strip_tags($this->rfc));
        $this->correo = htmlspecialchars(strip_tags($this->correo));
        $this->telefono = htmlspecialchars(strip_tags($this->telefono));
        $this->direccion = htmlspecialchars(strip_tags($this->direccion));
        $this->id_cliente = htmlspecialchars(strip_tags($this->id_cliente));

        // Vincular parámetros
        $stmt->bindParam(':nombre', $this->nombre);
        $stmt->bindParam(':rfc', $this->rfc);
        $stmt->bindParam(':correo', $this->correo);
        $stmt->bindParam(':telefono', $this->telefono);
        $stmt->bindParam(':direccion', $this->direccion);
        $stmt->bindParam(':id_cliente', $this->id_cliente);

        if ($stmt->execute()) {
            return true;
        }

        return false;
    }

    // Método para eliminar un cliente
    public function delete() {
        $query = "DELETE FROM " . $this->table_name . " WHERE id_cliente = ?";

        $stmt = $this->conn->prepare($query);

        $this->id_cliente = htmlspecialchars(strip_tags($this->id_cliente));
        $stmt->bindParam(1, $this->id_cliente);

        if ($stmt->execute()) {
            return true;
        }

        return false;
    }
}
?>
