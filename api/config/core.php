<?php
// Habilitar la visualización de errores para depuración
ini_set('display_errors', 1);
error_reporting(E_ALL);

// --- Configuración de JWT (JSON Web Token) ---

// Clave secreta para firmar el token.
// ¡IMPORTANTE! Cambiar esto por una cadena larga, aleatoria y segura en un entorno de producción.
define('JWT_KEY', "TREGAL3105_AUTOTECH_ERP_SECRET_KEY");

// Emisor del token (generalmente el dominio de tu aplicación)
define('JWT_ISS', "http://autotech.erp");

// Audiencia del token (generalmente el dominio de tu aplicación)
define('JWT_AUD', "http://autotech.erp");

// Hora de emisión del token (se establece al momento de crear el token)
// define('JWT_IAT', time()); // No es necesario como constante, se calcula al vuelo

// "Not Before" (el token no es válido antes de esta hora, se calcula al vuelo)
// define('JWT_NBF', time()); // No es necesario como constante, se calcula al vuelo

// Tiempo de expiración del token en segundos (ej. 1 hora = 3600, 24 horas = 86400)
define('JWT_EXP_SECONDS', (60 * 60 * 24)); // 24 horas

?>
