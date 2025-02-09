CREATE TABLE `user`(
    `user_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `telegram_id` BIGINT NOT NULL,
    `public_id` BIGINT NOT NULL,
    `is_admin` BOOLEAN NOT NULL,
    `nickname` BIGINT NOT NULL,
    `name` TEXT NOT NULL,
    `surname` TEXT NOT NULL,
    `city_id` BIGINT NOT NULL,
    `first_contact` DATETIME NOT NULL,
    `last_contact` DATETIME NOT NULL,
    `lichess_rating` BIGINT NOT NULL,
    `chesscom_rating` BIGINT NOT NULL,
    `rep_rating` BIGINT NOT NULL
);
ALTER TABLE
    `user` ADD UNIQUE `user_telegram_id_unique`(`telegram_id`);
CREATE TABLE `city`(
    `city_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `name` TEXT NOT NULL,
    `tg_channel` TEXT NOT NULL,
    `timetable_message_id` BIGINT NOT NULL,
    `timetable_photo` TEXT NOT NULL
);
ALTER TABLE
    `city` ADD UNIQUE `city_tg_channel_unique`(`tg_channel`);
CREATE TABLE `tournament`(
    `tournament_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `tg_channel` TEXT NOT NULL,
    `message_id` BIGINT NOT NULL,
    `city_id` BIGINT NOT NULL,
    `summary` TEXT NOT NULL,
    `date_time` DATETIME NOT NULL,
    `address` TEXT NOT NULL
);
CREATE TABLE `user_in_tournament`(
    `user_in_tournament_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `tournament_id` BIGINT NOT NULL,
    `user_id` BIGINT NOT NULL,
    `nickname` TEXT NOT NULL,
    `rating_before` BIGINT NOT NULL,
    `rating_after` BIGINT NOT NULL
);
CREATE TABLE `game`(
    `game_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `white_user_id` BIGINT NOT NULL,
    `black_user_id` BIGINT NOT NULL,
    `tournament_id` BIGINT NOT NULL,
    `user_in_tournament_id` BIGINT NOT NULL,
    `round` BIGINT NOT NULL,
    `desk_number` BIGINT NOT NULL,
    `result` BIGINT NOT NULL,
    `white_rating_change` BIGINT NOT NULL,
    `black_rating_change` BIGINT NOT NULL
);
CREATE TABLE `payment`(
    `payment_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `product_id` BIGINT NOT NULL,
    `user_id` BIGINT NOT NULL,
    `sum` BIGINT NOT NULL,
    `date_time` DATETIME NOT NULL
);
CREATE TABLE `product`(
    `product_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `description` BIGINT NOT NULL
);
ALTER TABLE
    `user_in_tournament` ADD CONSTRAINT `user_in_tournament_tournament_id_foreign` FOREIGN KEY(`tournament_id`) REFERENCES `tournament`(`tournament_id`);
ALTER TABLE
    `tournament` ADD CONSTRAINT `tournament_city_id_foreign` FOREIGN KEY(`city_id`) REFERENCES `city`(`city_id`);
ALTER TABLE
    `user_in_tournament` ADD CONSTRAINT `user_in_tournament_user_id_foreign` FOREIGN KEY(`user_id`) REFERENCES `user`(`user_id`);
ALTER TABLE
    `game` ADD CONSTRAINT `game_black_user_id_foreign` FOREIGN KEY(`black_user_id`) REFERENCES `user`(`user_id`);
ALTER TABLE
    `payment` ADD CONSTRAINT `payment_product_id_foreign` FOREIGN KEY(`product_id`) REFERENCES `product`(`product_id`);
ALTER TABLE
    `game` ADD CONSTRAINT `game_tournament_id_foreign` FOREIGN KEY(`tournament_id`) REFERENCES `tournament`(`tournament_id`);
ALTER TABLE
    `payment` ADD CONSTRAINT `payment_user_id_foreign` FOREIGN KEY(`user_id`) REFERENCES `user`(`user_id`);
ALTER TABLE
    `game` ADD CONSTRAINT `game_user_in_tournament_id_foreign` FOREIGN KEY(`user_in_tournament_id`) REFERENCES `user_in_tournament`(`user_in_tournament_id`);
ALTER TABLE
    `game` ADD CONSTRAINT `game_white_user_id_foreign` FOREIGN KEY(`white_user_id`) REFERENCES `user`(`user_id`);
ALTER TABLE
    `user` ADD CONSTRAINT `user_city_id_foreign` FOREIGN KEY(`city_id`) REFERENCES `city`(`city_id`);