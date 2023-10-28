CREATE Function to_prct(number INT)
RETURNS VARCHAR(10)
RETURN CONCAT(FORMAT(IFNULL(number,0), 0, 'fr_FR'), '%');