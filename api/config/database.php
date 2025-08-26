<?php
class Database {
    private $host = '127.0.0.1'; // o 'localhost'
    private $db_name = 'autotech_erp';
    private $username = 'autotech_user';
    private $password = 'autotech_password';
    private $conn;

    public function getConnection() {
        $this->conn = null;

        try {
            $this->conn = new PDO('mysql:host=' . $this->host . ';dbname=' . $this->db_name, $this->username, $this->password);
            $this->conn->exec("set names utf8");
            $this->conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        } catch(PDOException $exception) {
            // En un entorno de producción, registrar el error en lugar de mostrarlo
            http_response_code(500);
            echo json_encode(['message' => 'Error de conexión a la base de datos.', 'error' => $exception->getMessage()]);
            exit(); // Terminar el script si la conexión falla
        }

        return $this->conn;
    }
}
?>
