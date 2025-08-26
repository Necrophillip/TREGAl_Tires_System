<?php
class Inventory {
    private $conn;
    private $table_name = "inventario";

    // Propiedades del objeto
    public $id_producto;
    public $sku;
    public $descripcion;
    public $proveedor;
    public $stock;
    public $precio_compra;
    public $precio_venta;
    public $stock_minimo;
    public $created_at;

    public function __construct($db) {
        $this->conn = $db;
    }

    // Crear un nuevo producto en el inventario
    public function create() {
        $query = "INSERT INTO " . $this->table_name . " SET sku=:sku, descripcion=:descripcion, proveedor=:proveedor, stock=:stock, precio_compra=:precio_compra, precio_venta=:precio_venta, stock_minimo=:stock_minimo";
        $stmt = $this->conn->prepare($query);

        // Limpiar datos
        $this->sku = htmlspecialchars(strip_tags($this->sku));
        $this->descripcion = htmlspecialchars(strip_tags($this->descripcion));
        $this->proveedor = htmlspecialchars(strip_tags($this->proveedor));
        $this->stock = htmlspecialchars(strip_tags($this->stock));
        $this->precio_compra = htmlspecialchars(strip_tags($this->precio_compra));
        $this->precio_venta = htmlspecialchars(strip_tags($this->precio_venta));
        $this->stock_minimo = htmlspecialchars(strip_tags($this->stock_minimo));

        // Vincular parámetros
        $stmt->bindParam(":sku", $this->sku);
        $stmt->bindParam(":descripcion", $this->descripcion);
        $stmt->bindParam(":proveedor", $this->proveedor);
        $stmt->bindParam(":stock", $this->stock);
        $stmt->bindParam(":precio_compra", $this->precio_compra);
        $stmt->bindParam(":precio_venta", $this->precio_venta);
        $stmt->bindParam(":stock_minimo", $this->stock_minimo);

        if ($stmt->execute()) {
            $this->id_producto = $this->conn->lastInsertId();
            return true;
        }
        return false;
    }

    // Leer todos los productos del inventario
    public function read() {
        $query = "SELECT * FROM " . $this->table_name . " ORDER BY descripcion ASC";
        $stmt = $this->conn->prepare($query);
        $stmt->execute();
        return $stmt;
    }

    // Leer un solo producto por ID
    public function readOne() {
        $query = "SELECT * FROM " . $this->table_name . " WHERE id_producto = ? LIMIT 0,1";
        $stmt = $this->conn->prepare($query);
        $stmt->bindParam(1, $this->id_producto);
        $stmt->execute();

        $row = $stmt->fetch(PDO::FETCH_ASSOC);

        if($row) {
            $this->sku = $row['sku'];
            $this->descripcion = $row['descripcion'];
            $this->proveedor = $row['proveedor'];
            $this->stock = $row['stock'];
            $this->precio_compra = $row['precio_compra'];
            $this->precio_venta = $row['precio_venta'];
            $this->stock_minimo = $row['stock_minimo'];
            return true;
        }
        return false;
    }

    // Actualizar un producto
    public function update() {
        $query = "UPDATE " . $this->table_name . "
                SET
                    sku = :sku,
                    descripcion = :descripcion,
                    proveedor = :proveedor,
                    stock = :stock,
                    precio_compra = :precio_compra,
                    precio_venta = :precio_venta,
                    stock_minimo = :stock_minimo
                WHERE
                    id_producto = :id_producto";

        $stmt = $this->conn->prepare($query);

        // Limpiar datos
        $this->id_producto = htmlspecialchars(strip_tags($this->id_producto));
        $this->sku = htmlspecialchars(strip_tags($this->sku));
        $this->descripcion = htmlspecialchars(strip_tags($this->descripcion));
        $this->proveedor = htmlspecialchars(strip_tags($this->proveedor));
        $this->stock = htmlspecialchars(strip_tags($this->stock));
        $this->precio_compra = htmlspecialchars(strip_tags($this->precio_compra));
        $this->precio_venta = htmlspecialchars(strip_tags($this->precio_venta));
        $this->stock_minimo = htmlspecialchars(strip_tags($this->stock_minimo));

        // Vincular parámetros
        $stmt->bindParam(':id_producto', $this->id_producto);
        $stmt->bindParam(':sku', $this->sku);
        $stmt->bindParam(':descripcion', $this->descripcion);
        $stmt->bindParam(':proveedor', $this->proveedor);
        $stmt->bindParam(':stock', $this->stock);
        $stmt->bindParam(':precio_compra', $this->precio_compra);
        $stmt->bindParam(':precio_venta', $this->precio_venta);
        $stmt->bindParam(':stock_minimo', $this->stock_minimo);

        if ($stmt->execute()) {
            return true;
        }
        return false;
    }

    // Eliminar un producto
    public function delete() {
        $query = "DELETE FROM " . $this->table_name . " WHERE id_producto = ?";
        $stmt = $this->conn->prepare($query);
        $this->id_producto = htmlspecialchars(strip_tags($this->id_producto));
        $stmt->bindParam(1, $this->id_producto);

        if ($stmt->execute()) {
            return true;
        }
        return false;
    }
}
?>
