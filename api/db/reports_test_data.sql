-- Datos de prueba para el módulo de reportes
-- Primero, nos aseguramos de que existan los vehículos para nuestros clientes de prueba.
-- Suponemos que el cliente con id=1 y id=2 ya existen.
INSERT INTO vehiculos (cliente_id, marca, modelo, anio, vin, placas, km) VALUES
(1, 'Nissan', 'Versa', 2020, 'VIN-TEST-001', 'ABC-123', 50000),
(2, 'VW', 'Jetta', 2018, 'VIN-TEST-002', 'XYZ-789', 80000);

-- Venta 1 (Agosto 2025)
INSERT INTO cotizaciones (folio, cliente_id, vehiculo_id, fecha, validez, subtotal, descuento, iva, total, estatus)
VALUES ('AUT-TEST-01', 1, 1, '2025-08-15', 7, 2500, 0, 400, 2900, 'aceptada');
SET @quote_id = LAST_INSERT_ID();

INSERT INTO cotizacion_items (cotizacion_id, tipo, descripcion, cantidad, precio_unitario, importe) VALUES
(@quote_id, 'refaccion', 'Filtro de Aire', 1, 350, 350),
(@quote_id, 'refaccion', 'Aceite Sintetico 5L', 1, 900, 900),
(@quote_id, 'mano_obra', 'Cambio de Aceite y Filtro', 1, 500, 500),
(@quote_id, 'mano_obra', 'Revision General', 1, 750, 750);

INSERT INTO ordenes_trabajo (cotizacion_id, fecha_inicio, fecha_fin, tecnico_asignado, estatus)
VALUES (@quote_id, '2025-08-15', '2025-08-16', 'Juan Mecanico', 'finalizada');

-- Venta 2 (Julio 2025)
INSERT INTO cotizaciones (folio, cliente_id, vehiculo_id, fecha, validez, subtotal, descuento, iva, total, estatus)
VALUES ('AUT-TEST-02', 2, 2, '2025-07-10', 7, 1200, 100, 176, 1276, 'aceptada');
SET @quote_id_2 = LAST_INSERT_ID();

INSERT INTO cotizacion_items (cotizacion_id, tipo, descripcion, cantidad, precio_unitario, importe) VALUES
(@quote_id_2, 'refaccion', 'Filtro de Aire', 2, 350, 700), -- 2 filtros
(@quote_id_2, 'mano_obra', 'Diagnostico Computarizado', 1, 500, 500);

INSERT INTO ordenes_trabajo (cotizacion_id, fecha_inicio, fecha_fin, tecnico_asignado, estatus)
VALUES (@quote_id_2, '2025-07-10', '2025-07-11', 'Maria Tecnica', 'entregada');
