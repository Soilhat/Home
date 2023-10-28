CREATE TABLE budget (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    label varchar(45), 
    type varchar(45) ,
    amount int,
    start date,
    end date
)