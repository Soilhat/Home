CREATE TABLE loan (
    id varchar(60) PRIMARY KEY,
    duration int(11) ,
    insurance_amount decimal(10,0) ,
    maturity_date date ,
    nb_payments_left int(11) ,
    next_payment_amount varchar(45) ,
    next_payment_date date ,
    rate decimal(10,0) ,
    total_amount decimal(10,0) ,
    FOREIGN KEY (id) REFERENCES account(id)
)