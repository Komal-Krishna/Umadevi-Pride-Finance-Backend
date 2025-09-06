-- Complete Database Schema for Uma Devi's Pride Finance Management System
-- This is the single source of truth for the database structure

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Vehicles Table
CREATE TABLE IF NOT EXISTS vehicles (
    id SERIAL PRIMARY KEY,
    vehicle_name VARCHAR(100) NOT NULL,
    principle_amount NUMERIC(15,2) NOT NULL CHECK (principle_amount > 0),
    rent NUMERIC(15,2) NOT NULL CHECK (rent > 0),
    payment_frequency VARCHAR(20) NOT NULL DEFAULT 'monthly' CHECK (payment_frequency IN ('monthly', 'bimonthly', 'quarterly')),
    date_of_lending DATE NOT NULL,
    lend_to VARCHAR(100) NOT NULL,
    is_closed BOOLEAN NOT NULL DEFAULT FALSE,
    closure_date DATE NULL,
    deleted_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Outside Interest Table
CREATE TABLE IF NOT EXISTS outside_interest (
    id SERIAL PRIMARY KEY,
    to_whom VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    principle_amount DECIMAL(10,2) NOT NULL CHECK (principle_amount > 0),
    interest_rate_percentage DECIMAL(5,2) NOT NULL CHECK (interest_rate_percentage > 0 AND interest_rate_percentage <= 100),
    interest_rate_indian DECIMAL(5,2) NOT NULL CHECK (interest_rate_indian > 0 AND interest_rate_indian <= 100),
    payment_frequency VARCHAR(20) NOT NULL DEFAULT 'monthly' CHECK (payment_frequency IN ('monthly', 'bimonthly', 'quarterly')),
    date_of_lending DATE NOT NULL,
    lend_to VARCHAR(100) NOT NULL,
    is_closed BOOLEAN NOT NULL DEFAULT FALSE,
    closure_date DATE NULL,
    deleted_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Payments Table
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('vehicle', 'outside_interest', 'loan', 'other')),
    source_id INTEGER NULL,
    payment_type VARCHAR(20) NOT NULL CHECK (payment_type IN ('credit', 'debit')),
    payment_date DATE NOT NULL,
    amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
    description TEXT NULL,
    payment_status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (payment_status IN ('PAID', 'PARTIAL', 'PENDING')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Loans Table
CREATE TABLE IF NOT EXISTS loans (
    id SERIAL PRIMARY KEY,
    lender_name VARCHAR(100) NOT NULL,
    lender_type VARCHAR(20) NOT NULL CHECK (lender_type IN ('bank', 'personal', 'other')),
    principle_amount DECIMAL(10,2) NOT NULL CHECK (principle_amount > 0),
    interest_rate DECIMAL(5,2) NOT NULL CHECK (interest_rate > 0 AND interest_rate <= 100),
    payment_frequency VARCHAR(20) NOT NULL DEFAULT 'monthly' CHECK (payment_frequency IN ('monthly', 'bimonthly', 'quarterly')),
    date_of_borrowing DATE NOT NULL,
    is_closed BOOLEAN NOT NULL DEFAULT FALSE,
    closure_date DATE NULL,
    deleted_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_vehicles_lend_to ON vehicles(lend_to);
CREATE INDEX IF NOT EXISTS idx_vehicles_is_closed ON vehicles(is_closed);
CREATE INDEX IF NOT EXISTS idx_vehicles_date_of_lending ON vehicles(date_of_lending);
CREATE INDEX IF NOT EXISTS idx_vehicles_deleted_at ON vehicles(deleted_at);

CREATE INDEX IF NOT EXISTS idx_outside_interest_lend_to ON outside_interest(lend_to);
CREATE INDEX IF NOT EXISTS idx_outside_interest_is_closed ON outside_interest(is_closed);
CREATE INDEX IF NOT EXISTS idx_outside_interest_date_of_lending ON outside_interest(date_of_lending);
CREATE INDEX IF NOT EXISTS idx_outside_interest_deleted_at ON outside_interest(deleted_at);

CREATE INDEX IF NOT EXISTS idx_payments_source_type ON payments(source_type);
CREATE INDEX IF NOT EXISTS idx_payments_source_id ON payments(source_id);
CREATE INDEX IF NOT EXISTS idx_payments_payment_date ON payments(payment_date);
CREATE INDEX IF NOT EXISTS idx_payments_payment_status ON payments(payment_status);

CREATE INDEX IF NOT EXISTS idx_loans_lender_name ON loans(lender_name);
CREATE INDEX IF NOT EXISTS idx_loans_is_closed ON loans(is_closed);
CREATE INDEX IF NOT EXISTS idx_loans_deleted_at ON loans(deleted_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_vehicles_updated_at BEFORE UPDATE ON vehicles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_outside_interest_updated_at BEFORE UPDATE ON outside_interest
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_loans_updated_at BEFORE UPDATE ON loans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
