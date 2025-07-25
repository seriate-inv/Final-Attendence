CREATE DATABASE entry_exit_db;

USE entry_exit_db;

CREATE TABLE entries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    type VARCHAR(10),
    image_path VARCHAR(255),
    gps_location VARCHAR(100),
    timestamp DATETIME
);
select * from entries;

-- ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root';
-- FLUSH PRIVILEGES;
