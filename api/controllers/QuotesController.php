<?php
use Dompdf\Dompdf;
use Dompdf\Options;

class QuotesController {
    private $db;
    private $quote;

    public function __construct($db) {
        $this->db = $db;
        require_once 'auth/validate_token.php';
        require_once 'models/Quote.php';
        $this->quote = new Quote($this->db);
        validate_token();
    }

    // Crear una nueva cotización
    public function create() {
        $data = json_decode(file_get_contents("php://input"));

        // Validar datos principales
        if (
            !empty($data->cliente_id) &&
            !empty($data->vehiculo_id) &&
            !empty($data->fecha) &&
            !empty($data->items) &&
            is_array($data->items)
        ) {
            // Asignar datos al objeto cotización
            $this->quote->cliente_id = $data->cliente_id;
            $this->quote->vehiculo_id = $data->vehiculo_id;
            $this->quote->fecha = $data->fecha;
            $this->quote->validez = $data->validez ?? 7;
            $this->quote->notas = $data->notas ?? '';
            $this->quote->condiciones = $data->condiciones ?? '';
            $this->quote->estatus = $data->estatus ?? 'borrador';

            // Llamar al método create del modelo, que maneja la transacción
            if ($this->quote->create($data->items)) {
                http_response_code(201);
                echo json_encode([
                    "message" => "Cotización creada exitosamente.",
                    "id_cotizacion" => $this->quote->id_cotizacion,
                    "folio" => $this->quote->folio
                ]);
            } else {
                http_response_code(503);
                echo json_encode(["message" => "No se pudo crear la cotización."]);
            }
        } else {
            http_response_code(400);
            echo json_encode(["message" => "Datos incompletos. Se requiere cliente, vehículo, fecha y al menos un item."]);
        }
    }

