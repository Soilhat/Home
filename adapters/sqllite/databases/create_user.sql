CREATE TABLE `user` (
  `id` INTEGER PRIMARY KEY,
  `username` varchar(60) DEFAULT NULL,
  `password` varchar(100) DEFAULT NULL,
  `refreshed` datetime DEFAULT NULL
);