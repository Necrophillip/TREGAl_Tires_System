<?php
// Incluir la librería JWT
require_once 'vendor/autoload.php';
use Firebase\JWT\JWT;

class UsersController {
    private $db;
    private $user;

    public function __construct($db) {
        $this->db = $db;
        // Incluir el modelo de usuario
        require_once 'models/User.php';
        $this->user = new User($this->db);
    }

    // Método para crear un nuevo usuario (registro)
    public function create() {
        // Obtener los datos del cuerpo de la solicitud
        $data = json_decode(file_get_contents("php://input"));

        // Validar que los datos no estén vacíos
        if (
            !empty($data->nombre) &&
            !empty($data->email) &&
            !empty($data->password) &&
            !empty($data->rol)
        ) {
            // Asignar valores al objeto usuario
            $this->user->nombre = $data->nombre;
            $this->user->email = $data->email;
            $this->user->rol = $data->rol;

            // Hashear la contraseña
            $this->user->password_hash = password_hash($data->password, PASSWORD_BCRYPT);

            // Crear el usuario en la base de datos
            if ($this->createUserInDb()) {
                http_response_code(201); // Created
                echo json_encode(['message' => 'Usuario creado exitosamente.']);
            } else {
                http_response_code(503); // Service Unavailable
                echo json_encode(['message' => 'No se pudo crear el usuario.']);
            }
        } else {
            http_response_code(400); // Bad Request
            echo json_encode(['message' => 'Datos incompletos.']);
        }
    }

    private function createUserInDb() {
        $query = "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (:nombre, :email, :password_hash, :rol)";
        $stmt = $this->db->prepare($query);

        // Limpiar datos
        $this->user->nombre = htmlspecialchars(strip_tags($this->user->nombre));
        $this->user->email = htmlspecialchars(strip_tags($this->user->email));
        $this->user->rol = htmlspecialchars(strip_tags($this->user->rol));

        // Vincular parámetros
        $stmt->bindParam(':nombre', $this->user->nombre);
        $stmt->bindParam(':email', $this->user->email);
        $stmt->bindParam(':password_hash', $this->user->password_hash);
        $stmt->bindParam(':rol', $this->user->rol);

        if ($stmt->execute()) {
            return true;
        }
        return false;
    }

    // Método para el login de usuario
    public function login() {
        $data = json_decode(file_get_contents("php://input"));

        if (!empty($data->email) && !empty($data->password)) {
            // Buscar al usuario por email
            if ($this->user->findByEmail($data->email)) {
                // Verificar si el usuario está activo
                if ($this->user->activo) {
                    // Verificar la contraseña
                    if (password_verify($data->password, $this->user->password_hash)) {

                        // La configuración del token ya está cargada en index.php

                        $iat = time();
                        $exp = $iat + JWT_EXP_SECONDS;

                        $token_payload = [
                            "iss" => JWT_ISS,
                            "aud" => JWT_AUD,
                            "iat" => $iat,
                            "nbf" => $iat, // Not before
                            "exp" => $exp,
                            "data" => [
                                "id" => $this->user->id_usuario,
                                "nombre" => $this->user->nombre,
                                "email" => $this->user->email,
                                "rol" => $this->user->rol
                            ]
                        ];

                        // Generar el JWT
                        $jwt = JWT::encode($token_payload, JWT_KEY, 'HS256');

                        http_response_code(200); // OK
                        echo json_encode([
                            "message" => "Login exitoso.",
                            "jwt" => $jwt,
                            "user" => [
                                "id" => $this->user->id_usuario,
                                "nombre" => $this->user->nombre,
                                "email" => $this->user->email,
                                "rol" => $this->user->rol
                            ]
                        ]);
                    } else {
                        http_response_code(401); // Unauthorized
                        echo json_encode(['message' => 'Contraseña incorrecta.']);
                    }
                } else {
                    http_response_code(401); // Unauthorized
                    echo json_encode(['message' => 'El usuario está inactivo.']);
                }
            } else {
                http_response_code(404); // Not Found
                echo json_encode(['message' => 'El usuario no existe.']);
            }
        } else {
            http_response_code(400); // Bad Request
            echo json_encode(['message' => 'Datos de login incompletos.']);
        }
    }
}
?>
