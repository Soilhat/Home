CREATE TABLE saving (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name CHAR(50) UNIQUE NOT NULL,
    balance int(11),
    monthly_saving int(11),
    goal int(11)
);