    // Listar todas las cotizaciones
    public function read() {
        $stmt = $this->quote->read();
        $num = $stmt->rowCount();

        if ($num > 0) {
            $quotes_arr = ["records" => []];
            while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
                extract($row);
                $quote_item = [
                    "id_cotizacion" => $id_cotizacion,
                    "folio" => $folio,
                    "cliente_id" => $cliente_id,
                    "cliente_nombre" => $cliente_nombre,
                    "vehiculo_id" => $vehiculo_id,
                    "vehiculo_info" => $vehiculo_info,
                    "fecha" => $fecha,
                    "total" => $total,
                    "estatus" => $estatus,
                ];
                array_push($quotes_arr["records"], $quote_item);
            }
            http_response_code(200);
            echo json_encode($quotes_arr);
        } else {
            http_response_code(404);
            echo json_encode(["message" => "No se encontraron cotizaciones."]);
        }
    }

    // Obtener una sola cotización con sus items
    public function readOne($id) {
        $this->quote->id_cotizacion = $id;
        if ($this->quote->readOne()) {
            // Cargar el modelo de items
            require_once 'models/QuoteItem.php';
            $quote_item_model = new QuoteItem($this->db);
            $items_stmt = $quote_item_model->readByQuoteId($id);

            $items_arr = [];
            while ($row = $items_stmt->fetch(PDO::FETCH_ASSOC)) {
                array_push($items_arr, $row);
            }

            $quote_arr = [
                "id_cotizacion" => $this->quote->id_cotizacion,
                "folio" => $this->quote->folio,
                "cliente_id" => $this->quote->cliente_id,
                "cliente_nombre" => $this->quote->cliente_nombre,
                "vehiculo_id" => $this->quote->vehiculo_id,
                "vehiculo_info" => $this->quote->vehiculo_info,
                "fecha" => $this->quote->fecha,
                "validez" => $this->quote->validez,
                "notas" => $this->quote->notas,
                "condiciones" => $this->quote->condiciones,
                "subtotal" => $this->quote->subtotal,
                "descuento" => $this->quote->descuento,
                "iva" => $this->quote->iva,
                "total" => $this->quote->total,
                "estatus" => $this->quote->estatus,
                "items" => $items_arr
            ];

            http_response_code(200);
            echo json_encode($quote_arr);
        } else {
            http_response_code(404);
            echo json_encode(["message" => "Cotización no encontrada."]);
        }
    }

    // Actualizar el estatus de una cotización
    public function updateStatus($id) {
        $data = json_decode(file_get_contents("php://input"));

        if (!empty($id) && !empty($data->estatus)) {
            $this->quote->id_cotizacion = $id;
            $this->quote->estatus = $data->estatus;

            if ($this->quote->updateStatus()) {
                http_response_code(200);
                echo json_encode(["message" => "Estatus de la cotización actualizado."]);
            } else {
                http_response_code(503);
                echo json_encode(["message" => "No se pudo actualizar el estatus."]);
            }
        } else {
            http_response_code(400);
            echo json_encode(["message" => "ID o nuevo estatus no proporcionado."]);
        }
    }

    // Generar un PDF de la cotización
    public function generatePdf($id) {
        $this->quote->id_cotizacion = $id;
        if ($this->quote->readOne()) {
            // Cargar items
            require_once 'models/QuoteItem.php';
            $quote_item_model = new QuoteItem($this->db);
            $items_stmt = $quote_item_model->readByQuoteId($id);
            $items = $items_stmt->fetchAll(PDO::FETCH_ASSOC);

            // Generar el HTML para el PDF
            $html = $this->getQuoteHtml($this->quote, $items);

            // Usar Dompdf con manejo de errores
            try {
                $options = new Dompdf\Options();
                $options->set('isHtml5ParserEnabled', true);
                $options->set('isRemoteEnabled', true); // Necesario para algunas imágenes o fuentes remotas
                $dompdf = new Dompdf\Dompdf($options);
                $dompdf->loadHtml($html);
                $dompdf->setPaper('A4', 'portrait');
                $dompdf->render();

                // Enviar el PDF al navegador
                header('Content-Type: application/pdf');
                header('Content-Disposition: inline; filename="cotizacion-'.$this->quote->folio.'.pdf"');
                echo $dompdf->output();

            } catch (Exception $e) {
                http_response_code(500);
                echo json_encode(["message" => "Error al generar el PDF.", "error" => $e->getMessage()]);
            }

        } else {
            http_response_code(404);
            echo json_encode(["message" => "Cotización no encontrada para generar PDF."]);
        }
    }

    private function getQuoteHtml($quote, $items) {
        // Generador de HTML simple. En una app real, esto podría ser un template engine.
        $items_html = '';
        foreach ($items as $item) {
            $items_html .= '<tr>
                <td>'.htmlspecialchars($item['tipo']).'</td>
                <td>'.htmlspecialchars($item['descripcion']).'</td>
                <td style="text-align:right;">'.number_format($item['cantidad'], 2).'</td>
                <td style="text-align:right;">$'.number_format($item['precio_unitario'], 2).'</td>
                <td style="text-align:right;">$'.number_format($item['importe'], 2).'</td>
            </tr>';
        }

        return '
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Cotización '.$quote->folio.'</title>
                <style>
                    body { font-family: DejaVu Sans, sans-serif; font-size: 12px; }
                    .header { text-align: center; margin-bottom: 20px; }
                    .header h1 { margin: 0; }
                    .details { margin-bottom: 20px; }
                    .details table { width: 100%; }
                    .items-table { width: 100%; border-collapse: collapse; }
                    .items-table th, .items-table td { border: 1px solid #ccc; padding: 8px; }
                    .items-table th { background-color: #f2f2f2; }
                    .totals { float: right; width: 300px; margin-top: 20px; }
                    .totals table { width: 100%; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Autotech ERP</h1>
                    <p>Cotización de Servicio Automotriz</p>
                </div>
                <div class="details">
                    <table>
                        <tr>
                            <td><strong>Folio:</strong> '.htmlspecialchars($quote->folio).'</td>
                            <td><strong>Fecha:</strong> '.htmlspecialchars($quote->fecha).'</td>
                        </tr>
                        <tr>
                            <td><strong>Cliente:</strong> '.htmlspecialchars($quote->cliente_nombre).'</td>
                            <td><strong>Vehículo:</strong> '.htmlspecialchars($quote->vehiculo_info).'</td>
                        </tr>
                    </table>
                </div>
                <h3>Detalle de la Cotización</h3>
                <table class="items-table">
                    <thead>
                        <tr>
                            <th>Tipo</th>
                            <th>Descripción</th>
                            <th style="text-align:right;">Cantidad</th>
                            <th style="text-align:right;">P. Unitario</th>
                            <th style="text-align:right;">Importe</th>
                        </tr>
                    </thead>
                    <tbody>'.$items_html.'</tbody>
                </table>
                <div class="totals">
                    <table>
                        <tr><td><strong>Subtotal:</strong></td><td style="text-align:right;">$'.number_format($quote->subtotal, 2).'</td></tr>
                        <tr><td><strong>Descuento:</strong></td><td style="text-align:right;">-$'.number_format($quote->descuento, 2).'</td></tr>
                        <tr><td><strong>IVA (16%):</strong></td><td style="text-align:right;">$'.number_format($quote->iva, 2).'</td></tr>
                        <tr><td><h3>Total:</h3></td><td style="text-align:right;"><h3>$'.number_format($quote->total, 2).'</h3></td></tr>
                    </table>
                </div>
            </body>
            </html>
        ';
    }
}
?>
