CREATE TABLE transaction (
    id varchar(60) PRIMARY KEY,
    account varchar(60),
    amount decimal(11,2), 
    category varchar(45) ,
    date date ,
    label varchar(45) ,
    type varchar(45) ,
    real_date date ,
    value_date date,
    spending int,
    FOREIGN KEY (account) REFERENCES account(id)
    FOREIGN KEY (spending) REFERENCES spending(id)
)