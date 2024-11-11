create schema bank2;

create table bank2.transaction_type(
    id integer primary key,
    transaction_type_name varchar(50))
    distributed by(id);

create table bank2.transaction_status(
	id integer primary key,
	status varchar)
    distributed by(id);

create table bank2.account_status(
	id integer primary key,
	status varchar)
    distributed by(id);

create table bank2.account_type(
	id integer primary key,
	type varchar)
    distributed by(id);

create table bank2.currency(
	id varchar(3) primary key,
	full_name varchar)
    distributed by(id);

create table bank2.clients(
    id serial primary key,
	name varchar(20) not null,
	surname varchar(40) not null,
	date_of_birth date not null,
	gender varchar(1),
	phone_number bigint not null,
	email varchar(255) not null)
    distributed by (id);

create table bank2.accounts(
	id serial primary key,
	client_id integer references bank2.clients(id),
	type integer references bank2.account_type(id),
	status integer references bank2.account_status(id),
	balance decimal not null,
	currency varchar(3) references bank2.currency(id)
	)
    distributed by (id);

CREATE TABLE bank2.sellers (
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

create table bank2.terminal_type(
	id integer primary key,
	type varchar)
    distributed by(id);


create table bank2.terminals(
	id serial primary key,
	seller_id integer references bank2.sellers(id),
	type integer references bank2.terminal_type(id),
	created_at date)
    distributed by (id);

create table bank2.transactions(
	id serial primary key,
	terminal_id integer references bank2.terminals(id),
	account_id integer references bank2.accounts(id),
	transaction_date timestamp not null,
	amount decimal not null,
	currency varchar(3) references bank2.currency(id),
	status integer references bank2.transaction_status(id)
	)
    distributed by (id);