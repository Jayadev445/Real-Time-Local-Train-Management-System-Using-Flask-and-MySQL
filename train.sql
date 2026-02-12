CREATE DATABASE train_management;

USE train_management;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(100),
    password VARCHAR(100)
);

CREATE TABLE trains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    train_name VARCHAR(100),
    source_station VARCHAR(50),
    destination_station VARCHAR(50),
    departure_time TIME,
    arrival_time TIME,
    total_seats INT,
    available_seats INT,
    status VARCHAR(20)
);

CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    train_id INT,
    seats_booked INT,
    total_amount DECIMAL(10,2),
    status VARCHAR(20)
);
