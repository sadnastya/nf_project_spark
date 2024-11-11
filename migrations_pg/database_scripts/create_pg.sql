create schema if not exists bank1;


create table if not exists bank1.transaction_type(
	id integer primary key,
	type varchar);

create table if not exists bank1.transaction_status(
	id integer primary key,
	status varchar);

create table if not exists bank1.account_status(
	id integer primary key,
	status varchar);

create table if not exists bank1.account_type(
	id integer primary key,
	type varchar);

create table if not exists bank1.currency(
	id varchar(3) primary key,
	full_name varchar);

create table if not exists bank1.clients(
    id serial primary key,
	name varchar(20) not null,
	surname varchar(40) not null,
	date_of_birth date not null,
	gender varchar(1),
	phone_number bigint not null,
	email varchar(255) not null);

create table if not exists bank1.accounts(
	id serial primary key,
	client_id integer references bank1.clients(id),
	type integer references bank1.account_type(id),
	status integer references bank1.account_status(id),
	balance decimal not null,
	currency varchar(3) references bank1.currency(id)
	);

create table if not exists bank1.merchants (
    id serial primary key,
    name varchar(255) not null,
    inn varchar(12) not null,
    kpp varchar(9) not null,
    ogrn varchar(15) not null,
    okpo varchar(10),
    address varchar(255) NOT NULL,
    phone varchar(20),
    email varchar(100),
    created_at date not null default current_date
);

create table if not exists bank1.terminal_type(
	id integer primary key,
	type varchar);

create table if not exists bank1.terminal_status(
	id integer primary key,
	status varchar);

create table if not exists bank1.terminals(
	id serial primary key,
	merchant_id integer references bank1.merchants(id),
	type integer references bank1.terminal_type(id),
	status integer references bank1.terminal_status(id),
	created_at date);

create table if not exists bank1.transactions(
	id serial primary key,
	terminal_id integer references bank1.terminals(id),
	account_id integer references bank1.accounts(id),
	transaction_date timestamp not null,
	amount decimal not null,
	currency varchar(3) references bank1.currency(id),
	status integer references bank1.transaction_status(id)
	);