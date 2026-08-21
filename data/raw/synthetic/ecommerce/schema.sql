CREATE TABLE customers(
    customer_id INTEGER PRIMARY KEY,
    name VARCHAR,
    country VARCHAR
);

CREATE TABLE products(
    product_id INTEGER PRIMARY KEY,
    name VARCHAR,
    category VARCHAR,
    price DOUBLE
);

CREATE TABLE orders(
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    order_date DATE,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_items(
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    FOREIGN KEY(order_id) REFERENCES orders(order_id),
    FOREIGN KEY(product_id) REFERENCES products(product_id)
);