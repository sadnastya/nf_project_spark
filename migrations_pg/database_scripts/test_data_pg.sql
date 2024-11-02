INSERT INTO bank1.account_type (id, type) VALUES
  (1, 'credit'),
  (2, 'debit');


INSERT INTO bank1.account_status (id, status) VALUES
  (1, 'active'),
  (2, 'inactive'),
  (3, 'closed');


INSERT INTO bank1.currency (id, full_name) VALUES
  ('RUB', 'Russian Ruble');


INSERT INTO bank1.clients (name, surname, date_of_birth, gender, phone_number, email) VALUES
  ( 'Иван', 'Иванов', '1990-01-01', 'M', 123456789, 'ivan.ivanov@example.ru'),
  ('Мария', 'Петрова', '1995-06-01', 'F', 987654321, 'maria.petrova@example.ru'),
  ( 'Сергей', 'Смирнов', '1980-03-01', 'M', 555123456, 'sergey.smirnov@example.ru'),
  ( 'Екатерина', 'Кузнецова', '1992-09-01', 'F', 666789012, 'ekaterina.kuznetsova@example.ru'),
  ( 'Алексей', 'Попов', '1985-05-01', 'M', 777890123, 'aleksey.popov@example.ru'),
  ( 'Дмитрий', 'Соколов', '1991-02-01', 'M', 888901234, 'dmitry.sokolov@example.ru'),
  ( 'Наталья', 'Иванова', '1988-08-01', 'F', 999012345, 'natalia.ivanova@example.ru'),
  ( 'Михаил', 'Павлов', '1982-04-01', 'M', 111234567, 'mikhail.pavlov@example.ru'),
  ( 'Ольга', 'Сергеева', '1994-10-01', 'F', 222345678, 'olga.sergeeva@example.ru'),
  ( 'Владимир', 'Николаев', '1986-07-01', 'M', 333456789, 'vladimir.nikolaev@example.ru'),
  ( 'Александр', 'Михайлов', '1990-02-01', 'M', 444123456, 'alexander.mikhailov@example.ru'),
  ( 'Елена', 'Сергеева', '1995-07-01', 'F', 666789012, 'elena.sergeeva@example.ru'),
  ( 'Дмитрий', 'Николаев', '1980-04-01', 'M', 777890123, 'dmitry.nikolaev@example.ru'),
  ( 'Наталья', 'Петрова', '1992-10-01', 'F', 888901234, 'natalia.petrova@example.ru'),
  ( 'Михаил', 'Иванов', '1985-06-01', 'M', 999012345, 'mikhail.ivanov@example.ru'),
  ( 'Ольга', 'Соколова', '1991-03-01', 'F', 111234567, 'olga.sokolova@example.ru'),
  ( 'Владимир', 'Павлов', '1982-05-01', 'M', 222345678, 'vladimir.pavlov@example.ru'),
  ( 'Екатерина', 'Кузнецова', '1994-11-01', 'F', 333456789, 'ekaterina.kuznetsova@example.ru'),
  ( 'Сергей', 'Смирнов', '1986-08-01', 'M', 444567890, 'sergey.smirnov@example.ru'),
  ( 'Мария', 'Иванова', '1993-09-01', 'F', 555678901, 'maria.ivanova@example.ru');


INSERT INTO bank1.accounts (client_id, type, status, balance, currency)
VALUES
  (1, 2, 1, 50000.00, 'RUB'),
  (3, 1, 1, 20000.00, 'RUB'),
  (17, 2, 1, 80000.00, 'RUB'),
  (2, 1, 1, 15000.00, 'RUB'),
  (4, 2, 1, 30000.00, 'RUB'),
  (5, 1, 1, 25000.00, 'RUB'),
  (12, 2, 1, 100000.00, 'RUB'),
  (9, 1, 1, 18000.00, 'RUB'),
  (17, 2, 1, 60000.00, 'RUB'),
  (1, 1, 1, 12000.00, 'RUB');

INSERT INTO bank1.merchants(name, inn, kpp, ogrn, okpo, address, phone, email)
VALUES (
  'ООО "Магнит"',
  '123456789012',
  '123456789',
  '123456789012345',
  '1234567890',
  'Москва, ул. Ленина, д. 1',
  '+7 (495) 123-45-67',
  'info@magnit.ru'
);

insert into bank1.terminal_type (id, type) values
	(1, 'offline'),
	(2, 'online');

insert into bank1.terminal_status (id, status) values
	(1, 'active'),
	(2, 'inactive');


INSERT INTO bank1.terminals (merchant_id, type, status, created_at)
VALUES
  (1, 1, 1, '2022-01-01'),
  (1, 2, 1, '2022-02-01'),
  (1, 1, 1, '2022-03-01'),
  (1, 2, 1, '2022-04-01'),
  (1, 2, 1, '2022-05-01'),
  (1, 1, 1, '2022-06-01'),
  (1, 1, 1, '2022-07-01'),
  (1, 2, 1, '2022-08-01'),
  (1, 1, 1, '2022-09-01'),
  (1, 1, 1, '2022-10-01');



INSERT INTO bank1.transaction_status (id, status) VALUES
    (1, 'successful'),
    (2, 'pending'),
    (3, 'rejected');


INSERT INTO bank1.transactions (terminal_id, account_id, transaction_date, amount, currency, status)
VALUES
  (1, 1, '2022-01-01 12:00:00', 1000.00, 'RUB',1),
  (2, 2, '2022-01-02 14:00:00', 500.00,  'RUB',1),
  (1, 1, '2022-01-03 10:00:00', -200.00, 'RUB',1),
  (3, 4, '2022-01-04 16:00:00', 1500.00, 'RUB',1),
  (2, 5, '2022-01-05 12:00:00', 1000.00, 'RUB',1),
  (1, 6, '2022-01-06 14:00:00', 3000.00, 'RUB',1),
  (4, 6, '2022-01-07 10:00:00', 2500.00, 'RUB',3),
  (3, 7, '2022-01-08 16:00:00', 2000.00, 'RUB',1),
  (2, 8, '2022-01-09 12:00:00', 1200.00, 'RUB',1),
  (1, 1, '2022-01-10 14:00:00', 1500.00, 'RUB',1);