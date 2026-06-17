CREATE DATABASE Sales_Management_System;
GO
USE Sales_Management_System;

-- Branches Table
CREATE TABLE branches (
    branch_id INT PRIMARY KEY,
    branch_name VARCHAR(100),
    branch_admin_name VARCHAR(100)
);

-- Users Table
CREATE TABLE users (
    user_id INT PRIMARY KEY,
    username VARCHAR(100),
    password VARCHAR(255),
    branch_id INT NULL,
    role VARCHAR(20) CHECK (role IN ('Super Admin','Admin')) NOT NULL,
    email VARCHAR(255) UNIQUE,
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
);

-- Customer Sales Table
CREATE TABLE customer_sales (
    sale_id INT PRIMARY KEY,
    branch_id INT,
    date DATE,
    name VARCHAR(100),
    mobile_number VARCHAR(15) UNIQUE,
    product_name VARCHAR(30),
    gross_sales DECIMAL(12,2),
    received_amount DECIMAL(12,2) DEFAULT 0,
    pending_amount AS (gross_sales - received_amount),
    status VARCHAR(10) DEFAULT 'Open' CHECK (status IN ('Open','Close')),
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
);

-- Payment Splits Table
CREATE TABLE payment_splits (
    payment_id INT PRIMARY KEY,
    sale_id INT,
    payment_date DATE,
    amount_paid DECIMAL(12,2),
    payment_method VARCHAR(50),
    FOREIGN KEY (sale_id) REFERENCES customer_sales(sale_id)
);

-- Trigger to auto-update received_amount
GO
CREATE TRIGGER update_received_amount
ON payment_splits
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE cs
    SET cs.received_amount = (
        SELECT SUM(ps.amount_paid)
        FROM payment_splits ps
        WHERE ps.sale_id = cs.sale_id
    )
    FROM customer_sales cs
    WHERE cs.sale_id IN (SELECT DISTINCT sale_id FROM inserted);
END;
GO


DELETE FROM payment_splits;
DELETE FROM customer_sales;
DELETE FROM users;
DELETE FROM branches;

USE Sales_Management_System;
SELECT TOP 5 * FROM branches;
SELECT TOP 5 * FROM users;
SELECT TOP 5 * FROM customer_sales;
SELECT TOP 5 * FROM payment_splits;

SELECT * FROM customer_sales cs 
JOIN branches b ON cs.branch_id=b.branch_id 
WHERE b.branch_name='Chennai'

SELECT 
    cs.sale_id,
    cs.date,
    cs.name,
    cs.mobile_number,
    cs.product_name,
    cs.gross_sales,
    cs.received_amount,
    cs.pending_amount,
    cs.status,
    b.branch_name
FROM customer_sales cs
JOIN branches b ON cs.branch_id = b.branch_id
WHERE b.branch_name = 'Chennai'
