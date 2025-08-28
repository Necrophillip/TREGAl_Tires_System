-- Estructura de tablas para el módulo de Nóminas

-- Tabla: tecnicos_config
-- Almacena la configuración de pago para cada usuario que tenga el rol de 'tecnico'.
CREATE TABLE `tecnicos_config` (
  `id_config` INT AUTO_INCREMENT PRIMARY KEY,
  `usuario_id` INT NOT NULL UNIQUE,
  `tipo_pago` ENUM('salario_fijo', 'comision', 'mixto') NOT NULL,
  `monto_salario` DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Monto del salario fijo por periodo (semanal, quincenal, etc.)',
  `porcentaje_comision` DECIMAL(5,2) DEFAULT 0.00 COMMENT 'Porcentaje de comisión sobre la mano de obra realizada',
  FOREIGN KEY (`usuario_id`) REFERENCES `usuarios`(`id_usuario`) ON DELETE CASCADE
) COMMENT = 'Configuración de pago para los técnicos';

-- Tabla: nominas
-- Almacena el registro de cada cálculo de nómina generado.
CREATE TABLE `nominas` (
  `id_nomina` INT AUTO_INCREMENT PRIMARY KEY,
  `usuario_id` INT NOT NULL COMMENT 'El ID del técnico (de la tabla usuarios)',
  `fecha_inicio_periodo` DATE NOT NULL,
  `fecha_fin_periodo` DATE NOT NULL,
  `salario_base` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `comisiones` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `deducciones` DECIMAL(10,2) DEFAULT 0.00,
  `total_pagar` DECIMAL(10,2) NOT NULL,
  `fecha_generacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `estatus` ENUM('pendiente', 'pagada') DEFAULT 'pendiente',
  FOREIGN KEY (`usuario_id`) REFERENCES `usuarios`(`id_usuario`)
) COMMENT = 'Registro de nóminas generadas para los técnicos';
