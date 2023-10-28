CREATE Function to_currency(number INT)
RETURNS VARCHAR(10)
RETURN CONCAT(FORMAT(IFNULL(number,0), 2, 'fr_FR'), '€');