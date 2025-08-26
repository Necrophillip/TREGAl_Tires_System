-- Base de datos para Autotech ERP

-- Tabla: clientes
CREATE TABLE `clientes` (
  `id_cliente` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre` VARCHAR(150) NOT NULL,
  `rfc` VARCHAR(20),
  `correo` VARCHAR(120) NOT NULL,
  `telefono` VARCHAR(20),
  `direccion` TEXT,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: vehiculos
CREATE TABLE `vehiculos` (
  `id_vehiculo` INT AUTO_INCREMENT PRIMARY KEY,
  `cliente_id` INT NOT NULL,
  `marca` VARCHAR(50) NOT NULL,
  `modelo` VARCHAR(50) NOT NULL,
  `anio` YEAR NOT NULL,
  `vin` VARCHAR(20) UNIQUE,
  `placas` VARCHAR(15) UNIQUE,
  `km` INT,
  FOREIGN KEY (`cliente_id`) REFERENCES `clientes`(`id_cliente`) ON DELETE CASCADE
);

-- Tabla: cotizaciones
CREATE TABLE `cotizaciones` (
  `id_cotizacion` INT AUTO_INCREMENT PRIMARY KEY,
  `folio` VARCHAR(20) UNIQUE NOT NULL,
  `cliente_id` INT NOT NULL,
  `vehiculo_id` INT NOT NULL,
  `fecha` DATE NOT NULL,
  `validez` INT DEFAULT 7,
  `notas` TEXT,
  `condiciones` TEXT,
  `subtotal` DECIMAL(10,2) NOT NULL,
  `descuento` DECIMAL(10,2) DEFAULT 0.00,
  `iva` DECIMAL(10,2) NOT NULL,
  `total` DECIMAL(10,2) NOT NULL,
  `estatus` ENUM('borrador','enviada','aceptada','rechazada','vencida') DEFAULT 'borrador',
  FOREIGN KEY (`cliente_id`) REFERENCES `clientes`(`id_cliente`),
  FOREIGN KEY (`vehiculo_id`) REFERENCES `vehiculos`(`id_vehiculo`)
);

-- Tabla: cotizacion_items
CREATE TABLE `cotizacion_items` (
  `id_item` INT AUTO_INCREMENT PRIMARY KEY,
  `cotizacion_id` INT NOT NULL,
  `tipo` ENUM('refaccion','mano_obra') NOT NULL,
  `descripcion` VARCHAR(255) NOT NULL,
  `cantidad` DECIMAL(10,2) NOT NULL,
  `precio_unitario` DECIMAL(10,2) NOT NULL,
  `descuento` DECIMAL(5,2) DEFAULT 0,
  `aplica_iva` BOOLEAN DEFAULT 1,
  `importe` DECIMAL(10,2) NOT NULL,
  FOREIGN KEY (`cotizacion_id`) REFERENCES `cotizaciones`(`id_cotizacion`) ON DELETE CASCADE
);

-- Tabla: ordenes_trabajo
CREATE TABLE `ordenes_trabajo` (
  `id_ot` INT AUTO_INCREMENT PRIMARY KEY,
  `cotizacion_id` INT NOT NULL,
  `fecha_inicio` DATE,
  `fecha_fin` DATE,
  `tecnico_asignado` VARCHAR(100),
  `estatus` ENUM('pendiente','en_proceso','finalizada','entregada') DEFAULT 'pendiente',
  FOREIGN KEY (`cotizacion_id`) REFERENCES `cotizaciones`(`id_cotizacion`)
);

-- Tabla: inventario
CREATE TABLE `inventario` (
  `id_producto` INT AUTO_INCREMENT PRIMARY KEY,
  `sku` VARCHAR(50) UNIQUE,
  `descripcion` VARCHAR(255) NOT NULL,
  `proveedor` VARCHAR(150),
  `stock` INT NOT NULL,
  `precio_compra` DECIMAL(10,2),
  `precio_venta` DECIMAL(10,2) NOT NULL,
  `stock_minimo` INT DEFAULT 0,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: usuarios
CREATE TABLE `usuarios` (
  `id_usuario` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre` VARCHAR(100) NOT NULL,
  `email` VARCHAR(100) UNIQUE NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `rol` ENUM('admin','recepcion','tecnico') NOT NULL,
  `activo` BOOLEAN DEFAULT 1
);
