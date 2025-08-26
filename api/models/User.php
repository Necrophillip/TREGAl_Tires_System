<?php
class User {
    // Conexión a la base de datos y nombre de la tabla
    private $conn;
    private $table_name = "usuarios";

    // Propiedades del objeto
    public $id_usuario;
    public $nombre;
    public $email;
    public $password_hash;
    public $rol;
    public $activo;

    // Constructor con la conexión a la base de datos
    public function __construct($db) {
        $this->conn = $db;
    }

    // Método para encontrar un usuario por email
    public function findByEmail($email) {
        $query = "SELECT
                    id_usuario, nombre, email, password_hash, rol, activo
                FROM
                    " . $this->table_name . "
                WHERE
                    email = :email
                LIMIT
                    0,1";

        // Preparar la consulta
        $stmt = $this->conn->prepare($query);

        // Limpiar y vincular el parámetro
        $email = htmlspecialchars(strip_tags($email));
        $stmt->bindParam(':email', $email);

        // Ejecutar la consulta
        $stmt->execute();

        // Obtener la fila
        $row = $stmt->fetch(PDO::FETCH_ASSOC);

        // Si se encontró una fila, establecer las propiedades del objeto
        if ($row) {
            $this->id_usuario = $row['id_usuario'];
            $this->nombre = $row['nombre'];
            $this->email = $row['email'];
            $this->password_hash = $row['password_hash'];
            $this->rol = $row['rol'];
            $this->activo = $row['activo'];
            return true;
        }

        return false;
    }
}
?>
