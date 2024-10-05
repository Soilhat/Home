--
-- Table structure for table `bank`
--

CREATE TABLE `bank` (
    login varchar(60) NOT NULL PRIMARY KEY,
    module varchar(6) NOT NULL,
    name varchar(60),
    password varchar(70),
    website varchar(60)
);


--
-- Table structure for table `account`
--

CREATE TABLE `account` (
  `id` varchar(60) NOT NULL,
  `bank` varchar(45) DEFAULT NULL,
  `label` varchar(45) DEFAULT NULL,
  `type` varchar(45) DEFAULT NULL,
  `balance` decimal(10,2) DEFAULT NULL,
  `coming` decimal(10,2) DEFAULT NULL,
  `iban` varchar(27) DEFAULT NULL,
  `number` varchar(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
);


--
-- Table structure for table `budget`
--

CREATE TABLE `budget` (
  `id` INTEGER PRIMARY KEY,
  `label` varchar(45) DEFAULT NULL,
  `type` varchar(45) DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `start` date DEFAULT NULL,
  `end` date DEFAULT NULL,
  `fixed` INTEGER DEFAULT FALSE
);


--
-- Table structure for table `loan`
--

CREATE TABLE `loan` (
  `id` varchar(60) NOT NULL,
  `duration` int(11) DEFAULT NULL,
  `insurance_amount` decimal(10,0) DEFAULT NULL,
  `maturity_date` date DEFAULT NULL,
  `nb_payments_left` int(11) DEFAULT NULL,
  `next_payment_amount` varchar(45) DEFAULT NULL,
  `next_payment_date` date DEFAULT NULL,
  `rate` decimal(10,0) DEFAULT NULL,
  `total_amount` decimal(10,0) DEFAULT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `loan_account_FK` FOREIGN KEY (`id`) REFERENCES `account` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
);


--
-- Table structure for table `saving`
--

CREATE TABLE `saving` (
  `id` INTEGER PRIMARY KEY,
  `name` varchar(45) DEFAULT NULL UNIQUE,
  `balance` int(11) DEFAULT NULL,
  `monthly_saving` int(11) DEFAULT NULL,
  `goal` int(11) DEFAULT NULL
);

--
-- Table structure for table `transaction`
--

CREATE TABLE `transaction` (
  `id` varchar(60) NOT NULL,
  `account` varchar(60) DEFAULT NULL,
  `amount` decimal(11,2) DEFAULT NULL,
  `category` varchar(45) DEFAULT NULL,
  `date` date DEFAULT NULL,
  `label` varchar(250) DEFAULT NULL,
  `type` varchar(45) DEFAULT NULL,
  `real_date` date DEFAULT NULL,
  `value_date` date DEFAULT NULL,
  `budget_id` int(11) DEFAULT NULL,
  `saving_id` int(11) DEFAULT NULL,
  `coming` INTEGER DEFAULT FALSE,
  `comment` varchar(500) DEFAULT NULL,
  `parent` varchar(60) DEFAULT NULL,
  `internal` varchar(60) DEFAULT NULL,
  PRIMARY KEY (`id`),
  FOREIGN KEY (`account`) REFERENCES `account` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (`parent`) REFERENCES `transaction` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (`internal`) REFERENCES `transaction` (`id`) ON DELETE NO ACTION ON UPDATE CASCADE
);
