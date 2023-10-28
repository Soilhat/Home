CREATE TABLE account (
    id VARCHAR(60) PRIMARY KEY,
    bank varchar(45) ,
    label varchar(45), 
    type varchar(45) ,
    balance decimal(10,2), 
    coming decimal(10,2) ,
    iban varchar(27) ,
    number varchar(11)
)