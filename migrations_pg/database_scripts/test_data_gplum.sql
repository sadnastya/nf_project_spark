set schema 'student156';

INSERT INTO account_type (id, type) VALUES
  (1, 'credit'),
  (2, 'debit');


INSERT INTO account_status (id, status) VALUES
  (1, 'open'),
  (2, 'pending'),
  (3, 'closed'),
  (4, 'frozen');


INSERT INTO currency (id, full_name) VALUES
  ('RUB', 'Russian Ruble');


INSERT INTO clients (name, surname, date_of_birth, gender, phone_number, email) VALUES
  ( 'Павел', 'Никитин', '1981-02-15', 'M', 654321098, 'pavel.nikitin@example.ru'),
  ('Анастасия', 'Васильева', '1996-03-20', 'F', 876543210, 'anastasia.vasilieva@example.ru'),
  ( 'Игорь', 'Кузьмин', '1979-04-12', 'M', 342187654, 'igor.kuzmin@example.ru'),
  ( 'Юлия', 'Михайлова', '1991-05-25', 'F', 219876543, 'yulia.mikhaylova@example.ru'),
  ( 'Вадим', 'Сергеев', '1984-06-18', 'M', 765432109, 'vadim.sergeev@example.ru'),
  ( 'Ксения', 'Иванова', '1992-07-22', 'F', 982176543, 'ksenia.ivanova@example.ru'),
  ( 'Денис', 'Петров', '1987-08-15', 'M', 753219876, 'denis.petrov@example.ru'),
  ( 'Татьяна', 'Сидорова', '1990-09-28', 'F', 654398721, 'tatyana.sidorova@example.ru'),
  ( 'Алексей', 'Кузнецов', '1983-10-20', 'M', 982135764, 'aleksey.kuznetsov@example.ru'),
  ( 'Оксана', 'Николаева', '1993-11-12', 'F', 219854321, 'oksana.nikolaeva@example.ru'),
  ( 'Роман', 'Смирнов', '1989-12-25', 'M', 765943218, 'roman.smirnov@example.ru'),
  ( 'Евгения', 'Васильева', '1994-01-18', 'F', 876512093, 'evgeniya.vasilieva@example.ru'),
  ( 'Константин', 'Павлов', '1988-02-22', 'M', 342109876, 'konstantin.pavlov@example.ru'),
  ( 'Алина', 'Михайлова', '1995-03-15', 'F', 219876543, 'alina.mikhaylova@example.ru'),
  ( 'Дмитрий', 'Сергеев', '1986-04-12', 'M', 765432109, 'dmitry.sergeev@example.ru'),
  ( 'Наталья', 'Иванова', '1991-05-25', 'F', 982176543, 'natalya.ivanova@example.ru'),
  ( 'Владислав', 'Никитин', '1987-06-18', 'M', 753219876, 'vladislav.nikitin@example.ru'),
  ( 'Юлия', 'Васильева', '1992-07-22', 'F', 654398721, 'yulia.vasilieva@example.ru'),
  ( 'Иван', 'Кузьмин', '1988-08-15', 'M', 982135764, 'ivan.kuzmin@example.ru'),
  ( 'Ольга', 'Сидорова', '1993-09-28', 'F', 219854321, 'olga.sidorova@example.ru'),
  ( 'Сергей', 'Петров', '1989-10-20', 'M', 765943218, 'sergey.petrov@example.ru');


INSERT INTO accounts (client_id, type, status, balance, currency)
VALUES
  (1, 1, 1, 1500.00, 'RUB'),
  (3, 2, 1, 250.00, 'RUB'),
  (17, 1, 1, 10000.00, 'RUB'),
  (2, 2, 1, 5000.00, 'RUB'),
  (4, 1, 1, 4500.00, 'RUB'),
  (5, 2, 1, 2000.00, 'RUB'),
  (12, 1, 1, 12000.00, 'RUB'),
  (9, 2, 1, 3500.00, 'RUB'),
  (17, 1, 1, 8000.00, 'RUB'),
  (1, 2, 1, 6000.00, 'RUB');

INSERT INTO sellers(name, inn, kpp, ogrn, okpo, address, phone, email)
VALUES
    ('ООО "Лента"','987654321012','987654321','987654321012345','9876543210','Москва, ул. Ломоносова, д. 11','+7 (495) 987-65-43','info@lenta.ru'),
    ('ООО "Перекресток"','623456789012','623456789','123466789012345','6234567890','Москва, ул. Кошкина, д. 22','+7 (495) 123-45-67','info@perekrestok.ru');

insert into terminal_type (id, type) values
	(1, 'desk'),
	(2, 'self-service'),
    (3, 'online');


INSERT INTO terminals(seller_id, type, created_at)
VALUES
  (2, 2, '2022-01-02'),
  (1, 3, '2022-02-03'),
  (1, 1, '2022-03-04'),
  (2, 2, '2022-04-05'),
  (1, 3, '2022-05-06'),
  (1, 1, '2022-06-07'),
  (2, 2, '2022-07-08'),
  (1, 3, '2022-08-09'),
  (1, 1, '2022-09-10'),
  (1, 2, '2022-10-11');



INSERT INTO transaction_status (id, status) VALUES
    (1, 'success'),
    (2, 'processing'),
    (3, 'failed');


INSERT INTO transactions (terminal_id, account_id, transaction_date, amount, currency, status)
VALUES
  (8, 9, '2023-02-15 18:00:00', 4200.00, 'RUB',2),
  (7, 3, '2023-03-20 10:00:00', 300.00,  'RUB',1),
  (6, 5, '2023-04-05 16:00:00', -1000.00, 'RUB',3),
  (5, 2, '2023-05-01 12:00:00', 5000.00, 'RUB',1),
  (4, 1, '2023-06-12 14:00:00', 8000.00, 'RUB',1),
  (3, 8, '2023-07-22 10:00:00', 3500.00, 'RUB',3),
  (2, 6, '2023-08-15 16:00:00', 4500.00, 'RUB',1),
  (1, 4, '2023-09-01 12:00:00', 6500.00, 'RUB',1),
  (8, 7, '2023-10-25 14:00:00', 200.00, 'RUB',2),
  (9, 3, '2023-11-05 10:00:00', 10000.00, 'RUB',1);