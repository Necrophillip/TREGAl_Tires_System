#!/bin/bash
set -e

# Actualizar lista de paquetes
sudo apt-get update

# Instalar PHP y extensiones básicas
sudo apt-get install -y php-cli php-mysql php-curl php-xml php-mbstring unzip

# Instalar MySQL o MariaDB (dependiendo de lo que necesites)
sudo apt-get install -y mariadb-server mariadb-client
