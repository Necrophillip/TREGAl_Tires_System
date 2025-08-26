<?php
class InventoriesController {
    private $db;
    private $inventory;

    public function __construct($db) {
        $this->db = $db;
        require_once 'auth/validate_token.php';
        require_once 'models/Inventory.php';
        $this->inventory = new Inventory($this->db);
        validate_token();
    }

    // Listar todos los productos
    public function read() {
        $stmt = $this->inventory->read();
        $num = $stmt->rowCount();

        if ($num > 0) {
            $items_arr = ["records" => []];
            while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
                extract($row);
                $item = [
                    "id_producto" => $id_producto,
                    "sku" => $sku,
                    "descripcion" => $descripcion,
                    "proveedor" => $proveedor,
                    "stock" => $stock,
                    "precio_compra" => $precio_compra,
                    "precio_venta" => $precio_venta,
                    "stock_minimo" => $stock_minimo
                ];
                array_push($items_arr["records"], $item);
            }
            http_response_code(200);
            echo json_encode($items_arr);
        } else {
            http_response_code(404);
            echo json_encode(["message" => "No se encontraron productos en el inventario."]);
        }
    }

    // Obtener un solo producto
    public function readOne($id) {
        $this->inventory->id_producto = $id;
        if ($this->inventory->readOne()) {
            $item = [
                "id_producto" => $this->inventory->id_producto,
                "sku" => $this->inventory->sku,
                "descripcion" => $this->inventory->descripcion,
                "proveedor" => $this->inventory->proveedor,
                "stock" => $this->inventory->stock,
                "precio_compra" => $this->inventory->precio_compra,
                "precio_venta" => $this->inventory->precio_venta,
                "stock_minimo" => $this->inventory->stock_minimo
            ];
            http_response_code(200);
            echo json_encode($item);
        } else {
            http_response_code(404);
            echo json_encode(["message" => "Producto no encontrado."]);
        }
    }

    // Crear un nuevo producto
    public function create() {
        $data = json_decode(file_get_contents("php://input"));

        if (!empty($data->descripcion) && isset($data->stock) && isset($data->precio_venta)) {
            $this->inventory->sku = $data->sku ?? '';
            $this->inventory->descripcion = $data->descripcion;
            $this->inventory->proveedor = $data->proveedor ?? '';
            $this->inventory->stock = $data->stock;
            $this->inventory->precio_compra = $data->precio_compra ?? 0.00;
            $this->inventory->precio_venta = $data->precio_venta;
            $this->inventory->stock_minimo = $data->stock_minimo ?? 0;

            if ($this->inventory->create()) {
                http_response_code(201);
                echo json_encode(["message" => "Producto creado exitosamente.", "id_producto" => $this->inventory->id_producto]);
            } else {
                http_response_code(503);
                echo json_encode(["message" => "No se pudo crear el producto."]);
            }
        } else {
            http_response_code(400);
            echo json_encode(["message" => "Datos incompletos. Se requiere descripción, stock y precio de venta."]);
        }
    }

    // Actualizar un producto
    public function update($id) {
        $data = json_decode(file_get_contents("php://input"));

        if (!empty($id) && !empty($data->descripcion) && isset($data->stock) && isset($data->precio_venta)) {
            $this->inventory->id_producto = $id;
            $this->inventory->sku = $data->sku ?? '';
            $this->inventory->descripcion = $data->descripcion;
            $this->inventory->proveedor = $data->proveedor ?? '';
            $this->inventory->stock = $data->stock;
            $this->inventory->precio_compra = $data->precio_compra ?? 0.00;
            $this->inventory->precio_venta = $data->precio_venta;
            $this->inventory->stock_minimo = $data->stock_minimo ?? 0;

            if ($this->inventory->update()) {
                http_response_code(200);
                echo json_encode(["message" => "Producto actualizado exitosamente."]);
            } else {
                http_response_code(503);
                echo json_encode(["message" => "No se pudo actualizar el producto."]);
            }
        } else {
            http_response_code(400);
            echo json_encode(["message" => "Datos incompletos o ID de producto no proporcionado."]);
        }
    }

    // Eliminar un producto
    public function delete($id) {
        if (!empty($id)) {
            $this->inventory->id_producto = $id;
            if ($this->inventory->delete()) {
                http_response_code(200);
                echo json_encode(["message" => "Producto eliminado exitosamente."]);
            } else {
                http_response_code(503);
                echo json_encode(["message" => "No se pudo eliminar el producto."]);
            }
        } else {
            http_response_code(400);
            echo json_encode(["message" => "ID de producto no proporcionado."]);
        }
    }
}
?>
