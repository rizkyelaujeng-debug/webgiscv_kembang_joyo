-- ============================================================
-- Script SQL untuk XAMPP / phpMyAdmin
-- CV. Kembar Joyo - Update Schema
-- Jalankan di phpMyAdmin pada database yang dipakai
-- ============================================================

-- 1. Tambah kolom alamat_tujuan ke tabel pesanan
ALTER TABLE pesanan 
    ADD COLUMN IF NOT EXISTS alamat_tujuan VARCHAR(500) DEFAULT NULL 
    AFTER metode_penerimaan;

-- Verifikasi hasilnya
DESCRIBE pesanan;
