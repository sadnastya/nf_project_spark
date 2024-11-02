set schema 'student156';

create table if not exists transaction_type(
	id integer primary key,
	type varchar)
    distributed replicated;

create table if not exists transaction_status(
	id integer primary key,
	status varchar)
    distributed replicated;

create table if not exists account_status(
	id integer primary key,
	status varchar)
    distributed replicated;

create table if not exists account_type(
	id integer primary key,
	type varchar)
    distributed replicated;

create table if not exists currency(
	id varchar(3) primary key,
	full_name varchar)
    distributed replicated;

create table if not exists clients(
    id serial primary key,
	name varchar(20) not null,
	surname varchar(40) not null,
	date_of_birth date not null,
	gender varchar(1),
	phone_number bigint not null,
	email varchar(255) not null)
    distributed by (id);

create table if not exists accounts(
	id serial primary key,
	client_id integer references clients(id),
	type integer references account_type(id),
	status integer references account_status(id),
	balance decimal not null,
	currency varchar(3) references currency(id)
	)
    distributed by (id);

CREATE TABLE sellers (
    id serial primary key,
    name varchar(255) not null,
    inn varchar(12) not null,
    kpp varchar(9) not null,
    ogrn varchar(15) not null,
    okpo varchar(10),
    address varchar(255) NOT NULL,
    phone varchar(20),
    email varchar(100),
    created_at date not null default current_date)
    distributed by (id);

create table if not exists terminal_type(
	id integer primary key,
	type varchar)
    distributed replicated;


create table if not exists terminals(
	id serial primary key,
	seller_id integer references merchants(id),
	type integer references terminal_type(id),
	created_at date)
    distributed by (id);

create table if not exists transactions(
	id serial primary key,
	terminal_id integer references terminals(id),
	account_id integer references accounts(id),
	transaction_date timestamp not null,
	amount decimal not null,
	currency varchar(3) references currency(id),
	status integer references transaction_status(id)
	)
    distributed by (id);